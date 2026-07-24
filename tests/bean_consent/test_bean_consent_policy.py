"""Policy tests for the Bean-3 consent gate (tinyagentos/bean_consent.py).

Pure-function tests: no store, no DB, just injected lambdas — the whole
point of decoupling the policy from storage.
"""
from __future__ import annotations

from tinyagentos.bean_consent import FLAGGED_SCOPES, consent_check, is_flagged_scope


def test_non_flagged_tool_always_allowed():
    # Even an is_allowed_fn that always denies must not gate a non-flagged tool.
    allowed, reason = consent_check("list_tanks", lambda scope: False)
    assert allowed is True
    assert reason is None


def test_flagged_tool_gated_by_injected_fn_allow():
    allowed, reason = consent_check("drive", lambda scope: True)
    assert allowed is True
    assert reason is None


def test_flagged_tool_gated_by_injected_fn_deny():
    allowed, reason = consent_check("drive", lambda scope: False)
    assert allowed is False
    assert reason == "consent required (default-closed physical actuation)"


def test_is_flagged_scope_matches_consent_check_gating():
    for scope in FLAGGED_SCOPES:
        assert is_flagged_scope(scope) is True
    assert is_flagged_scope("list_tanks") is False


def test_flagged_scopes_contains_tank_movement_and_camera_ptz():
    # Tank: drive/stop (movement) + set_mode/autonomy (actuation mode changes).
    assert "drive" in FLAGGED_SCOPES
    assert "stop" in FLAGGED_SCOPES
    assert "camera_look" in FLAGGED_SCOPES
    assert "set_mode" in FLAGGED_SCOPES
    assert "autonomy" in FLAGGED_SCOPES
    # Camera bridge: ptz_move physically moves the camera.
    assert "ptz_move" in FLAGGED_SCOPES


def test_flagged_scopes_excludes_read_only_tools():
    read_only = {
        "list_tanks",
        "fleet_status",
        "list_cameras",
        "snapshot",
        "camera_capture",
        "led",
    }
    assert FLAGGED_SCOPES.isdisjoint(read_only)


def test_is_allowed_fn_only_called_for_flagged_tool():
    calls = []

    def tracker(scope):
        calls.append(scope)
        return True

    consent_check("list_tanks", tracker)
    assert calls == []  # never consulted for a non-flagged tool

    consent_check("drive", tracker)
    assert calls == ["drive"]
