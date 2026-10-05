# Independent visual gate 002 — needs_work

2026-10-04. Independent expert/simulated Chromium evaluation, not a human usability study. Actual application 61d0833ccc501d4c5988d875933f79f550c79ddb, clean /home/claude/ai-room-product-experience checkout. Local http://127.0.0.1:18787; Chromium 153.0.8010.12; 360x844, 390x844, 768x900, 1440x900. Separate fresh synthetic accounts and SQLite databases under /tmp/airoom-critic-002. No application source edits, shared data changes, service restarts, deployment or subagents.

Content is ordinary synthetic seed + init-skills, not approved published assessment content. Graph tree-2026-10-v1, basic-ai, verified-coverage-v1; source and response hashes in evidence.json. Public https://airoom.nolimlabs.uk/health independently returned dae021716ac92abe5fdf1253093f82ac8f3f3286 / schema 6 / ok. This old staged build and its publication content are NOT visually accepted by this candidate review.

## Judgment

The Atelier first slice is a substantial visual improvement and remains the chosen direction. Opened desktop/mobile welcome shows a clear promise, deliberate typographic scale, warm paper, terracotta action and purposeful illustration. Actual text lesson now prioritizes readable teaching and collapses curriculum on mobile. Catalogue, empty profile, saved work and 404 share this language. Desktop map uses legible branch illustrations and visible connectors. This is sufficient to continue implementation in the selected system, not permission to claim complete-product acceptance.

Compared with the selected Atelier prototype and earlier independently opened Brilliant first-action reference, the anonymous welcome achieves clear action hierarchy. The signed-in first experience still fails the guided-start benchmark. No new competitor or causal retention claims are made in this review.

## Concrete failures and required corrections

| ID / severity | Screenshot-specific observation | Correction |
|---|---|---|
| VC-01 BLOCKER, still open | fresh-login-1440-viewport.png: fresh ordinary login lands at /?view=map; onboarding remains a secondary link. | Integrate automatic welcome/onboarding with explicit skip and permitted first activity. Retest genuinely fresh account through ordinary entry. |
| VC-02 BLOCKER, partially repaired | pace-before-refresh-1440.png versus preferences-768-viewport.png: two interests persist, but refresh returns to interests instead of the active pace step. | Persist current step and answers server-side; restore after refresh/logout; complete optional diagnostic and recommendation flow. Do not call the legacy editor completed onboarding. |
| VC-09 BLOCKER, misleading save feedback | offline-save-390.png and offline-save-390-viewport.png: after editing previously saved work and aborting its save, small error text says no connection, while a prominent section still states Работа сохранена and offers onward navigation. The submitted badge also remains. | On dirty edit/failure, hide or explicitly qualify prior-version success, make unsaved state prominent and retry available; confirm current version through server reread. app.js input/catch handlers leave prior confirmation visible. |
| VC-10 major legibility failure | course-390-viewport.png and course-1440.png: Перед началом is white on a pale cream prerequisite panel. | Apply accessible dark heading color and verify actual computed contrast at four widths. Adjacent course action buttons also touch; restore spacing. |
| VC-11 content-state failure / publication dependency | diagnostic-started-390-viewport.png: a fresh learner clicks Start, answers zero questions, and sees Доступные проверки завершены. There is honest no-credit copy below, but the headline implies completed checks. Both API calls succeed. | Show explicit no-available-published-checks state with learning action; independently retest questions, feedback and source explanations with approved exact published forms. Do not manufacture assessment availability. |

Mobile map is much improved but remains visually spacious: map-360-viewport.png and map-768-viewport.png use most of the initial viewport for header/continuation/onboarding/search. At 360 only the root and a sliver of the next node are visible. VC-04 giant illustration blocker is closed; compacting remaining vertical gaps is a moderate refinement, especially after onboarding completion removes its prompt. Tablet selected heading focus outline overlaps the close-button area in map-selected-768-viewport.png: reserve separate space for heading/focus and close control.

## Earlier findings rechecked

- VC-03: CLOSED for tested foundation lesson save/return and profile hierarchy. Named work, actual saved text, unreviewed label and reopen action lead profile-saved-390-viewport.png. Home has named lesson continuation in return-390-viewport.png. Cross-branch/long-absence return is still UNVERIFIED.
- VC-04: CLOSED for oversized mobile art. Actual continuation uses a compact arrow, not the prototype giant cube.
- VC-05: CLOSED for tested Coding branch and Testing/debugging child. Clicked detail is brought into view, keyboard focus moves to title, Close restores branch focus and previous scroll. clicked-coding, closed-coding and deep-branch screenshots document this. Full recursive/list synchronization and touch-device matrix still need final coverage.
- VC-06: PARTIAL. Welcome/map/lesson/catalogue/profile/error now share the chosen shell, but course contrast VC-10 and unreviewed assessment/practical/video surfaces prevent full closure.
- VC-07: desktop connectors and node titles now readable in map-1440-viewport.png.
- VC-08: mobile course rail is collapsed and lesson content appears in first viewport; checked lesson-390-viewport.png.

## Actual interactions and endpoints

Fresh sign-in; two-interest selection and advance; refresh; lesson text entry; Save result; authenticated server reread; profile and home return; logout/login with saved text preserved; request-aborted save retaining editor text; Coding selection/close; deeper Testing/debugging selection; list search, URL refresh and empty search/reset; course load; diagnostic Start; root detail; intentional 404. audit.py adapts builder setup but was executed independently with fresh data; extra.py adds targeted critic journeys.

Direct authenticated probes: /api/skills/graph 200/15804 bytes; /api/skills/me 200/7664; /api/lessons/foundations-start-02 200/7780; /api/lessons/foundations-start-02/practice 200/700. Additional actual-browser API log contains 35 successful calls including node/detail/explore and diagnostic; see extra-evidence.json. Pages use real server data. Server-rendered catalogue/course/help do not imply nonexistent JSON APIs. No JS errors or measured horizontal overflow in initial capture suite. Font checks report loaded Golos Cyrillic.

Reduced-motion preference, map focus restoration and search typing focus tested. CSS 200% layout stress captured; this does not constitute real browser-zoom acceptance. No full keyboard traversal, touch-device emulation, authored long-Cyrillic stress, video playback, challenge questions/results/source explanations, uneven assessed profile, membership expiry, full offline/error matrix or cross-branch return acceptance is claimed. Those remain UNVERIFIED and block final complete-product gate. No green unit-test inference substitutes for missing journeys.

## Personally opened screenshots

Welcome 1440/360 viewport; map 1440/768/360 viewport; preferences 768 viewport; lesson 1440/390 viewport and full 360; catalogue 390 viewport; course 390 viewport/full 1440; empty profile 360 viewport; saved profile/return 390 viewport; error 360 viewport; selected map 390/768 viewport; clicked/closed Coding and deeper Testing/debugging 390 viewport; diagnostic initial 360 and started 390 viewport; failed-save full/viewport 390; CSS 200% lesson viewport. Both full-page and viewport captures are preserved for all recorded states; unlisted files are captured but not claimed visually reviewed.

## Gate matrix

| Requirement | Verdict |
|---|---|
| Selected Atelier identity carried into first connected slice | PASS with course correction required |
| Real interest values persist before advance | PASS |
| Automatic onboarding and active-step resume | FAIL |
| Saved practice and named foundation return after login | PASS |
| Honest failed-save/current-version state | FAIL |
| Mobile tested branch/detail/close and compact continuation | PASS within tested scope |
| Complete learning/challenge/return and failure-state matrix | UNVERIFIED |
| Final exact staged SHA plus approved content visual gate | UNVERIFIED |

Manager should assign VC-09/10 directly to frontend and coordinate VC-01/02/11 with the confirmed backend/content contract. Continue the selected visual system; do not deploy or accept the full product based on this bounded review.
