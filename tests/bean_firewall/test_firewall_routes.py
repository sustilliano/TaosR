"""Route tests for the Bean-4 firewall API (tinyagentos/routes/firewall.py).

Mounts ONLY routes/firewall.py on a bare FastAPI app (no full backend boot),
following tests/provenance/test_provenance_routes.py's / tests/bean_consent/
test_consent_routes.py's harness: app.state.data_dir points at tmp_path and
the current_user auth dependency is overridden.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tinyagentos.auth_context import CurrentUser, current_user
from tinyagentos.routes.firewall import router as firewall_router


def _make_app(tmp_path, *, authenticated: bool = True) -> FastAPI:
    app = FastAPI()
    app.state.data_dir = tmp_path
    app.include_router(firewall_router)
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
    store = getattr(app.state, "bean_firewall_store", None)
    if store is not None:
        await store.close()


def _events(*tools: str, start_ts: float = 0.0) -> list[dict]:
    return [{"tool": t, "ts": start_ts + i} for i, t in enumerate(tools)]


@pytest.mark.asyncio
class TestFirewallRoutes:
    async def test_get_unknown_agent_is_greenfield_not_404(self, client):
        resp = await client.get("/api/agents/ghost/firewall")
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_name"] == "ghost"
        assert body["baseline"]["greenfield"] is True
        assert body["baseline"]["event_count"] == 0
        assert body["alerts"] == []

    async def test_post_baseline_then_get_reflects_it(self, client):
        events = _events(*(["list_tanks", "fleet_status"] * 10))
        resp = await client.post(
            "/api/agents/scout-1/firewall/baseline", json={"events": events}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_name"] == "scout-1"
        assert body["baseline"]["event_count"] == 20
        assert body["baseline"]["greenfield"] is False
        assert set(body["baseline"]["tools"]) == {"list_tanks", "fleet_status"}

        resp = await client.get("/api/agents/scout-1/firewall")
        assert resp.status_code == 200
        assert resp.json()["baseline"]["event_count"] == 20

    async def test_post_baseline_rebuild_replaces_not_merges(self, client):
        await client.post(
            "/api/agents/scout-1/firewall/baseline",
            json={"events": _events(*(["list_tanks"] * 5))},
        )
        resp = await client.post(
            "/api/agents/scout-1/firewall/baseline",
            json={"events": _events(*(["ptz_move"] * 3))},
        )
        assert resp.status_code == 200
        assert resp.json()["baseline"]["tools"] == ["ptz_move"]
        assert resp.json()["baseline"]["event_count"] == 3

    async def test_post_baseline_requires_events_list(self, client):
        resp = await client.post("/api/agents/scout-1/firewall/baseline", json={})
        assert resp.status_code == 400
        resp = await client.post(
            "/api/agents/scout-1/firewall/baseline", json={"events": "not-a-list"}
        )
        assert resp.status_code == 400

    async def test_check_window_in_distribution_no_alert(self, client):
        await client.post(
            "/api/agents/scout-1/firewall/baseline",
            json={"events": _events(*(["list_tanks", "fleet_status"] * 20))},
        )
        resp = await client.post(
            "/api/agents/scout-1/firewall/check",
            json={"events": _events("list_tanks", "fleet_status", start_ts=1000.0)},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["anomalous"] is False
        assert body["reasons"] == []

        alerts_resp = await client.get("/api/agents/scout-1/firewall")
        assert alerts_resp.json()["alerts"] == []

    async def test_check_window_actuation_burst_records_alert(self, client):
        await client.post(
            "/api/agents/scout-1/firewall/baseline",
            json={"events": _events(*(["list_tanks", "fleet_status"] * 20))},
        )
        resp = await client.post(
            "/api/agents/scout-1/firewall/check",
            json={
                "events": _events(
                    "list_tanks", "fleet_status", "drive", "drive", start_ts=2000.0
                )
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["anomalous"] is True
        assert any("no prior actuation" in r for r in body["reasons"])

        status_resp = await client.get("/api/agents/scout-1/firewall")
        alerts = status_resp.json()["alerts"]
        assert len(alerts) == 1
        assert alerts[0]["score"] == body["score"]
        assert alerts[0]["reasons"] == body["reasons"]

    async def test_check_window_requires_events_list(self, client):
        resp = await client.post("/api/agents/scout-1/firewall/check", json={})
        assert resp.status_code == 400

    async def test_invalid_agent_slug_400(self, client):
        resp = await client.get("/api/agents/..bad/firewall")
        assert resp.status_code == 400
        resp = await client.post("/api/agents/..bad/firewall/baseline", json={"events": []})
        assert resp.status_code == 400
        resp = await client.post("/api/agents/..bad/firewall/check", json={"events": []})
        assert resp.status_code == 400

    async def test_unauthenticated_401(self, tmp_path):
        app = _make_app(tmp_path, authenticated=False)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/api/agents/scout-1/firewall")
            assert resp.status_code == 401
            resp = await c.post("/api/agents/scout-1/firewall/baseline", json={"events": []})
            assert resp.status_code == 401
            resp = await c.post("/api/agents/scout-1/firewall/check", json={"events": []})
            assert resp.status_code == 401
