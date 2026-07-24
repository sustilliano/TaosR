"""Store tests for the Bean-3 consent gate (tinyagentos/bean_consent_store.py)."""
from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio

from tinyagentos.bean_consent_store import BeanConsentStore


@pytest_asyncio.fixture
async def store(tmp_path: Path):
    s = BeanConsentStore(tmp_path / "bean_consent.db")
    await s.init()
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_default_closed_no_row(store):
    """No grant row at all -> denied (default closed)."""
    assert await store.is_allowed("scout-1", "drive") is False


@pytest.mark.asyncio
async def test_grant_then_allowed(store):
    await store.grant("scout-1", "drive", granted_by="operator")
    assert await store.is_allowed("scout-1", "drive") is True


@pytest.mark.asyncio
async def test_revoke_denies_immediately(store):
    await store.grant("scout-1", "drive", granted_by="operator")
    assert await store.is_allowed("scout-1", "drive") is True

    revoked = await store.revoke("scout-1", "drive")
    assert revoked is True
    assert await store.is_allowed("scout-1", "drive") is False


@pytest.mark.asyncio
async def test_revoke_idempotent_when_nothing_active(store):
    # Never granted -> nothing to revoke.
    revoked = await store.revoke("scout-1", "drive")
    assert revoked is False

    # Granted then revoked -> revoking again is still a no-op.
    await store.grant("scout-1", "drive")
    await store.revoke("scout-1", "drive")
    revoked_again = await store.revoke("scout-1", "drive")
    assert revoked_again is False


@pytest.mark.asyncio
async def test_regrant_after_revoke_allowed_again(store):
    await store.grant("scout-1", "drive")
    await store.revoke("scout-1", "drive")
    assert await store.is_allowed("scout-1", "drive") is False

    await store.grant("scout-1", "drive", granted_by="operator-2")
    assert await store.is_allowed("scout-1", "drive") is True


@pytest.mark.asyncio
async def test_scopes_are_independent(store):
    await store.grant("scout-1", "drive")
    assert await store.is_allowed("scout-1", "drive") is True
    assert await store.is_allowed("scout-1", "ptz_move") is False


@pytest.mark.asyncio
async def test_agents_are_independent(store):
    await store.grant("scout-1", "drive")
    assert await store.is_allowed("scout-1", "drive") is True
    assert await store.is_allowed("scout-2", "drive") is False


@pytest.mark.asyncio
async def test_list_grants_newest_first_and_never_deletes(store):
    await store.grant("scout-1", "drive", granted_by="alice")
    await store.revoke("scout-1", "drive")
    await store.grant("scout-1", "drive", granted_by="bob")

    grants = await store.list_grants("scout-1")
    assert len(grants) == 2
    # Newest first.
    assert grants[0]["granted_by"] == "bob"
    assert grants[0]["revoked_at"] is None
    assert grants[1]["granted_by"] == "alice"
    assert grants[1]["revoked_at"] is not None  # revoked, not deleted


@pytest.mark.asyncio
async def test_list_grants_scoped_to_agent(store):
    await store.grant("scout-1", "drive")
    await store.grant("scout-2", "ptz_move")

    grants = await store.list_grants("scout-1")
    assert len(grants) == 1
    assert grants[0]["agent_slug"] == "scout-1"


@pytest.mark.asyncio
async def test_list_grants_empty_for_unknown_agent(store):
    assert await store.list_grants("ghost") == []
