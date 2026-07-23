#!/usr/bin/env python3
"""taOS robotics: IP camera MCP bridge for Thingino/Cinnado cameras.

Gives taOS agents eyes: snapshot (returned inline as an MCP image block),
pan/tilt control, and camera inventory for Thingino-firmware cameras
(e.g. Cinnado D1 flashed with thingino.com firmware).

Thingino HTTP endpoints used:
    GET /image.jpg                          JPEG snapshot
    GET /ptz?cmd=move&pan=P&tilt=T          absolute PTZ move
    GET /ptz?cmd=move_rel&pan=dP&tilt=dT    relative PTZ move

Environment:
    TAOS_CAMERAS       inline JSON list of camera objects (takes precedence)
    TAOS_CAMERAS_FILE  path to a JSON file with the same list

Camera object fields (only "name" and "host" are required):
    {"name": "garage", "host": "192.168.1.64", "user": "root",
     "password": "...", "snapshot_path": "/image.jpg",
     "rtsp_port": 554, "rtsp_path": "/ch0"}
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_stdio import McpStdioServer  # noqa: E402

server = McpStdioServer("taos-cameras", "0.1.0")


def _load_cameras() -> dict[str, dict]:
    raw = os.environ.get("TAOS_CAMERAS")
    if not raw:
        path = os.environ.get("TAOS_CAMERAS_FILE")
        if path and os.path.exists(path):
            with open(path) as fh:
                raw = fh.read()
    cameras = json.loads(raw) if raw else []
    return {c["name"]: c for c in cameras}


CAMERAS = _load_cameras()


def _camera(name: str) -> dict:
    cam = CAMERAS.get(name)
    if cam is None:
        raise ValueError(
            f"Unknown camera {name!r}; configured: {sorted(CAMERAS) or 'none'}"
        )
    return cam


def _fetch(cam: dict, path_and_query: str) -> bytes:
    url = f"http://{cam['host']}{path_and_query}"
    req = urllib.request.Request(url)
    user = cam.get("user")
    if user:
        token = base64.b64encode(
            f"{user}:{cam.get('password', '')}".encode()
        ).decode("ascii")
        req.add_header("Authorization", f"Basic {token}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()


def _rtsp_url(cam: dict) -> str:
    port = cam.get("rtsp_port", 554)
    path = cam.get("rtsp_path", "/ch0")
    return f"rtsp://{cam['host']}:{port}{path}"


@server.tool(
    "list_cameras",
    "List configured IP cameras with their RTSP stream URLs",
    {"type": "object", "properties": {}},
)
def list_cameras() -> dict:
    return {
        name: {
            "host": cam["host"],
            "rtsp_url": _rtsp_url(cam),
            "ptz": cam.get("ptz", True),
        }
        for name, cam in CAMERAS.items()
    }


@server.tool(
    "snapshot",
    "Capture a JPEG snapshot from a camera and return it as an image",
    {
        "type": "object",
        "properties": {
            "camera": {"type": "string", "description": "Camera name from list_cameras"},
        },
        "required": ["camera"],
    },
)
def snapshot(camera: str):
    cam = _camera(camera)
    data = _fetch(cam, cam.get("snapshot_path", "/image.jpg"))
    return (data, "image/jpeg")


@server.tool(
    "ptz_move",
    "Pan/tilt a camera. mode=abs sets absolute angles, mode=rel nudges "
    "relative to the current position. Degrees.",
    {
        "type": "object",
        "properties": {
            "camera": {"type": "string"},
            "mode": {"type": "string", "enum": ["abs", "rel"]},
            "pan": {"type": "number"},
            "tilt": {"type": "number"},
        },
        "required": ["camera", "mode"],
    },
)
def ptz_move(camera: str, mode: str, pan: float = 0, tilt: float = 0) -> str:
    cam = _camera(camera)
    cmd = "move" if mode == "abs" else "move_rel"
    query = urllib.parse.urlencode({"cmd": cmd, "pan": pan, "tilt": tilt})
    _fetch(cam, f"/ptz?{query}")
    return f"{camera}: ptz {mode} pan={pan} tilt={tilt} ok"


if __name__ == "__main__":
    server.run()
