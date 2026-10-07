# Backend architecture audit 001 — needs_work

Reviewed 2026-10-04. No repository edits, shared data changes, deployment, service restart or process kill. Pending checkout clean at **bc4ba3c1f2eed39e42f611836d6990acf7b0a62d** before and after review. Main product brief read in full. Bilateral ownership record remains proposed, accepted UI handoff absent.

## Concrete evidence

- Actual local app at http://127.0.0.1:18871, private disposable data `/tmp/airoom-architect-_3974974`, Chromium **153.0.8010.12**, viewport **1440x1000**. Health reports pending SHA and schema 6. Graph **tree-2026-10-v1**. Isolated synthetic baseline; one explicitly synthetic transfer-shaped form `audit-transfer-v1`, one rubric, one submitted artifact, one unactivated graph proposal, one uploaded text fixture. No pending editorial package installed and no provider called.
- Loaded `/admin`, `/admin/tree`, `/admin/assessments`, `/admin/practice`, `/admin/measurement`, and diagnostic detail. Browser upload created a real protected source/job; GET job/source/file all 200 with actual content. Graph/me/node, diagnostics, forms, proposals/history, practical tasks/review, capabilities/jobs and skill measurement returned 200. Browser API calls and full DTOs: `http-browser.json`. No browser JavaScript errors on the initial admin traversal. Initially empty queues were genuine empty data, not missing routes; later populated tree and practice views were loaded and screenshots inspected.
- Opened and visually inspected admin-upload, admin-tree, admin-assessments, admin-practice, admin-measurement, populated tree/practice, and diagnostic screenshots. Desktop upload and queue contents visibly render. This is a limited architecture smoke review, NOT complete novice-teacher or responsive UI acceptance.
- Independently ran `python -m pytest --rootdir=/home/claude/ai-room-pending-review --confcutdir=/home/claude/ai-room-pending-review tests/test_release_bindings.py tests/test_retained_state.py tests/test_form_lifecycle.py tests/test_transfer_sources.py tests/test_graph_review.py tests/test_diagnostics.py tests/test_skill_measurement.py -q -p no:cacheprovider` using `/home/claude/ai-room/.venv/bin/python`: **46 passed in 40.19s**. Tests do not cover the defect below.
- Inspected staged-to-pending diff: 33 files, 2426 additions / 5 deletions. New retained source/curriculum tables, review candidates/commands and historical source reader; current-access changes in skills.py do not cover every consumer.
- Staged identity **dae021716ac92abe5fdf1253093f82ac8f3f3286**, schema 6, is manager-turn-2 evidence, NOT a fresh public-staging probe by this role (role probes restricted to localhost). Final staging still requires independent exact-build testing.

## A1 — blocking: current source authorization omitted in diagnostic and practical APIs

Source: `club/diagnostics.py:17` accessible() uses only form.access/current membership; dto() selects result body and returns feedback.source without transfer_access. `club/practical.py:22` task(), list_tasks() and list_submissions() similarly rely on original form.access; the list SQL does not supply the parent form body for current binding checks. Contrast `club/skills.py:106` and `club/transfer_sources.py:91`: challenge access checks current bound lesson/course status and access.

Reproduction on actual HTTP, using labelled synthetic source text:
1. Retain a reviewed test form with transfer_publication binding to an initially free published lesson and a source containing `PRIVATE-AUDIT-SOURCE-MARKER`.
2. Free learner starts diagnostic and challenge, submits wrong answers, then advances diagnostic.
3. Change only the bound lesson access to member in the disposable database.
4. Lesson GET and challenge resume GET now return **403**. Diagnostic detail and diagnostic history GET return **200 and the protected marker inside recommendations.source**. Evidence: `diagnostic-access-repro.json`. UI does not need to visibly print the marker for the API disclosure to be a failure.
5. Publish a test practical rubric against that form as admin. The free learner still GETs task list/detail with the protected marker (**200**), creates a submission (**201**) and submits it (**200**) while lesson/challenge remain blocked. Evidence: `practical-access-repro.json`.

Minimal engineering correction: one canonical form-content authorization predicate, reused by diagnostic planning/resume/advance/recommendations and practical task/submission list/detail/create/update. Join form.body explicitly; do not pass result.body or rubric.body to a predicate expecting form.body. Redact protected source and work fields in recovery metadata while retaining IDs and earned summaries. Keep staff access deliberate. Add real HTTP regressions for free→member, membership revocation, lesson/course withdrawal, and restoration; include both history lists and direct IDs, plus diagnostic next-form selection. No immutable evidence deletion or global graph rewrite required.

## Other exact gaps and limits

- `docs/skills-backend.md` incorrectly describes application/adaptive diagnostics/uploads as absent; `docs/teaching-backend.md` still says five-minute leases while code uses 900 seconds. Do not use those incremental documents as the integration contract. Use CONTRACT.md plus route-inventory.json below.
- `/health` schema 6 does not identify installed competency/teaching additive tables or content state. Record code SHA + migration inventory + active graph + publication/source manifest hashes separately. Do not equate schema 6 with pending migration completion.
- Inspected historical recovery `worker-service-recovery/result.json`: passing drill on **39302f2**, rollback **1bd6b76**, 900-second natural lease expiry, paired restore, later-write-preserving code rollback. Fault was injected BEFORE provider call; no live charge outcome tested. This is useful historical evidence, not final-build recovery acceptance. Paired snapshot restoration intentionally loses disposable later writes and cannot substitute for a production-safe reconciliation plan.
- Source caps, five-file packages, 6000 output tokens and three attempts exist. No monetary reservation/usage ledger in provider adapter; duration validation is after transcription. Approved provider account spend controls and actual bounded spoken-video/material run remain unverified. Isolated server deliberately has provider configuration removed; that says nothing about current shared credentials.
- Semantic acceptance of cumulative manifest **9360018f5f0a922e64ab5316fe2b065a4317de5edb77fc40519478b964639e28**, final staging review, UI handoff, live provider and recovery gates remain open. Do not publish candidate content based on this audit.

## Requirement evidence matrix

| Area | Verdict this turn | Evidence / remaining work |
|---|---|---|
| Immutable state, graph compatibility, retained rows | Limited local pass | 46 tests; schema/diff inspection; installed final state not tested |
| Current content authorization | FAIL | A1 real HTTP diagnostic/practical repro |
| Admin transport/upload | Limited local pass | Chromium pages, actual multipart upload, source reads, populated queues |
| Full novice teacher publish/correction | Unverified | No real provider-backed draft; independent admin reviewer required |
| Assessment semantics | Unverified | Synthetic test form is not editorial approval |
| Measurement contract | Limited local pass | Real aggregate endpoint + targeted tests, explicit denominators |
| Final migration/restart/restore/rollback | Unverified | Historical result only; final candidate needed |
| Real AI, cost controls, provider failures | Unverified | Provider run and configured spend boundary missing from this evidence |
| Learner visual preservation/final staging | Unverified | Accepted peer UI handoff absent |

Manager should assign A1 to backend engineer after bilateral ownership approval and ask security QA to independently reproduce and recheck. No broader rewrite recommended.
