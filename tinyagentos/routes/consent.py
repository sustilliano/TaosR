"""Bean-3 consent API (docs/design/bean-2-5-plan.md, "Bean-3 - consent gate
for physical actuation").

Grant / revoke / list per-agent, per-scope consent for the flagged physical
actuation tools (tank drive/stop/camera_look/set_mode/autonomy, camera
ptz_move — see tinyagentos/bean_consent.py FLAGGED_SCOPES). Default closed:
an agent with no grant for a scope is denied by mcp/permissions.py once that
gate is wired in (this router does not wire it in — see AGENTS/bean-2-5-plan
delegation rules; the integrator registers this router and connects the
consent store to check_permission()).

NOT registered anywhere yet: the integrator adds this to routes/__init__.py
when merging (see docs/design/bean-2-5-plan.md "Delegation rules").
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from tinyagentos.auth_context import CurrentUser, current_user
from tinyagentos.bean_consent import FLAGGED_SCOPES

router = APIRouter()

# Same slug shape as routes/inference_receipts.py / routes/provenance.py:
# the agent name is used as a stored value (and, for other Bean stores, a
# path component), so keep it to one safe segment.
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _valid_slug(name: str) -> bool:
    return bool(_SLUG_RE.match(name)) and ".." not in name


async def _get_store(request: Request):
    """Get or lazily create the consent store on app state.

    One shared store (grants are keyed by agent_slug + scope columns), same
    pattern as agent_provenance_store.py rather than the per-agent sqlbook
    pattern inference_receipts.py uses.
    """
    store = getattr(request.app.state, "bean_consent_store", None)
    if store is None:
        from tinyagentos.bean_consent_store import BeanConsentStore
        data_dir = getattr(request.app.state, "data_dir", Path("data"))
        store = BeanConsentStore(Path(data_dir) / "bean_consent.db")
        await store.init()
        request.app.state.bean_consent_store = store
    return store


class GrantIn(BaseModel):
    # Not required at the pydantic layer so a missing/empty scope is a 400
    # from our own validation below (matching routes/provenance.py's
    # "empty body -> 400" style) rather than FastAPI's generic 422.
    scope: str = ""
    granted_by: str | None = None


class RevokeIn(BaseModel):
    scope: str = ""


@router.post("/api/agents/{name}/consent/grant")
async def grant_consent(
    name: str,
    request: Request,
    body: GrantIn,
    user: CurrentUser = Depends(current_user),
):
    """Grant *name* an active consent for body.scope. Idempotent-additive:
    granting an already-granted scope just adds another active row; the
    scope is (and stays) allowed either way."""
    if not _valid_slug(name):
        return JSONResponse({"error": f"invalid agent name {name!r}"}, status_code=400)
    if not body.scope:
        return JSONResponse({"error": "scope is required"}, status_code=400)
    store = await _get_store(request)
    granted_by = body.granted_by or user.user_id
    row = await store.grant(name, body.scope, granted_by=granted_by)
    return {"agent_name": name, "grant": row}


@router.post("/api/agents/{name}/consent/revoke")
async def revoke_consent(
    name: str,
    request: Request,
    body: RevokeIn,
    user: CurrentUser = Depends(current_user),
):
    """Revoke any active consent grant for *name* + body.scope. Takes effect
    immediately on the next check_permission() call; idempotent when there
    is nothing active to revoke."""
    if not _valid_slug(name):
        return JSONResponse({"error": f"invalid agent name {name!r}"}, status_code=400)
    if not body.scope:
        return JSONResponse({"error": "scope is required"}, status_code=400)
    store = await _get_store(request)
    revoked = await store.revoke(name, body.scope)
    return {"agent_name": name, "scope": body.scope, "revoked": revoked}


@router.get("/api/agents/{name}/consent")
async def list_consent(
    name: str,
    request: Request,
    user: CurrentUser = Depends(current_user),
):
    """All grants (active + historical) for *name*, plus the current
    allowed/denied state of every flagged physical-actuation scope."""
    if not _valid_slug(name):
        return JSONResponse({"error": f"invalid agent name {name!r}"}, status_code=400)
    store = await _get_store(request)
    grants = await store.list_grants(name)
    flagged_scopes = {
        scope: await store.is_allowed(name, scope) for scope in sorted(FLAGGED_SCOPES)
    }
    return {"agent_name": name, "grants": grants, "flagged_scopes": flagged_scopes}
