# AGENTS.md — how to work in this repo

This applies to every agent working here: Claude Code sessions, taOS
agents, anything else. It is the **planekey work loop**, and it is the
default operating contract, not a suggestion.

## The work loop

1. **Baseline first.** Before a batch of changes, snapshot the tree
   (`pk-client import <path> --name <task>-baseline`, or the
   `pk_snapshot` tool from the pk-trust-mcp plugin). If you find a bug
   in a tool you need, fix the tool first and say so.
2. **Scoped, additive change.** Prefer new files and new modules over
   edits to shipped code. Touch existing files only when the task
   demands it. Match surrounding style; stdlib-only for anything that
   must run on small workers.
3. **Prove it works.** Tests for new behavior, run before commit. A
   smoke test over the real transport beats a mock when it's cheap.
4. **After-snapshot + compare.** Snapshot again, run
   `pk-client compare <baseline> <after>`. The added/removed/changed
   counts are the receipt for your work — report them. A clean feature
   lands as "N added / 0 removed / 0 changed".
5. **Scan before anything leaves the machine.** `repoguard scan` before
   pushing or publishing; call out hits and whether they're real.
6. **Report the delta, not the journey.** Lead with what shipped and
   the compare counts; flag anything you could not verify (e.g. an
   attestation that needs a human-held secret).

## Memory tiers

- **taosmd** — conversational memory: what was said, learned, decided.
- **TMrFS (pk-memory)** — artifact memory: what files exist, their
  hashes, versions, and lineage. Build with `pk_memory_build`, query
  with `pk_memory_query` / `pk_memory_lineage`.
- **pk-client snapshots** — trust memory: point-in-time tree states and
  provable deltas between them.

Use the right tier: "what did we decide" → taosmd; "where did this
file come from and which copy is canonical" → TMrFS; "what changed
while I worked" → snapshots.

## Repo specifics

- Backend: `tinyagentos/` (Python 3.11+, FastAPI). Frontend: `desktop/`.
- Robotics bridges: `robotics/` (stdlib-only MCP stdio servers; see
  `docs/robotics-edition.md`).
- PlaneKey bridge: `planekey/pk_trust_mcp.py` (needs Node >= 18 and a
  planekey-vse checkout via `PK_VSE_TOOLCHAIN`).
- Plugin manifests: `app-catalog/plugins/<id>/manifest.yaml`; local
  servers launch via `lifecycle.start` (see `tinyagentos/mcp/supervisor.py`).
- Standalone test dirs (`tests/robotics/`, `tests/planekey/`) run
  without the backend venv:
  `pytest tests/robotics/ --confcutdir=tests/robotics`.
