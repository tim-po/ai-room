# AI Room Club — fresh learning platform

Independent Russian-first application in the previously empty `tim-po/ai-room` repository. Flask + Jinja server-rendered pages, SQLite, native HTML media, small progressive JavaScript. The existing website, its data, APIs, accounts and billing are not used. Orbit charcoal/green/lime and Campus warmth/rounded spacing inform one shared responsive shell.

## Implemented learning and authoring slices

Course discovery and combined search/goal/level filters; 4 synthetic courses including 37 lessons in 9 modules; readable text and an original generated silent video fixture; server-protected lesson text/media/downloads; explicit completion/uncompletion; drafts and saved practice results; server-persisted video position; favourites; preference editing and optional weekly goal; profile; contextual help tickets and role-protected administrator inbox. Anonymous free lessons work. Separate seeded free/member/revoked/editor/admin accounts use hashed passwords. Cookies are signed, HTTP-only, SameSite Lax; mutations require CSRF. No credentials ship in static assets.

This is a first slice, **not an accepted complete release**. Protected course/module/lesson authoring, draft preview, publish/unpublish/archive, ordering, local media selection and additional protected TXT/link resources are now implemented. Standalone materials and registration/recovery are not implemented. Ordered shared-lesson routes and protected route authoring are implemented. Content is explicitly synthetic. Independent usability/product/functional reviews and HTTPS deployment remain required.

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

`club/schema.sql` sets schema `user_version=5`. Version 2 adds the resources table without changing existing IDs or learning records. `init-db` creates missing schema objects without deleting rows. Run it before `seed`. The seed uses stable IDs and `INSERT OR IGNORE`: re-running preserves existing content and user work. Never use the seed as a content-update migration. Future schema changes need explicit versioned migrations and backup/restore testing. SQLite foreign keys are enabled for every application connection. Progress and practice are keyed by user + stable lesson ID. User IDs are derived from the signed session, not accepted from client payloads.

Back up using SQLite's backup API or the `sqlite3 .backup` command before upgrades. Also retain the private signing key and `instance/media`. Stop writers before restoring a backup. Reordering future modules/lessons must retain their IDs; do not reset the database to deploy code. Schema v2 has no destructive downgrade operation; the earlier code ignores the additional resources table. Roll back by stopping the service, restoring its pre-upgrade SQLite backup and matching code commit, then starting the service and checking `/health` and a persisted learning flow.

`scripts/ai-room.service` runs an independent local service on port 8098. Install under `~/.config/systemd/user`, run `systemctl --user daemon-reload` and `systemctl --user enable --now ai-room`. Logs: `journalctl --user -u ai-room`. It does not replace `airoom-designs` on port 8097. Public deployment is pending coordinated routing that preserves the prototypes under a stable path. Do not repoint or alter the old live website.

## Content maintenance workflow

Open `/admin/content/` as editor or administrator. Create a draft course with goal, outcome, prerequisites, tools/cost disclosure and author/owner. Add named modules and lessons. Lessons support text/transcript, local video reference, copyable prompt, practical instructions/checklist, free/member access and independent lifecycle status. Save, then use **Предпросмотр ученика**; it uses the learner template with progress mutations disabled and is protected by role checks. Previewing never records learner progress.

Publish desired lessons, then publish the course. Course publication requires at least one published lesson. A lesson in a draft/archived course remains unavailable through learner pages, API and attachments. Changes to already published lessons become visible on save; there is no separate pending revision of published content. Set the lesson or course to draft before editing if it must be hidden during revision. Archive instead of deleting. Reordering normalizes sibling positions inside a transaction and preserves IDs, completion and practice. Existing lesson/course edit forms reject stale revisions with HTTP 409; copy unsaved text before refreshing. Module rename/reorder is serialized by SQLite but has no multi-editor revision UI.

Add downloadable TXT resources or HTTPS links below a saved lesson. TXT content is stored in the new platform database and served only after lesson authorization. HTTPS references are for public external sources, whose storage permissions are outside this platform. Unsafe schemes, embedded URL credentials and unknown local media paths are rejected. Archive a resource to withdraw it. All lesson text is escaped as plain text; HTML is not interpreted.

For protected videos, an operator places approved `.webm` or `.mp4` files in `instance/media` with filenames consisting of letters, digits, underscores, hyphens and dots. The editor selects from installed files. The directory must never be served as public static content. Videos pass course/lesson entitlement checks and support byte ranges. Include an accessible transcript in the lesson text; generated `fixture.webm` is explicitly labelled as a silent synthetic fixture. Browser uploads and external video providers are not implemented.

Upgrade v1 → v2: back up SQLite using its backup API, retain media/signing key, deploy source, run `.venv/bin/python -m flask --app club init-db`, restart `ai-room`, and check `/health` (schema 2), an existing saved practice and `/admin/content/`. The additive migration is repeatable; automated coverage verifies existing lessons and completion remain unchanged. Local pre-upgrade backup is `instance/pre-authoring-v1.sqlite` (private, not a deliverable). To roll back, stop writers and restore the matching database/code backup, then restart. Do not restore a stale backup after new learning activity without accounting for those later writes.

Authoring verification: `.venv/bin/python -m pytest -q` (7 integration tests), `.venv/bin/python -m compileall -q club`; `scripts/check_authoring_browser.py` exercises editor forms, validation, offline retry, preview playback, protected downloads and 360/390/768/1440px layouts using private local fixture credentials. Worker tests do not replace independent acceptance review.

## Learning measurement (schema v3)

`/admin/measurement` is restricted to administrators, including direct requests. It reports real database aggregates, with denominator and observation-window definitions alongside each number. Editors/admins are excluded; synthetic learner accounts are included and explicitly labelled.

Validated server-authored event names: `onboarding_completed`, `course_started`, `lesson_started`, `lesson_completed`, `practice_saved`, `practice_submitted`, `help_requested`, `meaningful_return`. The event writer accepts only this allowlist. There is no client event-ingestion endpoint. Events contain only learner ID, optional lesson ID, event name and server timestamp; no draft, help text, email, password or cookie. Course identity is resolved through the referenced lesson.

- Course start is unique per learner/course, enforced by the `course_starts` primary key in the learning transaction. A permitted lesson visit, completion toggle or valid practice save records course activity. Media polling, login and preview do not.
- Lesson start/completion retain first-event uniqueness. Repeated identical practice saves produce no additional event. A changed result creates an event but activation counts distinct learners.
- `learning_days` stores one row per learner/UTC date. The first activity on a later UTC date emits one meaningful-return event. It measures resumed activity, not quality or mastery.
- Activation: learners with at least one `practice_submitted` event / all current learner accounts. Draft saves are not activation.
- Time to first result: median seconds between first lesson/course start and first submission, restricted to learners with both timestamps in valid order. The report states this sample size and includes elapsed time off-site.
- Module noncompletion: current starters lacking completion for all currently published lessons / current starters. This is a mutable snapshot, explicitly not proof of abandonment. Publishing new lessons may change it.
- Weekly learning retention: distinct active learners in a UTC Monday–Sunday week also active the following week / distinct active learners in the first week. Four fully observed week pairs are displayed; zero denominators show no data. No partial current-week rate or unsupported renewal metric.

Upgrade v2 → v3: back up SQLite, deploy source, run `flask --app club init-db` with the application venv, restart the service, check `/health` (schema 3) and `/admin/measurement`. New tables are additive; prior learning records are unchanged. Learning-day/course-start history begins at this upgrade and is not fabricated retrospectively. Earlier first-lesson/submission events remain available for time-to-result. Rollback uses the retained v2 database/code backup with writers stopped, as above. The local backup is `instance/pre-measurement-v2.sqlite` and is private.

Verification: `tests/test_measurement.py` covers duplicate retries, role exclusion, authorization, absence of practice payloads in events, explicit metric denominators, median timing, fully observed calendar retention, module completion and repeatable migration preserving prior progress. Worker evidence is implementation verification, not independent release acceptance.

## Operational limits

Single-host SQLite, local media, no email/password reset or public signup yet; no external support notifications or promised response time. Help requests can be read in the protected inbox; reply workflow is not built. Video is a generated 20-second silent test pattern, labelled as a fixture in the UI; text lessons provide instructional context. The video endpoint supports byte ranges. Assets are served through entitlement checks rather than public static storage. Original author-created training content remains a separate editorial input.

## Navigation and onboarding correction (schema v4)

The home continue action now uses the last opened, still unfinished, published and
permitted lesson. `lesson_visits` keeps one row per learner/lesson with a monotonic
per-learner order, including visits within the same second. Video autosaves,
practice saves and completion writes cannot change that order. Anonymous reads,
API reads and editor previews do not create navigation records. If a recent lesson
becomes inaccessible or unpublished, the next eligible visited lesson is used;
otherwise the selected course's first permitted unfinished lesson is offered.
Historical navigation is not inferred from progress timestamps during upgrade.

Skipping onboarding dismisses the prompt only. The first later submitted preference
form records `onboarding_completed`; edits/retries do not add events. A unique index
protects this rule across concurrent requests. The migration retains the earliest
onboarding event if an older version recorded duplicate events for a learner.

Upgrade v3 → v4: back up SQLite, retain signing key/media, stop writers, deploy code,
run `.venv/bin/python -m flask --app club init-db`, then restart and check `/health`
(schema 4). The migration preserves lesson IDs, completion, practice and video
positions. Repeat initialization is supported. Rollback requires the matching v3
code/database backup with writers stopped; account for any post-upgrade learning
activity before restoring. This turn does not change running staging services.

`tests/test_acceptance_regressions.py` integrates the independent tester's two
regressions and verifies same-second reopen order, background writes, a recreated
application/second device, unpublished-lesson fallback, skip/edit retries and
repeatable v3 migration. These checks do not replace independent browser acceptance.


## Shared learning routes (schema v5)

`/routes` lists published routes; `/routes/<id>` shows the ordered milestones,
current completion, free/member access and recommendation explanation. The four
seeded routes reuse stable lesson IDs and existing progress/practice. Foundations
contains the full 37-lesson curriculum. The other goals add two introductory
foundation steps for beginners; agents adds a synthetic API safety introduction.
Experienced learners skip the marked introductory steps, with an explicit
explanation and link to change experience. They may still browse those lessons.

An explicit route switch persists in `route_selections`, preserves all learning
records, and starts recommendation from the new route rather than an old visit.
Subsequent permitted unfinished visits within the selected route resume normally.
Preference changes select the matching published route. Completion is derived
from current route composition and actual lesson completion; all-free-finished is
not full-route-completed. Withdrawn steps show an availability warning without
exposing draft titles. Adding a lesson increases the unfinished count without
resetting prior work. Route completion is not a claim of demonstrated skill.

Editors and admins use `/admin/routes`: create a draft, choose ordered existing
lessons, mark optional beginner-only introductions, preview, publish, unpublish or
archive. A published route requires published lessons/courses and at least one
main step. Duplicate/unknown lesson IDs are rejected. Reordering uses select rows;
empty rows remove route references only. Three empty rows are added after each
save; at most 100 steps are supported. Revision checks reject stale saves. All
mutations require role authorization and CSRF. Preview never records progress.
The editor uses the existing offline/error feedback and retains unsaved fields.

Upgrade v4 → v5: stop the local `ai-room` service; back up SQLite, media and signing
key; deploy this source; run `flask --app club init-db` using `.venv/bin/python -m`,
then `flask --app club seed-routes` to add the initial routes to the already seeded
synthetic content. No password is needed for the route-only seed; it never changes
accounts or existing route compositions. Restart and check `/health` (schema 5),
`/routes`, prior saved work and `/admin/routes`. Fresh setup still uses full `seed`.
Rollback: stop writers and restore the matching code/database backup; retain any
post-upgrade work separately before restoring an older database. Never reset the
shared database to upgrade.

Verification: 19 integration tests cover routes plus previous regressions;
`scripts/check_routes_browser.py` creates an isolated temporary database and HTTP
server for responsive route/home/profile/editor views, beginner next-step,
explicit switch, offline save retry and keyboard disclosure. Evidence output is
controlled by `CLUB_EVIDENCE_DIR`. Independent final-build acceptance remains open.
