# Isolated service recovery drill

Run from the candidate source directory with its Python environment:

```sh
CLUB_EVIDENCE_DIR=/absolute/evidence/directory .venv/bin/python scripts/check_service_recovery.py
```

The script needs Flask and Gunicorn, uses an ephemeral loopback port, and takes
about **15 minutes**. It starts only its own child processes. It never installs
systemd units, changes ingress, or reads staging accounts. Database, uploads,
credentials, process logs and rollback source live in a private temporary
directory that is removed on exit. Public evidence contains process IDs, build
identities, timestamps, a synthetic source hash and assertions; no credentials,
source text, database backups or provider values are copied out.

The real queue worker is paused by a test-only hook immediately after its normal
persisted claim. SIGKILL interrupts that process. A fresh unmodified worker waits
for the original 900-second lease to expire, without rewriting timestamps. This
is fault injection before the provider call, not proof of an interrupted live
provider request or charge. Provider configuration is removed from child
environments. The acknowledged retry must consequently become honestly blocked.

The drill also checks:

- Actual Gunicorn and queue readiness, SIGTERM and fresh process startup.
- A quiescent paired SQLite/private-source backup with matching media hash.
- Repeat additive `init-db`, `init-skills` and `init-teaching` commands and integrity.
- A compatible code rollback to `1bd6b76cb3e265302f6fb922c5f6c64abd232a7c`
  with later learner practice and completion changes retained in the current DB.
- Paired DB/media restoration while both writers are stopped, surviving session
  cookies and authenticated source access after restart.
- Natural interrupted-job recovery, rejected unacknowledged retry, explicit
  acknowledged retry, no generated drafts and clean process shutdown.

The paired restore intentionally discards **disposable** post-snapshot changes
and checks the restored earlier state. It is a different recovery path from code
rollback. For installed state, prefer compatible code rollback with current data;
a snapshot restore requires reconciliation of subsequent learner/editor writes.

`events.json` is updated during the wait. `result.json` is emitted only after all
assertions pass. An events file alone is not a successful result. The script is
an operations verification tool, not a deployment command or an AI acceptance
run. The rollback pair is deliberately fixed: re-review compatibility before
using it for any later schema or release. Shared systemd configuration, restart
policy and deployed service identity still require manager-scheduled checks.
