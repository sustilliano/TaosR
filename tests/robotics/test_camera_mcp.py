"""Tests for the Thingino/Cinnado camera MCP bridge."""
import base64
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROBOTICS = Path(__file__).resolve().parents[2] / "robotics"

JPEG = b"\xff\xd8\xff\xe0" + b"fakejpegdata"


@pytest.fixture()
def bridge(monkeypatch):
    monkeypatch.setenv("TAOS_CAMERAS", json.dumps([
        {"name": "garage", "host": "192.168.1.64"},
        {"name": "porch", "host": "192.168.1.65", "user": "root",
         "password": "pw", "rtsp_path": "/ch1"},
    ]))
    spec = importlib.util.spec_from_file_location(
        "camera_mcp_under_test", ROBOTICS / "camera_mcp.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    fetches = []

    def fake_fetch(cam, path_and_query):
        fetches.append({"cam": cam, "path": path_and_query})
        return JPEG

    monkeypatch.setattr(mod, "_fetch", fake_fetch)
    mod._test_fetches = fetches
    yield mod
    sys.modules.pop("camera_mcp_under_test", None)


def call_tool(mod, name, arguments=None):
    resp = mod.server.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    })
    assert "error" not in resp, resp
    return resp["result"]


def test_list_cameras_reports_rtsp_urls(bridge):
    result = call_tool(bridge, "list_cameras")
    listing = json.loads(result["content"][0]["text"])
    assert listing["garage"]["rtsp_url"] == "rtsp://192.168.1.64:554/ch0"
    assert listing["porch"]["rtsp_url"] == "rtsp://192.168.1.65:554/ch1"


def test_snapshot_returns_image_content(bridge):
    result = call_tool(bridge, "snapshot", {"camera": "garage"})
    block = result["content"][0]
    assert block["type"] == "image"
    assert block["mimeType"] == "image/jpeg"
    assert base64.b64decode(block["data"]) == JPEG
    assert bridge._test_fetches[-1]["path"] == "/image.jpg"


def test_ptz_move_hits_thingino_endpoint(bridge):
    call_tool(bridge, "ptz_move",
              {"camera": "porch", "mode": "rel", "pan": -5, "tilt": 2})
    path = bridge._test_fetches[-1]["path"]
    assert path.startswith("/ptz?")
    assert "cmd=move_rel" in path and "pan=-5" in path and "tilt=2" in path


def test_unknown_camera_is_tool_error(bridge):
    resp = bridge.server.handle_request({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "snapshot", "arguments": {"camera": "attic"}},
    })
    assert resp["result"]["isError"] is True
    assert "attic" in resp["result"]["content"][0]["text"]
