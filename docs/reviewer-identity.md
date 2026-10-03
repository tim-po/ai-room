# Practical review attribution

Additive DTO contract; no migration. Integrate after c362071.

- Authenticated, entitled practical task responses now have `reviewer` for the immutable rubric publisher (`skill_practical_tasks.reviewed_by`).
- Owner/editor-authorized submission responses have `decision.reviewer` for the immutable authenticated decision actor (`skill_practical_decisions.reviewer_id`). Draft/unreviewed submissions still have `decision: null`.
- Owner-only `/api/skills/me` application evidence has `reviewer` for that same decision actor.

Each reviewer object has `display_name: "Редактор · <16 hexadecimal characters>"` and `attribution: "recorded_reviewer_alias"`. Render display_name as text. This is a consistent pseudonymous editorial identity, not a real name, professional qualification, account role today or the current viewer. Rubric publisher and submission reviewer can differ. The alias is derived from the recorded ID with a versioned SHA-256 namespace and remains stable across profile/role changes and process restarts. It is not a promise of anonymity against someone who already knows the account ID. No emails, raw account IDs, account profile fields or credentials are serialized. Missing legacy provenance returns null, never an invented actor.

Existing access controls remain in effect: other learners cannot read submissions, editors cannot read another learner's drafts, anonymous requests are rejected and revoked member work remains protected. The existing owner evidence summary may retain the review alias after entitlement loss, just as it retains earned evidence metadata; it does not unlock source/work text.

Frontend ownership remains with worker; label the task alias as rubric review and decision alias as work review. No UI or shared staging change is included. Existing score rules, keys, evidence, assessment/rubric versions and IDs are unchanged.
