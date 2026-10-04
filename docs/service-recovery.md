# Isolated service recovery drill

Run from the candidate source directory with its Python environment:

```sh
CLUB_EVIDENCE_DIR=/absolute/evidence/directory .venv/bin/python scripts/check_service_recovery.py
```

The script needs Flask, Gunicorn, pytest (synthetic fixture helpers), and a local labelled WebM fixture at CLUB_RECOVERY_MEDIA (default /home/claude/ai-room/instance/media/fixture.webm). It exports the exact committed candidate into a temporary directory so learner media never modifies the checkout. It uses an ephemeral loopback port and takes
about **15 minutes**. It starts only its own child processes. It never installs
systemd units, changes ingress, or reads staging accounts. Database, uploads,
credentials, process logs and rollback source live in a private temporary
directory that is removed on exit. Public evidence contains process IDs, build
identities, timestamps, a synthetic source hash and assertions; no credentials,
source text, database backups or provider values are copied out.

The fault-injection child alone replaces provider readiness with true and denies socket connection calls, then pauses processing immediately after the real persisted claim. No real provider credentials are supplied and production readiness is unchanged. SIGKILL interrupts that process. A fresh unmodified worker waits
for the original 900-second lease to expire, without rewriting timestamps. This
is fault injection before the provider call, not proof of an interrupted live
provider request or charge. Provider configuration is removed from child
environments. Both acknowledged and unacknowledged retry requests must consequently return 409 and preserve the failed job unchanged; no additional attempt is consumed.

The drill also checks:

- Actual Gunicorn and queue readiness, SIGTERM and fresh process startup.
- A quiescent SQLite/private-source/learner-media backup with matching hashes and authenticated reads.
- Repeat additive `init-db`, `init-skills` and `init-teaching` commands and integrity.
- A code rollback to `CLUB_ROLLBACK_COMMIT` (defaults to the candidate parent, resolved to an exact SHA)
  with later learner practice and completion changes retained in the current DB.
- Populated synthetic attempts, understanding evidence, practical submissions, decisions and application evidence retained exactly across migration, rollback and restore. These fixtures are not editorial approval.
- Paired DB/media restoration while both writers are stopped, surviving session
  cookies and authenticated source access after restart.
- Natural interrupted-job recovery, rejected unacknowledged retry, rejected
  acknowledged retry without provider readiness, no generated drafts and clean process shutdown.

The paired restore intentionally discards **disposable** post-snapshot changes
and checks the restored earlier state. It is a different recovery path from code
rollback. For installed state, prefer compatible code rollback with current data;
a snapshot restore requires reconciliation of subsequent learner/editor writes.

`events.json` is updated during the wait. `result.json` is emitted only after all
assertions pass. An events file alone is not a successful result. The script is
an operations verification tool, not a deployment command or an AI acceptance
run. Select and independently review the rollback pair for the intended release; a default parent passing these fixture checks is not deployment authorization. Shared systemd configuration, restart
policy and deployed service identity still require manager-scheduled checks.

For a bounded module-state check while awaiting the final integrated candidate:

```sh
CLUB_EVIDENCE_DIR=/absolute/new/evidence/directory CLUB_ROLLBACK_COMMIT=<compatible-sha> .venv/bin/python scripts/check_service_recovery.py --state-only
```

This mode starts and stops real web/queue children, but does not inject a claim,
kill a worker or wait for lease expiry. Its result explicitly records
`state_only=true` and `natural_lease_verified=false`; it cannot replace the full
lease drill. Use a fresh evidence directory for each run.

Both modes now initialize and repeat all five current migration commands:
`init-db`, `init-skills`, `init-teaching`, `init-onboarding`, `init-support`.
Evidence lists every installed table and its initial row count, including empty
tables; that inventory is not a claim that every table has populated coverage.
Exact private row comparisons cover assessment history, onboarding state,
requests, events, committed preference revisions/interests, original support
questions and the append-only support response history. Synthetic fixtures
include completed onboarding with an unfinished edit, a second learner's
unfinished flow, and two support response revisions. Later onboarding and support
writes must remain usable through the same session cookies on the compatible
rollback build, including idempotent onboarding replay. Paired restore must
recover the earlier API responses and all original audit/request rows exactly.
No fixture text, cookie or signing key appears in the public evidence.
