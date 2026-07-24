from __future__ import annotations

"""Agent provenance store - Bean-0 of the silicon-bean integration.

Holds the *latest known* provenance record per deployed agent: the hashes
binding an agent to the framework, constitution (system prompt/template),
model, and corpus that produced it (see
docs/design/silicon-bean-integration.md).  One row per agent_name; setting
again overwrites - record history is deliberately out of scope for Bean-0.

The full record is stored verbatim as JSON; constitution_sha256, model_id
and recorded_at are denormalised into columns for cheap filtering later
(Bean-1 receipts will join on them).
"""

import json
import time
from datetime import datetime
from typing import Optional

import aiosqlite

from tinyagentos.base_store import BaseStore

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_provenance (
    agent_name          TEXT PRIMARY KEY,
    record              TEXT NOT NULL,
    constitution_sha256 TEXT,
    model_id            TEXT,
    recorded_at         INTEGER
);
"""


def _recorded_at_epoch(record: dict) -> int:
    """Return the record's recorded_at as a unix timestamp, or now."""
    raw = record.get("recorded_at")
    if isinstance(raw, str) and raw:
        try:
            return int(datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp())
        except ValueError:
            pass
    return int(time.time())


def _row_to_entry(row: aiosqlite.Row) -> dict:
    try:
        record = json.loads(row["record"])
    except (ValueError, TypeError):
        record = {}
    return {
        "agent_name": row["agent_name"],
        "record": record,
        "constitution_sha256": row["constitution_sha256"],
        "model_id": row["model_id"],
        "recorded_at": row["recorded_at"],
    }


class AgentProvenanceStore(BaseStore):
    """Persistent store for per-agent Bean-0 provenance records."""

    SCHEMA = SCHEMA

    async def init(self) -> None:
        await super().init()
        if self._db is not None:
            self._db.row_factory = aiosqlite.Row

    async def set_provenance(self, agent_name: str, record: dict) -> dict:
        """Upsert the provenance record for *agent_name* and return it.

        INSERT OR REPLACE: Bean-0 keeps only the latest known provenance.
        """
        if self._db is None:
            raise RuntimeError("AgentProvenanceStore not initialised - call init() first")
        await self._db.execute(
            "INSERT OR REPLACE INTO agent_provenance "
            "(agent_name, record, constitution_sha256, model_id, recorded_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                agent_name,
                json.dumps(record),
                record.get("constitution_sha256"),
                record.get("model_id"),
                _recorded_at_epoch(record),
            ),
        )
        await self._db.commit()
        return record

    async def get_provenance(self, agent_name: str) -> Optional[dict]:
        """Return the stored record dict for *agent_name*, or ``None``."""
        if self._db is None:
            raise RuntimeError("AgentProvenanceStore not initialised - call init() first")
        row = await (
            await self._db.execute(
                "SELECT * FROM agent_provenance WHERE agent_name = ?",
                (agent_name,),
            )
        ).fetchone()
        return _row_to_entry(row)["record"] if row else None

    async def list_provenance(self) -> list[dict]:
        """Return all provenance entries ordered by agent_name.

        Each entry: {agent_name, record, constitution_sha256, model_id,
        recorded_at}.
        """
        if self._db is None:
            raise RuntimeError("AgentProvenanceStore not initialised - call init() first")
        cursor = await self._db.execute(
            "SELECT * FROM agent_provenance ORDER BY agent_name"
        )
        rows = await cursor.fetchall()
        return [_row_to_entry(r) for r in rows]
