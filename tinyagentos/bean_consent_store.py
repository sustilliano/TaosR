from __future__ import annotations

"""Bean-3 consent store - default-closed, per-scope, revocable consent for
physical actuation (docs/design/bean-2-5-plan.md, "Bean-3 - consent gate for
physical actuation").

Grants are keyed by (agent_slug, scope). A grant is ACTIVE iff a row exists
for that pair with revoked_at IS NULL. Revocation never deletes a row - it
stamps revoked_at on the active row(s) - so the table stays append-only in
spirit (history is preserved) while `is_allowed` only ever sees the *latest*
state via the revoked_at IS NULL predicate. There is no DELETE anywhere in
this module.

Storage-only: this module never imports tinyagentos.mcp.bean_consent (the
policy layer) so the two stay independently testable. mcp/permissions.py is
wired to an instance's `is_allowed` via an injected callable - see
bean_consent.py / mcp/permissions.py for how the two compose.
"""

import time
from typing import Optional

import aiosqlite

from tinyagentos.base_store import BaseStore

SCHEMA = """
CREATE TABLE IF NOT EXISTS bean_consent (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_slug  TEXT NOT NULL,
    scope       TEXT NOT NULL,
    granted_at  INTEGER NOT NULL,
    granted_by  TEXT NOT NULL DEFAULT '',
    revoked_at  INTEGER
);
CREATE INDEX IF NOT EXISTS idx_bean_consent_agent_scope
    ON bean_consent(agent_slug, scope);
"""


def _row_to_dict(row: aiosqlite.Row) -> dict:
    return {
        "id": row["id"],
        "agent_slug": row["agent_slug"],
        "scope": row["scope"],
        "granted_at": row["granted_at"],
        "granted_by": row["granted_by"],
        "revoked_at": row["revoked_at"],
    }


class BeanConsentStore(BaseStore):
    """Persistent store for per-(agent, scope) physical-actuation consent."""

    SCHEMA = SCHEMA

    async def init(self) -> None:
        await super().init()
        if self._db is not None:
            self._db.row_factory = aiosqlite.Row

    async def grant(self, agent_slug: str, scope: str, granted_by: str = "") -> dict:
        """Record a new active grant for (agent_slug, scope).

        Does not touch any existing rows for the pair - granting again while
        already granted simply adds another active-looking row is avoided by
        the fact `is_allowed` only needs *one* active row to exist; callers
        that want a clean re-grant should revoke first (list_grants makes the
        current state visible). Returns the new row.
        """
        if self._db is None:
            raise RuntimeError("BeanConsentStore not initialised - call init() first")
        now = int(time.time())
        cursor = await self._db.execute(
            "INSERT INTO bean_consent (agent_slug, scope, granted_at, granted_by, revoked_at) "
            "VALUES (?, ?, ?, ?, NULL)",
            (agent_slug, scope, now, granted_by),
        )
        await self._db.commit()
        row = await (
            await self._db.execute(
                "SELECT * FROM bean_consent WHERE id = ?", (cursor.lastrowid,)
            )
        ).fetchone()
        return _row_to_dict(row)

    async def revoke(self, agent_slug: str, scope: str) -> bool:
        """Stamp revoked_at on any active grant(s) for (agent_slug, scope).

        Idempotent: revoking with no active grant is a no-op that returns
        False. Never deletes a row.
        """
        if self._db is None:
            raise RuntimeError("BeanConsentStore not initialised - call init() first")
        now = int(time.time())
        cursor = await self._db.execute(
            "UPDATE bean_consent SET revoked_at = ? "
            "WHERE agent_slug = ? AND scope = ? AND revoked_at IS NULL",
            (now, agent_slug, scope),
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def is_allowed(self, agent_slug: str, scope: str) -> bool:
        """True iff an active (revoked_at IS NULL) grant exists.

        Default closed: no row for the pair means False.
        """
        if self._db is None:
            raise RuntimeError("BeanConsentStore not initialised - call init() first")
        row = await (
            await self._db.execute(
                "SELECT 1 FROM bean_consent "
                "WHERE agent_slug = ? AND scope = ? AND revoked_at IS NULL LIMIT 1",
                (agent_slug, scope),
            )
        ).fetchone()
        return row is not None

    async def list_grants(self, agent_slug: str) -> list[dict]:
        """All grants (active + historical) for *agent_slug*, newest first."""
        if self._db is None:
            raise RuntimeError("BeanConsentStore not initialised - call init() first")
        cursor = await self._db.execute(
            "SELECT * FROM bean_consent WHERE agent_slug = ? ORDER BY id DESC",
            (agent_slug,),
        )
        rows = await cursor.fetchall()
        return [_row_to_dict(r) for r in rows]
