# Independent visual critic 001 — needs_work

2026-10-04. Independent expert/simulated evaluation, not a human usability study. No product files edited, shared learner data changed, deployment performed, or agents launched.

## Direction decision

Recommend **A / Мастерская (Atelier)** for manager selection. The warm paper, Golos Cyrillic, restrained terracotta action color, green continuation strip and editorial lesson composition form a credible coherent learner product. The desktop welcome has a clear text/art balance and a specific practical promise. Lesson examples and practice share the same visual grammar. Onboarding at 360 and 768 has readable choices and a clear next action. Feedback and saved work retain hierarchy and distinguish saving from assessed competence.

B / Обсерватория is a genuinely distinct welcome composition with centered promise and constellation art, but its nested dark lesson surfaces and faint connectors provide weaker hierarchy. Its 1440 map also pushes a branch below the first viewport. A is the stronger basis; this is an independent design judgment, not a retention claim. Neither prototype is accepted as a complete product. Preserve both prototypes.

Opened the researcher's Brilliant start screenshot: its single visible Continue action is a useful first-action benchmark. This is secondary screenshot observation (research/brilliant-start.png), not my own live competitor walkthrough. The new A onboarding approaches that clarity; the current application's small onboarding link does not. Five-product research and causal learning claims remain owned by the research register, not inferred from this image.

## Exact evidence

Actual local app: /home/claude/ai-room-pending-review at **bc4ba3c1f2eed39e42f611836d6990acf7b0a62d**, http://127.0.0.1:18779, headless Chromium **153.0.8010.12**. Fresh custom synthetic account in an isolated random SQLite DB under /tmp/airoom-critic-001; ordinary repository seed + init-skills, not private approved publication. Graph tree-2026-10-v1 / basic-ai / verified-coverage-v1; graph response SHA256 a1d968f83aacbab0ab65acf94ce731315d09ee1430b99ae750c914b3ee4a0e18.

Public https://airoom.nolimlabs.uk/health rechecked through Chromium: build **dae021716ac92abe5fdf1253093f82ac8f3f3286**, schema 6, status ok. This is identity/health verification only, NOT final staged visual or content acceptance. Staged content ledger and authenticated staged journeys remain unverified this turn.

Executable directions served from /art/index.html?direction=atelier or observatory, with welcome/onboarding/map/lesson/return hashes. Exact artifact hashes are in evidence.json and direction-verdict.json. audit.py adapts the art director's server/capture scaffolding; I executed it in a separate fresh database/output directory and independently inspected the resulting images. 84 states captured, each full-page and viewport, at 360x844, 390x844, 768x900 and 1440x900 (initial actual desktop 1440x960). No horizontal overflow observed; that does not establish visual acceptance.

Browser loaded actual anonymous entry, fresh login, preferences, map, discovery, text lesson, saved practice, profile, logout/login return and intentional 404. Direct authenticated endpoint probes all returned 200 with substantive content: /api/skills/graph 15804 bytes; /api/skills/me 7591 bytes; /api/lessons/foundations-start-02 7780 bytes; /api/lessons/foundations-start-02/practice 789 bytes. Browser practice POST succeeded and entered text survived logout/login (return_saved in evidence.json). Catalogue is server-rendered; no missing catalogue API inferred. Intentional missing page returned 404 with a rendered recovery action.

Actual fresh login lands at / without onboarding. Choose coding + content, Next, refresh: zero checked interests. Real code corroborates this: club/__init__.py login redirects to next or /; development.js only hides/shows steps on Next and persists interests at final form submission.

Prototype tasks personally executed through Chromium: two interests; Next/Back retention; first lesson; nonempty draft save; feedback; saved-work return; branch selection; list toggle; search and reset. These are in-memory demonstrations and cannot prove server persistence, assessment or real recursive navigation. Font checks loaded the applicable Cyrillic font at every width. Tab focus and reduced-motion preference were checked; 2x CSS layout zoom on final onboarding step had no overflow. This is not complete browser-zoom, touch-device or accessibility acceptance.

## Screenshot-specific findings

All paths below are relative to this visual-critic directory unless prefixed art/.

| ID / severity | Concrete observation | Required correction / recheck |
|---|---|---|
| VC-01 BLOCKER — actual first-use | actual-fresh-login-1440-viewport.png: almost the entire page is a dark map; onboarding is a tiny link competing with Continue. Fresh user never encounters welcome/value or guided first action. | Automatic fresh-login onboarding, explicit skip, preserved destination and permitted first practical activity. Test a new account from entry without direct onboarding URL. |
| VC-02 BLOCKER — actual interrupted start | actual-interests-390.png, evidence interrupted_selections=0 after choosing two and advancing then refreshing. | Persist selections and step server-side before advance; restore after refresh/logout, with failure recovery and no reset of learning. |
| VC-03 BLOCKER — actual return hierarchy | actual-profile-390-viewport.png and actual-return-390-viewport.png: after successful save the profile foregrounds absent confirmed skills/application; root again shows the map. The saved artifact is not the first useful continuation. | Lead returning state with actual named work/lesson and a reopen action. Keep unknown skill inventory subordinate and honest. |
| VC-04 BLOCKER — mobile prototype composition | atelier-map-390-viewport.png and observatory-map-360-viewport.png: continuation cube becomes a huge illustration. At 390 the lesson button is cut at the lower edge and no map is visible. Full atelier-mobile-selection-390.png shows how much this pushes navigation down. | Bound icon dimensions on mobile and keep continuation compact; show usable map/search and continuation without a giant decoration. Reopen actual 360/390 viewport captures. No-overflow is insufficient. |
| VC-05 BLOCKER before map acceptance — mobile selection | atelier-mobile-selection-390.png: choosing Coding updates a detail panel after all six nodes; no focused local detail or visible change beside selected branch. Both directions share it. | Inline detail or accessible sheet with branch title, Back/close, preserved selected node and scroll. Provide real recursive sibling navigation and synchronized list/search, including zero-results recovery. |
| VC-06 BLOCKER — actual visual coherence | actual-lesson-390-viewport.png: large cream curriculum and lesson containers in dark shell; actual-map-360-viewport.png dark dotted diagram; actual-404-390-viewport.png introduces green/lime styling. These read as different products. | Carry selected typography, color and composition through lesson, map, catalogue, profile and recovery surfaces. Make curriculum compact; prioritise lesson content. |
| VC-07 moderate design refinement | art/atelier-map-1440-viewport.png: six-node composition legible, but branch connectors are very pale and small secondary node copy has low visual prominence. art/observatory-map-1440-viewport.png makes connectors still fainter. | Maintain visible relationship lines and readable node subtitles at normal display/zoom; don't add more metadata to nodes. |
| VC-08 moderate mobile efficiency | atelier-lesson-360.png: prototype banner, global navigation and course rail consume much of the initial viewport before lesson content. | Remove preview-only chrome from implemented product; compress lesson context while keeping navigation available. Recheck actual lesson with realistic long Russian titles. |

## Personally opened images

Actual: fresh-login 1440 viewport; map 360 viewport; interests/profile/lesson 390 viewport; preferences 768 viewport; discovery 1440 viewport; 404 390 viewport. Prototype A: welcome desktop and 360 viewport; onboarding 360/768 viewport; map desktop/tablet/390 viewport and full mobile selected state; lesson desktop viewport/full 360; mobile feedback/saved; 2x zoom final onboarding. Prototype B: welcome desktop; onboarding 390 viewport; map desktop/360 viewport; lesson desktop/full 390. Desktop comparison and early onboarding images were opened from art/ and correspond to unchanged artifact hashes. Image generation alone is not claimed as review of all 168 files. gallery.html exposes all independent captures for subsequent review.

## Gate matrix

| Requirement | Verdict this turn |
|---|---|
| Two distinct rendered Russian directions and independent recommendation | PASS for selection package; recommend A with corrections |
| Real app/real endpoint checks on inspected baseline surfaces | PASS within stated scope |
| Automatic onboarding / interrupted persistence | FAIL |
| Saved result persisted across sign-out/in | PASS for real text practice |
| Useful visible return and coherent complete identity | FAIL |
| Mobile selected-map composition/context | FAIL in prototype |
| Complete fresh/experienced/diagnostic/challenge/source-feedback, real recursive map, course/video, uneven profile and all failures | UNVERIFIED; requires implemented redesign and complete actual journeys |
| All-page keyboard/touch/200% zoom/long Cyrillic acceptance | UNVERIFIED beyond targeted checks |
| Exact staged app + content final visual gate | UNVERIFIED; needs_work |

Manager can record A as selected visual direction; frontend must not treat selection as acceptance of these mobile failures. Fix VC-04/05 in the design/implementation, retain useful verified backend persistence, and bring the implemented connected journey back for independent review before staging acceptance.
