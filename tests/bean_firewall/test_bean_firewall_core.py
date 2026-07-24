"""Tests for the Bean-4 cognitive-firewall pure core
(tinyagentos/bean_firewall.py).

Covers: baseline building (incl. JSON round-trip + multi-agent filtering),
in-distribution windows scoring high, an injected unseen-actuation burst
scoring low with the actuation reason named verbatim, unseen-transition-only
drift, frequency-divergence-only drift, greenfield/empty-window safety, and
the trace_store adapter against a lightweight fake.
"""
from __future__ import annotations

import json

import pytest

from tinyagentos.bean_firewall import (
    DEFAULT_THRESHOLD,
    build_baseline,
    detect,
    empty_baseline,
    events_from_trace_store,
    is_greenfield,
    score_window,
)
from tinyagentos.bean_consent import FLAGGED_SCOPES


def _mk(agent: str, tool: str, ts: float) -> dict:
    return {"agent": agent, "tool": tool, "ts": ts}


def _patrol_events(agent: str = "scout-1", n_pairs: int = 10, start_ts: float = 0.0) -> list[dict]:
    """Alternating list_tanks/fleet_status — a normal, boring patrol rhythm.
    Neither tool is a flagged actuation scope."""
    events = []
    ts = start_ts
    for _ in range(n_pairs):
        events.append(_mk(agent, "list_tanks", ts)); ts += 1
        events.append(_mk(agent, "fleet_status", ts)); ts += 1
    return events


class TestBuildBaseline:
    def test_basic_counts_and_transitions(self):
        events = _patrol_events(n_pairs=5)
        baseline = build_baseline(events, agent="scout-1")
        assert baseline["event_count"] == 10
        assert baseline["tool_counts"] == {"list_tanks": 5, "fleet_status": 5}
        assert baseline["transition_counts"]["list_tanks->fleet_status"] == 5
        assert baseline["transition_counts"]["fleet_status->list_tanks"] == 4
        assert baseline["tools"] == ["fleet_status", "list_tanks"]

    def test_json_round_trip_is_identical(self):
        events = _patrol_events(n_pairs=3)
        baseline = build_baseline(events, agent="scout-1")
        restored = json.loads(json.dumps(baseline))
        assert restored == baseline

    def test_agent_filter_ignores_other_agents(self):
        mixed = _patrol_events(agent="scout-1", n_pairs=3) + _patrol_events(
            agent="scout-2", n_pairs=7
        )
        baseline = build_baseline(mixed, agent="scout-1")
        assert baseline["event_count"] == 6

    def test_no_agent_filter_uses_everything_given(self):
        events = _patrol_events(agent="scout-1", n_pairs=2)
        baseline = build_baseline(events)
        assert baseline["event_count"] == 4
        assert baseline["agent"] is None

    def test_out_of_order_events_are_sorted_by_ts(self):
        events = [
            _mk("scout-1", "fleet_status", 2.0),
            _mk("scout-1", "list_tanks", 1.0),
        ]
        baseline = build_baseline(events, agent="scout-1")
        # Chronological order is list_tanks(ts=1) -> fleet_status(ts=2).
        assert baseline["transition_counts"] == {"list_tanks->fleet_status": 1}

    def test_empty_events_gives_greenfield_shaped_baseline(self):
        baseline = build_baseline([], agent="scout-1")
        assert baseline["event_count"] == 0
        assert is_greenfield(baseline)


class TestGreenfieldAndEmptyWindow:
    def test_none_baseline_never_crashes(self):
        result = detect(None, _patrol_events(n_pairs=2), threshold=DEFAULT_THRESHOLD)
        assert result["score"] == 0.5
        assert result["anomalous"] is False

    def test_empty_baseline_dict_never_crashes(self):
        result = detect(empty_baseline("scout-1"), _patrol_events(n_pairs=2), threshold=0.9)
        assert result["anomalous"] is False
        assert result["score"] == 0.5

    def test_greenfield_score_window_is_neutral_constant(self):
        assert score_window(None, _patrol_events(n_pairs=1)) == 0.5
        assert score_window(empty_baseline(), []) == 0.5  # still greenfield even with no window

    def test_empty_window_against_real_baseline_scores_full_trust(self):
        baseline = build_baseline(_patrol_events(n_pairs=10), agent="scout-1")
        assert score_window(baseline, []) == 1.0
        result = detect(baseline, [], threshold=0.99)
        assert result["anomalous"] is False
        assert result["reasons"] == []


class TestInDistributionWindow:
    def test_matching_rhythm_scores_high_and_is_not_anomalous(self):
        baseline = build_baseline(_patrol_events(n_pairs=20), agent="scout-1")
        window = _patrol_events(n_pairs=4, start_ts=1000.0)
        score = score_window(baseline, window)
        assert score >= 0.95
        result = detect(baseline, window, threshold=DEFAULT_THRESHOLD)
        assert result["anomalous"] is False
        assert result["reasons"] == []


class TestInjectedActuationBurst:
    def test_unseen_actuation_scores_low_and_names_it(self):
        baseline = build_baseline(_patrol_events(n_pairs=20), agent="scout-1")
        assert "drive" in FLAGGED_SCOPES  # sanity: relying on the real flagged set

        window = [
            _mk("scout-1", "list_tanks", 2000.0),
            _mk("scout-1", "fleet_status", 2001.0),
            _mk("scout-1", "drive", 2002.0),
            _mk("scout-1", "drive", 2003.0),
        ]
        score = score_window(baseline, window)
        assert score < DEFAULT_THRESHOLD

        result = detect(baseline, window, threshold=DEFAULT_THRESHOLD)
        assert result["anomalous"] is True
        assert result["score"] == score
        assert "unseen tool 'drive' in a window with no prior actuation" in result["reasons"]
        # The burst reason (rate of actuation vs baseline) is also first-class.
        assert any("burst of physical-actuation" in r for r in result["reasons"])

    def test_actuation_reasons_come_before_generic_reasons(self):
        baseline = build_baseline(_patrol_events(n_pairs=20), agent="scout-1")
        window = [
            _mk("scout-1", "list_tanks", 2000.0),
            _mk("scout-1", "drive", 2001.0),
            _mk("scout-1", "some_other_new_tool", 2002.0),
        ]
        result = detect(baseline, window, threshold=DEFAULT_THRESHOLD)
        assert result["anomalous"] is True
        drive_idx = next(
            i for i, r in enumerate(result["reasons"]) if "drive" in r and "unseen tool" in r
        )
        other_idx = next(
            i
            for i, r in enumerate(result["reasons"])
            if "some_other_new_tool" in r
        )
        assert drive_idx < other_idx

    def test_below_threshold_score_boundary_is_not_anomalous(self):
        # score == threshold is documented as in-distribution (strict <).
        baseline = build_baseline(_patrol_events(n_pairs=20), agent="scout-1")
        window = _patrol_events(n_pairs=2, start_ts=5000.0)
        score = score_window(baseline, window)
        result = detect(baseline, window, threshold=score)  # threshold == score exactly
        assert result["anomalous"] is False


class TestUnseenTransitionOnly:
    def test_familiar_tools_unfamiliar_order_is_flagged(self):
        # Baseline only ever goes list_tanks -> fleet_status -> list_tanks ...
        baseline = build_baseline(_patrol_events(n_pairs=20), agent="scout-1")
        # Window repeats fleet_status back-to-back — a transition never seen.
        window = [
            _mk("scout-1", "fleet_status", 9000.0),
            _mk("scout-1", "fleet_status", 9001.0),
            _mk("scout-1", "fleet_status", 9002.0),
        ]
        result = detect(baseline, window, threshold=0.95)
        assert result["anomalous"] is True
        assert any("fleet_status->fleet_status" in r for r in result["reasons"])


class TestFrequencyDivergence:
    def test_pure_mix_shift_with_known_tools_and_transitions_is_named(self):
        # Baseline: heavily list_tanks-weighted, but constructed so all four
        # possible transitions between the two tools (LT->LT, LT->FS, FS->LT,
        # FS->FS) occur at least once — so a mix-shift window can be built
        # below using only already-known transitions, isolating the
        # frequency-divergence signal from the unseen-transition one.
        tools = []
        for _ in range(9):
            tools += ["list_tanks"] * 8 + ["fleet_status"]
        tools += ["fleet_status", "fleet_status"]  # adds one FS->FS occurrence
        events = [_mk("scout-1", t, float(i)) for i, t in enumerate(tools)]
        baseline = build_baseline(events, agent="scout-1")
        assert set(baseline["transition_counts"]) == {
            "list_tanks->list_tanks",
            "list_tanks->fleet_status",
            "fleet_status->list_tanks",
            "fleet_status->fleet_status",
        }
        baseline_fs_share = baseline["tool_counts"]["fleet_status"] / baseline["event_count"]
        assert baseline_fs_share < 0.2  # confirm it really is list_tanks-heavy

        # Window: same two known tools, only already-known transitions, but
        # the mix is inverted — mostly fleet_status now.
        window = [_mk("scout-1", "fleet_status", 5000.0 + i) for i in range(8)] + [
            _mk("scout-1", "list_tanks", 5100.0)
        ]
        result = detect(baseline, window, threshold=0.9)
        assert result["anomalous"] is True
        assert any("frequency diverges" in r for r in result["reasons"])
        # No unseen-tool or unseen-transition reasons should fire here.
        assert not any("unseen tool" in r for r in result["reasons"])
        assert not any("never seen in baseline" in r and "transition" in r for r in result["reasons"])


class _FakeTraceStore:
    """Duck-typed stand-in for trace_store.AgentTraceStore — only the
    surface events_from_trace_store() touches (.list(), .slug)."""

    def __init__(self, slug: str, envelopes: list[dict]):
        self.slug = slug
        self._envelopes = envelopes

    async def list(self, *, kind=None, limit=100):
        rows = [e for e in self._envelopes if kind is None or e.get("kind") == kind]
        return rows[:limit]  # already newest-first, like the real store


class TestTraceStoreAdapter:
    @pytest.mark.asyncio
    async def test_reads_tool_call_events_in_chronological_order(self):
        # Real trace_store.list() returns newest-first.
        envelopes = [
            {
                "kind": "tool_call",
                "agent_name": "scout-1",
                "created_at": 300.0,
                "payload": {"tool": "drive", "args": {}, "caller": "scout-1"},
            },
            {
                "kind": "tool_call",
                "agent_name": "scout-1",
                "created_at": 200.0,
                "payload": {"tool": "fleet_status", "args": {}, "caller": "scout-1"},
            },
            {
                "kind": "message_in",  # not a tool_call — the real store would
                "agent_name": "scout-1",  # filter this out via kind=, but the
                "created_at": 250.0,  # fake honours kind= just like the real one.
                "payload": {"from": "user", "text": "hi"},
            },
            {
                "kind": "tool_call",
                "agent_name": "scout-1",
                "created_at": 100.0,
                "payload": {"tool": "list_tanks", "args": {}, "caller": "scout-1"},
            },
        ]
        store = _FakeTraceStore("scout-1", envelopes)
        events = await events_from_trace_store(store)
        assert [e["tool"] for e in events] == ["list_tanks", "fleet_status", "drive"]
        assert [e["ts"] for e in events] == [100.0, 200.0, 300.0]
        assert all(e["agent"] == "scout-1" for e in events)

    @pytest.mark.asyncio
    async def test_events_are_directly_usable_by_build_baseline(self):
        envelopes = [
            {
                "kind": "tool_call",
                "agent_name": "scout-1",
                "created_at": float(i),
                "payload": {"tool": "list_tanks" if i % 2 == 0 else "fleet_status"},
            }
            for i in reversed(range(10))
        ]
        store = _FakeTraceStore("scout-1", envelopes)
        events = await events_from_trace_store(store)
        baseline = build_baseline(events, agent="scout-1")
        assert baseline["event_count"] == 10
