# Proposed measurement contract — research handoff, 2026-10-04

Status: **proposed, not implemented or accepted**. Backend owns schema/events and must agree with frontend on exposure delivery. Preserve existing events and explicitly version changed semantics. Do not silently redefine historical `meaningful_return`, which currently includes lesson visits. Existing `measurement.py` activation denominator is all current learner accounts; it is not the new onboarding-exposed cohort below.

Minimum fields: pseudonymous learner ID, event ID, server received time, event schema version, content/graph version, stable entity ID when needed, onboarding attempt ID/step enum, fixture flag. First-party only. No email, prompt, answer, practice text, source document, cookie, raw IP or arbitrary properties. Pseudonymous IDs remain personal data; restrict access and define deletion/retention with backend owner. No third-party tracker is needed. Do not add a new unconstrained client event endpoint.

| Proposed event | Definition | Retry/denominator rules |
|---|---|---|
| onboarding_exposed | Welcome actually rendered for eligible signed-in learner; server render marker plus visibility acknowledgement, distinguish delivery from exposure | One per learner/onboarding version for activation cohort; subsequent edits use new attempt with edit flag |
| onboarding_step_viewed | Allowlisted step becomes visible | Unique attempt/step for funnel; repeats can be counted separately without inflating learners |
| onboarding_step_saved | Validated preference + current step persisted server-side | Idempotency key/revision; retry does not count twice |
| onboarding_skipped | Explicit skip persisted, include step enum only | Separate exit from completed questionnaire; does not imply failure |
| onboarding_completed | Final preference state persisted | Once per attempt; preference editing is not another newly activated learner |
| first_meaningful_activity | First accepted substantive practice submission or completed reviewed challenge with responses | Server-derived first occurrence; mere login, map visit, lesson load, blank draft, video polling excluded |
| first_result_saved | First nonempty practice result committed, or completed reviewed assessment result durably available | Unreviewed saved result is eligible for product activation, never proof of competence; report result type separately |
| lesson_resumed | Explicit continue restores persisted lesson/location/draft | Report requested and successfully restored separately; a generic lesson view does not prove resume |
| feedback_viewed | Learner opens actual published explanation/review decision | Dedupe learner/result/version; never log answer text; telemetry does not prove understanding |
| meaningful_learning_action | Valid substantive submission/revision, completed reviewed challenge/review, or explicit lesson completion with a learning action | Define accepted action enum; duplicate unchanged saves and completion toggling cannot farm return |
| meaningful_return | Derived meaningful_learning_action after initial qualifying learning day/session | Distinct learner/window; preserved work reopened without substantive action is continuity, reported separately |

A plain lesson read may be valuable but is difficult to infer reliably from a page request. Report content visits and reading continuation alongside the stricter learning-action metric; do not pretend one measurement captures all learning.

## Cohorts and windows

Use UTC consistently in v1 and display it; do not mix calendar-day and rolling-day rates. Exclude staff/editor/admin and fixture/smoke accounts. Public synthetic staging data validates instrumentation only. Historical missing events stay missing; no fabricated backfill.

- **Exposure activation within 7 days:** distinct eligible learners with first_result_saved in `[exposure, exposure+168h)` / distinct first-time onboarding-exposed learners whose full 168h window ended. Also show numerator/denominator and result-type split. Skippers remain in denominator. Existing returning learners/edit attempts excluded from new-user cohort.
- **Onboarding completion and skip:** distinct completed / distinct exposed; skipped / exposed. Use a declared 24h observation window with fully matured cohort. These are navigation outcomes, not activation or learning quality.
- **Step nonprogression:** unique attempts reaching step S without advancing, completion, or explicit skip within 24h / fully observed attempts reaching S. Report skip separately; interrupted is not proven abandonment. Sequence step IDs by onboarding version.
- **Time to first result:** wall-clock seconds from first exposure to first_result_saved; report median and p75 among converters, converter count, total eligible count, and 24h/7d conversion rates. Excludes no-result users from timing only, never from activation denominator. Includes off-site time; do not call it active task time.
- **D1 meaningful return:** cohort starts at first_meaningful_activity `t0`; distinct cohort learners with meaningful_learning_action in `[t0+24h,t0+48h)` / cohort learners whose 48h observation window ended.
- **D7 meaningful return:** analogous `[t0+168h,t0+192h)` / learners with 192h follow-up. Report enrollment-week cohort, n, result/action definition and uncertainty. No right-censored users in rate denominator. A seven-day aggregate return is a different metric and must be separately labelled.
- **Resume success:** successfully restored continuation / explicit resume requests, split lesson/draft/video; unavailable content should count as recovery outcome rather than silently disappear.
- **Learning evidence:** reviewed delayed-item performance and independent rubric quality reported separately from return, submissions, and completion. No subscription-renewal metric without actual entitlement/billing lifecycle data.

Zero denominator = unavailable, never zero-percent success/failure. For small cohorts show raw counts and wide uncertainty; avoid public small-cell breakdowns. No real-user analytics were accessed in this turn and no achieved rate is asserted.

## Testable hypotheses, not claims

| ID | Intervention and population | Primary outcome | Guardrails and falsifier |
|---|---|---|---|
| H1 | Fresh Russian novice: automatic short skippable onboarding + permitted small task | 7-day exposure activation; time-to-result secondary | Onboarding skip/error rates, ability to browse, two interests retained. Reject if added steps reduce activation or block experienced learners. |
| H2 | Returning learner: latest saved result + accurate continuation placed above empty profile taxonomy | Resume success; D1/D7 meaningful return secondary | Wrong lesson/draft restores, unwanted overwrites, time to reopen. Reject if click lift does not produce successful restore/useful action. |
| H3 | Learners with approved prior content: optional spaced retrieval and reviewed corrective explanation | Delayed performance on independently reviewed equivalent items | D7 meaningful return, opt-out, frustration, answer exposure; no mastery farming. Reject if only visits/repeats rise or equivalence is unapproved. |

After the mandatory usable baseline is shipped, randomize eligible consenting/appropriately informed cohorts according to platform policy, predeclare observation windows, minimum useful effect and sample-size analysis from an observed baseline; do not invent a target uplift now. Preserve one variant per learner. Do not experiment by withholding required recovery, accessibility, privacy, or honest feedback. User interviews/observed human tasks can explain problems; simulated agent walkthroughs only establish mechanical behavior and expert concerns.

## Instrumentation acceptance

QA should run a disposable novice account through exposure → two interests → next → refresh/logout → resume → skip or complete → permitted task → save → feedback → continuation. Reconcile event rows against those exact actions, repeat the same requests and ensure idempotency. Use a second seeded cohort with controlled timestamps to verify D1/D7 boundary inclusion/exclusion, zero denominators, staff/fixture exclusion and late ingestion. These are synthetic correctness tests, never evidence of user retention. Coordinate this bounded implementation with backend owner; do not add an independent analytics subsystem from the UI loop.
