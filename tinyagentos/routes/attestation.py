"""Bean-5 attestation-walk API (docs/design/bean-2-5-plan.md, "Bean-5 —
attestation walk").

GET /api/agents/{name}/attestation/{inference_id} — loads one inference
receipt (Bean-1, ``InferenceReceiptStore``), the agent's Ed25519 public key
(Bean-2, ``bean_keystore``), its provenance record (Bean-0,
``AgentProvenanceStore``), and — if a manifest exists for the receipt's
model — the model-card manifest under ``app-catalog/models/{model_id}/``,
then runs ``bean_attest.walk_attestation`` and returns the resulting chain.

Gated by ``current_user`` and lazy per-slug/app-state stores, exactly like
``routes/provenance.py`` / ``routes/inference_receipts.py`` /
``routes/bean_keys.py``. 404 if the receipt id is not found for the agent.

Not registered anywhere (see docs/design/bean-2-5-plan.md "Delegation
rules") - the integrator wires this router into the app when merging.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from tinyagentos.auth_context import CurrentUser, current_user
from tinyagentos.bean_attest import walk_attestation

router = APIRouter()

# Same slug contract as routes/inference_receipts.py / routes/bean_keys.py:
# a single safe path segment under data/agent-memory/, no separators, no
# dot-prefix, no traversal. Also used to sanity-check model_id before it
# becomes a path component under app-catalog/models/.
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _valid_slug(name: str) -> bool:
    return bool(_SLUG_RE.match(name)) and ".." not in name


def _app_catalog_root() -> Path:
    # tinyagentos/routes/attestation.py -> tinyagentos -> repo root
    return Path(__file__).resolve().parent.parent.parent / "app-catalog"


async def _get_receipt_store(request: Request, slug: str):
    """Get or lazily create the per-agent receipt store on app state.

    Cached under the same app.state key routes/inference_receipts.py uses,
    so when both routers are mounted on the real app they share one open
    connection per agent instead of opening the sqlbook twice.
    """
    stores = getattr(request.app.state, "inference_receipt_stores", None)
    if stores is None:
        stores = {}
        request.app.state.inference_receipt_stores = stores
    store = stores.get(slug)
    if store is None:
        from tinyagentos.inference_receipt_store import InferenceReceiptStore
        data_dir = getattr(request.app.state, "data_dir", Path("data"))
        store = InferenceReceiptStore(
            Path(data_dir) / "agent-memory" / slug / "receipts.sqlbook"
        )
        await store.init()
        stores[slug] = store
    return store


async def _get_provenance_store(request: Request):
    """Get or lazily create the provenance store on app state (Bean-0)."""
    store = getattr(request.app.state, "agent_provenance_store", None)
    if store is None:
        from tinyagentos.agent_provenance_store import AgentProvenanceStore
        data_dir = getattr(request.app.state, "data_dir", Path("data"))
        store = AgentProvenanceStore(Path(data_dir) / "agent_provenance.db")
        await store.init()
        request.app.state.agent_provenance_store = store
    return store


async def _find_receipt(store, inference_id: str) -> dict | None:
    """Locate one receipt by id via the store's public list() API.

    InferenceReceiptStore (Bean-1) exposes no get-by-id method — only
    list()/count(). Page backwards through the ledger with the `before`
    cursor until the id turns up or the ledger runs out.
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


def _load_model_manifest(model_id: str | None) -> dict | None:
    """Best-effort read of app-catalog/models/{model_id}/manifest.yaml.

    Missing model_id, missing file, or unparsable YAML all yield None — the
    model_binding link then reports "unknown" rather than the route 500ing;
    the model card is a nice-to-have cross-check, not a hard dependency.
    """
    if not model_id or not _valid_slug(model_id):
        return None
    path = _app_catalog_root() / "models" / model_id / "manifest.yaml"
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


@router.get("/api/agents/{name}/attestation/{inference_id}")
async def get_attestation(
    name: str,
    inference_id: str,
    request: Request,
    user: CurrentUser = Depends(current_user),
):
    """Walk the offline Bean-5 attestation chain for one inference receipt."""
    if not _valid_slug(name):
        return JSONResponse({"error": f"invalid agent name {name!r}"}, status_code=400)

    receipt_store = await _get_receipt_store(request, name)
    receipt = await _find_receipt(receipt_store, inference_id)
    if receipt is None:
        return JSONResponse(
            {"error": f"no inference receipt {inference_id!r} for agent {name!r}"},
            status_code=404,
        )

    provenance_store = await _get_provenance_store(request)
    provenance_record = await provenance_store.get_provenance(name)

    from tinyagentos import bean_keystore
    data_dir = getattr(request.app.state, "data_dir", Path("data"))
    pubkey = bean_keystore.public_key_hex(name, data_dir)

    model_id = (provenance_record or {}).get("model_id") or receipt.get("model_id")
    model_manifest = _load_model_manifest(model_id)

    return walk_attestation(name, receipt, provenance_record, pubkey, model_manifest)
