# AI Room Club — fresh learning platform

Independent Russian-first application in the previously empty `tim-po/ai-room` repository. Flask + Jinja server-rendered pages, SQLite, native HTML media, small progressive JavaScript. The existing website, its data, APIs, accounts and billing are not used. Orbit charcoal/green/lime and Campus warmth/rounded spacing inform one shared responsive shell.

## Accepted staging release

Staging: https://airoom.nolimlabs.uk/. The manager accepted application commit
`bc700c5762f559a68b7c1caf9ad297ea29020e97` on branch `education/fresh-platform`
on 2026-10-02. R01–R11 and A01–A10 are covered by the consolidated product
matrix, independent functional/design reviews and manager verification of that
exact build over HTTPS. This is staging acceptance, not production cutover.

The durable acceptance and evidence index is
`/home/claude/bot-swarm/data/_loops/_output/education-platform-for-people-learning/deliverables/manager-final-public/release-acceptance.json`.
It records 35 passing integration tests, independent access-help/privacy checks,
public browser verification and attributed setup/restart/restore evidence.
Documentation-only commits after the accepted application commit do not change
the deployed build identifier or imply a redeployment.

## Implemented learning and authoring slices

Course and standalone material discovery with combined search/goal/level/tool/format filters; 4 synthetic courses including 37 lessons in 9 modules; readable text and an original generated silent video fixture; server-protected lesson text/media/downloads; explicit completion/uncompletion; drafts and saved practice results; server-persisted video position; favourites; preference editing and optional weekly goal; profile; contextual help tickets and role-protected administrator inbox. Anonymous free lessons work. Separate seeded free/member/revoked/editor/admin accounts use hashed passwords. Cookies are signed, HTTP-only, SameSite Lax; mutations require CSRF. No credentials ship in static assets.

Protected course/module/lesson authoring, draft preview, publish/unpublish/archive, ordering, local media selection and additional protected TXT/link resources are now implemented. Standalone guides, use cases and workshops have protected authoring/publication, resources, favourites and video resume. Accounts are operator-provisioned; self-service registration/recovery is not implemented. Ordered shared-lesson routes and protected route authoring are implemented. Content is explicitly synthetic. Independent release acceptance is recorded above; staging operations are documented below.

## Learner frontend (React)

Learner pages that have been migrated (the map at `/`, `/lessons/<id>`, `/profile`) are a React +
TypeScript app in `web/` (Vite, React Router). Flask still owns these URLs: it handles login,
onboarding redirects and status codes (403 for a locked lesson, 404 for a missing one), then serves
`templates/spa.html`, which loads the bundle. Page data comes from `/api/app/*`. Other pages are still
server-rendered and load normally; links between the two work in both directions.

```sh
cd web && npm ci && npm run build   # writes club/static/app/ (not committed)
cd web && npm run dev               # rebuilds on every change; reload the page
```

Node 20+ is needed only to build. The built files are plain static assets served by Flask, so the
server itself does not need Node. Deployments must run the build before restarting the app: without it,
migrated pages show a "frontend not built" notice. Styles are the shared stylesheets in `club/static`
(included through `templates/_styles.html`), so React and server pages look the same.

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

Account identifiers: `learner@example.test` (free), `member@example.test` (member), `revoked@example.test` (revoked), `editor@example.test` (editor), `admin@example.test` (admin). Expired is a supported entitlement value, with content boundaries and access-help recovery tested; entitlement changes are operator-managed, without an automatic billing lifecycle. No billing or automatic trial. Privileged roles may read all published lessons, while normal learner entitlement controls paid boundaries. New unauthenticated visitors can read free lessons but must sign in to persist work.

The local installed instance has privately generated credentials at `instance/reviewer-credentials.txt` (mode 0600). Do not copy this file into evidence, source control, browser bundles, or public reports. Reviewer agents on this host may read it in memory for isolated staging verification.

## Data and operations

`club/schema.sql` sets schema `user_version=6`. Version 2 adds the resources table without changing existing IDs or learning records. `init-db` creates missing schema objects without deleting rows. Run it before `seed`. The seed uses stable IDs and `INSERT OR IGNORE`: re-running preserves existing content and user work. Never use the seed as a content-update migration. Future schema changes need explicit versioned migrations and backup/restore testing. SQLite foreign keys are enabled for every application connection. Progress and practice are keyed by user + stable lesson ID. User IDs are derived from the signed session, not accepted from client payloads.

Back up using SQLite's backup API or the `sqlite3 .backup` command before upgrades. Also retain the private signing key and `instance/media`. Stop writers before restoring a backup. Reordering future modules/lessons must retain their IDs; do not reset the database to deploy code. Schema v2 has no destructive downgrade operation; the earlier code ignores the additional resources table. Roll back by stopping the service, restoring its pre-upgrade SQLite backup and matching code commit, then starting the service and checking `/health` and a persisted learning flow.

`scripts/ai-room.service` runs an independent local service on port 8098. Install under `~/.config/systemd/user`, run `systemctl --user daemon-reload` and `systemctl --user enable --now ai-room`. Logs: `journalctl --user -u ai-room`. It does not replace `airoom-designs` on port 8097. Public staging routing serves the application on port 8098 and preserves prototypes at /prototypes/. Do not repoint or alter the old live website.

## Content maintenance workflow

Open `/admin/content/` as editor or administrator. Create a draft course with goal, outcome, prerequisites, tools/cost disclosure and author/owner. Add named modules and lessons. Lessons support text/transcript, local video reference, copyable prompt, practical instructions/checklist, free/member access and independent lifecycle status. Save, then use **Предпросмотр ученика**; it uses the learner template with progress mutations disabled and is protected by role checks. Previewing never records learner progress.

Publish desired lessons, then publish the course. Course publication requires at least one published lesson. A lesson in a draft/archived course remains unavailable through learner pages, API and attachments. Changes to already published lessons become visible on save; there is no separate pending revision of published content. Set the lesson or course to draft before editing if it must be hidden during revision. Archive instead of deleting. Reordering normalizes sibling positions inside a transaction and preserves IDs, completion and practice. Existing lesson/course edit forms reject stale revisions with HTTP 409; copy unsaved text before refreshing. Module rename/reorder is serialized by SQLite but has no multi-editor revision UI.

Add downloadable TXT resources or HTTPS links below a saved lesson. TXT content is stored in the new platform database and served only after lesson authorization. HTTPS references are for public external sources, whose storage permissions are outside this platform. Unsafe schemes, embedded URL credentials and unknown local media paths are rejected. Archive a resource to withdraw it. All lesson text is escaped as plain text; HTML is not interpreted.

For protected videos, an operator places approved `.webm` or `.mp4` files in `instance/media` with filenames consisting of letters, digits, underscores, hyphens and dots. The editor selects from installed files. The directory must never be served as public static content. Videos pass course/lesson entitlement checks and support byte ranges. Include an accessible transcript in the lesson text; generated `fixture.webm` is explicitly labelled as a silent synthetic fixture. Browser uploads and external video providers are not implemented.

Upgrade v1 → v2: back up SQLite using its backup API, retain media/signing key, deploy source, run `.venv/bin/python -m flask --app club init-db`, restart `ai-room`, and check `/health` (schema 2), an existing saved practice and `/admin/content/`. The additive migration is repeatable; automated coverage verifies existing lessons and completion remain unchanged. Local pre-upgrade backup is `instance/pre-authoring-v1.sqlite` (private, not a deliverable). To roll back, stop writers and restore the matching database/code backup, then restart. Do not restore a stale backup after new learning activity without accounting for those later writes.

Authoring verification: `.venv/bin/python -m pytest -q` (full integration suite), `.venv/bin/python -m compileall -q club`; `scripts/check_authoring_browser.py` exercises editor forms, validation, offline retry, preview playback, protected downloads and 360/390/768/1440px layouts using private local fixture credentials. Worker tests do not replace independent acceptance review.

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

Verification: route integration tests cover routes plus previous regressions;
`scripts/check_routes_browser.py` creates an isolated temporary database and HTTP
server for responsive route/home/profile/editor views, beginner next-step,
explicit switch, offline save retry and keyboard disclosure. Evidence output is
controlled by `CLUB_EVIDENCE_DIR`. Final-build acceptance is recorded at the top of this runbook.


## Standalone materials (schema v6)

`/catalogue` combines courses, guides, use cases and workshop recordings. Search,
goal, level, format and tool filters combine in query parameters, retaining state
on browser back. The tool field searches the real tool/cost disclosures without
requiring a specific vendor. Cards disclose free/member access before opening;
only public description/outcome metadata is queried for discovery. Member-only
text, prompts, resources and media are authorized independently on every request.
Expired/revoked accounts retain free access. Draft/archived materials are absent
from discovery and return 404 at all learner boundaries, including staff learner
URLs. Protected previews use separate staff routes and do not record activity.

Open `/admin/materials` from the content editor. Create a draft, choose guide,
use case or workshop, set goal/level/access, describe outcome/prerequisites/tools
and costs, name the responsible author and add plain text, optional copyable
prompt and installed video. Save, preview, then publish. Save feedback, offline
retry preserving the form, and stale-revision rejection work as in lesson editing.
To unpublish choose Draft; to withdraw choose Archive. Existing IDs, favourites
and video positions remain. Changes to published material are immediately visible;
use Draft before editing when review must precede publication. The update date is
a server timestamp, not a claim of independent verification. Add downloadable TXT
resources or public HTTPS references; archive resources to withdraw them. External
sites enforce their own permissions. Operator-managed media stays in the protected
`instance/media` directory, never under public static storage.

Materials can be saved to profile favourites. Workshop video uses real HTML media
playback, authenticated per-user resume and a visible error fallback with readable
text. It does not create lesson completion, practice or learning events. There are
no invented attendance counts, live events or tutor services. The three labelled
fixtures are `guide-check-answer`, `case-meeting-plan`, `workshop-prompt-lab`.
The workshop shares the synthetic silent video asset; it is not a real recording.

Upgrade v5 → v6: take a private SQLite backup and preserve signing key/media, deploy
source, run `.venv/bin/python -m flask --app club init-db`, then
`.venv/bin/python -m flask --app club seed-materials`. The latter requires no account
password and never changes existing editorial or learner records. Restart the
independent `ai-room` service and check `/health` (schema 6), `/catalogue`, a protected
material, and an existing saved practice. Tables are additive and seeding is
idempotent. Rollback to v5 source can leave additive tables in place, preserving
post-upgrade learning writes; it hides material features until the upgrade is
reapplied. For full database restoration stop writers and restore the matching
private pre-upgrade snapshot, explicitly accounting for any later writes first.
Never operate on legacy-site storage.

Verification: `tests/test_materials.py` exercises draft/publish/unpublish/archive,
stale edits, role/CSRF checks, anonymous/free/member/expired/revoked boundaries,
protected downloads and range media, safe URL validation, combined discovery,
cross-user isolation, restarted-app persistence and repeatable migration/seeding.
`scripts/check_materials_browser.py` uses a temporary DB, private generated accounts
and copied media; tests playback/resume, failed media, favourite profile, combined
filters/back, resource download, offline save/retry and keyboard draft/preview at
360/390/768/1440px. Run with `CLUB_EVIDENCE_DIR` pointing to a report folder. The
existing generated `instance/media/fixture.webm` is required. No shared learner
records are mutated by this browser test. Independent acceptance and public HTTPS verification are recorded at the top
of this runbook.

### Route continuity and media recovery regression (2026-10-02)

Lesson pages belonging to the signed-in learner's selected route show their route
position and a separate next-route-step action. Course previous/next links remain
explicitly labelled as course navigation. Completed routes link to saved practice;
member-only next steps offer access help, and unpublished endings cannot appear
complete. Direct lessons outside the selected route retain course navigation.
Shared lesson IDs and progress storage are unchanged.

The video client reads existing error/network/metadata state on startup as well
as listening for subsequent events. This recovers failures and resume metadata
that arrive before the deferred script starts. `scripts/check_materials_browser.py`
now checks lesson and workshop 404 recovery both before and after script startup,
on initial navigation and reload. `scripts/check_routes_browser.py` checks keyboard
bridge exits for work and agents routes at all four review widths. Two additional
route integration tests cover completed, interrupted, blocked and unpublished
endings. No database migration is required (schema 6).

### Personal learning and weekly goals

Profile lists only courses with persisted course-start, progress or practice records for the signed-in learner. A course is completed when all its currently published lessons are completed (and at least one is published); otherwise it remains in progress. Publishing an additional lesson returns a completed course to in-progress without changing old completion records. Unstarted courses remain discoverable in the catalogue, and saved practice appears before learning cards. Home links directly to `/profile#practice`.

Home and profile share the same weekly-goal display. The achievement is the count of unique first lesson-completion events within the trailing seven days, using UTC server timestamps. Uncompletion does not erase this historical credit, and re-completion/retries never add credit or move an old first completion into the current window. This differs deliberately from current course completion and from the calendar-week retention metric. Pausing hides the target/progress bar while keeping the factual count and learning history; the target can be resumed in preferences. The count is not a skill assessment. No schema change or data backfill is required.

Verification: `tests/test_profile.py` covers empty/active/completed/reopened courses, newly published lessons, user isolation, unique weekly counts, rolling-window expiry, pause and Russian plural forms. `scripts/check_profile_browser.py` uses an isolated seeded database and checks 360/390/768/1440px empty and active profiles, actual saved practice/completion, keyboard activation of the results anchor, goal pause and browser errors. Set `CLUB_EVIDENCE_DIR` to retain screenshots and results.

### Long editorial curricula

Course modules use native keyboard-accessible disclosures. Create, rename and
reorder redirects identify the affected stable module/lesson in the URL fragment;
the editor opens its module and scrolls to it. Returning from a lesson editor also
opens its parent module. Route selectors put lesson titles first and repeat the
full selected title and course beneath each selector, including at mobile widths.
Up/down buttons swap existing lesson references and mark the form unsaved; the
existing explicit save and revision checks persist the order. Route bridges remain
attached to lesson IDs. Browser session storage holds only a one-use path/scroll
position after editorial saves; content and progress remain server-owned and
saving still works when that optional storage is disabled. No schema migration.

Run `scripts/check_editor_layout_browser.py` for isolated 37-lesson/9-module
editor checks at 360/390/768/1440px, keyboard route reorder, persisted order,
module rename location, wrapping and browser errors. `CLUB_EVIDENCE_DIR` selects
the screenshot/result destination. Independent review is included in the accepted-release evidence index above.

## Staging deployment (October 2026)

The platform is served at `https://airoom.nolimlabs.uk/`. Preserved design references
are `/prototypes/#/orbit/home` and `/prototypes/#/campus/home`; the original root hash
bookmarks redirect there. Configure `CLUB_PROTOTYPES_DIR` to the existing read-only
prototype public directory. This optional route serves only its three public assets.
`CLUB_BUILD_ID` identifies the deployed source commit in `/health`.

Set `CLUB_SECURE_COOKIE=1` and a stable `CLUB_SECRET_KEY` in a private systemd
EnvironmentFile. On this host the operator-managed file is `instance/staging.env`
(mode 0600), loaded by the ai-room user-service drop-in. Account provisioning remains
private in `instance/reviewer-credentials.txt`; request access from the staging
operator. These values are never put in this document or public bundles.

Before deployment, back up the installed database with SQLite's backup API and retain
media and signing key. Install dependencies, run additive `init-db`, run checks, then
restart `ai-room`. `scripts/publish_staging.py` updates only the existing dedicated
staging tunnel hostname to port 8098 and privately retains its previous configuration.
The old live website and its data are not accessed. The prototype service on 8097
continues running. Infrastructure access is operator-specific; this script is not
needed for a fresh local setup.

For compatible application rollback, stop both web and queue writers, restore the
reviewed compatible code and build identifier, and retain the current database,
media and signing key so later learner writes survive. If data restoration is
necessary, restore a coordinated database/media snapshot only after reconciling
all later writes; never restore the database alone. For routing
rollback, restore only the staging hostname's previous service (8097) using the private
snapshot, preserving any unrelated intervening tunnel edits. Never blindly replace the
whole tunnel configuration or reset installed learner data. The earlier baseline acceptance is recorded above. The skill-tree candidate
requires independent review of its own exact staged build; baseline acceptance
does not establish acceptance of the revised candidate.

`CLUB_MEDIA_OUTPUT` optionally directs fixture generation to an isolated output path.
`scripts/check_operations.py` verifies actual process stop/start and SQLite backup/restore
using disposable accounts/data. The fuller [service recovery drill](docs/service-recovery.md)
adds queue interruption, natural lease expiry, paired media restoration and
compatible code rollback. `scripts/check_route_resume_browser.py` verifies short-screen
sign-out with pointer/keyboard for learner/editor/admin and late-route resume.

### Repeatable public candidate smoke

Run `CLUB_EVIDENCE_DIR=<private-output-directory> .venv/bin/python scripts/check_public_browser.py --expected-build <full-commit>` from the repository root. Install Playwright/Chromium separately as for the other browser checks. The script requires HTTPS, rejects a mismatched `/health` build before signing in, checks schema/health, preserved prototype bookmarks, authenticated pages, real video playback, mobile overflow, learner denial at admin and measurement boundaries, and a nonempty secure/HTTP-only/SameSite session cookie. Optional `--url` and `--credentials` select another independent staging installation and its private credential file. Credentials and cookie values are never emitted.

This smoke uses the installed synthetic member account: lesson visits and video resume can update that account's learning activity. Run isolated scripts for destructive/data-reset checks; this script does not reset content, completion or drafts. Its screenshots can contain the synthetic account's existing learning state; use only designated staging accounts and keep evidence under operator control. The worker smoke supplements independent acceptance and does not replace it.

### Access-help recovery correction

Published locked lessons can be referenced from `/help?lesson=<stable-id>` without
membership. Help queries only the public lesson ID/title and requires both lesson
and course to be published. It never fetches paid text, prompts, practice, media or
resources. Submission still requires a signed-in identity, CSRF and a nonempty
question; the administrator receives the stable lesson context. Draft/archived or
unknown context returns 404. Existing content/attachment authorization is unchanged.
No migration or seed operation is needed for this correction.

`tests/test_access_help.py` adapts the independent tester's free/revoked regression
to isolated fixtures and extends it to expired access, submissions, privacy,
CSRF and unpublished context. `scripts/check_access_help_browser.py` verifies six
actual recovery/submission journeys at 390/1440px plus administrator receipt using
a disposable database. The repaired route browser check recognizes an already
selected route and continues testing navigation, keyboard controls and offline save.
