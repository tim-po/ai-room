# AI Room handoff — 2026-10-05

## Git entry point

Clone `https://github.com/tim-po/ai-room.git` and check out `education/product-experience`. This branch contains the latest deployed frontend source plus this handoff. Backend work is also preserved on `engine/admin-contract-v1`; it is not wholesale merged into the frontend. Supporting branches are pushed under their existing names.

The key briefs and reviews are copied into `docs/handoff-evidence/` so they are available from Git. Absolute paths elsewhere in this document identify the original Linux host and its private operational artifacts; they will not exist in a fresh clone. Screenshots, databases, uploads, private credentials and session logs are not included in these evidence copies. Obtain host access if those are needed. Do not assume a fresh clone has staging state or test logins.

## Read this first

The owner wants a local app session to take over the AI Room project after rejecting the latest frontend as visually poor. This file records the current state and an evidence-based verdict. It is not a release acceptance or authorization to launch more loops.

**Verdict: useful engineering improvements, but a poor/incomplete result against the redesign brief.** Preserve working persistence, recovery, access control and navigation. Do not treat this as an accepted design, and do not assume another large autonomous loop will fix the product without changing how decisions and priorities are managed.

The user explicitly requested the latest frontend be deployed so they could test it. That staging deployment is complete. They subsequently asked whether loop counts were inflated and whether the real work was any good. The current request is this handoff.

## Product and owner intent

- Independent Russian-first AI learning platform, repository historically identified as `tim-po/ai-room`.
- Complete learner experience: welcome, optional multi-interest onboarding, skill map, discovery, text/video lessons, practice, useful feedback, saved work, return journeys, profile, help and account/access states.
- Skill map includes Basic AI Knowledge plus Coding with AI, AI Teams, Content Creation, Automation and Agents, with recursive branches and multiple interests.
- Owner explicitly rejected previous visual quality. Required a substantial, distinctive redesign, not a recoloring or generic card dashboard.
- Onboarding must appear automatically for genuinely fresh learners. First useful activity must be achievable, concrete and connected to feedback and saved progress.
- Preserve accounts, IDs, entitlements, attempts, completions, evidence, practice, content, media and prototypes. Existing old production site and billing are outside this independent staging project.
- Content includes synthetic fixtures. Do not imply real learning efficacy, mastery, users or retention from test data.

Authoritative redesign brief:
`/home/claude/bot-swarm/data/_loops/ai-room-product-experience/product-brief.txt`

Backend peer brief:
`/home/claude/bot-swarm/data/_loops/ai-room-engine-admin/product-brief.txt`

Historical context, subordinate to the newer brief:
`/home/claude/bot-swarm/data/_loops/education-platform-for-people-learning/product-brief.json`
and `manager-loop-policy.json` in that directory.

## Where the code is

All paths below are on the existing Linux host. A session on a different machine must connect to this host or obtain the actual branches and artifacts; these are not Mac-local paths.

| Path | Branch / purpose | Last verified HEAD |
|---|---|---|
| `/home/claude/ai-room` | `education/fresh-platform`; historical main working checkout; historical handoff drafting location | `e4e8314d9afe0c4c996859426d49f99783b560c1` |
| `/home/claude/ai-room-product-experience` | `education/product-experience`; latest frontend candidate; start source inspection here | `548e724cc954e8efdeb73cc4cc1a14aa3d615edf` |
| `/home/claude/ai-room-engine-admin-work` | `engine/admin-contract-v1`; backend/admin peer | `358599ee91a2de0ae184f18212d210afef0031c6` |
| `/home/claude/ai-room-pending-review` | `education/worker-pending-review`; earlier candidate | `bc4ba3c` |
| `/home/claude/ai-room-ai-skill-tree` | `education/skill-tree-ai` | `d7ece4c` |
| `/home/claude/ai-room-skill-tree` | `education/skill-tree` | `f249fdb` |
| `/home/claude/ai-room-releases/548e724` | Exported deployed release, not the development checkout | `548e724` |

Recheck git status and worktrees before editing. Do not blindly merge the backend branch: some authorized backend commits were already integrated into the frontend branch, and other work remains separate. The historical main checkout is NOT the deployed candidate. README acceptance claims refer to an older release (`bc700c5`), not the current redesign.

No applicable AGENTS.md was found in the AI Room checkout trees during this work. Check again in the receiving environment.

## Stack and useful source locations

- Python, Flask 3.1.2, Jinja, SQLite, native JavaScript/CSS and HTML media. This frontend has no Node build step.
- Gunicorn 23.0.0, two workers. Existing venv: `/home/claude/ai-room/.venv`.
- App factory: `club:create_app()`.
- `club/__init__.py`: routes, sessions, access checks, practice and base database initialization.
- `club/onboarding.py`: persistent onboarding and recommendation selection.
- `club/continuation.py`: unfinished learning and saved-work continuation.
- `club/skills.py`, `club/skills_schema.sql`: skill graph and related state.
- `club/measurement.py`: existing learning metrics; semantic issues remain.
- `club/support_admin.py`: private support responses and audit history.
- `club/static/atlas.js`, `atlas.css`: map and navigation.
- `club/static/atelier.css`, `club/templates/`: visual system and learner surfaces.
- `club/static/lesson-context.js`: map return context and media recovery.
- `club/teaching.py` and related pipeline/worker modules: teaching uploads/jobs.
- `scripts/verify_retained_state.py`: validates retained database rows, integrity and media.

Use disposable databases for tests. Never seed/reset the installed staging database to make a demonstration pass. Review individual additive migration commands instead of following stale README upgrade instructions wholesale.

## What is deployed and how to operate it

- Public staging: https://airoom.nolimlabs.uk/
- Login: https://airoom.nolimlabs.uk/login
- Skill map for anonymous visitors: https://airoom.nolimlabs.uk/?view=map
- Health: https://airoom.nolimlabs.uk/health
- Current health build: `6f9eea9168449287a46c3e08f7ac81237396a85f` (deployed 2026-10-08; PR tim-po/ai-room#1), schema 6, status `ok`. Before it `f0b4bd1` (same day), then `7f9b053`.
- Local listener: `127.0.0.1:8098` behind the existing proxy.
- User systemd service: `ai-room.service`.
- Service override: `/home/claude/.config/systemd/user/ai-room.service.d/staging.conf`.
- WorkingDirectory now `/home/claude/ai-room-releases/6f9eea9`. It includes the built React bundle in `club/static/app/` (built locally with `cd web && npm ci && npm run build`; Node isn't needed at runtime).
- ExecStart uses `/home/claude/ai-room/.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8098 club:create_app()`.
- EnvironmentFile now `/home/claude/ai-room-staging-private/state-dae0217/frontend-6f9eea9.env` (same keys as `frontend-7f9b053.env`, new build id), originally the same values as `frontend-548e724.env`, plus `CLUB_PUBLIC_URL=https://airoom.nolimlabs.uk` (assistant links, calendar events, OAuth issuer) and `CLUB_DEMO_CHECKOUT=1` (the staging-only demo membership switch).
- `ai-room-teaching.service` still runs release `dae0217` with `staging.env`; it was only paused during the switch.
- 2026-10-07 content: ran `install-legacy-lessons --retire-synthetic`, which added 3 real courses, 6 modules and 8 lessons and archived the synthetic fixture courses. Learner rows were kept and no rows were lost; this was rehearsed twice on copies. Its own backup is `club.sqlite.before-legacy-20261007094544300190.sqlite`.
- 2026-10-07 rollback checkpoint: `/home/claude/ai-room-staging-private/rollback-7f9b053-20261007094542/`, containing the previous `staging.conf` and a database backup taken while writes were paused. To roll back the code, restore that `staging.conf` and restart; the new tables are additive.
- 2026-10-08: `install-legacy-lessons --retire-synthetic` on `f0b4bd1` published 6 free materials (4 guides, 2 use cases); rehearsed on a database copy first, no learner rows changed. Rollback checkpoints: `/home/claude/ai-room-staging-private/rollback-f0b4bd1-20261007233254/` (back to `7f9b053`) and `rollback-6f9eea9-20261007234114/` (back to `f0b4bd1`); each holds the previous `staging.conf` and a database backup. Static files are now cached at Cloudflare's edge (`cf-cache-status: HIT`).
- Network caveat, observed 2026-10-07: from a Russian ISP, responses through the Cloudflare tunnel often stall after about 16–19 KB. This affects old files too (for example `atlas.css`), and the 435 KB React bundle stalls on most attempts. From the VPS itself or other networks, everything loads in about 2 seconds. Learners in Russia need a path that doesn't go through Cloudflare.
- Persistent state stays at `/home/claude/ai-room-staging-private/state-dae0217`. Its old name does NOT mean old code is deployed.
- Release `instance` is a symlink to that persistent state directory. Preserve it: media and session signing key depend on this layout.
- State includes `club.sqlite`, `media/`, `teaching-uploads/`, `session.key` and private environment files.
- Preserve prototype routing under `/prototypes/`; the original prototype service used port 8097.

Read-only operational checks:

```sh
systemctl --user status ai-room.service
systemctl --user cat ai-room.service
curl -fsS https://airoom.nolimlabs.uk/health
```

Do not print entire environment files. They contain secrets. Preserve the stable signing key and database/media/upload paths when changing releases.

### Test accounts

Saved credentials: `/home/claude/ai-room-staging-private/state-dae0217/reviewer-credentials.txt` (private). Password intentionally omitted here.

- `learner@example.test`: free learner
- `member@example.test`: member
- `revoked@example.test`: revoked-access test
- `editor@example.test`: editor
- `admin@example.test`: administrator

Existing accounts may already have completed onboarding. Use an isolated fresh fixture to assess first-visit behavior, rather than clearing their progress.

### Deployment verification and rollback

Previous release: `/home/claude/ai-room-releases/dae0217`.

Rollback checkpoint: `/home/claude/ai-room-staging-private/rollback-548e724-20261005091221/` contains the previous `staging.conf` and paired `state/` backup.

Deployment rehearsed migrations on a copy, stopped staging writers, backed up state, ran `init-skills`, `init-onboarding`, and `init-support`, and verified all existing rows in 47 tables plus media/uploads were retained. No new curriculum or assessments were published. Existing learner data was preserved.

Restore the previous service configuration for a compatible code rollback; retain the additive migrated database and subsequent learner writes. Do not overwrite live state with an old backup merely to roll back code. Disaster restoration requires quiescence and deliberate handling of subsequent writes.

Deployment checks:

- 38 targeted tests passed: onboarding, continuation, challenge presentation, retained state, current-content access and support admin.
- Public Chromium navigation passed at 360, 390, 768 and 1440 widths.
- Evidence: `/home/claude/ai-room-staging-private/check-548e724-final/navigation.json` and screenshots in that directory.
- Original navigation script used obsolete anonymous map URLs. Temporary corrected script: `/tmp/check-airoom-navigation-548e724.py` explicitly uses `?view=map`. Initial failed runs remain in `check-548e724` and `check-548e724-current`; they are not the final passing run.
- Temporary deployment scripts: `/tmp/deploy-airoom-548e724.py` and `/tmp/activate-airoom-548e724.py`. Historical evidence, not reusable installers: inspect before any reuse.

These checks establish deployment health and bounded behavior, NOT visual/product acceptance or full authenticated journey coverage.

## Since 7f9b053 (on the branch, not yet on staging)

- **Обзор** replaces the library: a store front of shelves over lessons, courses, materials and coming courses, and an instant search (header dialog, `/`, ⌘K, and inline). See README "Обзор and search".
- **Профиль** replaces Моё обучение and took over the club page. The nav is now Карта навыков · Обзор · Профиль.
- **Skill map:** the stacked cards stay; the map card is nearly the window's height, and the wheel scrolls the page down to it before panning.
- **Theme switch:** the sunrise is unchanged, but the map holds its colours and fades through the switch, because repainting its ~60 composited nodes every frame was the stutter.
- **Speed:** first-page data is embedded in the HTML, links prefetch their data, static files are versioned and immutable, and fonts are WOFF2.
- **Staging slowness (measured 2026-10-07):** the app answers in 3–11 ms on the VPS. Each request takes 0.5–1.6 s through Cloudflare (owner's route via Oslo, tunnel to Almaty/Warsaw); direct ping to the VPS is 60 ms. Serving the hostname directly from the VPS (unproxied DNS plus Caddy) is the owner's decision.
- **Skill map gamification:** control points per module, ranks Новичок → Мастер per course, a one-time celebration, Звания in Профиль; pinned row labels show where you are when zoomed in.
- **Theme switch:** with view transitions the interface cross-fades and only the sky animates (smooth everywhere); the token animation remains the fallback.
- **Imported materials:** 4 free guides and 2 free use cases from app.airoom.club (`club/content/legacy/materials/`), without the old club's promotion. «Регистрация и оплата Claude / ChatGPT из РФ» was deliberately not imported: it teaches evading the providers' region and ban checks. Five more free guides (language tutor, Codex for beginners, Claude Code tokens, website in an evening, YouTube research agent) still need the owner's signed-in browser session to convert.
- **Direct serving from the VPS** is blocked without root: port 443 is taken by `xray` and nginx on 80 is root-owned. Options: root access for a Caddy/nginx vhost, or a high port with a Cloudflare DNS-01 certificate.

## Verdict on the real work

Reviewed the 54 actual report entries, relevant code and commit history, selected prototype, and independent rendered screenshots. This was not a full security audit or a new exhaustive acceptance run.

**Good and worth retaining:** persisted multi-step onboarding; save/retry/conflict behavior; unfinished cross-branch work; separate last saved result; support reply visibility and keyboard recovery; map search/list/selection context through lessons; several contrast and mobile layout repairs. Independent reviewers confirmed meaningful fixes rather than only trusting builder test counts.

**Weak against the brief:** inspected visuals are coherent but still sparse and utilitarian: rectangular nodes, generic panels, limited distinctive imagery and composition. Consistent colors/fonts did not fulfill the requested substantial redesign. This is our visual assessment; prior reviewers praised parts of the identity while still rejecting overall acceptance.

**Learning experience still fails:** the first lesson promises an example but asks the novice to invent a task. A concrete source case, worked comparison and useful instructional feedback remain absent. Saving confirms storage, not quality of learning. The selected Atelier prototype contained a concrete exercise that was not carried into the actual first-result journey.

**Personalization is incomplete:** `club/onboarding.py` recommendation selection chooses the first accessible published lesson ordered by course/module/lesson IDs and position. Collected interests, experience and available minutes do not determine that query. Independent reviewers observed a five-minute beginner receiving a ten-minute agent lesson.

**Management/prioritization was poor:** 25 research/design/review reports repeatedly identified the same core blockers. The backend/UI handoff did not resolve the approved first activity. All six final engineering turns refined video recovery while the central first useful result remained incomplete. Those media fixes are legitimate but were a poor allocation against the unresolved mission.

**Reviewers were mostly honest:** they repeatedly returned `needs_work`, not a false acceptance. The later owner-authorized test deployment should never be represented as those reviewers approving the latest build.

### Remaining material gaps

1. Deliver a real first novice task, source-grounded comparison/feedback, revision, save and reopen journey.
2. Make onboarding recommendations meaningfully use preferences/time, or remove unsupported personalization claims.
3. Rework visual composition to the owner's standard; obtain feedback on a small rendered end-to-end slice before extending it everywhere.
4. Fix meaningful-return metrics: passive lesson GET currently contributes to return activity. Do not imply genuine learning from page visits.
5. Complete real challenge/assessment/content review. A backend reviewer found a longest-answer strategy could score 21/21 on the reviewed forms; do not publish those as accepted assessments.
6. Full access/media/error/native-zoom/accessibility and exact-build independent acceptance remain incomplete. Last substantive independent frontend review targeted `cddc8b2`; subsequent changes through `548e724` were mainly builder-tested media recovery.
7. Real provider-backed teaching AI remains unverified. Approved configuration/spend gates were absent; do not borrow unrelated credentials or silently enable paid calls.

## Loop accounting incident — corrected facts

Loops:

- `ai-room-product-experience`: run ID `031c75b8eb63565e86d384431f872b8a`, ended 2026-10-05 around 08:58 UTC, `turn_limit`.
- `ai-room-engine-admin`: ended 2026-10-04 around 21:55 UTC, `turn_limit`; also suffered usage-limit failures and manager timeouts.

For the frontend loop, engine result `152` main turns breaks down as:

| Main-phase outcome | Count |
|---|---:|
| Actual reported work | 44 |
| Codex usage-limit exits | 85 |
| Manager timeouts | 23 |
| Total counted | 152 |

There were 10 additional real wrap-up reports: **54 actual reported work turns**, consistent with the roughly 60 timeline items the owner saw. Breakdown of those 54 report entries: 15 frontend engineer, 25 research/design/review, 14 manager. Reports do not prove all 54 were equally productive. The run also has a synthetic briefing event; do not count that as another substantive work report.

Earlier in this conversation we mistakenly described all `needs_work`/`work_remaining` events as real work and attributed the discrepancy mainly to parallelism/timeouts. That was corrected after checking event note contents and `status.jsonl`. Do not repeat the earlier 129-real-main-turn claim.

Root causes found in Loopyard source:

- `mcp_loops/headless.py::_run_headless`: a CLI exit without a status report falls back to role-specific `needs_work`/`work_remaining`, even for a usage-limit error.
- `mcp_loops/runner.py::_raw_turn`: increments the main counter for those outcomes and timeouts.
- Main budget checked between entire `stepOrder` cycles, allowing 152 counted attempts against saved `turnLimit: 120`.
- At engine turn 152 the manager reported “88 turns remain”: manager budget understanding diverged drastically from authoritative progress.
- Timeline uses agent reports, roster and thought-log; synthetic failed engine attempts are not ordinary agent reports. Raw `status.jsonl` has 105 entries: 54 real reports and 51 machinery entries (28 parallel, 23 re-nudge). The approximately 60 visible items are not evidence of missing 90 successful turns.
- Parallel agents genuinely count individually, but that does not explain away the 85 usage-limit failures.

No counter/runtime fix was implemented in this handoff task. Needed behavior: distinguish work reports, execution attempts and recovery; surface quota blockers and stop pointless scheduling; enforce budget predictably; supply authoritative remaining budget to managers; reconcile UI numbers with auditable event types. Add regression tests for quota exits and budget crossing. Preserve original historical evidence rather than rewriting it to make totals look clean.

## Codex models actually observed

Session `turn_context` records showed `gpt-6-astra` for most frontend/product work and backend/admin attempts. `gpt-6.1-sol` appeared in the frontend loop's final stretch, including frontend engineer sessions. Neither saved loop config explicitly pinned a model; inspected sessions did not specify reasoning effort. Do not claim high/max effort, or assume a model downgrade caused the design failure. Failed attempts are included in session counts.

Codex session records are under `/home/claude/.codex/sessions/2026/10/04` and `/05`. Treat conversations as private. The owner values original manager-session continuity; do not casually replace an existing manager with a fresh one when resuming work.

## Evidence index

Root: `/home/claude/bot-swarm/data/_loops/_output/ai-room-product-experience/deliverables/`

- `selected-direction.json`: Atelier selection and reasons, mandatory corrections.
- `art/VISUAL-SYSTEM.md`, `art/index.html`, `art/gallery.html`: two prototype directions, typography/art and captures.
- `art/atelier-lesson-1440-viewport.png`: chosen concrete lesson benchmark.
- `art/atelier-map-1440-viewport.png`: chosen map benchmark.
- `research/RESEARCH-DECISIONS.md`: research and adopted decisions; this handoff did not independently reverify external sources.
- `copy/ru-RU.json`: proposed Russian copy.
- `learning-003/content-decision.json`: approved narrow first source-check activity. Final reviews reference SHA256 `668ac857e48f2cba0d45513d443050cb0c8bd3636bcd4fd605bd440284b7a4d2`.
- `learning-020/REVIEW.md`: late independent learning verdict, novice mismatch, feedback and measurement blockers.
- `visual-critic-020/REVIEW.md`: late independent visual/interaction verdict with screenshot-specific findings.
- `visual-critic-020/lesson-1440.png`, `support/map-1440-viewport.png`, `support/map-390-viewport.png`: inspected implemented screens.
- `qa-016/REVIEW.md`: latest independent QA evidence.
- `frontend-031` through `frontend-038`: final UI/navigation/media implementation reports and galleries.
- `frontend-038/REPORT.md`: latest builder result for deployed `548e724`.

Loop source-of-truth records:
`/home/claude/bot-swarm/data/_loops/ai-room-product-experience/{config.json,run.json,status.jsonl,turns.json,progress.json,prompts/}`

Shared coordination:
`/home/claude/bot-swarm/data/_loops/_output/ai-room-shared-coordination/`

Backend evidence:
`/home/claude/bot-swarm/data/_loops/_output/ai-room-engine-admin/deliverables/`
including `backend-continuation-006`, `admin-graph-006`, and `ai-pipeline-006/REPORT.md`.

## Related Loopyard context

Loopyard is the orchestration tool, not the AI Room Flask app. Its source is `/home/claude/loopyard-devhome`, branch master, last verified `e942421`. MCP is normally at `127.0.0.1:8771/mcp`; operator dashboard https://dashboard.nolimlabs.uk/; hosted control plane https://swingshift.nolimlabs.uk/ and `/admin`.

Owner's Anthropic account was suspended; Loopyard was being made CLI-agnostic with Codex/Cursor subscriptions and eventual Claude return. Do not assume those subscriptions supply approved API credentials for AI Room's provider-backed teaching pipeline.

Latest recorded Loopyard signed release: `0.1.3-beta.6`, source `5b17d26`. A later session-state-root fix `e942421` was committed/pushed, but engine restart was previously deferred to preserve active loops; recheck actual running code before diagnosing. Do not conflate a repository fix with a running-service fix. Preserve untracked `.claude/` and `docs/TONY-BETA-PLAN.md` in that checkout.

## Suggested next-session sequence

1. Confirm source, deployed health and user intent. Read the brief and inspect the actual pages with the owner’s criticism in mind.
2. Keep the current candidate as a recoverable baseline. Do not restart large loops until quota handling and truthful turn accounting are addressed.
3. Produce one complete, visually strong first-visit → concrete exercise → feedback → saved return slice. Review rendered desktop/mobile screens with the owner before multiplying the design across the app.
4. Retain proven functional work. Integrate backend/content changes explicitly, with separate isolated test data and data-preservation checks.
5. Require a same-build independent product review before calling the redesign accepted. Count tests as behavior evidence, not proof of beauty or educational usefulness.

After writing the initial handoff, the owner explicitly requested pushing the handoff and code to Git. This publication adds documentation and preserves the existing development branches; it does not approve the product, merge the backend wholesale, or redeploy staging.

## Replacement loop prepared after this audit

`ai-room-product-recovery` is saved in Loopyard, NOT started. Configuration, execution brief, launch checklist and 67 preserved review/decision/contract files live at [docs/loops/ai-room-product-recovery/BRIEF.md](docs/loops/ai-room-product-recovery/BRIEF.md). It uses a manager, three implementers and two independent reviewers, explicit Codex/model selection, board-delivered concrete assignments, 80 collective main attempts and a single report-only wrap-up. Schema and fresh-board delivery smoke checks passed. The quota/accounting defects in the RUNNING engine remain a launch blocker; the checklist is documentary, not an engine interlock. No claim is made that board mode alone resolves the previous failures.
