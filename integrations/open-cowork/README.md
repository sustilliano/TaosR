# open-cowork ⇄ taOS

Wiring the open-cowork desktop (`sustilliano/jcloudwork`, forked from the
OpenCoworkAI root) to a self-hosted taOS controller, and putting cowork
under bean management. Design: `docs/design/open-cowork-integration.md`,
`docs/design/silicon-bean-all-digital.md`.

## 1. Model → taOS Hermes (config only)

open-cowork ships a **custom / OpenAI-compatible** provider profile
(`custom:openai`), so no app code change is needed — point it at taOS's
LiteLLM proxy, which serves your Hermes models OpenAI-style:

- **Settings → Provider:** Custom (OpenAI-compatible)
- **Base URL:** `http://<taos-controller>:4000/v1`
- **API Key:** a taOS LiteLLM key (any deployed agent has one)
- **Model:** `hermes-3-llama-3.1-8b` (local GGUF) or a Nous Portal Hermes 4
  id if you added the Nous provider in taOS

Reachability: LiteLLM binds localhost by default — put the cowork machine on
the same Tailnet and use the controller's Tailscale IP, or bind/proxy the
port deliberately (never expose it to the open internet). If the LiteLLM key
alias maps to a taOS agent, cowork's calls also land **Bean-1 inference
receipts**.

## 2. taOS tools → cowork MCP connectors

jcloudwork's MCP preset registry now includes taOS bean services
(`src/main/mcp/mcp-config-store.ts` → `MCP_SERVER_PRESETS`):
`taOS_Tank_Fleet`, `taOS_Cameras`, `taOS_TMrFS_Memory`, `taOS_PK_Trust`.

In cowork's MCP settings, add a server from one of these presets, then edit:
- the **script path** in `args` to where the fork's bridges live on this
  machine (clone `taosr`, or copy `robotics/ tmrfs/ planekey/`), and
- the **env URLs** to your controller (the UI prompts for `requiresEnv`).

The bridges are stdlib-only Python 3 — no venv. `taos-connectors.mcp.json`
here is the same set as a portable config file if you prefer file-based
setup over the preset UI.

## 3. cowork under bean management

Register cowork as the bean subject `app:open-cowork` — a provenance record
plus default-closed consent for exactly the gated capabilities you allow:

```bash
TAOS_URL=http://taos-controller:6969 TAOS_LOCAL_TOKEN=… \
  ./register-cowork-bean.sh drive stop ptz_move
```

This uses the all-digital consent substrate: the consent ledger and routes
now accept `kind:ident` subject keys, so cowork's grants live on the *same*
ledger as your agents' — one grant/revoke surface for every digital subject.
Ungranted gated capabilities stay closed; revoke is immediate.

## Status

- Seam 1 (model): works today, config only.
- Seam 2 (MCP presets): the preset entries are in jcloudwork; point them at
  your controller.
- Seam 3 (bean management): provenance + consent register today. Full
  *enforcement* — the bridges consulting the ledger for `app:open-cowork`
  before actuation — is the next step (the join point is
  `bean_consent.gated_consent_check`; the bridges call the coordinator
  directly today, so they don't yet gate on cowork's grants).
