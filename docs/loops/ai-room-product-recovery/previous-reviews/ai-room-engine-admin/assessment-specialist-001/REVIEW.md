# Independent assessment review — needs_work

Candidate bc4ba3c1f2eed39e42f611836d6990acf7b0a62d; cumulative manifest 9360018f5f0a922e64ab5316fe2b065a4317de5edb77fc40519478b964639e28. Recomputed package, curriculum, ten revision, seven original-form, seven bound transfer-form, source and two practical-rubric hashes. Exact decisions are in decisions.json. This reviewer did not author the reviewed content.

## Blocking findings

1. **Transfer case absent before response.** Reproduced at /challenges?node=basic-ai.verification&assessment=skill-transfer-form-verification-v1 on the local candidate. Exact bound hash 37583d6cb0a1738fc6dbec00a6db0aaff3ae1c999405a4505b55a626d7762da0. The question asks for the combined proportion, but the report containing 8/10 and 45/90 is absent. Material links lead to the original pilot and unrelated curriculum examples. /api/skills/forms/skill-transfer-form-verification-v1/sources/transfer-source-verification-B/1 returns 200 and correct text; the UI exposes it only after submission. club/skills.py attempt_dto allow-lists prompt/choices but omits the case; club/static/challenge.js renders source only in showResult. Provide an authorized exact-source case before answering without exposing keys/explanations. Recheck all seven forms and diagnostic consumers.
2. **Shared fixed answer pattern.** Every transfer form has correct options 0,1,2 in question order. Neither attempt_dto nor challenge.js changes choice ordering. Cross-branch success can therefore follow a position rule. Revise the pack or implement persisted per-attempt choice presentation; preserve keyed IDs and exposure lineage. Also balance distractor plausibility/length. The retained foundation trio shares its own answer sequence; acceptable here only for narrow taught-case formative understanding, never proof of independent transfer.
3. **No equivalent-retake approval.** Seven transfer cases are not interchangeable measures merely because IDs/case nouns change. In particular workflow/tools largely mirror taught decisions; new lineage IDs cannot alone make them independent. All equivalence decisions remain not approved.

## Explicit semantic decisions

- Accept all ten revised teaching passages and their narrow declared teaching mappings. Source, worked result, learner task and checklist were read. No mastery or broad skill coverage inferred.
- Accept the three retained foundation forms and seven original proposals for narrow taught-case understanding only. All 30 items/keys/explanations reviewed; their quoted source hashes match actual retained lesson passages. This does not approve publication of an arbitrary runtime form: final bound publication hash/thresholds/context must match the reviewed content. Retained export hashes differ intentionally from the staged publication ledger hashes.
- Revise all seven transfer forms for publication for the findings above. The keys are substantively consistent with their editorial cases, but delivery and cross-form cues invalidate acceptance.
- Accept mobile rubric 0aac26ae641a246df817cd64134de94c3f7e0cff14339f1ee4433d16ae4e3dce and tools rubric 0352c362a1eb9de25587c64cbca2e68492116ec8e5a09efc15c16a0235adbaa5 as instruments for the exact synthetic tasks. Human review must inspect reproducible artifacts; no actual learner competence certified here.
- Other historical inventory mappings remain individually unverified; no blanket approval or most-content coverage signoff.

## Product evidence

Ran the candidate on 127.0.0.1:18763 against a SQLite backup in /tmp/assessment-independent-kq60xz1j. Added two synthetic learners only to that copy. The transfer form was installed only as a disposable reproduction fixture using the existing publication API and compatible active graph binding; this is NOT editorial approval or shared publication. No repository source, staging data or production changed.

Chromium 1440x1000: loaded challenge, exercised real node/start/submit/resume/profile-state endpoints, and inspected all five saved screenshots with the image viewer. Initial unknown foundation objectives=4. Partial 2/3 produced assessed=1, unknown=3, verified=0. Perfect first attempt produced verified=1 and application_verified=0. Perfect repeated attempt remained practice with one understanding evidence record. Source endpoint returned real content. Response logs and exact state are in http-browser-results.json and transfer-browser.json.

Targeted independent execution of tests/test_form_lifecycle.py, tests/test_practical.py and tests/test_release_bindings.py: 22 passed in 29.07s. This supports withdrawal, uncertain review, self-review prevention and compatible version preservation but is not final staged browser acceptance. First invocation used the wrong cwd and failed fixture lookup; rerun from the candidate corrected the harness, with no product edits.

Loopback staging health at 127.0.0.1:8098 reports dae021716ac92abe5fdf1253093f82ac8f3f3286, schema 6. Read the staged three-form publication ledger; no new staged browser signoff issued. Required final integrated staging assessment/admin/security/recovery review remains open. Actual provider-generated spoken-video/material outputs were not supplied in this synthetic package; their source/timestamp/item/rubric review remains unverified.
