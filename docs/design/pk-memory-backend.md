# PlaneKey memory as a taOS memory-system option

Status: proposal + phase 1 shipped
Author: robotics-edition fork

## Why

taosmd answers "what was said, learned, decided" — conversational
memory. It has no opinion about *artifacts*: which files an agent
produced, where a file came from, which of five copies is canonical,
or what provably changed while an agent worked.

PlaneKey already solves that axis with two dependency-free Node tools
(planekey-vse `toolchain/`):

- **pk-memory (TMrFS + Rgano)** — persistent artifact-memory indexes:
  every file hashed and versioned, lineage across archives, canon
  ranking, structural pattern scoring.
- **pk-client** — workspace snapshots with provable compare
  (added/removed/changed), secret scanning, layer attestation.

An agent session run with this loop (baseline snapshot → scoped change
→ compare → report delta) produced a clean, auditable "18 added /
0 removed / 0 changed" receipt for the entire robotics edition. That
loop should be how taOS agents work by default, and its artifacts are
a memory tier taosmd cannot provide.

## Memory tiers

| Tier | Engine | Question it answers |
|------|--------|---------------------|
| Conversational | taosmd | "What did we discuss/decide/learn?" |
| Artifact | pk-memory (TMrFS) | "What is this file, where did it come from, which copy is canon?" |
| Trust | pk-client snapshots | "What exactly changed while the agent worked?" |

## Phase 1 — shipped: pk-trust-mcp plugin

`planekey/pk_trust_mcp.py` + `app-catalog/plugins/pk-trust-mcp/`.
Any agent framework gets the loop as tools: `pk_snapshot`,
`pk_compare`, `pk_repoguard`, `pk_memory_build`, `pk_memory_query`,
`pk_memory_lineage`, `pk_doctor`. AGENTS.md makes the loop the
repo's operating contract.

## Phase 2 — artifact memory per agent

Mirror the taosmd layout: alongside
`data/agent-memory/{name}/index.sqlite` (taosmd), add
`data/agent-memory/{name}/artifacts/` holding that agent's TMrFS
indexes and snapshot workspace. Deploy wizard gains a "memory systems"
multi-select: taosmd (default) + planekey artifact memory. The agent's
file store becomes automatically indexed memory: a nightly (or
post-task) `pk-memory memory build` over the agent's storage, queryable
through the same adapter layer that already translates taosmd across
the 17 frameworks.

## Phase 3 — the loop in the orchestrator

`app_orchestrator` + `receipts.py` integration: when an agent task
starts, the orchestrator takes the baseline snapshot of the agent's
writable scope; on completion it takes the after-snapshot, runs
compare, and attaches the added/removed/changed receipt to the task
record. Repoguard runs before any channel/publish action. Layer
attestation stays human-keyed (`PLANEKEY_INDEX_SECRET`) — agents
produce the evidence, humans sign it.

## Non-goals

- Replacing taosmd. The tiers are complementary; retrieval-style
  memory stays taosmd's job.
- Rewriting the Node tools in Python. They are dependency-free and
  stable; the bridge shells out.

## Open questions

- Node runtime on LXC agent containers (present on controller;
  workers may need `nodejs` added to the container profile).
- Snapshot storage growth — pk-client stores full file copies per
  snapshot; needs a retention policy (keep last N + all attested).
- Whether Phase 3 receipts should feed RiskSignals (uknocked) when
  compare shows unexpected removals/changes.
