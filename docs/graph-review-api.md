# Shared graph editorial review API

Backend ownership: `club/graph_review.py`, additive tables in `club/skills_schema.sql`, registration in `club/skills.py`, and `tests/test_graph_review.py`. No content or frontend files changed. Built on backend practical commit `4d0e7cb`; integrate that first, then this commit. Worker remains sole owner of `club/skill_content.py`, teaching content, UI, integration and deployment.

Run `flask --app club init-skills` on the candidate database before using these APIs. This existing command creates a timestamped SQLite backup with mode 0600 before additive migrations. Existing releases, assessments, attempts, evidence, interests, practical work and lesson progress are retained. No staging database was changed by this work.

All endpoints below require an authenticated editor/admin; writes require the existing CSRF header. Editors see/edit their own proposals; administrators can review all. Source job access follows the same boundary. Proposals are private, including their source snapshots. Learner graph remains the active edition only.

## Create and review

`POST /api/skills/graph-proposals` accepts:

```json
{"base_release":"CURRENT_RELEASE", "note":"Why this structural change is useful", "job_id":"OPTIONAL_TEACHING_JOB", "draft_revision":1, "graph":{}}
```

Supply a complete graph when making structural changes. Omit `graph` to start from the active graph. The server assigns its release ID. Source job/revision are optional together; when supplied the server pins the actual stored draft's skill proposals and canonical source snapshots, never caller-supplied provenance. The initial source-derived proposal contains the unchanged graph: AI suggestions do not silently enter the shared tree. UI should let the teacher select a proposed ability, resolve its existing/new ID, choose a parent and title, and explicitly review resulting structure. No-op activation is rejected.

`GET /api/skills/graph-proposals` returns `{proposals:[...]}`. `GET /api/skills/graph-proposals/<id>` returns a proposal containing `id`, `base_release`, `revision`, `state`, `graph`, `source`, `note`, `stale`, `editions` and `diff`.

`diff` contains full added nodes, changed nodes with before/after, added/removed edges, affected node IDs including affected descendants, affected lesson IDs from existing mappings, and evidence policy. It describes curriculum impact, not invented learner proficiency or private work. `editions` lists retained revision/note/editor metadata.

`PUT /api/skills/graph-proposals/<id>` accepts `{revision, graph, note}`; each successful edit increments revision and retains the preceding immutable edition. Only draft proposals are editable. A stale graph may still be edited but cannot activate; create a fresh proposal against the current release after reviewing intervening changes.

## Decisions

`POST /api/skills/graph-proposals/<id>/activate` accepts `{revision, note, confirm_reviewed:true}`. Activation atomically validates the candidate, creates its immutable release, switches the active pointer and records the reviewer and old/new release IDs. An explicit semantic/structural review is required; validation does not certify AI-generated ability wording.

`POST .../<id>/reject` accepts `{revision,note}`. Rejection retains all editions and source provenance.

`POST .../<id>/rollback` accepts `{revision,note}`. Only the currently active proposal can be rolled back. The pointer returns to its base edition; all releases, attempts, earned evidence and practical work remain. If later publication/activation has changed the pointer, rollback returns 409 so it cannot discard that later work. Rolled-back proposals remain historical; create a new reviewed proposal to restore or revise them.

`GET /api/skills/graph-history` returns `{active_release,events}` with timestamp, action, actor, explanation and old/new release IDs. Editors receive events for their own proposals; admins receive all.

400 means invalid structure/input or missing explicit review. 403 means wrong role. 404 includes hidden/unknown proposals/source drafts. 409 means stale revision, terminal proposal, or changed active graph. These are explicit conflicts, not automatic retries. A response lost after activation can be reconciled by GET proposal/history; repeat activation does not add another release/event.

## Validation and scope

One existing root, all existing nodes, stable kinds and revisions, unique bounded IDs, a single containment parent per non-root node, complete rooted containment, separate containment/prerequisite DAGs, valid typed endpoints, advisory relationships only, and major branches under the root. Ability labels/semantics are immutable under an existing ID, including IDs in historical/rolled-back editions: changed ability meaning requires a new ID. Reviewers must still judge duplication and meaning; string validation cannot establish semantic quality.

Existing content mappings and score rules cannot be changed through this structural API. Source publication and worker-owned content integration retain those responsibilities. New abilities start unknown; existing evidence is never migrated to a new ability by title similarity. Current schema permits revision 1 abilities; semantic revisions use distinct IDs to prevent accidental recertification.

This API is ready for a separate compact structural review workspace. It does not deliver frontend controls, assessment withdrawal/replacement, unseen equivalent retake inventory, revised measurement, real-provider acceptance or final staging acceptance. Source linkage tests use an explicitly mocked provider; they are not evidence of live AI processing.
