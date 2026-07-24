"""Store tests for the Bean-1 inference-receipt ledger.

Exercises InferenceReceiptStore directly against a tmp_path sqlbook: the
one-row book identity, append-only writes, newest-first listing with a
backward cursor, count, and the hash-only record contract.  Modeled on the
store-test style in tests/test_agent_registry.py.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

aiosqlite = pytest.importorskip("aiosqlite")

from tinyagentos.inference_receipt_store import (
    BOOK_PROFILE,
    InferenceReceiptStore,
)

H1 = "1" * 64
H2 = "2" * 64


@pytest_asyncio.fixture
async def store(tmp_path):
    s = InferenceReceiptStore(tmp_path / "agent-memory" / "scout-1" / "receipts.sqlbook")
    await s.init()
    yield s
    await s.close()


async def _record(s, **over):
    kw = dict(model_id="hermes-3-llama-3.1-8b", prompt_hash=H1, output_hash=H2)
    kw.update(over)
    return await s.record(**kw)


@pytest.mark.asyncio
class TestInferenceReceiptStore:

    async def test_book_row_seeded_on_init(self, store):
        book = await store.book()
        assert book is not None
        assert book["profile"] == BOOK_PROFILE
        assert book["version"] and book["created_at"]

    async def test_record_roundtrip(self, store):
        inf_id = await _record(
            store, trace_id="call-abc",
            prompt_tokens=10, completion_tokens=20,
            started_at="2026-07-24T00:00:00+00:00",
            completed_at="2026-07-24T00:00:01+00:00",
        )
        assert inf_id.startswith("inf-")
        rows = await store.list()
        assert len(rows) == 1
        r = rows[0]
        assert r["inference_id"] == inf_id
        assert r["model_id"] == "hermes-3-llama-3.1-8b"
        assert r["prompt_hash"] == H1 and r["output_hash"] == H2
        assert r["prompt_tokens"] == 10 and r["completion_tokens"] == 20
        assert r["trace_id"] == "call-abc"
        assert r["status"] == "success"
        # Bean-1: signature stays NULL until Bean-2 signing.
        assert r["signature"] is None

    async def test_append_only_no_mutation_api(self, store):
        # The store must not expose update/delete — receipts are immutable.
        assert not hasattr(store, "update")
        assert not hasattr(store, "delete")

    async def test_list_is_newest_first(self, store):
        ids = [await _record(store, status="success") for _ in range(3)]
        rows = await store.list()
        assert [r["inference_id"] for r in rows] == list(reversed(ids))

    async def test_list_limit_and_before_cursor(self, store):
        ids = [await _record(store) for _ in range(5)]  # oldest..newest
        newest_first = list(reversed(ids))

        page1 = await store.list(limit=2)
        assert [r["inference_id"] for r in page1] == newest_first[:2]

        page2 = await store.list(limit=2, before=page1[-1]["inference_id"])
        assert [r["inference_id"] for r in page2] == newest_first[2:4]

    async def test_unknown_before_cursor_is_empty_page(self, store):
        await _record(store)
        assert await store.list(before="inf-nope9999") == []

    async def test_count(self, store):
        assert await store.count() == 0
        for _ in range(4):
            await _record(store)
        assert await store.count() == 4

    async def test_error_status_persisted(self, store):
        await _record(store, status="error", output_hash="0" * 64)
        (r,) = await store.list()
        assert r["status"] == "error"

    async def test_missing_hashes_rejected(self, store):
        with pytest.raises(ValueError):
            await store.record(model_id="m", prompt_hash="", output_hash=H2)
        with pytest.raises(ValueError):
            await store.record(model_id="", prompt_hash=H1, output_hash=H2)

    async def test_persistence_across_reopen(self, tmp_path):
        path = tmp_path / "agent-memory" / "scout-2" / "receipts.sqlbook"
        s1 = InferenceReceiptStore(path)
        await s1.init()
        await _record(s1)
        await s1.close()

        s2 = InferenceReceiptStore(path)
        await s2.init()
        try:
            assert await s2.count() == 1          # data survived
            book = await s2.book()
            assert book["profile"] == BOOK_PROFILE  # book not double-seeded
            async with s2._db.execute("SELECT COUNT(*) FROM book") as cur:
                (n,) = await cur.fetchone()
            assert n == 1
        finally:
            await s2.close()
