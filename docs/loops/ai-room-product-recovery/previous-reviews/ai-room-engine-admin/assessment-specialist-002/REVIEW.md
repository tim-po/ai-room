# Independent assessment recheck — needs_work

Exact candidate b32d43fb94bdb523750d1b20cd702062815d93bc; graph curriculum-aa69319f873d2dc30c38d1f67184d77c4e4b08ed8d21b58358e242909f601350. URL http://127.0.0.1:18764, Chromium 153.0.8010.12, viewport 1440x1000. Test database copied from prior disposable review fixture into a new /tmp directory; new synthetic learner; no shared application, learner data or content publication changed. Review script: /tmp/assessment-review-002.py. Actual HTTP/browser evidence: result.json. Opened and inspected all three PNGs.

## Decisions

Preserve every exact-artifact decision in ../assessment-specialist-001/decisions.json. No new content has been authored or approved by this reviewer. Seven transfer forms remain revise, all equivalent-retake claims remain unapproved, and actual provider-generated output remains unverified. Earlier acceptance of narrow taught-case items/mappings and two synthetic practical instruments does not authorize arbitrary runtime hashes or shared publication.

Reproduced verification transfer form missing its case before answering. The browser displays the combined proportion question without the report containing 8/10 and 45/90; the exact source API returns 200 and the correct report. Correct-choice positions remain [0,1,2]. Runtime raw body hash 111ae31b20836bf38ca7c734f88ab3b9badbc5772f8a7b2a423ce11cde3277b9; canonical hash d4a6cc7365def8d6954a9785d0e2e58595a304672c842c6d218c45e659d5d080. This is the same disposable binding used for the earlier reproduction, not a publication decision. skills.py attempt_dto still exposes only id/prompt/choices/type/objective_id; challenge.js still shows exact source via result feedback. Git diff of these files and diagnostic.js against bc4ba3c is empty. Do not spend another semantic acceptance pass until authorized source/choice presentation fixes are available.

## State and lifecycle evidence

Fresh learner began unknown with no understanding/application evidence. A 2/3 foundation attempt produced partial feedback, no credit; a perfect repeat returned practice without new credit. Real graph, node, attempt start/submit/resume, learner-state and exact-source APIs returned success and populated content. Screenshot inspection confirms partial and practice-only labels match responses. The capabilities endpoint returns expected 403 to this learner; this is not a provider-readiness test. Positive first-attempt understanding and human applied-review browser rechecks are still required on final integrated candidate.

Independently ran tests/test_current_content_access.py, tests/test_form_lifecycle.py, tests/test_practical.py and tests/test_release_bindings.py: 27 passed in 39.41 seconds. This provides current HTTP access-change and supporting withdrawal/uncertain-review/version-preservation evidence, not final staged acceptance. Initial browser harness omitted the explicit start-button click and timed out; corrected harness completed without application changes.

## Remaining gates

Latest pipeline names-only provider-status.json reports CLUB_AI_APPROVED not approved, CLUB_AI_API_KEY and CLUB_AI_MODEL absent, ffprobe absent. No real spoken-video/material output supplied, so timestamp/source/item/rubric semantic approval cannot occur. Monetary controls are additionally reported unresolved by pipeline engineer.

Read-only loopback staging health at 127.0.0.1:8098 remains dae021716ac92abe5fdf1253093f82ac8f3f3286, schema 6. This is distinct from the tested local candidate. No final staging browser or exact integrated build signoff issued. Requirement verdict: transfer delivery FAIL; equivalence UNAPPROVED; real-provider semantics UNVERIFIED; tested partial/repeat separation PASS; lifecycle/access targeted checks PASS with stated limits.
