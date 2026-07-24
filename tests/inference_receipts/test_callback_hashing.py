"""Bean-1 hashing + emission-guard tests for the LiteLLM callback.

Covers the pure hash helpers (canonical, order-independent prompt digest;
response-text digest) and that _emit_inference_receipt is hash-only,
fail-open, and skips the unknown-slug sentinel.  Mirrors the mock style of
tests/test_litellm_callback.py.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from tinyagentos.litellm_callback import (
    _UNKNOWN_SLUG,
    _output_hash,
    _prompt_hash,
    taos_callback,
)

# The real callback class only exists when litellm is installed; without it
# the module exports a no-op stub. The hash helpers are plain module
# functions and are always tested; the emission tests need the real class.
_HAS_REAL_CALLBACK = hasattr(taos_callback, "_emit_inference_receipt")


class TestHashHelpers:

    def test_prompt_hash_is_canonical_sha256(self):
        messages = [{"role": "user", "content": "hi"}]
        expected = hashlib.sha256(
            json.dumps(messages, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        assert _prompt_hash(messages) == expected
        assert len(_prompt_hash(messages)) == 64

    def test_prompt_hash_is_key_order_independent(self):
        a = [{"role": "user", "content": "hi"}]
        b = [{"content": "hi", "role": "user"}]
        assert _prompt_hash(a) == _prompt_hash(b)

    def test_prompt_hash_distinguishes_content(self):
        assert _prompt_hash([{"role": "user", "content": "a"}]) != _prompt_hash(
            [{"role": "user", "content": "b"}]
        )

    def test_prompt_hash_survives_non_json_value(self):
        # default=str keeps the digest total even for odd payloads.
        class Weird:
            def __str__(self):
                return "weird"

        assert len(_prompt_hash([{"role": "user", "content": Weird()}])) == 64

    def test_output_hash_handles_empty(self):
        assert _output_hash("") == hashlib.sha256(b"").hexdigest()
        assert _output_hash(None) == hashlib.sha256(b"").hexdigest()


@pytest.mark.skipif(
    not _HAS_REAL_CALLBACK,
    reason="litellm not installed — real TaosLiteLLMCallback unavailable",
)
@pytest.mark.asyncio
class TestEmitInferenceReceipt:

    async def test_skips_unknown_slug(self):
        posted = []
        orig = taos_callback._post

        async def spy(url, payload):
            posted.append((url, payload))

        taos_callback._post = spy
        try:
            await taos_callback._emit_inference_receipt(
                _UNKNOWN_SLUG, "m", {"messages": []}, None, None, None,
                None, None, "success",
            )
        finally:
            taos_callback._post = orig
        assert posted == []

    async def test_emits_hash_only_payload(self):
        posted = []

        async def spy(url, payload):
            posted.append((url, payload))

        orig = taos_callback._post
        taos_callback._post = spy
        try:
            await taos_callback._emit_inference_receipt(
                "scout-1", "hermes-3-llama-3.1-8b",
                {"messages": [{"role": "user", "content": "secret prompt"}]},
                None, None, None, 10, 20, "error",
            )
        finally:
            taos_callback._post = orig

        assert len(posted) == 1
        url, payload = posted[0]
        assert url.endswith("/api/agents/scout-1/inference-receipts")
        # No raw content anywhere in the payload — hashes + metadata only.
        blob = json.dumps(payload)
        assert "secret prompt" not in blob
        assert len(payload["prompt_hash"]) == 64
        assert len(payload["output_hash"]) == 64
        assert payload["model_id"] == "hermes-3-llama-3.1-8b"
        assert payload["status"] == "error"
        assert payload["prompt_tokens"] == 10

    async def test_fail_open_when_post_raises(self):
        async def boom(url, payload):
            raise RuntimeError("controller down")

        orig = taos_callback._post
        taos_callback._post = boom
        try:
            # Must not raise — receipt emission can never break inference.
            await taos_callback._emit_inference_receipt(
                "scout-1", "m", {"messages": []}, None, None, None,
                None, None, "success",
            )
        finally:
            taos_callback._post = orig

    async def test_thought_id_passed_through_when_present(self):
        posted = []

        async def spy(url, payload):
            posted.append((url, payload))

        orig = taos_callback._post
        taos_callback._post = spy
        try:
            await taos_callback._emit_inference_receipt(
                "scout-1", "m", {"messages": []}, None, None, None,
                None, None, "success", thought_id="scout-1:th-abc",
            )
        finally:
            taos_callback._post = orig
        assert posted[0][1]["thought_id"] == "scout-1:th-abc"

    async def test_thought_id_none_when_absent(self):
        posted = []

        async def spy(url, payload):
            posted.append((url, payload))

        orig = taos_callback._post
        taos_callback._post = spy
        try:
            await taos_callback._emit_inference_receipt(
                "scout-1", "m", {"messages": []}, None, None, None,
                None, None, "success",
            )
        finally:
            taos_callback._post = orig
        assert posted[0][1]["thought_id"] is None


@pytest.mark.skipif(
    not _HAS_REAL_CALLBACK,
    reason="litellm not installed — real TaosLiteLLMCallback unavailable",
)
@pytest.mark.asyncio
class TestTmrfsAutoCapture:
    """Track 3 auto-capture: gated on TAOS_TMRFS_AGENT + TAOS_TMRFS_URL."""

    def _success_kwargs(self, call_id: str = "call-1") -> dict:
        return {
            "litellm_call_id": call_id,
            "model": "hermes-3-llama-3.1-8b",
            "messages": [{"role": "user", "content": "hi there"}],
            "litellm_params": {"metadata": {"user_api_key_alias": "taos-scout-1"}},
        }

    async def test_gate_off_when_env_unset_no_capture_attempted(self, monkeypatch):
        monkeypatch.delenv("TAOS_TMRFS_AGENT", raising=False)
        monkeypatch.delenv("TAOS_TMRFS_URL", raising=False)

        called = []

        async def spy(url, payload):
            called.append((url, payload))
            return {"success": True, "name": "should-not-be-used"}

        orig = taos_callback._tmrfs_store
        taos_callback._tmrfs_store = spy
        try:
            result = await taos_callback._maybe_capture_thought(
                "scout-1", "m", self._success_kwargs(), "success"
            )
        finally:
            taos_callback._tmrfs_store = orig
        assert result is None
        assert called == []  # gate short-circuits before any HTTP attempt

    async def test_gate_on_captures_and_returns_thought_id(self, monkeypatch):
        monkeypatch.setenv("TAOS_TMRFS_AGENT", "scout-1")
        monkeypatch.setenv("TAOS_TMRFS_URL", "http://tmrfs.local:8080")

        posted = []

        async def spy(url, payload):
            posted.append((url, payload))
            return {"success": True, "name": "scout-1:call-1", "vector_shape": [99]}

        orig = taos_callback._tmrfs_store
        taos_callback._tmrfs_store = spy
        try:
            result = await taos_callback._maybe_capture_thought(
                "scout-1", "hermes-3-llama-3.1-8b", self._success_kwargs(), "success"
            )
        finally:
            taos_callback._tmrfs_store = orig

        assert result == "scout-1:call-1"
        assert len(posted) == 1
        url, payload = posted[0]
        assert url == "http://tmrfs.local:8080/tmrfs/store"
        # Compact tag, never raw prompt content (privacy-conservative).
        assert "hi there" not in json.dumps(payload)
        assert payload["text"] == "model=hermes-3-llama-3.1-8b status=success"

    async def test_tmrfs_failure_is_fail_open(self, monkeypatch):
        monkeypatch.setenv("TAOS_TMRFS_AGENT", "scout-1")
        monkeypatch.setenv("TAOS_TMRFS_URL", "http://tmrfs.local:8080")

        async def boom(url, payload):
            raise RuntimeError("tmrfs bridge unreachable")

        orig = taos_callback._tmrfs_store
        taos_callback._tmrfs_store = boom
        try:
            result = await taos_callback._maybe_capture_thought(
                "scout-1", "m", self._success_kwargs(), "success"
            )
        finally:
            taos_callback._tmrfs_store = orig
        assert result is None

    async def test_end_to_end_success_event_stamps_thought_id(self, monkeypatch):
        monkeypatch.setenv("TAOS_TMRFS_AGENT", "scout-1")
        monkeypatch.setenv("TAOS_TMRFS_URL", "http://tmrfs.local:8080")

        posted_receipts = []

        async def store_spy(url, payload):
            return {"success": True, "name": "scout-1:call-1"}

        async def post_spy(url, payload):
            if url.endswith("/inference-receipts"):
                posted_receipts.append(payload)

        orig_store = taos_callback._tmrfs_store
        orig_post = taos_callback._post
        taos_callback._tmrfs_store = store_spy
        taos_callback._post = post_spy
        try:
            await taos_callback.async_log_success_event(
                self._success_kwargs(), None, None, None,
            )
        finally:
            taos_callback._tmrfs_store = orig_store
            taos_callback._post = orig_post

        assert len(posted_receipts) == 1
        assert posted_receipts[0]["thought_id"] == "scout-1:call-1"

    async def test_end_to_end_success_event_env_unset_no_thought(self, monkeypatch):
        monkeypatch.delenv("TAOS_TMRFS_AGENT", raising=False)
        monkeypatch.delenv("TAOS_TMRFS_URL", raising=False)

        posted_receipts = []
        tmrfs_calls = []

        async def store_spy(url, payload):
            tmrfs_calls.append((url, payload))
            return {"success": True, "name": "should-not-happen"}

        async def post_spy(url, payload):
            if url.endswith("/inference-receipts"):
                posted_receipts.append(payload)

        orig_store = taos_callback._tmrfs_store
        orig_post = taos_callback._post
        taos_callback._tmrfs_store = store_spy
        taos_callback._post = post_spy
        try:
            await taos_callback.async_log_success_event(
                self._success_kwargs(), None, None, None,
            )
        finally:
            taos_callback._tmrfs_store = orig_store
            taos_callback._post = orig_post

        assert tmrfs_calls == []
        assert len(posted_receipts) == 1
        assert posted_receipts[0]["thought_id"] is None

    async def test_end_to_end_tmrfs_failure_still_emits_receipt(self, monkeypatch):
        monkeypatch.setenv("TAOS_TMRFS_AGENT", "scout-1")
        monkeypatch.setenv("TAOS_TMRFS_URL", "http://tmrfs.local:8080")

        posted_receipts = []

        async def store_boom(url, payload):
            raise RuntimeError("tmrfs bridge unreachable")

        async def post_spy(url, payload):
            if url.endswith("/inference-receipts"):
                posted_receipts.append(payload)

        orig_store = taos_callback._tmrfs_store
        orig_post = taos_callback._post
        taos_callback._tmrfs_store = store_boom
        taos_callback._post = post_spy
        try:
            # Must not raise — TMrFS failure never breaks inference logging.
            await taos_callback.async_log_success_event(
                self._success_kwargs(), None, None, None,
            )
        finally:
            taos_callback._tmrfs_store = orig_store
            taos_callback._post = orig_post

        assert len(posted_receipts) == 1
        assert posted_receipts[0]["thought_id"] is None
