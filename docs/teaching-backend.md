# Private teacher sources and durable jobs

This increment implements upload/storage and job lifecycle, **not AI generation**.
`process-teaching-once` honestly blocks work with
`provider_adapter_and_approved_configuration_required`. Do not treat this command,
source paragraphs, or unit tests as a provider-backed acceptance run. No lesson,
assessment or graph mutation is published by uploading.

## Setup and boundaries

After baseline init/seed, run `flask --app club init-teaching` against a disposable
local database. It uses SQLite backup before additive tables and preserves schema
version 6 and existing content/progress. Repeated migration is safe. Backups are
mode 0600. No staging or shared database migration has been performed here.

`CLUB_UPLOAD_DIR` optionally selects a private directory. Default: teaching-uploads
beside the database. Never expose that directory through a web server alias.
Application refuses storage inside its static directory. Files have generated IDs
and mode 0600; untrusted names never become paths. Back up database AND private
uploads together while processing/uploads are stopped; a database rollback alone
cannot recover deleted file bytes. Current lifecycle retains files on cancellation.
Storage cleanup/retention tooling remains pending; operator backup retention is
required. A killed process can leave an unreferenced private file, but never a
public file or a duplicate job; reconcile orphans offline against upload IDs.

Supported: UTF-8 TXT/MD (200 KiB), WAV/MP4/WebM (25 MiB). One file per request.
Media validation checks a container signature only: actual decoding, duration,
audio extraction and transcription remain pending. No PDF, Office, archives or
remote URL fetching yet. HTML and source instructions remain inert source text;
frontends must render source strings as text, never HTML. Source hash and numbered
paragraphs are persisted. Media source metadata explicitly has no transcript.

25 MiB upload ceiling is scoped to the upload endpoint. Existing endpoints retain
64 KiB request limits. Multipart overhead allowance is 64 KiB. Default cumulative
storage per uploader is 250 MiB, enforced transactionally. Overrides in app config:
TEACHING_UPLOAD_LIMIT and TEACHING_OWNER_QUOTA. There is no automatic paid call.

## HTTP contract

Session role editor/admin and X-CSRF-Token are required for mutations. Editors
read/change only their own jobs; admins can inspect/change any known job ID. List
returns only the current author's newest 100. Learners get 403, unauthenticated
clients 401, other authors' known IDs 404. Missing/stale CSRF gives 400.

- GET `/api/teaching/capabilities`: supported extensions/limits and explicit
  processing dependency. Use it to explain available formats and blocked AI.
- POST `/api/teaching/uploads`: multipart field `file`; header `Idempotency-Key`
  containing 8–100 ASCII letters/digits/underscore/hyphen. Returns job DTO (201);
  identical bytes/key replay returns same DTO (200); changed bytes/key gives 409.
- GET `/api/teaching/jobs`: `{jobs:[DTO]}` for retained work.
- GET `/api/teaching/jobs/<id>`: DTO contains id, upload_id, filename, media_type,
  size, sha256, state, attempt, revision, error_code, created_at, updated_at.
- GET `/api/teaching/jobs/<id>/source`: document paragraphs and hash, or media
  signature-validation metadata with transcript=null. No generated content.
- GET `/api/teaching/jobs/<id>/file`: protected attachment, octet-stream, no-store,
  nosniff. Never embed as trusted inline HTML.
- POST `/api/teaching/jobs/<id>/cancel` or `/retry`: JSON `{revision: integer}`.
  Stale revisions return 409; source survives. Retry is allowed from blocked,
  failed or cancelled state, at most three processing claims per job. Interrupted or cancelled in-flight
  work requires `acknowledge_possible_charge:true` because its provider outcome
  may be unknown. Ready jobs cannot be cancelled through this endpoint.

States: queued → running → blocked/failed/ready; cancel invalidates a queued or
running lease. Current runner only produces blocked; ready is reserved for the
future adapter and must mean persisted source-grounded draft, not publication.
All transitions have durable event records. State writes use immediate SQLite
transactions, fenced random lease tokens, five-minute expiry and revision CAS.
`claim_job` marks expired running jobs failed before claiming more queued work.
It never silently resubmits expired work. A stale or cancelled worker cannot
finish a job. Leases have no heartbeat yet: future provider calls must be bounded
below five minutes or the adapter must add tested renewal. Cancellation fences
local writes; it cannot reverse an already-sent provider request or its cost.

## Next integration work

A configured production-capable provider adapter and approved generation and
transcription models are still required. Persist provider/model, stage receipts,
transcript spans and grounded proposals before adding reviewed draft publication.
Avoid blindly repeating completed stages or charging on browser polling. Add
semantic source review, revision-checked editing, explicit publication and
separate graph approval/rollback. Keep provider keys and answer keys server-side.
The frontend may now upload, resume, inspect source, cancel and retry real retained
work, but must label AI review/publication as unavailable until connected.
