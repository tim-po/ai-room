# Independent admin product review 005

Verdict: needs_work. P3 remains a blocking usability failure in choosing an assessment edition before irreversible withdrawal. This turn adds the explicit three-edition acceptance fixture; it does not repeat the previously passed graph/practical/replacement lifecycle suite.

Exact app: 358599ee91a2de0ae184f18212d210afef0031c6, /home/claude/ai-room-engine-admin-work. Tested 2026-10-04 with actual Chromium 153.0.8010.12 at 1440×1000 and 390×844, local HTTP http://127.0.0.1:18876/admin/assessments, disposable /tmp/admin-review-005/data.sqlite. Graph tree-2026-10-v1, canonical graph response SHA256 c19c98cef4c00cce21f36c796f2c8732b7229557b56da9546d786a7308a76553. Forms response SHA256 8db22e022f3666853444eda0a94851a4f354ee60098432d8e06b7780519eeaa0; exact populated response and request log retained in result.json. Three explicitly synthetic same-objective, two-item forms were installed in disposable data through the existing test fixture/publishing helper. This is agent task simulation, not human research or semantic approval.

| Task | Result | Evidence |
|---|---|---|
| Load populated assessment list | Pass locally | Real browser GET /admin/assessments and GET /api/skills/forms returned 200; three actual stored forms displayed. Explicit HTTP re-fetch returned all three records. |
| Choose intended original edition without technical IDs | Fail P3 | All three buttons read “Проверить утверждение по источнику · заданий: 2”. Only additional row disclosure is a technical identifier. |
| Choose intended replacement and check selection | Fail P3 | Both eligible options have the same label; selected summary repeats that label. No source/content/date context or edition preview action is presented to distinguish them. |
| Responsive rendering | Limited pass | No horizontal overflow at 390px or JavaScript errors. Opened and inspected edition-list-1440.png, edition-list-390.png, edition-choice-390.png. Copy wraps; the select truncates its long label at mobile width. Fixed navigation shown inside full-page captures is not separately classified as a defect. |
| Real provider correction/remap/reject/preview/publish | Unverified, blocking | Existing provider dependency remains per current-direction.json. No provider called or mocked this turn. |
| Accepted token integration/final staging | Unverified, blocking | Target is unchanged local backend, not accepted integrated UI or final staging. No remote request made; no current staging SHA inferred from old records. |

Source inspection: club/static/assessment_maintenance.js defines label as title plus item_count and reuses it for rows, replacement options and selected summary. The rendered behavior matches that real code. No new backend/API defect was observed. GET /api/skills/graph returned populated graph data with the hash above; browser landing calls including /api/skills/me succeeded. No withdrawal was submitted in this bounded choice test; previous review 004 retains the separate historical-preservation evidence.

## Concrete correction and acceptance

Admin engineer owns P3 within admin routes/templates/styles; request a scoped DTO addition if necessary. Every edition should visibly identify its editorial version or label and source/lesson context, with reviewed timestamp as supporting information. Date alone is insufficient for same-day editions. Retain technical IDs as secondary details. The opened original, replacement options and selection summary must use the same unambiguous identity. Provide source/item review context before confirmation without requiring schema knowledge. Preserve the existing consequence counts, irreversible-action explanation and stable IDs.

Recheck with three same-objective, same-count editions including two reviewed on the same day. At desktop and mobile, a novice agent must select a specified original and replacement from visible meaningful labels, inspect the chosen edition, and confirm the same identity in the summary without DOM inspection or technical-ID lookup. Then recheck withdrawal and retained historical rows. Do not assign distinct fixture titles solely to evade the shared-title case.

Manager handoff: explicitly assign P3; the current direction names T1 passed but does not track P3 as its own finding. Preserve review 004 local passes without treating them as final staging approval. No need to reschedule another unchanged local recheck before a correction or integrated candidate arrives. Mandatory actual spoken-video/material AI run, independent output review and final staging acceptance remain separate gates.

No repo source edits, service restarts, process kills, deployments, shared data writes or production actions. No capability denial occurred. Initial interpreter discovery found no `python` executable and no Playwright in the loop worker environment; the existing /home/claude/ai-room/.venv supplied working app/Chromium dependencies. These are harness setup facts, not product failures.
