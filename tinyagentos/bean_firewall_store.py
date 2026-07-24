from __future__ import annotations

"""Bean-4 cognitive firewall store (docs/design/bean-2-5-plan.md, "Bean-4 —
cognitive firewall").

Two tables, following agent_provenance_store.py's latest-wins-baseline /
board_audit.py's append-only-log conventions:

  - ``bean_firewall_baseline`` — one row per agent (PRIMARY KEY agent_name),
    the JSON-serialised baseline dict produced by
    ``bean_firewall.build_baseline``. INSERT OR REPLACE, same "latest known"
    semantics as agent_provenance_store.py — a baseline is a live model of
    "normal", not a history, so rebuilding replaces it.
  - ``bean_firewall_alerts`` — append-only, one row per ``detect()`` call
    that came back anomalous. Never updated or deleted (same spirit as
    board_audit.py): the alert log is the durable evidence trail for "the
    firewall flagged agent X at time T because Y".

This module is pure storage: it never imports ``bean_firewall.py``'s scoring
functions, so the two stay independently testable (same split as
bean_consent_store.py / bean_consent.py).
"""

import json
import time
from typing import Optional

import aiosqlite

from tinyagentos.base_store import BaseStore

SCHEMA = """
CREATE TABLE IF NOT EXISTS bean_firewall_baseline (
    agent_name  TEXT PRIMARY KEY,
    baseline    TEXT NOT NULL,
    updated_at  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS bean_firewall_alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name  TEXT NOT NULL,
    ts          INTEGER NOT NULL,
    score       REAL NOT NULL,
    reasons     TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_bean_firewall_alerts_agent_ts
    ON bean_firewall_alerts(agent_name, ts DESC);
"""


def _baseline_row_to_dict(row: aiosqlite.Row) -> dict:
    try:
        return json.loads(row["baseline"])
    except (ValueError, TypeError):
        return {}


def _alert_row_to_dict(row: aiosqlite.Row) -> dict:
    try:
        reasons = json.loads(row["reasons"])
    except (ValueError, TypeError):
        reasons = []
    return {
        "id": row["id"],
        "agent_name": row["agent_name"],
        "ts": row["ts"],
        "score": row["score"],
        "reasons": reasons,
    }


class BeanFirewallStore(BaseStore):
    """Persistent store for per-agent Bean-4 baselines + the alert log."""

    SCHEMA = SCHEMA

    async def init(self) -> None:
        await super().init()
        if self._db is not None:
            self._db.row_factory = aiosqlite.Row

    async def set_baseline(self, agent: str, baseline: dict) -> dict:
        """Upsert the baseline for *agent* and return it (INSERT OR
        REPLACE — a baseline is the current model of normal, not a
        history; rebuilding replaces the prior one)."""
        if self._db is None:
            raise RuntimeError("BeanFirewallStore not initialised - call init() first")
        now = int(time.time())
        await self._db.execute(
            "INSERT OR REPLACE INTO bean_firewall_baseline (agent_name, baseline, updated_at) "
            "VALUES (?, ?, ?)",
            (agent, json.dumps(baseline), now),
        )
        await self._db.commit()
        return baseline

    async def get_baseline(self, agent: str) -> Optional[dict]:
        """Return the stored baseline dict for *agent*, or ``None`` if
        none has been built yet (a greenfield agent)."""
        if self._db is None:
            raise RuntimeError("BeanFirewallStore not initialised - call init() first")
        row = await (
            await self._db.execute(
                "SELECT * FROM bean_firewall_baseline WHERE agent_name = ?",
                (agent,),
            )
        ).fetchone()
        return _baseline_row_to_dict(row) if row else None

    async def record_alert(self, agent: str, score: float, reasons: list[str]) -> dict:
        """Append an alert row for *agent*. Never updated or deleted —
        the alert log is an evidence trail, not current state. Returns the
        stored row."""
        if self._db is None:
            raise RuntimeError("BeanFirewallStore not initialised - call init() first")
        now = int(time.time())
        cursor = await self._db.execute(
            "INSERT INTO bean_firewall_alerts (agent_name, ts, score, reasons) "
            "VALUES (?, ?, ?, ?)",
            (agent, now, float(score), json.dumps(list(reasons))),
        )
        await self._db.commit()
        row = await (
            await self._db.execute(
                "SELECT * FROM bean_firewall_alerts WHERE id = ?", (cursor.lastrowid,)
            )
        ).fetchone()
        return _alert_row_to_dict(row)

    async def list_alerts(self, agent: str, limit: int = 50) -> list[dict]:
        """Alerts for *agent*, newest first, capped at *limit*."""
        if self._db is None:
            raise RuntimeError("BeanFirewallStore not initialised - call init() first")
        limit = max(1, min(limit, 1000))
        cursor = await self._db.execute(
            "SELECT * FROM bean_firewall_alerts WHERE agent_name = ? "
            "ORDER BY id DESC LIMIT ?",
            (agent, limit),
        )
        rows = await cursor.fetchall()
        return [_alert_row_to_dict(r) for r in rows]


async def bridge_alert_to_notifications(
    notification_store: object,
    agent: str,
    score: float,
    reasons: list[str],
) -> None:
    """Optional one-line bridge: post an already-recorded alert to the
    existing notification store (``tinyagentos/notifications.py``'s
    ``NotificationStore`` — the same sink MCP supervisor errors use, per
    docs/design/bean-2-5-plan.md's "alerts feed the same notification store
    as MCP supervisor errors").

    NOT called automatically by this module. Wiring ``NotificationStore``
    requires a booted app (it lives at ``app.state.notifications``, built
    in ``tinyagentos/app.py``), which is out of scope for a standalone,
    additive-only store module. The integrator's one-line step is:

        from tinyagentos.bean_firewall_store import bridge_alert_to_notifications
        ...
        result = detect(baseline, window_events, threshold)
        if result["anomalous"]:
            await fw_store.record_alert(agent, result["score"], result["reasons"])
            await bridge_alert_to_notifications(
                request.app.state.notifications, agent, result["score"], result["reasons"]
            )

    Until that call is added somewhere, ``record_alert`` above is the
    complete, durable sink — nothing is lost, it simply is not surfaced in
    the notification bell yet.

    *notification_store* is accepted duck-typed (only ``.add()`` is used)
    so this can be unit-tested with a lightweight fake instead of a real
    ``NotificationStore``. Best-effort: any failure is swallowed (matching
    the existing notification call-sites' pattern, e.g.
    scheduler/failure_handler.py / routes/agent_registry.py) so a
    notification-store outage never breaks the firewall's own alert log.
    """
    try:
        await notification_store.add(
            title=f"Cognitive firewall alert: {agent}",
            message=(
                f"Agent '{agent}' scored {score:.2f} against its behavioural "
                f"baseline — {'; '.join(reasons) if reasons else 'off-baseline tool-call topology'}"
            ),
            level="warning",
            source="bean_firewall",
            data={"agent": agent, "score": score, "reasons": reasons},
        )
    except Exception:  # noqa: BLE001 — best-effort bridge, never breaks the caller.
        pass
