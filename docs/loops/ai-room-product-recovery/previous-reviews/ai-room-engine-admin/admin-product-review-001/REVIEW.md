# Independent admin product review 001 — needs_work

2026-10-04. Agent novice simulation, not human user research. No application source edits, deployments, shared content mutations, service restarts or provider calls. Staging login/read-only inspection used the designated synthetic editor; temporary uploads and queue mutations used fresh isolated data. No mock provider.

## Exact targets and evidence

- Actual HTTPS staging https://airoom.nolimlabs.uk, health build `dae021716ac92abe5fdf1253093f82ac8f3f3286`, schema 6. Confirmed both via browser request and local staging-origin `/health` curl.
- Graph release returned by actual endpoint: `tree-specialists-v1-9064a25e953bf5408059`; score rule `verified-coverage-v1`. `/api/skills/forms` returned the three foundation forms; exact response retained in impact.json. No pending manifest installed or published.
- Isolated candidate `/home/claude/ai-room-pending-review`, clean HEAD `bc4ba3c1f2eed39e42f611836d6990acf7b0a62d`, fresh disposable SQLite/upload directories, real HTTP at http://127.0.0.1:18848. Source was an original, labelled synthetic Markdown teaching note; bytes/hash in script/manifest. It is not a spoken-video acceptance run.
- Headless Chromium 153.0.8010.12, desktop 1440×1000; staging intake additionally 390×844. Screenshots opened and visually inspected: admin, admin-mobile, admin-assessments, assessment-impact, admin-tree, admin-practice, admin-content, isolated-blocked. Additional upload/retry screenshots retained.
- `result.json` and `impact.json` preserve actual page text, endpoint responses and network statuses. `review2.py` and `impact.py` reproduce the successful checks; manifest.json pins artifacts. No credentials/cookies saved.

## Requirement-to-evidence matrix

| Task | Verdict | Observed evidence / remaining gate |
|---|---|---|
| Upload-first intake | Partial pass | Actual staged intake at desktop/mobile shows upload action, supported formats/limits and provider-unavailable disclosure. Fresh candidate browser upload returned 201; package returned 200; job survived page reload. |
| Processing and real generated lesson | Blocked | Staged capabilities returns `processing_available:false`, dependency names `CLUB_AI_APPROVED,CLUB_AI_API_KEY,CLUB_AI_MODEL`. Fresh candidate real worker returns `provider_approved_configuration_required`; no draft generated. These names are a combined dependency report, not proof that each individual variable is absent. |
| Recoverable failure/retry | Fail usability | Blocked job retains source and clear explanation; Retry accepts and queues while dependency is unchanged, then another actual worker run blocks it again. UI also shows possible duplicate-charge checkbox when no request reached provider; retry succeeds unchecked in this case. |
| Edit/remap/reject AI proposal | Unverified | No actual generated draft available; code inspection and historic mock walkthrough do not establish this gate. |
| Learner preview/publish | Unverified | No actual provider-backed draft; no publication attempted. |
| Published assessment inventory/impact disclosure | Partial pass | Actual three forms render from 200 `/api/skills/forms`. Clicking context form shows withdrawal consequences, public reason, no compatible replacement and confirmation. No withdrawal submitted. |
| Quantified impact and rollback | Unverified / gap | Observed impact screen supplies generic consequences only, no current attempt/learner/practice counts or detailed inspection link. It labels withdrawal irreversible. Content rollback and assessment replacement need separate demonstrated flows; do not equate withdrawal with rollback. |
| Taxonomy proposal queue | Empty-state pass only | `/admin/tree` and graph/proposals endpoints return 200; proposals empty, graph real/nonempty. Creation/review/activation/rollback not tested on shared staging. |
| Practical review queue | Empty-state pass only | `/admin/practice` and `/api/skills/practical-review` return 200 with no submissions. Cannot accept actual decision task from empty state. |
| Manual content queue | Load pass only | `/admin/content/` server renders real course list with published/draft/archive states, status 200. Editing/preview/archive not exercised here. |
| Support and learner evidence | Unverified | Support is folded under manual-content/support disclosure; no real support handling journey undertaken. |
| Accepted visual tokens | Blocked | Coordination says accepted UI handoff absent. Observed manual course queue uses green/lime surfaces while teacher/assessment/tree screens use navy/cream; current inconsistency is concrete, final token choice belongs to UI handoff. |
| Final integrated staging acceptance | Unverified | No accepted UI handoff/integrated candidate, no real spoken-video/material processing, no final-stage editorial journey. |

All loaded staged pages returned 200: `/admin`, `/admin/assessments`, `/admin/tree`, `/admin/practice`, `/admin/content/`. Independently requested the actual GET endpoints: teaching capabilities/jobs; skills graph/forms/graph-proposals/practical-review/practical-tasks, all 200 JSON. Empty arrays were real backend states, not missing routes; they do not prove populated workflows. No observed browser script errors. Manual content is server-rendered and does not fetch a page-specific API. Mutating endpoints only tested in the disposable candidate: real upload/package/retry success and actual worker dependency failure.

## Concrete implementation requests

1. **P1 recovery — avoid retry without a changed prerequisite.** When provider unavailable, retain uploaded source and show “Saved; waiting for AI connection” with an operator/support path and a readiness refresh. Do not offer a processing retry that can only fail identically. Show duplicate-charge acknowledgement only for an uncertain prior request. Recheck: unavailable → saved/blocked persists across reload; readiness restored → one explicit retry; no duplicate upload/job; uncertain request retains explicit charge acknowledgement.
2. **P1 impact — make consequences inspectable.** Before withdrawal/replacement/content rollback, show backend-derived affected in-progress attempts, retained results and linked practice/content, with stable names and counts. Distinguish zero from unavailable. Keep the current plain-language preservation explanation. Recheck using populated disposable data and compare displayed counts with backend state; ensure later learner writes survive a compatible rollback.
3. **P1 visual integration dependency.** Once UI loop supplies accepted tokens, apply them to admin-only surfaces including manual content forms. Do not change learner styles. Current green manual queue versus navy teacher workspace is visibly inconsistent; recheck desktop/mobile with actual long titles and error states.
4. **P2 novice terminology.** Published assessment buttons expose long implementation IDs as primary text. Keep human titles and question counts primary; move stable IDs/version detail into inspectable secondary metadata.

## Task specification for next independent acceptance

1. Start in Workshop. Upload an approved spoken video plus notes via Chromium. Show saved filenames/limits and one processing status; closing/reopening resumes the same job. Invalid format/size errors identify the file and preserve other successful uploads.
2. Real provider transcription/analysis creates a source-grounded draft. Review summary presents lesson title, outcomes, assessment coverage and uncertain proposals. Sources open at exact paragraph/timestamp; questions expose answer/explanation only to reviewer. Provider/model/source hashes and bounded cost/attempt provenance are inspectable.
3. Correct title/text/source, remap one outcome to an existing skill, reject one outcome and one question. Explain exactly which assessments were removed and resulting unassessed coverage; preserve decisions after refresh. Shared taxonomy proposals remain a separate review queue.
4. Simulate connection loss and two-editor stale revision against real endpoints. Keep unsaved input, explain conflict and offer safe reopen/reapply; no silent overwrite or repeated publication.
5. Preview as learner with real protected video/material access and no answer keys. Publish only after explicit review and access choice; repeated/lost-response publish resolves to the same stable lesson. Confirm learner visibility and retained existing records.
6. Return via processing/draft/published queues. Exercise failure/cancel/retry and lifecycle impact, withdrawal/replacement/archive and compatible rollback with populated data; explain preserved histories and changed future eligibility.
7. Submit a learner help request and practical revision, then locate and resolve/review from admin with privacy-safe evidence. Verify metric denominators independently.

Repeat on final exact integrated staging SHA/content manifest after fixes and approved real provider availability. Screenshots must be opened, not just written. Independent assessment and security/recovery decisions remain separate requirements.

## Harness limitations

The initial harness incorrectly expected a duplicate-charge checkbox after a successful no-charge retry; the control correctly disappeared when queued. Corrected harness records the queued state and executes the second worker instead. A separate accidental rerun reused a seeded disposable DB with a new password and failed login; that is harness setup, not a product failure. Successful final run uses a fresh DB/port and is recorded in result.json. No capability denial occurred. Provider-backed correction/preview/publication remains unverified, not failed by assertion.
