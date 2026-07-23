#!/usr/bin/env python3
"""taOS robotics: tank fleet MCP bridge.

Exposes a tank-agents cluster coordinator (github.com/sustilliano/claudecode
projects/tank-agents — Freenove tank robots on Pi 4 / Pi Zero 2W) as MCP
tools, so any taOS agent framework can drive the fleet.

Coordinator REST API (axum, default port 8420):
    GET  /api/tanks              list connected tanks
    POST /api/tanks/{id}/command send one Command (serde externally tagged)
    POST /api/broadcast          send a Command to every tank
    GET  /api/status             coordinator status

Environment:
    TAOS_TANK_COORDINATOR_URL  base URL, default http://localhost:8420
    TAOS_TANK_MAX_SPEED        speed clamp 1-100, default 70
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_stdio import McpStdioServer  # noqa: E402

COORDINATOR_URL = os.environ.get(
    "TAOS_TANK_COORDINATOR_URL", "http://localhost:8420"
).rstrip("/")
MAX_SPEED = max(1, min(100, int(os.environ.get("TAOS_TANK_MAX_SPEED", "70"))))

server = McpStdioServer("taos-tank-fleet", "0.1.0")


def _http(method: str, path: str, body: dict | None = None) -> str:
    req = urllib.request.Request(
        COORDINATOR_URL + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode()


def _command(kind, priority: int = 0, interrupt: bool = False) -> dict:
    # Full Command struct; serde has no field defaults, so send every field.
    return {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "priority": priority,
        "interrupt": interrupt,
    }


def _send(tank_id: str, kind, priority: int = 0, interrupt: bool = False) -> str:
    return _http(
        "POST", f"/api/tanks/{tank_id}/command",
        _command(kind, priority, interrupt),
    )


def _clamp_speed(speed) -> int:
    return max(0, min(MAX_SPEED, int(speed)))


@server.tool(
    "list_tanks",
    "List all tanks connected to the fleet coordinator, with their state",
    {"type": "object", "properties": {}},
)
def list_tanks() -> dict:
    return json.loads(_http("GET", "/api/tanks"))


@server.tool(
    "fleet_status",
    "Get coordinator status (tank count, uptime)",
    {"type": "object", "properties": {}},
)
def fleet_status() -> dict:
    return json.loads(_http("GET", "/api/status"))


@server.tool(
    "drive",
    "Drive a tank. Actions: forward, backward, turn_left, turn_right. "
    "Speed is 0-100 (clamped to the fleet limit). If duration_ms is given "
    "the tank moves for that long then stops on its own — prefer this.",
    {
        "type": "object",
        "properties": {
            "tank_id": {"type": "string", "description": "Tank UUID from list_tanks"},
            "action": {"type": "string",
                       "enum": ["forward", "backward", "turn_left", "turn_right"]},
            "speed": {"type": "integer", "minimum": 0, "maximum": 100},
            "duration_ms": {"type": "integer", "minimum": 1, "maximum": 30000,
                            "description": "Auto-stop after this many ms"},
        },
        "required": ["tank_id", "action"],
    },
)
def drive(tank_id: str, action: str, speed: int = 40, duration_ms: int | None = None) -> str:
    speed = _clamp_speed(speed)
    if duration_ms is not None:
        left, right = {
            "forward": (speed, speed),
            "backward": (-speed, -speed),
            "turn_left": (-speed, speed),
            "turn_right": (speed, -speed),
        }[action]
        kind = {"Move": {"Timed": {
            "left": left, "right": right, "duration_ms": int(duration_ms),
        }}}
    elif action in ("forward", "backward"):
        variant = "Forward" if action == "forward" else "Backward"
        kind = {"Move": {variant: {"speed": speed}}}
    else:
        direction = "Left" if action == "turn_left" else "Right"
        kind = {"Move": {"Turn": {"direction": direction, "speed": speed}}}
    return _send(tank_id, kind)


@server.tool(
    "stop",
    "Stop a tank immediately. Omit tank_id for an EMERGENCY STOP of the whole fleet.",
    {
        "type": "object",
        "properties": {
            "tank_id": {"type": "string", "description": "Tank UUID; omit to stop all"},
        },
    },
)
def stop(tank_id: str | None = None) -> str:
    if tank_id:
        return _send(tank_id, "Stop", priority=255, interrupt=True)
    return _http("POST", "/api/broadcast",
                 _command("Stop", priority=255, interrupt=True))


@server.tool(
    "camera_look",
    "Aim a tank's pan/tilt camera. Angles in degrees, -90 to +90; 0/0 is center.",
    {
        "type": "object",
        "properties": {
            "tank_id": {"type": "string"},
            "pan": {"type": "integer", "minimum": -90, "maximum": 90},
            "tilt": {"type": "integer", "minimum": -90, "maximum": 90},
        },
        "required": ["tank_id"],
    },
)
def camera_look(tank_id: str, pan: int = 0, tilt: int = 0) -> str:
    pan = max(-90, min(90, int(pan)))
    tilt = max(-90, min(90, int(tilt)))
    return _send(tank_id, {"Camera": {"Look": {"pan": pan, "tilt": tilt}}})


@server.tool(
    "camera_capture",
    "Ask a tank to capture a single camera frame (delivered on its video channel)",
    {
        "type": "object",
        "properties": {"tank_id": {"type": "string"}},
        "required": ["tank_id"],
    },
)
def camera_capture(tank_id: str) -> str:
    return _send(tank_id, {"Camera": "Capture"})


@server.tool(
    "led",
    "Control a tank's LED strip: solid color, blink, status indicator, or off",
    {
        "type": "object",
        "properties": {
            "tank_id": {"type": "string"},
            "mode": {"type": "string", "enum": ["solid", "blink", "status", "off"]},
            "r": {"type": "integer", "minimum": 0, "maximum": 255},
            "g": {"type": "integer", "minimum": 0, "maximum": 255},
            "b": {"type": "integer", "minimum": 0, "maximum": 255},
            "interval_ms": {"type": "integer", "minimum": 50},
            "status_level": {"type": "string",
                             "enum": ["Ok", "Busy", "Warning", "Error", "Alert"]},
        },
        "required": ["tank_id", "mode"],
    },
)
def led(tank_id: str, mode: str, r: int = 0, g: int = 255, b: int = 0,
        interval_ms: int = 500, status_level: str = "Ok") -> str:
    rgb = {"r": int(r) & 255, "g": int(g) & 255, "b": int(b) & 255}
    kind = {
        "solid": {"Led": {"Solid": rgb}},
        "blink": {"Led": {"Blink": {**rgb, "interval_ms": int(interval_ms)}}},
        "status": {"Led": {"Status": status_level}},
        "off": {"Led": "Off"},
    }[mode]
    return _send(tank_id, kind)


@server.tool(
    "set_mode",
    "Set a tank's operation mode",
    {
        "type": "object",
        "properties": {
            "tank_id": {"type": "string"},
            "mode": {"type": "string",
                     "enum": ["Manual", "Autonomous", "Coordinated",
                              "Standby", "EmergencyStop"]},
        },
        "required": ["tank_id", "mode"],
    },
)
def set_mode(tank_id: str, mode: str) -> str:
    return _send(tank_id, {"SetMode": mode})


@server.tool(
    "autonomy",
    "Start or stop autonomous behavior on a tank. Start modes: avoid "
    "(obstacle avoidance), explore, follow_person, return_home.",
    {
        "type": "object",
        "properties": {
            "tank_id": {"type": "string"},
            "action": {"type": "string", "enum": ["start", "stop"]},
            "mode": {"type": "string",
                     "enum": ["avoid", "explore", "follow_person", "return_home"]},
        },
        "required": ["tank_id", "action"],
    },
)
def autonomy(tank_id: str, action: str, mode: str = "avoid") -> str:
    if action == "stop":
        return _send(tank_id, "StopAutonomy", interrupt=True)
    variant = {
        "avoid": "Avoid",
        "explore": "Explore",
        "follow_person": "FollowPerson",
        "return_home": "ReturnHome",
    }[mode]
    return _send(tank_id, {"StartAutonomy": variant})


if __name__ == "__main__":
    server.run()
