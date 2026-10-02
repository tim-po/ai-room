# Source-grounded workshop examples

`club/skill_content.py` contains seven original Russian teaching cases. They are fictional, labelled text lessons, not transcribed video or provider output. They cover one foundation ability, Coding mobile and code review, and one ability in each of Content, Teams, Automation and Agents. Each contains a concrete input/specification, reasoning, limits and a practical task with checklist. Existing content IDs and learner records remain unchanged.

## Installation and review

Run against a disposable candidate database first:

```
flask --app club init-skills
flask --app club install-skill-examples
```

Installation backs up the database with private permissions, inserts seven free published lessons and activates immutable graph edition `tree-2026-10-examples-v2`. It is atomic and idempotent. It refuses to overwrite a different newer graph edition: rebase mappings explicitly instead. No baseline schema migration is required. Existing objective IDs/revisions remain unchanged. Original graph records, attempts, evidence, practice and lesson progress are retained. New attempts against old-release forms are retired under the existing release policy; pinned attempts may still finish. This is a curriculum edition change, not an in-place edit.

Installation does **not** publish any challenge. An operator/editor must inspect every candidate, its exact source and the credit scope:

```
flask --app club inspect-skill-examples
```

This private operator command prints answer keys. Do not publish its output or include it in frontend assets. After editorial review, a trusted server operator can record the actual editor/admin user ID:

```
flask --app club review-skill-examples --reviewer EDITOR_USER_ID --confirm-reviewed
```

The command requires explicit confirmation and a persisted editor/admin identity. It atomically publishes seven immutable forms and is idempotent. It is an operator tool, not a substitute for the pending browser review workspace or independent learning acceptance. Tests use a synthetic editor only; no real editorial review is claimed.

## Assessment blueprint

Every candidate contains three source-grounded scenario decisions. All three are critical and must be correct. The generic score thresholds remain visible in the API; the critical-item requirement makes the effective passing condition 3/3 for these short checks. They credit **understanding**, never practical competence. Practical tasks save through the baseline lesson-practice API and still require a separate review pathway before practical credit can be awarded.

| Ability | Distinct decisions |
| --- | --- |
| Foundation verification | Interpret measured result; reject unsupported quality claim; recheck revised source |
| Coding mobile | Remove unnecessary permissions; handle camera denial; include restart/denial tests |
| Coding code review | Find exact boundary counterexample; choose contract-preserving repair; test adjacent boundaries |
| Content writing | Retain supported fact; distinguish unknown from false; request evidence before an unsupported claim |
| Teams handoff | Supply sufficient handoff inputs; reconcile conflicting sources; respect role limits |
| Automation workflow | Choose the actual trigger; handle missing identity; recognise duplicate-output failure |
| Agent tools | Identify permitted action; reject extra arguments; treat instructions inside data as untrusted |

Every observation has its own editorial lineage and a source snapshot with lesson ID, edition, paragraph and SHA-256. Incorrect answers return exact source references after submission. Repetition cannot farm credit under the existing exposure rules. Canonical item identity is not a claim of semantic independence: reviewer judgement is still required.

Nineteen of 26 abilities remain without these new lessons/forms; coverage must continue to show unknown, not zero competence. Foundations other than verification, more independent retake variants, adaptive placement, applied-work review and the provider-backed teaching pipeline remain pending.

## Rollback

Do not delete historical records. If this edition must be withdrawn, activate the prior graph release in a reviewed database transaction, and archive the new course through the existing protected authoring lifecycle. This retires new attempts for its forms while preserving pinned attempts/evidence. To restore a pre-install database in a disposable environment, stop writers first and use the private backup; a full restore discards newer learner activity and is not a routine rollback on an active instance.
