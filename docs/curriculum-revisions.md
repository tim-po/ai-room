# Reviewed revisions of existing lessons

This pack revises ten existing foundation lessons in place,
with topic-specific fictional inputs, instructions, worked artifacts, error
analysis and observable practice checklists. The first two cover context. Eight further revisions cover data minimisation,
model limitations, fact checking, document versions, writing, workflow definition,
retrieved evidence and common rubric scoring. Each proposes one narrow existing
objective teaching mapping. They create no assessment, completion or proficiency evidence.
The existing IDs, access, ordering, titles, progress, resume and saved practice
remain intact. The replacement text edition has no video; the complete preceding
row, including any media reference, is retained in an immutable revision manifest.

Independent learning review is still required. The command below prepares exact
before/after lesson rows and a complete graph hash; it does not mutate state:

```sh
python -m club.curriculum_revisions --database /isolated/copy.sqlite > /private/revision-review.json
```

Output includes member/draft lesson content. Keep it private and out of static
assets. Review all teaching, practice and proposed objective scopes, including
the deliberately incorrect draft and correction in the second lesson. The hash
covers the exact existing lesson rows, replacements, scopes and graph. Approval
on a synthetic baseline cannot authorize a different integrated content hash.

After independent approval of that exact hash and manager-scheduled integration,
run the existing backed-up `flask --app club init-skills` migration to add
`skill_curriculum_revisions`, then:

```sh
python -m club.curriculum_revisions --database /isolated/copy.sqlite \
  --reviewer EXISTING_EDITOR_ID --reviewed-sha256 EXACT_APPROVED_HASH
```

The installer backs up private state with mode0600, locks the transaction,
rechecks the hash and editor role, retains the complete immutable before/after
manifest, updates only source fields on those same lesson rows, and activates a
new graph release with compatible original assessment IDs. Any failure rolls
back the entire change. Current existing mappings for these lessons require
separate reconciliation and are rejected. A replay is a no-op, including after
later editorial changes; it cannot silently reset those changes or the graph.

The internal `install` function requires a caller-owned locked transaction and
backup; the module CLI supplies both. Prior editions remain queryable by staff
in `skill_curriculum_revisions.body`; no public historical-source endpoint is
introduced, and no existing assessment source is repinned. For rollback restore
the paired pre-install DB/media backup only on an isolated/quiescent target;
never restore it over later learner writes. A forward editorial revision should
be used when later learner activity exists.

This ten-row pack supersedes the uninstalled two-row preview: its hash must be
reviewed afresh. On a copy with all prior teaching packs, mapped coverage changes
from 29/70 to 39/70 without removing lessons. This arithmetic does not close the
most-content semantic acceptance gate. An already-installed two-row pack will
fail the existing-mapping guard; do not bypass it or replay this pack over it. No independent
acceptance, live installation, provider success or broader skill mastery is
implied by the tests.


## Cumulative private review bundle

After private transfer sources and existing example lessons are present on an
isolated copy, export all seven final learner-bound transfer candidates, existing
immutable forms, the ten full before/after revisions and the unchanged inventory:

```sh
umask 077
python -m club.curriculum_review_bundle --database /isolated/copy.sqlite \
  --reviewer EXISTING_EDITOR_ID > /private/cumulative-review.json
```

The export uses a read-only transaction and requires a named editor/admin. It
contains answer keys and paid content, so never serve it as a public asset.
Export identity is not signoff. Transfer form IDs and source URLs are fixed in
this proposal; access or ID changes need new hashes. Individual final form
hashes remain distinct from the curriculum hash and cumulative package hash.
No transfer is installed, published or deemed equivalent by this command.
Role, entitlement, withdrawal and retained-history HTTP regressions are in
`tests/test_transfer_sources.py`; export immutability and access-change hash
checks are in `tests/test_curriculum_review_bundle.py`.
