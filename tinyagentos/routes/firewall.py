"""Bean-4 cognitive firewall API (docs/design/bean-2-5-plan.md, "Bean-4 —
cognitive firewall").

GET  /api/agents/{name}/firewall           — current baseline summary + recent alerts.
POST /api/agents/{name}/firewall/baseline  — (re)build the baseline from provided events.

Follows routes/consent.py's shape: a lazily-created store on app.state, the
same ``_valid_slug`` contract as routes/provenance.py / routes/consent.py /
routes/bean_keys.py, and ``current_user`` auth on every endpoint.

NOT registered anywhere yet: the integrator adds this to routes/__init__.py
when merging (see docs/design/bean-2-5-plan.md "Delegation rules") and, per
bean_firewall_store.bridge_alert_to_notifications's docstring, is also where
the notification-store bridge gets wired in (one line, at the call site
below marked TODO).
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse

from tinyagentos.auth_context import CurrentUser, current_user
from tinyagentos.bean_firewall import (
    DEFAULT_THRESHOLD,
    build_baseline,
    detect,
    empty_baseline,
    is_greenfield,
)

router = APIRouter()

# Same slug shape as routes/provenance.py / routes/consent.py / routes/bean_keys.py.
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _valid_slug(name: str) -> bool:
    return bool(_SLUG_RE.match(name)) and ".." not in name


async def _get_store(request: Request):
    """Get or lazily create the firewall store on app state."""
    store = getattr(request.app.state, "bean_firewall_store", None)
    if store is None:
        from tinyagentos.bean_firewall_store import BeanFirewallStore
        data_dir = getattr(request.app.state, "data_dir", Path("data"))
        store = BeanFirewallStore(Path(data_dir) / "bean_firewall.db")
        await store.init()
        request.app.state.bean_firewall_store = store
    return store


def _baseline_summary(baseline: dict | None) -> dict:
    """Trim a (possibly large) baseline down to a summary safe to hand back
    over the API: counts + tool list, not the full transition matrix."""
    if baseline is None:
        baseline = empty_baseline()
    tool_counts = baseline.get("tool_counts", {}) or {}
    transition_counts = baseline.get("transition_counts", {}) or {}
    return {
        "event_count": baseline.get("event_count", 0),
        "greenfield": is_greenfield(baseline),
        "tools": baseline.get("tools") or sorted(tool_counts.keys()),
        "tool_counts": tool_counts,
        "transition_count": len(transition_counts),
        "top_transitions": sorted(
            transition_counts.items(), key=lambda kv: kv[1], reverse=True
        )[:10],
    }


@router.get("/api/agents/{name}/firewall")
async def get_firewall_status(
    name: str,
    request: Request,
    limit: int = 20,
    user: CurrentUser = Depends(current_user),
):
    """Current baseline summary + recent alerts for agent *name*.

    A never-baselined agent is not a 404: it comes back as a greenfield
    baseline summary (event_count=0) with an empty alert list, matching
    bean_firewall.is_greenfield's "must not crash" contract.
    """
    if not _valid_slug(name):
        return JSONResponse({"error": f"invalid agent name {name!r}"}, status_code=400)
    store = await _get_store(request)
    baseline = await store.get_baseline(name)
    alerts = await store.list_alerts(name, limit=limit)
    return {
        "agent_name": name,
        "baseline": _baseline_summary(baseline),
        "alerts": alerts,
    }


@router.post("/api/agents/{name}/firewall/baseline")
async def rebuild_firewall_baseline(
    name: str,
    request: Request,
    body: dict = Body(default={}),
    user: CurrentUser = Depends(current_user),
):
    """Rebuild agent *name*'s baseline.

    Body shape: ``{"events": [{"agent": ..., "tool": ..., "ts": ...}, ...]}``.
    ``agent`` may be omitted on each event (defaults to *name*) or present
    for defensive filtering against a mixed-agent payload — either way only
    events belonging to *name* are folded into the baseline (see
    ``bean_firewall.build_baseline``'s ``agent=`` filter).

    Documented source for "or a documented source": events are supplied by
    the caller, not read from a store here. The obvious real source is
    ``tinyagentos.bean_firewall.events_from_trace_store`` fed from
    ``TraceStoreRegistry.get(name)`` (see that function's docstring) — that
    call needs a booted app's trace registry, so it is left to the caller
    (e.g. a scheduled job or an admin action) to fetch events and POST them
    here, rather than this route reaching into app internals itself.
    """
    if not _valid_slug(name):
        return JSONResponse({"error": f"invalid agent name {name!r}"}, status_code=400)
    events = body.get("events")
    if not isinstance(events, list):
        return JSONResponse(
            {"error": "body.events must be a list of {agent, tool, ts} objects"},
            status_code=400,
        )
    # Default each event's agent to *name* so callers may omit it; still
    # filtered through build_baseline's agent= so a stray foreign-agent
    # event in the payload can never contaminate this agent's baseline.
    normalised = [dict(ev, agent=ev.get("agent") or name) for ev in events]
    baseline = build_baseline(normalised, agent=name)
    store = await _get_store(request)
    await store.set_baseline(name, baseline)
    return {"agent_name": name, "baseline": _baseline_summary(baseline)}


@router.post("/api/agents/{name}/firewall/check")
async def check_firewall_window(
    name: str,
    request: Request,
    body: dict = Body(default={}),
    user: CurrentUser = Depends(current_user),
):
    """Score a window of recent events against *name*'s stored baseline and
    record an alert if it comes back anomalous.

    Body shape: ``{"events": [...], "threshold": 0.6}`` (threshold optional,
    defaults to ``bean_firewall.DEFAULT_THRESHOLD``). This is the endpoint a
    caller (scheduled job, or the integrator's tool-call hook) uses to
    actually run detection; ``/firewall/baseline`` above only builds the
    model. On an anomalous result the alert is appended to this store's
    alert log unconditionally; bridging it to the shared notification store
    is the documented one-line integrator step — see
    bean_firewall_store.bridge_alert_to_notifications's docstring.
    """
    if not _valid_slug(name):
        return JSONResponse({"error": f"invalid agent name {name!r}"}, status_code=400)
    events = body.get("events")
    if not isinstance(events, list):
        return JSONResponse(
            {"error": "body.events must be a list of {agent, tool, ts} objects"},
            status_code=400,
        )
    threshold = body.get("threshold", DEFAULT_THRESHOLD)
    store = await _get_store(request)
    baseline = await store.get_baseline(name)
    normalised = [dict(ev, agent=ev.get("agent") or name) for ev in events]
    result = detect(baseline, normalised, threshold=threshold)
    if result["anomalous"]:
        await store.record_alert(name, result["score"], result["reasons"])
        # TODO: wire real sink — bridge to the shared notification store
        # (tinyagentos.notifications.NotificationStore at
        # request.app.state.notifications) once this router is registered
        # in a booted app; see bean_firewall_store.bridge_alert_to_notifications.
    return {"agent_name": name, **result}
