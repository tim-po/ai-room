# Competency backend increment

Install against an initialized baseline database with `flask --app club init-skills`.
The command makes a SQLite online backup next to the database (mode 0600) before
adding isolated competency tables. Baseline schema/user_version stays at 6;
competency curriculum versions live in skill_releases. Repeating installation
preserves the active release and all learner data. Never run seed against shared
staging during this milestone. Rollback: stop the service, restore the recorded
backup, and use the baseline code; do not restore while accepting learner writes.

Public graph contains one root, five major branches, 22 sibling categories and
26 abilities. Contains, advisory prerequisite and related edges are separate.
Interests may be replaced; explorations and earned evidence are independent.
Current coverage counts distinct objectives at their current revision. Historical
evidence remains visible if an objective revision changes; there is no implicit
semantic equivalence. Unknown is not an ability score. Application credit is not
implemented and is always zero, distinct from understanding.

Reviewed forms are inserted through `publish_reviewed_form` by backend editorial
code; this increment deliberately does not seed allegedly reviewed assessments.
The test form is synthetic test-only, not release learning content. Structural
validation requires two observations per objective including a scenario, 80%
overall and 75% per objective rounded up, and all critical items. Human review
must establish independence, correctness and semantic source support; structural
checks alone do not establish assessment quality. Keys and rationales are omitted
from attempt DTOs; rationale/source feedback is available only after submission.
Exposure is checked across all historical forms/releases for the learner. Any
overlap makes the entire new form practice-only; unfinished overlapping attempts
return 409. Canonical content hashes ignore item/form IDs, choice ordering, Unicode
compatibility typography, case and whitespace. Editors must preserve lineage_id
for paraphrased variants of one observation. Exact copies cannot evade detection
by changing that field. Semantic paraphrase detection is an editorial obligation,
not an automatic guarantee. Repeated content/lineage within a form is rejected. Request idempotency is per user; result submissions are immutable. Credits
never write lesson completion or video progress. All mutations require the existing
session CSRF token, and member access is checked at creation and submission.

API paths and DTOs are in the loop output skill-tree-r2/api-contract.json. The
frontend worker owns presentation and its route registration; this backend adds
only register_skills in the shared app bootstrap.

Remaining required work: reviewed production forms and mappings; adaptive placement;
practical artifact review; per-form withdrawal/editorial UI; graph change
preview/approval and coverage-change explanation; protected upload and durable AI
jobs, source-grounded generation, publication and operational/provider verification.
No upload endpoint or AI fallback is claimed by this increment. Approved provider
API credentials and model selections were absent from inspected runtime/project
configuration. The real provider release gate remains blocked, not passed by tests.

## Integrity and reload contract (increment 003)

New attempts are allowed only for forms on the active graph release. There is no
implicit carry-forward: an editor must explicitly publish a reviewed form against
the new release. Previous item exposure follows the learner across this operation.
Previously pinned attempts may be resumed by their original request_id, read, and
submitted after retirement; original scoring/version and entitlement checks apply.
No schema changes or data rewrite are required for this increment.

GET /api/skills/challenges/<id> returns the public attempt DTO plus result (null
until submission); ownership and current membership access are checked. Result is
the immutable saved submission. No answer/rationale appears before submission.
Node assessment metadata adds item_count, objective_ids, availability=active and
credit_kind=understanding; no question bodies or keys are exposed by node lookup.

Assessed coverage includes historical results with the same objective ID/revision,
regardless of graph release. Verified evidence implies assessed coverage. A changed
objective revision is unknown until assessed again; original evidence stays visible.
The editor must increment the revision whenever the objective meaning changes.

This is a conservative integrity policy: partial overlap downgrades the whole form;
it does not try to certify using the remaining subset. An entirely independent
reviewed form can still certify. No semantic calibration or live AI acceptance is
claimed by these deterministic checks.
