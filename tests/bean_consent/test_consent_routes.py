"""Route tests for the Bean-3 consent API (tinyagentos/routes/consent.py).

Mounts ONLY routes/consent.py on a bare FastAPI app (no full backend boot),
following tests/provenance/test_provenance_routes.py's harness: app.state.data_dir
points at tmp_path and the current_user auth dependency is overridden.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tinyagentos.auth_context import CurrentUser, current_user
from tinyagentos.routes.consent import router as consent_router


def _make_app(tmp_path, *, authenticated: bool = True) -> FastAPI:
    app = FastAPI()
    app.state.data_dir = tmp_path
    app.include_router(consent_router)
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
    store = getattr(app.state, "bean_consent_store", None)
    if store is not None:
        await store.close()


@pytest.mark.asyncio
class TestConsentRoutes:

    async def test_grant_then_list_shows_active(self, client):
        resp = await client.post(
            "/api/agents/scout-1/consent/grant",
            json={"scope": "drive", "granted_by": "operator"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_name"] == "scout-1"
        assert body["grant"]["scope"] == "drive"
        assert body["grant"]["granted_by"] == "operator"
        assert body["grant"]["revoked_at"] is None

        resp = await client.get("/api/agents/scout-1/consent")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["grants"]) == 1
        assert body["grants"][0]["scope"] == "drive"
        assert body["flagged_scopes"]["drive"] is True
        # Untouched flagged scope stays denied (default closed).
        assert body["flagged_scopes"]["ptz_move"] is False

    async def test_grant_defaults_granted_by_to_caller(self, client):
        resp = await client.post(
            "/api/agents/scout-1/consent/grant", json={"scope": "drive"}
        )
        assert resp.status_code == 200
        assert resp.json()["grant"]["granted_by"] == "test-user"

    async def test_revoke_round_trip(self, client):
        await client.post(
            "/api/agents/scout-1/consent/grant", json={"scope": "drive"}
        )
        resp = await client.post(
            "/api/agents/scout-1/consent/revoke", json={"scope": "drive"}
        )
        assert resp.status_code == 200
        assert resp.json() == {"agent_name": "scout-1", "scope": "drive", "revoked": True}

        resp = await client.get("/api/agents/scout-1/consent")
        body = resp.json()
        assert body["flagged_scopes"]["drive"] is False
        # History preserved, not deleted.
        assert len(body["grants"]) == 1
        assert body["grants"][0]["revoked_at"] is not None

    async def test_revoke_with_no_active_grant_is_idempotent(self, client):
        resp = await client.post(
            "/api/agents/scout-1/consent/revoke", json={"scope": "drive"}
        )
        assert resp.status_code == 200
        assert resp.json()["revoked"] is False

    async def test_list_unknown_agent_empty(self, client):
        resp = await client.get("/api/agents/ghost/consent")
        assert resp.status_code == 200
        body = resp.json()
        assert body["grants"] == []
        assert all(v is False for v in body["flagged_scopes"].values())

    async def test_grant_missing_scope_400(self, client):
        resp = await client.post("/api/agents/scout-1/consent/grant", json={})
        assert resp.status_code == 400

    async def test_invalid_agent_slug_400(self, client):
        # Leading '.' fails _SLUG_RE (must start alnum) -> 400, not a 404
        # from path-routing weirdness.
        resp = await client.get("/api/agents/..bad/consent")
        assert resp.status_code == 400

    async def test_unauthenticated_401(self, tmp_path):
        app = _make_app(tmp_path, authenticated=False)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/api/agents/scout-1/consent/grant", json={"scope": "drive"}
            )
            assert resp.status_code == 401
            resp = await c.post(
                "/api/agents/scout-1/consent/revoke", json={"scope": "drive"}
            )
            assert resp.status_code == 401
            resp = await c.get("/api/agents/scout-1/consent")
            assert resp.status_code == 401
