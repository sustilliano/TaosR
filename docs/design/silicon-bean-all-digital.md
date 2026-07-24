# Silicon bean = all digital: one consent substrate for agents and apps

Deep dive prompted by the branch-matrix finding that `feat/app-runtime-v1`
(sandboxed userspace apps) and Bean-3 (agent consent gate) look like two
features. They are not. Under PlaneKey's framing — the silicon bean covers
**all digital**, not just model inference — an installed app and an AI agent
are two *subject-kinds* of the same bean, and their action-gating is one
primitive wearing two costumes.

## The two costumes, side by side

| | Bean-3 (agents) | app-runtime-v1 broker (apps) |
|---|---|---|
| Subject | AI agent (`agent_slug`) | installed app (`app_id`) |
| Free set | every non-flagged tool | `FREE_CAPS` = {app.kv, app.table, app.files, app.notify, app.window} |
| Gated set | `FLAGGED_SCOPES` = {drive, stop, camera_look, set_mode, autonomy, ptz_move} | `GATED_CAPS` = {app.net, app.agent, app.llm, app.memory} |
| Grant lookup | `BeanConsentStore.is_allowed(agent_slug, scope)` | membership in the app's `granted` set |
| Default | closed for gated, open otherwise | closed for gated, open otherwise |
| Chokepoint | `mcp/permissions.check_permission` | `userspace/broker.handle_capability` |
| Decision | `consent_check(tool, is_allowed_fn)` | inline `if ns in GATED_CAPS and ns not in granted` |

Read the two rows for "Default" and "Decision": they are the **same rule**.
`consent_check` and the broker's gate compute an identical function —
`gated ∧ ¬granted ⇒ deny`. The only differences are (a) which set is gated
and (b) who the subject is. Everything else — default-closed, per-subject,
revocable, enforced at one dispatch point — is shared.

## The unification

`bean_consent` already generalizes for free in two ways the code didn't
name:

1. **The store is subject-agnostic.** `bean_consent(agent_slug, scope, …)` —
   `agent_slug` is just a TEXT key. Nothing stops it holding `agent:scout-1`
   or `app:com.acme.notes`. It is a **subject id**, not an agent id.
2. **The policy is set-agnostic.** `consent_check` hard-codes
   `is_flagged_scope`, but the decision core (`gated ∧ ¬granted`) doesn't
   care *which* predicate says a scope is gated.

So the substrate is: **one `BeanConsentStore`, one decision function, N
enforcement points.** An app capability call and an agent tool call both
become `is_allowed(subject, scope)` against the same ledger, and both can
emit the same action receipt.

```
            ┌───────────────── one bean_consent ledger ─────────────────┐
            │  grant / revoke / is_allowed(subject, scope)  (default-closed) │
            └───────▲───────────────────────────────────────▲──────────┘
                    │ subject = agent:<slug>                 │ subject = app:<id>
                    │ gated  = FLAGGED_SCOPES                │ gated  = GATED_CAPS
        ┌───────────┴───────────┐               ┌───────────┴────────────┐
        │ mcp/permissions       │               │ userspace/broker       │
        │ check_permission()    │               │ handle_capability()    │
        │  (agent tool calls)   │               │  (app capability RPC)  │
        └───────────────────────┘               └────────────────────────┘
```

## What this fork ships now (the spine)

Two additive, non-breaking pieces so the model is real, not just prose —
Bean-3 keeps working byte-for-byte:

- **`tinyagentos/bean_subject.py`** — formalizes subject identity:
  `subject_key(kind, ident)` → `"agent:scout-1"`, `"app:com.acme.notes"`;
  `parse_subject(key)` → `(kind, ident)`. Kinds are open
  (`agent`, `app`, and whatever "all digital" grows to next). This is the
  vocabulary the shared ledger is keyed by.
- **`bean_consent.gated_consent_check(scope, is_gated, is_allowed_fn)`** —
  the decision core, generalized over the gated predicate. `consent_check`
  (Bean-3's physical-actuation gate) is now a thin wrapper binding
  `is_gated = is_flagged_scope`, so an app broker gets the *same* audited
  decision by binding `is_gated = lambda c: namespace(c) in GATED_CAPS`.

Together: any digital subject, any gated capability, one decision, one
ledger — the "all digital" consent primitive.

## Adopting app-runtime-v1 against this

When/if we port the userspace runtime, the broker's `granted`-set check
becomes `gated_consent_check(cap, is_gated_cap, lambda c:
consent_store.is_allowed(subject_key("app", app_id), c))`. Consequences:

- **One consent UI** — the same grant/revoke surface lists an agent's
  physical-actuation grants and an app's net/llm/memory grants, because
  they're rows in one table.
- **One revocation** — "revoke everything this app can touch" and "stop
  this agent from driving" are the same operation.
- **Receipts extend to apps** — a gated app capability call is an *action
  receipt* (the third receipt plane from silicon-bean-integration.md), so
  "what a digital subject did in the world" covers apps too, not just
  agents.

## Naming collision to settle first (matrix flagged it)

`feat/provenance-sandbox-tiers` uses **provenance** for *install-source
provenance* (where a `.taosapp` came from → a capability ceiling). Bean-0
uses **provenance** for *model-inference provenance* (corpus + constitution
+ model-card → a signed receipt chain). Both are legitimate; they are not
the same axis. Before adopting the sandbox-tiers branch, disambiguate:
suggest **`install_provenance` / capability ceiling** for the app-runtime
concept, reserving unqualified "provenance" for the Bean-0 attestation
chain. A capability ceiling by install source is actually the *policy* layer
above this consent substrate — it bounds which scopes an app may ever be
granted — and slots in cleanly as a per-subject max-grant set.

## Recommendation

- **Adopt the spine now** (this commit) — zero risk, makes the model
  concrete, and is the join point any future app-runtime port plugs into.
- **Read app-runtime-v1's broker as a consumer of this substrate**, not a
  parallel consent system — port it (later, deliberately) so its gate calls
  the shared ledger instead of a private `granted` set.
- **Rename app "provenance" → install_provenance / capability ceiling** to
  keep the Bean-0 term unambiguous, and model the ceiling as a per-subject
  max-grant bound over this same substrate.
