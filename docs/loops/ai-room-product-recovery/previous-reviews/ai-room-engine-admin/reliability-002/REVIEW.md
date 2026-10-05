# Independent reliability review 002 — needs_work

2026-10-04. Full current product brief read. No repository edits or shared state changes. Current clean candidate **775f69bf6d8a5dbe7e3a5f503d96e748b196b85a**, based on pending bc4ba3c. Separate executor drill **0aff086d0608ee8b24a6d83b2def536993655455**, rollback **6dfdc99062cc21d9b11f5dca86f5244b36df3e1d**. Neither is a final accepted UI-integrated staging build. Staging identity remains historical manager evidence; no remote HTTP allowed by reviewer instructions.

## Direct evidence

`review.py` / `result.json`: independently launched isolated app at http://127.0.0.1:18874 with temporary DB and files. Fresh init-db, seed, init-skills, init-teaching; synthetic fixtures only, no pending editorial pack. Chromium 1440x1000 profile and 390x844 admin; screenshots actually opened and inspected. Saved practice and 1/37 completed lesson rendered; competence remains unknown. Admin renders retained source.txt, unavailable-provider explanation and refresh action. Zero browser JS errors. Real graph/me, lesson/practice/media and teaching capabilities/list/detail/source/file endpoints succeeded with nonempty responses; upload 201, missing-provider retry expected 409 with unchanged job. The inherited script's guessed /admin/teach and /admin/teaching 404s are discovery paths, not calls made by the actual page.

Repeat init-db/init-skills/init-teaching/**init-onboarding/init-support** preserves all 133 prior rows across 49 preexisting tables. `module-migrations.json`: onboarding backfilled five users, both repeats produced private 0700 backup directories and 0600 databases with integrity ok. Onboarding snapshots include learner media and protected uploads. Support snapshots are DB-only as documented; deployment still requires paired files/signing key. Empty support/onboarding event tables are not evidence of populated-history preservation. All remain global schema 6: `/health` alone cannot prove module migrations installed.

Offline paired DB/upload/media restore hashes and snapshot learner state pass; compatible historical source process reads later practice/uncompletion without erasing rows. Historical 1bd6b76 used only as a read-compatibility probe, not approved operational rollback or security target. See result.json for exact graph version/hash and limits. Restored handler check is not supervised HTTP restore.

Targeted verification at candidate 775f69b: `python -m pytest --rootdir=/home/claude/ai-room-engine-admin-work --confcutdir=/home/claude/ai-room-engine-admin-work tests/test_onboarding.py tests/test_support_admin.py tests/test_teaching_worker.py tests/test_retained_state.py -q`: **20 passed in 18.34s**. Includes populated attempt/evidence preservation for onboarding, paired backup, help response persistence/conflicts and worker state regressions. Tests supplement real browser/HTTP observations.

## Corrected recovery harness and live independent observation

Read full scripts/check_service_recovery.py. R1's original readiness defect is repaired in source: only the fault-injection child overrides readiness, denies socket connects, pauses after real claim, and is killed by the executor. Normal production worker remains provider-gated (independently verified through real CLI and HTTP on current candidate). No provider credentials, network calls or interrupted paid request acceptance inferred.

Executor evidence: ../deliverables/ai-pipeline-004/events.json, result.json and driver-result.json. The corrected script populates one row each in attempts, understanding evidence, practical submissions, human decisions and application evidence, then compares exact contents through migration, rollback and paired restore. It copies both learner media and protected uploads. Existing authenticated sessions survive restart/restore, supporting signing-key continuity. The original 900-second lease is not rewritten. This is Gunicorn/queue child-process lifecycle, not installed systemd service testing.

I independently read the live disposable DB read-only: real running claim, attempt 1, lease_until 1791127678; five populated history tables each have one row. `executor-observation-before.json` records graph tree-2026-10-v1 and exact persisted graph-row hash. `executor-browser.json`: actual loopback http://127.0.0.1:37517/login rendered in Chromium 1440x900, health returned build 0aff086d/schema6/ok. Opened executor-login.png; form visibly rendered. No executor credentials accessed. Restart/kill were performed before my observation by the builder executor, not by this reviewer.

## Remaining acceptance gates / concrete next action

- Final accepted UI-integrated source/content/environment and final staged independent operational review still absent. UI loop is deployment owner per coordination record; no concurrent deployment.
- Current drill never runs init-onboarding or init-support, and its populated history set excludes onboarding requests/events and support responses. Extend final drill to migrate/populate/preserve those records, then exercise actual module endpoints across restart and compatible rollback. Both modules retain global schema6, so record module state separately from health.
- Installed-data comparison remains unverified: synthetic populated records establish bounded recovery behavior, not preservation of the installed learner corpus.
- Reviewer instructions still forbid process kill/restart and restrict HTTP to loopback. No forbidden action attempted; there is no DENIED command. Independent observation can strengthen executor evidence but cannot be relabeled reviewer-executed supervisor testing or final HTTPS verification. Manager/engine must provide the required capability for final review.
- Real spoken-video/material provider processing, enforceable spend boundary and provider failure recovery remain unverified. Mocked/fault-injected work cannot pass this gate.

No production changes, publication, shared migrations or credentials in evidence. Initial shell `python` was absent; rerun used the existing explicit application venv successfully. This is a tooling correction, not a product failure.

## Completed natural-expiry observation, 15:28 UTC

**R1 closed for the bounded isolated harness.** Independently sampled the same live read-only DB through expiry: at epoch **1791127678.9434905** the job transitioned to **failed / interrupted_outcome_unknown**, attempt stayed **1**, lease cleared. Original expiry was 1791127678. `lease-observations.json` preserves the two observed states. This is direct runtime evidence, not reasoning from tests.

Executor result now has **passed=true**, driver **exit_code=0**, final **clean_shutdown** at 15:28:01 UTC. Both acknowledged and unacknowledged retry return 409 without provider readiness, job unchanged, zero duplicate drafts. Evidence hashes saved in executor-evidence-hashes.json. The earlier detached-driver interruption is superseded by this completed run, not counted as success itself.

| Requirement | Status in this review |
|---|---|
| Fresh app, real profile/admin HTTP and browser | Pass locally on 775f69b |
| Additive fixture migrations including onboarding/support | Pass locally, 133 retained rows; module backup boundaries recorded |
| Killed claim natural 900-second expiry | Pass bounded executor drill; transition independently observed on 0aff086d |
| Child Gunicorn/queue restart, paired restore, compatible rollback | Executor run passed; code/results independently inspected, restart actions not independently driven |
| Full installed-data comparison and populated new-module operational recovery | Unverified |
| Final integrated staging health/supervisor/HTTPS smoke | Unverified; capability and handoff gates remain |
| Actual provider-backed recovery | Unverified; explicitly not simulated into acceptance |

Overall **needs_work** for remaining acceptance gates. Do not repeat the repaired R1 failure or discard this completed isolated-drill evidence; extend and reverify on the final candidate with all migrations and approved operational capability.
