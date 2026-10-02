# AI Room Club — fresh learning platform

Independent Russian-first application in the previously empty `tim-po/ai-room` repository. Flask + Jinja server-rendered pages, SQLite, native HTML media, small progressive JavaScript. The existing website, its data, APIs, accounts and billing are not used. Orbit charcoal/green/lime and Campus warmth/rounded spacing inform one shared responsive shell.

## First slice

Course discovery and combined search/goal/level filters; 4 synthetic courses including 37 lessons in 9 modules; readable text and an original generated silent video fixture; server-protected lesson text/media/downloads; explicit completion/uncompletion; drafts and saved practice results; server-persisted video position; favourites; preference editing and optional weekly goal; profile; contextual help tickets and role-protected administrator inbox. Anonymous free lessons work. Separate seeded free/member/revoked/editor/admin accounts use hashed passwords. Cookies are signed, HTTP-only, SameSite Lax; mutations require CSRF. No credentials ship in static assets.

This is a first slice, **not an accepted complete release**. Admin content CRUD/preview/publish/reorder, standalone materials, route composition, full measurement definitions/summary and registration/recovery are not implemented. Content is explicitly synthetic. Independent usability/product/functional reviews and HTTPS deployment remain required.

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

`club/schema.sql` sets schema `user_version=1`. `init-db` creates missing schema objects without deleting rows. Run it before `seed`. The seed uses stable IDs and `INSERT OR IGNORE`: re-running preserves existing content and user work. Never use the seed as a content-update migration. Future schema changes need explicit versioned migrations and backup/restore testing. SQLite foreign keys are enabled for every application connection. Progress and practice are keyed by user + stable lesson ID. User IDs are derived from the signed session, not accepted from client payloads.

Back up using SQLite's backup API or the `sqlite3 .backup` command before upgrades. Also retain the private signing key and `instance/media`. Stop writers before restoring a backup. Reordering future modules/lessons must retain their IDs; do not reset the database to deploy code. This first migration has no downgrade operation. Roll back by stopping the service, restoring its pre-upgrade SQLite backup and matching code commit, then starting the service and checking `/health` and a persisted learning flow.

`scripts/ai-room.service` runs an independent local service on port 8098. Install under `~/.config/systemd/user`, run `systemctl --user daemon-reload` and `systemctl --user enable --now ai-room`. Logs: `journalctl --user -u ai-room`. It does not replace `airoom-designs` on port 8097. Public deployment is pending coordinated routing that preserves the prototypes under a stable path. Do not repoint or alter the old live website.

## Measurement currently present

Server-authored events: first lesson start, first lesson completion, changed practice save/submission, first onboarding completion, help request. First-completion events are unique in behavior per learner/lesson even after uncomplete/recomplete; current completion state is a separate table. No raw draft, password, cookie, email or help text is copied into events. Counts reflect fixture actions, not learning mastery. Course-start and meaningful-return events, validated activation/time-to-first-result/module-drop-off/retention reports and denominators remain next-stage work. No renewal metrics or retention claims.

## Operational limits

Single-host SQLite, local media, no email/password reset or public signup yet; no external support notifications or promised response time. Help requests can be read in the protected inbox; reply workflow is not built. Video is a generated 20-second silent test pattern, labelled as a fixture in the UI; text lessons provide instructional context. The video endpoint supports byte ranges. Assets are served through entitlement checks rather than public static storage. Original author-created training content remains a separate editorial input.
