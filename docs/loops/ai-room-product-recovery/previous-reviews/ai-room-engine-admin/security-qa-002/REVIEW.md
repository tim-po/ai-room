# Independent QA turn 002 — needs_work

Exact candidate: 775f69bf6d8a5dbe7e3a5f503d96e748b196b85a, clean before/after. Local actual HTTP http://127.0.0.1:18883; Chromium 153.0.8010.12 at 1440x1000 and 390x844. Disposable /tmp database with seeded accounts, seven explicitly local transfer publications and one synthetic support ticket. These publications are test fixtures, not editorial approval or shared publication. Exact seven hashes in result.json; graph body SHA256 c3a055181b36104aca4f4e28cce249006e5bc0f329e03efbb50574cc513e0246. Read full current brief, historical capabilities/policy/unresolved gates, current-direction and changed source. No repository changes, staging mutations, service restart or process kill.

## Concrete results

- New onboarding API: actual PUT succeeds 200; identical request replay matches; conflicting key returns 409; missing CSRF 400; forged user_id 400; staff GET 403; second learner retains empty interests. Skip 200. Five hostile login redirect targets (external, protocol-relative, encoded slash, backslash, admin) all redirect to /. **API limited local pass.**
- **Integration blocker O1:** fresh login routes to /onboarding which returns 503 with bare “Onboarding screen is awaiting the UI integration.” Browser screenshot onboarding.png inspected. Migrating onboarding on this candidate strands new users until UI integration; do not deploy this combination.
- Seven transfer attempts each POST 201; exact retained case present in all item DTOs, only permitted item/choice keys, no answer/rationale metadata, stable GET presentation, unrelated learner 404. Changing bound lesson to member-only makes case GET and request replay 403. **S1 backend delivery limited local pass.**
- **S1 remains blocked end-to-end:** actual challenge screen displays questions/choices but omits returned case, confirmed by DOM exact-source check and inspected challenge.png. Renderer integration is still required; semantic/equivalent-retake approval remains specialist-owned. Synthetic publishing here grants no editorial acceptance.
- **A2 locally closed:** opened populated assessment impact after bound lesson became member-only. View now says declared assessment tier is free and explicitly explains current lesson publication/tier and subscription also govern access; free form does not unlock subscription lesson. Inspected assessments.png; actual impact reflects one learner/attempt and zero evidence. Enforcement 403 above.
- Support actual browser answer save succeeds; learner GET returns saved reply, different learner list empty/detail 404; learner handle 403, staff missing CSRF 400. Repeated reply returns 200 without extra audit entry, stale differing reply 409. Two actual distinct successful replies yield exactly two audit rows. Browser conflicting save retains “My unsaved correction” and displays recovery instructions. Question/reply IMG/onerror text renders literally, no dialogs. Inspected support.png, support-conflict.png and support-mobile.png; no mobile horizontal overflow. Captured real 200 graph/capabilities/jobs/ticket/save calls and expected 409 conflict in result.json. Empty jobs represent intentionally empty fixture queue.
- **P2 remains incomplete end-to-end:** reloaded learner /help shows original question and raw “handled” status but no saved answer; direct learner API has reply. learner-help.png inspected. UI consumer required before support can be called complete.
- **Minor T1:** browser tab title is literally `Мастерская преподавателя<script defer src="/static/support_admin.js"></script> · AI Room Club`. club/templates/admin.html line 1 puts a script inside title block. Remove that occurrence; body already loads script. It does not execute from title, so this is a title defect, not an XSS claim.

Independently ran existing tests/test_onboarding.py, test_challenge_presentation.py, test_support_admin.py in candidate cwd using isolated pytest root/confcutdir: **20 passed in 28.52s**. This supports concurrency, persistence, duplicate-credit, legacy ordering and malformed source binding checks; browser/HTTP evidence above is independent of these tests. Initial run from wrong cwd had import errors; corrected cwd run passed. Shell `python` alias absent; used existing venv interpreter. Neither is a product failure or capability denial.

## Acceptance matrix

| Gate | Status | Evidence |
|---|---|---|
| New onboarding API boundaries | Local limited pass | result.json + 20 targeted tests |
| Optional onboarding browser journey | Fail / integration pending | Actual 503 and onboarding.png |
| Pre-answer case security and stable presentation | Local backend pass | Seven actual attempt DTOs; source hashes; revocation/isolation checks |
| Pre-answer case visible to learner | Fail / integration pending | challenge.png, case_visible_in_browser=false |
| Admin current-access label A2 | Local pass | Member-only bound lesson; inspected impact view |
| Support handling security and stale-save UX | Local limited pass | HTTP statuses, audit row count, inspected screenshots |
| Learner receives support answer P2 | Fail / integration pending | API reply exists; /help omits it |
| Real AI spoken-video + material run and provider failures | Unverified / blocked | Fresh local capabilities: processing_available=false; CLUB_AI_APPROVED, CLUB_AI_API_KEY, CLUB_AI_MODEL missing. This harness deliberately clears those names and makes no provider request; it does not independently establish staged config |
| Final recovery, graph/lifecycle regression, approved learner visual preservation | Unverified this turn | Requires integrated final build and independent recovery review; prior local evidence not promoted |
| Same-SHA/content public staging signoff | Unverified | Fresh permitted loopback service health :8098 remains dae021716ac92abe5fdf1253093f82ac8f3f3286/schema6, different from this candidate |

Role permits localhost probes only and prohibits service restart/process kill. Public HTTPS and required independent recovery drill remain capability dependencies; no denied command attempted and no workaround used. Manager should coordinate missing UI consumers, assign T1 to admin engineer, retain S1/P2 integration gates, and obtain approved provider/spend readiness plus exact integrated staging review. No repeated unchanged A1 baseline audit performed.
