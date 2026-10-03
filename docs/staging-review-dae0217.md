# Skill-tree staging review deployment

On 2026-10-03 the manager-authorized review candidate
`dae021716ac92abe5fdf1253093f82ac8f3f3286` was deployed to
https://airoom.nolimlabs.uk/. This is not final release acceptance.

The immutable tracked-source archive is extracted at
`/home/claude/ai-room-releases/dae0217`. The existing user unit
`ai-room.service` retains listener `127.0.0.1:8098`. Its private drop-in selects
that release and `/home/claude/ai-room-staging-private/state-dae0217/staging.env`.
The new `ai-room-teaching.service` uses the same release, environment and state,
with the repository's sequential queue, restart policy and graceful stop timeout.
Both use the existing `/home/claude/ai-room/.venv` runtime. Prototype routing and
all ingress configuration are unchanged. Baseline source and its original state
remain at `/home/claude/ai-room`; that database is no longer the active database.

Before switching, the web writer was stopped and its zero PID verified. The
private paired database/media/configuration checkpoint is
`/home/claude/ai-room-staging-private/pre-dae0217`. The release's `instance` link
points to the separate retained, migrated state directory. Never seed this state.
The exact migration/content installation was exercised on an isolated database
copy first, then repeated against the quiescent copied state. Every original row
and media checksum was checked before opening the new services to requests.

Installed graph lineage: `tree-2026-10-v1` → `tree-2026-10-examples-v2` →
`tree-foundations-v1-ff1a38a487c7e61e261b` →
`tree-specialists-v1-9064a25e953bf5408059`. All 26 abilities have teaching material.
No forms or evidence were created/published. The 41-unmapped-baseline-lessons
curriculum issue remains separate. Provider configuration is unavailable;
capabilities honestly name the required variables without their values.

Verification includes 130 passing tests; actual HTTPS logins for synthetic
free/member/revoked/editor accounts; anonymous and authenticated paid-content
boundaries; secure cookies; protected range media and Chromium playback;
preserved prototypes; mobile/desktop map screenshots; and actual serial restarts
of both shared user services with retained progress/practice. Curl and Chromium
reach the exact build over HTTPS. Default Python urllib receives Cloudflare 403;
no ingress change was made to bypass that client-dependent boundary.

`scripts/verify_retained_state.py` compares an immutable pre-migration snapshot
against a quiescent migrated copy, including duplicate rows, SQLite integrity,
foreign keys and media hashes. It deliberately rejects changed rows. Do not use
it to claim an untouched database after opening service to learners: video smoke
and real learning legitimately update resume timestamps and progress fields.

## Compatible rollback

Prepared `/home/claude/ai-room-releases/39302f2` contains the previously verified
compatible code and an instance link to the **current** active state. Its `club/`
and runtime requirements are identical to dae0217; only operational scripts/docs
differ. The earlier isolated real-process recovery evidence covers this compatible
rollback retaining later writes. A baseline application check also opened an
isolated post-deployment database successfully without changing progress/practice;
that older baseline is not the recommended skill-tree rollback target.

To roll back code, stop queue then web; retain the current database/media/session
key; update both units' working directory to the prepared compatible release and
the private environment's build identifier to the full rollback SHA; reload
systemd and start web then queue. Verify `/health`, login, media and saved work.
No live rollback was needed or performed during this deployment. Never restore
the pre-deployment snapshot over later writes. Data recovery requires a new
quiescent paired checkpoint or explicit reconciliation of every later write.

Independent staged functional, visual, learning and product signoffs, approved
real-provider processing, novice-teacher acceptance and pending curriculum/
assessment review remain open. Screenshots and sanitized deployment evidence:
`/home/claude/bot-swarm/data/_loops/_output/education-platform-for-people-learning/deliverables/worker-staging-dae0217/`.
