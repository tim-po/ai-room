# Independent visual gate 003 — needs_work

2026-10-04. Independent expert/simulated evaluation, not a human usability study. Actual clean candidate **6e7d7b31e9d82ba2849a0415a8563eebe5a6d8e6**, `/home/claude/ai-room-product-experience`. Headless Chromium 153.0.8010.12; local URLs `http://127.0.0.1:18867` through `:18870`. Viewports 360×844, 390×844, 768×900, 1440×900; additional 360×640. Fresh synthetic accounts and disposable SQLite/media/upload/instance directories in /tmp. No repository edits, shared data changes, deployment, service restarts, process kills or subagents.

Content: ordinary synthetic seed + init-skills + init-onboarding, **not approved assessment publication**. Graph `tree-2026-10-v1`, `basic-ai`; graph JSON SHA256 `c19c98cef4c00cce21f36c796f2c8732b7229557b56da9546d786a7308a76553`. Source hashes, state rereads and API observations are in evidence.json, supplement.json, targeted.json and help.json. Exact source ledger is in source-ledger.json.

## Judgment

Atelier remains a coherent direction: warm paper, loaded Cyrillic Golos, clear terracotta action, restrained green saved-work surfaces, purposeful branch line art. Desktop welcome is composed and calm; actual course hierarchy, readable text lesson and saved-work-led profile are material improvements over the rejected baseline. I reopened the selected Atelier lesson prototype and the research team's Brilliant screenshot. The prototype contains a concrete worked example that the current synthetic first lesson still lacks; the implementation cannot claim the same instructional completeness from typography alone. Brilliant's observed welcome offers a clear learner action beside a product example. Its marketing claims are not evidence for AI Room retention. Primary source revisited 2026-10-04: https://brilliant.org/ . This review does not substitute for the five-product research register.

**Acceptance is blocked by mobile onboarding composition, false saved-state feedback, broken return continuity and Help contrast.** Do not average these away because other screens are attractive.

## Screenshot-specific blockers

| ID / severity | Actual observation | Required correction |
|---|---|---|
| VC-12 / major, matches IX2-01 | `interests-390-viewport.png`: Next spans y787.8–838.2, almost entirely behind fixed tabs beginning near y791. `pace-360-viewport.png`: Next begins y956.2, absent from initial viewport. `pace-768-viewport.png`: tabs cover the action. Desktop pace Next extends below 900px. Full-page images confirm actions exist and become usable by scrolling. | Active onboarding needs a dedicated visible Next/Back/Skip task hierarchy with reserved bottom space, rather than global navigation covering the task. Test 360×640, tablet, focus and zoom without covering choices or status. |
| VC-13 / major, false acknowledgment | `dirty-interest-viewport.png`: after selecting Coding, status still reads «Сохранено в аккаунте.» while GET /api/onboarding shows draft interests []; only the visible checkbox changed. | Clear/replace prior-step success on input changes; explicitly say current choices are unsaved until acknowledged. Restore truthful status after retry/refresh. |
| VC-03 reopened / blocker, matches QA-03/L04/IX2-02 | `profile-viewport.png` leads with saved agent work; `return-viewport.png` and `map-1440.png` instead advertise «Первый небольшой шаг» linking foundations-start-01. The actual completed onboarding and saved practice were agent-lab-intro-01. Reproduced after logout/login. | Integrate backend-owned latest permitted activity selection. Home must resume the named actual work after cross-branch activity and login, preserving earlier progress. |
| VC-14 / major, matches IX2-03 | `browser-back-viewport.png`: welcome → interests → acknowledged pace → browser Back returns to /login despite authenticated header. Explicit in-page Back passes. | Add bounded step history with server revision awareness. Browser Back/Forward must retain orientation and acknowledged answers without replaying stale writes. |
| VC-15 / major legibility | `verified-help-390-viewport.png`: «Задать вопрос» and field label are nearly invisible cream on cream. Computed foreground rgb(255,253,247), background rgb(237,232,218), documented in help.json. Real help submission succeeds, so this is a visual failure rather than missing endpoint. | Apply readable dark text to this panel and audit inherited pale-panel headings/labels throughout learner surfaces. Course-only selector repair is insufficient. |

## Previous blockers rechecked

- **VC-01 closed locally:** ordinary fresh login automatically reaches onboarding. Welcome and all steps captured at four widths.
- **VC-02 persistence closed locally:** coding+content persist after advance; refresh and logout/login resume pace with both interests. Explicit Back retains choices. Editing later adds agents without deleting saved practice. Remaining history/dirty-status failures are VC-13/14.
- **VC-09 closed for tested practice failure:** saved work → edit → aborted save retains text, shows network error and removes stale successful confirmation. Retry succeeds. `practice-failed-resave-viewport.png`; authenticated reread confirms saved text.
- **VC-10 closed on tested course at all four widths:** dark prerequisite heading and separated actions; `course-recheck-{360,390,768,1440}`. A 37-lesson/9-module course also loads and has collapsed module hierarchy (`long-course-390.png`). Help exposes a separate inherited contrast defect above.
- **VC-11 empty-state copy closed:** real diagnostic start returns successful response but no observations; UI now says unavailable/no results and offers learning. Challenge without a published form also has honest unavailable copy and recovery links. This does not verify actual questions/results/source explanations.
- **VC-04/05 bounded passes retained:** compact map continuation, readable desktop connectors, touch Coding open/close restores Coding focus, Testing/debugging deep branch and list search operate with real graph endpoints. Full approved-content map→lesson→map context remains unverified.

## Actual journeys and evidence limits

Executed fresh login → two interests → pace → refresh → logout/login → Back → start → permitted agent lesson → save practical text → failed edit/retry → profile → edit interests → map → logout/login return. Separate fresh users skipped onboarding and exercised a server-committed response lost for 15 seconds; choices and controls recover and unchanged retry uses identical payload/key with revision 2, not a duplicate transition. No actual human participants.

Loaded real welcome, onboarding, map/selected/deep/list/search, catalogue, course, lesson/practice, profile, preferences, help, 404, diagnostic and unavailable challenge. Main audit records 55 successful API responses and no application JS errors; supplement records 26 responses. Direct probes include graph 200/15804 bytes, me 200/7673, coding detail 200/210, onboarding 200/758, lesson and saved practice with real JSON. Fresh practice null and empty diagnostic list in the separate untouched account are intentional empty states, not missing routes. Help POST produced a persisted visible question. Course/catalogue/help are server-rendered and do not require invented JSON endpoints. Relevant code inspected: onboarding.js, onboarding.html, atelier.css, atlas.js, diagnostic.js, course.html and help.html.

No measured horizontal overflow in the main capture run; loaded Golos Cyrillic confirmed. Reduced-motion emulation and touch Coding open/close tested. CSS 200% layout screenshot is **not actual browser-zoom acceptance**. Full keyboard traversal, actual browser 200% zoom, authored long-string stress, virtual keyboard, actual video playback/resume, available reviewed challenge/feedback, uneven assessed profile, full access/offline/media matrix, next-day/long-absence return remain **UNVERIFIED**. Synthetic saved text proves storage, not meaningful instructional feedback.

Harness transparency: audit.py's supplemental page loop ran while the third account was still onboarding, so files named catalogue/help/error/profile-saved/preferences/diagnostic/map-selected at its end can show onboarding redirects; **they are excluded from surface acceptance**. Correct actual pages were captured by supplement.py under `verified-*` and `course-recheck-*`. A first supplementary navigation raced the skip redirect; rerun awaited the map URL. A response-body listener logged a navigation cancellation; it is harness instrumentation, not proof of an app failure. Main lost-response interception logs cancellation on browser teardown. Do not mistake those logs for independent passing app tests or product blockers.

## Personally opened images

Opened viewport: onboarding-welcome-1440; interests-390; pace-360/768; welcome-360; lesson-390/1440; start-1440; practice-failed-resave; return; profile; all four course-recheck widths; verified-catalogue-768; verified-diagnostic-started; verified-deep-node; verified-error-360; lesson-css-zoom200; verified-list-search; dirty-interest; browser-back; challenge-unavailable; verified-help-390; verified-profile-empty-360. Opened full-page: interests-390, pace-360, map-1440, course-recheck-1440, long-course-390. Also opened selected Atelier prototype lesson and researcher-captured Brilliant benchmark. Other generated files are not claimed visually reviewed. Full-page and task/viewport captures are durable beside this report.

## Gate matrix

| Requirement | Status |
|---|---|
| Selected visual direction across tested core surfaces | Partial pass; Help contrast fails |
| Automatic onboarding and acknowledged server resume | Pass locally |
| Onboarding action visibility, truthful dirty state, browser history | Fail |
| Practice save, failed-save recovery, edit preservation | Pass tested scope |
| Actual-work home return after login | Fail |
| Map basic touch/detail/list and unavailable assessment recovery | Pass bounded scope |
| Meaningful learning/feedback and complete state matrix | Unverified |
| Exact staged SHA plus approved content verdict | Unverified |

Final verdict applies only to local **6e7d7b3 + disposable seed/graph above: needs_work**. Public staging health fetch through web tool was unavailable this turn; prior dae0217 is historical evidence, not a newly verified deployed SHA. No final staging/content signoff or deployment approval. Fix VC-12/13/14/15 in frontend, consume exact continuation patch, then recheck one integrated SHA and approved content ledger before broad acceptance.
