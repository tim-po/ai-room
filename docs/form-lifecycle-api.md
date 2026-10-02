# Per-form withdrawal and replacement

Run backed-up `flask --app club init-skills` before serving this revision. This adds an immutable withdrawal ledger, leaving all published forms, graph releases, attempts, results and evidence intact. No restore/reactivate endpoint exists: publish a reviewed new immutable form instead. Graph rollback cannot reactivate a withdrawn form. Mapping-only copies follow their recorded inherited_from_form ancestry: withdrawal of any ancestor fences both existing and future copies. An explicitly newly reviewed independent form is not an inherited copy.

Authenticated editor/admin with CSRF: `POST /api/skills/forms/<assessment_id>/withdraw`:

```json
{"confirm_reviewed":true,"reason":"Editorial reason, 10–2000 characters","replacement_id":null}
```

Returns 201 `{status:"withdrawn",replacement_id,reason,created_at}`. Exact replay returns 200, changed replay 409. Reason is learner-visible; do not enter keys, answers or private review notes. Optional replacement must already be reviewed/published, active in the current graph, non-withdrawn, cover exactly the same objectives with the same semantic revisions and preserve access. Invalid/incompatible replacement is 409. Replacement is a pointer, never a copy or automatic publication. A replacement can later be withdrawn itself; always resolve its current status. Existing internal `publish_reviewed_form` remains the explicit publication boundary with review required.

Learner behavior:

- Withdrawn forms disappear from node assessments and diagnostic next recommendations; new attempts return 409 with lifecycle and optional replacement metadata.
- Existing attempts remain readable/resumable, including idempotent creation replay. Attempt DTO now includes `lifecycle`. If submitted after withdrawal they retain scoring/feedback but `credited:false`; result includes lifecycle at grading time. A previously stored result returns unchanged, preserving earned evidence.
- Practical task DTO includes lifecycle. Withdrawal removes tasks from the current listing, blocks publishing linked new tasks and starting new submissions. Existing work can still be recovered/saved/submitted/reviewed. A new human decision after withdrawal can show criteria met but cannot grant application credit. Previously stored decisions/evidence remain unchanged.
- Exposure survives withdrawal and graph changes. Repackaged/overlapping questions and shared editorial lineage remain practice-only. An unseen reviewed independent form can certify; exposure is per learner across all forms. Semantic independence still requires learning review: different wording alone does not establish equivalence or independence.

All withdrawal, challenge creation/submission and practical decisions serialize through SQLite immediate transactions. Withdrawal is immutable under update/delete triggers. Existing graph-retirement policy remains: pinned attempts may finish after graph replacement unless their particular form was explicitly withdrawn.

Frontend: render a short withdrawn explanation, preserve work/history, offer replacement only after retrieving current node metadata. Do not label `passed:true,credited:false` as newly verified. No frontend controls shipped in this backend commit. This does not deliver the outstanding independent transfer-case inventory, which belongs to learning review/content integration.
