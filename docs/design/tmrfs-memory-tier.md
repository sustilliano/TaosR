# TMrFS as a taOS memory tier

Realizes the artifact/tensor memory tier from `pk-memory-backend.md`:
gives taOS agents a **tensor-memory** plane backed by TMrFS (Tensor
Memory Recursive Fractal System), alongside taosmd.

## The three memory planes, now all reachable

| Plane | Engine | Question | Surface |
|-------|--------|----------|---------|
| Conversational | taosmd | "what was said/decided?" | native |
| Tensor / thought | **TMrFS** | "what durable ideas relate to X, by memory score?" | `tmrfs-memory` plugin (this) |
| Trust / artifact | pk-client + pk-memory | "what changed / where did this file come from?" | `pk-trust-mcp` plugin |

taosmd stays the default. TMrFS is opt-in per agent (attach the plugin),
for durable "thoughts" that decay, link into a knowledge graph, and are
recalled by concept + memory score — distinct from transcript recall.

## What shipped (v0.1)

A stdlib-only MCP stdio bridge, same pattern as the robotics and pk-trust
bridges, so it runs on any worker with no venv:

- `tmrfs/tmrfs_memory_mcp.py` — tools `tmrfs_store`, `tmrfs_query`,
  `tmrfs_link`, `tmrfs_status`, backed by the TMrFS HTTP bridge
  (`tmrfs-python web/localai_bridge.py`: `/tmrfs/store|query|link`).
- `app-catalog/plugins/tmrfs-memory/manifest.yaml` — launches it via
  `lifecycle.start`; `TAOS_TMRFS_URL` points at the running bridge.
- Per-agent namespacing via `TAOS_TMRFS_AGENT` so one TMrFS instance can
  hold many agents' memories without name collisions.

## Architecture

```
taOS agent (any framework)
      │  MCP: tmrfs_store / tmrfs_query / tmrfs_link
      ▼
tmrfs-memory bridge (stdlib, on the worker)
      │  HTTP  TAOS_TMRFS_URL
      ▼
TMrFS bridge (tmrfs-python) ── 99-D vectors, decay, links, memory score
```

The bridge is a thin, dependency-free HTTP client. TMrFS itself (HDF5
tensor store, decay, K-SNE, knowledge graph) stays a separate service —
taOS integrates at the API boundary, not by vendoring TMrFS.

## Roadmap

- **Deploy-wizard tier**: expose "memory systems" as a multi-select
  (taosmd default + TMrFS), auto-setting `TAOS_TMRFS_AGENT` to the agent
  slug so memories are namespaced without manual config.
- **Auto-capture**: mirror salient agent turns into TMrFS as thoughts
  (a callback like Bean-1's, but writing memories instead of receipts),
  so recall improves without the agent explicitly calling `tmrfs_store`.
- **Cross-tier link**: an inference receipt (Bean-1) or an action receipt
  could carry a TMrFS thought id, linking "what the model did" to "what
  it was thinking about" — the two planes referencing each other.
- **Semantic query**: the bridge's `tmrfs_query` currently rides TMrFS's
  keyword+score path; wire it to `conversation/vector_storage.py` for
  true vector search when the bridge exposes it.

## Licensing

TMrFS is AGPL-3.0. taOS talks to it over HTTP only (no vendored code),
so the boundary stays clean — same posture as the pk-trust bridge.
