from __future__ import annotations

"""Bean-3 consent policy (docs/design/bean-2-5-plan.md, "Bean-3 - consent
gate for physical actuation").

Deliberately decoupled from bean_consent_store.py: everything here is a pure
function of its inputs, so it is unit-testable with a plain dict/lambda and
importable from mcp/permissions.py without pulling in aiosqlite or a live
store. The store is wired in by the caller via an injected `is_allowed_fn`.

--- FLAGGED_SCOPES derivation ---

Read from robotics/tank_fleet_mcp.py and robotics/camera_mcp.py (read-only
per AGENTS.md/task constraints). A scope is flagged iff calling it moves a
physical thing or changes an actuator's live mode - i.e. it is the class of
"consequential output" silicon-bean-integration.md calls out ("drive and
stop in tank_fleet_mcp.py"). Read-only / informational tools are excluded
even though they hit the same bridge:

tank_fleet_mcp.py:
    list_tanks       -- read-only inventory                    EXCLUDED
    fleet_status      -- read-only coordinator status            EXCLUDED
    drive             -- physically moves the tank                FLAGGED
    stop              -- physically halts the tank (or fleet)     FLAGGED
    camera_look       -- physically slews the pan/tilt camera     FLAGGED
    camera_capture    -- triggers a frame capture, moves nothing;
                          same actuation class as camera_mcp's
                          `snapshot` (explicitly read-only)        EXCLUDED
    led               -- cosmetic indicator, not physical motion
                          or a change of actuation/movement mode   EXCLUDED
    set_mode          -- changes the tank's live actuation mode
                          (Manual/Autonomous/.../EmergencyStop)    FLAGGED
    autonomy          -- starts/stops autonomous physical
                          behaviour (drives the tank on its own)   FLAGGED

camera_mcp.py:
    list_cameras      -- read-only inventory                    EXCLUDED
    snapshot          -- read-only image capture                 EXCLUDED
    ptz_move          -- physically pans/tilts the camera          FLAGGED

`camera_capture` and `led` are the two judgment calls: neither moves
anything nor changes an actuation mode, so both are excluded, matching the
"read-only tools ... are excluded" instruction and keeping the flagged set
limited to genuine physical actuation.
"""

from typing import Callable

FLAGGED_SCOPES: frozenset[str] = frozenset(
    {
        # tank_fleet_mcp.py
        "drive",
        "stop",
        "camera_look",
        "set_mode",
        "autonomy",
        # camera_mcp.py
        "ptz_move",
    }
)

_DENIAL_REASON = "consent required (default-closed physical actuation)"


def is_flagged_scope(tool_name: str) -> bool:
    """True iff *tool_name* is a physical-actuation scope requiring consent."""
    return tool_name in FLAGGED_SCOPES


def gated_consent_check(
    scope: str,
    is_gated: Callable[[str], bool],
    is_allowed_fn: Callable[[str], bool],
    denial_reason: str | None = None,
) -> tuple[bool, str | None]:
    """Subject-agnostic consent decision — the all-digital core
    (docs/design/silicon-bean-all-digital.md).

    The rule is the same one Bean-3 and the userspace app broker both
    compute: ``gated and not granted -> deny``. What varies between subject
    kinds is only *which* predicate marks a scope gated:

    - ``is_gated`` — the caller's gated-set membership test
      (``is_flagged_scope`` for agent actuation; ``ns in GATED_CAPS`` for
      app capabilities).
    - ``is_allowed_fn`` — the per-subject grant lookup (typically
      ``BeanConsentStore.is_allowed`` bound to a subject key).

    non-gated scope -> (True, None); gated + granted -> (True, None);
    gated + not granted -> (False, reason). Pure: no store, no I/O.
    """
    if not is_gated(scope):
        return True, None
    if is_allowed_fn(scope):
        return True, None
    return False, denial_reason or _DENIAL_REASON


def consent_check(
    tool_name: str, is_allowed_fn: Callable[[str], bool]
) -> tuple[bool, str | None]:
    """Pure consent decision for a single agent tool call (Bean-3).

    Thin wrapper over ``gated_consent_check`` binding the gated predicate to
    ``is_flagged_scope`` (physical actuation); behaviour is unchanged.

    - non-flagged tool -> (True, None): no gate, unchanged from today.
    - flagged tool + is_allowed_fn(tool_name) is True -> (True, None).
    - flagged tool + is_allowed_fn(tool_name) is False -> (False, reason).

    *is_allowed_fn* is injected (typically `BeanConsentStore.is_allowed`
    bound to an agent, or a lambda in tests) so this function needs no store
    and no I/O, only a scope -> bool lookup.
    """
    return gated_consent_check(tool_name, is_flagged_scope, is_allowed_fn)
