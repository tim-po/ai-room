# Optional diagnostic API (increment 009)

Backend-owned module `club/diagnostics.py`, additive `skills_schema.sql`; no frontend files or deployment. Existing session/CSRF rules apply. Run `init-skills` (backs up first).

- `POST /api/skills/diagnostics`: `{request_id: string(8..128), interests: [node_id]}`. Returns 201 persisted diagnostic; identical request replay 200, changed payload 409. Interests are local to this diagnostic, never replace exploration/preferences. Empty interests checks foundations only.
- `GET /api/skills/diagnostics`: owner session history, newest first.
- `GET /api/skills/diagnostics/{id}`: owner-only resumable state.
- `POST /api/skills/diagnostics/{id}/advance`: `{revision, attempt_id}` acknowledges an immutable completed challenge from the session’s pinned plan (normally `next.assessment_id`). Create/resume/submit that challenge through existing challenge APIs. No grades accepted. Revision conflict 409; acknowledged attempt replay returns current state. `skip:true` ends diagnostic without awarding evidence.

DTO: `id, revision, release, interests, state(active|completed|skipped), next, observations, unknown_objectives, recommendations`. `next` includes assessment ID, node, objective IDs, explanation and pending attempt ID if present. Foundation first, then round-robin across selected interests, maximum 8 forms. Each advance recomputes from pinned reviewed forms and current evidence; already verified objectives are skipped. Failed observations recommend their exact gaps and source references through the existing challenge result. Practice-only success cannot create strengths. Untested scope remains explicitly unknown. No global level, application competence or prerequisite lock. Insufficient reviewed inventory can finish with unknown objectives.

Pinned session history survives graph changes; `next` is null with `state=completed` once its release retires (existing challenge remains separately resumable). Entitlement is reevaluated on each read/advance. Response contains no answer keys. Same evidence sufficiency and exposure protections as topic challenges.
