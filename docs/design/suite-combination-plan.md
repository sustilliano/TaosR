# Non-destructive suite combination plan (planekey-derived)

The endgoal is a full-suite environment: taOS (`sustilliano/taosr`) + the
open-cowork desktop (`sustilliano/jcloudwork`) as one product. This plan is
grounded in a **pk-memory hash-tensor overlap matrix** of the two repos, so
the "non-destructive" claim is measured, not asserted.

## Evidence — pk-memory `memory matrix` (reports/suite-matrix.md)

Ran `pk-memory memory matrix` over both repos as two zip layers. Pairwise
overlap, jcloudwork ↔ taosr:

| Layer | Files | HTTP routes |
|-------|-------|-------------|
| taosr | 2131 | **1004** |
| jcloudwork | 404 | **0** |

| Overlap dimension | Value |
|-------------------|-------|
| content (exact sha256) | **0.000** |
| paths (filenames) | **0.000** |
| routes (HTTP surface) | **0.000** |
| rgano (structural) | 0.002 |
| shared content hashes | **0** |

The only "cross-layer" assets pk-memory found (8) are within-repo trivia —
jcloudwork's icon PNG variants and empty `__init__.py` files (the empty-file
hash). **Zero meaningful code, path, or route collision between the repos.**

## What the matrix means

The two projects are disjoint on every axis pk-memory measures. taOS is the
**server/platform** — it owns all 1004 HTTP routes, the agents, the bean
trust plane, the models. open-cowork is a **desktop client** — 0 routes,
Electron IPC, its own sandbox. They do not merge; they **compose**. So the
right combine is not a graft (pk-memory's `graft-plan` is for de-duping
multiple versions of the *same* files — inapplicable at 0.000 path overlap)
but a **composition overlay**: a thin layer that references both and wires
them, touching neither repo's internals.

This is the strongest possible non-destructive result: there is nothing to
overwrite.

## The combine: a suite overlay (touches neither repo's core)

```
taos-suite/                      ← new, thin overlay repo (or dir)
├── compose/                     ← brings up controller + workers
├── clients/
│   └── open-cowork/             ← installs jcloudwork; first-run auto-wire
├── wiring/                      ← already built, lives in taosr:
│   │                              integrations/open-cowork/
│   ├── provider → taOS LiteLLM (Hermes)         (config)
│   ├── MCP presets → taOS bridges               (merged in jcloudwork)
│   └── register-cowork-bean.sh  → app:open-cowork consent/provenance
└── suite.env                    ← one controller URL/token both sides read
```

- taOS stays canonical and unmodified beyond the thin, already-committed
  `integrations/open-cowork/` additions.
- jcloudwork stays canonical beyond the already-merged MCP presets.
- The overlay owns only orchestration + first-run wiring — additive, and
  removable without harming either repo.

## Graft actions (composition, per pk-memory's accept/review/quarantine idea)

| Target | Action | Why |
|--------|--------|-----|
| Both repos' source trees | **accept as-is** | 0.000 overlap — no conflict to resolve |
| Wiring artifacts (integrations/open-cowork/, MCP presets) | **already grafted** | committed, additive |
| Suite overlay (compose + first-run wire) | **add new** | the only net-new surface |
| The 8 pk-memory "cross-layer" dupes | **ignore** | empty files + icons, not code |

## Phasing

1. **Overlay skeleton** — a `taos-suite` repo/dir: compose for the
   controller, an installer step for open-cowork, and one `suite.env` both
   read.
2. **First-run auto-wire** — on suite up: write cowork's provider profile to
   the local taOS LiteLLM, install the taOS MCP presets pointed at the local
   controller, run `register-cowork-bean.sh`. Cowork boots bean-managed.
3. **One trust spine** — cowork's actions flow through `app:open-cowork` on
   the shared consent ledger; taOS remains the platform layer.
4. (Optional, harder) **cowork as a taOS desktop window** — needs taOS's
   container-app runtime + a servable cowork build; out of scope for the
   non-destructive overlay, tracked separately.

## Redo this analysis

```
# stage each repo's source as its own zip layer, then:
pk-memory memory matrix <folder-of-zips> --name taosr-vs-jcloudwork
# read matrix.md §2 (pairwise overlap) and §3 (cross-layer assets)
```
Re-run whenever either repo changes shape to confirm the combine stays
collision-free.
