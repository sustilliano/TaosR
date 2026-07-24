"""Tests for the Bean-2 keystore (tinyagentos/bean_keystore.py).

Covers key persistence/stability, the canonical byte encoding, and the
sign/verify round-trip including the tri-state verify_receipt contract.
"""
from __future__ import annotations

import json

import pytest

from tinyagentos import bean_keystore

RECEIPT = {
    "inference_id": "inf-abc12345",
    "trace_id": "call-1",
    "model_id": "hermes-3-llama-3.1-8b",
    "prompt_hash": "a" * 64,
    "output_hash": "b" * 64,
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "started_at": "2026-07-24T00:00:00+00:00",
    "completed_at": "2026-07-24T00:00:01+00:00",
    "status": "success",
}


class TestKeyPersistence:
    def test_key_generated_once_and_stable_across_reload(self, tmp_path):
        key1 = bean_keystore.get_or_create("scout-1", tmp_path)
        raw1 = key1.private_bytes_raw()

        key2 = bean_keystore.get_or_create("scout-1", tmp_path)
        raw2 = key2.private_bytes_raw()

        assert raw1 == raw2

    def test_key_file_written_with_0600_perms(self, tmp_path):
        bean_keystore.get_or_create("scout-1", tmp_path)
        path = tmp_path / "agent-memory" / "scout-1" / "bean-key" / "private.ed25519"
        assert path.exists()
        assert (path.stat().st_mode & 0o777) == 0o600
        # Raw 32-byte private key, not PEM/JSON.
        assert len(path.read_bytes()) == 32

    def test_different_agents_get_different_keys(self, tmp_path):
        pub1 = bean_keystore.public_key_hex("scout-1", tmp_path)
        pub2 = bean_keystore.public_key_hex("scout-2", tmp_path)
        assert pub1 != pub2

    def test_public_key_hex_stable(self, tmp_path):
        pub1 = bean_keystore.public_key_hex("scout-1", tmp_path)
        pub2 = bean_keystore.public_key_hex("scout-1", tmp_path)
        assert pub1 == pub2
        assert len(pub1) == 64  # 32 raw bytes, hex-encoded
        bytes.fromhex(pub1)  # does not raise


class TestCanonicalBytes:
    def test_key_order_independent(self):
        reordered = dict(reversed(list(RECEIPT.items())))
        assert (
            bean_keystore.canonical_receipt_bytes(RECEIPT)
            == bean_keystore.canonical_receipt_bytes(reordered)
        )

    def test_excludes_signature_field(self):
        with_sig = dict(RECEIPT, signature="deadbeef")
        assert (
            bean_keystore.canonical_receipt_bytes(RECEIPT)
            == bean_keystore.canonical_receipt_bytes(with_sig)
        )

    def test_is_compact_sorted_json(self):
        raw = bean_keystore.canonical_receipt_bytes(RECEIPT)
        assert b" " not in raw  # separators=(",", ":") -> no whitespace
        decoded = json.loads(raw.decode("utf-8"))
        assert list(decoded.keys()) == sorted(decoded.keys())
        assert "signature" not in decoded

    def test_missing_fields_become_none(self):
        sparse = {"inference_id": "inf-1"}
        raw = bean_keystore.canonical_receipt_bytes(sparse)
        decoded = json.loads(raw.decode("utf-8"))
        assert decoded["inference_id"] == "inf-1"
        assert decoded["model_id"] is None


class TestSignVerify:
    def test_sign_then_verify_is_valid(self, tmp_path):
        sig = bean_keystore.sign_receipt("scout-1", tmp_path, RECEIPT)
        pub = bean_keystore.public_key_hex("scout-1", tmp_path)
        signed = dict(RECEIPT, signature=sig)
        assert bean_keystore.verify_receipt(signed, pub) == "valid"

    def test_signature_is_hex(self, tmp_path):
        sig = bean_keystore.sign_receipt("scout-1", tmp_path, RECEIPT)
        bytes.fromhex(sig)  # does not raise
        assert len(sig) == 128  # 64-byte Ed25519 signature, hex-encoded

    def test_no_signature_is_unsigned(self, tmp_path):
        pub = bean_keystore.public_key_hex("scout-1", tmp_path)
        assert bean_keystore.verify_receipt(RECEIPT, pub) == "unsigned"
        assert bean_keystore.verify_receipt(dict(RECEIPT, signature=None), pub) == "unsigned"
        assert bean_keystore.verify_receipt(dict(RECEIPT, signature=""), pub) == "unsigned"

    @pytest.mark.parametrize("field", [
        "inference_id", "trace_id", "model_id", "prompt_hash", "output_hash",
        "prompt_tokens", "completion_tokens", "started_at", "completed_at", "status",
    ])
    def test_tampering_any_signed_field_invalidates(self, tmp_path, field):
        sig = bean_keystore.sign_receipt("scout-1", tmp_path, RECEIPT)
        pub = bean_keystore.public_key_hex("scout-1", tmp_path)
        tampered = dict(RECEIPT, signature=sig)
        if isinstance(tampered[field], int):
            tampered[field] = (tampered[field] or 0) + 1
        else:
            tampered[field] = str(tampered[field]) + "-tampered"
        assert bean_keystore.verify_receipt(tampered, pub) == "invalid"

    def test_wrong_public_key_invalidates(self, tmp_path):
        sig = bean_keystore.sign_receipt("scout-1", tmp_path, RECEIPT)
        wrong_pub = bean_keystore.public_key_hex("scout-2", tmp_path)
        signed = dict(RECEIPT, signature=sig)
        assert bean_keystore.verify_receipt(signed, wrong_pub) == "invalid"

    def test_malformed_signature_invalidates_not_raises(self, tmp_path):
        pub = bean_keystore.public_key_hex("scout-1", tmp_path)
        signed = dict(RECEIPT, signature="not-hex-at-all")
        assert bean_keystore.verify_receipt(signed, pub) == "invalid"

    def test_verify_needs_no_private_key_or_data_dir(self, tmp_path):
        # verify_receipt takes only (receipt, public_key_hex) - no data_dir,
        # no slug, no filesystem access at all.
        sig = bean_keystore.sign_receipt("scout-1", tmp_path, RECEIPT)
        pub = bean_keystore.public_key_hex("scout-1", tmp_path)
        signed = dict(RECEIPT, signature=sig)
        import inspect
        params = list(inspect.signature(bean_keystore.verify_receipt).parameters)
        assert params == ["receipt", "public_key_hex"]
        assert bean_keystore.verify_receipt(signed, pub) == "valid"
