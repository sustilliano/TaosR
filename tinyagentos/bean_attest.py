from __future__ import annotations

"""Bean-5 attestation walk (offline verifier).

Given an agent, one of its inference receipts, its Ed25519 public key, its
Bean-0 provenance record, and (optionally) a model-card manifest, walk the
whole trust chain and report each link's status
(``docs/design/bean-2-5-plan.md``, "Bean-5 — attestation walk"):

    inference receipt --(Bean-2 signature check)--> provenance record (Bean-0)
        --> model_id + model_file_sha256 matches a model-card manifest
        --> constitution_sha256 present --> published corpus ref(s)

``walk_attestation`` is a pure function: it only ever reads the values
handed to it. It never opens a store, never touches a private key, never
makes a network call — that is the "offline" promise. Callers (the
``routes/attestation.py`` API and ``bean_attest_cli.py``) are responsible
for loading the receipt/provenance/manifest and handing them in; this
module only needs ``bean_keystore.verify_receipt`` (stdlib + the
``cryptography`` package bean_keystore already depends on — nothing else).
"""

import re
from typing import Optional

from tinyagentos import bean_keystore

_HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")

# Worst-status wins. Higher rank = worse.
_STATUS_RANK = {"pass": 0, "unknown": 1, "fail": 2}


def _link(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


def _check_signature(receipt: dict, public_key_hex: str) -> dict:
    """Bean-2 signature check: valid=pass, invalid=fail, unsigned=unknown."""
    verdict = bean_keystore.verify_receipt(receipt, public_key_hex)
    if verdict == "valid":
        return _link(
            "signature", "pass",
            "receipt signature verifies against the agent's Ed25519 public key",
        )
    if verdict == "invalid":
        return _link(
            "signature", "fail",
            "receipt signature does NOT verify against the agent's Ed25519 "
            "public key — the receipt may be forged or tampered with",
        )
    return _link(
        "signature", "unknown",
        "receipt carries no signature (pre-Bean-2 or signing failed at "
        "write time) — authenticity cannot be confirmed",
    )


def _check_provenance_present(provenance_record: Optional[dict]) -> dict:
    """A Bean-0 provenance record must exist, or the chain stops here."""
    if provenance_record:
        return _link(
            "provenance_present", "pass",
            "a Bean-0 provenance record is registered for this agent",
        )
    return _link(
        "provenance_present", "fail",
        "no Bean-0 provenance record is registered for this agent — the "
        "chain cannot be walked any further",
    )


def _check_model_binding(
    receipt: dict,
    provenance_record: Optional[dict],
    model_manifest: Optional[dict],
) -> dict:
    """receipt.model_id vs provenance.model_id, then provenance's
    model_file_sha256 vs a variant sha256 in the model-card manifest."""
    if not provenance_record:
        return _link(
            "model_binding", "unknown",
            "no provenance record to bind the receipt's model_id against",
        )

    receipt_model_id = receipt.get("model_id")
    prov_model_id = provenance_record.get("model_id")
    if receipt_model_id != prov_model_id:
        return _link(
            "model_binding", "fail",
            f"receipt model_id {receipt_model_id!r} does not match "
            f"provenance model_id {prov_model_id!r}",
        )

    if model_manifest is None:
        return _link(
            "model_binding", "unknown",
            f"receipt model_id matches provenance ({prov_model_id!r}); no "
            "model-card manifest supplied to verify model_file_sha256",
        )

    model_file_sha256 = provenance_record.get("model_file_sha256")
    if not model_file_sha256:
        return _link(
            "model_binding", "unknown",
            "receipt model_id matches provenance, but the provenance "
            "record has no model_file_sha256 to check against the model card",
        )

    variants = model_manifest.get("variants") or []
    variant_shas = {v.get("sha256") for v in variants if isinstance(v, dict)}
    if model_file_sha256 in variant_shas:
        return _link(
            "model_binding", "pass",
            f"model_id {prov_model_id!r} and model_file_sha256 match a "
            "variant in the model-card manifest",
        )
    return _link(
        "model_binding", "fail",
        f"provenance model_file_sha256 {model_file_sha256!r} does not "
        f"match any variant sha256 in the model-card manifest for "
        f"{prov_model_id!r}",
    )


def _check_constitution(provenance_record: Optional[dict]) -> dict:
    """constitution_sha256 present and 64-hex -> pass, else unknown."""
    if not provenance_record:
        return _link(
            "constitution", "unknown",
            "no provenance record to read constitution_sha256 from",
        )
    sha = provenance_record.get("constitution_sha256")
    if isinstance(sha, str) and _HEX64_RE.match(sha):
        return _link("constitution", "pass", f"constitution_sha256 present ({sha})")
    return _link(
        "constitution", "unknown",
        "constitution_sha256 is missing or not a 64-hex sha256 — the "
        "constitution binding cannot be confirmed",
    )


def _check_corpus(provenance_record: Optional[dict]) -> dict:
    """corpus_refs non-empty and URL-shaped -> pass, else unknown."""
    if not provenance_record:
        return _link(
            "corpus", "unknown",
            "no provenance record to read corpus_refs from",
        )
    refs = provenance_record.get("corpus_refs") or []
    if refs and all(
        isinstance(r, str) and r.startswith(("http://", "https://")) for r in refs
    ):
        return _link("corpus", "pass", f"{len(refs)} published corpus ref(s) present")
    return _link(
        "corpus", "unknown",
        "no published (URL) corpus refs on the provenance record",
    )


def _overall(links: list[dict]) -> str:
    """Worst link wins: any fail -> broken; any unknown (no fail) -> partial;
    all pass -> verified."""
    worst = max((link["status"] for link in links), key=lambda s: _STATUS_RANK[s])
    if worst == "fail":
        return "broken"
    if worst == "unknown":
        return "partial"
    return "verified"


def walk_attestation(
    agent: str,
    receipt: dict,
    provenance_record: Optional[dict],
    public_key_hex: str,
    model_manifest: Optional[dict] = None,
) -> dict:
    """Walk the offline attestation chain for one inference receipt.

    Returns ``{agent, inference_id, overall, links}`` where ``links`` is the
    ordered list of chain checks — signature, provenance_present,
    model_binding, constitution, corpus — each
    ``{name, status: "pass"|"fail"|"unknown", detail}``.

    Pure and dependency-light: no store, no controller, no private key, no
    network access — only the inputs handed in. This is the whole point:
    anyone holding a receipt, a provenance record, a public key, and
    (optionally) a model-card manifest can run this offline.
    """
    links = [
        _check_signature(receipt, public_key_hex),
        _check_provenance_present(provenance_record),
        _check_model_binding(receipt, provenance_record, model_manifest),
        _check_constitution(provenance_record),
        _check_corpus(provenance_record),
    ]
    return {
        "agent": agent,
        "inference_id": receipt.get("inference_id"),
        "overall": _overall(links),
        "links": links,
    }
