# Durable teaching worker

`flask --app club process-teaching-worker --poll-seconds 5` waits for queued jobs and processes them sequentially. `--max-jobs N` exits after N claims (including failed/blocked jobs); 0 means continuous operation. It waits if there is no work. `process-teaching-once` remains available for a bounded one-shot invocation that exits on an empty queue. The continuous worker closes its database connection after each job/poll. It does not publish, migrate, approve, or retry failed jobs automatically.

SIGTERM/SIGINT stop idle waits immediately and let the current job finish before exit. A supervisor's forced kill can interrupt the provider request: the persisted 900-second lease then expires, and the next queue scan records `interrupted_outcome_unknown`. The teacher must acknowledge possible duplicate charge to retry. Do not clear leases manually. Transcriptions already committed remain available to a later retry. Cancellation prevents a stale worker from storing a transcript/draft or publishing anything; an in-flight provider call can still charge. Transcript persistence now obtains the database write lock before checking the lease.

Jobs remain queued across process restart. A missing provider configuration produces `blocked / provider_approved_configuration_required`, not invented draft output. No continuous automatic retries occur; the existing explicit three-attempt cap applies, including blocked attempts. Set configuration before processing to avoid consuming those attempts. Missing/unreadable source media records `blocked / source_storage_unavailable` and processing continues with the next job; restore the protected file from backup before an explicit retry. Unexpected programming/operational failures terminate the worker for supervisor inspection; never blindly loop restarts to conceal them.

## Setup and ownership

Manager/worker owns installation and staging deployment. `scripts/ai-room-teaching.service.example` is a non-installed systemd user service template. Replace `REVIEWED_RELEASE` and `PRIVATE_STATE` with the intended absolute paths and inspect the rendered unit. Use the same operating-system account, private upload directory and database as the web service. Install one queue service; SQLite claims also fence an accidental second instance, but multiple workers increase simultaneous provider costs. No schema change accompanies this increment.

Private environment-file variable names:

- `CLUB_DATABASE`: absolute existing database path.
- `CLUB_UPLOAD_DIR`: absolute existing protected upload path, outside static assets.
- `CLUB_SECRET_KEY`: shared web secret (or existing private session-key arrangement).
- `CLUB_AI_APPROVED`, `CLUB_AI_API_KEY`, `CLUB_AI_MODEL`: approved provider configuration only; `CLUB_AI_APPROVED` must equal `1`.

Set the file to mode 0600; never copy values into reports or command lines. Other credentials, including CLI login credentials, are not authorized substitutes. Retain provider account spend controls. The adapter has a 6,000-token output cap, 80 KB source-context cap, five-file package cap, 90-second per-request timeout and no automatic HTTP retry. This is a bounded per-job limit, not a daily monetary budget. The template allows 960 seconds for graceful shutdown; forced termination is handled through the persisted lease. Configure operator log collection; stdout contains fixed outcomes and counts, no source content, keys or user data.

## Backup, migration, restart and rollback

1. Stop the queue service gracefully. Stop the web service before a consistent backup so no uploads/publications change during the snapshot. Check that the services have actually stopped; a pending SIGTERM is not completion.
2. With restrictive umask, use SQLite's backup API to create a database snapshot and copy the complete private upload directory to the same labelled backup set. Include the session secret separately in the private operational backup. Do not publish these files as evidence. Record candidate commit and backup paths privately. If forced shutdown left running jobs, preserve them as-is: lease recovery is intentional.
3. On the intended DB, run documented baseline setup only for a new empty installation. For an existing installation run `flask --app club init-skills` followed by `flask --app club init-teaching`. These additive commands create their own DB backups, but do not replace the coordinated media snapshot. Do not reseed or replace stable IDs/progress. This worker increment itself requires no new migration.
4. Start the reviewed web release and queue service against the same state. Check service identity, health, protected job status and sanitized worker logs. Test controlled queue/restart/cancel/retry before release acceptance. Publication remains an explicit authenticated teacher action and is idempotent at the reviewed revision.
5. To roll back code, stop both services and return both to the recorded previous compatible release; retain additive tables and earned records. If restoring data is necessary, restore DB and uploads from the same snapshot while stopped, then restart. A snapshot restore loses all changes after that snapshot; do not restore only one half or silently discard subsequent learner activity.

Do not install/start this template on shared staging until manager schedules deployment. Prototype and production services remain untouched.

## Verification boundary

`tests/test_teaching_worker.py` exercises fresh CLI processes with provider variables removed, idle SIGTERM, an abruptly killed persisted claim, explicit acknowledged retry, in-flight graceful-stop behavior, private-source failure isolation, closed DB connections and one draft per job. Ready-state tests deliberately use a mock provider and are not AI acceptance. Existing pipeline tests cover cancelled stale workers, cached transcription reuse, owner isolation, immutable draft editions and idempotent publication.

Still required: approved synthetic spoken video plus notes processed by the real provider; retain model/source/transcript provenance, editorial corrections and learner publication evidence for independent semantic review. This increment does not establish provider-backed, supervisor-installed or staged acceptance.
