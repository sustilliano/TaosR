"""Bean-2 public-key API (docs/design/bean-2-5-plan.md, "Bean-2 — receipt signing").

GET /api/agents/{name}/bean-pubkey — the agent's Ed25519 public key, so an
external holder of a signed inference receipt can verify it offline with
``bean_keystore.verify_receipt`` and no controller involvement.  Gated by
``current_user`` exactly like the read side of routes/inference_receipts.py;
unlike that GET, the key itself is generated (not just read back) on first
call, matching ``bean_keystore.get_or_create``'s generate-on-first-use
behaviour.

Not registered anywhere (see docs/design/bean-2-5-plan.md "Delegation
rules") - the integrator wires this router into the app when merging.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from tinyagentos.auth_context import CurrentUser, current_user

router = APIRouter()

# Same slug contract as routes/inference_receipts.py: a single safe path
# segment under data/agent-memory/, no separators, no dot-prefix, no
# traversal.
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _valid_slug(name: str) -> bool:
    return bool(_SLUG_RE.match(name)) and ".." not in name


@router.get("/api/agents/{name}/bean-pubkey")
async def get_agent_bean_pubkey(
    name: str,
    request: Request,
    user: CurrentUser = Depends(current_user),
):
    """Return agent *name*'s Ed25519 public key, minting it if absent."""
    if not _valid_slug(name):
        return JSONResponse({"error": f"invalid agent name {name!r}"}, status_code=400)
    from tinyagentos.bean_keystore import public_key_hex

    data_dir = getattr(request.app.state, "data_dir", Path("data"))
    return {
        "agent_name": name,
        "public_key_hex": public_key_hex(name, data_dir),
    }
