"""Tests for the TMrFS tensor-memory MCP bridge.

Drives McpStdioServer.handle_request directly and stubs the HTTP layer, so
no running TMrFS bridge is needed.
"""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

TMRFS = Path(__file__).resolve().parents[2] / "tmrfs"


def _load(monkeypatch, *, prefix=""):
    monkeypatch.setenv("TAOS_TMRFS_URL", "http://tmrfs.test:8080")
    if prefix:
        monkeypatch.setenv("TAOS_TMRFS_AGENT", prefix)
    else:
        monkeypatch.delenv("TAOS_TMRFS_AGENT", raising=False)
    spec = importlib.util.spec_from_file_location(
        "tmrfs_memory_under_test", TMRFS / "tmrfs_memory_mcp.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    calls = []

    def fake_http(path, body):
        calls.append({"path": path, "body": body})
        if path == "/tmrfs/store":
            return {"success": True, "name": body["name"], "vector_shape": [99]}
        if path == "/tmrfs/query":
            return {"success": True, "concept": body["concept"], "count": 1,
                    "thoughts": [{"name": "t1", "score": 0.9}]}
        return {"success": True}

    monkeypatch.setattr(mod, "_http", fake_http)
    mod._calls = calls
    return mod


@pytest.fixture
def bridge(monkeypatch):
    mod = _load(monkeypatch)
    yield mod
    sys.modules.pop("tmrfs_memory_under_test", None)


def call(mod, name, args=None):
    resp = mod.server.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": args or {}},
    })
    assert "error" not in resp, resp
    return resp["result"]


def test_tool_listing(bridge):
    resp = bridge.server.handle_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )
    names = {t["name"] for t in resp["result"]["tools"]}
    assert {"tmrfs_store", "tmrfs_query", "tmrfs_link", "tmrfs_status"} <= names


def test_store_posts_text_and_metadata(bridge):
    call(bridge, "tmrfs_store", {"name": "m1", "text": "the tank patrols at dawn",
                                 "metadata": {"topic": "patrol"}})
    c = bridge._calls[-1]
    assert c["path"] == "/tmrfs/store"
    assert c["body"]["name"] == "m1"
    assert c["body"]["text"] == "the tank patrols at dawn"
    assert c["body"]["metadata"] == {"topic": "patrol"}


def test_query_clamps_max_thoughts(bridge):
    call(bridge, "tmrfs_query", {"concept": "patrol", "max_thoughts": 999})
    assert bridge._calls[-1]["body"]["max_thoughts"] == 100


def test_link_clamps_strength(bridge):
    call(bridge, "tmrfs_link", {"source": "a", "target": "b", "strength": 5})
    body = bridge._calls[-1]["body"]
    assert body["strength"] == 1.0
    assert body["source"] == "a" and body["target"] == "b"


def test_agent_prefix_namespaces_thoughts(monkeypatch):
    mod = _load(monkeypatch, prefix="scout-1")
    try:
        call(mod, "tmrfs_store", {"name": "m1", "text": "x"})
        assert mod._calls[-1]["body"]["name"] == "scout-1:m1"
        # Already-prefixed names are not double-prefixed.
        call(mod, "tmrfs_link", {"source": "scout-1:m1", "target": "m2"})
        b = mod._calls[-1]["body"]
        assert b["source"] == "scout-1:m1" and b["target"] == "scout-1:m2"
    finally:
        sys.modules.pop("tmrfs_memory_under_test", None)


def test_status_reachable(bridge):
    res = call(bridge, "tmrfs_status")
    import json
    payload = json.loads(res["content"][0]["text"])
    assert payload["reachable"] is True
    assert payload["url"] == "http://tmrfs.test:8080"


def test_http_error_surfaces_as_tool_error(bridge, monkeypatch):
    def boom(path, body):
        raise OSError("tmrfs bridge down")

    monkeypatch.setattr(bridge, "_http", boom)
    resp = bridge.server.handle_request({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "tmrfs_store", "arguments": {"name": "m", "text": "t"}},
    })
    assert resp["result"]["isError"] is True
    assert "tmrfs bridge down" in resp["result"]["content"][0]["text"]
