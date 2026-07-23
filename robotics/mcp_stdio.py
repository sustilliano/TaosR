"""Minimal MCP stdio server scaffolding, stdlib only.

Speaks newline-delimited JSON-RPC 2.0 over stdin/stdout per the MCP stdio
transport. Robotics bridges stay dependency-free so they run on any worker
(Pi Zero 2W included) without a venv or the `mcp` package installed.

Usage:
    server = McpStdioServer("taos-tank-fleet", "0.1.0")

    @server.tool(
        "drive",
        "Drive a tank forward/backward or turn in place",
        {"type": "object", "properties": {...}, "required": [...]},
    )
    def drive(tank_id: str, action: str, speed: int = 40) -> str:
        ...

    server.run()

Tool handlers may return:
    str                     -> single text content block
    (bytes, "image/jpeg")   -> single image content block (base64-encoded)
    dict                    -> JSON-serialized as a text content block
    a full {"content": [...]} dict -> passed through untouched
Raising an exception produces an isError tool result, not a protocol error.
"""
from __future__ import annotations

import base64
import json
import sys
import traceback

PROTOCOL_VERSION = "2025-06-18"


class McpStdioServer:
    def __init__(self, name: str, version: str) -> None:
        self.name = name
        self.version = version
        self._tools: dict = {}

    def tool(self, name: str, description: str, input_schema: dict):
        def register(fn):
            self._tools[name] = {
                "fn": fn,
                "spec": {
                    "name": name,
                    "description": description,
                    "inputSchema": input_schema,
                },
            }
            return fn

        return register

    # --- protocol handling ---

    def handle_request(self, req: dict) -> dict | None:
        """Handle one JSON-RPC message; returns the response dict or None
        for notifications. Separated from run() so tests can drive it
        directly without subprocess plumbing."""
        method = req.get("method", "")
        req_id = req.get("id")

        if method.startswith("notifications/"):
            return None

        if method == "initialize":
            client_version = (req.get("params") or {}).get(
                "protocolVersion", PROTOCOL_VERSION
            )
            return self._result(req_id, {
                "protocolVersion": client_version,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": self.name, "version": self.version},
            })

        if method == "ping":
            return self._result(req_id, {})

        if method == "tools/list":
            return self._result(req_id, {
                "tools": [t["spec"] for t in self._tools.values()],
            })

        if method == "tools/call":
            params = req.get("params") or {}
            tool_name = params.get("name")
            tool = self._tools.get(tool_name)
            if tool is None:
                return self._error(req_id, -32602, f"Unknown tool: {tool_name}")
            try:
                raw = tool["fn"](**(params.get("arguments") or {}))
            except Exception as exc:  # tool failure -> isError result
                return self._result(req_id, {
                    "content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}],
                    "isError": True,
                })
            return self._result(req_id, self._to_tool_result(raw))

        if req_id is not None:
            return self._error(req_id, -32601, f"Method not found: {method}")
        return None

    @staticmethod
    def _to_tool_result(raw) -> dict:
        if isinstance(raw, dict) and "content" in raw:
            return raw
        if isinstance(raw, tuple) and len(raw) == 2 and isinstance(raw[0], bytes):
            data, mime = raw
            return {"content": [{
                "type": "image",
                "data": base64.b64encode(data).decode("ascii"),
                "mimeType": mime,
            }]}
        if isinstance(raw, (dict, list)):
            text = json.dumps(raw, indent=2)
        else:
            text = str(raw)
        return {"content": [{"type": "text", "text": text}]}

    @staticmethod
    def _result(req_id, result: dict) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    @staticmethod
    def _error(req_id, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": req_id,
                "error": {"code": code, "message": message}}

    def run(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                resp = self.handle_request(req)
            except Exception:
                traceback.print_exc(file=sys.stderr)
                resp = self._error(req.get("id"), -32603, "internal error")
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
