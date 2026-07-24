from __future__ import annotations

"""Bean-4 cognitive firewall (docs/design/bean-2-5-plan.md, "Bean-4 —
cognitive firewall (tool-call topology baseline)"); see also
docs/design/silicon-bean-integration.md's "Cognitive firewall (output-
topology baseline)" row.

Pure, synchronous, stdlib-only core. Operates entirely on in-memory lists of
tool-call events — deliberately decoupled from *where* those events come
from (taOS records tool activity in a few different places; see
bean_firewall_store.py / the adapter note below for how a real source is
wired in). Every event is a plain dict:

    {"agent": "<agent-name>", "tool": "<tool-name>", "ts": <epoch float>}

A *baseline* is the per-agent model of "normal" tool-call topology built by
``build_baseline`` — a JSON-friendly dict (plain str/int/float/dict), so it
round-trips through ``json.dumps``/``json.loads`` unchanged and can be
persisted verbatim by bean_firewall_store.py.

--- The scoring formula ---

``score_window`` blends three signals into one score in [0, 1] (1 = fully
in-distribution, 0 = maximally anomalous):

1. **Unseen-tool rate** — the fraction of events in the window whose tool
   was never called by this agent in the baseline period. A brand-new tool
   appearing is the single strongest topology signal (this is exactly what
   "an injected agent suddenly issuing `drive`" looks like).
2. **Unseen-transition rate** — the fraction of consecutive
   ``tool_a -> tool_b`` pairs in the window that never occurred in the
   baseline's first-order transition counts. Catches an agent using
   familiar tools in an unfamiliar *order* (e.g. a normally read-only agent
   suddenly chaining straight into an actuator call).
3. **Frequency divergence** — total-variation distance between the
   baseline's and the window's tool-frequency distributions (each
   normalised to sum to 1, compared over the union of tools seen on either
   side). Catches a mix-shift even when every tool itself is familiar and
   every transition has happened before (e.g. a patrol agent that normally
   calls `drive` 5% of the time suddenly calling it 60% of the time).

    score = 1 - (W_UNSEEN_TOOL       * unseen_tool_rate
                 + W_UNSEEN_TRANSITION * unseen_transition_rate
                 + W_FREQ_DIVERGENCE   * freq_divergence)

with weights ``UNSEEN_TOOL_WEIGHT + UNSEEN_TRANSITION_WEIGHT +
FREQ_DIVERGENCE_WEIGHT == 1.0`` (see the constants below), clamped to
[0, 1].

Convention for degenerate inputs (documented, not a crash):
  - **Greenfield baseline** (no prior history for this agent, i.e.
    ``event_count == 0``) — there is nothing to compare against, so the
    score is neither "in-distribution" nor "anomalous"; it is the neutral
    constant ``GREENFIELD_SCORE`` (0.5), and ``detect`` always reports
    ``anomalous=False`` for a greenfield baseline (you cannot fairly
    penalise an agent for having no history yet).
  - **Empty window** — nothing happened, so there is no evidence of
    anomalous behaviour; the score is ``EMPTY_WINDOW_SCORE`` (1.0).

--- Actuation burst: the first-class reason ---

Per docs/design/silicon-bean-integration.md, the threat that matters most
for the robotics edition is a prompt-injected agent suddenly issuing
physical-actuation commands. ``FLAGGED_SCOPES`` (imported from
``tinyagentos.bean_consent`` to stay consistent with the Bean-3 consent
gate) names those tools (drive, stop, camera_look, set_mode, autonomy,
ptz_move). ``detect`` always surfaces two actuation-specific reasons ahead
of the generic ones, when applicable:

  - an actuation tool appears in the window that the baseline never saw at
    all, worded exactly as "unseen tool '<tool>' in a window with no prior
    actuation" when the agent has *no* actuation history whatsoever, or a
    slightly different wording when the agent has used *other* actuation
    tools before but not this one;
  - a *rate* burst — actuation calls make up a much larger share of the
    window than they did historically (``ACTUATION_BURST_MARGIN``), even
    when every individual tool/transition has been seen before (e.g. an
    agent that already had `drive` in its repertoire but normally used it
    rarely, now spamming it).

Both checks are folded into the same score above (they show up as unseen
tools / unseen transitions / frequency divergence); this module additionally
*names* them explicitly in ``detect``'s ``reasons`` so an operator does not
have to reverse-engineer the number.
"""

import time
from typing import Any

from tinyagentos.bean_consent import FLAGGED_SCOPES

# --- scoring weights (sum to 1.0) ---
UNSEEN_TOOL_WEIGHT = 0.40
UNSEEN_TRANSITION_WEIGHT = 0.35
FREQ_DIVERGENCE_WEIGHT = 0.25

# --- degenerate-input conventions ---
GREENFIELD_SCORE = 0.5
EMPTY_WINDOW_SCORE = 1.0

# --- reason-surfacing thresholds (independent of the score weights above;
# these only control which explanatory reasons get named, not the score) ---
FREQ_DIVERGENCE_REASON_THRESHOLD = 0.30
ACTUATION_BURST_MARGIN = 0.25

# How many distinct unseen tools / transitions to name individually before
# collapsing the rest into an "...and N more" summary reason.
_MAX_NAMED_REASONS = 5

DEFAULT_THRESHOLD = 0.6

BASELINE_VERSION = 1


def _sorted_events(events: list[dict]) -> list[dict]:
    """Chronological copy of *events* (stable sort on ``ts``, missing ts
    treated as 0 so callers that omit it still get deterministic order)."""
    return sorted(events, key=lambda e: e.get("ts") or 0)


def empty_baseline(agent: str | None = None) -> dict:
    """The canonical greenfield baseline: no history yet for this agent."""
    return {
        "version": BASELINE_VERSION,
        "agent": agent,
        "event_count": 0,
        "tool_counts": {},
        "transition_counts": {},
        "tools": [],
    }


def is_greenfield(baseline: dict | None) -> bool:
    """True iff *baseline* has no recorded history (None counts as
    greenfield too, so callers can pass ``store.get_baseline(agent)``
    straight through without a None-check)."""
    if not baseline:
        return True
    return int(baseline.get("event_count", 0)) <= 0


def build_baseline(events: list[dict], agent: str | None = None) -> dict:
    """Build a per-agent baseline from a list of ``{agent, tool, ts}`` events.

    If *agent* is given, only events with ``event["agent"] == agent`` are
    used — so callers may pass a mixed-agent event log straight from a
    shared store without pre-filtering. If omitted, every event given is
    treated as belonging to one agent (the caller is responsible for
    pre-filtering); this matches how bean_firewall_store.py keys one
    baseline per agent name.

    Returns a plain JSON-friendly dict:
        {
          "version": 1,
          "agent": agent or None,
          "event_count": N,                      # events used
          "tool_counts": {tool: count},
          "transition_counts": {"a->b": count},   # first-order, ordered
          "tools": [sorted tool names],
        }
    """
    filtered = [e for e in events if agent is None or e.get("agent") == agent]
    ordered = _sorted_events(filtered)

    tool_counts: dict[str, int] = {}
    transition_counts: dict[str, int] = {}
    prev_tool: str | None = None
    for ev in ordered:
        tool = ev.get("tool")
        if not tool:
            continue
        tool_counts[tool] = tool_counts.get(tool, 0) + 1
        if prev_tool is not None:
            key = f"{prev_tool}->{tool}"
            transition_counts[key] = transition_counts.get(key, 0) + 1
        prev_tool = tool

    return {
        "version": BASELINE_VERSION,
        "agent": agent,
        "event_count": sum(tool_counts.values()),
        "tool_counts": tool_counts,
        "transition_counts": transition_counts,
        "tools": sorted(tool_counts.keys()),
    }


def _transition_pairs(ordered_events: list[dict]) -> list[tuple[str, str]]:
    pairs = []
    prev_tool: str | None = None
    for ev in ordered_events:
        tool = ev.get("tool")
        if not tool:
            continue
        if prev_tool is not None:
            pairs.append((prev_tool, tool))
        prev_tool = tool
    return pairs


def _freq_divergence(baseline_tool_counts: dict, window_tool_counts: dict) -> float:
    """Total-variation distance in [0, 1] between the two normalised tool
    frequency distributions (compared over the union of tools seen on
    either side; a tool absent from one side contributes its full weight
    from the other)."""
    base_total = sum(baseline_tool_counts.values())
    win_total = sum(window_tool_counts.values())
    if base_total == 0 or win_total == 0:
        return 0.0
    tools = set(baseline_tool_counts) | set(window_tool_counts)
    diff_sum = 0.0
    for t in tools:
        p = baseline_tool_counts.get(t, 0) / base_total
        q = window_tool_counts.get(t, 0) / win_total
        diff_sum += abs(p - q)
    return min(1.0, 0.5 * diff_sum)


def _analyze(baseline: dict | None, window_events: list[dict]) -> dict:
    """Shared internals for score_window()/detect(): one pass over the
    window against the baseline, producing every stat both need."""
    greenfield = is_greenfield(baseline)
    ordered = _sorted_events(window_events)
    n = len(ordered)

    if greenfield:
        return {
            "score": GREENFIELD_SCORE,
            "greenfield": True,
            "empty_window": n == 0,
            "n": n,
            "unseen_tool_rate": 0.0,
            "unseen_transition_rate": 0.0,
            "freq_divergence": 0.0,
            "unseen_tools": [],
            "unseen_actuation_tools": [],
            "unseen_transitions": [],
            "window_actuation_rate": 0.0,
            "baseline_actuation_rate": 0.0,
        }

    if n == 0:
        return {
            "score": EMPTY_WINDOW_SCORE,
            "greenfield": False,
            "empty_window": True,
            "n": 0,
            "unseen_tool_rate": 0.0,
            "unseen_transition_rate": 0.0,
            "freq_divergence": 0.0,
            "unseen_tools": [],
            "unseen_actuation_tools": [],
            "unseen_transitions": [],
            "window_actuation_rate": 0.0,
            "baseline_actuation_rate": 0.0,
        }

    baseline_tool_counts: dict[str, int] = baseline.get("tool_counts", {}) or {}
    baseline_transitions: dict[str, int] = baseline.get("transition_counts", {}) or {}
    baseline_total = sum(baseline_tool_counts.values())

    window_tool_counts: dict[str, int] = {}
    unseen_tools: list[str] = []
    seen_unseen: set[str] = set()
    for ev in ordered:
        tool = ev.get("tool")
        if not tool:
            continue
        window_tool_counts[tool] = window_tool_counts.get(tool, 0) + 1
        if tool not in baseline_tool_counts and tool not in seen_unseen:
            seen_unseen.add(tool)
            unseen_tools.append(tool)
    unseen_tool_events = sum(
        1 for ev in ordered if ev.get("tool") and ev["tool"] not in baseline_tool_counts
    )
    unseen_tool_rate = unseen_tool_events / n

    pairs = _transition_pairs(ordered)
    n_trans = len(pairs)
    unseen_transitions: list[tuple[str, str]] = []
    seen_unseen_trans: set[tuple[str, str]] = set()
    if n_trans:
        unseen_trans_count = 0
        for a, b in pairs:
            key = f"{a}->{b}"
            if key not in baseline_transitions:
                unseen_trans_count += 1
                if (a, b) not in seen_unseen_trans:
                    seen_unseen_trans.add((a, b))
                    unseen_transitions.append((a, b))
        unseen_transition_rate = unseen_trans_count / n_trans
    else:
        # Can't judge order with fewer than 2 events — neutral, not anomalous.
        unseen_transition_rate = 0.0

    freq_divergence = _freq_divergence(baseline_tool_counts, window_tool_counts)

    score = 1.0 - (
        UNSEEN_TOOL_WEIGHT * unseen_tool_rate
        + UNSEEN_TRANSITION_WEIGHT * unseen_transition_rate
        + FREQ_DIVERGENCE_WEIGHT * freq_divergence
    )
    score = max(0.0, min(1.0, score))

    # Actuation-specific stats (first-class reason material — see module
    # docstring). Kept separate from the generic unseen-tool bookkeeping
    # above so detect() can word them specially.
    unseen_actuation_tools = [t for t in unseen_tools if t in FLAGGED_SCOPES]
    window_actuation_events = sum(
        1 for ev in ordered if ev.get("tool") in FLAGGED_SCOPES
    )
    window_actuation_rate = window_actuation_events / n
    baseline_actuation_total = sum(
        c for t, c in baseline_tool_counts.items() if t in FLAGGED_SCOPES
    )
    baseline_actuation_rate = (
        baseline_actuation_total / baseline_total if baseline_total else 0.0
    )

    return {
        "score": score,
        "greenfield": False,
        "empty_window": False,
        "n": n,
        "unseen_tool_rate": unseen_tool_rate,
        "unseen_transition_rate": unseen_transition_rate,
        "freq_divergence": freq_divergence,
        "unseen_tools": unseen_tools,
        "unseen_actuation_tools": unseen_actuation_tools,
        "unseen_transitions": unseen_transitions,
        "window_actuation_rate": window_actuation_rate,
        "baseline_actuation_rate": baseline_actuation_rate,
    }


def score_window(baseline: dict | None, window_events: list[dict]) -> float:
    """Score *window_events* against *baseline*; see module docstring for
    the formula. Always returns a float in [0, 1]; never raises for an
    empty window or a greenfield (or None) baseline — see the documented
    conventions above."""
    return _analyze(baseline, window_events)["score"]


def _reasons_from_analysis(stats: dict) -> list[str]:
    reasons: list[str] = []

    if stats["greenfield"]:
        reasons.append(
            "no baseline history yet for this agent (greenfield) — cannot "
            "evaluate topology drift; treating as non-anomalous by convention"
        )
        return reasons

    if stats["empty_window"]:
        return reasons  # nothing happened; no reasons to report

    # --- 1. Actuation-specific reasons, first-class (see module docstring) ---
    baseline_actuation_rate = stats["baseline_actuation_rate"]
    for tool in stats["unseen_actuation_tools"][:_MAX_NAMED_REASONS]:
        if baseline_actuation_rate == 0.0:
            reasons.append(
                f"unseen tool '{tool}' in a window with no prior actuation"
            )
        else:
            reasons.append(
                f"unseen tool '{tool}' (physical actuation) never seen in "
                f"baseline, though other actuation exists"
            )
    if len(stats["unseen_actuation_tools"]) > _MAX_NAMED_REASONS:
        reasons.append(
            f"...and {len(stats['unseen_actuation_tools']) - _MAX_NAMED_REASONS} "
            "more unseen actuation tool(s)"
        )

    if (
        stats["window_actuation_rate"] > 0.0
        and (stats["window_actuation_rate"] - baseline_actuation_rate)
        >= ACTUATION_BURST_MARGIN
    ):
        reasons.append(
            "burst of physical-actuation tool calls: actuation made up "
            f"{stats['window_actuation_rate']:.0%} of this window vs "
            f"{baseline_actuation_rate:.0%} normally"
        )

    # --- 2. Generic unseen tools (non-actuation ones not already named above) ---
    other_unseen = [t for t in stats["unseen_tools"] if t not in FLAGGED_SCOPES]
    for tool in other_unseen[:_MAX_NAMED_REASONS]:
        reasons.append(f"unseen tool '{tool}' never seen in baseline")
    if len(other_unseen) > _MAX_NAMED_REASONS:
        reasons.append(f"...and {len(other_unseen) - _MAX_NAMED_REASONS} more unseen tool(s)")

    # --- 3. Unseen transitions ---
    for a, b in stats["unseen_transitions"][:_MAX_NAMED_REASONS]:
        reasons.append(f"transition {a}->{b} never seen in baseline")
    if len(stats["unseen_transitions"]) > _MAX_NAMED_REASONS:
        reasons.append(
            f"...and {len(stats['unseen_transitions']) - _MAX_NAMED_REASONS} "
            "more unseen transition(s)"
        )

    # --- 4. Frequency divergence ---
    if stats["freq_divergence"] >= FREQ_DIVERGENCE_REASON_THRESHOLD:
        reasons.append(
            "tool-usage frequency diverges from baseline "
            f"(Δ={stats['freq_divergence']:.2f} "
            f"≥ {FREQ_DIVERGENCE_REASON_THRESHOLD:.2f})"
        )

    return reasons


def detect(
    baseline: dict | None,
    window_events: list[dict],
    threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    """Score *window_events* against *baseline* and decide whether it is
    off-baseline enough to alert on.

    Returns ``{"score": float, "anomalous": bool, "reasons": [str, ...]}``.

    - A greenfield baseline (no history) always yields ``anomalous=False``
      (see ``GREENFIELD_SCORE`` convention) — a new agent cannot yet be
      judged.
    - Otherwise ``anomalous = score < threshold`` (strictly less than —
      landing exactly on the threshold is treated as in-distribution).
    - ``reasons`` is populated only when ``anomalous`` is True (they
      enumerate what tripped it); a greenfield baseline is the one
      exception, where a single explanatory (non-tripping) reason is
      included for transparency even though anomalous is False.
    """
    stats = _analyze(baseline, window_events)
    if stats["greenfield"]:
        return {
            "score": stats["score"],
            "anomalous": False,
            "reasons": _reasons_from_analysis(stats),
        }
    anomalous = stats["score"] < threshold
    reasons = _reasons_from_analysis(stats) if anomalous else []
    return {"score": stats["score"], "anomalous": anomalous, "reasons": reasons}


# ---------------------------------------------------------------------------
# Optional adapter: read recent tool-call events from an existing store.
#
# taOS records tool activity in tinyagentos/trace_store.py — one
# AgentTraceStore per agent slug, with a "tool_call" event kind whose payload
# is {"tool": str, "args": dict, "caller": str} (see trace_store.py's
# ENVELOPE_V1_SCHEMA). That is an obvious, already-per-agent source of
# exactly the {agent, tool, ts} shape this module needs, so it is wired
# below rather than left as a stub.
#
# tinyagentos/board_audit.py was also read (per the task): it is an
# append-only log of *board task* status transitions (event/from_status/
# to_status keyed by task_id), not per-agent tool-call history — there is no
# tool name or agent-topology signal in it, so no adapter is provided for it.
# If a future phase wants board activity folded into the firewall (e.g.
# "agent X closed N tasks" as a coarse behavioural signal), that is a
# schema-shaped decision left to that phase, not invented here.
# ---------------------------------------------------------------------------


async def events_from_trace_store(agent_trace_store: Any, limit: int = 500) -> list[dict]:
    """Read recent tool-call events for one agent out of its
    ``trace_store.AgentTraceStore``, in the ``{agent, tool, ts}`` shape
    ``build_baseline``/``score_window``/``detect`` expect.

    *agent_trace_store* is a ``tinyagentos.trace_store.AgentTraceStore``
    instance (typically obtained via
    ``TraceStoreRegistry.get(agent_slug)``) — accepted duck-typed (only
    ``.list()`` and ``.slug`` are used) so tests can pass a lightweight
    fake without importing aiosqlite. Returns events oldest-first (trace
    store's ``list()`` is newest-first; this adapter reverses it since the
    firewall core needs chronological order for transitions).

    Events whose payload has no ``tool`` key (malformed / non-tool_call
    rows that slipped through a `kind` filter) are skipped defensively.
    """
    raw = await agent_trace_store.list(kind="tool_call", limit=limit)
    events: list[dict] = []
    for envelope in reversed(raw):  # newest-first -> chronological
        payload = envelope.get("payload") or {}
        tool = payload.get("tool")
        if not tool:
            continue
        events.append(
            {
                "agent": envelope.get("agent_name") or getattr(agent_trace_store, "slug", None),
                "tool": tool,
                "ts": envelope.get("created_at") or time.time(),
            }
        )
    return events
