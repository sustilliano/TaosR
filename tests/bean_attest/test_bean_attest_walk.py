"""Tests for the Bean-5 attestation walk (tinyagentos/bean_attest.py).

Pure-function tests: no store, no FastAPI, no filesystem beyond
bean_keystore's per-agent key file (needed to produce real Ed25519
signatures to verify against).
"""
from __future__ import annotations

import pytest

from tinyagentos import bean_keystore
from tinyagentos.bean_attest import walk_attestation

MODEL_ID = "hermes-3-llama-3.1-8b"

PROVENANCE_RECORD = {
    "substrate": "silicon",
    "framework": "hermes",
    "framework_ref": "v0.2.1",
    "installer_sha256": "a" * 64,
    "constitution_sha256": "b" * 64,
    "model_id": MODEL_ID,
    "model_file_sha256": "c" * 64,
    "corpus_refs": ["https://huggingface.co/datasets/teknium/OpenHermes-2.5"],
    "recorded_at": "2026-07-24T00:00:00Z",
}

MODEL_MANIFEST = {
    "id": MODEL_ID,
    "variants": [
        {"id": "q4_k_m", "sha256": "c" * 64},
        {"id": "q8_0", "sha256": "d" * 64},
    ],
}


def _receipt(**overrides) -> dict:
    base = {
        "inference_id": "inf-abc12345",
        "trace_id": "call-1",
        "model_id": MODEL_ID,
        "prompt_hash": "e" * 64,
        "output_hash": "f" * 64,
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "started_at": "2026-07-24T00:00:00+00:00",
        "completed_at": "2026-07-24T00:00:01+00:00",
        "status": "success",
    }
    base.update(overrides)
    return base


def _link_by_name(result: dict, name: str) -> dict:
    for link in result["links"]:
        if link["name"] == name:
            return link
    raise AssertionError(f"no link named {name!r} in {result['links']!r}")


def _signed(agent, tmp_path, receipt: dict) -> dict:
    sig = bean_keystore.sign_receipt(agent, tmp_path, receipt)
    return dict(receipt, signature=sig)


class TestFullySignedChain:
    def test_all_links_pass_overall_verified(self, tmp_path):
        agent = "scout-1"
        receipt = _signed(agent, tmp_path, _receipt())
        pub = bean_keystore.public_key_hex(agent, tmp_path)

        result = walk_attestation(agent, receipt, PROVENANCE_RECORD, pub, MODEL_MANIFEST)

        assert result["agent"] == agent
        assert result["inference_id"] == "inf-abc12345"
        assert [link["name"] for link in result["links"]] == [
            "signature", "provenance_present", "model_binding",
            "constitution", "corpus",
        ]
        for link in result["links"]:
            assert link["status"] == "pass", link
        assert result["overall"] == "verified"


class TestTamperedReceipt:
    def test_tampered_receipt_signature_fails_overall_broken(self, tmp_path):
        agent = "scout-1"
        receipt = _signed(agent, tmp_path, _receipt())
        receipt["output_hash"] = "0" * 64  # tamper after signing
        pub = bean_keystore.public_key_hex(agent, tmp_path)

        result = walk_attestation(agent, receipt, PROVENANCE_RECORD, pub, MODEL_MANIFEST)

        assert _link_by_name(result, "signature")["status"] == "fail"
        assert result["overall"] == "broken"


class TestMissingProvenance:
    def test_missing_provenance_fails_that_link_overall_broken(self, tmp_path):
        agent = "scout-1"
        receipt = _signed(agent, tmp_path, _receipt())
        pub = bean_keystore.public_key_hex(agent, tmp_path)

        result = walk_attestation(agent, receipt, None, pub, MODEL_MANIFEST)

        assert _link_by_name(result, "signature")["status"] == "pass"
        assert _link_by_name(result, "provenance_present")["status"] == "fail"
        assert result["overall"] == "broken"


class TestModelIdMismatch:
    def test_model_id_mismatch_fails_model_binding(self, tmp_path):
        agent = "scout-1"
        receipt = _signed(agent, tmp_path, _receipt(model_id="some-other-model"))
        pub = bean_keystore.public_key_hex(agent, tmp_path)

        result = walk_attestation(agent, receipt, PROVENANCE_RECORD, pub, MODEL_MANIFEST)

        link = _link_by_name(result, "model_binding")
        assert link["status"] == "fail"
        assert "some-other-model" in link["detail"]
        assert result["overall"] == "broken"

    def test_manifest_sha256_mismatch_also_fails_model_binding(self, tmp_path):
        agent = "scout-1"
        receipt = _signed(agent, tmp_path, _receipt())
        pub = bean_keystore.public_key_hex(agent, tmp_path)
        record = dict(PROVENANCE_RECORD, model_file_sha256="9" * 64)  # not in manifest

        result = walk_attestation(agent, receipt, record, pub, MODEL_MANIFEST)

        assert _link_by_name(result, "model_binding")["status"] == "fail"
        assert result["overall"] == "broken"

    def test_no_manifest_supplied_is_unknown_not_fail(self, tmp_path):
        agent = "scout-1"
        receipt = _signed(agent, tmp_path, _receipt())
        pub = bean_keystore.public_key_hex(agent, tmp_path)

        result = walk_attestation(agent, receipt, PROVENANCE_RECORD, pub, model_manifest=None)

        assert _link_by_name(result, "model_binding")["status"] == "unknown"
        assert result["overall"] == "partial"


class TestUnsignedReceipt:
    def test_unsigned_receipt_signature_unknown_overall_partial(self, tmp_path):
        agent = "scout-1"
        receipt = _receipt()  # no signature attached
        pub = bean_keystore.public_key_hex(agent, tmp_path)

        result = walk_attestation(agent, receipt, PROVENANCE_RECORD, pub, MODEL_MANIFEST)

        assert _link_by_name(result, "signature")["status"] == "unknown"
        # every other link passes -> worst status is "unknown" -> partial
        others = [l for l in result["links"] if l["name"] != "signature"]
        assert all(l["status"] == "pass" for l in others)
        assert result["overall"] == "partial"

    def test_none_and_empty_string_signature_both_unknown(self, tmp_path):
        agent = "scout-1"
        pub = bean_keystore.public_key_hex(agent, tmp_path)
        for sig in (None, ""):
            receipt = _receipt(signature=sig)
            result = walk_attestation(agent, receipt, PROVENANCE_RECORD, pub, MODEL_MANIFEST)
            assert _link_by_name(result, "signature")["status"] == "unknown"


class TestCorpusAndConstitution:
    def test_empty_corpus_refs_is_unknown(self, tmp_path):
        agent = "scout-1"
        receipt = _signed(agent, tmp_path, _receipt())
        pub = bean_keystore.public_key_hex(agent, tmp_path)
        record = dict(PROVENANCE_RECORD, corpus_refs=[])

        result = walk_attestation(agent, receipt, record, pub, MODEL_MANIFEST)

        assert _link_by_name(result, "corpus")["status"] == "unknown"
        assert result["overall"] == "partial"

    def test_non_url_corpus_refs_is_unknown(self, tmp_path):
        agent = "scout-1"
        receipt = _signed(agent, tmp_path, _receipt())
        pub = bean_keystore.public_key_hex(agent, tmp_path)
        record = dict(PROVENANCE_RECORD, corpus_refs=["not-a-url"])

        result = walk_attestation(agent, receipt, record, pub, MODEL_MANIFEST)

        assert _link_by_name(result, "corpus")["status"] == "unknown"

    def test_missing_constitution_sha256_is_unknown(self, tmp_path):
        agent = "scout-1"
        receipt = _signed(agent, tmp_path, _receipt())
        pub = bean_keystore.public_key_hex(agent, tmp_path)
        record = dict(PROVENANCE_RECORD, constitution_sha256=None)

        result = walk_attestation(agent, receipt, record, pub, MODEL_MANIFEST)

        assert _link_by_name(result, "constitution")["status"] == "unknown"

    def test_non_hex_constitution_sha256_is_unknown(self, tmp_path):
        agent = "scout-1"
        receipt = _signed(agent, tmp_path, _receipt())
        pub = bean_keystore.public_key_hex(agent, tmp_path)
        record = dict(PROVENANCE_RECORD, constitution_sha256="not-hex")

        result = walk_attestation(agent, receipt, record, pub, MODEL_MANIFEST)

        assert _link_by_name(result, "constitution")["status"] == "unknown"


class TestWrongPublicKey:
    def test_wrong_pubkey_makes_signature_invalid(self, tmp_path):
        agent = "scout-1"
        receipt = _signed(agent, tmp_path, _receipt())
        wrong_pub = bean_keystore.public_key_hex("someone-else", tmp_path)

        result = walk_attestation(agent, receipt, PROVENANCE_RECORD, wrong_pub, MODEL_MANIFEST)

        assert _link_by_name(result, "signature")["status"] == "fail"
        assert result["overall"] == "broken"


class TestNoRequiredDependencies:
    def test_walk_attestation_signature_has_no_extra_required_params(self):
        import inspect
        params = list(inspect.signature(walk_attestation).parameters)
        assert params == [
            "agent", "receipt", "provenance_record", "public_key_hex", "model_manifest",
        ]
