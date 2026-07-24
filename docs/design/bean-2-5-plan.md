# Bean-2 … Bean-5: the rest of the silicon-bean rollout

Extends `silicon-bean-integration.md`. Bean-0 (provenance) and Bean-1
(hash-only inference receipts) are shipped. This doc defines the four
remaining phases and their dependency order.

```
Bean-0 provenance ──┐
Bean-1 receipts ────┼──> Bean-2 signing ──> Bean-5 attestation walk
                    ├──> Bean-3 consent gate (physical actuation)
                    └──> Bean-4 cognitive firewall (topology baseline)
```

Bean-2 and Bean-3 are independent of each other and run in parallel.
Bean-4 reads existing tool-call history and can start any time. Bean-5
consumes Bean-2's signatures, so it lands last.

## Bean-2 — receipt signing (attestation completion)

Fills the `signature` column Bean-1 reserved. Each agent gets an Ed25519
keypair; every inference receipt is signed over its canonical bytes, so a
holder can verify offline that the controller really issued it.

- **Keystore** (`bean_keystore.py`): generate/load a per-agent Ed25519
  private key under `data/agent-memory/{agent}/bean-key/`; expose the
  public key. Private key never leaves the controller; 0600 perms.
- **Signing**: canonical receipt bytes = `json.dumps` of
  `{inference_id, trace_id, model_id, prompt_hash, output_hash,
  prompt_tokens, completion_tokens, started_at, completed_at, status}`
  with `sort_keys=True, separators=(',',':')`. Sign at receipt-record
  time; store the hex signature in the existing `signature` column.
- **Verify**: `bean_keystore.verify(agent, receipt) -> bool` plus
  `GET /api/agents/{name}/bean-pubkey` so an external holder can fetch the
  key. A receipt + pubkey verifies with no controller involvement.
- Backward compatible: Bean-1 receipts with `signature IS NULL` stay
  valid as "unsigned" — verification returns a tri-state
  (signed-valid / signed-invalid / unsigned).

## Bean-3 — consent gate for physical actuation

Default-closed, per-scope, immediately revocable consent — applied first
to the tools that move things in the world (tank drive/stop/turn, camera
and tank PTZ). Non-physical tools are unaffected (no regression).

- **Consent store** (`bean_consent_store.py`): grants keyed by
  `(agent, scope)` with `granted_at`, `revoked_at`, `granted_by`. Active =
  a row with `revoked_at IS NULL`. No grant → denied (default closed).
- **Flagged scopes**: a static set of actuation tool names
  (`drive`, `stop`, `camera_look`, `ptz_move`, …). Only these are gated;
  everything else passes as today.
- **Enforcement**: hook `mcp/permissions.py::check_permission` — after the
  existing allowlist/resource checks, if the tool is a flagged scope and
  no active consent grant exists, return `PermissionResult(allowed=False,
  reason="consent required (default-closed)")`.
- **Action receipt**: on an *allowed* actuation, append an action receipt
  (reuse `receipt_store.py`) — the third receipt plane (what the agent did
  in the world).
- **API**: grant / revoke / list consent for an agent; revocation takes
  effect on the very next `check_permission`.

## Bean-4 — cognitive firewall (tool-call topology baseline)

Per-agent behavioural baseline over tool-call sequences; flags drift the
way the biological firewall flags injected neural signals.

- **Baseline** (`bean_firewall.py`): build a per-agent model of normal
  tool-call topology (tool frequencies + ordered transition counts) from
  existing history (trace/board-audit stores — read-only).
- **Scoring**: score a recent window against the baseline; a low score =
  off-baseline behaviour (e.g. an injected agent suddenly issuing
  max-speed actuation bursts).
- **Alerts**: below-threshold scores post to the existing notification
  store (same sink as MCP supervisor errors). Detect-and-alert only in
  Bean-4; auto-blocking is a later tightening.

## Bean-5 — attestation walk (offline verifier)

The payoff: one verifier that walks all three receipt planes back to
origin, offline. Given an agent + a receipt, it produces a signed chain:
action/inference receipt → **Bean-2 signature check** → provenance record
→ model card + constitution hashes → published corpus ref. Ships as a
`pk-client`-style CLI plus a read-only UI panel. Assumed scope: the
offline attestation walk (not an E2EE transport envelope — lower value
for a single-owner self-hosted fleet). Flag if a different Bean-5 was
intended.

## Delegation rules (avoid collisions)

Each phase owns a disjoint file set and its own `tests/<phase>/` dir.
**No phase edits `routes/__init__.py`** — the integrator registers all
new routers there when merging, so parallel phases never conflict on it.
Every phase follows AGENTS.md: standalone-runnable tests, no commits
(integrator commits with the pk-client receipt).
