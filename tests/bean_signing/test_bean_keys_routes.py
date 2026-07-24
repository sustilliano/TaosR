"""Route tests for the Bean-2 public-key API (tinyagentos/routes/bean_keys.py).

Mounts ONLY the bean_keys router on a bare FastAPI app (no full backend
boot), following the pattern in
tests/inference_receipts/test_inference_receipts_routes.py.
"""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tinyagentos.auth_context import CurrentUser, current_user
from tinyagentos.routes.bean_keys import router as bean_keys_router


def _make_app(tmp_path, *, authenticated: bool = True) -> FastAPI:
    app = FastAPI()
    app.state.data_dir = tmp_path
    app.include_router(bean_keys_router)
    if authenticated:
        app.dependency_overrides[current_user] = lambda: CurrentUser(
            user_id="test-user", is_admin=False
        )
    return app


@pytest.mark.asyncio
class TestBeanPubkeyRoute:
    async def test_get_pubkey_returns_64_hex_chars(self, tmp_path):
        app = _make_app(tmp_path)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/api/agents/scout-1/bean-pubkey")
            assert resp.status_code == 200
            body = resp.json()
            assert body["agent_name"] == "scout-1"
            pub = body["public_key_hex"]
            assert len(pub) == 64
            bytes.fromhex(pub)  # does not raise

    async def test_pubkey_stable_across_calls(self, tmp_path):
        app = _make_app(tmp_path)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r1 = await c.get("/api/agents/scout-1/bean-pubkey")
            r2 = await c.get("/api/agents/scout-1/bean-pubkey")
            assert r1.json()["public_key_hex"] == r2.json()["public_key_hex"]

    async def test_different_agents_get_different_pubkeys(self, tmp_path):
        app = _make_app(tmp_path)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r1 = await c.get("/api/agents/scout-1/bean-pubkey")
            r2 = await c.get("/api/agents/scout-2/bean-pubkey")
            assert r1.json()["public_key_hex"] != r2.json()["public_key_hex"]

    async def test_invalid_slug_rejected(self, tmp_path):
        app = _make_app(tmp_path)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/api/agents/.hidden/bean-pubkey")
            assert resp.status_code == 400

    async def test_requires_auth(self, tmp_path):
        app = _make_app(tmp_path, authenticated=False)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/api/agents/scout-1/bean-pubkey")
            assert resp.status_code == 401
