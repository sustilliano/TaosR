"""Route tests for the Bean-5 attestation-walk API
(tinyagentos/routes/attestation.py).

Mounts the attestation router alongside routes/inference_receipts.py and
routes/provenance.py on a bare FastAPI app (no full backend boot) —
exactly the pattern in tests/bean_signing/test_bean_keys_routes.py. Seeding
uses those two routers' own POST endpoints so a real signed receipt (via
bean_keystore, wired in by routes/inference_receipts.py) and a real
provenance record land on the same app.state.data_dir the attestation
route reads from.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tinyagentos.auth_context import CurrentUser, current_user
from tinyagentos.routes.attestation import router as attestation_router
from tinyagentos.routes.inference_receipts import router as receipts_router
from tinyagentos.routes.provenance import router as provenance_router

MODEL_ID = "hermes-3-llama-3.1-8b"
# Real sha256 of the q4_k_m variant in
# app-catalog/models/hermes-3-llama-3.1-8b/manifest.yaml, so the
# model_binding link can genuinely pass against the real model card.
MODEL_FILE_SHA256 = "d4403ce5a6e930f4c2509456388c20d633a15ff08dd52ef3b142ff1810ec3553"

PROVENANCE_RECORD = {
    "substrate": "silicon",
    "framework": "hermes",
    "framework_ref": "v0.2.1",
    "installer_sha256": "a" * 64,
    "constitution_sha256": "b" * 64,
    "model_id": MODEL_ID,
    "model_file_sha256": MODEL_FILE_SHA256,
    "corpus_refs": ["https://huggingface.co/datasets/teknium/OpenHermes-2.5"],
    "recorded_at": "2026-07-24T00:00:00Z",
}

RECEIPT_IN = {
    "model_id": MODEL_ID,
    "prompt_hash": "e" * 64,
    "output_hash": "f" * 64,
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
    app.include_router(attestation_router)
    app.include_router(receipts_router)
    app.include_router(provenance_router)
    if authenticated:
        app.dependency_overrides[current_user] = lambda: CurrentUser(
            user_id="test-user", is_admin=False
        )
    return app


async def _close_stores(app):
    for store in getattr(app.state, "inference_receipt_stores", {}).values():
        await store.close()
    store = getattr(app.state, "agent_provenance_store", None)
    if store is not None:
        await store.close()


@pytest_asyncio.fixture
async def app_client(tmp_path):
    app = _make_app(tmp_path)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield app, c
    await _close_stores(app)


async def _seed(client, agent: str = "scout-1") -> str:
    """POST a (real, signed) receipt and a provenance record; return the
    generated inference_id."""
    resp = await client.post(f"/api/agents/{agent}/inference-receipts", json=RECEIPT_IN)
    assert resp.status_code == 200
    await client.post(f"/api/agents/{agent}/provenance", json=PROVENANCE_RECORD)
    return resp.json()["inference_id"]


@pytest.mark.asyncio
class TestAttestationRoute:

    async def test_full_chain_verified(self, app_client):
        app, client = app_client
        inference_id = await _seed(client)

        resp = await client.get(f"/api/agents/scout-1/attestation/{inference_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent"] == "scout-1"
        assert body["inference_id"] == inference_id
        names = [link["name"] for link in body["links"]]
        assert names == [
            "signature", "provenance_present", "model_binding",
            "constitution", "corpus",
        ]
        for link in body["links"]:
            assert link["status"] == "pass", link
        assert body["overall"] == "verified"

    async def test_missing_provenance_yields_broken(self, app_client):
        app, client = app_client
        resp = await client.post(
            "/api/agents/scout-1/inference-receipts", json=RECEIPT_IN
        )
        inference_id = resp.json()["inference_id"]
        # No provenance POSTed for this agent.

        resp = await client.get(f"/api/agents/scout-1/attestation/{inference_id}")
        assert resp.status_code == 200
        body = resp.json()
        links = {link["name"]: link for link in body["links"]}
        assert links["signature"]["status"] == "pass"
        assert links["provenance_present"]["status"] == "fail"
        assert body["overall"] == "broken"

    async def test_unknown_inference_id_404(self, app_client):
        app, client = app_client
        await _seed(client)
        resp = await client.get("/api/agents/scout-1/attestation/inf-doesnotexist")
        assert resp.status_code == 404

    async def test_unknown_agent_404(self, app_client):
        app, client = app_client
        resp = await client.get("/api/agents/ghost-agent/attestation/inf-doesnotexist")
        assert resp.status_code == 404

    async def test_invalid_slug_400(self, app_client):
        app, client = app_client
        resp = await client.get("/api/agents/.hidden/attestation/inf-x")
        assert resp.status_code == 400

    async def test_unauthenticated_401(self, tmp_path):
        app = _make_app(tmp_path, authenticated=False)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/api/agents/scout-1/attestation/inf-whatever")
            assert resp.status_code == 401
        await _close_stores(app)
