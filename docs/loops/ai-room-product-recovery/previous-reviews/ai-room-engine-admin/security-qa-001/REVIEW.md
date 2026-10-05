# Independent security QA — needs_work

Reviewed 2026-10-04. Candidate b32d43fb94bdb523750d1b20cd702062815d93bc, clean before/after. Baseline bc4ba3c1f2eed39e42f611836d6990acf7b0a62d. No application edits, deployment, service restart, process kill or shared learner mutations. Scripts/data confined to /tmp; durable review artifacts copied here.

## Direct evidence

Actual HTTP servers: baseline http://127.0.0.1:18878, candidate http://127.0.0.1:18879. Chromium 153.0.8010.12, 1440x1000 desktop and 390x844 mobile. Synthetic seeded inventory plus one explicitly synthetic bound form, rubric, learner draft and wrong-answer result. Graph response SHA256 c19c98cef4c00cce21f36c796f2c8732b7229557b56da9546d786a7308a76553; exact form SHA256 9a4025b2362894e940a98e7760e3c3802b6d06babfad233c3d4a0319b314d9cb. This is not the pending editorial content manifest or semantic approval.

Own reproduction harness review.py, baseline.json and candidate.json show:
- Baseline after free-to-member change: practical task/submission 200, protected marker leaked through diagnostic history, next diagnostic selects protected assessment.
- Candidate same scenario: task/submission 403, marker absent, next=null. **A1 locally verified fixed.** Source inspection confirms parent form.body is supplied to canonical current-content authorization in diagnostic and practical consumers.
- Candidate challenge payload omits answer/rationale; another learner's attempt returns 404. Missing CSRF returns 400; learner teaching API returns 403.
- Actual browser multipart upload 201 and package 200; protected source/file/job 200 for owning editor, 403 learner, 404 unrelated editor. Administrator access remains deliberately 200.
- Worker claim with unavailable provider consumes zero attempts. Actual retry returns 409 and leaves job DTO unchanged. No mock provider used in this harness.
- HTML, bogus MP4 and ZIP upload attacks each return 400. Uploaded malicious instruction text remains untrusted stored source; actual model prompt-injection resistance remains unverified without provider access.
- Browser loaded /admin, /admin/tree, /admin/assessments, /admin/practice, /admin/measurement. Observed real 200 API responses for graph, graph-proposals, forms, practical-review, capabilities/jobs; direct /api/admin/measurement/skills returned 200. Empty graph proposals and practical review reflect genuinely empty eligible queues, not absent endpoints. Populated assessment impact opens and renders one learner/attempt/task/work and zero earned evidence, consistent with fixture. All screenshots opened and visually inspected, including populated impact. Waiting upload persists across page reload, gives a clear connection-check action; mobile no horizontal overflow; observed editor page errors none.
- Minor editorial accuracy issue: impact view displays qa-bound as “Бесплатно” after its bound lesson becomes member-only. Access enforcement correctly blocks the learner, but label reflects original form tier rather than effective current access. Backend/admin should clarify effective access instead of presenting that label as unconditional availability.

Independently executed existing targeted tests with /home/claude/ai-room/.venv/bin/python -m pytest --rootdir=/home/claude/ai-room-engine-admin-work --confcutdir=/home/claude/ai-room-engine-admin-work -p no:cacheprovider -q against test_current_content_access, test_teaching, test_teaching_worker, test_teaching_pipeline, test_form_lifecycle, test_graph_review, test_practical, test_skills: **78 passed in 74.25 seconds**. Covers membership revocation, lesson/course withdrawal/restoration, learner isolation, retry/idempotency, lifecycle and graph checks. Existing mocked-provider tests are supporting regression evidence only, not actual AI acceptance.

Read candidate changes in diagnostics.py, practical.py, transfer_sources.py, teaching.py, teaching_provider.py. Provider adapter fixes endpoint, refuses redirects, bounds request bytes/output tokens, has no tools and requires human publication. Media preflight now precedes paid transcription. Actual monetary reservation/spend enforcement and real-provider failures remain unverified.

## Requirement matrix / next gates

| Requirement | Verdict | Evidence or dependency |
|---|---|---|
| A1 current-content leak | Local pass | Independent baseline fails / candidate passes, candidate.json |
| Roles, CSRF, keys, protected sources | Local limited pass | Direct HTTP statuses above; tests |
| Duplicate credit / graph / lifecycle | Regression pass | 78 tests; not full independent final-stage journeys |
| Admin browser transport and waiting recovery | Local limited pass | Actual upload/package, inspected screenshots and impact |
| Full novice correction/preview/publish | Unverified | Real provider-produced draft absent |
| Real spoken-video + notes provider run | Blocked | Approved CLUB_AI_APPROVED, CLUB_AI_API_KEY, CLUB_AI_MODEL and bounded spend readiness required; AI engineer reports ffprobe absent |
| Provider prompt-injection and actual timeout/failure | Unverified | No approved actual provider run; mocks cannot close |
| Final recovery and installed-state preservation | Unverified | Reliability reviewer must independently test final candidate |
| Final staging SHA/content and UI preservation | Unverified | UI handoff absent, candidate not deployed |

Fresh localhost staging-service health probe at http://127.0.0.1:8098/health returns build dae021716ac92abe5fdf1253093f82ac8f3f3286, schema 6, ok. This is not an HTTPS/public staging acceptance. Role restricts probes to localhost. Candidate b32d43f and staged dae0217 are different builds; local pass cannot be promoted to final signoff.

Manager: close A1 for this local candidate, retain overall needs_work. Arrange exact integrated UI/content build and independent staging, semantic, real-provider and recovery reviews. Do not re-open completed A1 solely because the broader acceptance gates remain incomplete. Do not publish content based on these synthetic fixtures.
