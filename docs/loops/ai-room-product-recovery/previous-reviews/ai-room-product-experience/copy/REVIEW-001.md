# Russian copy review 001 — needs_work

2026-10-04, ux_writer. Read current brief in full, manager direction 002 and historical references. Own only deliverables/copy/; no repository edits or service/deployment changes. Delivered ru-RU.json: 193 proposed strings with semantic and integration conditions. This is an expert/simulated evaluation, not a human usability study. Copy proposals are ready for integration; product acceptance is not granted.

## Actual inspection

Pending source `/home/claude/ai-room-pending-review`, git HEAD independently verified `bc4ba3c1f2eed39e42f611836d6990acf7b0a62d`. Chromium 153.0.8010.12; actual local HTTP app `http://127.0.0.1:18749`, disposable `/tmp/ux-copy-*` database. New ordinary seeded learner with no saved interests, practice or evidence; generated password never recorded. Ordinary synthetic seed + skill seed, no private approved forms. Graph `tree-2026-10-v1`, canonical response SHA256 `c19c98cef4c00cce21f36c796f2c8732b7229557b56da9546d786a7308a76553`. This is not the staged publication manifest. Server ended naturally after inspection.

Actually signed in, selected two interests, advanced, refreshed, opened map/preferences/lesson/profile/help/challenge/error, saved nonempty practice through the UI and independently fetched saved content. Every API called by these observed pages returned 200 with real JSON: GET graph, me, node basic-ai.limitations; POST and GET foundations-start-02/practice. Node had zero available assessments: transport succeeds but challenge journey fails. HTML pages returned 200; deliberately nonexistent /missing-copy-audit returned expected 404. No endpoint mock. `browser-evidence.json` retains responses, page text and JSON bodies. Help submission and access-recovery workflow were not exercised; help page was loaded only.

Captured full-page and viewport PNGs. Personally opened login/fresh map at 1440×1000; interests at 360/390/768×844 and 1440×1000; pace/interrupted/profile/challenge/help/error at 390×844; lesson and saved-result full pages at width390. Inspected all named evidence below. Full-page lesson is long; screenshot fixed-navigation overlays alone do not establish inaccessible content. No acceptance inferred for 200% zoom, keyboard, reduced motion, offline, paid/expired states, real assessed results, long-content variants, final selected direction or staging. Proposed new text is NOT yet rendered and tested.

## Findings requiring changes

| ID | Observed evidence | Copy and interaction correction |
|---|---|---|
| C01 blocking | `fresh-home-1440-viewport.png`: first login opens map, small «Найти своё начало» and generic «Продолжить урок» even with no prior activity. | Automatic welcome; one «Подобрать начало» action. Start vs continue must depend on actual history. Copy alone cannot repair routing. |
| C02 blocking | `pace-390-viewport.png` then `interrupted-390-viewport.png`: refresh loses both selected interests and returns to first step; checked_after_refresh=0. | Persist each completed step before claiming «Ответы сохранены». Resume from acknowledged server state, retain choices on failed save. |
| C03 blocking | `challenge-390-viewport.png`: named topic, «Выберите проверку на карте навыков», «Повторить загрузку», despite successful node response with no checks. | «Для этой темы пока нет проверки» + actual return-to-topic or permitted lesson. Network failure uses distinct retry text. Empty inventory is not completed/failed assessment. |
| C04 material hierarchy | `profile-390-viewport.png`: «пространство роста», repeated «подтверждённые»/«свидетельства», no saved-work-first structure. | «Моё обучение», latest work first, evidence explanation in disclosure. Preserve evidence semantics while simplifying terminology. Recheck after first save, partial result and application-only evidence. |
| C05 material beginner clarity | `interests-360-viewport.png`: «Кодинг с AI», «AI-команды», unexplained «Агенты»; next action below viewport while skip prominent. | Russian labels and concise descriptions; reduce repeated instructions. Engineer/art director must allocate room for «Программирование с ИИ» without truncation and keep progression discoverable. |
| C06 material access clarity | `login-1440-viewport.png`: anonymous first entry says «С возвращением», «Продолжим с того же места», «хранятся на сервере», «владелец среды», future recovery promise. | Neutral «Войти в AI Room»; explain saved work benefit; remove roadmap promises. Honest invitation-based fallback is interim only: working recovery remains an acceptance gap. |
| C07 improve with first-result journey | `saved-result-390.png`: actual saved text and timestamp, explicit no curator review; no response-specific feedback. | Preserve honest save, add reopen action and approved self-comparison when available. «Работа сохранена» never implies passed assessment. Do not invent grading or tutor. |
| C08 minor wording | `missing-390-viewport.png`: helpful recovery exists, but generic «К бесплатным урокам» link needs actual filtered destination to justify label. `help-390-viewport.png`: question storage is honest. | Use «Открыть библиотеку» for unfiltered library; keep help storage wording, disclose no reply workflow. Do not promise notifications. |

Useful existing behavior: two interests can be selected; unknown evidence differs from confirmed understanding/application; practice storage truly persists nonempty work; practice and lesson completion are separate. Keep synthetic teaching labels, but remove platform implementation narrative from ordinary learner copy. Current sample content remains a fixture, not approved teaching publication.

## Engineer handoff

Integrate names consistently in navigation, onboarding, graph/list/detail/search, lesson, profile and accessibility labels without changing stable IDs. `branches` keys are copy keys, not a migration. Check AI Teams semantics with learning owner. Keep access eligibility separate from readiness. Use a single term «Карта навыков»; «дерево» may describe structure internally. Replace «свидетельства» with «На чём основан результат». Use «ИИ» in Russian sentences, retain AI Room and tool names. Course/content title edits need content ownership, not blind replacement.

Onboarding order: welcome → optional multiple interests → experience/time → optional available diagnostic → named permitted first activity. Welcome skip must work at every point. Profile edit uses distinct title and must not reset learning. Proposed 3 experience options and time preference need agreed persistence contract; current two options/weekly goal cannot be silently repurposed. Optional weekly goal is separate from time available now. Step labels use actual flow length rather than fabricated fixed count.

First task narrative: say what learner will make, give approved example/instructions, invite a small attempt, show specific reviewed feedback or explicitly self-comparison, save, acknowledge actual save, link back to work and offer one next activity. Current text practice can store output, but first result and feedback are incomplete. Learning designer owns example/source/rubric approval. No proposed content publication here.

Return copy names the actual unfinished work across branches. After completion use «Вы завершили: {activity_title}» and real next option. After a break offer continuation/another topic with no missed-days count, guilt, lost streak, fabricated urgency or fixed daily obligation. Optional review requires real reviewed material. Never claim retention uplift.

## Long Russian text and state acceptance fixtures — unverified until rendered

- Title: «Как проверить ответ ИИ, если исходные документы противоречат друг другу». Show complete title in course, lesson and detail; cards may truncate only with accessible full title. Buttons may wrap; no tiny-font workaround.
- Branch: «Программирование с ИИ»; one-word node «Многопользовательский»; learner name «Александра-Екатерина». Test 360/390/768/1440 and 200% zoom, including selected and keyboard focus states.
- Resume button with the long lesson title above; 3-digit count; zero denominator; missing title. Use «Эта тема» fallback, never raw node IDs.
- Russian quantities: 1 урок, 2 урока, 5 уроков, 11 уроков, 21 урок, 22 урока, 25 уроков. Use locale pluralization or noun-before-count «Подтверждено навыков: 2 из 18». Avoid naive suffix concatenation.
- Error «Работа не сохранена. Текст остался в поле — попробуйте ещё раз» only if textarea survives. Expired session needs preserved draft or explicit loss warning before login. No blanket «всё сохранено».
- Test no-checks, loading, failed fetch, assessed-unconfirmed, no assessment, pending review and reviewed application as distinct states. A saved lesson exercise must not show pending-review unless it actually entered the review workflow.

## Research trace and remaining gate

Used colleague's documented research register `../research/RESEARCH-DECISIONS.md` as input, not as my independent external-product inspection. D01 informs obvious start and short optional steps; D03 unknown/evidence distinction; D04 saved artifact separate from assessed work; D07 nonpunitive return; D08 explanatory feedback. No new causal/retention claim or copied marketing promise. Direct evidence this turn is the actual app/code and opened screenshots above.

Next review requires integrated strings on exact candidate and approved content manifest: genuinely fresh auto-onboarding, intermediate save/refresh/logout, skip and existing edit, two interests, permitted first activity, saved/reopened work, actual partial/unknown/source feedback, recovery endpoints and return. Then independent staged recheck. New copy, long variants, and unexercised states remain unverified. Verdict needs_work, not minor_only.
