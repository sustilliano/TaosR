# taos-suite

The composition overlay that brings up **taOS** (server/platform) and
**open-cowork** (`sustilliano/jcloudwork`, the desktop client) as one
environment — without modifying either repo's core.

This is the non-destructive combine proven safe by the pk-memory overlap
matrix (`docs/design/suite-combination-plan.md`): the two repos share
**0.000 content / 0.000 paths / 0.000 routes**, so they *compose* rather than
merge. This overlay owns only orchestration + first-run wiring.

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
