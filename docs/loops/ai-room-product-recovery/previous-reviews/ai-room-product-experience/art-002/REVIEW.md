# Independent art direction review — needs_work

Reviewed 2026-10-04. App `6e7d7b31e9d82ba2849a0415a8563eebe5a6d8e6`, clean worktree `/home/claude/ai-room-product-experience`; actual running Flask app at `http://127.0.0.1:18869`, headless Chromium `153.0.8010.12`. Disposable synthetic database, separate temporary instance/media/uploads, seed + init-skills + init-onboarding; no reviewed assessment publication. Graph source `club/skill_seed.py` SHA256 `7b7b7a36063555cc1131f8822b8a0d9339d6b3664b69ed18394cbca4983d50a9`. Health reports development/schema6; git identifies source, not a deployed build. This is independent expert/simulated inspection, not a human usability study or staging acceptance.

No repository edits, service restart, deployment, installed data changes or subagents. Owned output is only this art review/spec directory. Existing two working directions remain in ../art; Atelier selection is retained. Compared opened actual images to opened ../art/atelier-welcome-1440-viewport.png and ../art/atelier-lesson-1440-viewport.png. The selected paper/Golos/vermilion system now spans welcome, map and practice more convincingly, but visual and first-result blockers remain. No new direction exploration is needed.

## Evidence and bounded passes

Ran a new reviewer-authored browser harness, not a builder test verdict. Fresh login automatically reached onboarding; selected Coding and Content, refreshed the saved next step, selected beginner/10 minutes, finished and opened a real permitted lesson. Submitted practical text, directly reread stored body/status, edited and aborted a subsequent save. The old practice success panel correctly disappeared. Visited return, map, selected Coding, catalogue, course, profile, challenges, help and preferences at 360/390/768/1440. Started a real optional diagnostic against the deliberately empty reviewed inventory. Captured 63 states, 126 full-page/viewport files; zero JS errors and measured horizontal overflow. Golos Text loaded and computed as body family. Reduced motion was requested throughout, not a comprehensive motion audit.

Actual browser API responses: onboarding reads/writes 200; practice POST/GET 200 with exact submitted text; graph/me 200 with real nodes/evidence aggregates; Coding and six child ability detail endpoints 200; explore POST 200; diagnostics GET 200 and creation POST 201. Direct browser-request probes `/health`, `/api/onboarding`, `/api/skills/graph`, `/api/skills/me` all returned 200 with content. Catalogue/course/help/preferences are server-rendered, not missing client APIs. Their templates were inspected. No fake API success is inferred from screenshots. The first run accidentally probed /catalog and /api/skills/profile; those are reviewer URL mistakes, corrected in the final run, not product bugs.

Visually opened: welcome390; onboarding-welcome390/768/1440; interests390 viewport and360 full; pace390 full; start390; lesson1440 viewport; failed-resave390 full; map1440; selected390; catalogue390/1440; course390; profile390; preferences1440; help390/768; challenge1440; diagnostic-unavailable390; return390. Gallery is an index, not a claim every generated image was opened.

| Gate | Verdict | Evidence |
|---|---|---|
| Automatic fresh onboarding and multiple interests | Bounded pass | Real login redirect; API committed coding/content, beginner,10 minutes |
| Practice stale-success correction | Bounded pass | failed-resave-390.png; current editor retained, prior confirmation hidden |
| Course prerequisite title/action correction | Bounded visual pass | course-390-viewport.png: readable dark title, separate actions |
| Selected direction coherence | Improving, incomplete | Welcome/map/profile share type/paper/actions; help fails |
| Honest unavailable checks | Partial | Diagnostic says unavailable/no result, but direct challenge actions touch |
| First meaningful instructional result | Fail | Real first lesson has generic prose, no worked example/comparison |
| Correct return continuation | Fail, existing QA-03/L04 | Return recommends foundations while saved work is agent-lab-intro-01 |
| Full product/staging/available assessment/video/zoom | Unverified | Not exercised sufficiently this turn; no staging signoff |

## Concrete corrections

**AD2-01 — blocking, dirty onboarding falsely reads saved.** `interests-390-viewport.png` and evidence.json `dirty_interests`: two visibly checked boxes, status «Сохранено в аккаунте.», while direct GET draft interests is `[]`. `onboarding.js` line34 carries prior transition success into the editable new screen. Any input/change must clear or qualify the prior success and state «Изменения ещё не сохранены». Only acknowledge the exact current draft after backend confirmation. Recheck checkbox/radio changes, back, error/retry and logout before save. This is the same trust issue already repaired for practice.

**AD2-02 — blocking, help contrast.** `help-390-viewport.png`, `help-768-viewport.png`: «Задать вопрос» and «Что не получается?» are white on pale warm surface. Actual `templates/help.html` uses `.panel.warm`; inherited ink token is unsuitable after Atelier recoloring. Set explicit dark text/label/heading tokens for every learner warm panel and audit focus/error/help copy there. Recheck 360/390/768/1440, including typed form and error state. Course-specific repair did not fix the shared defect.

**AD2-03 — required onboarding composition correction.** `onboarding-welcome-1440-viewport.png` keeps three global navigation destinations; mobile `interests-360.png` and `pace-390.png` retain a fixed bottom nav across the form. At the initial 360 viewport, the save action begins beneath that unrelated bar; users can scroll, so this is not a claim of a permanently unreachable button. Use the already specified focused onboarding shell: brand, help and sign-out; Back/Skip/Next in the flow, no global bottom nav. Reduce mobile top whitespace and provide a concise persistent step indication without adding a questionnaire sidebar. Recheck initial viewport and scroll-to-focused Next, including short screens and native 200% zoom.

**AD2-04 — required recovery action layout.** `challenge-1440-viewport.png`: «Выбрать доступный урок →Вернуться к навыку →» is one visually concatenated line. Give the first recovery one primary button and the second a separate secondary link in a wrapping action group, gap >=12px and mobile targets >=44px. Diagnostic unavailable is materially clearer; do not call its empty inventory a completed assessment. Check the destination retains actual node context when provided.

**AD2-05 — blocking first-value gap, joint content/backend.** A beginner with coding/content interests and ten minutes reaches «Границы и разрешения агента», while catalogue calls that course advanced (`discover-390-viewport.png`). The fallback disclaimer is honest but does not fulfill an appropriate first activity. Lesson heading «Разбираемся на примере» precedes generic instructions with no example (`lesson-1440-viewport.png`). Coordinate an approved beginner fallback and exact worked example, attempt, comparison and revision flow. Preserve semantic distinction: saving is not understanding. Return should resume this actual work, not promote an unrelated first foundations lesson (`return-390-viewport.png`). Existing backend QA-03/L04 remains blocking; do not fix only the copy.

**AD2-06 — supporting-surface composition debt.** `preferences-1440-viewport.png` reuses an enormous onboarding headline, large blank middle band, narrow choice tiles and a detached diagnostic link. Give returning account preferences a modest page title, grouped fields, visible current values, one clear save action and optional diagnostic availability. Align interest naming across onboarding/map/preferences. This is full-product work after the immediate slice blockers; not permission to hold up AD2-01/02 for speculative redesign.

## Exact authored content candidate

`worked-example-candidate.md`, SHA256 `38ae678413b0d106a78e76a3027319567e1462ee2485f6016921c687a5b83d7d`, is a rights-clear fictional source, task, comparison and self-check with responsive placement/save-state instructions. It deliberately labels an inferred next step rather than pretending it is a source fact. Independent learning reviewer must approve these exact bytes and lesson mapping before any publication. It belongs to a foundations source-verification lesson, not automatically to the agent permissions lesson. No assessment score or claimed mastery.

## Recheck limits

Native 200% zoom, exhaustive keyboard/focus, all graph branches/list/search, real video playback, approved available challenge/partial feedback, expired/forbidden access, saved favorites, account recovery, long-absence continuation and exact staging review remain open. Current gallery proves selected states only. No external health request was made under this turn's localhost-only probe constraint. Sole deployment ownership stays with manager. Material findings above prevent acceptance even though API calls and layout overflow checks pass.
