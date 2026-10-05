# Independent reliability review 001 — needs_work

2026-10-04. Candidate `/home/claude/ai-room-engine-admin-work` at **b32d43fb94bdb523750d1b20cd702062815d93bc**, clean before/after. Base pending bc4ba3c1f2eed39e42f611836d6990acf7b0a62d. No repository files edited. Current product brief read in full; historical direction and operations boundaries inspected. This is early local review, not integrated staging acceptance.

## Evidence and boundaries

Executable reviewer harness: `review.py`; structured assertions and HTTP observations: `result.json`. Actual loopback application at http://127.0.0.1:18873, schema 6, Chromium at 1440×1000 and 390×844. `result.json` records active graph ID and SHA-256 over persisted graph rows. Fresh synthetic `seed`, `init-skills`, `init-teaching`, plus one synthetic TXT upload; no pending teaching/assessment content installed. Provider prerequisites deliberately removed from this disposable environment; no provider call, credentials or configuration values in evidence. Learner WebM copied from the existing labelled fixture, 810903 bytes served successfully.

Opened and visually inspected `profile-1440.png` and `admin-390.png`: saved synthetic practice and 1/37 lesson activity displayed, understanding/application remain unverified; admin displays retained source.txt and waiting-for-AI explanation with refresh action. This is a recovery-state observation, not final design or novice teacher acceptance. Browser JS errors: zero. Actual graph/me requests succeeded; authenticated lesson/practice/media, capabilities, populated jobs, individual job/source/file all returned 200 with content. Upload returned 201. Missing-provider retry returned expected 409 and preserved the entire job DTO. Two guessed admin paths (`/admin/teach`, `/admin/teaching`) returned 404 during route discovery; real UI is `/admin`, which loaded and fetched working APIs. These guessed paths are not product defects.

## Requirement-to-evidence matrix

| Requirement | Verdict | Evidence / limit |
|---|---|---|
| Fresh setup | Pass locally | init-db → seed → init-skills → init-teaching; real login, profile/admin, health, protected file and media responses |
| Repeat additive migrations | Pass for fixture | Two repeats preserve all 133 preexisting rows across 49 tables, FK/integrity checks pass, six skill/teaching backup files mode 0600 |
| Installed data preservation / upgrade | Unverified | No installed DB snapshot or earlier-schema populated upgrade supplied. Assessment, attempt, evidence, practical submission tables are empty in this fixture; no preservation credit inferred for empty tables |
| Paired DB / protected uploads / learner media restore | Pass offline fixture only | Quiescent SQLite backup plus both file trees; SHA-256 maps equal; restored DB has earlier practice/completion; original later-write DB retained. Restored handlers checked through Flask client, not restored supervisor/HTTP/media playback |
| Compatible code rollback with later writes | Partial | Separate naturally exiting process using old SHA 1bd6b76cb3e265302f6fb922c5f6c64abd232a7c reads current DB later practice and uncompletion; all rows retained. No old queue/supervisor/security compatibility signoff; this old code is not an approved deployment rollback target |
| Provider-unavailable persistence | Pass locally | Real upload and process-teaching-once produce blocked state, attempt 0; HTTP retry 409 changes nothing |
| Documented killed-claim drill | Fail prerequisite | R1 below; full script deliberately not run because it kills processes |
| Real app/queue supervisor restart and killed-claim natural lease recovery | Unverified — capability gap | Reviewer instructions prohibit service restart and process kill, including isolated child processes. No forbidden command attempted, so no DENIED text exists |
| Final staging operational smoke | Unverified | Allowed HTTP origins are localhost/127.0.0.1 only. No accepted UI/integrated candidate per current manager direction. Prior dae0217 staging identity is historical manager evidence, not independently reverified here |

Additional appropriate checks: `python -m pytest --rootdir=/home/claude/ai-room-engine-admin-work --confcutdir=/home/claude/ai-room-engine-admin-work tests/test_retained_state.py tests/test_materials.py tests/test_release_bindings.py -q` using existing application venv: **19 passed in 19.56s**. These supplement real HTTP/browser evidence, not substitute for restart acceptance.

## R1 — recovery verification script no longer reaches its persisted claim

`scripts/check_service_recovery.py:51` removes CLUB_AI_APPROVED, CLUB_AI_API_KEY and CLUB_AI_MODEL. Lines 141–145 only replace `process_claim` with a sleep; lines 147–149 require state running before SIGKILL. Current `club/teaching.py:58` claim logic calls processing_available; absent configuration sends queued jobs to blocked without lease/attempt. Independently observed via the real worker CLI and HTTP job endpoint: queued → blocked, attempt 0, provider_approved_configuration_required. Consequently the hook is never reached and wait_state cannot succeed. This is a concrete test/runbook regression, not a fault in the desirable missing-provider job behavior.

Repair the isolated fault-injection harness so only the test process can cross readiness into a real persisted claim while provider networking stays disabled; label the injection explicitly. Do not weaken production readiness or inject/borrow provider credentials. An authorized operator must then execute the real process/900-second natural-lease drill and supply exact-build evidence for independent review.

## Remaining operations boundaries

The historical service drill's snapshot covers uploads, not the learner `instance/media` tree; do not describe it as whole-platform paired media recovery. This review includes both trees but has not restored a supervised application against them. Complete the final drill with session-signing-key continuity, both media roots, installed synthetic learning/evidence rows and queue state. Snapshot restore intentionally removes later writes; only compatible code rollback preserves them, and no destructive database restore is authorized by this evidence.

Manager should resolve reviewer process-control/remote-HTTP capability gaps through the loop configuration or an authorized operational test executor, with independent observation on the final integrated SHA. No production or shared staging state was touched. No supervisor restart, process kill, shared migration, publication or real-provider acceptance claimed.
