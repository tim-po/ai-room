# Specialist teaching installation

Sixteen original fictional worked lessons cover the remaining specialist
abilities: four in coding and three each in teams, content, automation and
agents. Existing seven examples and six foundation lessons remain intact.
Together they provide teaching mappings for all 26 existing abilities. This is
an inventory statement, not independent semantic acceptance or learner mastery.
The 12-minute lesson duration is an editorial estimate, not observed task time;
local execution exercises can take longer. No provider generated these lessons.

Use the application venv and an isolated database copy first:

```
python -m flask --app club install-skill-specialists --from-release EXACT_CURRENT_RELEASE --reviewer EDITOR_ID
python -m flask --app club inspect-skill-specialists
```

`init-skills` must already have run. Install examples and foundations first for
the combined inventory. The specialist installer can rebase on another inspected
edition with unchanged target ability semantics; it does not assume an obsolete
fixed parent. It makes a private SQLite backup, locks the transaction, verifies
the parent, inserts one course/five modules/sixteen lessons and source mappings,
and carries compatible forms with original IDs and lineage. No existing lesson,
ability revision, assessment, rubric, attempt, evidence, completion or practice
is rewritten. No assessment is published. A stale parent, source ID collision or
changed ability semantics aborts the whole installation. Repeating the same
installation is a no-op; installing an existing pack onto another parent requires
explicit reconciliation.

The inspector verifies persisted body, practice and mapping before exporting
edition-1 paragraph hashes and the exact lesson inventory. Changed sources must
receive a fresh edition and independent review; do not silently regenerate pins.
The pack is separate from baseline generic fixtures deliberately: the learning
audit rejected title-only mappings, and replacing baseline text could invalidate
existing completion context and source provenance. Those fixtures stay unmapped.

Each new lesson has a concrete fictional input, worked reasoning, a result
artifact, a learner task and observable checks. Reliability, monitoring and
agent-execution tasks request actual local logs; a plan alone does not demonstrate
execution. The lessons neither create applied-evidence rubrics nor claim those
tasks passed. The existing mobile/tools practical-rubric revision and alternate
assessment candidates remain separate work requiring independent review.

Manager owns installation on shared staging. Stop writers and retain matching
code and private database backup before that operation. To abandon an isolated
drill, restore its matching database/code with writers stopped; never restore over
subsequent learner writes. No schema migration or public deployment is part of
this pack. Real provider-backed upload acceptance remains outstanding.
