# Independent visual gate 004 — needs_work

2026-10-04. Exact clean candidate **ddc0f32e37a045687f9aecaffbda5b964aa77514**, `/home/claude/ai-room-product-experience`. Independent expert/simulated evaluation; no human usability participants. No application edits, retained-data mutation, deployment, process kills or subagents.

Actual headless Chromium **153.0.8010.12**. URLs: onboarding `http://127.0.0.1:18991`, assessment `:18882`, code case `:18992`, complete first-session/return journey `:18993`. Disposable SQLite and instance directories under /tmp. Onboarding/assessment/code captured at **360×640, 390×844, 768×900, 1440×900**; journey at 360×844, 390×844, 768×900, 1440×900. Full-page and viewport images, executed harnesses, API response logs and state rereads live alongside this report; gallery.html provides a browsable index. Source hashes in source-ledger.json.

## Decision

**Close VC-12/13/14/15 for the tested local scope. Keep product acceptance blocked by VC-03 return continuity and the incomplete approved first-result journey.** Case transport/presentation passes its bounded visual and interaction check; this does not approve editorial content or retake equivalence. No final staged verdict is possible from this local evidence.

The revised onboarding is substantially better composed. The visible terracotta action, optional secondary actions and quieter status now form a task hierarchy across desktop and mobile. Warm paper, Golos, green selection and restrained illustration remain consistent with selected Atelier. Help no longer has pale text on a pale panel. I reopened the selected Atelier lesson reference (`../visual-critic/atelier-lesson-1440-viewport.png`): its concrete worked example remains stronger than the actual seed lesson's generic instruction under “Разбираемся на примере”. The current design direction is viable; a polished shell does not complete the instructional task.

## Corrections independently rechecked

| Requirement | Verdict and evidence |
|---|---|
| VC-12 onboarding controls | **Pass tested widths.** Opened `onboarding/pace-{360,390,768,1440}-viewport.png`, `pace-last-choice-visible-360.png`. At 360×640 time choices require scrolling, but the main action stays visible and every focused choice passes hit-testing above the footer. Last-choice screenshot shows all time choices and actions together. No global bottom tabs during onboarding. Conflict/retry also remain reachable. |
| VC-13 dirty vs saved state | **Pass.** `onboarding/dirty-interests-390-viewport.png` says unsaved while the server still has empty interests. After acknowledgment, the server and displayed step agree. Error copy does not retain stale success. |
| VC-14 browser history | **Pass bounded sequence.** Fresh login → two interests → pace → browser Back/Forward; step, revision and selected interests persist. Editing experience then explicit Back/refresh also preserves it. Actual concurrent server PUT returns 409 on stale continuation; reload recovery restores current data. `onboarding/conflict-360-viewport.png` and `error-390-viewport.png` opened. Exhaustive ABA/uncertain-write concurrency remains QA scope. |
| VC-15 Help legibility | **Pass.** Opened `onboarding/help-390-viewport.png` and `help-1440.png`; dark heading/label on warm panel. Computed foreground rgb(41,46,40). Separate real Help POST in journey persists a visible synthetic ticket. Support reply/history integration remains unfinished. |
| Case before choices | **Pass for two disposable fixtures.** Opened assessment case at all four widths and code case desktop/mobile. Exact API case bytes appear before stable ordered choices; reload preserves them. Keyboard Space selects; submission returns retained feedback. Diagnostic genuinely resumes the foundation attempt and returns to results. Code source disclosure fetches retained source successfully. |

## Remaining failures and corrections

| ID / severity | Screenshot-specific finding | Expected correction |
|---|---|---|
| VC-03 / blocker, reproduced | `journey/profile-viewport.png` leads with saved “Границы и разрешения агента”; after logout/login `journey/return-viewport.png` instead says “Первый небольшой шаг” and links `/lessons/foundations-start-01`. The completed onboarding and saved practice were `/lessons/agent-lab-intro-01`. `journey/map-1440.png` shows the same mismatch on desktop. | Integrate the named continuation handoff and consume one server-selected context on home/profile. Recheck unfinished work vs last result, cross-branch edits, login and denied content. Do not close from the presence of a separate saved-work link. |
| First useful result / major existing scope failure | `journey/lesson-390-viewport.png`: “Разбираемся на примере” presents generic task instructions, without the concrete worked case promised by the selected direction. `journey/start-768-viewport.png` sends a fresh beginner to the agent lesson. Saving text succeeds, but is not meaningful instructional feedback. | Install/consume the approved first activity and recommendation; provide the actual source-comparison task and honest comparison feedback. Keep semantic approval distinct from this visual review. |
| Assessment reading hierarchy / minor | `assessment/challenge-case-360-viewport.png`: header, title and instructions fill nearly all the short viewport; first case is below it. Full desktop capture repeats the identical case three times. Code source is readable but code and prose share typography. | Compact assessment intro and consider a clearly labelled shared-case presentation where source binding allows it. Preserve case access at each question and stable choices. This is not a new blocker for the three-question fixture: actual scroll, keyboard answer selection and submit work. |

## Journeys and real endpoints

Fresh synthetic ordinary account, automatic onboarding, two interests, server acknowledgment, refresh, logout/login resume, explicit Back, permitted first lesson, saved practice, failed resave retaining text, retry, profile, interest edit preserving work, map selection/list/search/recenter and logout/login return were exercised on this exact SHA. Separate fresh account skipped onboarding. Help submission persisted. Loaded actual catalogue/preferences/help/404 and map routes. API observations: onboarding 48 responses (four intentional 409 conflicts and four simulated 502s); foundation assessment 65 successful responses; code case 33 successful responses; main journey 52 successful API responses. No application page errors in these runs. Direct browser request probes verify actual graph, learner state, node detail, onboarding, attempt and saved practice JSON. Retained code source route returned HTTP 200 at all four widths. Server-rendered Help uses a form POST, not an invented API. Logs/evidence describe the exact calls.

Content is disposable ordinary seed + init-skills + init-onboarding. Graph `tree-2026-10-v1`, root basic-ai. Canonical graph JSON hash using ensure_ascii=False: `8634a70d10413cb0d7dc71e9400c3079f2a9c6ebc36e0ddafa509020207bd918`. Journey hash `c19c98ce…` uses ensure_ascii=True serialization, not a different graph version.

Temporary delivery fixtures only, **not editorial approval or retained/staged publication**:
- Foundation form `5ae6314a8fb03ce5849c320e51017dc3e2c68bf70b36ebaf293053c4b22547fe`; case `f46f852a4a97276d59199690028bf6a7f78eb820315a4394f9cbd49eba0103d1`.
- Code-review form `b4084de80287f699316d8bfa82ce119909162a097f4309d9e83c3b43a0d7d4cb`; case `b2ec243279b7a459636d381128ca3feba671f4853358b2d397eb6a0ad758818d`.

Harness transparency: onboarding and assessment scripts were adapted from builder harnesses and rerun by this independent reviewer, followed by separate full-journey reproduction and personal image inspection. Initial onboarding port 18881 was occupied; selected unused 18991 without touching that process. First code-fixture pass incorrectly assumed its specialist form would appear in a fresh foundation diagnostic; timed out on the absent link. Corrected the harness to review specialist challenge directly; this is not evidence of an application error. Final code run succeeds at four widths. Full-page captures place fixed bottom tabs at the original viewport position; task captures and actual scrolling, not that compositing artifact, establish reachability.

## Personally opened images

Onboarding: pace at all four widths, last-choice 360, dirty-interests 390, conflict 360, error 390, Help 390 viewport and 1440 full-page. Assessment: challenge-case 360/390/768 viewports and 1440 full-page; choices 390; feedback 768 viewport and 360 full-page. Code: code-case 360 full-page and 1440 viewport, choices 390, source-open 768. Journey: return/profile/lesson 390 viewports, map 1440 full-page, welcome 360/1440 viewports, start 768, failed-resave viewport. Selected Atelier desktop lesson reference reopened. Other captured files are not claimed personally opened.

## Gate matrix and limits

| Requirement | Status |
|---|---|
| Four assigned onboarding/Help corrections | Pass bounded local scope |
| Cyrillic case/choice/feedback/source presentation | Pass two actual delivery fixtures |
| Fresh entry, two interests, resume, skip, saved work/error recovery | Pass tested local journey |
| Correct home continuation after login | **Fail** |
| Approved concrete first activity and meaningful feedback | **Incomplete** |
| Keyboard choice access, reduced-motion emulation, no horizontal overflow | Pass bounded tests |
| Native 200% browser zoom, virtual keyboard, complete accessibility and stress matrix | Unverified |
| Full video playback/resume, map→lesson context roundtrip, all access/media/offline states, next-day/long-absence journey, approved assessed profile | Unverified this turn |
| Exact staged app/content final acceptance | Unverified |

Public staging health could not be accessed by web tool this turn. Builder-reported dae0217 is not a new independent health verification. No staging deployment or acceptance authorization. **Final verdict: needs_work on local ddc0f32 and the precisely limited content above.** Preserve closed correction findings; fix continuation and approved first-result integration, then schedule the remaining full-product and staged visual gates.
