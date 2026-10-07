# Independent learning review 018 — needs_work

2026-10-05. Expert/simulated evaluation, not a human usability study. Current brief read in full. App **58af5d9aece9615fd8c883c85a1f146f557082cb**, clean before and after. Chromium **153.0.8010.12**, local URLs **http://127.0.0.1:18936** and **http://127.0.0.1:18937**, disposable /tmp databases. No repository edits, retained-data mutation, deployment or service restart. Staging SHA/content NOT reverified; this is not staging acceptance.

Ordinary synthetic seed + init-skills + init-onboarding; graph tree-2026-10-v1 canonical response SHA256 **c19c98cef4c00cce21f36c796f2c8732b7229557b56da9546d786a7308a76553**. Source hashes, exact rendered text, URL, viewport, network transactions and fixture paths are in evidence.json. No reviewed assessment forms installed in this disposable inventory. Do not infer staged form availability from that absence.

## Independently exercised

Fresh account login automatically opened onboarding. Selected Coding + Content, beginner, 5 minutes; refreshed, went Back, logged out/in before completion and recovered the acknowledged choices. Opened the recommended first lesson; submitted, revised, deliberately aborted a save, retried and recovered exact saved text after login. Edited interests to add Agents without losing work. A second fresh account skipped onboarding and stayed skipped in a new browser context. Opened optional diagnostic and challenge unavailable states.

Separate cross-branch journey: skipped onboarding, completed foundations-start-01, then saved an unfinished agent-lab-intro-01 draft. Both home and profile linked to **/lessons/agent-lab-intro-01#practice**. Logout, new browser context and login preserved that continuation; clicked it and read back the exact draft. Foundation completion remained 1. Prior incorrect-default-continuation finding is closed for these tested paths. Access withdrawal, isolation and long-absence combinations remain unverified this turn.

Onboarding start captured at 360/390/768/1440 × 844; main journey 390×844, cross-branch recovery 1440×900. Actual request log has no HTTP >=400. Intentional aborted save is a separate network failure, with stale-success message correctly hidden. Explicit endpoint opens all returned nonempty 200: onboarding (779 bytes), graph (15804), me (7618), limitations node (337), diagnostics (749), practice (395), checklist attachment (167). Real onboarding PUT, practice POST and diagnostic POST were exercised; diagnostic creation returned 201 with honest unavailable state.

Opened and visually inspected start-360-viewport, start-1440-viewport, first-lesson full page, saved-viewport, return-viewport, profile-viewport, diagnostic-unavailable-viewport, experienced-challenge-unavailable-viewport, cross-branch-home full page and cross-branch-restored-1440 full page. Clear action hierarchy and explicit unknown/unreviewed labels support the bounded tasks. Full-page fixed navigation appears at the viewport boundary; screenshots alone do not establish an obstruction. This is not full-product visual/accessibility acceptance.

## Requirement-to-evidence matrix

| Requirement | Verdict | Evidence / required correction |
|---|---|---|
| Automatic, optional, persistent multi-interest onboarding | PASS bounded | Fresh login, two interests, refresh/Back/logout recovery; skip survives new context; later three interests coexist. |
| Save/revise/retry/reopen work with honest status | PASS bounded | Exact text restored after retry/login/preferences edit; saved acknowledgment explicitly says no proficiency confirmation. |
| Cross-branch continuation | PASS bounded | Completed foundation + unfinished agent draft; home/profile/new context all select the actual draft. Completion remains intact. See cross-branch.json. |
| First achievable novice activity | FAIL | 5-minute beginner receives 10-minute agent lesson. Heading promises an example, but body only asks learner to choose their own task; no source, flawed answer or worked comparison. |
| Meaningful first feedback | FAIL | Storage acknowledgment and generic checklist work; explanatory self-check is absent. Cannot close the learn/practice/feedback cycle. |
| Meaningful return and onboarding/activation analytics | FAIL | After inserting only yesterday's learning-day fixture, GET lesson emits meaningful_return=1. Actual code lesson route calls learning_activity on GET; measurement.py counts calendar activity and all learner accounts, rather than required mature exposure/activity cohorts. |
| Optional diagnostic, unknown proficiency | PASS unavailable-state only | Honest no-results/no-credit copy and available-lesson exit. No successful assessed journey or semantic form acceptance established. |
| Reviewed challenge/partial feedback, complete unit, long absence, supporting/error/media/access surfaces, native zoom and full keyboard/touch matrix | UNVERIFIED | Not covered by this bounded correction check. Prior fixture tests cannot establish exact-current production content approval. |
| Exact staging app/content and retained learner journeys | UNVERIFIED | Not inspected this turn; no deployment acceptance. |

## Concrete next work

1. Install and connect the exact previously approved narrow instructional self-check, preserving IDs: first-result proposal SHA256 **668ac857e48f2cba0d45513d443050cb0c8bd3636bcd4fd605bd440284b7a4d2**, title «Исправьте ответ по исходным заметкам». learning-003/content-decision.json remains the bounded semantic decision, not proof of installation. Required UI: actual fictional notes and flawed answer → attempt → optional comparison explaining unsupported details → revision → confirmed save → profile reopen. Comparison is source verification, not memory retrieval or proficiency evidence. Do not add automatic grading claims.
2. Backend-owned versioned substantive-activity measurement remains necessary. Keep legacy counts explicitly separate. Passive GET/login/heartbeat, unchanged save and completion toggles must not count as meaningful learning return. Separate draft continuity, submitted artifact proxy, feedback exposure and reviewed assessment evidence; exclude staff/fixtures and raw text/answers/session data.
3. Follow the latest manager-direction-007 / learning-004 windows, which supersede the initial contract's calendar-day variant: D1 [t0+24h,t0+48h), D7 [t0+168h,t0+192h), t0 first qualifying substantive action, fully mature 48h/192h denominators and null for zero. Activation: eligible onboarding-exposed learners with explicit nonempty artifact submission within 7 days / fully observed eligible exposed learners, including eligible skippers. Report converter counts, denominator, median/p75 elapsed time and nonconverters separately. Onboarding funnel uses mature 24h observation and distinguishes viewed/saved/skipped/completed; action ledger alone is not exposure.
4. Recheck remaining full journeys and exact installed content after these corrections, then the same deployed app/content ledger. Synthetic smoke demonstrates instrumentation only; no achieved learning or retention uplift asserted.

No new external empirical claim or content approval issued. Existing primary-study research and journey contract remain background; today's decisions follow observed code, HTTP responses and actual Chromium tasks. Overall **needs_work**: novice first-result/feedback and measurement are material blockers, despite working onboarding persistence and corrected continuation.
