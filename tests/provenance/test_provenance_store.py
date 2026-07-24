"""Tests for the Bean-0 agent provenance store (silicon-bean-integration).

Covers: set/get round-trip, unknown agent -> None, overwrite (latest wins),
list_provenance, denormalised columns, recorded_at parsing, and persistence
across store reopen.
"""
from __future__ import annotations

import time

import pytest

from tinyagentos.agent_provenance_store import AgentProvenanceStore

RECORD = {
    "substrate": "silicon",
    "framework": "hermes",
    "framework_ref": "v0.2.1",
    "installer_sha256": "a" * 64,
    "constitution_sha256": "b" * 64,
    "model_id": "hermes-3-llama-3.1-8b",
    "model_file_sha256": "c" * 64,
    "corpus_refs": ["https://huggingface.co/datasets/teknium/OpenHermes-2.5"],
    "recorded_at": "2026-07-24T00:00:00Z",
}


@pytest.mark.asyncio
class TestAgentProvenanceStore:

    async def _make_store(self, db_path):
        store = AgentProvenanceStore(db_path)
        await store.init()
        return store

    async def test_set_get_roundtrip(self, tmp_path):
        store = await self._make_store(tmp_path / "prov.db")
        try:
            await store.set_provenance("scout-1", RECORD)
            rec = await store.get_provenance("scout-1")
            assert rec == RECORD
        finally:
            await store.close()

    async def test_get_unknown_agent_returns_none(self, tmp_path):
        store = await self._make_store(tmp_path / "prov.db")
        try:
            assert await store.get_provenance("never-registered") is None
        finally:
            await store.close()

    async def test_set_again_overwrites(self, tmp_path):
        store = await self._make_store(tmp_path / "prov.db")
        try:
            await store.set_provenance("scout-1", RECORD)
            updated = dict(RECORD, framework_ref="v0.3.0", model_id="hermes-4")
            await store.set_provenance("scout-1", updated)
            rec = await store.get_provenance("scout-1")
            assert rec == updated
            assert rec["framework_ref"] == "v0.3.0"
            # Still exactly one row for the agent.
            entries = await store.list_provenance()
            assert len(entries) == 1
        finally:
            await store.close()

    async def test_list_provenance(self, tmp_path):
        store = await self._make_store(tmp_path / "prov.db")
        try:
            assert await store.list_provenance() == []
            await store.set_provenance("beta", dict(RECORD, model_id="m-beta"))
            await store.set_provenance("alpha", dict(RECORD, model_id="m-alpha"))
            entries = await store.list_provenance()
            assert [e["agent_name"] for e in entries] == ["alpha", "beta"]
            assert entries[0]["record"]["model_id"] == "m-alpha"
            assert entries[1]["record"]["model_id"] == "m-beta"
        finally:
            await store.close()

    async def test_denormalised_columns(self, tmp_path):
        store = await self._make_store(tmp_path / "prov.db")
        try:
            await store.set_provenance("scout-1", RECORD)
            entries = await store.list_provenance()
            entry = entries[0]
            assert entry["constitution_sha256"] == RECORD["constitution_sha256"]
            assert entry["model_id"] == RECORD["model_id"]
            # 2026-07-24T00:00:00Z as unix epoch.
            assert entry["recorded_at"] == 1784851200
        finally:
            await store.close()

    async def test_recorded_at_defaults_to_now_when_missing(self, tmp_path):
        store = await self._make_store(tmp_path / "prov.db")
        try:
            record = {k: v for k, v in RECORD.items() if k != "recorded_at"}
            before = int(time.time())
            await store.set_provenance("scout-1", record)
            after = int(time.time())
            entry = (await store.list_provenance())[0]
            assert before <= entry["recorded_at"] <= after
            # The stored record itself is untouched (no recorded_at injected).
            assert "recorded_at" not in (await store.get_provenance("scout-1"))
        finally:
            await store.close()

    async def test_recorded_at_unparseable_falls_back_to_now(self, tmp_path):
        store = await self._make_store(tmp_path / "prov.db")
        try:
            before = int(time.time())
            await store.set_provenance("scout-1", dict(RECORD, recorded_at="not-a-date"))
            after = int(time.time())
            entry = (await store.list_provenance())[0]
            assert before <= entry["recorded_at"] <= after
        finally:
            await store.close()

    async def test_persists_across_reopen(self, tmp_path):
        db_path = tmp_path / "prov.db"
        store = await self._make_store(db_path)
        try:
            await store.set_provenance("scout-1", RECORD)
        finally:
            await store.close()

        store = await self._make_store(db_path)
        try:
            assert await store.get_provenance("scout-1") == RECORD
        finally:
            await store.close()

    async def test_uninitialised_store_raises(self, tmp_path):
        store = AgentProvenanceStore(tmp_path / "prov.db")
        with pytest.raises(RuntimeError):
            await store.set_provenance("scout-1", RECORD)
        with pytest.raises(RuntimeError):
            await store.get_provenance("scout-1")
        with pytest.raises(RuntimeError):
            await store.list_provenance()
