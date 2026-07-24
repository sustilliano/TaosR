# Branch matrix

Generated 2026-07-24T07:32:33.587814+00:00 — 197 branches on `origin` vs. base `origin/robotics-edition`.

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
