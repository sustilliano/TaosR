"""Tests for the tank fleet MCP bridge.

Drives McpStdioServer.handle_request directly and stubs urllib at the
module level, so no coordinator or subprocess is needed.
"""
import importlib.util
import json
import sys
import uuid
from pathlib import Path

import pytest

ROBOTICS = Path(__file__).resolve().parents[2] / "robotics"


@pytest.fixture()
def bridge(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "tank_fleet_mcp_under_test", ROBOTICS / "tank_fleet_mcp.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    calls = []

    def fake_http(method, path, body=None):
        calls.append({"method": method, "path": path, "body": body})
        if path == "/api/tanks":
            return "[]"
        if path == "/api/status":
            return '{"status": "running", "tanks_connected": 0}'
        return "Command sent"

    monkeypatch.setattr(mod, "_http", fake_http)
    mod._test_calls = calls
    yield mod
    sys.modules.pop("tank_fleet_mcp_under_test", None)


def call_tool(mod, name, arguments=None):
    resp = mod.server.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    })
    assert "error" not in resp, resp
    return resp["result"]


def test_initialize_and_tool_listing(bridge):
    resp = bridge.server.handle_request({
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18"},
    })
    assert resp["result"]["serverInfo"]["name"] == "taos-tank-fleet"

    resp = bridge.server.handle_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )
    names = {t["name"] for t in resp["result"]["tools"]}
    assert {"list_tanks", "drive", "stop", "camera_look",
            "led", "set_mode", "autonomy"} <= names


def test_drive_forward_builds_externally_tagged_command(bridge):
    tank = str(uuid.uuid4())
    call_tool(bridge, "drive", {"tank_id": tank, "action": "forward", "speed": 50})

    call = bridge._test_calls[-1]
    assert call["path"] == f"/api/tanks/{tank}/command"
    body = call["body"]
    # serde externally-tagged enums: {"Move": {"Forward": {"speed": 50}}}
    assert body["kind"] == {"Move": {"Forward": {"speed": 50}}}
    assert set(body) == {"id", "kind", "priority", "interrupt"}
    uuid.UUID(body["id"])  # valid v4


def test_drive_speed_clamped_to_fleet_limit(bridge):
    call_tool(bridge, "drive",
              {"tank_id": "t", "action": "forward", "speed": 100})
    body = bridge._test_calls[-1]["body"]
    assert body["kind"]["Move"]["Forward"]["speed"] == bridge.MAX_SPEED


def test_timed_drive_uses_differential_variant(bridge):
    call_tool(bridge, "drive", {
        "tank_id": "t", "action": "turn_left", "speed": 30, "duration_ms": 500,
    })
    body = bridge._test_calls[-1]["body"]
    assert body["kind"] == {"Move": {"Timed": {
        "left": -30, "right": 30, "duration_ms": 500,
    }}}


def test_stop_single_tank_is_interrupt_priority(bridge):
    call_tool(bridge, "stop", {"tank_id": "abc"})
    call = bridge._test_calls[-1]
    assert call["path"] == "/api/tanks/abc/command"
    assert call["body"]["kind"] == "Stop"
    assert call["body"]["interrupt"] is True
    assert call["body"]["priority"] == 255


def test_stop_without_tank_broadcasts_emergency_stop(bridge):
    call_tool(bridge, "stop", {})
    call = bridge._test_calls[-1]
    assert call["path"] == "/api/broadcast"
    assert call["body"]["kind"] == "Stop"
    assert call["body"]["interrupt"] is True


def test_camera_look_clamps_angles(bridge):
    call_tool(bridge, "camera_look", {"tank_id": "t", "pan": 180, "tilt": -400})
    body = bridge._test_calls[-1]["body"]
    assert body["kind"] == {"Camera": {"Look": {"pan": 90, "tilt": -90}}}


def test_led_and_mode_and_autonomy_shapes(bridge):
    call_tool(bridge, "led", {"tank_id": "t", "mode": "blink",
                              "r": 255, "g": 0, "b": 0, "interval_ms": 200})
    assert bridge._test_calls[-1]["body"]["kind"] == {"Led": {"Blink": {
        "r": 255, "g": 0, "b": 0, "interval_ms": 200,
    }}}

    call_tool(bridge, "set_mode", {"tank_id": "t", "mode": "Autonomous"})
    assert bridge._test_calls[-1]["body"]["kind"] == {"SetMode": "Autonomous"}

    call_tool(bridge, "autonomy", {"tank_id": "t", "action": "start",
                                   "mode": "explore"})
    assert bridge._test_calls[-1]["body"]["kind"] == {"StartAutonomy": "Explore"}

    call_tool(bridge, "autonomy", {"tank_id": "t", "action": "stop"})
    assert bridge._test_calls[-1]["body"]["kind"] == "StopAutonomy"


def test_unknown_tool_is_protocol_error(bridge):
    resp = bridge.server.handle_request({
        "jsonrpc": "2.0", "id": 9, "method": "tools/call",
        "params": {"name": "nope", "arguments": {}},
    })
    assert resp["error"]["code"] == -32602


def test_tool_exception_returns_is_error_result(bridge, monkeypatch):
    def boom(method, path, body=None):
        raise OSError("coordinator unreachable")

    monkeypatch.setattr(bridge, "_http", boom)
    resp = bridge.server.handle_request({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "list_tanks", "arguments": {}},
    })
    assert resp["result"]["isError"] is True
    assert "coordinator unreachable" in resp["result"]["content"][0]["text"]
