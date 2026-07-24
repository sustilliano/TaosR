# Memory systems as a first-class agent choice

Makes the three memory planes selectable at agent creation and wires the
tensor plane into the inference loop. Builds on `tmrfs-memory-tier.md`,
`pk-memory-backend.md`, and Bean-1 receipts.

## The contract (all three tracks build to this)

An agent carries a **`memory_systems`** selection: a list drawn from

    "taosmd"    conversational (native, always available — the default)
    "tmrfs"     tensor/thought memory  -> tmrfs-memory MCP plugin
    "pk-trust"  artifact/trust memory  -> pk-trust-mcp MCP plugin

- Wire name everywhere: `memory_systems: string[]`.
- `taosmd` is always effectively on; the selection governs the two
  optional planes.
- The deployer, given `"tmrfs"`, sets container env
  `TAOS_TMRFS_AGENT=<agent-slug>` (namespacing the agent's thoughts) and
  `TAOS_MEMORY_SYSTEMS=<comma-list>`, and best-effort attaches the
  matching MCP plugin(s). Selection is persisted on the agent regardless,
  so it survives and is surfaceable even if a plugin isn't installed yet.

## Track 1 — backend: memory_systems on deploy (files: deployer.py, agent_registry_store.py, tests)

- Add `memory_systems: list[str] = field(default_factory=lambda: ["taosmd"])`
  to `DeployRequest`; persist it on the agent registry row (additive
  column, backward-compatible default).
- In `deploy_agent`'s env section: inject `TAOS_TMRFS_AGENT` (slug) when
  `"tmrfs"` is selected, plus `TAOS_MEMORY_SYSTEMS`. Best-effort attach of
  the `tmrfs-memory` / `pk-trust-mcp` plugins via the existing MCP
  attachment path when those servers are registered; skip-with-log
  otherwise. Never break a deploy over an unavailable plugin.
- Do NOT touch desktop/, litellm_callback.py, inference_receipt_store.py,
  or routes/__init__.py (integrator registers any new route).

## Track 2 — wizard UI: memory-systems multi-select (files: desktop/ only)

- Extend `DeployWizard.tsx`'s `MemoryWizardStep` with a checkbox group for
  the three systems (taosmd checked + disabled as the always-on default;
  tmrfs and pk-trust toggleable, each with a one-line description).
- Thread the selection into the wizard's deploy submit as
  `memory_systems: string[]` (the Track 1 field).
- Match existing wizard styling; add/extend a component test. desktop/ only.

## Track 3 — auto-capture + cross-tier link (files: litellm_callback.py, inference_receipt_store.py, routes/inference_receipts.py, tests)

- **Cross-tier link**: add an optional `thought_id: str | None` column to
  the inference receipt (store + POST body + `record()`), backward
  compatible (NULL default). A receipt can now reference the TMrFS thought
  the turn produced — "what the model did" -> "what it was thinking about".
- **Auto-capture**: in the LiteLLM callback success path, when the agent
  has TMrFS enabled (env `TAOS_TMRFS_AGENT` set) and a bridge URL is
  configured (`TAOS_TMRFS_URL`), best-effort POST a compact "thought"
  (a short summary/tag of the turn, NOT full transcript) to the TMrFS
  bridge `/tmrfs/store`, take the returned thought name/id, and include it
  as `thought_id` on the inference receipt it already emits. Fail-open and
  hash-only-adjacent: a TMrFS or receipt error never breaks inference;
  when TMrFS is off, behaviour is exactly Bean-1.
- Do NOT touch deployer.py, agent_registry_store.py, desktop/, or
  routes/__init__.py.

## Integration (me)

Register any new route, confirm the wizard's `memory_systems` payload
matches Track 1's field, run every suite + regression, repoguard, pk
receipt, push.
