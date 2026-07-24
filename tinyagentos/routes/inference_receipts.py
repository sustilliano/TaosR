"""Bean-1 inference receipts API (docs/design/silicon-bean-integration.md).

POST /api/agents/{name}/inference-receipts — called by the LiteLLM proxy
callback (litellm_callback.py) with hash-only receipt rows: sha256 digests
plus metadata, never message or response text.  Like the callback's other
controller endpoints (POST /api/trace, POST /api/lifecycle/notify in
routes/trace.py) there is no route-level auth dependency: the callback
authenticates with the local token (``Authorization: Bearer``), which
AuthMiddleware validates before the request reaches the handler, and
verify_csrf is bearer-exempt.

GET /api/agents/{name}/inference-receipts — authenticated read-back for
the UI/CLI, gated by current_user exactly like routes/provenance.py.

One append-only sqlbook per agent at
``{data_dir}/agent-memory/{slug}/receipts.sqlbook``; stores are opened
lazily and cached on app.state keyed by slug.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from tinyagentos.auth_context import CurrentUser, current_user

router = APIRouter()

# Agent slugs become a path component under data/agent-memory/, so the
# name must be a single safe segment — no separators, no dot-prefix.
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _valid_slug(name: str) -> bool:
    return bool(_SLUG_RE.match(name)) and ".." not in name


async def _get_store(request: Request, slug: str):
    """Get or lazily create the per-agent receipt store on app state."""
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


class InferenceReceiptIn(BaseModel):
    """Hash-only receipt row — the schema forbids content by construction.

    ``signature`` is deliberately absent: it stays NULL in Bean-1 (agent-held
    Ed25519 signing is Bean-2+).
    """
    model_id: str
    prompt_hash: str
    output_hash: str
    trace_id: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    status: str = "success"


@router.post("/api/agents/{name}/inference-receipts")
async def post_inference_receipt(name: str, request: Request, body: InferenceReceiptIn):
    """Append a hash-only inference receipt for agent *name*."""
    if not _valid_slug(name):
        return JSONResponse({"error": f"invalid agent name {name!r}"}, status_code=400)
    if not body.model_id or not body.prompt_hash or not body.output_hash:
        return JSONResponse(
            {"error": "model_id, prompt_hash and output_hash are required"},
            status_code=400,
        )
    store = await _get_store(request, name)
    # Bean-2: sign the receipt with the agent's Ed25519 key. The signer runs
    # inside record() so the signature covers the generated inference_id, in
    # one append-only write; it is fail-open (a signing error stores the row
    # unsigned rather than dropping it).
    from tinyagentos import bean_keystore
    data_dir = getattr(request.app.state, "data_dir", Path("data"))
    inference_id = await store.record(
        model_id=body.model_id,
        prompt_hash=body.prompt_hash,
        output_hash=body.output_hash,
        trace_id=body.trace_id,
        prompt_tokens=body.prompt_tokens,
        completion_tokens=body.completion_tokens,
        started_at=body.started_at,
        completed_at=body.completed_at,
        status=body.status,
        signer=lambda receipt: bean_keystore.sign_receipt(name, data_dir, receipt),
    )
    return {"agent_name": name, "inference_id": inference_id}


@router.get("/api/agents/{name}/inference-receipts")
async def list_inference_receipts(
    name: str,
    request: Request,
    limit: int = 50,
    before: str | None = None,
    user: CurrentUser = Depends(current_user),
):
    """Newest-first receipts for agent *name* plus the ledger's total count."""
    if not _valid_slug(name):
        return JSONResponse({"error": f"invalid agent name {name!r}"}, status_code=400)
    store = await _get_store(request, name)
    receipts = await store.list(limit=limit, before=before)
    count = await store.count()
    return {"receipts": receipts, "count": count}
