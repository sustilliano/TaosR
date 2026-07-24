"""Bean-0 agent provenance API (docs/design/silicon-bean-integration.md).

A deployed agent registers its provenance record - the hashes binding it to
the framework, constitution, model, and corpus that produced it - and any
authenticated caller can read it back.  Latest-wins: posting again replaces
the stored record.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse

from tinyagentos.auth_context import CurrentUser, current_user

router = APIRouter()


async def _get_store(request: Request):
    """Get or lazily create the provenance store on app state."""
    store = getattr(request.app.state, "agent_provenance_store", None)
    if store is None:
        from tinyagentos.agent_provenance_store import AgentProvenanceStore
        data_dir = getattr(request.app.state, "data_dir", Path("data"))
        store = AgentProvenanceStore(Path(data_dir) / "agent_provenance.db")
        await store.init()
        request.app.state.agent_provenance_store = store
    return store


@router.post("/api/agents/{name}/provenance")
async def set_agent_provenance(
    name: str,
    request: Request,
    record: dict = Body(...),
    user: CurrentUser = Depends(current_user),
):
    """Store (or replace) the Bean-0 provenance record for agent *name*."""
    if not record:
        return JSONResponse(
            {"error": "provenance record must be a non-empty JSON object"},
            status_code=400,
        )
    store = await _get_store(request)
    await store.set_provenance(name, record)
    return {"agent_name": name, "record": record}


@router.get("/api/agents/{name}/provenance")
async def get_agent_provenance(
    name: str,
    request: Request,
    user: CurrentUser = Depends(current_user),
):
    """Return the stored provenance record for agent *name*, 404 if none."""
    store = await _get_store(request)
    record = await store.get_provenance(name)
    if record is None:
        return JSONResponse(
            {"error": f"no provenance recorded for agent {name!r}"},
            status_code=404,
        )
    return record
