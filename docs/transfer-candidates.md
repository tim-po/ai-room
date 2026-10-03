# Private transfer review bundle

`python -m club.transfer_candidates` emits seven private keyed forms (21 scenario
items) and two practical rubric proposals. Keep stdout in a private operator
location, never public static assets. Export is read-only and calls no provider.
It does not install sources, publish forms, approve equivalence or grant credit.

Source: independent learning `learning-0fe5163/transfer-case-blueprints.json`.
The bundled snapshots preserve exact text, source IDs, edition, paragraph, hashes,
expected decisions and lineage IDs. Any text/hash mismatch fails export. Supported
assessment schema validation requires three correct decisions here (3/3 overall
and per objective). No decision is newly designated critical. Three questions
about one scenario do not establish three independent general abilities.

The new distractors and mobile/tools observable criteria require independent
semantic review. Reviewers should record exact form and practical hashes,
source support, ambiguity and construct scope; compare against the original
seven example cases before deciding equivalence. Foundation A/B forms are a
separate pack and retain their narrow taught-case status. Neither package's
structural validity implies interchangeable retakes.

Publication remains blocked: first explicitly accept/revise the content and
construct/equivalence, then bind these retained private source snapshots into the
application's canonical source storage with entitlement and historical access.
A `source_id` in this export identifies a bundled document, not an installed
lesson or an already fetchable API resource. Do not invent lesson IDs or repin
the snapshot to an unrelated teaching paragraph. This increment intentionally
provides no publisher or installer; candidates are ready for editorial review,
not operational learner delivery. Existing publish_reviewed_form is an internal
primitive, not permission to bypass these gates.

Mobile and tool practice proposals use the current practical endpoint's
instructions/criteria schema, but omit assessment_id and confirm_reviewed until
actual publication is approved. All criteria need human-reviewed observed
artifacts. A missing/inaccessible run, planned test, prose assertion or uncertain
result must remain unmet/uncertain, never award application credit. The mobile
rubric covers microphone permission/revocation only, not broad mobile expertise;
the tools rubric covers this synthetic read-only boundary only.

Regression tests demonstrate keyed export is absent from public static paths,
export creates no forms/evidence, changed source text fails without silent
repinning, and repackaging IDs/prompts/choice order while retaining lineage causes
a second completed runtime attempt to be practice-only with no duplicate credit.
The publication inside that test is disposable engine verification, not editorial
acceptance. No shared DB, graph release, historical form or baseline progress is
modified by this package.

## Retained editorial storage (direction030 increment)

After the backed-up additive `flask --app club init-skills` migration, run
`flask --app club install-transfer-sources --reviewer <existing-editor-id>`.
The command makes a mode0600 SQLite backup, uses a locked transaction and
idempotently stores all seven exact source editions. Immutable/update-delete
triggers preserve historical snapshots; conflicting text requires a new edition.
It changes no graph, lesson, assessment, rubric or evidence. Installation records
an operator identity, not an approval verdict.

`flask --app club inspect-transfer-sources` exports PRIVATE keyed candidates with
canonical snapshot URLs and recalculated bound-form hashes. `unbound_sha256`
identifies the preceding review bundle. All prompts, choices, keys, source text,
lineage and practical hashes are preserved. Review must name the bound hash.
The endpoint `/api/skills/editorial-sources/<source_id>/<edition>` is editor/admin
only and no-store. Anonymous and learner requests are forbidden, including free
members: these are unpublished editorial documents, not public course resources.
The endpoint returns source text only, never assessment keys.

This closes retained private storage, not learner publication. An explicitly
reviewed publication must still bind each source to the resulting lesson/form
and enforce its entitlement/lifecycle. Do not publish these forms while their
snapshot URLs are editor-only. Equivalence and mobile/tools practical decisions
remain pending independent review. No actual AI-provider processing is implied.
