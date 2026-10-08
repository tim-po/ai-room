# AI Room — retention research and ideas (2026-10-06)

Question: what should the product do around the lessons so that learning with AI Room is engaging, enjoyable, and something people come back to? Focus: library, courses and lessons; the skill map is supporting.

Constraints:
- Lesson content is out of scope. Everything around it is in scope: navigation, progress, the practice UI, completion, reminders, the library, course pages, the profile and the club.
- Staging has no real learners. Nothing here can be validated yet, so every idea is a hypothesis and the first job is to measure.
- Lessons run 10–20 minutes and the audience is Russian-speaking adults.
- Free lessons come first, then the paid club.
- There is no way to reach a learner between visits: no email, no Telegram, no push notifications.
- AI feedback that calls a provider is not approved (handoff gap 7).

## TL;DR — five bets

_Status 2026-10-06: bets 1, 3 and 4 are built (see README › Learning loop). Bets 2 and 5 are parked._

1. **Give each lesson a finish line.** Show progress through the lesson's steps, reopen at the step where the learner stopped, and end with a real finish moment that pulls them into the next lesson.
2. **A weekly rhythm instead of a daily streak.** The default goal is 1 lesson a week, a missed week can be paused for free, and the rhythm is visible on the map. Duolingo's data says a low barrier matters more than volume.
3. **A plan the learner chooses, plus a calendar.** "How will you study?" → pick days → a `.ics` file whose events open the next lesson. This gives us a reminder channel without any infrastructure; a Telegram bot comes later.
4. **A return briefing.** After a few days away: where you stopped, a 3-line recap of the lesson, your last saved work, and one button.
5. **Personal prompt library.** Every prompt in a lesson can be saved to "Мои промпты". It's a practical reason to come back that doesn't depend on willpower.

Measure first. Return should count only meaningful actions, never page views (handoff gap 4).

## 1. What retention means here

| Metric | Definition | Why |
|---|---|---|
| Activation | In the first session, the learner saves practice or finishes a lesson. | Tests whether the first useful result happened. |
| Meaningful return (D1/D7/D30) | A later day with a meaningful action: reached a new step, saved practice, completed a lesson. | Today `meaningful_return` fires on a passive lesson visit, which needs fixing. |
| Weekly active learners | Learners with a meaningful action this calendar week. | Our north star: with 10–20-minute lessons, weekly is the natural rhythm. |
| Course momentum | Share of started courses with ≥3 lessons done within 30 days. | Library and course-page health. |
| Club conversion | Free → member, plus member retention by week. | The business outcome. |

What we record today:
- `lesson_started`
- `lesson_completed`
- `practice_saved` and `practice_submitted`
- `onboarding_completed`
- `meaningful_return`, which is misdefined

What's missing: step reached, prompt copied or saved, plan created, calendar downloaded, return session and finish screen shown.

## 2. Audit — the loop as it is today

The habit loop for a learning product: **trigger** (between visits) → **start a session** → **choose** → **in the lesson** → **finish and reward** → **investment** (something saved that makes coming back worth it) → the next trigger.

| Stage | What exists | Gap |
|---|---|---|
| Trigger | Nothing. | **The biggest gap.** No email, Telegram or calendar, so the learner has to remember on their own. |
| Session start | "Продолжить" strip on the map, "Продолжить урок" in Моё обучение. | Opens the lesson at the top, not where you stopped. No recap after a break. |
| Choose | A map with full overview; a library with filters; course outlines. | Nothing "for you" from the onboarding interests, no "short" or "new" view, no time to finish, no plan. |
| In the lesson | Contents with the active step, video resume, copy buttons on prompts, practice saved to the account. | No sense of how far through the lesson you are, no checkpoints, and prompts can't be kept. The practice checklist is plain text. |
| Finish | An "Отметить завершённым" panel at the bottom, plus a small next-lesson link. | No moment of accomplishment and no pull into what's next. Completion is a manual toggle that's easy to miss. |
| Investment | Мои работы, favourites, a weekly goal (rolling 7 days, default 2, only visible in Моё обучение). | The goal is hidden and higher than it should be. Saved work is never brought back. |
| Identity | Map node states, course progress bars. | Nothing says "what I can do now". A finished course has no ending. |
| Social | None; "Клуб" is just the paywall. | No sense that anyone else is learning. |

## 3. What the evidence says

| # | Finding | Implication for us |
|---|---|---|
| E1 | Duolingo separated the streak from the daily goal so that a single lesson keeps the streak. Day-14 retention rose 3.3%, and learners on 7+ day streaks went from about a third to over half. Learners with "intense" goals were the least likely to keep a streak. [Duolingo blog](https://blog.duolingo.com/improving-the-streak) | Keep the barrier low: default goal 1 lesson a week. Make the streak unit achievable with 10–20-minute lessons, which means weekly, not daily. |
| E2 | Choosing a streak goal improved retention even when the value wasn't used, and a "commit to my goal" button beat "continue". Streak Wager raised Day-7 retention by 14%. [Lazyweb summary of Duolingo experiments](https://lazyweb.com/research/duolingo-streak-goals-retention) | Let the learner choose a plan and word it as a commitment. |
| E3 | Duolingo's first big streak win was a notification sent when a streak was about to break. Learners with 10-day streaks rarely drop off. Leaderboards added 17% learning time. [Lenny's Newsletter](https://www.lennysnewsletter.com/p/how-duolingo-reignited-user-growth) | A reminder channel and something worth protecting are both needed, with forgiveness built in (a pause). |
| E4 | Six years of MIT/Harvard edX data (5.6 million learners): completion of self-paced courses stayed low and didn't improve, and most learners never returned after their first year. [The MOOC Pivot, Science 2019](https://tsl.mit.edu/research/the-mooc-pivot/). Secondary reports claim fixed-schedule and cohort courses complete 2–3× more often (e.g. 45% vs 13%); treat that as directional, since the source is an aggregator. [Overview](https://donnatech.it.com/understanding-the-persistent-low-completion-rates-of-moocs) | Self-paced alone won't do. Offer optional cohorts ("потоки") with start dates, and measure it ourselves. |
| E5 | Fresh-start effect: motivation spikes after temporal landmarks such as Mondays and new months. [APS](https://www.psychologicalscience.org/news/minds-business/why-monday-is-the-best-day-for-setting-new-goals.html) | Start plans and cohorts on Mondays; invite people back at the start of a week. |
| E6 | Spaced retrieval beats massed practice (g ≈ 0.74), and spaced online education beats massed, especially for practical skills. [Spaced practice overview](https://inspire.acu.edu.au/articles/spaced-practice) | Bring material back after a few days: the learner's own work and the lesson's steps, not only new lessons. |
| E7 | Yandex Praktikum: a sense that knowledge is growing predicts finishing a course, and type of motivation doesn't. Practical value, clarity and "warmth" drive recommendations. [Skillbox Media](https://skillbox.ru/media/edtech/4-vyvoda-yandeks-praktikuma-o-dokhodimosti-na-kurse-i-gotovnosti-ego-rekomendovat/) | Make growth and practical wins visible ("what you can do now", the portfolio). Keep the copy human. |
| E8 | Gamification has a small positive effect overall. Points, badges and leaderboards can hurt intrinsic motivation when they feel controlling, so autonomy matters. [Gamification and SDT](https://icenet.blog/2025/06/17/align-the-game-to-your-aim-considering-gamification-through-the-lens-of-self-determination-theory/). Duolingo's forced linear path drew a strong backlash. [NBC](https://www.nbcnews.com/tech/tech-news/duolingos-update-redesign-luis-von-ahn-interview-rcna44655) | Keep free choice on the map and recommend a next step without locking anything. No points for visits. Leaderboards late, if at all. |
| E9 | Brilliant opens each lesson with an open question (a curiosity gap) and uses short daily units; a few problems are enough to keep the streak. [Brilliant showcase](https://screensdesign.com/showcase/brilliant-learn-by-doing), [Brilliant help](https://brilliant.org/help/using-brilliant/what-is-a-streak) | End every lesson with a teaser for the next one, built from its objective. |
| E10 | Telegram is the main channel for Russian self-improvement audiences, and EdTech mini-apps report large gains in daily activity (one reported +48%). [Sostav](https://www.sostav.ru/blogs/280723/63040) | The reminder channel should eventually be a Telegram bot. A calendar file is the zero-infrastructure start. |
| E11 | Portfolio projects give learners something concrete to finish and show. [Codecademy](https://codecademy.com/resources/blog/portfolio-projects-in-career-paths/) | Turn Мои работы into a portfolio. |

## 4. Ideas

Effort: **S** = days · **M** = about a week · **L** = several weeks or new infrastructure.

### A. Measure first
| # | Idea | Why | Effort |
|---|---|---|---|
| A1 | Meaningful events (step reached, practice saved, completion, prompt saved, plan created) and a cohort dashboard: activation, D1/D7/D30 meaningful return, weekly active learners. Fix `meaningful_return`. | Nothing else can be judged without it. | S–M |
| A2 | Simple feature flags, so cohorts before and after each change can be compared. | Lets us run honest before/after comparisons. | S |

### B. Inside the lesson (around the content)
| # | Idea | Why | Effort |
|---|---|---|---|
| B1 | **Progress rail.** The lesson's steps already have anchors, so show them as checkpoints: "Шаг 3 из 6", filled as the learner reads, with an explicit "готово". It sits on the existing table of contents, with a sticky bar on phones. | Visible progress within the session (E7) and a finish line. | S |
| B2 | **Resume at your step.** Remember the last step reached, so "Продолжить" opens `#step-3` with "Вы остановились здесь". | Lowers the cost of re-entering after a break. | S |
| B3 | **Interactive self-check.** The lesson's checklist becomes tick boxes before saving practice; unticked items become "что доработать". | Feedback without AI; a sense of quality, not just "saved". | S |
| B4 | **Мои промпты.** A "★ Сохранить" button next to "Скопировать" on every prompt block, collected into a searchable tab in Моё обучение. | A practical reason to return; investment. | M |
| B5 | Personal notes per lesson ("заметка для себя"), shown again in the return briefing. | Writing it yourself aids memory; investment. | M |
| B6 | Practice starters: when the learner can't think of a task, offer example tasks for the topic ("возьмите пример"). The copy belongs to the topic UI, not to lessons. | Addresses the handoff's "novice must invent a task" problem. | S–M |

### C. Lesson finish
| # | Idea | Why | Effort |
|---|---|---|---|
| C1 | **Finish moment.** Once the last step is reached and practice saved (or "Завершить урок" is pressed), show a card: the steps done ✓, the saved result, this week's rhythm filling in, and the map node lighting up. | People remember the peak and the end; feeling of growth (E7). | S–M |
| C2 | **Next-lesson pull.** The finish card teases the next lesson (its objective and minutes) with "Начать сейчас" and "Запланировать". | Curiosity gap (E9). | S |
| C3 | Suggest completion automatically when the steps are reached and practice is saved; the manual toggle stays. | Completion stops being a hidden chore, and the progress data becomes accurate. | S |

### D. Between visits (triggers)
| # | Idea | Why | Effort |
|---|---|---|---|
| D1 | **Plan + calendar.** "Как будете учиться?": pick days and a time (default 1×/week, starting Monday) → a recurring `.ics` event whose link opens the next lesson. | Commitment (E2), planning when and where, fresh start (E5); no infrastructure needed. | S–M |
| D2 | `/continue`: a stable link that always resolves to the learner's best next step. | Powers D1, D3 and the briefing. | S |
| D3 | Opt-in Telegram bot: reminders at the planned times, a Sunday "keep your rhythm" nudge, new lessons, support replies. | The channel our audience actually uses (E10); the rhythm-save nudge (E3). | L |
| D4 | Weekly email digest, if email infrastructure ever appears. | A fallback channel. | M |

### E. Return visit
| # | Idea | Why | Effort |
|---|---|---|---|
| E1 | **Return briefing.** After 3 or more days away, a "С возвращением" card on the map and in Моё обучение: where you stopped (lesson and step), a 3-line recap (step titles), your last work or notes, one button. | Re-entry cost; spaced review (E6). | S |
| E2 | **Revisit your work.** 3–7 days after saving practice: "Вернитесь к работе: что бы вы улучшили сейчас?". Opens the previous text; saving keeps versions. | Spaced retrieval applied to the learner's own artifact (E6, E11). | M |
| E3 | Fresh-start invitation: on Monday or at the start of a month, if the rhythm has lapsed, "Новая неделя — один урок?". | E5. Shown only when useful, never as nagging. | S |

### F. Library and course pages
| # | Idea | Why | Effort |
|---|---|---|---|
| F1 | **Library rows for a returning learner:** "Продолжить", "Под ваши интересы" (from onboarding, which today is barely used), "Быстро: до 15 минут", "Новое в клубе", plus collections by job to be done ("Автоматизировать рутину", "Контент без монтажёра"). | Faster choice; personalization; a reason to look again. | M |
| F2 | **Outcome-first courses.** The card and course page say what you'll make, the time to finish at your pace ("≈3 недели по 1 уроку"), milestones per module, and your next lesson. | Practical value (E7). | S–M |
| F3 | "Начать с планом" on the course page, leading into D1 for that course. | Commitment at the moment of highest intent. | S (with D1) |
| F4 | **Course finale:** a completion card listing what you can now do, a shareable image, and the next course suggested. | Identity and an ending; a word-of-mouth loop. | M |
| F5 | "Новое с вашего прошлого визита" badges on courses, modules and the map. | Gives a reason to return; depends on how often content is added. | S |

### G. Progress and identity (map and Моё обучение)
| # | Idea | Why | Effort |
|---|---|---|---|
| G1 | **Weekly rhythm.** Replace the rolling weekly goal with calendar weeks. Default goal 1; a streak of weeks; one free pause a month; a chip in the header and on the map. | E1–E3, at our lesson length. | S–M |
| G2 | "Что вы теперь умеете": each completed module adds a capability line (from module titles) to Моё обучение and the map. | Feeling of growth (E7). | S |
| G3 | Map moments: a just-completed node lights up on the next visit; "следующие 3 шага" are suggested while everything stays open. | Autonomy plus guidance (E8). | S |
| G4 | Мои работы becomes a portfolio: versions, before/after, and an optional public link. | E11; gives learners something to show. | M–L |

### H. Club and social (needs real learners)
| # | Idea | Why | Effort |
|---|---|---|---|
| H1 | **Потоки:** 2-week sprints through existing lessons, starting on Mondays, with honest participant counts and finishing together. | Cohorts and deadlines (E4), fresh start (E5). | L |
| H2 | "Как сделали другие": an opt-in, moderated gallery of results per lesson. | Belonging, examples, social proof — only when real. | L |
| H3 | The Клуб page shows what's happening this week (new lessons, the current поток). | The club as a place, not a paywall. | M |

### I. AI feedback (gated)
| # | Idea | Why | Effort |
|---|---|---|---|
| I1 | AI review of practice against the lesson checklist, only after provider and spend approval. B3 is the non-AI step towards it. | The strongest learning loop, but blocked by gap 7. | L |

## 5. Scoring

Impact and confidence are rated 1–3; confidence comes from the evidence above, not from our own data.

| Idea | Impact | Confidence | Effort | Priority |
|---|---|---|---|---|
| A1 measurement | enabler | 3 | S–M | **Now** |
| B1+B2 progress rail and resume | 2 | 3 | S | **Now** |
| C1+C2(+C3) finish and next pull | 3 | 2 | S–M | **Now** |
| G1 weekly rhythm | 3 | 3 | S–M | **Now** |
| D1+D2 plan, calendar, `/continue` | 3 | 2 | S–M | **Now** |
| E1 return briefing | 2 | 2 | S | **Now** |
| B4 Мои промпты | 2 | 2 | M | Next |
| F1 library rows | 2 | 2 | M | Next |
| F2+F3 outcome-first course and plan | 2 | 2 | S–M | Next |
| B3 self-check | 2 | 2 | S | Next |
| E2 revisit your work | 2 | 3 | M | Next |
| G2 "что вы умеете" | 1 | 2 | S | Next |
| D3 Telegram bot | 3 | 2 | L | Later (infrastructure) |
| H1 потоки | 3 | 2 | L | Later (needs learners) |
| F4 course finale | 2 | 2 | M | Later (needs a completable course) |
| G4 portfolio | 2 | 2 | M–L | Later |
| I1 AI feedback | 3 | 2 | L | Later (approval) |

## 6. Recommended plan

**Now — one end-to-end slice of the loop.**
1. Pick a plan, which leads to a calendar reminder.
2. The reminder link opens the lesson at the step where you stopped.
3. Progress is visible through the lesson.
4. A finish moment ends the lesson.
5. A teaser pulls you into the next one.
6. The weekly rhythm fills in.
7. A return briefing greets you after a break.

Build it with A1 alongside, so the slice is measurable from day one. Review it rendered on desktop and phone before widening it.

**Next:** Мои промпты, library rows, the outcome-first course page with a plan, the self-check, revisiting your work, "что вы умеете".

**Later:** the Telegram bot (the real reminder channel), потоки once there are learners, the course finale and portfolio, and AI feedback once approved.

## 7. Guardrails

- **No daily streak** and no shame copy ("вы потеряете…"). Pausing is free; the rhythm is weekly because the lessons are 10–20 minutes and the audience is adults.
- **Progress means work:** steps reached, practice saved, lessons completed. No points for page views.
- **No invented social proof.** Show counts only when they're real, and hide them below a threshold.
- **No forced path.** Recommend, never lock; the map stays fully open.
- **Reminders are opt-in**, at times the learner chooses, at most one a day, and easy to switch off.
- **No efficacy or retention claims from staging data.**
