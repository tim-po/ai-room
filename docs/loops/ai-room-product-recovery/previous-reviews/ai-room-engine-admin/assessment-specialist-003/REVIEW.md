# Independent assessment review 003 — needs_work

Exact application: 775f69bf6d8a5dbe7e3a5f503d96e748b196b85a. Local URL http://127.0.0.1:18765, Chromium 153.0.8010.12, viewport 1440x1000. Content: cumulative manifest 9360018f5f0a922e64ab5316fe2b065a4317de5edb77fc40519478b964639e28; graph curriculum-aa69319f873d2dc30c38d1f67184d77c4e4b08ed8d21b58358e242909f601350. Disposable database backed up from previous review fixture; new synthetic learner. No application source, shared data, publication or deployment changed.

## Exact decisions

Accept four previously unverified historical teaching mappings: skill-specialist-design-v1, skill-specialist-web-v1, skill-specialist-debug-v1 and skill-specialist-codebase-v1. decisions.json records recomputed source/body hashes, exact mappings and individual rationale. All paragraphs, worked examples, practice instructions and checklists were read against real stored and browser-rendered content. Acceptance covers narrow synthetic teaching only. These checklists are not approved applied-certification rubrics, and lesson completion never certifies competence. Reviewer did not author the reviewed teaching content.

Debugging content in this exact retained manifest is valid: JSON parses, string-key sorting produces B,A, numeric-key sorting produces A,B. Initial suspicion based on escapes in serialized inspection output was disproved by stored-text parsing and browser inspection. No migration or repair occurred; copied before/after body bytes are equal. Do not carry an older debug-JSON rejection onto this exact hash without matching its actual bytes.

Preserve all other prior decisions. Seven transfer forms remain revise; equivalent retakes remain unapproved. No blanket acceptance of remaining inventory mappings, no mastery claim, no shared publication instruction.

## Actual browser and HTTP evidence

Loaded all four /lessons/skill-specialist-{design,web,debug,codebase}-v1 pages, fetched their corresponding populated /api/skills/nodes/coding.*.demonstrate routes and nonempty checklist downloads. Exercised each real practice endpoint using both Save draft and Save result controls, then its completion endpoint. Practice returned 200; completion returned 302 followed by rendered 200. Inspected all four final PNGs using image viewer: source passages, saved practice, completion and separate-credit wording are visible. Graph/me requests also returned 200. result.json contains real endpoint logs and before/after learner state.

Persisted counts for this synthetic learner: four progress rows, four practice rows, zero understanding evidence. All 26 objectives remain unknown; verified and application_verified remain zero. Thus saved activity and completed lessons do not generate false understanding/application credit in these tested flows. Partial, positive understanding, human applied review and withdrawal/version behavior retain earlier scoped evidence; they were not re-certified on final staging this turn.

## S1 backend improvement, remaining UI gate

Independently executed test_challenge_presentation.py: 11 passed in 20.40 seconds. Coverage includes seven transfer-source bindings, persistent order/restart, access changes, invalid-source rejection, historical attempts and repeat-credit prevention. These are synthetic local implementation tests, not equivalence approval.

Actual loopback POST /api/skills/challenges for verification transfer returns populated case text and hashes before response; all three hashes independently match the delivered bytes. Real GET resume and idempotent POST replay preserve item/choice order. Exact source endpoint returns 200. This is a local backend delivery pass for the exercised form, supported by all-seven automated tests; it is not all-seven browser acceptance.

Current club/static/challenge.js still renders choices without item.case, so the UI integration gate remains open. Following manager direction, did not repeat the unchanged missing-case challenge screenshot audit. After UI integration, independently inspect all seven pre-answer cases, answer distractors, exposure and transfer sufficiency. Shuffling does not establish equivalent measurement.

## Remaining dependencies

Latest pipeline report ai-pipeline-004/REPORT.md says CLUB_AI_APPROVED not approved; CLUB_AI_API_KEY and CLUB_AI_MODEL absent, approved monetary ceiling missing. No actual provider-generated spoken-video/material artifacts available to review; provider semantics remain unverified. Synthetic fixtures and local media probes do not satisfy this gate.

Read-only loopback staging health http://127.0.0.1:8098/health still reports dae021716ac92abe5fdf1253093f82ac8f3f3286, schema 6. This differs from tested candidate. Final integrated staging browser/assessment signoff remains unverified. Role permits loopback testing; no remote final-staging browser claim.

Scripts: /tmp/assessment-review-003.py and /tmp/assessment-decisions-003.py. Results: result.json, decisions.json and four inspected PNGs in this directory. No denied commands; initial unavailable bare python interpreter and nonexistent optional path were tooling lookup errors, not product failures.
