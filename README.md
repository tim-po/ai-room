# AI Room Club — fresh learning platform

Independent Russian-first application in the previously empty `tim-po/ai-room` repository. Flask + Jinja server-rendered pages, SQLite, native HTML media, small progressive JavaScript. The existing website, its data, APIs, accounts and billing are not used. Orbit charcoal/green/lime and Campus warmth/rounded spacing inform one shared responsive shell.

## Implemented learning and authoring slices

Course discovery and combined search/goal/level filters; 4 synthetic courses including 37 lessons in 9 modules; readable text and an original generated silent video fixture; server-protected lesson text/media/downloads; explicit completion/uncompletion; drafts and saved practice results; server-persisted video position; favourites; preference editing and optional weekly goal; profile; contextual help tickets and role-protected administrator inbox. Anonymous free lessons work. Separate seeded free/member/revoked/editor/admin accounts use hashed passwords. Cookies are signed, HTTP-only, SameSite Lax; mutations require CSRF. No credentials ship in static assets.

This is a first slice, **not an accepted complete release**. Protected course/module/lesson authoring, draft preview, publish/unpublish/archive, ordering, local media selection and additional protected TXT/link resources are now implemented. Standalone materials, route composition, full measurement definitions/summary and registration/recovery are not implemented. Content is explicitly synthetic. Independent usability/product/functional reviews and HTTPS deployment remain required.

## Setup

Python 3.12+; `uv` or a working Python venv/pip installation.

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m flask --app club init-db
# Set CLUB_SEED_PASSWORD privately before seeding (12+ characters).
.venv/bin/python -m flask --app club seed
# Media generator tooling is needed only once, not at runtime.
uv pip install --python .venv/bin/python imageio-ffmpeg==0.6.0
.venv/bin/python scripts/make_media.py
.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8098 'club:create_app()'
```

Open `http://127.0.0.1:8098`. Health: `/health`. Run verification with `.venv/bin/python -m pytest -q` and `.venv/bin/python -m compileall -q club`. Browser verification additionally uses `playwright` and its Chromium installation.

### Environment variables (names only)

- `CLUB_DATABASE`: separate platform SQLite location; default `instance/club.sqlite`.
- `CLUB_SECRET_KEY`: stable signing secret. If absent, generates a private `instance/session.key`, preserved across restarts. Set explicitly for hosted staging.
- `CLUB_SECURE_COOKIE`: enable secure cookies for HTTPS staging.
- `CLUB_SEED_PASSWORD`: private initial password for synthetic accounts; seed does not reset existing passwords or progress.

Account identifiers: `learner@example.test` (free), `member@example.test` (member), `revoked@example.test` (revoked), `editor@example.test` (editor), `admin@example.test` (admin). Expired is a supported entitlement value; dedicated expiry lifecycle/testing is pending. No billing or automatic trial. Privileged roles may read all published lessons, while normal learner entitlement controls paid boundaries. New unauthenticated visitors can read free lessons but must sign in to persist work.

The local installed instance has privately generated credentials at `instance/reviewer-credentials.txt` (mode 0600). Do not copy this file into evidence, source control, browser bundles, or public reports. Reviewer agents on this host may read it in memory for isolated staging verification.

## Data and operations

`club/schema.sql` sets schema `user_version=2`. Version 2 adds the resources table without changing existing IDs or learning records. `init-db` creates missing schema objects without deleting rows. Run it before `seed`. The seed uses stable IDs and `INSERT OR IGNORE`: re-running preserves existing content and user work. Never use the seed as a content-update migration. Future schema changes need explicit versioned migrations and backup/restore testing. SQLite foreign keys are enabled for every application connection. Progress and practice are keyed by user + stable lesson ID. User IDs are derived from the signed session, not accepted from client payloads.

Back up using SQLite's backup API or the `sqlite3 .backup` command before upgrades. Also retain the private signing key and `instance/media`. Stop writers before restoring a backup. Reordering future modules/lessons must retain their IDs; do not reset the database to deploy code. Schema v2 has no destructive downgrade operation; the earlier code ignores the additional resources table. Roll back by stopping the service, restoring its pre-upgrade SQLite backup and matching code commit, then starting the service and checking `/health` and a persisted learning flow.

`scripts/ai-room.service` runs an independent local service on port 8098. Install under `~/.config/systemd/user`, run `systemctl --user daemon-reload` and `systemctl --user enable --now ai-room`. Logs: `journalctl --user -u ai-room`. It does not replace `airoom-designs` on port 8097. Public deployment is pending coordinated routing that preserves the prototypes under a stable path. Do not repoint or alter the old live website.

## Content maintenance workflow

Open `/admin/content/` as editor or administrator. Create a draft course with goal, outcome, prerequisites, tools/cost disclosure and author/owner. Add named modules and lessons. Lessons support text/transcript, local video reference, copyable prompt, practical instructions/checklist, free/member access and independent lifecycle status. Save, then use **Предпросмотр ученика**; it uses the learner template with progress mutations disabled and is protected by role checks. Previewing never records learner progress.

Publish desired lessons, then publish the course. Course publication requires at least one published lesson. A lesson in a draft/archived course remains unavailable through learner pages, API and attachments. Changes to already published lessons become visible on save; there is no separate pending revision of published content. Set the lesson or course to draft before editing if it must be hidden during revision. Archive instead of deleting. Reordering normalizes sibling positions inside a transaction and preserves IDs, completion and practice. Existing lesson/course edit forms reject stale revisions with HTTP 409; copy unsaved text before refreshing. Module rename/reorder is serialized by SQLite but has no multi-editor revision UI.

Add downloadable TXT resources or HTTPS links below a saved lesson. TXT content is stored in the new platform database and served only after lesson authorization. HTTPS references are for public external sources, whose storage permissions are outside this platform. Unsafe schemes, embedded URL credentials and unknown local media paths are rejected. Archive a resource to withdraw it. All lesson text is escaped as plain text; HTML is not interpreted.

For protected videos, an operator places approved `.webm` or `.mp4` files in `instance/media` with filenames consisting of letters, digits, underscores, hyphens and dots. The editor selects from installed files. The directory must never be served as public static content. Videos pass course/lesson entitlement checks and support byte ranges. Include an accessible transcript in the lesson text; generated `fixture.webm` is explicitly labelled as a silent synthetic fixture. Browser uploads and external video providers are not implemented.

Upgrade v1 → v2: back up SQLite using its backup API, retain media/signing key, deploy source, run `.venv/bin/python -m flask --app club init-db`, restart `ai-room`, and check `/health` (schema 2), an existing saved practice and `/admin/content/`. The additive migration is repeatable; automated coverage verifies existing lessons and completion remain unchanged. Local pre-upgrade backup is `instance/pre-authoring-v1.sqlite` (private, not a deliverable). To roll back, stop writers and restore the matching database/code backup, then restart. Do not restore a stale backup after new learning activity without accounting for those later writes.

Authoring verification: `.venv/bin/python -m pytest -q` (7 integration tests), `.venv/bin/python -m compileall -q club`; `scripts/check_authoring_browser.py` exercises editor forms, validation, offline retry, preview playback, protected downloads and 360/390/768/1440px layouts using private local fixture credentials. Worker tests do not replace independent acceptance review.

## Measurement currently present

Server-authored events: first lesson start, first lesson completion, changed practice save/submission, first onboarding completion, help request. First-completion events are unique in behavior per learner/lesson even after uncomplete/recomplete; current completion state is a separate table. No raw draft, password, cookie, email or help text is copied into events. Counts reflect fixture actions, not learning mastery. Course-start and meaningful-return events, validated activation/time-to-first-result/module-drop-off/retention reports and denominators remain next-stage work. No renewal metrics or retention claims.

## Operational limits

Single-host SQLite, local media, no email/password reset or public signup yet; no external support notifications or promised response time. Help requests can be read in the protected inbox; reply workflow is not built. Video is a generated 20-second silent test pattern, labelled as a fixture in the UI; text lessons provide instructional context. The video endpoint supports byte ranges. Assets are served through entitlement checks rather than public static storage. Original author-created training content remains a separate editorial input.
