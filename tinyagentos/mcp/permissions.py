from __future__ import annotations

import fnmatch
import inspect
from dataclasses import dataclass
from typing import Awaitable, Callable, Union

from tinyagentos.bean_consent import consent_check, is_flagged_scope
from tinyagentos.mcp.registry import MCPServerStore


@dataclass
class PermissionResult:
    allowed: bool
    reason: str


# Bean-3 (docs/design/bean-2-5-plan.md): a scope -> bool (or awaitable bool)
# lookup, typically `BeanConsentStore.is_allowed` bound to an agent. Kept as
# a `Callable` here (not a `bean_consent_store` import) so this module never
# takes a hard dependency on the store.
ConsentChecker = Callable[[str], Union[bool, Awaitable[bool]]]


async def check_permission(
    store: MCPServerStore,
    server_id: str,
    agent_name: str,
    agent_groups: list[str],
    tool: str | None = None,
    resource: str | None = None,
    consent_is_allowed: ConsentChecker | None = None,
) -> PermissionResult:
    attachments = await store.list_attachments_for_agent(agent_name, agent_groups)
    # Filter to only attachments for this server
    matching = [a for a in attachments if a["server_id"] == server_id]

    if not matching:
        return PermissionResult(allowed=False, reason="no attachment grants access")

    if tool is not None:
        # Find attachments that have a non-empty tool list containing this tool,
        # or have an empty tool list (meaning unrestricted).
        tool_allowed = False
        for att in matching:
            tools = att["allowed_tools"]
            if not tools:
                # Empty list = unrestricted within this attachment
                tool_allowed = True
                break
            if tool in tools:
                tool_allowed = True
                break
        if not tool_allowed:
            return PermissionResult(allowed=False, reason="tool not in allowlist")

    if resource is not None:
        # At least one attachment must allow the resource. Attachments with
        # an empty resource list are unrestricted (allow any resource).
        resource_allowed = False
        for att in matching:
            patterns = att["allowed_resources"]
            if not patterns:
                resource_allowed = True
                break
            if any(fnmatch.fnmatch(resource, p) for p in patterns):
                resource_allowed = True
                break
        if not resource_allowed:
            return PermissionResult(allowed=False, reason="resource pattern mismatch")

    # Determine the reason string based on which attachment matched
    scope_kinds = {a["scope_kind"] for a in matching}
    if "agent" in scope_kinds:
        reason = "allowed via agent attachment"
    elif "group" in scope_kinds:
        reason = "allowed via group attachment"
    else:
        reason = "allowed via all-scope attachment"

    # Bean-3 consent gate (docs/design/bean-2-5-plan.md). Opt-in only: when
    # no consent_is_allowed callable is supplied (the default), this block
    # is skipped entirely and behaviour is byte-for-byte what it was before
    # Bean-3 — every pre-existing call site (mcp/proxy.py, tests/test_mcp.py)
    # calls check_permission() without this kwarg, so nothing changes for
    # them. A caller opts in by passing a store-backed checker, e.g.
    # `consent_is_allowed=lambda scope: consent_store.is_allowed(agent_name, scope)`.
    if consent_is_allowed is not None and tool is not None and is_flagged_scope(tool):
        active = consent_is_allowed(tool)
        if inspect.isawaitable(active):
            active = await active
        allowed, denial_reason = consent_check(tool, lambda _scope, _v=bool(active): _v)
        if not allowed:
            return PermissionResult(allowed=False, reason=denial_reason)

    return PermissionResult(allowed=True, reason=reason)
