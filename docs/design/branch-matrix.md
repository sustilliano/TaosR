# Branch matrix — robotics-edition vs. all fork branches

This is the fanned-out sibling of `docs/design/beta44-adoption.md`: instead of
one upstream release branch, this compares **all 197 remote branches** of our
fork (`sustilliano/taosr`) against `robotics-edition`, looking for
features/designs worth adopting. Same rule as beta.44: **analysis and
recommendations only** — nothing here was cherry-picked, merged, or pushed.
The human decides what to adopt next.

## Method

Adapted the mirror-clone bandwidth-saver from
`planekey_messy/scripts/planekey-fanout.sh` to this problem: that script
gives every branch its own working folder off one `git clone --mirror`. We
don't need per-branch working folders (197 checkouts would be wasteful) —
we need per-branch **refs**, so `git merge-base` / `git diff` / `git rev-list`
resolve locally. So the adaptation was:

```
git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
git fetch origin --prune --no-tags      # pulls all 197 branch tips
git fetch origin --unshallow            # full history, not just tips
```

Both fetches succeeded on the first attempt (proxied network, no retries
needed). The repo went from a shallow single-branch clone to a full clone at
**247M** (`.git`), **914M** total working copy, against a 27G disk budget —
no pruning or `--deepen` fallback was required. `git rev-parse
--is-shallow-repository` returns `false`.

The comparison tool is `scripts/branch_matrix.py` (stdlib-only Python). For
every branch B on `origin` it computes, against `--base` (default
`origin/robotics-edition`):

- `merge-base` (or "unrelated/deep" if none exists — see `cla-signatures`
  below, an orphan branch with no shared history at all)
- commits ahead/behind, and whether B is already merged (ahead == 0)
- `git diff --shortstat`/`--name-only` `base...B` (files, +/-, top-level
  directory buckets — a cheap proxy for "what area this branch touches")
- the branch's newest commit subject/author/date
- a coarse `kind` from the branch name (dependabot / release / sync /
  exec-scratch / docs / feat / fix / test / chore / other)
- **`absorbed_files`** — see below

Run it with:

```
python3 scripts/branch_matrix.py \
  --base origin/robotics-edition --remote origin \
  --json-out reports/branch-matrix.json --md-out reports/branch-matrix.md
```

`--help` works, output is deterministic (stable sort: ahead desc, files
desc, branch name as tiebreak), and it's re-runnable/parameterizable
(`--base`, `--remote`, `--branch <name>` to scope to one branch).

### The "absorbed" check (why it exists)

Doing this at fan-out scale surfaced something the single-branch beta.44
comparison never had to deal with: a chunk of these 197 branches are **old**
(some fork from `beta.32`-era history), and by now their content may have
landed on our side anyway — through a squash-merge, a rebase, or an
independent re-implementation with a different commit message — so git's
ancestor tracking doesn't call the branch "merged" even though the tree
state already converged. Comparing purely by commit ancestry (`ahead`/
`merged`) would flag those as live adoption candidates when there is
nothing left to adopt.

So for every file the branch touches (relative to its own merge-base), the
tool also checks whether that file is **byte-identical** between our current
base tip and the branch tip (`git diff --quiet base ref -- <touched files>`).
`absorbed_files` is the count that already match; `fully_absorbed` is true
when all of them do. This caught real cases — e.g. `feat/council-role-registry`,
`feat/invite-s3-a2a-stream`, and `feat/agent-governance-slice1` are `ahead >
0` / `merged: no` by commit ancestry, yet 6/9, 2/3, and 7/12 of their touched
files respectively are already identical to what's on `robotics-edition`
today (full detail in the shortlist below). 29 of the 196 resolvable
branches are **fully** absorbed — ahead by commit graph, redundant by content.

## Resolution

**196 of 197 branches resolved** a merge-base against `origin/robotics-edition`.
The one exception is `cla-signatures` — an orphan branch (CLA-bot signature
log) with genuinely no common ancestor; this is a real "unrelated/deep" case,
not a fetch-depth artifact, since the full unshallow succeeded.

As a consistency check: this matrix's numbers for `release/beta.44` (10
commits ahead, 37 files, +3351/−45) match `beta44-adoption.md`'s
single-branch numbers exactly.

## Full matrix

Sorted most-ahead / most-changed first (`ahead` desc, then `files` desc,
branch name as tiebreak). "Absorbed" reads `x/y` (of y touched files, x are
already byte-identical on our tip) or `yes` for fully redundant branches;
merged branches show `—` since there's nothing to absorb-check.

| Branch | Kind | Ahead | Behind | Merged | Absorbed | Files | +/- | Top dirs | Last commit |
|---|---|---:|---:|---|---|---:|---|---|---|
| `feat/app-runtime-v1` | feat | 21 | 2164 | no | 6/40 | 40 | +1928/-3 | tests (18), tinyagentos (15), desktop (7) | fix(userspace): harden backend proxy (block ../ + strip headers) and make container re-install idempotent |
| `release/beta.44` | release | 10 | 41 | no | 18/37 | 37 | +3351/-45 | tinyagentos (15), desktop (13), tests (4), CHANGELOG.md (1), README.md (1) | chore(release): v1.0.0-beta.44 version bump + changelog |
| `dev` | other | 9 | 41 | no | 18/32 | 32 | +3321/-41 | tinyagentos (14), desktop (12), tests (4), README.md (1), docs (1) | fix(shortcuts): resolve the container's real incus project (and start it) for terminal shortcuts (#2105) |
| `fix/shortcut-pty-project-resolution` | fix | 9 | 41 | no | 18/32 | 32 | +3321/-41 | tinyagentos (14), desktop (12), tests (4), README.md (1), docs (1) | fix(shortcuts): resolve the container's real incus project (and start it) for terminal shortcuts |
| `fix/assistant-studio-optional-catalog` | fix | 8 | 41 | no | 16/30 | 30 | +3189/-39 | tinyagentos (13), desktop (12), tests (3), README.md (1), docs (1) | fix(apps): register assistant-studio as an installable optional app |
| `feat/agent-scope-requests` | feat | 8 | 41 | no | 16/27 | 27 | +2480/-38 | tinyagentos (12), desktop (10), tests (3), README.md (1), docs (1) | fix(agents): take the per-request lock in deny_scope_request too (#1921) |
| `design/trust-comms-layer` | other | 7 | 2001 | no | 4/13 | 13 | +2626/-153 | tinyagentos (8), tests (3), .github (1), docs (1) | docs(spec): trust-comms — dashboard gating on managed_by + view->app ownership |
| `feat/assistant-studio` | feat | 6 | 41 | no | 12/25 | 25 | +2104/-38 | desktop (12), tinyagentos (9), tests (2), README.md (1), docs (1) | feat(desktop): Assistant Studio - a workspace for a personal-assistant agent |
| `test/gamestudio-backfill` | test | 6 | 459 | no | 0/3 | 3 | +164/-2 | desktop (3) | test(gamestudio): fold Kilo findings (role-based queries, exact matches, drop dead non-null assertions) |
| `feat/gamestudio-ai-maker` | feat | 5 | 441 | no | 31/38 | 38 | +3423/-1593 | desktop (34), tinyagentos (2), README.md (1), tests (1) | feat(gamestudio): wire Create/Editor/Library/Share rail; adapt tests; docs |
| `feat/provenance-sandbox-tiers` | feat | 5 | 462 | no | 7/13 | 13 | +870/-57 | tinyagentos (6), desktop (5), tests (2) | refactor(sandbox): fold Kilo review notes (namespace match, migration commit) |
| `feat/video-studio` | feat | 5 | 459 | no | 5/11 | 11 | +1032/-4 | desktop (8), tinyagentos (2), README.md (1) | fix(video-studio): fold Kilo findings (delete rollback, seed validation, download href, timer/preload hygiene) |
| `feat/agent-project-files-access` | feat | 4 | 41 | no | 7/15 | 15 | +563/-36 | tinyagentos (6), desktop (5), tests (2), README.md (1), docs (1) | feat(agents): surface Files in the invite bundle + fix agent API-surface docs |
| `feat/office-studio-slides` | feat | 4 | 463 | no | 6/10 | 10 | +1617/-149 | desktop (10) | feat(office-studio): wire Slides into a real presentation editor |
| `feat/appstudio-code-analyzer` | feat | 4 | 459 | no | 5/9 | 9 | +1403/-9 | desktop (5), tests (2), tinyagentos (2) | fix(code-analyzer): fold Kilo findings (analyze DoS limits, TOCTOU, utf8 replace, sort perf, detector coverage) |
| `feat/consent-project-picker` | feat | 4 | 238 | no | 2/7 | 7 | +393/-11 | desktop (5), tests (1), tinyagentos (1) | fix(consent): tighten project gate and require project_id for project_tasks |
| `feat/web-studio-real-gen-sandbox-share` | feat | 3 | 420 | no | yes | 18 | +1520/-102 | desktop (14), tests (2), tinyagentos (2) | fix(web-studio): fold Kilo review findings |
| `feat/nous-portal-provider` | feat | 3 | 41 | no | 9/15 | 15 | +244/-30 | desktop (7), tinyagentos (7), tests (1) | feat(providers): add Nous Portal as a cloud model provider |
| `feat/userspace-container-tier` | feat | 3 | 453 | no | 5/11 | 11 | +703/-48 | tests (6), tinyagentos (3), desktop (2) | test(userspace): update stale 501 container-gate assertions for the lifted web-only gate |
| `feat/platform-backend-one-tap` | feat | 3 | 439 | no | 8/10 | 10 | +1264/-128 | tests (3), tinyagentos (3), desktop (2), app-catalog (1), scripts (1) | feat(setup): platform-aware "install a local model backend" checklist step |
| `fix/files-trash-and-modal-zindex` | fix | 3 | 439 | no | 6/10 | 10 | +954/-28 | tinyagentos (4), desktop (3), CHANGELOG.md (1), docs (1), tests (1) | fix(files): validate trash item_id against path traversal before destructive ops |
| `feat/browser-cdp-driver` | feat | 3 | 2022 | no | 2/8 | 8 | +1202/-14 | tests (3), app-catalog (2), tinyagentos (2), .github (1) | test(browser): fake-CDP server tests + Phase B port-wiring assertions |
| `feat/office-ai-assist` | feat | 3 | 418 | no | yes | 6 | +1039/-24 | desktop (6) | fix(office): fold Kilo review findings into Write Assist and Calc Ask your data |
| `feat/music-studio-wav-export` | feat | 3 | 408 | no | yes | 4 | +509/-24 | desktop (4) | fix(music-studio): harden WAV bounce guards per review |
| `docs/skill-refresh` | docs | 3 | 96 | no | 1/2 | 2 | +88/-57 | .claude (2) | docs(skill): fold kilo - state the GraphQL-vs-REST bot-login form difference explicitly + null-guard the REST jq |
| `fix/csrf-global-fetch` | fix | 3 | 96 | no | yes | 2 | +91/-1 | desktop (2) | fold kilo: also attach CSRF header to same-origin Request-object fetches |
| `fix/reject-embedding-agent-model` | fix | 3 | 264 | no | 1/2 | 2 | +164/-1 | tests (1), tinyagentos (1) | fix(agents): tolerate missing app.state.registry in the context-window warning |
| `review/docs-path-classification` | docs | 3 | 1542 | no | 0/2 | 2 | +31/-2 | tests (1), tinyagentos (1) | ci: re-trigger checks |
| `docs/contributor-pitfalls` | docs | 3 | 65 | no | 0/1 | 1 | +112/-0 | docs (1) | docs: extend pitfall 14 with the stale-base green lesson from the #2009/#1932 incident |
| `docs/cross-user-collab-spec` | docs | 3 | 89 | no | yes | 1 | +588/-0 | docs (1) | docs(design): address 1 Kilo + 5 CodeRabbit security findings on cross-user-collab spec (#2024) |
| `exec/tsk-bdclrf` | exec-scratch | 2 | 1244 | no | 0/1499 | 1499 | +373608/-3 | node_modules (1496), desktop (1), package-lock.json (1), package.json (1) | add a Vitest test next to desktop/src/components/ServiceIcon |
| `feat/music-studio-daw` | feat | 2 | 418 | no | 20/27 | 27 | +3232/-358 | desktop (20), tinyagentos (4), tests (3) | fix(music-studio): fold Kilo review — incremental edits, non-destructive piano-roll, content cap, robustness |
| `feat/routines-schedules` | feat | 2 | 423 | no | 9/17 | 17 | +2108/-4 | tinyagentos (6), desktop (5), tests (4), pyproject.toml (1), uv.lock (1) | fix(projects): harden routines — cron validation, atomic fire, indexed token, webhook rate limit |
| `feat/weight-license-metadata-nc-gate` | feat | 2 | 412 | no | 12/17 | 17 | +753/-11 | tests (5), tinyagentos (5), desktop (4), app-catalog (3) | fix(store): start install-progress poller on license-accept install; clearer empty weights-license label |
| `feat/elements-slice-3` | feat | 2 | 204 | no | 14/15 | 15 | +1342/-74 | desktop (15) | chore(projects): doc-gate trailer for elements slice 3 UI |
| `feat/agent-governance-slice1` | feat | 2 | 423 | no | 7/12 | 12 | +913/-1 | tests (6), tinyagentos (6) | feat(governance): narrow default gating + exempt admin human sessions (#160 slice 1) |
| `feat/task-relational-context` | feat | 2 | 424 | no | 5/12 | 12 | +555/-22 | tinyagentos (5), desktop (4), tests (3) | docs: no README change for relational-context |
| `fix/model-reachability-provider-errors` | fix | 2 | 433 | no | 7/12 | 12 | +515/-21 | tests (6), tinyagentos (6) | fix(models): guard _required_backend_ids against non-dict manifest variants |
| `perf/controller-restart-time` | chore | 2 | 1906 | no | 8/12 | 12 | +308/-123 | tinyagentos (5), tests (4), systemd (2), scripts (1) | fix(shutdown): dedupe stamp only on successful prepare; correct stop_all error logging; sturdier concurrency test |
| `feat/elements-slice-1` | feat | 2 | 211 | no | 3/10 | 10 | +1044/-13 | tinyagentos (6), tests (4) | test(projects): slice 1 element store, CRUD route, and task tag coverage |
| `fix/mobile-pass-1` | fix | 2 | 259 | no | 8/9 | 9 | +29/-17 | desktop (9) | fix(images): edit options panel goes full-width when stacked on mobile |
| `feat/docreview-stamp-store` | feat | 2 | 200 | no | 3/8 | 8 | +833/-2 | tinyagentos (5), desktop (2), tests (1) | feat(projects): add doc-review stamp badge to FilesApp and fix projects.ts types |
| `feat/os-level-agent-invites` | feat | 2 | 100 | no | 1/8 | 8 | +1026/-83 | tinyagentos (4), desktop (2), tests (2) | fold kilo review: strip project scopes + validate display_name (#1918) |
| `feat/invite-s1-store` | feat | 2 | 163 | no | 0/7 | 7 | +829/-0 | tinyagentos (4), tests (3) | fix(invite): make project_id nullable for agent-centric invites |
| `fix/images-quality-tier-downgrade-honesty` | fix | 2 | 418 | no | 6/7 | 7 | +372/-14 | desktop (5), tests (1), tinyagentos (1) | fix(images): show disabled-tier tooltip + align tier_healthy with router |
| `feat/agent-context-budget` | feat | 2 | 238 | no | yes | 6 | +333/-7 | tests (3), tinyagentos (3) | fix(chat): cap history budget at the default when a recipient window is unknown |
| `feat/office-database-view` | feat | 2 | 420 | no | 4/6 | 6 | +1078/-2 | desktop (6) | fix(office): address Database view review — coerce on type change, guard async, tighten types |
| `fix/taos-agent-runtime` | fix | 2 | 433 | no | 3/6 | 6 | +315/-15 | desktop (2), tests (2), tinyagentos (2) | fix(taos-agent): render dialog shell + error state instead of blank window (#1615) |
| `fix/video-studio-async-job` | fix | 2 | 410 | no | 4/6 | 6 | +487/-82 | desktop (3), tinyagentos (2), tests (1) | fix(video-studio): harden video job store + poll path against Kilo findings |
| `feat/hub-slice-2` | feat | 2 | 213 | no | 1/5 | 5 | +705/-0 | tinyagentos (3), tests (2) | chore(hub): doc-gate trailer for the hub store slice |
| `feat/managed-backend-contract` | feat | 2 | 254 | no | 3/4 | 4 | +283/-0 | .github (1), app-catalog (1), scripts (1), tests (1) | fix(manifest-lint): harden auto_manage/YAML checks (fold Kilo review on #1756) |
| `feat/taosnet-passkey-client` | feat | 2 | 266 | no | 1/4 | 4 | +212/-3 | tests (2), tinyagentos (2) | test(download-manager): accept passkey/web_seeds in torrent.download mocks |
| `fix/canvas-text-render` | fix | 2 | 204 | no | 3/4 | 4 | +100/-2 | desktop (4) | chore(canvas): doc-gate trailer for text shape |
| `fix/logs-app` | fix | 2 | 453 | no | 3/4 | 4 | +798/-12 | tinyagentos (2), desktop (1), tests (1) | feat(logs): wire Settings Logs pane to the system-logs API |
| `fix/providers-error-state` | fix | 2 | 443 | no | 1/4 | 4 | +163/-5 | desktop (2), tests (1), tinyagentos (1) | Merge branch 'master' into fix/providers-error-state |
| `exec/tsk-ihf2vw` | exec-scratch | 2 | 41 | no | 0/3 | 3 | +408/-46 | desktop (3) | tsk-ihf2vw  [OPEN]  Library UI: storage accounting view |
| `feat/members-rename-confirm` | feat | 2 | 96 | no | 2/3 | 3 | +353/-26 | desktop (3) | fold kilo + coderabbit on members rename/confirm |
| `fix/agents-mobile` | fix | 2 | 259 | no | yes | 3 | +111/-27 | desktop (3) | fix(agents): mobile header buttons to 44px tap targets |
| `fix/onboarding-gate-mermaid` | fix | 2 | 100 | no | 1/3 | 3 | +25/-10 | desktop (3) | fix onboarding tests for the gated username step (#1844) |
| `docs/gate-agent-api` | docs | 2 | 163 | no | 1/2 | 2 | +35/-1 | docs (2) | docs: reference the invite design by issue #1780, not the unmerged file path |
| `exec/tsk-fnqd7e` | exec-scratch | 2 | 1239 | no | 0/2 | 2 | +61/-1 | desktop (1), node_modules (1) | add a Vitest test next to desktop/src/components/UpdateAvailableToast |
| `exec/tsk-pv3xrn` | exec-scratch | 2 | 1236 | no | 0/2 | 2 | +88/-1 | desktop (1), node_modules (1) | add a Vitest test next to desktop/src/components/ConsentNotification |
| `exec/tsk-xq7iz3` | exec-scratch | 2 | 1236 | no | 0/2 | 2 | +62/-1 | desktop (1), node_modules (1) | add a Vitest test next to desktop/src/components/ContextMenu |
| `feat/account-slice-3` | feat | 2 | 223 | no | 0/2 | 2 | +222/-0 | tests (1), tinyagentos (1) | test(account): cover subdomain proxy forwarding, 503, and name validation |
| `feat/backend-service-manager` | feat | 2 | 252 | no | 0/2 | 2 | +430/-0 | tests (1), tinyagentos (1) | fix(backend-services): drain+close subprocess pipes on restart timeout (fold Kilo on #1758) |
| `feat/hailo-slice-3` | feat | 2 | 217 | no | yes | 2 | +44/-0 | app-catalog (1), tests (1) | fix(hailo): declare the proprietary license in the hailo-ollama manifest |
| `fix/mac-app-rebuild` | fix | 2 | 459 | no | yes | 2 | +163/-26 | mac (1), tinyagentos (1) | fix(mac): locate the SPA root by index.html, guard against layout drift |
| `fix/registry-poll-scroll` | fix | 2 | 234 | no | 0/2 | 2 | +132/-17 | desktop (2) | fix(desktop): guard registryEntriesEqual index access and drop em dashes |
| `docs/readme-agent-collaboration` | docs | 2 | 207 | no | 0/1 | 1 | +11/-0 | README.md (1) | docs(readme): reference only docs that exist on dev |
| `feat/hailo-slice-2` | feat | 2 | 219 | no | 0/1 | 1 | +479/-0 | scripts (1) | chore(hailo): doc-gate trailer for install-hailo.sh |
| `fix/1730-rkllama-pin-preload` | fix | 2 | 272 | no | 0/1 | 1 | +2/-2 | scripts (1) | fix(install-rknpu): pin rkllama with --preload restore + context-overflow fix (#1730, #1732) |
| `spec/backend-service-mgmt` | chore | 2 | 255 | no | yes | 1 | +112/-0 | docs (1) | docs(design): correct contract to extend existing lifecycle block (not a new managed block) |
| `feat/elements-slice-2` | feat | 1 | 209 | no | 16/19 | 19 | +312/-6 | desktop (19) | feat(projects): kanban element filter bar (slice 2) |
| `verify/design-batch` | chore | 1 | 1751 | no | 1/15 | 15 | +2393/-458 | desktop (7), tinyagentos (5), app-catalog (1), scripts (1), tests (1) | Merge remote-tracking branches 'origin/feat/images-edit-backends', 'origin/feat/agents-cards' and 'origin/feat/contacts-polish' into verify/design-batch |
| `feat/app-studio-real-pipeline` | feat | 1 | 416 | no | yes | 13 | +1019/-350 | desktop (11), tests (1), tinyagentos (1) | feat(app-studio): real build to package to analyze to install to sandbox-render pipeline (mock to functional) |
| `feat/elements-slice-4` | feat | 1 | 202 | no | 6/13 | 13 | +354/-39 | desktop (5), tinyagentos (5), tests (3) | Projects elements slice 4: element-scoped canvas + files |
| `fix/settings-persist-apply` | fix | 1 | 435 | no | 8/13 | 13 | +307/-44 | desktop (11), tests (1), tinyagentos (1) | fix(settings): persist theme/wallpaper across sessions + apply Desktop & Dock settings (#1601, #1603) |
| `feat/design-studio-persistence` | feat | 1 | 416 | no | 9/12 | 12 | +1102/-6 | desktop (5), tinyagentos (4), tests (3) | feat(design-studio): save/open/rename/delete designs (persistence) |
| `feat/pwa-web-push` | feat | 1 | 238 | no | 7/12 | 12 | +1317/-20 | desktop (6), tinyagentos (5), tests (1) | feat(notifications): OS-level PWA web-push (VAPID) for taOS notifications |
| `feat/council-role-registry` | feat | 1 | 200 | no | 6/9 | 9 | +423/-0 | tinyagentos (6), tests (3) | feat(council): role registry + member store slice per taos-council.md |
| `feat/hub-slice-4` | feat | 1 | 209 | no | 5/9 | 9 | +1310/-6 | tinyagentos (4), desktop (3), tests (2) | feat(hub): post objects, chain logic, image ingest, composer + own-timeline (slice 4) |
| `feat/docreview-markdown-reader` | feat | 1 | 200 | no | 4/8 | 8 | +773/-14 | desktop (8) | feat(projects): markdown doc reader (#1802 slice 1) |
| `feat/hub-slice-3` | feat | 1 | 211 | no | 3/8 | 8 | +1431/-16 | tinyagentos (5), tests (3) | feat(hub): follow / friend / circle model + request brokering (slice 3) |
| `fix/audit-hotfix-vram-manifest` | fix | 1 | 247 | no | 2/8 | 8 | +206/-60 | tinyagentos (5), tests (2), scripts (1) | fix(worker,models): audit hotfixes - manifest crash, VRAM fail-open, real min_ram_mb key |
| `fix/npu-backend-install-runs-service` | fix | 1 | 444 | no | 1/8 | 8 | +415/-22 | tests (3), tinyagentos (3), app-catalog (1), scripts (1) | fix(npu): store install actually creates+starts+verifies the rkllama service (self-heal) + one-tap install endpoint |
| `fix/settings-persist-across-login` | fix | 1 | 433 | no | 5/8 | 8 | +351/-14 | desktop (7), tests (1) | fix(settings): actually persist theme/wallpaper/dock across sessions (#1601, #1603) |
| `feat/hailo-slice-5` | feat | 1 | 213 | no | 2/7 | 7 | +129/-5 | tinyagentos (4), tests (3) | feat(hailo): slice 5 runtime detection + provider adapter for Hailo-10H (per design doc) |
| `fix/consent-ui-nits` | fix | 1 | 447 | no | 5/7 | 7 | +78/-11 | desktop (5), tests (1), tinyagentos (1) | fix(userspace): consent dialog dismiss-guard while submitting + skip needless row fetch |
| `fix/installer-account-hub` | fix | 1 | 171 | no | 5/7 | 7 | +170/-14 | tests (4), tinyagentos (3) | fix(security): account proxy stops forwarding local session cookie + hub binds author to signing key (audit #7, #8) |
| `feat/userspace-consent-ui` | feat | 1 | 454 | no | 0/6 | 6 | +452/-0 | desktop (6) | feat(userspace): install-time permission consent dialog |
| `fix/fold-kilo-1748-1749` | fix | 1 | 259 | no | 3/6 | 6 | +73/-27 | desktop (4), tests (1), tinyagentos (1) | fix(agent-window,activity): fold Kilo review findings from #1748/#1749 |
| `fix/framework-store-install` | fix | 1 | 453 | no | 1/6 | 6 | +546/-10 | desktop (4), tests (1), tinyagentos (1) | fix(store): agent-framework install enables deploy + prefetches base image + notifies (#1582) |
| `fix/guard-randomuuid-secure-context` | fix | 1 | 453 | no | 5/6 | 6 | +51/-8 | desktop (6) | fix(desktop): guard crypto.randomUUID for non-secure-context (http) across assistant/push/webstudio |
| `release/1.0.0-beta.36` | release | 1 | 267 | no | 0/6 | 6 | +19/-6 | desktop (2), CHANGELOG.md (1), pyproject.toml (1), tinyagentos (1), uv.lock (1) | release: 1.0.0-beta.36 |
| `release/1.0.0-beta.37` | release | 1 | 262 | no | 0/6 | 6 | +16/-6 | desktop (2), CHANGELOG.md (1), pyproject.toml (1), tinyagentos (1), uv.lock (1) | release: 1.0.0-beta.37 |
| `release/beta.38` | release | 1 | 256 | no | 0/6 | 6 | +17/-6 | desktop (2), CHANGELOG.md (1), pyproject.toml (1), tinyagentos (1), uv.lock (1) | release: 1.0.0-beta.38 (agent-window resilience + mobile-friendliness) |
| `release/beta.40` | release | 1 | 235 | no | 0/6 | 6 | +15/-6 | desktop (2), CHANGELOG.md (1), pyproject.toml (1), tinyagentos (1), uv.lock (1) | release: 1.0.0-beta.40 (consent project picker, PWA web-push, model-aware chat context budget) |
| `exec/tsk-bbdmdr` | exec-scratch | 1 | 889 | no | 0/5 | 5 | +159/-2 | tinyagentos (4), tests (1) | Add taOSgo remote-relay Pro entitlement and relay authorize endpoints |
| `feat/ai-stack-recovery` | feat | 1 | 261 | no | 1/5 | 5 | +504/-3 | desktop (3), tests (1), tinyagentos (1) | feat(activity): recover/restart the local AI stack (#1743) |
| `feat/hub-slice-1` | feat | 1 | 215 | no | 2/5 | 5 | +546/-0 | tinyagentos (3), tests (2) | feat(hub): identity keypair keystore + directory registration proxy (slice 1) |
| `fix/downloaded-models-agent` | fix | 1 | 439 | no | 1/5 | 5 | +177/-10 | tests (2), tinyagentos (2), desktop (1) | fix(models): downloaded rkllama models register via /api/pull so the agent can select + deploy them; taOS-agent picker lists local models (#1599, #1600) |
| `fix/models-delete-and-refresh` | fix | 1 | 453 | no | 2/5 | 5 | +354/-4 | desktop (3), tests (1), tinyagentos (1) | fix(models): real delete endpoint + auto-refresh installed state after download (#1581, #1548) |
| `release/beta.41` | release | 1 | 96 | no | 0/5 | 5 | +22/-4 | CHANGELOG.md (1), desktop (1), pyproject.toml (1), tinyagentos (1), uv.lock (1) | chore(release): 1.0.0-beta.41 |
| `release/beta.42` | release | 1 | 50 | no | 0/5 | 5 | +31/-4 | CHANGELOG.md (1), desktop (1), pyproject.toml (1), tinyagentos (1), uv.lock (1) | chore(release): v1.0.0-beta.42 version bump + changelog |
| `feat/account-slice-4` | feat | 1 | 219 | no | yes | 4 | +529/-33 | desktop (4) | feat(account): frontend types + Account panel split for username/subdomains (slice 4) |
| `feat/docreview-deeplink-registry` | feat | 1 | 200 | no | 3/4 | 4 | +210/-7 | desktop (4) | feat(projects): deep-link target registry (#1802 slice 2) |
| `feat/hailo-slice-1` | feat | 1 | 223 | no | 3/4 | 4 | +25/-1 | tests (2), tinyagentos (2) | feat(hailo): reserve port 7836 and map hailo-ollama llm-chat capability |
| `fix/identity-followups` | fix | 1 | 171 | no | 0/4 | 4 | +273/-15 | tests (2), tinyagentos (2) | fix(projects): stop cleared Lead re-promotion + approve canvas scope adds membership (audit #4, #11) |
| `fix/vram-reservation-1766` | fix | 1 | 220 | no | 3/4 | 4 | +329/-26 | tests (2), tinyagentos (2) | fix(models): VRAM reservation TTL sweep + #1766 acceptance coverage |
| `exec/tsk-cpgdhh` | exec-scratch | 1 | 41 | no | 0/3 | 3 | +814/-0 | desktop (3) | feat(library): item card component with thumbnail, status, artifacts, collection link |
| `feat/account-username-promo` | feat | 1 | 447 | no | 0/3 | 3 | +94/-3 | desktop (3) | feat(settings): frame taOS account for future features + reserve-your-username promo |
| `feat/agent-window-resilience` | feat | 1 | 261 | no | 1/3 | 3 | +249/-1 | desktop (3) | feat(agent-window): scrollbars and stall detection (#1741, #1742) |
| `feat/cli-account-recovery` | feat | 1 | 264 | no | 1/3 | 3 | +183/-0 | tinyagentos (2), tests (1) | feat(cli): taos recover-password for offline local account recovery |
| `feat/hailo-slice-4` | feat | 1 | 215 | no | 1/3 | 3 | +167/-0 | scripts (2), install.sh (1) | feat(hailo): slice 4 install-time gates for Hailo-10H (per design doc) |
| `feat/invite-s3-a2a-stream` | feat | 1 | 163 | no | 2/3 | 3 | +292/-5 | tinyagentos (2), tests (1) | feat(a2a): authenticated SSE stream proxy + since cursor (#1780 S3) |
| `fix/canvas-hardening` | fix | 1 | 171 | no | yes | 3 | +90/-1 | tinyagentos (2), tests (1) | fix(canvas): bound snapshot render dimensions + offload render + clamp element geometry (audit #1) |
| `fix/dock-wallpaper-merge-regression` | fix | 1 | 416 | no | yes | 3 | +103/-0 | desktop (1), tests (1), tinyagentos (1) | test(settings): lock in dock/wallpaper partial-save isolation (#1603, #1601) |
| `fix/framework-verified-tiers` | fix | 1 | 103 | no | 2/3 | 3 | +23/-14 | tinyagentos (2), tests (1) | fix(frameworks): verified_only returns tested+beta, not beta-only |
| `fix/invite-burn-scope-validation` | fix | 1 | 96 | no | 0/3 | 3 | +118/-0 | tinyagentos (2), tests (1) | fix(invites): failed approve no longer burns the invite + validate scopes at mint (#1993) |
| `fix/skill-exec-authz` | fix | 1 | 433 | no | 1/3 | 3 | +282/-2 | tests (2), tinyagentos (1) | fix(security): require admin or local-token auth for skill execution — closes non-admin RCE via code_exec (GHSA-h24f-gp4c-8qjm) |
| `docs/agent-coordination` | docs | 1 | 962 | no | 0/2 | 2 | +86/-796 | docs (1), uv.lock (1) | docs: add agent coordination guide for multi-agent build lane |
| `feat/account-slice-5` | feat | 1 | 217 | no | 0/2 | 2 | +287/-4 | desktop (2) | feat(account): onboarding free username claim step (slice 5) |
| `feat/canvas-excalidraw-slice1` | feat | 1 | 679 | no | 0/2 | 2 | +252/-0 | desktop (2) | feat(canvas): CanvasElement to Excalidraw skeleton mapping (slice 1) |
| `feat/npu-backend-one-tap-install` | feat | 1 | 442 | no | 0/2 | 2 | +189/-6 | desktop (2) | feat(setup): one-tap NPU backend install from the checklist + notification |
| `feat/onboarding-cloud-account-step` | feat | 1 | 444 | no | 0/2 | 2 | +139/-10 | desktop (2) | feat(onboarding): optional taOS cloud-account step with reserve-username hint (#141) |
| `fix/1724-searxng-secret-perms` | fix | 1 | 269 | no | yes | 2 | +27/-2 | tests (1), tinyagentos (1) | fix(docker-installer): 0600 perms + validity guard on the persisted app secret |
| `fix/1743-rewire-backend-services` | fix | 1 | 251 | no | yes | 2 | +160/-131 | tests (1), tinyagentos (1) | refactor(system): derive #1743 restart targets from managed-backend contract (Phase 1.3) |
| `fix/canvas-note-colors` | fix | 1 | 207 | no | 1/2 | 2 | +21/-0 | desktop (2) | fix: map violet and red note colors to valid tldraw palette names |
| `fix/external-agent-members-section` | fix | 1 | 234 | no | 0/2 | 2 | +90/-1 | desktop (2) | fix(projects): show consent-flow external agents in the External section |
| `fix/github-app-key-semantic-conflict` | fix | 1 | 66 | no | yes | 2 | +13/-8 | tests (1), tinyagentos (1) | fix(github): resolve #2009/#1932 semantic conflict - app key comes from SecretsStore |
| `fix/hub-append-race` | fix | 1 | 207 | no | 0/2 | 2 | +51/-12 | tests (1), tinyagentos (1) | fix(hub): serialize chain appends so racing posts are not orphaned |
| `fix/rkllama-managed-service` | fix | 1 | 255 | no | 1/2 | 2 | +22/-9 | scripts (1), tinyagentos (1) | fix(rknpu): a live rkllama port is not 'installed' unless it is a managed systemd service |
| `fix/settings-authz-guard` | fix | 1 | 427 | no | 1/2 | 2 | +264/-2 | tests (1), tinyagentos (1) | fix(security): require admin or local-token auth on system settings router (GHSA-47g9-fwwp-hrfp) |
| `fix/texteditor-create` | fix | 1 | 453 | no | 0/2 | 2 | +69/-1 | desktop (2) | fix(texteditor): restore create/save of notes and documents (#1584) |
| `fix/texteditor-focus` | fix | 1 | 439 | no | yes | 2 | +53/-13 | desktop (2) | fix(texteditor): guard remaining randomUUID call sites; keep focus while typing (#1596) |
| `fix/texteditor-focus-loss` | fix | 1 | 439 | no | 0/2 | 2 | +64/-2 | desktop (2) | fix(texteditor): stop focus loss per keystroke (#1596) |
| `fix/video-delete-confirm` | fix | 1 | 202 | no | yes | 2 | +86/-2 | desktop (2) | Add confirm guard before video delete |
| `dependabot/npm_and_yarn/desktop/npm_and_yarn-88fb2ca490` | dependabot | 1 | 19 | no | 0/1 | 1 | +8/-8 | desktop (1) | chore(deps): bump immutable |
| `docs/account-subdomain-design` | docs | 1 | 226 | no | yes | 1 | +310/-0 | docs (1) | docs(design): account model, free username plus paid chosen subdomains |
| `docs/dev-skill-pr-lifecycle` | docs | 1 | 60 | no | 0/1 | 1 | +54/-0 | .claude (1) | docs(skill): add PR lifecycle discipline - fold-first, rebase cadence, closure conventions |
| `docs/doc-review-surface-design` | docs | 1 | 219 | no | 0/1 | 1 | +558/-0 | docs (1) | docs(design): document review surface, md reader + stamps + review chat |
| `docs/hailo-backend-design` | docs | 1 | 226 | no | yes | 1 | +417/-0 | docs (1) | docs(design): Hailo-10H LLM backend, zero-touch install parity with RK3588 |
| `docs/hub-social-design` | docs | 1 | 226 | no | yes | 1 | +602/-0 | docs (1) | docs(design): hub.taos.my local-first P2P social network foundation |
| `docs/library-app-spec` | docs | 1 | 56 | no | yes | 1 | +145/-0 | docs (1) | docs(design): Library app spec - universal ingestion into memory and collections |
| `docs/project-elements-design` | docs | 1 | 223 | no | yes | 1 | +650/-0 | docs (1) | docs(design): Projects app nested elements, one project with typed elements |
| `docs/taostalk-slice1-spec` | docs | 1 | 85 | no | yes | 1 | +289/-0 | docs (1) | docs(design): taOStalk slice 1 spec - Tier 0 push+poll session bridge (#1953) |
| `feat/opencrabs-deploy-install` | feat | 1 | 538 | no | 0/1 | 1 | +235/-0 | tinyagentos (1) | feat(opencrabs): deploy install script (binary + LiteLLM provider + SSE bridge) |
| `fix/hailo-pin-idempotency` | fix | 1 | 171 | no | 0/1 | 1 | +10/-2 | scripts (1) | fix(hailo): correct re-install idempotency check + narrow the orphan reaper |
| `fix/hailo-real-repo-build` | fix | 1 | 165 | no | yes | 1 | +41/-36 | scripts (1) | fix(hailo): install from hailo_model_zoo_genai via cmake, not a nonexistent repo |
| `fix/installer-chown-warn` | fix | 1 | 171 | no | 0/1 | 1 | +5/-1 | scripts (1) | fix(installer): do not abort the installer if the re-run chown partially fails |
| `fix/rkllama-context-error-pin` | fix | 1 | 266 | no | 0/1 | 1 | +2/-2 | scripts (1) | fix(install-rknpu): pin rkllama with structured context-overflow error (#1738) |
| `fix/rkllama-repin-1.3.0` | fix | 1 | 249 | no | 0/1 | 1 | +17/-2 | scripts (1) | fix(install-rknpu): pin rkllama to the 1.3.0 ref + guard the fork patches |
| `gauge/kilo-secrets-test` | chore | 1 | 234 | no | 0/1 | 1 | +227/-0 | desktop (1) | test(secrets): add coverage for the Secrets app |
| `test/chess-app` | test | 1 | 231 | no | yes | 1 | +176/-0 | desktop (1) | test(chess): add vitest coverage for ChessApp |
| `test/imageviewer-app` | test | 1 | 231 | no | yes | 1 | +199/-0 | desktop (1) | test(imageviewer): add vitest coverage for ImageViewerApp |
| `test/notes-app` | test | 1 | 234 | no | yes | 1 | +204/-0 | desktop (1) | test(notes): add vitest coverage for NotesApp/TodoApp mounted behavior |
| `test/slides-view` | test | 1 | 207 | no | 0/1 | 1 | +147/-0 | desktop (1) | test(officestudio): add SlidesView component tests for add slide, reorder, and present mode |
| `chore/172-prune-agent-worktrees` | chore | 0 | 350 | yes | — | 0 | +0/-0 | — | chore(scripts): safe prune policy for stale agent worktrees (#172) |
| `chore/relicense-agpl-dual` | chore | 0 | 282 | yes | — | 0 | +0/-0 | — | chore(license): dual-license taOS as AGPL-3.0-or-later + commercial |
| `docs/taosnet-current-state` | docs | 0 | 275 | yes | — | 0 | +0/-0 | — | docs(taosnet): reconcile model-torrent-mesh design with the shipped closed swarm |
| `feat/1675-gpu-lease-finish` | feat | 0 | 343 | yes | — | 0 | +0/-0 | — | fix(cluster): atomic lease claim + VRAM-unknown handling + review fixes; drop redundant model-archive (#893) |
| `feat/apple-client-slice1` | feat | 0 | 359 | yes | — | 0 | +0/-0 | — | fix(devices): fold Kilo review on #1671 (input caps, device cap, APNs sandbox, touch debounce) |
| `feat/lead-identity-base` | feat | 0 | 194 | yes | — | 0 | +0/-0 | — | fix(canvas): fold adversarial review findings 1, 2, 4 into route gating |
| `feat/lead-identity-mw-allowlist` | feat | 0 | 198 | yes | — | 0 | +0/-0 | — | fix(agents): escape the dot in the canvas snapshot allowlist regexes |
| `feat/lead-identity-route-gating` | feat | 0 | 194 | yes | — | 0 | +0/-0 | — | fix(canvas): fold adversarial review findings 1, 2, 4 into route gating |
| `feat/lead-identity-scope-vocab` | feat | 0 | 196 | yes | — | 0 | +0/-0 | — | test(agents): update ConsentActions test to the new project-picker label |
| `feat/taosnet-client-passkey` | feat | 0 | 275 | yes | — | 0 | +0/-0 | — | feat(taosnet): client passkey + web-seed + torrent_url wiring, DHT off |
| `feat/taosnet-license-classifier` | feat | 0 | 280 | yes | — | 0 | +0/-0 | — | feat(taosnet): license-eligibility classifier for redistribution |
| `feat/unified-model-store-rkllama` | feat | 0 | 345 | yes | — | 0 | +0/-0 | — | fix(rkllama): fold Kilo review on the unified-model-store slice (#1548) |
| `fix/1548-scan-rkllama-service-dir` | fix | 0 | 329 | yes | — | 0 | +0/-0 | — | fix(models): use rkllama.service explicit unit in systemctl fallback (fold Kilo #1548) |
| `fix/1548-surface-rkllama-pull-error` | fix | 0 | 347 | yes | — | 0 | +0/-0 | — | refactor(rkllama): fold Kilo review on the pull-error parser (#1548) |
| `fix/1603-user-wallpaper-wins-over-theme` | fix | 0 | 367 | yes | — | 0 | +0/-0 | — | fix(desktop): user's wallpaper pick wins over theme default on login (#1603) |
| `fix/1616-opencode-discovery` | fix | 0 | 327 | yes | — | 0 | +0/-0 | — | fix(agents): log when TAOS_OPENCODE_BIN is set but not executable (fold Kilo #1616) |
| `fix/163-hide-admin-settings` | fix | 0 | 354 | yes | — | 0 | +0/-0 | — | fix(doc-gate): exempt test files from structural rules (#171) |
| `fix/165-backup-scheduler-executor` | fix | 0 | 350 | yes | — | 0 | +0/-0 | — | fix(scheduler): execute due scheduled tasks incl. auto-backup, allow-list dispatch (#165) |
| `fix/1668-weather-csp-open-meteo` | fix | 0 | 367 | yes | — | 0 | +0/-0 | — | fix(weather): allow open-meteo origins in CSP connect-src (#1668) |
| `fix/1686-persist-key-discard` | fix | 0 | 330 | yes | — | 0 | +0/-0 | — | fix(agents): persist the stale-key discard (fold Kilo review on #1686) |
| `fix/1697-rkllama-provider-port` | fix | 0 | 331 | yes | — | 0 | +0/-0 | — | fix(config): heal stale rkllama provider port :8080 -> :7833 on load (#1697) |
| `fix/173-npm-dependabot-overrides` | fix | 0 | 355 | yes | — | 0 | +0/-0 | — | fix(deps): override lodash-es/uuid/nanoid to clear Dependabot alerts (#173) |
| `fix/174-decision-routing-dedup` | fix | 0 | 369 | yes | — | 0 | +0/-0 | — | fix(governance): fold Kilo review on #1667 (no grant leak + honest exec message) |
| `fix/bump-rkllama-pin-chat-fix` | fix | 0 | 294 | yes | — | 0 | +0/-0 | — | fix(rkllama): bump pinned rkllama ref to main HEAD for the /api/chat fix (#1710) |
| `fix/delegation-org-hardening` | fix | 0 | 305 | yes | — | 0 | +0/-0 | — | fix(governance): create _reporting_lock at construction, not in init() |
| `fix/gpu-lease-auth-hardening` | fix | 0 | 306 | yes | — | 0 | +0/-0 | — | fix(cluster): authenticate GPU lease endpoints + validate inputs + widen ids |
| `fix/retro-hygiene-heartbeat-apns` | fix | 0 | 300 | yes | — | 0 | +0/-0 | — | fix: fold Kilo review WARNINGs on retro-hygiene PR |
| `fix/rkllama-backend-name-registry-match` | fix | 0 | 294 | yes | — | 0 | +0/-0 | — | fix(config): rename rkllama backend local-npu to local-rkllama so installed models resolve (#1710) |
| `master` | other | 0 | 18 | yes | — | 0 | +0/-0 | — | Update README.md |
| `release/1.0.0-beta.32` | release | 0 | 357 | yes | — | 0 | +0/-0 | — | release: 1.0.0-beta.32 (Weather search fix, wallpaper-persistence fix, Apple client foundation) |
| `release/1.0.0-beta.33` | release | 0 | 333 | yes | — | 0 | +0/-0 | — | release: 1.0.0-beta.33 (rkllama unified model store + #1548 fix, GPU-lease coordination, scheduler execution) |
| `release/1.0.0-beta.34` | release | 0 | 316 | yes | — | 0 | +0/-0 | — | release: 1.0.0-beta.34 (rkllama model discovery + provider port heal for existing installs, opencode discovery, agent key persist) |
| `release/1.0.0-beta.35` | release | 0 | 284 | yes | — | 0 | +0/-0 | — | release: 1.0.0-beta.35 (rkllama agent chat fix #1710, copy/select messages, update badge, cluster GPU-lease auth) |
| `robotics-edition` | other | 0 | 0 | yes | — | 0 | +0/-0 | — | docs(design): beta.44 comparison + adoption record |
| `sync/dev-to-master` | sync | 0 | 157 | yes | — | 0 | +0/-0 | — | Merge dev into master: land identity epic + audit fixes + all unreleased work |
| `sync/dev-to-master-2` | sync | 0 | 152 | yes | — | 0 | +0/-0 | — | Merge remote-tracking branch 'origin/dev' into sync/dev-to-master-2 |
| `sync/dev-to-master-beta41` | sync | 0 | 76 | yes | — | 0 | +0/-0 | — | Merge dev into master: v1.0.0-beta.41 |
| `sync/dev-to-master-beta42` | sync | 0 | 49 | yes | — | 0 | +0/-0 | — | chore(release): v1.0.0-beta.42 version bump + changelog (#2061) |
| `sync/dev-to-master-beta43` | sync | 0 | 20 | yes | — | 0 | +0/-0 | — | Merge dev into master: v1.0.0-beta.43 |
| `cla-signatures` | other | — | — | — | — | — | — | unrelated/deep | @hognek has signed the CLA in jaylfc/taOS#1686 |

## Adoption shortlist

Excluded by policy: 34 branches already merged (`ahead == 0`), the one
dependabot branch, the 7 `exec/tsk-*` scratch branches, and docs-only
branches whose content is already `fully_absorbed`. What's left below is
picked for genuine, non-redundant signal, weighted toward our stated focus:
agents/providers/memory/permissions/trust/robotics.

| Branch(es) | What it adds | Why it might matter here | Overlap risk | Call |
|---|---|---|---|---|
| `feat/app-runtime-v1` (+ `feat/userspace-container-tier`, `feat/userspace-consent-ui`, `feat/consent-project-picker` as smaller slices of the same epic) | A full **sandboxed third-party "userspace app" runtime**: `.taosapp` package install/validate, capability broker with permission + namespace + path enforcement, install-time consent (+re-prompt on permission changes), per-app namespaced KV/table data store, SSRF guard on install, sandboxed iframe window + parent bridge, Docker container-app backend (separate from agent deploy), and (this branch's tip commit) path-traversal + header-stripping hardening on the broker proxy. | This is a **capability-broker + consent-gate + namespace-isolation** pattern for a different actuation surface (installed desktop apps) than our Bean-3 consent gate (agent actions) — genuinely complementary trust-plane thinking, not a duplicate. Largest "ahead" of any branch (21 commits) and the biggest real (non-absorbed) diff — 34 of 40 touched files are new to us. | Low direct file conflict (new `tinyagentos/userspace/` + `desktop/src/apps/StoreApp` paths we don't have), but **conceptual** overlap with Bean-3/cognitive-firewall is real — read together, don't build in parallel. | **Recommend** — read the design, don't blind-adopt; decide whether Bean-3's consent model should absorb this or stay separate. |
| `feat/provenance-sandbox-tiers` | Extends the same userspace-app runtime with **provenance tiers + a capability-ceiling model** (broker/permission API enforce a ceiling by install provenance), a provenance badge in App Studio's publish view. Depends on `feat/app-runtime-v1`'s files. | Direct **naming collision** with our own Bean-0 provenance chain — but this is *install-source provenance for sandboxed apps*, not *model-inference-receipt provenance*. Worth reading precisely because the vocabulary overlaps: could either inform Bean-0's design or cause confusion if merged verbatim under the same term. | Medium — same files as `app-runtime-v1`, plus the term "provenance" itself needs disambiguating before any adoption. | **Recommend** (read together with `app-runtime-v1`), flag the naming collision explicitly if pursued. |
| `feat/agent-scope-requests` (residual only) | Already mostly adopted (`#1921`, 16/27 files absorbed). The two commits still genuinely new: `04e2865c5` "fold scope-request approval security findings (#1921)" and `1389f1f4e` "take the per-request lock in deny_scope_request too" — both post-merge security/concurrency hardening on the feature we already took. | Small, concrete, security-relevant follow-ups to a feature already in our trust/permissions surface. | Low — narrowly scoped to `agent_scope_requests_store.py`/routes we already have. | **Recommend** — cheap, high-confidence hardening we're currently missing. |
| `feat/agent-project-files-access` (residual only) | Already mostly adopted (`#2100`, 7/15 files absorbed). Residual: `51d6d3537` "surface Files in the invite bundle + fix agent API-surface docs" — a follow-up to the files_read/write feature. | Small permissions-surface polish on top of something we already ship. | Low. | **Recommend** — small, low-risk follow-up. |
| `design/trust-comms-layer` | A **governance lifecycle state machine for the agent registry** (status transitions + audit trail) and **per-user ownership scoping** of the knowledge store and projects routes, plus a design spec doc (`docs/specs/2026-06-09-trust-comms-layer-design.md`). | Directly hits our "trust" focus area by name. | **High** — verified directly: our `tinyagentos/governance/policy_store.py`, `tinyagentos/agent_registry_store.py` (status/lifecycle), and `tinyagentos/knowledge_store.py` (`user_id` scoping) already implement equivalent concepts, built through a *different* commit lineage (none of this branch's 7 commits are ancestors of our history). This is a parallel, independently-evolved implementation of the same idea — merging the code would conflict, not add. | **Defer** — the spec doc may be worth a read for framing, but do not adopt the code; we already have a (differently-shaped) equivalent. |
| `fix/npu-backend-install-runs-service` + `feat/npu-backend-one-tap-install` | Store-install self-heal for the rkllama NPU backend (actually creates+starts+verifies the systemd service, not just claims success) plus a one-tap install trigger from the setup checklist. | Robotics-relevant: rkllama runs the NPU backend on RK3588-class edge boards, the same hardware class our robotics bridges (`robotics/tank_fleet_mcp.py`, `robotics/camera_mcp.py`) plausibly deploy alongside. Install reliability for edge NPU deploys is directly useful. | Low — narrowly scoped install/service-verification code, 7-8 new files. | **Recommend** — small, concrete reliability win for edge/robotics deploys. |
| `feat/os-level-agent-invites` | Hardens the OS-level agent invite flow: strips project scopes and validates `display_name` on invite acceptance (fold of a security review, `#1918`). | Permissions/invite hardening, adjacent to the scope-request work we already track. | Low (7 of 8 files genuinely new, narrowly scoped). | **Recommend** — small permissions hardening worth a look. |
| `feat/assistant-studio` + `fix/assistant-studio-optional-catalog` | A full **Assistant Studio** desktop workspace app for a personal-assistant agent (this is the "#2103/#2104 Assistant Studio" already flagged as deferred in `beta44-adoption.md`). | Confirmed still true at fan-out scale: this is the 2nd/5th-largest branches by ahead-count in the *entire* 197-branch set, but it's desktop-UI-heavy with low overlap with our robotics/Bean/memory focus. | Low conflict, but large adoption cost for out-of-focus surface area. | **Defer** — unchanged call from the beta.44 doc; worth a dedicated port only if we decide to ship the workspace app. |
| `feat/gamestudio-ai-maker` | Game-maker studio app (Create/Editor/Library/Share rail). | Large diff (38 files) but 31/38 already absorbed — nearly redundant already; the residual 7 files are cosmetic desktop wiring. | Low, but low value too. | **Skip** — mostly already present; residual isn't focus-area relevant. |
| `feat/nous-portal-provider` | Nous Portal cloud provider. | Already adopted (`#2102`); the 3 "ahead" commits here are exactly the already-adopted/-deferred set (`#2102`, `#2098` deferred, `#2092` adopted) — nothing new. | — | **Skip** — fully covered by the existing beta.44 adoption + deferral record. |
| `feat/council-role-registry`, `feat/invite-s3-a2a-stream`, `feat/agent-governance-slice1` | Multi-agent "council" role registry, an authenticated A2A SSE bus stream, and a governance action-class policy store. All three sound squarely on-focus (multi-agent trust/governance). | This is the most interesting methodological finding of the whole matrix: **all three are already present on `robotics-edition`**, byte-identical, at `tinyagentos/council/*`, `tinyagentos/routes/a2a_bus.py`, and `tinyagentos/governance/*` — confirmed with a direct `git diff origin/robotics-edition <branch> -- <path>` (empty for council/ and a2a_bus.py; one unrelated one-line difference for governance/action_classes.py, where **our version is stricter** — it already includes `"delegate"` in `SENSITIVE_ACTION_CLASSES`, which this branch's copy lacks). Git shows `ahead > 0` only because the content landed on our side through different commit hashes (squash/rebase upstream). | None — content already converged. | **Skip** — nothing to adopt; also the clearest evidence of "where we're already ahead" in this scan. |
| `feat/hailo-slice-1` … `feat/hailo-slice-5`, `docs/hailo-backend-design`, `fix/hailo-real-repo-build`, `fix/hailo-pin-idempotency` | The Hailo-10H NPU backend build-out (port reservation, install script, manifest, runtime detection/provider adapter, install-time gates). | Directly robotics/edge-AI relevant by name. | None — checked directly: our `scripts/install-hailo.sh` (492 lines) is a **superset** of `feat/hailo-slice-2`'s version (479 lines) and already contains the exact fix that `fix/hailo-real-repo-build` makes (hailo-ollama ships inside the Hailo repo, it isn't a standalone clone target) — i.e. we're already past all five slices *and* the fix. | **Skip** — fully superseded; this is the robotics-focus confirmation that our fork is already ahead here, matching what `AGENTS.md`/`beta44-adoption.md` already claim. |

## pk-client rpg drift

Built RPG symbol databases (`pk-memory memory rpg`) scoped to `tinyagentos/`
for our current tip and for the top-ranked candidate, `feat/app-runtime-v1`
(checked out via a temporary `git worktree`, removed after use), then ran
`pk-client rpg drift` between them:

- our tip: 186 modules / 5590 symbols / 126 capabilities
- `feat/app-runtime-v1`: 95 modules / 2769 symbols / 77 capabilities
- `capabilities_in_left_only` (in the branch, missing from us): **empty**
- `capabilities_in_right_only`: 49 capability buckets

Read honestly: this does **not** mean the branch's userspace-sandbox feature
is already present — a direct path check confirms `tinyagentos/userspace/`
does not exist on our tip. The rpg tool's "capability" is a coarse
name-bucketing heuristic (roughly: first word of a module/symbol name), and
several of the branch's new modules (`broker.py`, `store.py`) happen to
bucket under generic terms (`Broker`, `Store`, …) that our much-larger tree
already has unrelated matches for. So the drift output is real but weak
signal here — useful as a sanity check that adopting this branch would not
regress or collide with a named capability area, not as proof the feature
exists elsewhere. The git-diff-based `absorbed_files` check in the matrix
above is the stronger signal for this branch (6/40 absorbed — genuinely new).
DBs and the raw JSON are saved under `reports/rpg-drift/` for reference. (The
sandbox here lacked the `sqlite3` CLI that pk-client's `rpg` commands shell
out to — `apt-get install sqlite3` failed against this specific mirror. Used
a small local, throwaway `sqlite3 -json <db> <sql>` shim backed by Python's
stdlib `sqlite3` module, matching the exact one-shot invocation pk-client
makes; it is not part of this commit.)

We did not build/compare a third RPG db — `design/trust-comms-layer`'s
overlap was already conclusively resolved by direct file diff (see shortlist
above), so a symbol-level comparison wouldn't have added signal proportional
to the cost of a third full `tinyagentos/` rpg build.

## Where our fork is already ahead

Confirmed at fan-out scale, not just for beta.44:

- **Hailo NPU backend** — our `scripts/install-hailo.sh` supersedes all five
  `feat/hailo-slice-*` branches plus their follow-up fixes; verified by
  direct file diff, not just commit-graph position.
- **Multi-agent governance/council/A2A** — `tinyagentos/council/*`,
  `tinyagentos/governance/*`, and the A2A bus route already match (or in one
  case, exceed) three dedicated feature branches for the same surface,
  despite no ancestry link between them and our history.
- **Bean trust stack, three-plane memory model, robotics edition** — as
  already recorded in `beta44-adoption.md`; nothing in this 197-branch scan
  surfaced an equivalent anywhere else in the fork.

## Redo the comparison later

```
git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
git fetch origin --prune --no-tags     # refresh all branch tips
git fetch origin --unshallow           # only needed once; no-op after
python3 scripts/branch_matrix.py       # regenerate reports/branch-matrix.{json,md}
```

To re-check one branch in isolation (e.g. after it gets new commits):

```
python3 scripts/branch_matrix.py --branch feat/app-runtime-v1
```
