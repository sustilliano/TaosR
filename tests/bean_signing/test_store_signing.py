"""Bean-2 regression tests: InferenceReceiptStore.record(signature=...).

Proves the optional ``signature`` kwarg added to record() persists a
signature when given, and that omitting it keeps Bean-1's NULL behaviour
exactly as before (see tests/inference_receipts/test_inference_receipt_store.py
for the full Bean-1 regression suite, re-run separately).
"""
from __future__ import annotations

import pytest
import pytest_asyncio

aiosqlite = pytest.importorskip("aiosqlite")

from tinyagentos import bean_keystore
from tinyagentos.inference_receipt_store import InferenceReceiptStore

H1 = "1" * 64
H2 = "2" * 64


@pytest_asyncio.fixture
async def store(tmp_path):
    s = InferenceReceiptStore(tmp_path / "agent-memory" / "scout-1" / "receipts.sqlbook")
    await s.init()
    yield s
    await s.close()


@pytest.mark.asyncio
class TestStoreSigning:
    async def test_record_without_signature_stays_null(self, store):
        inf_id = await store.record(model_id="m", prompt_hash=H1, output_hash=H2)
        (row,) = await store.list()
        assert row["inference_id"] == inf_id
        assert row["signature"] is None

    async def test_record_with_signature_persists_and_returns_it(self, tmp_path, store):
        receipt = dict(
            inference_id="inf-placeholder",  # not yet known; signing precedes id assignment here
            trace_id=None,
            model_id="m",
            prompt_hash=H1,
            output_hash=H2,
            prompt_tokens=None,
            completion_tokens=None,
            started_at=None,
            completed_at=None,
            status="success",
        )
        sig = bean_keystore.sign_receipt("scout-1", tmp_path, receipt)

        inf_id = await store.record(
            model_id="m", prompt_hash=H1, output_hash=H2, signature=sig,
        )
        (row,) = await store.list()
        assert row["inference_id"] == inf_id
        assert row["signature"] == sig
        assert len(row["signature"]) == 128

    async def test_end_to_end_sign_after_record_then_verify(self, tmp_path, store):
        # Realistic flow: record first (id is store-generated), sign the
        # resulting receipt dict, then verify with the public key alone.
        inf_id = await store.record(
            model_id="hermes-3-llama-3.1-8b",
            prompt_hash=H1, output_hash=H2,
            trace_id="call-1", prompt_tokens=5, completion_tokens=7,
            started_at="2026-07-24T00:00:00+00:00",
            completed_at="2026-07-24T00:00:01+00:00",
        )
        (row,) = await store.list()
        assert row["signature"] is None  # not signed at record time in this flow

        sig = bean_keystore.sign_receipt("scout-1", tmp_path, row)
        signed_row = dict(row, signature=sig)
        pub = bean_keystore.public_key_hex("scout-1", tmp_path)
        assert bean_keystore.verify_receipt(signed_row, pub) == "valid"

    async def test_signed_receipt_round_trips_through_signature_kwarg(self, tmp_path, store):
        # Sign, then pass the signature straight into record() (the shape
        # the integrator's wiring will use at the POST route).
        draft = dict(
            inference_id="inf-not-yet-known",
            trace_id="call-9", model_id="m", prompt_hash=H1, output_hash=H2,
            prompt_tokens=1, completion_tokens=2,
            started_at="2026-07-24T00:00:00+00:00",
            completed_at="2026-07-24T00:00:01+00:00",
            status="success",
        )
        sig = bean_keystore.sign_receipt("scout-1", tmp_path, draft)
        inf_id = await store.record(
            model_id="m", prompt_hash=H1, output_hash=H2,
            trace_id="call-9", prompt_tokens=1, completion_tokens=2,
            started_at="2026-07-24T00:00:00+00:00",
            completed_at="2026-07-24T00:00:01+00:00",
            signature=sig,
        )
        (row,) = await store.list()
        assert row["inference_id"] == inf_id
        assert row["signature"] == sig
