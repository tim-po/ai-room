# Onboarding v1 backend contract

Base: b32d43fb94bdb523750d1b20cd702062815d93bc. Ownership: agreed shared onboarding-v1-proposal.json; backend owns club/onboarding.py, tests, and only registration/login/entry hooks in club/__init__.py. UI owns onboarding.html and its JS/CSS. No shared runtime migration or deployment performed.

Run `flask --app club init-onboarding` after `init-skills`, with the application and queue quiescent. This creates a private timestamped paired database, learner-media and teaching-upload backup before additive storage/backfill. Local session.key is copied when present; environment-provided CLUB_SECRET_KEY must remain unchanged through restore. Existing schema user_version stays 6, and IDs, rows, assessment history, evidence and weekly goals remain unchanged. Repeating the command retains state. New accounts initialize compatibility state on first use. Before migration the application keeps existing routing, and the new API returns 503. After migration fresh learner HTML entry redirects to /onboarding; integrate the peer's template before releasing, otherwise that screen returns an explicit 503.

GET /api/onboarding returns the state below. PUT requires X-CSRF-Token, authentication and learner role. No request may specify user_id or return_to. Draft fields are partial and allowlisted. All actions require a nonnegative integer expected_revision and per-user idempotency_key matching `[A-Za-z0-9_.:-]{8,128}`. Keys persist across restart.

```json
{"action":"next","expected_revision":0,"idempotency_key":"onboard-device-a-0001","step":"interests","draft":{"interests":["coding","content"]}}
```

Example acknowledged response (timestamps/title depend on installed data):

```json
{
  "flow_version":1,
  "status":"in_progress",
  "step":"interests",
  "draft":{"interests":["coding","content"],"experience":"beginner","available_minutes":null,"diagnostic_choice":"unset"},
  "committed_preferences":{"interests":[],"experience":"beginner","available_minutes":null,"diagnostic_choice":"unset"},
  "revision":1,
  "return_to":"/",
  "updated_at":"2026-10-04T15:00:00+00:00",
  "editing":false,
  "recommendation":{"lesson_id":"foundations-start-01","title":"Installed lesson title","url":"/lessons/foundations-start-01","reason":"available_learning"},
  "diagnostic":{"available":false,"start_url":null},
  "next_url":null
}
```

Step order is welcome → interests → pace → start. `next` and `back` advance exactly one step; if `step` is supplied it must match the resulting step. `save` preserves step. `complete` requires start unless explicitly editing completed/skipped preferences. It atomically commits interests, optional experience, separate available_minutes and diagnostic_choice. It does not change goal, weekly_goal, progress, attempts, evidence or practical work. Experience is null/beginner/experienced; minutes null/5/10/20; diagnostic_choice unset/skip/start. Interests are zero or more active graph node IDs, deduplicated and sorted.

`skip` keeps committed preferences and retains the draft. `edit` is allowed only after completed/skipped, seeds current committed interests/experience, and keeps terminal status plus editing=true. `cancel` exits editing and resets draft to committed preferences. Complete/skip/cancel return next_url; navigation is the client’s responsibility. A saved diagnostic_choice=start does not launch a diagnostic automatically: after acknowledgement the UI can use the existing diagnostic API and documented UI flow. Diagnostic availability excludes withdrawn, inaccessible and edition-incompatible forms. The recommendation is an actual currently permitted lesson, explicitly a basic available-learning fallback, not an inferred competence or interest ranking; null when none exists.

Same-key/same-payload replay returns acknowledged state before testing revision; different payload or stale new key returns 409 with `{error: "idempotency_conflict"|"revision_conflict"|"transition_conflict", state: ...}`. Replay never repeats preference writes or telemetry. Historical acknowledged revision may be older than current state; GET reloads current state. Return URLs, recommendation and diagnostic availability are recomputed even on replay to enforce current access. Invalid input/CSRF returns existing app 400 format; unauthenticated 401; nonlearner 403. Ordinary learner APIs, assets, logout, admin and login are not intercepted.

Return paths are captured only from authenticated login/entry, restricted to known static learner destinations and published entitled lesson pages. No query strings, external redirects, encoded slashes, arbitrary paths or paid lesson targets after revocation. An unsafe/unavailable target becomes `/`. A later ordinary root login preserves a previously captured valid lesson destination. Saved destination changes increment revision to make competing tabs conflict. Existing onboarding_done=1 learners are backfilled completed with no invented telemetry; legacy preference complete/skip remains recognized during rollout.

`onboarding_events_v1` contains only user_id, revision, action, step, timestamp. It does not contain drafts, answers, email, interest IDs or source text. Passive GET and identical saves produce no events, and replay produces none. It is an action ledger, not a claim that a step was visibly exposed or meaningful learning occurred. Existing event names and meaningful_return semantics remain unchanged. Versioned cohort analytics remain a separate pending implementation.

Rollback to compatible previous application code can retain these additive tables and all later writes; do not overwrite a live database with the pre-migration backup merely to remove this feature. Disaster restore requires quiescence and the matching DB/media/upload set plus unchanged signing key. Independent process restart/restore and integrated browser acceptance remain required.

## Cross-route committed preference revision (O1)

Run `flask --app club init-onboarding` with writers quiesced before running
this version, including upgrades from the earlier onboarding module. The command
makes its existing private paired backup and installs the additive
`committed_preference_revisions` table and four SQLite triggers. Re-running it
preserves states, request history, learning records and revision counters.
Include this table and triggers in database recovery inventory.

All SQL interest mutations and updates naming users.experience/onboarding_done
advance a per-user counter in the writer's transaction, including legacy routes.
Same-value UPDATEs and delete/reinsert interest saves invalidate open edits;
an empty-to-empty interests request performs no mutation and leaves the counter
unchanged. The counter is monotonic but is not a count of user actions.
`committed_revision` is additive in the DTO. Existing `expected_revision` remains
the concurrency input; revision values can jump. Clients must use returned values.
GET and 409 state expose current committed interests/experience while keeping
saved onboarding draft values separate. PUT checks a fresh user snapshot under
BEGIN IMMEDIATE. Cancel discards draft in favor of current committed preferences.
Matching idempotent retries return current state without executing any mutation;
this intentionally supersedes replay of the historical response snapshot. The
stored historical request response remains intact for recovery/audit purposes.
No event or evidence credit is added by the database revision triggers.
