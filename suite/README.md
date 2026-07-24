# taos-suite

The composition overlay that brings up **taOS** (server/platform) and
**open-cowork** (`sustilliano/jcloudwork`, the desktop client) as one
environment — without modifying either repo's core.

## How this was built (pk-client, from two separate projects)

This overlay was **derived with the planekey pk-client toolchain**, not
hand-guessed. Two independent repositories — `sustilliano/taosr` (a Python
self-hosted agent platform) and `sustilliano/jcloudwork` (a TypeScript/
Electron desktop app, forked from OpenCoworkAI's open-cowork) — were run
through `pk-memory memory matrix` (the hash-tensor overlap tool) as two
layers. The measured pairwise overlap was **0.000 content / 0.000 paths /
0.000 routes / 0 shared hashes**: the projects are disjoint on every axis
pk-client measures (taOS owns all 1004 HTTP routes; cowork owns 0).

That evidence is what makes this a *composition*, not a merge — there is
nothing to overwrite, so the combine is non-destructive by construction.
`graft-plan` (pk-client's same-file version-dedup planner) was inapplicable
at 0 path overlap. Full analysis + the raw matrix: `docs/design/
suite-combination-plan.md` and `reports/suite-matrix.md`. This overlay owns
only orchestration + first-run wiring across the two projects.

## Layout

```
suite/
├── suite.env.example   → copy to suite.env, edit (one controller both sides read)
├── compose/taos-up.sh  → verify/start the taOS controller
├── clients/open-cowork/
│   └── wire-cowork-mcp.sh → merge taOS MCP connectors into cowork (auto)
└── scripts/suite-up.sh → orchestrator: controller → MCP wire → bean register → provider hint
```

## Run

```bash
cd suite
cp suite.env.example suite.env      # edit: controller URL, local token, LLM key, bridge dir
./scripts/suite-up.sh
```

## What auto-wires vs. what's manual

| Piece | How | Why |
|-------|-----|-----|
| taOS controller | `compose/taos-up.sh` verifies/starts uvicorn :6969 | it's a service, not a container by default |
| cowork MCP connectors | **auto** — `wire-cowork-mcp.sh` writes `mcp-config.json` | that store is plain JSON |
| bean subject (`app:open-cowork`) | **auto** — `register-cowork-bean.sh` (curl) | controller API |
| model provider | **manual** — paste into cowork Settings | cowork's provider store is **encrypted** at rest; can't be safely written from outside |

## Result

open-cowork boots running on your self-hosted taOS Hermes, with the taOS
robot/camera/memory/trust tools as MCP connectors, governed as
`app:open-cowork` on the shared bean consent ledger — one environment, two
processes, neither repo's internals touched.

## Status (skeleton)

Phase-1 overlay. Functional: MCP wiring, bean registration, controller
verify/start. Documented-manual: the encrypted provider config. Not yet
built: packaging into a single installer, and (separate, harder track)
cowork-as-a-taOS-desktop-window.
