# Wiring open-cowork to taOS

Scoping doc. `open-cowork` (OpenCoworkAI's open-source Claude Cowork; an
Electron desktop app built on the Claude Agent SDK) is **independent** of
taOS — no shared code. But it's a good front-end for a self-hosted taOS
because it meets taOS at two clean seams. This is the plan to wire them; it
is not yet a tested integration (open-cowork isn't in this session — fork it
to `sustilliano` to hack on it directly).

## The two seams

```
┌──────────────── open-cowork (Electron desktop, your laptop) ───────────────┐
│  Claude Agent SDK runner                                                     │
│    • model provider (Settings): baseUrl + apiKey + model                     │
│    • MCP connectors (src/main/mcp/)                                          │
└───────────┬──────────────────────────────────┬─────────────────────────────┘
            │ (A) OpenAI-format /v1             │ (B) MCP stdio
            ▼                                    ▼
   taOS LiteLLM proxy :4000/v1        taOS bridges (robotics/ pk-trust/ tmrfs)
   (self-hosted models)                → tank coordinator / cameras / TMrFS / bean APIs
```

## Seam A — models: cowork runs on your taOS models

open-cowork's provider types are `openrouter | anthropic | custom | openai |
gemini | ollama`, each `{ apiKey, baseUrl, model }`. The `openai` / `custom`
/ `ollama` types are **OpenAI-format** — exactly what taOS's LiteLLM proxy
serves at `/v1`. So there is **no need to expose an Anthropic endpoint**:

1. Mint a taOS LiteLLM key (any deployed agent has one; or generate via the
   proxy admin surface).
2. In open-cowork Settings, add a provider:
   - type: `openai` (or `custom`)
   - baseUrl: `http://<taos-host>:4000/v1`
   - apiKey: the LiteLLM key
   - model: a taOS model id (what `/v1/models` on the proxy lists)
3. **Reachability** is the only real work: LiteLLM binds `localhost:4000`
   by default. For a cowork machine that isn't the controller, put both on
   the same Tailnet and use the controller's Tailscale IP, or bind/proxy
   the LiteLLM port deliberately (don't expose it to the open internet — it
   is an un-authenticated-by-default model gateway behind the local token).

Result: the cowork desktop's agent runs on your self-hosted models,
routed/attested by taOS — and every call flows through the LiteLLM callback,
so **Bean-1 inference receipts are written for cowork's activity too** if
the key alias maps to a taOS agent.

## Seam B — tools: cowork drives taOS via MCP connectors

Our bridges (`robotics/tank_fleet_mcp.py`, `robotics/camera_mcp.py`,
`planekey/pk_trust_mcp.py`, `tmrfs/tmrfs_memory_mcp.py`) are stdlib-only MCP
stdio servers that reach taOS over HTTP. open-cowork bundles the Claude
Agent SDK, which takes standard `mcpServers` stdio connectors — so the same
bridges register as cowork connectors, giving the desktop tank driving,
camera vision, TMrFS memory, and the pk-trust work-loop.

Because the bridges are HTTP-backed and portable, the cowork machine runs
them locally pointed at the controller's URLs — see
`integrations/open-cowork/taos-connectors.mcp.json` (drop the bridge dirs on
the cowork machine, or clone this fork there, and set the env URLs to your
controller). Confirm the exact config location/format against your
open-cowork version's `src/main/mcp/` — the template uses the Claude Agent
SDK's canonical `{command, args, env}` stdio shape.

## The consent tie-in (the reason this is on-theme)

When cowork drives taOS through the bridges, it is a **digital subject** in
exactly the sense of `silicon-bean-all-digital.md`. Model it as
`app:open-cowork` in the bean consent ledger: its access to gated
capabilities (drive/stop/ptz, `app.net`-class actions) is default-closed and
grantable/revocable through the *same* substrate as agents. So the wiring
isn't just convenience — cowork becomes another subject-kind under the
silicon bean, and the consent spine already covers it.

## Phasing

1. **Seam A now** (config-only, no code): point cowork at taOS LiteLLM,
   confirm a chat runs on a self-hosted model, verify a Bean-1 receipt
   lands. Zero taOS changes.
2. **Seam B next**: register the connector bundle; confirm cowork can
   `list_tanks` / `snapshot` / `tmrfs_query` against the controller.
3. **Consent**: give cowork an `app:open-cowork` subject and gate its
   actuation through bean consent (needs the bridges to consult the ledger —
   the join point the all-digital spine already exposes).

## Open questions to verify against the real app

- open-cowork's exact MCP config surface (file path vs UI registration) in
  `src/main/mcp/`.
- Whether its Agent SDK runner forwards a stable key alias taOS can map to
  an agent (for receipt attribution).
- Its sandbox (WSL2/Lima) network egress rules — the connectors must be able
  to reach the controller from inside the sandbox.
