# Personal path («Мой путь») and onboarding v2 — state and plan

Branch `claude/fresh-platform-polish` (based on `origin/education/fresh-platform`), worktree
`.claude/worktrees/product-experience-handoff-b83046`. Nothing pushed or deployed since `415a1e2` on staging.

## What the user asked for (agreed design)
- Onboarding replaced entirely (old v1 is gone; nobody went through it).
  1. **Hello**: «Давай познакомимся и сделаем твой путь персональным» + a description (answers saved to the profile,
     shape recommendations and goals, changeable in settings). Nothing else on the page.
  2. **Goals**: 10 *big* goals (not small tasks), pick up to 3, with the hint «лучше выбрать близкие, даже не на 100%».
     Plus a free-text own goal: saved only; trying to analyse it shows «Нужна подписка для анализа» (402 hook).
  3. **«Строим твой путь»** loading screen (min ~3.2 s) while the path is computed.
  4. **Level + deadlines** with a preview of the path (round mini-map SVG with coloured goal lines):
     level «Только начинаю / Иногда / В работе / Проекты»; anything above beginner opens 0–5 sliders
     (chats, sites/services, automations/agents, images/video); deadline per goal (месяц/3 мес/полгода/год).
  5. **Schedule**: 3 plans (Лёгкий 2×20, Ровный 4×30, Интенсив 6×45 мин/нед) + «Свой темп» sliders, each showing
     when every goal is reached vs its deadline; then «Добавить в календарь» (existing /api/app/plan + .ics/Google).
  6. Then **«Мой путь»** (`/path`): the real skill map with each goal as a coloured path (toggle on/off) and a time
     slider (today → months ahead) showing what will be done and each goal's % at that date.
- Skills: 8 skills, 0–100 points; every lesson (also «скоро» ones) adds synthetic points. Goals = target points.
- Next (not started, user said «later»): a **new main page**.

## What is built (uncommitted at time of writing → committed as WIP, see git log)
- `scripts/make_skill_model.py` → `club/content/skills.json`: 8 skills, 10 goals (targets), hand-written module
  profiles → per-lesson points (scaled so each skill offers ~125), synthetic planned modules for the DB courses
  `ai-agents-start` and `ai-video` (in skills.json only; NOT yet in catalog/map — see TODO), `requires`
  (vibecoding-pro needs vibecoding 30; hermes needs automation 15). Lesson key = `course:moduleIndex:lessonIndex`.
- `club/paths.py`: `build_path(goals, levels, deadlines, minutes)` (goals by deadline; courses by what they offer
  the goal; a lesson is taken if it adds to a lacking skill above the learner's level; prerequisites from the course
  teaching that skill most; shared lessons credited to all goals), `progress`, `timeline`, `at_week`, `plans`.
- `club/journey.py`: table `personal_paths(user_id, body JSON, status new/draft/done/skipped)`;
  `GET /api/app/journey`, `POST /api/app/journey/preview`, `PUT /api/app/journey`, `GET /api/app/journey/custom`
  (402 «Нужна подписка для анализа»), `GET /path` (SPA). Summary includes map outline, goals (colour, modules
  `course:index`, targets), lessons (real titles/urls/states from the tree), plans, pace result.
- `club/onboarding.py` rewritten: only the gate (learners not finished → `/onboarding`; deep links to lessons/courses
  still open), login destination, no-op `init-onboarding` CLI. Seeded accounts are created `onboarding_done=1`.
- Frontend: `web/src/journey.ts` (types), `web/src/pages/Onboarding.tsx` (all steps), `web/src/components/PathPreview.tsx`
  (mini round map), `web/src/pages/MyPath.tsx` (/path: SkillMap + overlay + time slider + goal toggles + custom-goal
  paywall chip), `web/src/journey.css`. `SkillMap` got `title`, `decorate`, `children` props; `engine.js` tags
  `data-module="course:index"`, `data-course`, `data-topic` on nodes and edges. «Мои курсы» menu links «Мой путь».
- Tests: `tests/test_paths.py` (4), `tests/test_onboarding.py` rewritten (4), `tests/test_legacy_content.py`
  recommendation test replaced by a path test. Last full run before the frontend work: 237 passed + those fixed.
- Walkthrough script (scratchpad, not in repo): `journey_walk.py OUT theme` — fresh learner through every screen.

## Walkthrough fixes (done, uncommitted on top of the WIP commit)
«Мой путь» panel on its own full-width row; goal colours strong on modules and edges (`--goal-ink` keeps lime readable
on the light map); the map opens on the first course of the path (`SkillMap focus` → `mountTree(..., {focus})`);
time slider looks ≥ 6 months ahead with month labels, a flag per goal and each goal's finish date; header nav hidden
during onboarding; building screen bars are the 8 named skills sized by the chosen goals' targets; calendar time
select inline; mini-map names placed outward, topic names on their junctions, off-path courses faint, lines outlined;
late plans say «позже срока» in muted text (the club palette's gold-ink is green).

## Round 2 (done, uncommitted)
- Onboarding: every step on a glass card (no text straight on the sky); goals are a ring carousel
  (`components/GoalRing.tsx`); skills drawn as a radar (`components/SkillRadar.tsx`) on the building screen (goal
  shapes grow in) and on the level step (goal shapes + «ты сейчас» following the sliders). PathPreview removed.
- «Мой путь»: map and plan side by side, «Карта»/«План» fold either away (one at a time under 900px); the plan is a
  metro line (`components/PathPlan.tsx`): station = module, a rail per goal, interchange = module serving several
  goals, a goal's rail ends at its finish, dates from the pace, «К <date> — здесь» marker from the slider, next lesson
  on top; clicking a station flies the map to it (`tree:module` event). Map opens framed on the first stretch of the
  path (`frame` option); off-path parts stay visible (opacity .6).
- Quick check: `build_path(..., include)` + `assumed` (lessons the level skips before a lesson the path takes in the
  same course); answers `check: {module_key: known|learn}`; «Пройти» puts those lessons first; known modules get a
  dashed «знаешь ✓» on the map.

## Round 4 (done, uncommitted) — current «Мой путь»
- The map is the page: fixed under the header, edge to edge, the normal radial layout with milestones
  (compact mode and the metro scheme were tried and rejected). Engine options `fill`, `course` (open framed on that
  course's whole branch), `inset()` (pixels a panel covers on the right); event `tree:course` frames a branch.
- The plan floats on the right (400px glass panel); it folds into a slim timeline (no text): goal rails ending at
  their goals, month ticks, a knob at the date; click/drag/arrow keys move through time. Phone: bottom sheet.
- The plan lists lessons under module headers (dates per lesson, rails with dots per goal); goals are small chips
  with % in the sticky head; «Ты, вероятно, уже знаешь» then «Ты изучишь»; pace at the end.
- Time = plan scroll (lesson crossing 40% of the panel); the camera frames the branch of the course being read.

## Real course structure (2026-10-09)
- catalog.json now mirrors the logged-in app.airoom.club exactly for its 6 active courses (titles, levels, module
  titles, every lesson, minutes per lesson; a range → its middle); the archived Hermes course is left out.
  Lessons are `{"title", "minutes"}` (coming) or `{"id", "minutes"}` (on this platform). The two imported Claude
  modules in legacy_content.py were renamed to the full titles so the admin's module matching still works.
- The invented «planned» modules for ai-video / ai-agents-start were removed from scripts/make_skill_model.py
  (only skill *points* are synthetic). skills.json regenerated: 192 lessons (187 real + 5 in our two demo courses).
- Open question for the owner: keep the demo courses «Видео с ИИ-агентом» and «Первый ИИ-агент» (made from free
  guides + labelled demo lessons for the paywall) on the map, or drop them; and how to bring in guides, use cases
  and workshops.

## Guides, goals everywhere (2026-10-09)
- The two demo courses (ai-video, ai-agents-start) are gone: their source guides (chatcut-video-editing,
  what-is-ai-agent) moved to content/legacy/materials as guides; install() archives the courses (RETIRED).
  The rank test builds its own small admin-style course.
- Guides/use cases are side stops: make_skill_model.py gives each a small profile (MATERIAL_PROFILES, else its
  branch's) → `materials` in skills.json with `near` (best-fitting module); journey summary `guides` = those that
  train a goal's skill, placed at that module (or the course's first path module). Shown dashed in the plan
  («по желанию») and as a «＋ гайд» chip on map modules. They don't move goal progress. Workshops never.
- Map follows a module with one neighbour each side at ≥ 85% zoom (lessons listed).
- Goals across the platform: journey.alignment(query, user) → goals + per course/lesson/material goal ids;
  Discover/search items carry `goals`, a «Для твоих целей» shelf; cards/hero show colour dots (GoalMarks).
- Waiting on the owner's login: read the app's guides, use cases and workshops lists (titles, length, topic;
  free bodies only) to import them; workshops go to Обзор only.

## Guides, use cases, workshops from the app (2026-10-09)
- Free guides imported in full into content/legacy/materials (codex-for-beginners, claude-code-tokens,
  youtube-researcher-agent, site-in-one-evening, language-tutor) with the old club's promotion removed, as before.
  «Регистрация и оплата Claude / ChatGPT из РФ» is NOT imported (region-restriction and KYC workarounds).
- Club-only guides (37), use cases (15) and workshops (2): club/content/club_materials.json — only what a visitor
  without a subscription sees (title, topic, level, one line; workshops: programme, length). Installed as member
  materials flagged material_profiles.club_only; their page links to the original; length hidden when unknown.
  Vibecoding guides the app files under «Основы»/Claude are under «Код» here.
- All of them get skill profiles (club ones from topic + title keywords) and can be side stops (max 3 per module,
  free first); workshops only in Обзор. «Для твоих целей» repeats items (doesn't empty the rows below).

## Round 5 (2026-10-09): shared goals, guide islands, Главная, the map is the path

- Shared goals on the map: a module on several goals' paths gets a band and border striped in all their colours
  and a «2 цели» chip; a lesson's dot is ringed in the colours of the goals it serves (split ring); the branch
  carries one parallel line per goal on a dark track (engine.js `lanes`, from the edge's `data-lanes`).
  Lessons of a path module that the path doesn't take recede.
- Guides and use cases are islands beside their module (engine option `islands`), on a dotted line: up to
  three, alternating sides of the arm; framing a module includes its islands; dimmed when their goals are hidden.
- Главная (`/` signed in, pages/Dashboard.tsx): the lesson to jump into (unfinished → first open on the path →
  server's next), the next five steps with dates and goal dots, goal progress now + date reached, radar,
  guides along the way, courses in progress, a card to the map. Without goals: an invitation to onboarding.
  Visitors keep the welcome page. Skipping onboarding lands here.
- The map is «Мой путь»: `/map` renders the same page (plain map + invitation without goals, also for
  visitors); nav: Главная · Мой путь (Карта навыков for visitors) · Обзор · Мои курсы.

## Next steps after fixes
- Settings: «Цели и путь» section (change goals/level/deadlines/pace without redoing onboarding).
- Update README (onboarding v2, skill model, paths), run full tests + `scripts/check_admin_browser.py`, commit.

## Constraints to remember
- Local preview: `club` launch config (port 8098); seed password in `instance/local-seed-password.txt` (user asked
  for it once; shared by learner/member/editor/admin @example.test).
- Don't commit `HANDOFF.md`, `docs/design/*.png`, `docs/.DS_Store`; `handoff.md` shows deleted (case clash) — leave it.
- User's local HANDOFF edits are in stash `handoff-local-edits-b83046-20261009`.
- Staging deploy procedure: build release tarball with `COPYFILE_DISABLE=1` (macOS `._*` files broke install),
  rehearse install on a DB copy, then switch (scratchpad `deploy-415a1e2.py` pattern); only when the user asks.
