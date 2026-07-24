"""Tests for the Bean-3 consent gate wired into mcp/permissions.py::check_permission.

Verifies the hook is opt-in / non-breaking: omitting consent_is_allowed (the
default) reproduces pre-Bean-3 behaviour exactly, and a provided checker only
gates FLAGGED_SCOPES tools.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio

from tinyagentos.mcp.permissions import check_permission
from tinyagentos.mcp.registry import MCPServerStore


@pytest_asyncio.fixture
async def store(tmp_path: Path):
    s = MCPServerStore(tmp_path / "mcp.db")
    await s.init()
    await s.register_server("taos-tank-fleet", "0.1.0", "stdio")
    await s.add_attachment("taos-tank-fleet", "agent", "scout-1")
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_no_consent_checker_unchanged_behaviour(store):
    """consent_is_allowed omitted -> identical to calling check_permission
    with no Bean-3 knowledge at all, even for a flagged tool name."""
    result = await check_permission(
        store, "taos-tank-fleet", "scout-1", [], tool="drive"
    )
    assert result.allowed is True


@pytest.mark.asyncio
async def test_consent_checker_none_explicit_also_unchanged(store):
    result = await check_permission(
        store, "taos-tank-fleet", "scout-1", [], tool="drive",
        consent_is_allowed=None,
    )
    assert result.allowed is True


@pytest.mark.asyncio
async def test_denying_checker_blocks_flagged_tool(store):
    result = await check_permission(
        store, "taos-tank-fleet", "scout-1", [], tool="drive",
        consent_is_allowed=lambda scope: False,
    )
    assert result.allowed is False
    assert result.reason == "consent required (default-closed physical actuation)"


@pytest.mark.asyncio
async def test_denying_checker_passes_non_flagged_tool(store):
    result = await check_permission(
        store, "taos-tank-fleet", "scout-1", [], tool="list_tanks",
        consent_is_allowed=lambda scope: False,
    )
    assert result.allowed is True


@pytest.mark.asyncio
async def test_allowing_checker_permits_flagged_tool(store):
    result = await check_permission(
        store, "taos-tank-fleet", "scout-1", [], tool="drive",
        consent_is_allowed=lambda scope: True,
    )
    assert result.allowed is True


@pytest.mark.asyncio
async def test_async_checker_is_awaited(store):
    async def checker(scope: str) -> bool:
        return scope == "drive"

    result = await check_permission(
        store, "taos-tank-fleet", "scout-1", [], tool="drive",
        consent_is_allowed=checker,
    )
    assert result.allowed is True

    result2 = await check_permission(
        store, "taos-tank-fleet", "scout-1", [], tool="camera_look",
        consent_is_allowed=checker,
    )
    assert result2.allowed is False


@pytest.mark.asyncio
async def test_existing_denial_paths_still_win_over_consent(store):
    """The allowlist/resource checks still short-circuit before the consent
    gate is ever consulted — a tool the attachment doesn't allow is denied
    for the original reason, not the consent reason."""
    await store.register_server("other-server", "0.1.0", "stdio")
    result = await check_permission(
        store, "other-server", "scout-1", [], tool="drive",
        consent_is_allowed=lambda scope: True,
    )
    assert result.allowed is False
    assert result.reason == "no attachment grants access"


@pytest.mark.asyncio
async def test_consent_gate_integrates_with_real_store(tmp_path):
    """End-to-end with the actual BeanConsentStore, not a lambda."""
    from tinyagentos.bean_consent_store import BeanConsentStore

    mcp_store = MCPServerStore(tmp_path / "mcp.db")
    await mcp_store.init()
    await mcp_store.register_server("taos-tank-fleet", "0.1.0", "stdio")
    await mcp_store.add_attachment("taos-tank-fleet", "agent", "scout-1")

    consent_store = BeanConsentStore(tmp_path / "bean_consent.db")
    await consent_store.init()

    def make_checker(agent_name: str):
        return lambda scope: consent_store.is_allowed(agent_name, scope)

    # No grant yet -> denied.
    result = await check_permission(
        mcp_store, "taos-tank-fleet", "scout-1", [], tool="drive",
        consent_is_allowed=make_checker("scout-1"),
    )
    assert result.allowed is False

    # Grant -> allowed.
    await consent_store.grant("scout-1", "drive", granted_by="operator")
    result = await check_permission(
        mcp_store, "taos-tank-fleet", "scout-1", [], tool="drive",
        consent_is_allowed=make_checker("scout-1"),
    )
    assert result.allowed is True

    # Revoke -> denied again, immediately.
    await consent_store.revoke("scout-1", "drive")
    result = await check_permission(
        mcp_store, "taos-tank-fleet", "scout-1", [], tool="drive",
        consent_is_allowed=make_checker("scout-1"),
    )
    assert result.allowed is False

    await mcp_store.close()
    await consent_store.close()
