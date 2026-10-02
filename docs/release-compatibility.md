# Reviewed graph release compatibility

Structural activation and rollback now retain the original forms and practical tasks through explicit `skill_form_bindings`. A binding records target release, original form, originating release, reviewer and creation time; update/delete is prohibited. No new assessment item, unseen attempt, rubric or evidence is created by a structural edit. Original source snapshots, access, scoring, exposure keys, withdrawal ancestry and attempt provenance remain unchanged.

Compatibility requires identical covered ability nodes (including revision and title), an existing assessment node and unchanged score rules. Category rename, added unrelated ability and reparenting therefore retain available certification. Rollback excludes forms for newly added abilities absent in the target tree. Forms newly reviewed in the departing edition can remain available after rollback only when their covered abilities are compatible. Past attempts and submissions remain pinned even if new starts become unavailable.

Availability is always combined with the permanent withdrawal check and entitlement check. A retained binding cannot reactivate a withdrawn form or a descendant of a withdrawn mapping copy. Existing in-progress diagnostics retain their pinned scope and can continue with forms bound to the current graph.

Teacher mapping-only publication also carries bindings instead of cloning retained forms, preserving attached practical rubrics. Historical clones remain supported by withdrawal ancestry; this change does not rewrite them.

## API additions for the worker

Existing graph proposal endpoints keep their methods and request shapes. Proposal DTOs now include:

```
diff.availability = {
  assessments: {unchanged: [form_id], added: [form_id], removed: [form_id]},
  practical_tasks: {unchanged: [task_id], added: [task_id], removed: [task_id]},
  withdrawn_assessments: [form_id],
  policy: "..."
}
rollback_availability = null | <same shape>
```

Show unchanged inventory as well as additions/removals; do not equate no node removals with no assessment impact. `rollback_availability` is populated for an active proposal. These previews are live inventory projections, recomputed on read; they are not frozen publication counts. Structural confirmation already authorizes retention of compatible inventory, and activation/rollback calculates bindings in the same database transaction as the active pointer and graph event.

All existing learner endpoint shapes remain valid. `release` on attempts/tasks continues to mean the original pinned assessment release, which can differ from the active display graph. IDs do not change. Replacement validation accepts a compatible bound form in the active edition while retaining same-objective/access checks.

For a future worker-owned content rebase: call `carry_forms(connection, query, previous_release_id, new_graph, reviewer_id)` after inserting the new graph and before switching the active pointer, inside the same transaction. `query(sql, args=(), one=False)` returns SQLite mapping rows. Do not use `WHERE skill_forms.release_id = active_release` to infer availability; use `available_forms` or `form_available`. The helper does not authorize publication or skip semantic review.

## Migration and operations

Integrate after lifecycle commit `6342d4d`. Stop serving requests while applying migrations, run the existing `flask --app club init-skills` with the configured application database, then restart. The command creates a SQLite backup with mode 0600 before applying additive schema. It replays already-authorized activate/rollback graph events to reconstruct missing compatible bindings for pre-fix structural editions. Running it repeatedly is idempotent and does not change graph selection, source content, forms, progress or evidence. No migration was run against shared staging during this work.

No destructive downgrade is needed for the new table; however older application code ignores bindings and can hide inventory again. A deployment rollback must restore the matching pre-migration application/database snapshot while preserving any later learner writes according to the manager's operational rollback plan. Do not drop history tables as a live rollback technique.

## Verification scope

Cross-feature tests exercise add/rename/reparent, pending and new challenges/practical submissions, continued diagnostics, restart, rollback, exposure/unique credit, withdrawal before/after transitions including ancestor copies, member access, migration repair/idempotence, incompatible new ability rollback, and teaching publication after a structural change. These are functional backend fixtures, not independent semantic assessment approval, live-provider evidence or staged UI acceptance.

Revised derived measurement remains the next assigned backend task. Live AI still requires approved provider configuration (`CLUB_AI_APPROVED`, `CLUB_AI_API_KEY`, `CLUB_AI_MODEL`, names only). No provider call or deployment is claimed here.
