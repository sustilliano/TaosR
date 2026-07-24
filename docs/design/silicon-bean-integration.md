# Silicon beans: every taOS agent as an attested individual

Status: design mapping (source: planekey_messy products/planekey-bean +
sqlbooks/profiles/{corpus,constitution,model-card,inference-receipts})
Relation: extends `pk-memory-backend.md` Phase 3; robotics-edition consent

## The claim

PlaneKey Bean defines a **silicon bean**: a registered AI agent bound to
the corpus + constitution + model card that produced it, whose every
consequential output is a signed receipt, gated by per-output consent,
default closed. A taOS deployment is a *fleet of silicon beans* — the
deploy wizard already gives each agent identity, isolated memory, and
keys. What's missing is the trust layer, and taOS has a natural mount
point for every bean primitive:

| Bean primitive | taOS mount point |
|---|---|
| Bean registry (`substrate='silicon'`) | Agent registry (`agent_registry_store.py`) — one bean row per deployed agent |
| Provenance tri-layer (corpus/constitution/model-card sqlbooks) | Model catalog manifests + the agent's system prompt/template as a versioned **constitution sqlbook**; hash-pinned at deploy time |
| Inference receipts (prompt_hash, output_hash, model_id, signature) | The LiteLLM proxy — the single choke point every agent inference already passes through (`litellm_config.py`, existing callback hooks + `receipts.py`) |
| Cognitive firewall (output-topology baseline) | MCP permission layer (`mcp/permissions.py`) + board audit: baseline each agent's tool-call topology, flag drift |
| Consent gate (per-output, default closed, revocable) | Tool/plugin attachments (`mcp_attachments.allowed_tools`) upgraded from a static allowlist to a consent gate with receipts |

## Why the robotics edition makes this urgent

The inference-receipts spec names "an autonomous-agent command" as the
canonical consequential output. That is literally `drive` and `stop` in
`robotics/tank_fleet_mcp.py`. Today the bridge has manual guardrails
(speed clamp, timed moves, emergency stop). Bean turns those into
policy:

- **Actuation is consent-gated.** A physical command (drive, ptz_move)
  requires a live consent token for that agent + tool scope; default
  closed. Revocation stops the fleet without touching the robots.
- **Actuation is receipted.** Every physical command becomes an
  inference-receipt row: which agent (bean), which model version, what
  command hash, when. A tank's motion log becomes walkable back to the
  constitution that governed the agent that ordered it — offline.
- **Actuation is topology-checked.** The cognitive firewall baseline
  for a patrol agent is its normal command rhythm; a prompt-injected
  agent suddenly issuing max-speed sequences scores as off-baseline and
  gets the same treatment as injected neural signals: blocked.

## The three receipts, unified

The work already done or specced in this fork gives an agent task three
receipt kinds, one per plane:

1. **Artifact receipt** — pk-client snapshot compare (what files
   changed): `pk-memory-backend.md` Phase 3.
2. **Inference receipt** — signed inference log (what the model said):
   this doc, via the LiteLLM choke point.
3. **Action receipt** — consent-gated tool/actuator calls (what the
   agent did in the world): MCP layer + robotics bridges.

All three are sqlbook-shaped (repoguard reports already emit
`.sqlbook`), signable, diffable, and portable — the same
"docs-as-artifact" bet sqlbooks make, applied to agent behavior.

## Phasing

- **Bean-0 (cheap, now):** register each deployed agent with a
  provenance row — model manifest hash + sha256 of its system
  prompt/template ("constitution"). Surface it in the agent UI.
- **Bean-1:** LiteLLM callback writes hash-only inference receipts
  (manifest mode — no content stored, matching the spec's redaction
  posture) into `data/agent-memory/{name}/receipts.sqlbook`.
- **Bean-2:** consent gate on flagged tool scopes (physical actuation
  first: tank-fleet-mcp, taos-camera-mcp ptz). Default closed for new
  attachments; explicit grant per scope; revocation is immediate.
- **Bean-3:** topology baseline per agent over tool-call sequences;
  alerts feed the same notification store as MCP supervisor errors.

## Non-goals

- No neural/biological anything — taOS only ever hosts silicon beans.
- No content retention in receipts by default; hashes + metadata only.
- Signing keys: agent-held Ed25519 for receipts, human-held secret for
  layer attestation — same split as `pk-memory-backend.md`.

## The fleet-controller trajectory

Bean's docs + this fork converge on the same shape the wbt-branch
"bean fleet controller" was heading toward: a controller that manages a
fleet of attested agents (and their robots) where identity, provenance,
consent, and receipts are enforced at the platform layer — not by each
agent's goodwill. taOS is that controller's chassis; the robotics
bridges are its hands; planekey is its trust spine.
