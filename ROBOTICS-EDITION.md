# taOS — Robotics Edition (this fork)

`sustilliano/taosr`, branch **`robotics-edition`**. This is a fork of taOS
with three things upstream doesn't have, all built on top of beta.43:

1. **Silicon-bean trust stack** (Bean-0…5) — every agent is an attested
   individual: provenance, signed hash-only inference receipts,
   consent-gated actuation, a cognitive firewall, and an offline
   attestation walk.
2. **Three-plane memory** — taosmd (conversational) + TMrFS (tensor/thought)
   + pk-trust (artifact/snapshots), selectable per agent at deploy.
3. **Robotics bridges** — drive a tank fleet and see through IP cameras
   from any agent framework, over MCP.

Plus the beta.44 provider/infra wins we adopted (Nous Portal, etc.) and an
"all-digital" consent spine that unifies agent and app permission.

> This doc is the **run guide** for the fork's additions. For the base
> platform (desktop shell, clustering, frameworks) see the upstream
> `README.md`.

---

## 0. Base platform (once)

The controller + workers are stock taOS. Installers still point at the
upstream URL; to run **this fork**, clone it and run from source:

```bash
git clone -b robotics-edition https://github.com/sustilliano/taosr ~/tinyagentos
cd ~/tinyagentos
python -m venv .venv && . .venv/bin/activate
pip install -e .
python -m uvicorn tinyagentos.app:create_app --factory --host 0.0.0.0 --port 6969
```

Open `http://your-host:6969/` for the desktop shell. Workers:
`tinyagentos-worker http://your-server:6969`. Ports: **6969** API/UI,
**7832** embeddings (qmd), **4000** LiteLLM proxy (localhost).

---

## 1. Deploy an agent with memory planes

In the desktop **Deploy Wizard**, the memory step now has a
**memory-systems** selector:

- **taosmd** — always on (conversational memory).
- **tmrfs** — tensor/thought memory; the deployer auto-sets
  `TAOS_TMRFS_AGENT=<agent-slug>` so the agent's thoughts are namespaced,
  and best-effort attaches the `tmrfs-memory` plugin.
- **pk-trust** — artifact/snapshot memory; attaches `pk-trust-mcp`.

Or via API: `POST /api/agents/deploy` with `"memory_systems": ["taosmd","tmrfs"]`.

For **Nous-hosted Hermes** models, add the **Nous** provider in the
Providers app (base URL `https://inference-api.nousresearch.com/v1`) — this
completes the Bean-0 chain for the Hermes 4 family.

---

## 2. Robotics bridges

Two stdlib-only MCP plugins under `robotics/` (run on any worker, no venv).

**Tank fleet** — start the tank-agents coordinator (separate repo,
`projects/tank-agents`) on the cluster:

```bash
TANK_PORT=8420 cargo run --release      # in tank-agents/src/cluster
```

Install the `tank-fleet-mcp` plugin and attach it to an agent. Env:
`TAOS_TANK_COORDINATOR_URL` (default `http://localhost:8420`),
`TAOS_TANK_MAX_SPEED` (default 70 — every drive is clamped to this). Tools:
`list_tanks`, `drive`, `stop` (omit tank_id = fleet-wide emergency stop),
`camera_look`, `led`, `set_mode`, `autonomy`.

**IP cameras** (Thingino/Cinnado) — install `taos-camera-mcp`, point
`TAOS_CAMERAS_FILE` at a JSON list:

```json
[{"name":"garage","host":"192.168.1.64"},
 {"name":"porch","host":"192.168.1.65","user":"root","password":"…"}]
```

Tools: `list_cameras`, `snapshot` (returns the JPEG inline), `ptz_move`.

See `docs/robotics-edition.md`.

---

## 3. The bean trust stack (per-agent APIs + CLI)

All under `/api/agents/{name}/…`:

| Plane | Endpoint / tool | What |
|-------|-----------------|------|
| Bean-0 provenance | `GET/POST …/provenance` | framework/constitution/model/corpus hashes |
| Bean-1 receipts | `GET …/inference-receipts` | hash-only signed log of every inference (auto-written by the LiteLLM callback) |
| Bean-2 signing | `GET …/bean-pubkey` | the agent's Ed25519 public key for offline verify |
| Bean-3 consent | `POST …/consent/grant`·`/revoke`, `GET …/consent` | default-closed grants for physical actuation |
| Bean-4 firewall | `GET …/firewall`, `POST …/firewall/{baseline,check}` | tool-call topology baseline + anomaly alerts |
| Bean-5 attestation | `GET …/attestation/{inference_id}` | offline walk: receipt → signature → provenance → model card → corpus |

Offline attestation from the shell:

```bash
python -m tinyagentos.bean_attest_cli <agent> <inference_id> [--data-dir DIR] [--json]
```

Hermes is the reference agent for Bean-0 — `TAOS_HERMES_RELEASE` pins the
framework version; the installer hashes it, hashes the system prompt
(`/opt/taos/constitution.txt`), and posts a provenance record on deploy.

Design: `docs/design/silicon-bean-integration.md`, `bean-2-5-plan.md`.

---

## 4. All-digital consent (agents *and* apps, one ledger)

The consent gate is subject-agnostic: `bean_consent` keys grants by a
**subject** (`agent:scout-1`, `app:com.acme.notes` — reverse-DNS id, a
placeholder for a domain you control, not an account you register).
`bean_consent.gated_consent_check(scope, is_gated, is_allowed_fn)` is the
shared decision core; Bean-3's `consent_check` is a thin wrapper. This is
the join point a future userspace-app runtime plugs into.

Design: `docs/design/silicon-bean-all-digital.md`.

---

## 5. Dev workflow

**Tests** — our suites run standalone (no full backend venv needed):

```bash
pip install aiosqlite pytest pytest-asyncio fastapi httpx cffi
for t in provenance inference_receipts bean_signing bean_consent \
         bean_firewall bean_attest memory_systems robotics tmrfs; do
  python3 -m pytest tests/$t/ --confcutdir=tests/$t -q
done
python3 -m pytest tests/test_mcp.py -q --noconftest      # permissions regression
cd desktop && npx tsc -b && npx vitest run                # frontend
```

**pk-client work loop** (the operating contract — see `AGENTS.md`):
baseline snapshot → scoped change → tests → after-snapshot → `compare` →
`repoguard scan` → report the delta. The `pk-trust-mcp` plugin exposes this
to agents; the toolchain lives in the `planekey-vse` checkout
(`PK_VSE_TOOLCHAIN`).

**Branch comparison** — `scripts/branch_matrix.py` compares every fork
branch against ours:

```bash
python3 scripts/branch_matrix.py --base origin/robotics-edition
# -> reports/branch-matrix.{json,md}; see docs/design/branch-matrix.md
```

---

## 6. Environment variables (fork additions)

| Var | Used by | Default |
|-----|---------|---------|
| `TAOS_TANK_COORDINATOR_URL` | tank bridge | `http://localhost:8420` |
| `TAOS_TANK_MAX_SPEED` | tank bridge | `70` |
| `TAOS_CAMERAS` / `TAOS_CAMERAS_FILE` | camera bridge | — |
| `TAOS_TMRFS_URL` | TMrFS bridge / auto-capture | `http://localhost:8080` |
| `TAOS_TMRFS_AGENT` | set by deployer per agent | agent slug |
| `TAOS_MEMORY_SYSTEMS` | set by deployer | `taosmd` |
| `TAOS_HERMES_RELEASE` | Hermes installer (Bean-0) | `main` |
| `PK_VSE_TOOLCHAIN` / `PK_WORKSPACE` | pk-trust bridge | `../planekey-vse/toolchain`, `~/.taos/pk-workspace` |

---

## 7. Design doc index

| Doc | Topic |
|-----|-------|
| `silicon-bean-integration.md` | Bean-0/1 + the silicon-bean mapping |
| `bean-2-5-plan.md` | signing, consent, firewall, attestation |
| `silicon-bean-all-digital.md` | one consent substrate for agents + apps |
| `tmrfs-memory-tier.md` | TMrFS as a memory plane |
| `pk-memory-backend.md` | the three-plane memory model |
| `memory-systems-integration.md` | deploy-time memory selection + cross-tier link |
| `robotics-edition.md` (in `docs/`) | tank + camera bridges |
| `beta44-adoption.md` | what we took from upstream beta.44 |
| `branch-matrix.md` | all-197-branch comparison + adoption shortlist |
