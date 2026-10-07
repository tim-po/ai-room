# Independent QA 015 — needs_work

2026-10-05. Actual headless Chromium 153.0.8010.12. Exact clean application **58af5d9aece9615fd8c883c85a1f146f557082cb**, checked before/after. Disposable local servers **http://127.0.0.1:18881**, **:18886**, **:18887**, **:18888**, temporary databases and synthetic accounts; no repo edits, production changes, staging writes, deployment or service restart. Expert/agent simulation, not human usability research.

Widths: **360×640, 390×844, 768×900, 1440×900**. Main audit uses four genuinely fresh provisioned accounts; continuation and support use separately seeded accounts in isolated databases. Credentials are generated in memory and excluded from evidence. Content: ordinary seed + init-skills + init-onboarding; support additionally init-support. Graph SHA256 (Unicode-preserving sorted JSON) **8634a70d10413cb0d7dc71e9400c3079f2a9c6ebc36e0ddafa509020207bd918**. Support lesson inventory digest **f8cb55702c470b43554efdae9228c2ad8aa42591ce04176f21b3112c650d8d30**. Continuation digest **f52360d22618c87d5348fec1546dfdf2bd77eb9b194dd57385616ea1fee03f6a** includes its deliberately changed access fixtures. These are not approved-content publication manifests.

## Findings and decisions

**QA-03 continuation CLOSED for the tested local candidate.** Current home and profile both lead to `/lessons/agent-api-basics#practice` after completed foundations and a saved unfinished second-branch draft. Last result separately points to `/lessons/foundations-start-01`. Reopened through keyboard and checked exact draft readback, changed interests, logout/login, fresh browser contexts at every width. Another learner receives neither record. Expired entitlement fixture removes inaccessible continuation/result and retains saved draft and completion; profile explains preservation. Evidence: `continuation/evidence.json`, `continuation/run.log`, `continuation/home-360-viewport.png`, `continuation/profile-768-viewport.png`. The main fresh-account journey also now returns to the correct agent lesson (`return-viewport.png`, `evidence.json` home_links).

**QA-15 support keyboard focus regression — correction required.** On `/help`, focus `#support-refresh`, press Enter, let refresh fail with injected 503, then retry with Enter after restoring the real endpoint. Refresh succeeds and answer is retained, but `document.activeElement` becomes BODY at **all four widths**. Disabling the focused button in `club/static/support.js` drops focus and the finally block does not restore it. Preserve keyboard position during refresh or restore focus when activation originated there without stealing focus from subsequent navigation. `support/evidence.json` focus_after_retry and `support/focus-after-retry-*.png` reproduce it. This is a bounded accessibility finding; it is not the sole reason the overall gate fails.

**Meaningful-return measurement FAIL remains independently reproduced.** In an isolated fresh learner database, insert a synthetic prior-day learning row, then only navigate to a permitted lesson. GET returns 200 and increments meaningful_return from 0 to 1 with zero practice rows and no video play, answer, or substantive task. `measurement/evidence.json`, `measurement/audit.py`. Real browser navigation confirms source behavior: lesson GET in `club/__init__.py` calls learning_activity; `club/measurement.py` emits return on a new calendar date. Fixture validates event behavior only; this is not an observed real learner retention statistic. Required substantive-activity/D1/D7 replacement remains open.

**Exact staging delivery FAIL remains.** Independently opened https://airoom.nolimlabs.uk/ in Chromium; GET `/health` is 200 with build **dae021716ac92abe5fdf1253093f82ac8f3f3286**, schema 6. Opened `staging-welcome-viewport.png`: old dark map, not local cream/green welcome/onboarding. No staged fresh-account or redesigned-product signoff is claimed. Public staging was read-only.

**First meaningful instructional result remains UNVERIFIED.** A fresh beginner choosing coding/content is sent to `/lessons/agent-lab-intro-01`; stored practice survives edits and new login, but this generic seed does not prove the approved source-comparison activity, teaching feedback or appropriate novice recommendation. Challenge and diagnostic inventory is empty in this disposable seed; the unavailable state is honest, but no successful experienced challenge, feedback or uneven evidence profile is signed off. Do not infer missing shared approved assessments from disposable seed inventory.

## Other independently exercised behavior

- Fresh sign-in automatically reaches onboarding. Two interests survive explicit Back, refresh, logout/login and new browser context. Skip, preference editing, practical result save/readback and cross-user isolation work.
- Lost response after a real committed onboarding mutation retains selections; retry sends identical payload/key. Failed practical resave shows recovery and subsequent save succeeds. Main harness emitted an asyncio CancelledError while disposing the intentionally withheld route; process exited 0, browser page-error list empty. This harness cleanup warning is not a product defect.
- Map selection, close/focus restoration, search/list/reload/reset and touch selection were exercised. No document overflow in 74 main screenshot states. This does not establish the full deep mapped-learning roundtrip.
- Support: actual question POST, admin response POST, own history GET and fresh login exact response readback pass. HTML payloads render literally without executing. Long unbroken Cyrillic wraps. Failed refresh retains answer; failed initial fetch retains question; actual retry restores answer. Other learner direct ticket GET returns 404; signed-out history absent. All four widths exercised. `support/final-run.log`, `support/evidence.json`.
- Loaded catalogue (7 items), long course (37 lessons), lessons/practice, profile, help, preferences, map/list, challenge unavailable and 404. Actual graph/me/node/onboarding/practice requests returned 200 with nonempty content; diagnostics returned a genuine empty inventory. Learner admin/measurement/member lesson/member practice 403; anonymous practice 401; another learner's practice null. Expected denials are successful boundaries, not backend defects. Main temporary media directory has no media fixture, so black video/404 media is a setup limitation and video acceptance remains unverified.

Harness provenance: main audit copied the prior independently authored QA script and executed it on the new candidate; continuation/support rerun disclosed builder browser harnesses, corrected support's CSP-incompatible string wait to function wait, and replaced its failing focus assertion with recorded observed outcomes to finish the remaining checks. No product source changed. Initial support CSP EvalError was a harness defect, not an app failure; the subsequent real focus failure is preserved separately in rerun.log. Measurement probe is independently authored this turn.

## Opened-image inspection

Personally opened this run's welcome desktop, full mobile interests, pace 360, return mobile, old staging mobile, catalogue 360, course 390, lesson 1440, help 390, challenge unavailable 390, 404 390, map 1440, continuation home 360/profile 768/expired home 390, support answer 360 and full failed-refresh 390. Cream/green surfaces, dark Russian text, terracotta actions and consistent spacing render legibly in these inspected views. On 360 pace, time controls are below the first viewport and require scrolling; visible footer retains actions. Support long text remains readable and failed refresh retains content. Local home now visibly prioritizes saved work. Full-page captures include fixed navigation at the capture scroll position; they are not proof that all content is permanently obscured. Other gallery screenshots are captured evidence, not individually visually approved. No blanket visual approval or benchmark-complete claim.

## Requirement matrix

| Requirement | Status | Current evidence / limit |
|---|---|---|
| Automatic fresh onboarding, skip, two interests, explicit Back, refresh/logout resume | PASS | evidence.json four fresh accounts |
| Saved practice, preference editing, new-context persistence, cross-user isolation | PASS | evidence.json |
| Consistent home/profile continuation and separate last result | PASS | continuation/evidence.json; QA-03 closed locally |
| Entitlement loss retains work and removes forbidden continuation | PASS | continuation fixture and screenshots; not full access matrix |
| Support response/history/escaping/failure/retry/privacy | PASS | support/evidence.json, real endpoints |
| Support keyboard focus after refresh | FAIL | BODY at 360/390/768/1440 |
| Passive GET excluded from meaningful return | FAIL | measurement/evidence.json 0→1 event without substantive activity |
| Four-width core page renders, map touch/search/list | PASS within tested scope | 74 main captures and API evidence; not complete accessibility approval |
| Browser Back/Forward, O1 cross-route ABA/conflict | UNVERIFIED this SHA | Earlier candidate evidence is not inherited |
| Native browser 200% zoom, complete reduced motion/accessibility | UNVERIFIED | Reduced-motion media preference exercised; no native zoom acceptance |
| Deep branch→approved lesson→map context, complete discovery filters/favorites | UNVERIFIED | Bounded navigation only |
| Video playback/resume/media failure and all revoked/unpublished/access states | UNVERIFIED | Empty temporary media fixture; full matrix pending |
| Approved first instructional result and novice recommendation | UNVERIFIED | Synthetic practice storage only |
| Successful experienced challenge/feedback/source/uneven strengths | UNVERIFIED | Empty disposable inventory; no semantics inference |
| D1/D7 privacy/cohort measurement | UNVERIFIED/FAIL | Passive-return defect; no real retention claims |
| Exact redesigned staging and final content manifest | FAIL/UNVERIFIED | Old dae0217 still public; candidate not staged |

Next: fix focus and substantive measurement; integrate approved first-activity/content and finish remaining mapped/video/assessment/accessibility gates on one exact candidate, then authorized sole-owner staging deployment and independent same-build recheck. Overall **needs_work**.
