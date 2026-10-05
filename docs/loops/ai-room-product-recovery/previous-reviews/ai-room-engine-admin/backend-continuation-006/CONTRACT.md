# Learning continuation v1

Ownership: shared coordination revision 5, backend accepted home continuation correction; base d111d4e8179a62596461f5b3bfbe0557fe8db3ca. Source ownership for this correction is club/continuation.py, bounded home context in club/__init__.py, one profile render-context argument, targeted tests and this document. No schema, AI/admin templates, learner templates or grading edits.

Both home.html and profile.html receive `continuation`:

```
{
  "version": "learning-continuation-v1",
  "unfinished": null | {
    "lesson_id": "stable lesson ID", "title": "current title",
    "course_id": "stable course ID", "url": "/lessons/<ID>",
    "status": "draft" | "in_progress", "updated_at": "SQLite UTC timestamp"
  },
  "last_result": null | {
    "lesson_id": "stable lesson ID", "title": "current title",
    "course_id": "stable course ID", "url": "/lessons/<ID>",
    "status": "submitted" | "completed", "updated_at": "SQLite UTC timestamp"
  }
}
```

Unfinished means a saved practice draft (including one attached to a completed lesson), otherwise an incomplete progress row. A submitted practice on an incomplete lesson can remain an in-progress lesson and appear separately as a submitted result. Draft saves without a lesson visit are included. Empty drafts retain existing storage semantics; they are not activation evidence.

Order: descending persisted practice.updated_at for drafts, otherwise progress.updated_at; ties use existing per-user lesson_visits.visit_order, then stable lesson ID. The last-result slot uses submitted-practice or completed-progress updated_at with the same tie rule. These are record-update timestamps, not inferred completion times or new visit timestamps. Legacy visits have a sequence but no wall-clock timestamp; revisiting an unchanged older row only changes tie ordering. No timestamp migration or fabricated historical times.

Both slots enforce current lesson/course publication and current entitlement/editor access, and scope every learning-state join to the authenticated user. No private body, answer, rubric, or evidence claim enters the DTO. Anonymous users receive null slots. No writes or backfills occur.

Home next_lesson now prefers unfinished across all branches. Route preference, visit_floor and changed interests cannot erase it. A permitted route suggestion remains the fallback, then existing course fallback when no route exists. `started` is true for retained unfinished work, including API-only drafts. Last result is independent; submission/completion is activity, not competence.

UI consumer handoff: home/profile should render unfinished as the continuation and last_result as a separate result. Use server URL/title/status; do not reimplement branch filtering in JS. This commit adds profile context but does not change the peer-owned profile template. Browser visual acceptance must occur on the combined UI candidate. No new endpoint or migration is needed.
