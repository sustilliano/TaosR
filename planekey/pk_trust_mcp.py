#!/usr/bin/env python3
"""taOS planekey bridge: the trust work-loop + artifact memory as agent tools.

Gives every taOS agent the operating loop PlaneKey uses for humans:

    baseline snapshot -> scoped change -> compare -> report the delta

plus TMrFS artifact memory (lineage-aware file memory, distinct from
taosmd conversational memory — this remembers *artifacts and their
provenance*, taosmd remembers *what was said and learned*).

Shells out to the dependency-free Node toolchain from planekey-vse:
    toolchain/pk-client/bin/pk-client.js   snapshots, compare, scans
    toolchain/pk-memory/pk-memory.js       TMrFS build/query/lineage

Environment:
    PK_VSE_TOOLCHAIN  path to a planekey-vse/toolchain checkout
                      (default: ../planekey-vse/toolchain next to this repo)
    PK_WORKSPACE      pk-client workspace dir, auto-initialized on first
                      use (default: ~/.taos/pk-workspace)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "robotics"))
from mcp_stdio import McpStdioServer  # noqa: E402

TOOLCHAIN = os.environ.get(
    "PK_VSE_TOOLCHAIN",
    os.path.join(os.path.dirname(os.path.dirname(_HERE)), "planekey-vse", "toolchain"),
)
WORKSPACE = os.path.expanduser(
    os.environ.get("PK_WORKSPACE", "~/.taos/pk-workspace")
)

PK_CLIENT = os.path.join(TOOLCHAIN, "pk-client", "bin", "pk-client.js")
PK_MEMORY = os.path.join(TOOLCHAIN, "pk-memory", "pk-memory.js")

server = McpStdioServer("taos-pk-trust", "0.1.0")


def _run(script: str, args: list[str], timeout: int = 300) -> str:
    os.makedirs(WORKSPACE, exist_ok=True)
    proc = subprocess.run(
        ["node", script, *args],
        cwd=WORKSPACE, capture_output=True, text=True, timeout=timeout,
    )
    out = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0:
        raise RuntimeError(out or f"exit {proc.returncode}")
    return out


def _ensure_workspace() -> None:
    if not os.path.exists(os.path.join(WORKSPACE, "client.config.json")):
        _run(PK_CLIENT, ["init"])


@server.tool(
    "pk_snapshot",
    "Take a named baseline/after snapshot of a folder. Do this BEFORE and "
    "AFTER any batch of changes so the delta is provable.",
    {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Folder to snapshot"},
            "label": {"type": "string", "description": "Snapshot label, e.g. 'my-task-baseline'"},
        },
        "required": ["path", "label"],
    },
)
def pk_snapshot(path: str, label: str) -> str:
    _ensure_workspace()
    return _run(PK_CLIENT, ["import", path, "--name", label])


@server.tool(
    "pk_list_snapshots",
    "List snapshots in the trust workspace",
    {"type": "object", "properties": {}},
)
def pk_list_snapshots() -> str:
    _ensure_workspace()
    return _run(PK_CLIENT, ["list"])


@server.tool(
    "pk_compare",
    "Compare two snapshots (added/removed/changed files). Run after your "
    "after-snapshot and report the delta — it is the receipt for your work.",
    {
        "type": "object",
        "properties": {
            "before": {"type": "string", "description": "Baseline snapshot id or name"},
            "after": {"type": "string", "description": "After snapshot id or name"},
        },
        "required": ["before", "after"],
    },
)
def pk_compare(before: str, after: str) -> str:
    _ensure_workspace()
    return _run(PK_CLIENT, ["compare", before, after])


@server.tool(
    "pk_repoguard",
    "Scan a folder for secrets/private files before anything is published",
    {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
)
def pk_repoguard(path: str) -> str:
    _ensure_workspace()
    return _run(PK_CLIENT, ["repoguard", "scan", path])


@server.tool(
    "pk_memory_build",
    "Build a TMrFS artifact-memory index over a folder or zip: every file "
    "hashed, versioned, and lineage-tracked. This is artifact memory — use "
    "it to remember codebases/exports, not conversations.",
    {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Folder or zip to index"},
            "name": {"type": "string", "description": "Index name, e.g. 'taosr-canon'"},
        },
        "required": ["path", "name"],
    },
)
def pk_memory_build(path: str, name: str) -> str:
    return _run(PK_MEMORY,
                ["memory", "build", path, "--name", name,
                 "--out", os.path.join(WORKSPACE, "reports")],
                timeout=900)


@server.tool(
    "pk_memory_query",
    "Query an artifact-memory index for everything known about a file path",
    {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Index name from pk_memory_build"},
            "file_path": {"type": "string", "description": "File path to look up, e.g. server.js"},
        },
        "required": ["name", "file_path"],
    },
)
def pk_memory_query(name: str, file_path: str) -> str:
    report = os.path.join(WORKSPACE, "reports", "memory", name)
    return _run(PK_MEMORY, ["memory", "query", report, "--path", file_path])


@server.tool(
    "pk_memory_lineage",
    "Show the version lineage of a file across everything indexed — which "
    "copies exist, how they evolved, which is canonical",
    {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "file_path": {"type": "string"},
        },
        "required": ["name", "file_path"],
    },
)
def pk_memory_lineage(name: str, file_path: str) -> str:
    report = os.path.join(WORKSPACE, "reports", "memory", name)
    return _run(PK_MEMORY, ["memory", "lineage", report, "--path", file_path])


@server.tool(
    "pk_doctor",
    "Check that the planekey toolchain is reachable and report versions",
    {"type": "object", "properties": {}},
)
def pk_doctor() -> dict:
    status = {
        "toolchain": TOOLCHAIN,
        "workspace": WORKSPACE,
        "pk_client": os.path.exists(PK_CLIENT),
        "pk_memory": os.path.exists(PK_MEMORY),
    }
    if status["pk_client"]:
        try:
            status["pk_client_version"] = _run(
                PK_CLIENT, ["self", "version"], timeout=30
            ).splitlines()[0]
        except Exception as exc:
            status["pk_client_version"] = f"error: {exc}"
    return status


if __name__ == "__main__":
    server.run()
