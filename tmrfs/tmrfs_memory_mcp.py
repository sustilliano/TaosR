#!/usr/bin/env python3
"""taOS memory tier: TMrFS (Tensor Memory Recursive Fractal System) bridge.

Gives taOS agents a tensor-memory tier alongside taosmd — the "artifact /
tensor memory" plane from docs/design/pk-memory-backend.md. Where taosmd
remembers conversation ("what was said/decided") and pk-client snapshots
remember trees ("what changed"), TMrFS remembers *thoughts as vectors*:
each memory is stored as a 99-D personality vector, decays over time,
links to related thoughts, and is retrieved by concept + memory score.

Backed by the TMrFS HTTP bridge (tmrfs-python web/localai_bridge.py):
    POST /tmrfs/store  {name, text, metadata?}    -> {success, name, vector_shape}
    POST /tmrfs/query  {concept, max_thoughts}    -> {success, count, thoughts:[{name,score}]}
    POST /tmrfs/link   {source, target, strength} -> {success, ...}

Environment:
    TAOS_TMRFS_URL   base URL of the TMrFS bridge (default http://localhost:8080)
    TAOS_TMRFS_AGENT default thought-name prefix, so one TMrFS instance can
                     hold many agents' memories without collision
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "robotics"))
from mcp_stdio import McpStdioServer  # noqa: E402

TMRFS_URL = os.environ.get("TAOS_TMRFS_URL", "http://localhost:8080").rstrip("/")
AGENT_PREFIX = os.environ.get("TAOS_TMRFS_AGENT", "").strip()

server = McpStdioServer("taos-tmrfs-memory", "0.1.0")


def _http(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        TMRFS_URL + path,
        method="POST",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _scoped(name: str) -> str:
    """Namespace a thought under the configured agent prefix (if any)."""
    if AGENT_PREFIX and not name.startswith(f"{AGENT_PREFIX}:"):
        return f"{AGENT_PREFIX}:{name}"
    return name


@server.tool(
    "tmrfs_store",
    "Store a memory in the TMrFS tensor-memory tier. The text is encoded to "
    "a 99-D vector; give it a short stable name so you can link/recall it. "
    "Use for durable, decaying 'thoughts' — not conversation transcript.",
    {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Short stable id for this memory"},
            "text": {"type": "string", "description": "The memory content to encode"},
            "metadata": {"type": "object", "description": "Optional structured tags"},
        },
        "required": ["name", "text"],
    },
)
def tmrfs_store(name: str, text: str, metadata: dict | None = None) -> dict:
    return _http("/tmrfs/store", {
        "name": _scoped(name), "text": text, "metadata": metadata or {},
    })


@server.tool(
    "tmrfs_query",
    "Recall memories related to a concept from the TMrFS tier, ranked by "
    "memory score (usage/recency/relevance). Returns thought names + scores.",
    {
        "type": "object",
        "properties": {
            "concept": {"type": "string", "description": "What to recall about"},
            "max_thoughts": {"type": "integer", "minimum": 1, "maximum": 100},
        },
        "required": ["concept"],
    },
)
def tmrfs_query(concept: str, max_thoughts: int = 10) -> dict:
    return _http("/tmrfs/query", {
        "concept": concept, "max_thoughts": max(1, min(100, int(max_thoughts))),
    })


@server.tool(
    "tmrfs_link",
    "Link two stored memories so recall traverses between them "
    "(strength 0..1). Use to build a knowledge graph of related thoughts.",
    {
        "type": "object",
        "properties": {
            "source": {"type": "string"},
            "target": {"type": "string"},
            "strength": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["source", "target"],
    },
)
def tmrfs_link(source: str, target: str, strength: float = 1.0) -> dict:
    return _http("/tmrfs/link", {
        "source": _scoped(source), "target": _scoped(target),
        "strength": max(0.0, min(1.0, float(strength))),
    })


@server.tool(
    "tmrfs_status",
    "Check the TMrFS memory bridge is reachable and report the endpoint",
    {"type": "object", "properties": {}},
)
def tmrfs_status() -> dict:
    try:
        # A benign query doubles as a reachability probe.
        res = _http("/tmrfs/query", {"concept": "__ping__", "max_thoughts": 1})
        return {"url": TMRFS_URL, "reachable": True,
                "agent_prefix": AGENT_PREFIX or None, "probe_ok": bool(res.get("success"))}
    except Exception as exc:
        return {"url": TMRFS_URL, "reachable": False, "error": str(exc)}


if __name__ == "__main__":
    server.run()
