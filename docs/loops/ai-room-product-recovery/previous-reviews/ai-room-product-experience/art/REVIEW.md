# Art director 001 — needs_work

Two executable directions are ready for independent critique. Recommended candidate: **A / Мастерская**, not yet selected by an independent critic/manager. Application acceptance remains blocked by the actual baseline and the absence of an implemented, reviewed redesign. Do not interpret prototype completion as functional product completion.

## Evidence personally gathered

2026-10-04; Chromium 153.0.8010.12, headless; actual app `/home/claude/ai-room-pending-review`, exact clean SHA `bc4ba3c1f2eed39e42f611836d6990acf7b0a62d`. Local URL `http://127.0.0.1:18767`, disposable freshly seeded DB under `/tmp/airoom-art-001/`, fresh custom synthetic learner. Graph `tree-2026-10-v1`, root `basic-ai`, score rule `verified-coverage-v1`; response SHA256 `a1d968f83aacbab0ab65acf94ce731315d09ee1430b99ae750c914b3ee4a0e18`. This is ordinary seed/init-skills, **not** private reviewed content or the deployed publication ledger. Public staging was not independently rechecked this turn; manager's recorded dae0217 remains historical context only.

Read actual login route in `club/__init__.py` and interest/profile behavior in `club/static/development.js`. Loaded anonymous root, actual login, signed-in root, preferences, text lesson `foundations-start-02`, saved practice and profile. Browser-requested graph and me APIs returned 200 with real bodies (15,804 and 7,591 bytes), actual practice POST returned 200, authenticated practice GET returned the entered nonempty text. Graph also directly curled on localhost. Network table and saved data in `evidence.json`. No mocked backend and no inspection of credentials. No shared account or retained learner data changed.

Captured 57 baseline/prototype states, each full-page and viewport, in the main run. Prototype welcome, onboarding, map, lesson and return at 360/390/768/1440; extra mobile pace/first-task/feedback/saved states and desktop selected-map states. Prototype interactions exercised: two interests, Back retention, first-task entry, nonempty draft save, feedback/return, branch selection, map/list, search and recenter. The two in-page fonts were verified loaded for their respective direction; the other unused font correctly remains unloaded. Native Tab focus reached the first-task action, and reduced-motion preference was set and confirmed. CSS layout zoom 2 at 1440 tested on onboarding, not a claim of exhaustive browser-zoom/a11y acceptance for every surface.

Opened and visually inspected actual fresh-login, interests, lesson, profile screenshots; A welcome at desktop/mobile, onboarding at 360/390/768/1440 and zoom, map at desktop/tablet, lesson desktop/full mobile, pace/feedback/saved; B welcome desktop/full mobile, onboarding mobile/zoom, map desktop, lesson desktop/full mobile and saved return. Subsequent connector/tablet corrections are recorded in `visual-recheck.json` with final hashes and localhost:18768 URLs; final relevant screenshots reopened. `gallery.html` links all captures. Generation alone is not presented as visual review of every image.

## Concrete baseline blockers

| ID | Observed evidence | Required correction and gate |
|---|---|---|
| ART-01 / blocking | `actual-fresh-login-1440-viewport.png`: fresh learner sees a large dark diagram with tiny “Найти своё начало” link; final URL is `/`. | Real automatic onboarding after first sign-in, clear first-result action, preserved deep-link destination. A visible optional settings link does not satisfy onboarding. |
| ART-02 / blocking | Choose coding + content, Next, refresh: zero selected interests. `actual-interests-390-viewport.png` and evidence interrupted_selections=0. | Persist server-side values and current step before advancing; restore after refresh/logout. Recover failed save visibly without losing selections. |
| ART-03 / blocking | `actual-profile-390-viewport.png`: first screen is “Здесь появятся…” plus unconfirmed application, immediately after successful saved practice. Actual full profile keeps saved work below unknown summaries. | Lead with just-saved artifact and named continuation; move unknown branch inventory below disclosure. Retest reopening the exact work from mobile profile. |
| ART-04 / blocking visual coherence | Actual map is a dark full-width field; actual lesson is a cream card in the dark shell with a second cream curriculum card consuming mobile height (`actual-lesson-390-viewport.png`). | One selected visual system across welcome/map/course/lesson/profile and error states. Keep curriculum available, reduce its prominence before the first useful content. Not a map-only recolor. |
| ART-05 / not yet delivered | No selected-direction application, final same-SHA gallery or independent selection in this turn. | Critic reviews BOTH rendered directions, manager records choice, frontend implements owned learner routes and all supporting states, reviewers repeat actual endpoint-connected journeys. |

## Prototype corrections made and self-critique

Fixed search visibility overridden by node display CSS; explicit hidden selector now works. Removed accidental main-container focus outline while retaining visible control focus. Removed competing global navigation during onboarding. Fixed 768px root/agent proximity. Added container-based onboarding reflow after genuine 2x CSS zoom overflow; final tested zoom captures do not overflow. Dynamic connectors now meet actual node anchors after responsive layout rather than relying on a stretched static curve. B now has a separate centered constellation illustration/composition, not a recolored notebook.

A is the recommendation because its editorial paper carries naturally into reading and saved work. B has stronger exploratory atmosphere but more container weight and weaker differentiation from the rejected dark baseline. This is design judgment, not a measured preference or conversion result. The borrowed benchmark is first-action clarity and explanation/practice proximity, not competitor branding or an unproven retention claim. See `VISUAL-SYSTEM.md` for comparison, sources, tokens, Cyrillic fonts, responsive behavior, map language, complete-surface composition and acceptance tasks.

Known prototype limits to resolve during design/implementation: mobile selection detail follows the tree rather than preserving context in a focused inline panel/sheet; recursive children are textual examples, not functioning deep graph routes; search has no explicit zero-results message; course links in the example curriculum share a demonstrative lesson and are clearly marked; pace selections and drafts are not server-persisted; no real diagnostic, auth or grading is simulated. These are not accepted as production controls. Production must use the retained real backend and reviewed content. The manuscript teaching example remains an editorial proposal, not content publication approval.

## Requirement status for this turn

| Requirement | Verdict |
|---|---|
| Two contrasting working Russian welcome/onboarding/map/lesson directions | PASS as design artifacts only; both rendered and exercised |
| Local licensed Cyrillic fonts / tokens / icons / original SVG illustration / responsive specification | PASS for selection package |
| Desktop/mobile prototype visual review plus targeted corrections | PASS within recorded captures; independent visual_critic still required |
| Actual baseline browser and live endpoint evidence | PASS within explicitly listed surfaces |
| Automatic persisted onboarding / first useful result / return in real app | FAIL / needs implementation |
| Independent direction selection before broad rollout | UNVERIFIED; recommendation only |
| Complete product, real recursive map, challenge/source feedback, media, failure states, all keyboard/touch/zoom journeys | UNVERIFIED |
| Verified staging deployment + exact-build independent acceptance | UNVERIFIED; no deployment made |

Next scheduled roles: visual_critic inspect the two executable directions and gallery; interaction_designer resolve mobile selected-detail/deep-list behavior; manager record selection; frontend engineer implement only after selection and shared ownership agreement. No subagents launched, no production edits, no staging action. This is an expert simulated evaluation, not human usability research.
