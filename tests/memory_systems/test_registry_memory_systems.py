"""Track 1 (memory_systems on deploy) — agent_registry_store persistence.

Covers: memory_systems persists + round-trips on register()/get(), the
always-on ["taosmd"] default when omitted, and that a pre-existing row
written before the memory_systems column existed reads back the same
default (simulating the guarded ALTER's backward-compat path — see
agent_registry_store.py's _migration_v5_add_memory_systems and
base_store.py's guarded-ALTER pattern).

Run standalone (no full backend venv needed):

    pytest tests/memory_systems/ --confcutdir=tests/memory_systems
"""
from __future__ import annotations

import json

import pytest

from tinyagentos.agent_registry_store import AgentRegistryStore


@pytest.mark.asyncio
class TestMemorySystemsRegistry:

    async def _make_store(self, db_path):
        store = AgentRegistryStore(db_path)
        await store.init()
        return store

    async def test_register_persists_memory_systems(self, tmp_path):
        store = await self._make_store(tmp_path / "reg.db")
        try:
            rec = await store.register(
                framework="openclaw",
                display_name="Memory Agent",
                memory_systems=["taosmd", "tmrfs"],
            )
            assert rec["memory_systems"] == ["taosmd", "tmrfs"]
        finally:
            await store.close()

    async def test_memory_systems_round_trips_through_get(self, tmp_path):
        store = await self._make_store(tmp_path / "reg.db")
        try:
            rec = await store.register(
                framework="openclaw",
                display_name="Round Trip Agent",
                memory_systems=["taosmd", "pk-trust"],
            )
            fetched = await store.get(rec["canonical_id"])
            assert fetched is not None
            assert fetched["memory_systems"] == ["taosmd", "pk-trust"]
        finally:
            await store.close()

    async def test_memory_systems_round_trips_through_list_all(self, tmp_path):
        store = await self._make_store(tmp_path / "reg.db")
        try:
            rec = await store.register(
                framework="openclaw",
                display_name="List Agent",
                memory_systems=["taosmd", "tmrfs", "pk-trust"],
            )
            records = await store.list_all()
            match = next(r for r in records if r["canonical_id"] == rec["canonical_id"])
            assert match["memory_systems"] == ["taosmd", "tmrfs", "pk-trust"]
        finally:
            await store.close()

    async def test_default_is_taosmd_when_unset(self, tmp_path):
        store = await self._make_store(tmp_path / "reg.db")
        try:
            rec = await store.register(framework="hermes", display_name="Default Agent")
            assert rec["memory_systems"] == ["taosmd"]
        finally:
            await store.close()

    async def test_default_is_taosmd_when_empty_list_passed(self, tmp_path):
        store = await self._make_store(tmp_path / "reg.db")
        try:
            rec = await store.register(
                framework="hermes", display_name="Empty List Agent", memory_systems=[],
            )
            assert rec["memory_systems"] == ["taosmd"]
        finally:
            await store.close()

    async def test_preexisting_row_without_column_reads_back_default(self, tmp_path):
        """Simulate a DB row written before the memory_systems column existed.

        Insert directly with only the columns available pre-migration (bypassing
        register(), which always supplies memory_systems), matching what an
        existing DB would contain the moment the guarded ALTER TABLE runs (the
        SQL column DEFAULT then applies on read).
        """
        db_path = tmp_path / "reg.db"
        store = await self._make_store(db_path)
        try:
            now = "2026-07-24T00:00:00+00:00"
            await store._db.execute(
                """INSERT INTO agent_registry
                   (canonical_id, display_name, framework, user_id, origin,
                    handle, role, capabilities, created_ts)
                   VALUES (?, '', 'legacy', '', 'taos-deployed', '', NULL, '[]', ?)""",
                ("legacy-agent-pre-column", now),
            )
            await store._db.commit()

            rec = await store.get("legacy-agent-pre-column")
            assert rec is not None
            # The column's SQL DEFAULT ('["taosmd"]') applies to the INSERT
            # above (which omits memory_systems entirely), so the always-on
            # default is what comes back — exactly the backward-compat
            # behaviour existing (pre-column) agents get once the guarded
            # ALTER TABLE has run.
            assert rec["memory_systems"] == ["taosmd"]
        finally:
            await store.close()

    async def test_memory_systems_column_added_by_guarded_alter(self, tmp_path):
        """The column must exist on the table after init(), added idempotently."""
        db_path = tmp_path / "reg.db"
        store = await self._make_store(db_path)
        try:
            cols = {
                row[1]
                for row in await (
                    await store._db.execute("PRAGMA table_info(agent_registry)")
                ).fetchall()
            }
            assert "memory_systems" in cols
        finally:
            await store.close()

        # Re-opening an existing DB must not fail (idempotent guarded ALTER).
        store2 = await self._make_store(db_path)
        try:
            rec = await store2.register(framework="openclaw", display_name="Reopen Agent")
            assert rec["memory_systems"] == ["taosmd"]
        finally:
            await store2.close()

    async def test_malformed_memory_systems_json_falls_back_to_default(self, tmp_path):
        """A corrupted memory_systems cell must not crash the reader."""
        store = await self._make_store(tmp_path / "reg.db")
        try:
            rec = await store.register(framework="openclaw", display_name="Corrupt Agent")
            await store._db.execute(
                "UPDATE agent_registry SET memory_systems = 'not-json' WHERE canonical_id = ?",
                (rec["canonical_id"],),
            )
            await store._db.commit()
            fetched = await store.get(rec["canonical_id"])
            assert fetched["memory_systems"] == ["taosmd"]
        finally:
            await store.close()
