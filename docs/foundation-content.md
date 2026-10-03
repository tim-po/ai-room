# Foundation installation and private assessment candidates

This pack implements the six original fictional cases from the independent
learning foundations handoff. It covers the existing `basic-ai.limitations`,
`basic-ai.context`, and `basic-ai.safety` objectives, two cases each. Verification
and every existing objective revision remain unchanged. All lessons are free.
No AI provider produced this pack, and it does not satisfy the real-provider gate.

With the application venv, `CLUB_DATABASE` pointing at the intended isolated
candidate database, and an existing editor/admin identity:

```
python -m flask --app club install-skill-foundations --from-release EXACT_CURRENT_RELEASE --reviewer EDITOR_ID
python -m flask --app club inspect-skill-foundations
```

Install only after `init-skills`. The first command backs up SQLite (mode 0600),
locks the write transaction, checks the supplied parent is still active, adds six
stable lessons and mappings, and carries compatible reviewed forms using
`carry_forms`. It adds no forms, rubrics, evidence or completion. Repeat with the
same parent is a no-op; another active edition requires explicit reconciliation.
Source collisions roll back the whole transaction. On changed foundation ability
semantics the installer refuses and requires fresh review. No schema migration.

The second command is a private operator preview containing answer keys. Never
place its output in public static assets. It verifies persisted lesson bodies and
active mappings, then returns six supported forms with canonical lesson IDs,
edition 1, paragraph numbers and individual paragraph SHA-256 hashes. This
corrects draft handoff references, whose document IDs were not persisted lesson
IDs and whose hashes covered the whole draft rather than each cited paragraph.
Form hashes support exact independent editorial review. Existing lineages are
preserved. Modified lesson text requires a new source edition and fresh review;
the inspector refuses silently repinning altered text.

Each form has three distinct decisions and requires 3/3: ceil(3 * .80) overall,
ceil(3 * .75) for its objective, plus all three critical decisions. Critical flags
retain the learning handoff: each decision prevents a different unsupported claim,
wrong transformation or violation of the fictional data policy. They do not turn
three correlated scenario decisions into general mastery. Practical task/checklist
proposals are retained but grant no applied evidence. Alternate-case equivalence,
semantic sufficiency and publication require independent editor approval. There
is deliberately no bulk auto-approval command for these new forms.

Install and validate on a copy first. Before shared staging installation stop
writers and retain code plus the generated private database backup. To abandon a
failed drill, stop writers, restore its matching database/code, and restart. Do
not restore a backup over later learner writes. Shared deployment and real
backup/restore operations remain manager-scheduled.
