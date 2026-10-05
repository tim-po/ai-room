# Independent visual review 019 — needs_work

2026-10-05. Exact clean local app **58af5d9aece9615fd8c883c85a1f146f557082cb**, `/home/claude/ai-room-product-experience`. Independent expert/simulated walkthrough, not a human usability study. No repository edits, deployment, retained-data mutation, service restart or process kills.

Actual headless Chromium **153.0.8010.12** on local ports **18979** (journey) and **18978** (support). Disposable /tmp SQLite instances with ordinary synthetic seed + init-skills + init-onboarding + init-support. Journey widths/heights: 360×844, 390×844, 768×900, 1440×900; support also covers 360×640. Full-page and viewport captures are linked in gallery.html. Harnesses and real endpoint observations are retained alongside this report.

Content: graph `tree-2026-10-v1`, root `basic-ai`, canonical Unicode JSON SHA256 `8634a70d10413cb0d7dc71e9400c3079f2a9c6ebc36e0ddafa509020207bd918`. Journey JSON uses ASCII escaping and therefore hashes to `c19c98cef4c00cce21f36c796f2c8732b7229557b56da9546d786a7308a76553`. Seed lesson identity/title/access/status manifest hash `f8cb55702c470b43554efdae9228c2ad8aa42591ce04176f21b3112c650d8d30`. This is not an installed staging-content ledger or approval of assessment forms. Relevant source hashes in source-ledger.json.

## Decision and concrete findings

The warm paper, Golos Cyrillic typography, terracotta primary actions and line illustrations form a coherent Atelier direction. The welcome has purposeful composition and a clear first action. The core product gate nevertheless remains blocked: the actual first lesson still fails to deliver the concrete learning experience promised by the selected benchmark. I reopened `../visual-critic/atelier-lesson-1440-viewport.png` for direct comparison.

| Finding | Severity and evidence | Required correction |
|---|---|---|
| Approved first activity still absent from the tested journey | **Major/blocking**. `start-768-viewport.png`, `lesson-390-viewport.png`, `lesson-1440.png`: fresh beginner selecting coding + content receives “Границы и разрешения агента”. Under “Разбираемся на примере” the lesson gives generic instructions to invent a task, not an actual worked case. Saving a result works but provides no source comparison or meaningful feedback. The benchmark provides concrete source notes and a worked prompt. | Integrate the approved first-activity content and recommendation, actual attempt/comparison/revision/save/reopen flow. Recheck fresh novice entry, not merely direct URL access. |
| Return map is visually displaced by repeated context | **Major composition issue for the central mobile map**. `map-360-viewport.png`, `return-viewport.png`, `map-768-viewport.png`: heading, edit link, continuation, repeated last-result title, saved-work link and controls consume roughly 645px before map surface; at 360 only the common root appears before bottom navigation. None of the five branches is initially visible. | Compact secondary last-result/saved-work information while retaining unfinished-work priority; make branch discovery visible substantially earlier. Keep continuation and result semantics separate without repeating two large task sections. Recheck at 360×640 and 390×844. |
| Help keyboard refresh drops focus | **Moderate usability defect**. `support/retry-focus-360.png` and support/evidence.json: at all four widths, keyboard Enter refresh succeeds but activeElement becomes BODY. `club/static/support.js` disables the focused button and does not restore focus. | Preserve or restore focus after refresh if the user has not moved it; independently test success and failure without forcing focus after the operation. |
| Return continuity previously failed | **Original reproduction now passes, bounded**. `profile-viewport.png`, `return-viewport.png` show the same actual agent lesson. After saved result, interest edit and logout/login, home points to `/lessons/agent-lab-intro-01`, with separate result anchor. | Keep closed for this reproduction; still verify competing unfinished drafts across branches, unavailable content, and second-context continuation before broad acceptance. |

## Actual journey and endpoint evidence

Fresh ordinary synthetic login automatically entered onboarding. Selected coding and content, saved server state, refreshed, logged out/in mid-flow and resumed; explicit Back restored selections. Beginner/10-minute setup led to permitted agent lesson. Saved practical text, reread actual practice JSON, simulated network failure on resave, retained text and successfully retried. Profile reopened saved work. Edited interests to add agents without resetting the saved result. Explored map selection, close/focus, list/search, refresh and recenter. Signed out/in and verified correct continuation. Separate fresh account skipped onboarding. Submitted Help question and saw it persisted; loaded catalogue/preferences/404.

Journey evidence records **54 real API responses, all HTTP 200**, zero page errors and no horizontal overflow in 42 paired screenshot states. Simulated aborted save requests are deliberately not successful HTTP responses. Direct authenticated browser probes returned real nonempty graph, skill state, coding-node detail and onboarding JSON; practice readback contains the submitted result. See evidence.json for exact URLs, methods and response status. Server-rendered Help was exercised via actual form POST.

Support run created a synthetic question and actual admin response in disposable data, exercised `/api/support/tickets`, POST `/api/support/tickets/{id}/handle`, four-width authenticated answer rendering, initial-fetch failure, 503 refresh preserving prior answer, retry and fresh-context sign-in/readback. Another learner saw empty history and received expected 404 for the private ticket. Long Cyrillic text wraps; HTML-like answer/question content stays literal. All final checks pass except recorded focus failure. Reduced-motion emulation used in this run. Real HTTP observations retained in support/browser.log. No real third-party messages were sent.

Harness transparency: reused/adapted prior reviewer journey and builder support harnesses, then personally opened the images. Initial support run exposed Playwright string-predicate CSP evaluation incompatibility; changed the test predicate to an arrow function without changing app CSP. Next run reproduced focus assertion failure; retained it as explicit false evidence and continued the remaining independent checks. This is not silently treated as a pass.

## Personally opened images

Journey: welcome-1440-viewport, onboarding-welcome-360-viewport, pace-768-viewport, lesson-390-viewport, lesson-1440 full page, return-viewport, map-1440 full page, map-360-viewport, map-768-viewport, selected-viewport, profile-viewport, start-768-viewport, catalogue full page, diagnostic-unavailable-viewport, error-viewport. Support: answer-360/390-viewport, failure-360 full page, retry-focus-360, help-768/1440 full page. Selected Atelier desktop lesson reference also reopened. All four required widths are represented among personally opened captures; other captures are not claimed individually opened. Fixed bottom navigation in full-page image middles is capture compositing, not evidence of an actual in-flow duplicate bar.

## Requirement-to-evidence matrix

| Requirement | Status |
|---|---|
| Clear welcome and automatically encountered onboarding | Pass tested local journey |
| Multi-interest save/back/refresh/logout resume/skip/edit | Pass tested local journey |
| Saved result persistence and failed-save recovery | Pass tested local journey |
| Original wrong-home-continuation reproduction | Pass bounded recheck |
| Approved first useful activity and meaningful feedback | **Fail** |
| Central mobile map composition | **Fail** as described above |
| Support response/history/privacy/error retry | Pass tested states; keyboard focus **fails** |
| Cohesive palette/Cyrillic hierarchy/welcome illustration | Pass bounded observed surfaces |
| All course, video/playback/resume, deep mapped lesson roundtrip, challenge/source feedback, assessed profile, access/expired/media states | **Unverified** on this SHA; not inherited from earlier runs |
| Full native 200% zoom, virtual keyboard/touch, long-absence/next-day return, competing drafts and denied continuation | **Unverified** |
| Exact staged SHA and installed-content acceptance | **Unverified** |

Public staging health at https://airoom.nolimlabs.uk/health was inaccessible through the web tool on this turn. This is a verification limitation, not evidence staging is down. Prior recorded dae0217 is not a current independent health result. No exact staged verdict can be issued.

**Final verdict: needs_work.** Preserve the bounded continuity improvement, repair the concrete first-result and mobile composition failures plus keyboard refresh, then run the remaining complete-product and exact staging/content gates. No deployment or overall completion approval.
