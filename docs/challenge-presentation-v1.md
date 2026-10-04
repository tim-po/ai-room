# Challenge presentation v1

Additive contract for POST `/api/skills/challenges` (including idempotent replay) and GET `/api/skills/challenges/<attempt_id>`. Existing session, CSRF, owner isolation and current bound content authorization apply. The UI owns `club/static/challenge.js`; backend owns only attempt DTO/start hunks in `club/skills.py` under the shared ownership record revision 3.

Items with a published retained transfer-source binding now contain `case`:

```json
{"source_id":"transfer-source-verification-B","edition":1,"paragraph":1,"text":"<exact retained case text>","sha256":"<reviewed source text hash>"}
```

Render `item.case.text` as plain text before its answer choices, preserving whitespace (code cases need line breaks). Identical source ID/edition/hash cases may share a block before their questions. Do not wait for submit or depend on feedback to reveal the case. No fetch is required. Sources without a retained transfer binding retain their existing DTO without `case`; this does not authorize exposing general teaching explanations before assessment. Missing retained rows or mismatched source text hashes return 409 without creating an attempt. A changed lesson/course publication or entitlement returns 403 before case disclosure, including on replay/resume. Completed/historical authorized attempts can retain their case; withdrawal still prevents new certification via existing lifecycle rules.

Choices remain `{id,text}`. Render their returned order; submit their unchanged IDs, never display indices. New opaque attempt IDs begin `p1-`, followed by a random UUID. This persisted ID is the seed for the version-1 order: choices sort by SHA-256 of UTF-8 compact JSON `[attempt_id,item_id,choice_id]`. This preserves ordering across retry, sessions, application restart and graph editions without schema changes or relying on the session signing key. Historical IDs lacking the prefix preserve original order. Treat the algorithm/version as a compatibility contract; a future algorithm must use a different version prefix. IDs remain opaque URL components to clients.

Grading, original choice IDs, item IDs, form hashes, exposure lineage and historical result bytes are unchanged. New presentation does not change retake eligibility. Keys/rationale/private choice metadata are excluded from pre-answer DTOs. Randomized display is not cryptographic protection against an already exposed question bank or evidence of semantic equivalence. The seven transfer forms remain blocked pending independent source/item/construct review and UI/browser acceptance; this change publishes none of them.

Local automated tests use explicitly synthetic disposable publications; they are not content approval, staging acceptance or provider-backed evidence.
