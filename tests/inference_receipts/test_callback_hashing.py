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
