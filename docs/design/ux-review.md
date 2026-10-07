# AI Room — UI/UX review (2026-10-05)

Scope: every learner-facing page, desktop 1440×900 and mobile 390×844, light theme (Мастерская) and dark theme (Ночной лес), as an anonymous visitor and as a free learner with real progress (one completed lesson, one saved draft, three started courses).

Severity: **P1** broken or blocks a task · **P2** confusing or inconsistent · **P3** polish.

## Cross-cutting

| # | Sev | Finding | Fix |
|---|---|---|---|
| G1 | P1 | On mobile the header wraps to two rows ("Тема" picker + Помощь + Выйти), eating ~80px on every page. | One-row header; theme picker becomes a compact icon control. |
| G2 | P1 | Old pages from earlier iterations are still reachable and dead-end: `/practice` ("задания ещё готовятся"), `/challenges` ("Проверка пока не выбрана"), `/diagnostic` (unreviewed assessments, old 5-branch taxonomy), `/routes` (routes over archived synthetic courses, "Основы AI · 37 шагов"). | Redirect to the current equivalents; remove links into them. |
| G3 | P1 | Dark themes: coral CTA buttons sit on mint/blue accent panels (paywall, membership) — clashing and low-contrast. | Buttons on accent panels use the inverse style. |
| G4 | P2 | Three taxonomies at once: map uses Основы ИИ / Код / Контент / Агенты; library cards use "Агенты и автоматизация / Создание с AI / Основы AI"; preferences and diagnostic use "Кодинг с AI / AI-команды / Автоматизация". "AI" vs "ИИ" mixed. | One taxonomy (the map's four topics) everywhere. |
| G5 | P2 | Lesson counts disagree: map says Claude с 0 до PRO has 37 lessons; library and course page say "3 урока". Course outline shows 2 of 9 modules. | Show "N из M открыто" and the full outline with "скоро" lessons, from the same catalogue as the map. |
| G6 | P2 | No "you are here" state in the main navigation. | Highlight the current section. |
| G7 | P2 | Raw timestamps: "Последнее сохранение: 2026-10-05 19:52:28 UTC". | Human dates: "сегодня в 22:52", "вчера", "3 окт". |
| G8 | P3 | Same cube illustration on welcome, login and all onboarding steps; in dark themes it is a bright cream block. | Tone it down in dark themes; drop it where it adds nothing. |
| G9 | P3 | Naming: nav says "Библиотека", breadcrumb says "← Каталог". | Use "Библиотека". |

## Pages

### Welcome (anonymous `/`)
- P2 Says nothing concrete about what's inside: no topics, courses or free lessons — just a slogan and a cube.
- P2 The main CTA "Найти своё начало" goes to an invite-only login; the honest primary action for a visitor is "try a free lesson / look at the map".
- P3 Desktop page is short with small body copy; the three "principles" are tiny.

### Login
- OK. P3 cube art; error/forgot-password guidance is fine.

### Onboarding (4 steps)
- P2 "Сохранено в аккаунте." appears before the learner has done anything.
- P2 Progress is plain text "Шаг 2 из 4" — no visual progress.
- P2 Step 4: the recommended lesson is a bare heading above a sentence — not a card, no course/length/why at a glance.
- P3 Three similar-weight buttons (Сохранить / Назад / Пропустить); "Назад" and "Пропустить" should be quieter.
- P3 Right half is the same cube on every step.

### Map
- Desktop is good after the tree work. P2 on mobile the header + title + tools + resume strip leave half the screen for the canvas (G1 fixes most of it).

### Library (`/catalogue`)
- P2 Shows only 3 courses while the map shows 8; nothing tells a visitor that ChatGPT, Вайбкодинг, ИИ-контент, Hermes exist (G5).
- P2 Card labels use the old taxonomy (G4); "Начальный · 50 мин · 3 урока" undercounts real courses.

### Course page
- P2 "Синтетическая учебная программа" — false now; the content is real.
- P2 "Начать курс →" even when the learner already has progress/draft in it.
- P2 Outline lists only imported modules (G5); "3 урока · 40 минут" for a 37-lesson course.
- P3 No way to jump to the course on the map.

### Lesson
- P1 Very long (≈9,000px desktop / 13,000px mobile) with no in-lesson navigation; the 6 steps are only discoverable by scrolling.
- P2 Ending has three competing decisions in two boxes: "Сохранить черновик", "Сохранить результат", then a separate "Готовы отметить свой шаг? → Отметить завершённым".
- P2 "Материалы → Чек-лист проверки результата (TXT)" duplicates the checklist already shown in the practice box.
- P2 Course outline sidebar only lists imported lessons (G5); on mobile it sits above the lesson title.
- P3 Raw save timestamp (G7). Images have no reserved space, so text jumps as they load.

### Paywall
- P1 Bug: the free-lesson link at the bottom of the offer ("Пока можно пройти бесплатный урок этого курса: …") is invisible — link colour equals the panel colour.
- P1 Dark themes: CTA colour clash (G3).

### Club (`/membership`)
- P3 Thin page; dark-theme clash (G3).

### Моё обучение
- P2 Weekly goal copy is technical ("Впервые завершено за последние 7 дней… Повторные отметки не добавляют счёт. Это история первых завершений…").
- P2 A course whose next lesson is club-only shows a bare "Открыть" with no explanation.
- P3 Raw timestamps (G7); no active nav state (G6).

### Preferences (`/preferences`, linked from "Изменить цель и темп")
- P1 Old interests questionnaire with the old 5-branch taxonomy, no main navigation, cramped two-column checkboxes, and a link to the unreviewed diagnostic. Duplicates onboarding.

### Help
- P3 "Сохранить вопрос" should read as sending; empty space in the quick-answers box. Otherwise fine.

### 404
- OK.

## Fix order
1. P1 bugs and dead ends: paywall link, dark CTA clash, mobile header, legacy pages, preferences page.
2. Consistency: one taxonomy, honest counts and full outlines from the catalogue, naming, active nav, human dates.
3. Lesson page: in-lesson step navigation, single clear ending, no duplicate materials, outline placement on mobile.
4. Onboarding and welcome: progress, recommendation card, quieter secondary actions, concrete welcome content.

## Status after fixes (same day)

| Finding | Status |
|---|---|
| G1 mobile header on two rows | Fixed — one row; theme picker moves to the footer on phones |
| G2 dead-end legacy pages | Fixed — `/practice`, `/challenges`, `/diagnostic`, `/routes` redirect to current pages; APIs untouched |
| G3 coral-on-mint in dark themes | Fixed — buttons on accent panels use the inverse style |
| G4 three taxonomies | Fixed for learner pages — library, course page and onboarding use the map's four topics; levels use the filter words |
| G5 counts and outlines disagree | Fixed — "Открыто 3 из 37 уроков", full outline with «Скоро» on course page, lesson sidebar and paywall; library lists upcoming courses |
| G6 no active nav | Fixed |
| G7 raw timestamps | Fixed — "сегодня в 22:52", localised in the browser |
| G8 cube everywhere | Partly — shown only on the first onboarding step; dimmed on dark themes |
| G9 Каталог vs Библиотека | Fixed |
| Welcome page | Fixed — topics with real counts, free lessons, primary action "Попробовать бесплатный урок" |
| Onboarding | Fixed — progress bar, no premature "Сохранено", recommendation card, quieter Назад/Пропустить |
| Lesson page | Fixed — "В этом уроке" step list (sidebar on desktop, collapsible on phones), outline below lesson on phones, single primary ending, no duplicate TXT checklist, reserved image space |
| Paywall link invisible | Fixed |
| Моё обучение | Fixed — plain weekly-goal copy, locked next lesson explained with "Открыть доступ" |
| Preferences page | Fixed — simple "Настройки обучения" (опыт, недельная цель) + link to edit interests |
| Help button wording | Not changed — pinned by an access-help test; low value |
| Content references "Урок 1", "Модуль 2" in imported lesson 6 | Open — editorial decision for the content owner |
