from __future__ import annotations

"""Bean-5 attestation-walk CLi (docs/design/bean-2-5-plan.md, "Bean-5 —
attestation walk").

A ``pk-client``-style CLI: given an agent and one of its inference-receipt
ids, walk the whole offline trust chain and print each link's status.
Opens the same stores the route in ``routes/attestation.py`` uses, but
directly on disk — no HTTP, no running controller required:

    python -m tinyagentos.bean_attest_cli <agent> <inference_id> [--data-dir DIR] [--json]

Dependency-free by default: only the stdlib plus the modules this walk is
built from (``inference_receipt_store``, ``agent_provenance_store``,
``bean_keystore``, ``bean_attest`` — which need ``aiosqlite`` and
``cryptography``, already required by those modules themselves). If
PyYAML happens to be installed, the CLI also reads the model-card
manifest under ``app-catalog/models/{model_id}/manifest.yaml`` for the
``model_binding`` link; if it isn't, that link just reports "unknown"
for the manifest cross-check instead of "pass" — the walk still runs.

Exit codes:
  0  the walk ran to completion (any overall status — this is a report
     tool, not a policy gate; read the printed "OVERALL" to see whether
     the chain is verified/partial/broken)
  1  could not run the walk at all (bad arguments, unknown inference_id)
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from tinyagentos import bean_keystore
from tinyagentos.agent_provenance_store import AgentProvenanceStore
from tinyagentos.bean_attest import walk_attestation
from tinyagentos.inference_receipt_store import InferenceReceiptStore

_REPO_ROOT = Path(__file__).resolve().parent.parent

_STATUS_SYMBOL = {"pass": "✓", "fail": "✗", "unknown": "?"}


def _load_model_manifest(model_id: str | None, repo_root: Path) -> dict | None:
    """Best-effort read of app-catalog/models/{model_id}/manifest.yaml.

    Optional: returns None (never raises) if there is no model_id, no
    manifest file, or PyYAML is not installed — the walk still runs, just
    without the model-card cross-check.
    """
    if not model_id or "/" in model_id or ".." in model_id:
        return None
    path = repo_root / "app-catalog" / "models" / model_id / "manifest.yaml"
    if not path.exists():
        return None
    try:
        import yaml
    except ImportError:
        return None
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
    except (OSError, ValueError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


async def _find_receipt(store: InferenceReceiptStore, inference_id: str) -> dict | None:
    """Locate one receipt by id via the store's public list() API.

    InferenceReceiptStore (Bean-1) has no get-by-id method — page
    backwards through the ledger with the `before` cursor until the id
    turns up or the ledger runs out.
    """
    cursor = None
    while True:
        page = await store.list(limit=200, before=cursor)
        if not page:
            return None
        for row in page:
            if row["inference_id"] == inference_id:
                return row
        cursor = page[-1]["inference_id"]


async def _run(agent: str, inference_id: str, data_dir: Path) -> dict | None:
    """Open the stores directly, run the walk, return the result (or None
    if the receipt id is unknown for this agent)."""
    receipt_store = InferenceReceiptStore(
        data_dir / "agent-memory" / agent / "receipts.sqlbook"
    )
    await receipt_store.init()
    try:
        receipt = await _find_receipt(receipt_store, inference_id)
    finally:
        await receipt_store.close()
    if receipt is None:
        return None

    provenance_store = AgentProvenanceStore(data_dir / "agent_provenance.db")
    await provenance_store.init()
    try:
        provenance_record = await provenance_store.get_provenance(agent)
    finally:
        await provenance_store.close()

    pubkey = bean_keystore.public_key_hex(agent, data_dir)

    model_id = (provenance_record or {}).get("model_id") or receipt.get("model_id")
    model_manifest = _load_model_manifest(model_id, _REPO_ROOT)

    return walk_attestation(agent, receipt, provenance_record, pubkey, model_manifest)


def _print_chain(result: dict) -> None:
    print(f"attestation walk: agent={result['agent']} inference_id={result['inference_id']}")
    for link in result["links"]:
        symbol = _STATUS_SYMBOL.get(link["status"], "?")
        print(f"  [{symbol}] {link['name']}: {link['status']} — {link['detail']}")
    print(f"OVERALL: {result['overall']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tinyagentos.bean_attest_cli",
        description=(
            "Bean-5 offline attestation walk: verify an inference receipt's "
            "signature and trace it back through provenance, model card, "
            "constitution, and corpus refs — entirely offline."
        ),
    )
    parser.add_argument("agent", help="agent slug (e.g. scout-1)")
    parser.add_argument("inference_id", help="inference receipt id (e.g. inf-abc12345)")
    parser.add_argument(
        "--data-dir", default="data",
        help="taOS data directory (default: ./data)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="print the chain as JSON instead of a human-readable report",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    data_dir = Path(args.data_dir)

    result = asyncio.run(_run(args.agent, args.inference_id, data_dir))
    if result is None:
        print(
            f"error: no inference receipt {args.inference_id!r} for agent {args.agent!r}",
            file=sys.stderr,
        )
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_chain(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
