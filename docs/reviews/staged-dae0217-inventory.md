# Staged learning inventory and publication proposal

Review target: `dae021716ac92abe5fdf1253093f82ac8f3f3286`, https://airoom.nolimlabs.uk/.
Worker verification only; independent functional, design, learning and product acceptance remains required. Runtime, graph, forms and content were not redeployed or published in this turn.

The active database has **0 forms, 0 reviewed practical tasks, 0 understanding evidence and 0 applied evidence**. Ten learner node endpoints confirm no available assessments. Teaching/practice instructions in lessons must not be described as published assessment tasks. The staged browser probe checks 25 learner/editor page loads at 390/1440, all 13 candidate source pages and the ten node endpoints; health before/after pins the exact release. It inspects page loads and empty states, not successful challenges, keyboard journeys or teacher publication.

## Concrete editorial selection

`publication-manifest.json` contains 13 candidate identities with objective, active graph, lesson URL, course/access binding, complete candidate form hash, persisted lesson body hash, paragraph source pins, 3/3 thresholds, matching item decisions and explicit hold reasons. It contains no questions, answer keys, credentials or learner submissions. The inventory opens SQLite in read-only/query-only mode within one read transaction and imports candidate builders from the immutable staged checkout, not incoming backend HEAD.

All six foundation forms match the incoming learning audit's complete form hashes and item source/key decisions. Proposed initial selection: **limitations A, context A, safety A**, each on its existing free published source lesson and its existing objective. Leave B private: equivalence has not been approved. This selection is a proposal for an explicitly scheduled editor decision, not authorization to run a bulk publisher. Scope remains understanding of the taught fictional case, never transferable mastery or applied performance. A/B are not interchangeable retakes.

Seven original cases match source hashes, editions, paragraphs, objectives, lineage and answer decisions. Their available item audit does not pin complete form hashes. Hold them for hash-specific form confirmation using this manifest. Do not use `review-skill-examples` against the current graph: its original-release guard deliberately rejects a later graph, and bypassing that guard would lose the explicit rebasing/review boundary.

No practical tasks are proposed for applied certification. Mobile/tools rubrics and transfer equivalence remain separate independent learning decisions. Incoming staff-only historical source URLs are not approved learner feedback links. Backend/schema ownership remains with the AI engineer; this turn adds operations verification scripts/tests only.

## Exact-build A01–A20 evidence index

Artifact paths below are relative to the parent `deliverables` directory. Prior local implementation tests are not upgraded to staged acceptance.

| Scenario | Exact staged evidence / remaining gap |
|---|---|
| A01 | `worker-staging-dae0217/access-and-map.json` verifies role logins; optional onboarding and concurrent persisted interests need staged journey acceptance. |
| A02 | `worker-staged-inventory/browser/staged-browser.json` checks library page loading; combined filtering, long curriculum and back navigation still need exact-stage acceptance. |
| A03 | `worker-staging-dae0217/deployment.json`, `public.json`: range/video playback; this turn opens all 13 text sources. Full resume/fallback acceptance remains. |
| A04 | `worker-staging-dae0217/restart.json`: retained progress/practice over real service restarts. Two-device save/isolation journey remains. |
| A05 | `worker-staging-dae0217/access-and-map.json`: anonymous/free/member/revoked/editor boundaries, free/paid APIs. |
| A06 | No exact-stage full manual content lifecycle journey yet; do not mutate frozen content for this index. |
| A07 | Supporting surfaces exist; exact-stage favourites/material/help persistence not demonstrated by this turn. |
| A08 | Prior 360/390/768/1440 map screenshots plus this turn's 390/1440 learner/editor pages; full keyboard task completion not claimed. |
| A09 | No exact-stage controlled analytics reconciliation in this turn. |
| A10 | `worker-staging-dae0217/REPORT.md`, `verification.json`: migration, HTTPS and preservation checks; isolated setup tests are identified separately. |
| A11 | Prior exact-stage map screenshots; this turn reads ten node inventories. Concurrent exploration persistence remains to be accepted. |
| A12 | Placement cannot credit staged expertise with zero forms. Optional preference UI is not evidence of diagnostic credit. |
| A13 | Blocked on reviewed publication: zero staged forms. Local challenge tests do not substitute. |
| A14 | Zero staged proficiency evidence; character screen loads, uneven verified-state acceptance not exercised here. |
| A15 | Provider-backed upload/transcription/publication remains blocked on approved provider configuration. |
| A16 | No exact-stage provider/retry/malicious-source journey; local backend tests remain separate. |
| A17 | Map/node and source loading checked; full touch/keyboard/challenge journey remains. |
| A18 | Exact-stage screenshots available; worker capture is not independent design acceptance. |
| A19 | Teacher intake and empty assessment/practice screens open. Novice upload-to-publication remains incomplete. |
| A20 | Exact-stage restart/preservation evidence exists; four independent signoffs, provider smoke and publication coverage remain open. |

## Verification tooling

`scripts/assessment_publication_inventory.py` requires explicit source root, read-only database path, both review decision files and an output path. `scripts/check_staged_inventory.py` requires explicit HTTPS URL, expected SHA, private credentials file, sanitized manifest and output directory. Neither publishes or submits learner work. Ordinary authenticated page visits can record existing visit/analytics behavior.

`tests/test_publication_inventory.py` verifies that review-hash drift and persisted-source drift put candidates on hold, that clean inspection writes no rows and that output excludes keyed question fields. One focused regression passed. These tools are committed separately from the frozen runtime; no independent release signoff is inferred.
