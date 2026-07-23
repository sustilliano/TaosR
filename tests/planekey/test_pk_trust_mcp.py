"""Tests for the planekey trust-loop MCP bridge.

Stubs subprocess execution; verifies tool wiring and argv shapes.
Run standalone: pytest tests/planekey/ --confcutdir=tests/planekey
"""
import importlib.util
import sys
from pathlib import Path

import pytest

PLANEKEY = Path(__file__).resolve().parents[2] / "planekey"


@pytest.fixture()
def bridge(monkeypatch, tmp_path):
    monkeypatch.setenv("PK_WORKSPACE", str(tmp_path / "pkws"))
    spec = importlib.util.spec_from_file_location(
        "pk_trust_mcp_under_test", PLANEKEY / "pk_trust_mcp.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    runs = []

    def fake_run(script, args, timeout=300):
        runs.append({"script": script, "args": args})
        return "ok"

    monkeypatch.setattr(mod, "_run", fake_run)
    monkeypatch.setattr(mod, "_ensure_workspace", lambda: None)
    mod._test_runs = runs
    yield mod
    sys.modules.pop("pk_trust_mcp_under_test", None)


def call_tool(mod, name, arguments=None):
    resp = mod.server.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    })
    assert "error" not in resp, resp
    return resp["result"]


def test_tool_listing_covers_loop_and_memory(bridge):
    resp = bridge.server.handle_request(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )
    names = {t["name"] for t in resp["result"]["tools"]}
    assert {"pk_snapshot", "pk_compare", "pk_repoguard",
            "pk_memory_build", "pk_memory_query", "pk_memory_lineage",
            "pk_doctor"} <= names


def test_snapshot_and_compare_argv(bridge):
    call_tool(bridge, "pk_snapshot", {"path": "/x", "label": "t-baseline"})
    assert bridge._test_runs[-1]["args"] == [
        "import", "/x", "--name", "t-baseline"]
    assert bridge._test_runs[-1]["script"] == bridge.PK_CLIENT

    call_tool(bridge, "pk_compare", {"before": "a", "after": "b"})
    assert bridge._test_runs[-1]["args"] == ["compare", "a", "b"]


def test_memory_tools_target_pk_memory_reports(bridge):
    call_tool(bridge, "pk_memory_build", {"path": "/x", "name": "canon"})
    run = bridge._test_runs[-1]
    assert run["script"] == bridge.PK_MEMORY
    assert run["args"][:4] == ["memory", "build", "/x", "--name"]

    call_tool(bridge, "pk_memory_lineage",
              {"name": "canon", "file_path": "server.js"})
    run = bridge._test_runs[-1]
    assert run["args"][0:2] == ["memory", "lineage"]
    assert run["args"][1] == "lineage"
    assert run["args"][-2:] == ["--path", "server.js"]
    assert "canon" in run["args"][2]


def test_run_failure_surfaces_as_tool_error(bridge, monkeypatch):
    def boom(script, args, timeout=300):
        raise RuntimeError("node not found")

    monkeypatch.setattr(bridge, "_run", boom)
    resp = bridge.server.handle_request({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "pk_list_snapshots", "arguments": {}},
    })
    assert resp["result"]["isError"] is True
    assert "node not found" in resp["result"]["content"][0]["text"]
