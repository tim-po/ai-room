# Reviewed practical assessment API — increment 010

All endpoints require a session; mutations require X-CSRF-Token. This increment owns club/practical.py, additive skills_schema.sql tables, skills.py registration/profile fields and tests/test_practical.py in the backend worktree. Frontend ownership stays with integration worker; no deployment.

- `POST /api/skills/practical-tasks` (editor/admin): `{assessment_id, objective_id, instructions, criteria:[{id,text}], confirm_reviewed:true}`. Publishes an immutable, explicitly reviewed practical rubric, pinned to an existing active reviewed assessment and one covered ability/revision. Access and sources inherit that assessment; no generated proposal automatically becomes a task.
- `GET /api/skills/practical-tasks?node_id=...`: active-release accessible tasks; `GET /api/skills/practical-tasks/{id}`: pinned task with rubric and sources, entitlement enforced.
- `POST /api/skills/practical-submissions`: `{task_id,request_id}` creates a draft, idempotent by learner/key. Only one undecided submission per learner/task.
- `GET /api/skills/practical-submissions`: own submissions. `GET /api/skills/practical-submissions/{id}` resumes persisted work; owner only while draft; owner or editor/admin once submitted, entitlement enforced for owner.
- `PUT /api/skills/practical-submissions/{id}`: `{revision,body,status:'draft'|'submitted'}`; only owner, optimistic revision, submitted work frozen. Plain text only; links are not fetched. Rubric is pinned and remains reviewable after release changes.
- `GET /api/skills/practical-review`: editor/admin pending queue.
- `POST /api/skills/practical-submissions/{id}/review`: editor/admin, never self-review; `{revision,ratings:{criterion_id:'met'|'not_met'|'uncertain'},feedback}`. Immutable human decision. All criteria met earns one `application` evidence record per learner/objective/revision; any uncertain or unmet rating earns none. Replaying an identical review returns the original; differing reviews conflict. New attempt after decision permits correction without rewriting history.
- `/api/skills/me` adds `application_evidence` and actual `application_verified` counts, distinct from understanding coverage. No lesson-watch/completion writes.

No automated grading or automatic practical credit from knowledge questions. Criteria and feedback are human-reviewed plain text. AI draft practice stays a proposal until explicit rubric publication. UI for task publication/submission/review remains frontend work. Run `init-skills` to back up then apply additive migration; retain baseline schema and prior evidence.
