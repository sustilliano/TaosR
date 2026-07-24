"""Route tests for the Bean-0 provenance API.

Mounts ONLY tinyagentos/routes/provenance.py on a bare FastAPI app (no full
backend boot): app.state.data_dir points at tmp_path and the current_user
auth dependency is overridden, exactly what the router reads at runtime.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tinyagentos.auth_context import CurrentUser, current_user
from tinyagentos.routes.provenance import router as provenance_router

RECORD = {
    "substrate": "silicon",
    "framework": "hermes",
    "framework_ref": "v0.2.1",
    "installer_sha256": "a" * 64,
    "constitution_sha256": "b" * 64,
    "model_id": "hermes-3-llama-3.1-8b",
    "model_file_sha256": "c" * 64,
    "corpus_refs": ["https://huggingface.co/datasets/teknium/OpenHermes-2.5"],
    "recorded_at": "2026-07-24T00:00:00Z",
}


def _make_app(tmp_path, *, authenticated: bool = True) -> FastAPI:
    app = FastAPI()
    app.state.data_dir = tmp_path
    app.include_router(provenance_router)
    if authenticated:
        app.dependency_overrides[current_user] = lambda: CurrentUser(
            user_id="test-user", is_admin=False
        )
    return app


@pytest_asyncio.fixture
async def client(tmp_path):
    app = _make_app(tmp_path)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    store = getattr(app.state, "agent_provenance_store", None)
    if store is not None:
        await store.close()


@pytest.mark.asyncio
class TestProvenanceRoutes:

    async def test_post_then_get_roundtrip(self, client):
        resp = await client.post("/api/agents/scout-1/provenance", json=RECORD)
        assert resp.status_code == 200
        assert resp.json() == {"agent_name": "scout-1", "record": RECORD}

        resp = await client.get("/api/agents/scout-1/provenance")
        assert resp.status_code == 200
        assert resp.json() == RECORD

    async def test_get_unknown_agent_404(self, client):
        resp = await client.get("/api/agents/ghost/provenance")
        assert resp.status_code == 404

    async def test_post_again_overwrites(self, client):
        await client.post("/api/agents/scout-1/provenance", json=RECORD)
        updated = dict(RECORD, framework_ref="v0.3.0")
        resp = await client.post("/api/agents/scout-1/provenance", json=updated)
        assert resp.status_code == 200

        resp = await client.get("/api/agents/scout-1/provenance")
        assert resp.json() == updated

    async def test_post_empty_record_400(self, client):
        resp = await client.post("/api/agents/scout-1/provenance", json={})
        assert resp.status_code == 400

    async def test_unauthenticated_401(self, tmp_path):
        app = _make_app(tmp_path, authenticated=False)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post("/api/agents/scout-1/provenance", json=RECORD)
            assert resp.status_code == 401
            resp = await c.get("/api/agents/scout-1/provenance")
            assert resp.status_code == 401
