# beta.44 comparison & adoption

Our fork branched from upstream at **v1.0.0-beta.43** (`3878ccb4`). Upstream
shipped **release/beta.44** = 10 commits / 37 files (+3351/−45) on top of
that base. This records the pk-client comparison, what we adopted, and what
we deliberately left.

## pk-client comparison

Merge-base with beta.44 is the beta.43 release commit, so the two deltas
are cleanly separable:

- beta.44 vs beta.43: 37 files changed.
- our fork vs beta.43: 89 files changed.
- **Overlap: 4 files** (`README.md`, `app.py`, `auth_middleware.py`,
  `uv.lock`) — and our side of those traces to inherited upstream merges
  (e.g. the doc-review store), not our own edits, so no true conflicts.

pk-client tree compare (beta44 → our head): 756 added / 9 removed / 41
changed (the "added" count is inflated by our build/cache artifacts; the
signal is that our additions are almost entirely new files).

## Adopted (cherry-picked with `-x`, upstream authorship preserved)

| Commit | What | Why it earns its place here |
|--------|------|------------------------------|
| #2102 Nous Portal provider | `nous` as a first-class cloud provider → `inference-api.nousresearch.com/v1`, Hermes 4 family | **Direct Bean-0 synergy** — an agent can now run Nous-hosted Hermes as its model, and our provenance chain (corpus + constitution + model-card) already targets exactly that family. This is the cloud counterpart to our local Hermes-3 GGUF manifest. |
| #2100 files_read/files_write enforcement | member agents gated on project Files scopes | Complements Bean-3's consent gate — same "default-closed, scope-checked" posture, applied to file access. |
| #1921 agent scope requests | an existing agent identity can request additional scopes | The request/grant half of the trust story our consent + provenance work is building toward. |
| #2092 dialogs above windows + mint URL/PIN | desktop z-index fix | Clean bug fix; our attestation/provenance panels live in the same window stack. |
| #2105 shortcuts resolve real incus project | terminal-shortcut container fix | Clean infra fix; relevant to our LXC-deployed agents. |

All five apply cleanly on top of our branch. Our six Bean routers and the
memory-systems wiring are untouched; bean/memory suites stay green (158
tests), desktop `tsc -b` clean, the adopted desktop fixes' tests pass.

## Deferred (available upstream, not adopted yet)

| Commit | What | Why deferred |
|--------|------|--------------|
| #2103/#2104 Assistant Studio | a new personal-assistant desktop workspace app | Large, desktop-heavy, low overlap with our robotics/bean/memory focus. Worth a dedicated port if we want the workspace; no dependency the other work needs. |
| #2097 library item card | UI component | Cosmetic; adopt when we touch the library surface. |
| #2098 project_tasks_create scope | one more agent scope | Small; fold in if/when we extend the scope set (pairs with #1921). |
| release bump / changelog | version metadata | Our fork carries its own version identity; not adopting upstream's bump. |

## Where our fork is ahead

beta.44 has no equivalent of what this fork adds on top of beta.43:

- **Silicon-bean trust stack** (Bean-0…5): provenance, signed hash-only
  inference receipts, consent-gated actuation, cognitive firewall, offline
  attestation walk — a whole trust plane beta.44 doesn't have.
- **Three-plane memory model**: taosmd + TMrFS tensor memory + pk-trust
  artifact memory, selectable at deploy.
- **Robotics edition**: tank-fleet and IP-camera MCP bridges + Hailo/GGUF
  Hermes provenance.

So the adoption is one-directional by design: we take beta.44's clean
infra/provider wins; our trust + memory + robotics work is the fork's
reason to exist and stays canonical here.

## Redo the comparison later

```
git fetch origin release/beta.NN
git merge-base HEAD FETCH_HEAD                     # the shared base
git log --oneline <base>..FETCH_HEAD               # upstream delta
comm -12 <(git diff --name-only <base> FETCH_HEAD | sort) \
        <(git diff --name-only <base> HEAD | sort) # overlap / conflict risk
```
