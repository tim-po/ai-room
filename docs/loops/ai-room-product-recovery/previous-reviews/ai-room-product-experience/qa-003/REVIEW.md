# Independent QA 003 — needs_work

2026-10-04. Clean candidate **ddc0f32e37a045687f9aecaffbda5b964aa77514**, `/home/claude/ai-room-product-experience`; SHA and clean state checked before and after. Actual headless Chromium **153.0.8010.12**, disposable local applications on **127.0.0.1:18881–18884**, temporary databases/media and fresh synthetic users. Widths **360×640, 390×844, 768×900, 1440×900**, plus fresh touch context. Expert/simulated agent evaluation, **not a human usability study**. No repository edits, staging data writes, deployment, service restart or process kills.

Harness provenance: independently executed prior QA audit plus disclosed builder correction/case harnesses, supplemented with independently authored cross-route/ABA/cancel probes and source-disclosure checks. All four executions exited 0. No inherited signoff. See scripts and JSON beside this report; `gallery.html` links durable full-page and viewport screenshots.

## Material remaining failure

**QA-03 persists.** Fresh learner chooses coding/content, completes onboarding, opens `/lessons/agent-lab-intro-01`, saves practice, edits interests, logs out/in and signs into a wholly new browser context. Home still calls foundations-start-01 the “Первый небольшой шаг”; profile correctly offers “Границы и разрешения агента” and the saved work. Opened `return-viewport.png`, `new-context-return-viewport.png` is captured, and `profile-viewport.png`; exact home hrefs and persisted practice in `evidence.json`. This breaks the required return continuation. Integrate shared continuation consumer on home/profile and independently recheck; a correct saved-work link alone does not resolve the contradictory primary action.

**Staging delivery gate remains open.** Read-only actual public browser navigation to https://airoom.nolimlabs.uk/ and GET `/health` returned **dae021716ac92abe5fdf1253093f82ac8f3f3286**, schema 6, HTTP 200. Opened `staging-welcome-viewport.png`: old dark tree, not reviewed cream/green candidate. No candidate staged signoff is possible yet.

## Corrections independently closed within tested scope

- **QA-06:** Dedicated onboarding footer keeps Next/Back/Skip in the viewport at all four sizes. Every pace input was focused and its center hit-tested; last choice is reachable by keyboard, with Tab reaching footer. At 360×640 time choices require scrolling; focused last-choice capture shows them above accessible actions. Conflict/error recovery actions are visible. Global bottom tabs no longer obscure onboarding.
- **QA-07:** Real browser Back returns pace → interests with two choices retained; Forward returns to pace. Each transition uses current revision. Explicit Back retains changed experience through reload. No stale mutation replay observed.
- **QA-08:** Help warm-panel heading and label now dark `rgb(41,46,40)`, visibly legible in opened 390 capture; former white-on-cream failure corrected.
- Dirty selections display an unsaved warning and remain absent from server until acknowledged. Real committed response withheld for 15 seconds retains two choices and retry uses identical payload/key. Synthetic 502 recovery succeeds. Cross-route interests update, agents→content→agents ABA and legacy experience POST each advance revision; stale onboarding shows conflict and disables actions. Reload/cancel retains latest committed preferences (`cross-route.json`).
- Automatic first-login onboarding, two interests, refresh/logout resume, completed preference editing, saved result persistence in fresh context, cross-user isolation, touch map open/close focus, search/list/reset and failed-practice-resave recovery rerun successfully.

## Assessment delivery, with explicit fixture boundary

`cases/run.py` independently exercises actual challenge and diagnostic APIs at all four widths. Exact case text appears before choices, DOM choice IDs/order match API, reload preserves item ordering, diagnostic resumes the same pending attempt, keyboard Space selects answers, submit persists feedback, and diagnostic return works. Opened feedback labels distinguish partial result from practice without new credit. Opened every source disclosure in the flow; actual `/api/skills/forms/presentation-fixture/sources/transfer-source-verification-B/1` returns 200 and renders retained paragraph text. API records contain successful 200/201 GET/POST/PUT, no page errors.

This is **one disposable synthetic transport fixture**, not editorial approval, seven-form semantic acceptance, equivalent retakes, a successful novice learning result, or a staged publication. First width uses the initial attempt; subsequent widths deliberately exercise practice on the same seeded account. Fresh novice identities are independently used for onboarding. Form SHA256 **5ae6314a8fb03ce5849c320e51017dc3e2c68bf70b36ebaf293053c4b22547fe**; retained case SHA256 **f46f852a4a97276d59199690028bf6a7f78eb820315a4394f9cbd49eba0103d1**; graph response hash with Unicode-preserving serialization **8634a70d10413cb0d7dc71e9400c3079f2a9c6ebc36e0ddafa509020207bd918**.

Ordinary audit seed is `seed_database + init-skills + init-onboarding`, graph `tree-2026-10-v1`, root `basic-ai`, score rule `verified-coverage-v1`; escaped-JSON graph hash **c19c98cef4c00cce21f36c796f2c8732b7229557b56da9546d786a7308a76553**. File hashes in `evidence.json`; serialization difference explains graph hash difference, not different editorial approval.

## Actual API and visual observations

Loaded catalogue (7 items), course (37 lessons), text lesson, practice, profile, Help, preferences, map/list, challenge and 404 pages. Separate authenticated HTTP rereads verify graph 15,804 bytes, me 7,673, node 358, onboarding 781, practice 214; all 200 with real content. Browser exercise records successful node/explore/practice/onboarding endpoints. Ordinary-seed diagnostics is a real empty inventory, not a missing endpoint. Learner admin/measurement/member lesson/member practice return 403, anonymous practice 401, another learner sees null practice. Expected denials and injected failures are not application defects.

Personally opened rendered images: welcome desktop; full interests mobile; pace 360/768/1440 and last focused choice at 360; conflict 360 full/390 viewport; gateway error 360; Help 390; challenge 390/768/1440; mobile choices; feedback 360/390 viewport and 390 full; retained sources 390/1440; return/profile/staging; course 390, catalogue 360, lesson 1440, map 768, ABA conflict, lost-response and 404. Remaining gallery images are captured, not individually approved. Also opened selected Atelier desktop benchmark. Candidate retains its warm paper, restrained box illustration, dark headings and terracotta primary action; text lesson remains generic synthetic content and home lacks the benchmark's useful saved-work priority. Challenge text/choices wrap legibly and source remains readable; repeated case creates a long mobile page, without an observed interaction block in this fixture. No document overflow or application page errors in the audited journey.

Native 200% zoom **unverified**: attempted actual headless Chromium Ctrl++ four times; inner/outer width remain 1440 and devicePixelRatio/visualViewport scale remain 1. This is not successful native zoom and CSS scaling is not substituted. Virtual keyboard, long code-case variants, full reduced-motion behavior and complete accessibility matrix remain open.

## Requirement matrix

| Requirement | Status | Evidence/limit |
|---|---|---|
| Fresh automatic onboarding | PASS | audit evidence fresh_login_url; four fresh accounts in corrections |
| Multi-interest acknowledged persistence, refresh/logout/new context | PASS | evidence.json two_interest_draft/logout_resume/new_context_onboarding |
| QA-06 mobile footer and focus | PASS | corrections at 360x640/390x844/768x900/1440x900; all pace inputs focused and elementFromPoint checked |
| QA-07 browser Back/Forward | PASS | corrections actual browser history and current-revision assertions |
| Dirty/acknowledged and gateway/lost-response recovery | PASS | corrections and audit identical retry payload; actual 15-second response timeout |
| Cross-route stale/ABA conflict and edit/cancel | PASS | cross-route.json actual interests PUT and preferences POST |
| QA-08 Help contrast | PASS | corrections foreground rgb(41,46,40), screenshots |
| Challenge case/order/diagnostic/resume/submit/source delivery | PASS | cases/evidence.json; explicitly synthetic fixture only |
| QA-03 consistent return continuation | FAIL | return-viewport.png home foundations; profile-viewport.png saved agent work |
| First meaningful instructional result and novice recommendation | UNVERIFIED | Generic synthetic lesson/practice storage works; approved comparison activity not installed |
| Map selection/search/list/reset/touch | PASS | evidence.json bounded tested controls; deep mapped lesson roundtrip excluded |
| Deep map-to-lesson and return context | UNVERIFIED | No reviewed mapped-content roundtrip in this run |
| Auth anonymous/nonmember/admin/cross-user practice | PASS | evidence.json actual 401/403 and cross-user null |
| Expired/revoked/unpublished/media access matrix | UNVERIFIED | Not exercised on this candidate |
| Native browser 200% zoom | UNVERIFIED | cross-route.json keyboard shortcut leaves innerWidth 1440 DPR 1; no CSS zoom substitution |
| Video playback/resume/media recovery | UNVERIFIED | Not exercised on this candidate |
| Full filter/favourite/support history and long code stress | UNVERIFIED | Pages load; full task matrix pending |
| Real approved assessment semantics/uneven profile | UNVERIFIED | Fixture transport success does not approve seven forms or evidence coverage |
| Events/funnel/D1/D7 and long-absence behavior | UNVERIFIED | No measurement/retention acceptance inferred from synthetic smoke |
| Exact redesigned staging | FAIL | Public Chromium and health still dae021716ac92abe5fdf1253093f82ac8f3f3286 |

Next required work: fix shared continuation, install approved first-result/recommendation content, complete mapped/video/access/support/measurement journeys and native zoom gate on one integrated candidate, then sole-owner deployment and fresh exact-staging review. Current verdict **needs_work**.
