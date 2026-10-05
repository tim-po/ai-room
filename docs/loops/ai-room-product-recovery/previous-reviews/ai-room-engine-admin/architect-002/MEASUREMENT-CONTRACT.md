# Minimal measurement v2 implementation contract — architect proposal

Based on acknowledged shared ownership revision 4 and peer research MEASUREMENT-CONTRACT.md. This is a bounded implementation proposal, not implemented acceptance. Preserve `/api/admin/measurement/skills` version skill-measurement-v1 and all historical events unchanged. Add an explicitly versioned aggregate section or separately versioned endpoint under admin authorization. Never relabel old meaningful_return rows with new semantics.

## Storage and event authority

One additive event table can hold opaque event ID, user FK, schema version 2, server accepted UTC timestamp, allowlisted kind, stable entity ID/revision where applicable, graph/content version, onboarding flow/attempt/step, fixture flag and unique dedup key. No arbitrary JSON, text, answer, source, IP, email, cookie or provider payload. Internal user IDs are restricted personal data, not public analytics identifiers. Join role/fixture eligibility explicitly; synthetic accounts must be flagged in storage, not guessed from email. Historical unknown fixture status must not silently become production evidence.

Server mutation transactions emit substantive events only after an actual accepted state change. Rollback emits none. Duplicate request IDs and identical saves emit none. Maintain uniqueness for first completion per learner/stable lesson so toggle/un-toggle does not farm activity. Saved nonempty result is activation evidence only; submitted/revised artifact and completed reviewed assessment with responses qualify as substantive activity, never competence by themselves. Applied/understanding evidence stays in existing independently governed tables. Reading visits remain their own legacy/activity count.

Welcome delivery and visible exposure are distinct. UI can acknowledge a server-issued opaque exposure marker tied to current user, flow version, attempt and allowlisted step. A bounded session/CSRF protected endpoint accepts only this marker plus allowlisted `visible` or `feedback_viewed` event; it cannot create learning-action events or choose timestamps/user IDs. First visibility per learner/flow/new-user attempt defines cohort; editing never creates another newly exposed learner. Do not equate server GET delivery with visibility. Client clocks are not trusted: use server acceptance time; delayed acknowledgement is measured at acceptance, not backdated.

Use dedicated revision/dedup constraints for onboarding step saves/skips/completion; current onboarding_events_v1 can supply committed mutation evidence once mapped explicitly, but absent visibility cannot be fabricated retroactively. O1 preference concurrency must be fixed independently. Feedback visibility references an authorized existing published result/version; validate current access without logging its text.

## Exact aggregate semantics

Return `{version, observed_at, timezone:"UTC", eligibility_definition, fixture_excluded, numerator, denominator, rate}` for rates; rate null when denominator is zero. Include the cohort interval and observation window alongside each metric. No raw learner event stream in the admin summary.

- Navigation complete/skip within 24h: only first exposed cohorts with exposure+24h <= observed_at; skip remains explicit and denominator includes skippers.
- Activation: first nonempty saved result or completed reviewed assessment available within [exposure, exposure+168h); denominator first exposed eligible learners whose entire 168h window ended. Result types reported separately from earned evidence.
- Time to first result: median/p75 wall-clock duration among converters; always show converter and eligible counts. No-result learners excluded from time statistic only.
- D1: t0 first accepted substantive activity; numerator learners with qualifying action in [t0+24h,t0+48h), denominator learners with t0+48h <= observed_at.
- D7: [t0+168h,t0+192h), denominator fully observed through t0+192h. This is distinct from a calendar-week or any-seven-day-return measure.
- Existing cross-branch, job attempts, ready/publication aggregates remain versioned current-outcome measures. Do not combine original graph attribution with today's mappings without a visible projection label. Retry counts are not provider billing counts.

Retain learning evidence, attempts, support audit and content provenance per existing product retention requirements; never purge those via telemetry cleanup. Proposed default for newly collected raw measurement events: 90 days, with a documented cleanup boundary and privacy-safe aggregate snapshots if longer comparison is needed. This duration needs manager adoption before implementation; do not delete existing rows under this proposal. Account erasure policy must address both event rows and aggregates explicitly. Suppress public small-cell output; these endpoints are admin-only.

## Acceptance and migration

Additive initialized schema plus private paired DB/media/signing-key backup. Existing installed records and user_version=6 alone are insufficient evidence: record migration inventory, active graph and source/publication hashes. No backfilled exposure or substantive activity from old GETs. Compatible old code ignores new tables; code rollback retains later learning writes. Snapshot data restoration requires stopped writers and reconciliation of writes after the snapshot.

Independent controlled-timestamp fixtures must test exact inclusive lower/exclusive upper boundaries, fully matured denominators, zero→null, duplicate retries/unchanged saves/completion toggles, role and fixture exclusion, multiple tabs, delayed acknowledgement, current-content loss and real browser exposure→save→result→feedback. Reconcile each aggregate against SQL event identities. Do not report achieved retention on synthetic staging data.
