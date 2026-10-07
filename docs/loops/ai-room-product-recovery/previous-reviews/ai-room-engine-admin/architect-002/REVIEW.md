# Architecture review 002 — needs_work

Exact candidate: **775f69bf6d8a5dbe7e3a5f503d96e748b196b85a**, clean `/home/claude/ai-room-engine-admin-work`, baseline bc4ba3c. Reviewed actual code/diffs, current-direction and bilateral ownership revision 4; main brief read in full. No application edits, shared data mutations, deployment, restarts or process kills. Staging identity dae0217 is inherited coordination evidence, not a fresh remote probe: this role is limited to loopback HTTP. UI manager remains sole staging owner; no accepted UI handoff exists in current-direction.

## Actual evidence

- Chromium 153.0.8010.12, 1440x1000, http://127.0.0.1:18874, disposable synthetic SQLite/media under `/tmp/architect002-amyyc20a`. Health independently fetched with curl; schema 6. Graph and exact retained source hash are in result.json. The transfer-shaped publication is solely an isolated delivery fixture, not independent semantic approval or shared publication.
- Real browser login, onboarding API next/replay/stale/complete, legacy interests write, concurrent onboarding edit, challenge create/resume/browser load/current-content denial, admin measurement HTML and actual populated aggregate API. Requests and bodies retained in result.json. Opened and inspected onboarding.png, challenge.png and measurement.png from the identical first successful run at the same SHA; retained screenshots reproduce the same states on final concurrency run.
- Independent targeted run: `/home/claude/ai-room/.venv/bin/python -m pytest --rootdir=/home/claude/ai-room-engine-admin-work --confcutdir=/home/claude/ai-room-engine-admin-work tests/test_onboarding.py tests/test_challenge_presentation.py tests/test_current_content_access.py tests/test_support_admin.py -q -p no:cacheprovider`: **24 passed in 39.23 seconds**. Includes populated migration preservation, paired fixture backup, same-route competing revisions, all seven exact-case DTOs, choice stability across recreated apps, historical order, grading/dedup, current access and support isolation. These tests do not catch the cross-route lost update below and do not substitute for final browser/staging acceptance.

## O1 — blocking compatibility defect: cross-route preference lost update

Actual HTTP on the named candidate:
1. Complete onboarding with coding/content; response commits both at revision 4.
2. PUT `/api/skills/interests` with `{node_ids:["agents"]}` returns 200 and GET skills/me returns agents. GET `/api/onboarding` still calls coding/content the committed interests at revision 4.
3. PUT onboarding `edit` revision 4 returns revision 5 and seeds agents.
4. A later PUT skills/interests with automation returns 200.
5. PUT onboarding `complete` expected_revision 5 returns **200**, revision 6, and GET skills/me returns **agents**. The newer acknowledged automation selection is silently lost.

Source: onboarding.py state() only reconciles legacy onboarding_done while in nonterminal status; edit refreshes a snapshot, complete replaces skill_interests. skills.py interests() replaces the same rows without advancing/checking the onboarding preference revision. Legacy preferences experience writes similarly bypass that concurrency boundary; that related case is code inspection, not separately reproduced.

Minimal fix owned by backend: one shared committed-preference revision across all writers of interests/experience. Legacy writes must invalidate an open onboarding edit; stale complete must return 409 with current committed values while retaining the user's draft. GET committed_preferences must reflect canonical committed state without promoting draft. Preserve payload compatibility and stable IDs. Backend needs the explicit small interests()/legacy-preferences hunk ownership transfer because current skills.py transfer covers attempt DTO/start only. Regression: exact five-step HTTP reproduction, two sessions, and legacy experience edit during onboarding. Do not fix by removing the still-supported interests endpoint or silently replacing new values.

## Integration failures, not new backend source defects

- Fresh login redirects to `/onboarding`, which returns **503** and a raw English Service Unavailable page: UI-owned onboarding.html is absent. Browser/API onboarding acceptance remains blocked; do not migrate/enable this candidate on staging before integrated page review.
- `/challenges?attempt=...` loads and its API returns 200 with the exact source case plus shuffled choices. Browser shows questions/options but **no case text**. Screenshot visibly asks about groups whose data are missing. Existing challenge.js does not consume item.case. Backend source transport passes locally; S1 remains open until the UI consumer and independent semantic review pass on the integrated build. No equivalence approval is inferred.

## Limited passes and recovery audit

- Onboarding replay returns the acknowledged state; new stale key gets 409; missing CSRF gets 400; six actual mutation events/requests after the extended review, zero progress/evidence/results. No fabricated mastery.
- Challenge create 201, resume 200 with identical ordering and exact source hash; changing bound lesson free→member produces 403 before source disclosure. Historical compatibility covered by independent targeted tests, not this single synthetic browser form.
- Existing admin aggregate endpoint returned real counts including the created certification attempt. It remains skill-measurement-v1 with current-outcome windows, not the research exposure/D1/D7 contract. No new telemetry contract implemented yet; see MEASUREMENT-CONTRACT.md.
- Inspected recovery script readiness injection: only a disposable child patches processing_available and process_claim, denies socket connect, then pauses before any provider call. Normal web/queue still enforce production readiness. This is an appropriate isolated pre-provider crash test boundary; it cannot evidence provider timeout, actual costs or ambiguous charged retry behavior.
- Recovery artifacts at inspection recorded real claim, stopped writers, paired snapshot of both media roots, populated migration, compatible code rollback preserving later writes, signing-key continuity and paired restore. Natural-lease full result was still pending at 15:27:04 UTC (53 seconds remaining); no pass inferred from intermediate events. Candidate there is 0aff086, rollback 6dfdc99, neither is final integrated 775f69b + accepted UI. Independent operational reviewer still required. Any later final result must be read separately.

## Remaining acceptance

O1 lost update fails. Onboarding HTML and challenge case presentation fail on this candidate. Versioned measurement, real approved spoken-video/material provider run, provider spend ceiling, final same-build independent assessment/admin/security/recovery and accepted learner UI integration are unverified. Support tests pass locally but support browser acceptance belongs to the admin reviewer and learner reply consumer integration remains separate. No repository change or publication authorized by this review.

## End-of-turn recovery update

After completing the review, inspected `ai-pipeline-004/result.json` and `driver-result.json`: **passed=true**, **exit_code=0**, clean_shutdown at 15:28:01 UTC, natural 900-second lease recovery, both acknowledged and unacknowledged retries correctly 409 without provider readiness, zero duplicate drafts. This supersedes the pending status above for the isolated 0aff086 drill only. Builder-operated artifact review supports the corrected harness; it is not final independent staging operation acceptance. Provider acceptance explicitly remains false. No live paid/in-flight provider failure tested.

Local health reports build=`development`, schema=6; exact review SHA comes from git, not an injected deployment build label. Graph `tree-2026-10-v1`; tested source SHA-256 `f46f852a4a97276d59199690028bf6a7f78eb820315a4394f9cbd49eba0103d1`. Final retained challenge screenshot was also opened and inspected after copying. Repository remained clean at close.
