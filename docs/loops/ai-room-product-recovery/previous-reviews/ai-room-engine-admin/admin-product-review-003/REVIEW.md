# Independent admin product review 003: needs_work

Reviewed app 775f69bf6d8a5dbe7e3a5f503d96e748b196b85a in /home/claude/ai-room-engine-admin-work, clean checkout. Actual Chromium 153.0.8010.12 at http://127.0.0.1:18873 with disposable /tmp/admin-review-003 SQLite/uploads. Desktop 1440×1000 and admin support mobile 390×844. Source and graph hashes are in manifest.json; actual HTTP responses and graph contents in result.json. Agent novice simulation, not human user research. No repository edits, staging/production mutations, credentials discovery, mock provider, service restart or process killing.

## Requirement-to-evidence matrix

| Task | Verdict | Observed evidence |
|---|---|---|
| Learner submits question | Pass locally | Real browser POST /help 302, rendered original question after redirect. |
| Admin locates, answers and handles question | Pass locally | Actual browser GET /api/support/tickets/1 and POST /api/support/tickets/1/handle 200; response and handled timestamp persist after reload. |
| Learner reads answer after reload | FAIL | /help 200 displays original question plus untranslated `handled`, but no answer. Own-ticket API 200 contains the saved response. |
| Support responsive presentation | Pass for tested state | Opened handled-desktop.png and handled-mobile.png; readable wrapping and usable buttons, no horizontal overflow at 390px. Save confirmation is below the captured mobile viewport; no assertion of visible confirmation without scrolling. |
| Real file upload and saved unavailable-provider state | Pass locally | Browser uploads labelled synthetic spoken MP4 plus TXT (both POST /api/teaching/uploads 201), package POST 200, one visible retained job after reload. Worker consumes zero attempts with provider unavailable. Opened upload-waiting.png. |
| Real provider processing, proposal corrections/remap/reject, preview/publish | Unverified/blocking | Provider deliberately absent in isolated run. No transcription/analysis call or generated draft; upload success does not establish AI acceptance. |
| Stale generated draft, retry after restored readiness, uncertain-charge recovery | Unverified | Not tested this turn. |
| Content replacement/rollback, taxonomy lifecycle, practical decisions | Unverified | Prior local evidence does not establish current integrated acceptance. |
| Final accepted tokens and staged independent reviews | Unverified/blocking | This is isolated backend candidate, not accepted UI integration or final staging. |

## Required integration correction: learner cannot see support response

Exact reproduction: member submits question at /help; editor opens workshop disclosure, writes response and clicks Save response and mark handled; editor receives success and reload retains response; member reloads /help and sees only `handled`. Opened learner-after.png to verify visually. `response_visible` is false in result.json while own-ticket API contains the response. Code agrees: club/templates/help.html prints body/status only, and has no response consumer.

This closes the old admin-side handling absence, but does not close end-to-end support. Canonical shared ownership revision 4 assigns help.html consumer to UI, support API to backend/admin. Manager should hand off this reproduction to UI under that existing allocation; do not redesign the learner page. Minimum acceptance: own original question/context plus escaped saved reply, localized handled status and response time appear after reload; other learners cannot read it. Recheck exact integrated SHA in Chromium and have security independently verify cross-user/role/CSRF protections. This is an integration blocker, not a claim that the admin engineer's explicitly scoped API contract was violated.

## Evidence and limits

All exercised workflow requests succeeded (2xx/redirects); no browser script errors. Actual direct API re-probes of support, teaching capabilities/jobs and nonempty graph succeeded. No missing endpoint masked by UI. Login landing graph/me calls also returned 200. Source assets are existing labelled synthetic teaching fixtures in ai-pipeline-003; hashes retained. All four screenshots were opened and inspected, not merely captured. Existing navy admin versus green learner shell remains pending accepted UI integration; no new aesthetic approval is implied.

Final staging health was not reverified: turn's permitted probes are localhost only. No capability denial encountered. Missing final staging/provider/assessment/security/recovery evidence must remain open; this bounded local correction review cannot replace those gates.
