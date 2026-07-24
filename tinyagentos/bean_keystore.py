from __future__ import annotations

"""Bean-2 per-agent Ed25519 keystore and receipt signing (attestation completion).

Fills the ``signature`` column Bean-1 left NULL
(``docs/design/bean-2-5-plan.md``, "Bean-2 — receipt signing").  Each agent
gets its own Ed25519 keypair, generated on first use and persisted as the
raw 32-byte private key at
``data/agent-memory/{slug}/bean-key/private.ed25519`` (mode 0600).  The
private key never leaves the controller process; only the public key and
signatures are ever exposed (see ``routes/bean_keys.py``).

Mirrors the atomic-write pattern in ``hub/identity.py``: write a temp file
then ``os.replace`` into place, so a crash mid-write never leaves a partial
key on disk.

Verification is deliberately free-standing: ``verify_receipt`` takes only a
receipt dict and a hex public key, so a holder can check a receipt offline
with no controller, private key, or network access involved.
"""

import json
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

_KEY_FILENAME = "private.ed25519"

# Exact key set + order the receipt is canonicalized over. ``signature``
# itself is deliberately excluded (see module docstring).
_CANONICAL_FIELDS = (
    "inference_id",
    "trace_id",
    "model_id",
    "prompt_hash",
    "output_hash",
    "prompt_tokens",
    "completion_tokens",
    "started_at",
    "completed_at",
    "status",
)


def _key_path(slug: str, data_dir: str | Path) -> Path:
    return Path(data_dir) / "agent-memory" / slug / "bean-key" / _KEY_FILENAME


def get_or_create(slug: str, data_dir: str | Path) -> Ed25519PrivateKey:
    """Load *slug*'s Ed25519 private key, minting it on first use.

    Idempotent: once a key exists on disk it is loaded unchanged, so the
    agent keeps the same signing identity (and thus verifiable receipt
    history) across restarts.
    """
    path = _key_path(slug, data_dir)
    if path.exists():
        return Ed25519PrivateKey.from_private_bytes(path.read_bytes())

    key = Ed25519PrivateKey.generate()
    raw = key.private_bytes_raw()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:  # pragma: no cover - best effort on odd filesystems
        pass
    return key


def public_key_hex(slug: str, data_dir: str | Path) -> str:
    """Hex-encoded 32-byte Ed25519 public key for *slug*."""
    key = get_or_create(slug, data_dir)
    return key.public_key().public_bytes_raw().hex()


def canonical_receipt_bytes(receipt: dict) -> bytes:
    """Deterministic byte representation of a receipt for signing/verifying.

    Picks exactly ``_CANONICAL_FIELDS`` out of *receipt* (missing keys become
    ``None``; extra keys, including ``signature``, are ignored) and encodes
    them as canonical JSON: sorted keys, no whitespace, ``default=str`` for
    any non-primitive value, UTF-8 bytes.  Key order in the input dict never
    matters — ``sort_keys=True`` makes the output independent of it.
    """
    view = {field: receipt.get(field) for field in _CANONICAL_FIELDS}
    return json.dumps(
        view, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")


def sign_receipt(slug: str, data_dir: str | Path, receipt: dict) -> str:
    """Sign *receipt*'s canonical bytes with *slug*'s private key; hex result."""
    key = get_or_create(slug, data_dir)
    return key.sign(canonical_receipt_bytes(receipt)).hex()


def verify_receipt(receipt: dict, public_key_hex: str) -> str:
    """Tri-state verification: ``"unsigned"`` / ``"valid"`` / ``"invalid"``.

    Needs only the receipt dict and the agent's public key — no private key
    or controller involvement, so a holder can verify entirely offline.
    """
    signature = receipt.get("signature")
    if not signature:
        return "unsigned"
    try:
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        pub.verify(bytes.fromhex(signature), canonical_receipt_bytes(receipt))
        return "valid"
    except (InvalidSignature, ValueError, TypeError):
        return "invalid"
