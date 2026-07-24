"""Route tests for the Bean-1 inference-receipts API.

Mounts ONLY tinyagentos/routes/inference_receipts.py on a bare FastAPI app
(no full backend boot): app.state.data_dir points at tmp_path and the
current_user auth dependency is overridden for the GET path.  POST is
un-gated at the route level (the LiteLLM callback authenticates with the
local bearer token, validated by AuthMiddleware in the real app), so it
works here without an override — matching routes/trace.py's POST /api/trace.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tinyagentos.auth_context import CurrentUser, current_user
from tinyagentos.routes.inference_receipts import router as receipts_router

RECEIPT = {
    "model_id": "hermes-3-llama-3.1-8b",
    "prompt_hash": "a" * 64,
    "output_hash": "b" * 64,
    "trace_id": "call-1",
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "started_at": "2026-07-24T00:00:00+00:00",
    "completed_at": "2026-07-24T00:00:01+00:00",
    "status": "success",
}


def _make_app(tmp_path, *, authenticated: bool = True) -> FastAPI:
    app = FastAPI()
    app.state.data_dir = tmp_path
    app.include_router(receipts_router)
    if authenticated:
        app.dependency_overrides[current_user] = lambda: CurrentUser(
            user_id="test-user", is_admin=False
        )
    return app


async def _close_stores(app):
    for store in getattr(app.state, "inference_receipt_stores", {}).values():
        await store.close()


@pytest_asyncio.fixture
async def app_client(tmp_path):
    app = _make_app(tmp_path)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield app, c
    await _close_stores(app)


@pytest.mark.asyncio
class TestInferenceReceiptRoutes:

    async def test_post_then_get_roundtrip(self, app_client):
        _, client = app_client
        resp = await client.post("/api/agents/scout-1/inference-receipts", json=RECEIPT)
        assert resp.status_code == 200
        inf_id = resp.json()["inference_id"]
        assert inf_id.startswith("inf-")

        resp = await client.get("/api/agents/scout-1/inference-receipts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["receipts"][0]["inference_id"] == inf_id
        assert body["receipts"][0]["prompt_hash"] == "a" * 64

    async def test_get_empty_agent_is_zero_not_404(self, app_client):
        _, client = app_client
        # Unlike provenance, a fresh receipt ledger is a valid empty ledger.
        resp = await client.get("/api/agents/fresh/inference-receipts")
        assert resp.status_code == 200
        assert resp.json() == {"receipts": [], "count": 0}

    async def test_newest_first_and_limit(self, app_client):
        _, client = app_client
        for i in range(3):
            await client.post("/api/agents/scout-1/inference-receipts",
                              json=dict(RECEIPT, trace_id=f"call-{i}"))
        resp = await client.get("/api/agents/scout-1/inference-receipts?limit=2")
        body = resp.json()
        assert body["count"] == 3
        assert len(body["receipts"]) == 2
        assert body["receipts"][0]["trace_id"] == "call-2"  # newest first

    async def test_post_missing_hash_400(self, app_client):
        _, client = app_client
        bad = dict(RECEIPT)
        bad["output_hash"] = ""
        resp = await client.post("/api/agents/scout-1/inference-receipts", json=bad)
        assert resp.status_code == 400

    async def test_invalid_slug_rejected(self, app_client):
        _, client = app_client
        # A dot-prefixed segment is a single path component (not normalized
        # away like '..') and is rejected by _valid_slug — no path traversal
        # into agent-memory/.
        resp = await client.post("/api/agents/.hidden/inference-receipts", json=RECEIPT)
        assert resp.status_code == 400

    async def test_get_requires_auth(self, tmp_path):
        app = _make_app(tmp_path, authenticated=False)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            # POST is bearer-authed at middleware level (not present on this
            # bare app) so it is reachable; GET is current_user-gated → 401.
            resp = await c.get("/api/agents/scout-1/inference-receipts")
            assert resp.status_code == 401
        await _close_stores(app)
