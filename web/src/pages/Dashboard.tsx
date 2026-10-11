import {useMemo, useState} from 'react';
import {useRevalidator} from 'react-router';
import {ApiError, bootstrap, putJson} from '../api';
import {CalendarLinks} from '../components/PlanEditor';
import {dateIn, planOf, type Plan as PathTimes} from '../components/PathPlan';
import SkillRadar from '../components/SkillRadar';
import {plural} from '../format';
import {weeksLabel, type JourneyData, type JourneyPath} from '../journey';
import {DAYS_SHORT, formatDays} from '../plan';
import {AppLink} from '../Shell';
import type {HomeData, Plan, TreeCourse} from '../types';
import {useTitle} from '../useTitle';

// Главная for people signed in: what to do now and how it's going. The lesson to jump into and the milestones
// ahead; the study plan as a calendar (sessions to come with their lessons, days already studied, settings and
// calendar links); the goals on a large radar; the next steps and courses in progress. Without goals yet,
// an invitation to choose them takes the place of the path.

/** How far a goal is from the learner's level now (0–1): the share of its target points already there. */
function reached(path: JourneyPath, targets: Record<string, number>) {
  let need = 0, got = 0;
  for (const [skill, target] of Object.entries(targets)) { need += target; got += Math.min(path.start[skill] ?? 0, target); }
  return need ? got / need : 1;
}

const STEPS = 5;
// Study days suggested for a number of sessions a week (as in onboarding).
const DAYS_FOR: Record<number, number[]> = {1: [3], 2: [2, 4], 3: [1, 3, 5], 4: [1, 2, 4, 6], 5: [1, 2, 3, 4, 5], 6: [1, 2, 3, 4, 5, 6], 7: [1, 2, 3, 4, 5, 6, 7]};
const MINUTES = [15, 20, 30, 45, 60, 90];
const TIMES = ['07:00', '08:00', '09:00', '12:00', '13:00', '18:00', '19:00', '20:00', '21:00', '22:00'];
const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const dayStart = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());

/** The next two weeks from this Monday: past days with what was done, study days with the lessons that fall on them. */
function StudyCalendar({path, times, plan, activity, onSaved}: {
  path: JourneyPath | null; times: PathTimes | null; plan: Plan; activity: {day: string; lessons: number}[]; onSaved: () => void;
}) {
  const pace = path?.pace ?? null;
  const [editing, setEditing] = useState(false);
  const [sessions, setSessions] = useState(pace?.sessions ?? (plan.days.length || 3));
  const [minutes, setMinutes] = useState(pace?.session_minutes ?? 30);
  const [days, setDays] = useState<number[]>(plan.days.length ? plan.days : DAYS_FOR[pace?.sessions ?? 3]);
  const [time, setTime] = useState(plan.time || '19:00');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const studyDays = plan.days.length ? plan.days : DAYS_FOR[pace?.sessions ?? 3];
  const done = new Map(activity.map(a => [a.day, a.lessons]));
  // A missed study day counts only from the first day the learner studied here (not before they joined).
  const since = activity.length ? activity.map(a => a.day).sort()[0] : null;

  // Lessons ahead, session by session: each study day takes lessons until its minutes are used (at least one).
  const today = dayStart(new Date());
  const monday = new Date(today); monday.setDate(today.getDate() - ((today.getDay() || 7) - 1));
  const ahead = times?.lessons.filter(i => i.lesson.state !== 'done') ?? [];
  const perSession = pace?.session_minutes ?? minutes;
  const cells: {date: Date; study: boolean; lessons: typeof ahead}[] = [];
  let next = 0;
  for (let i = 0; i < 14; i++) {
    const date = new Date(monday); date.setDate(monday.getDate() + i);
    const study = studyDays.includes(date.getDay() || 7);
    const lessons: typeof ahead = [];
    if (study && date >= today) {
      let used = 0;
      while (next < ahead.length && (lessons.length === 0 || used + ahead[next].lesson.minutes <= perSession)) { used += ahead[next].lesson.minutes; lessons.push(ahead[next++]); }
    }
    cells.push({date, study, lessons});
  }
  // Twelve weeks of activity, Monday-first columns.
  const weeks: {day: string; lessons: number; active: boolean; future: boolean}[][] = [];
  const first = new Date(monday); first.setDate(monday.getDate() - 7 * 11);
  for (let w = 0; w < 12; w++) {
    const column = [];
    for (let d = 0; d < 7; d++) {
      const date = new Date(first); date.setDate(first.getDate() + w * 7 + d);
      const key = iso(date);
      column.push({day: key, lessons: done.get(key) ?? 0, active: done.has(key), future: date > today});
    }
    weeks.push(column);
  }
  const activeDays = activity.length, lessonsDone = activity.reduce((n, a) => n + a.lessons, 0);

  async function save() {
    setBusy(true); setError('');
    try {
      await putJson('/api/app/plan', {days, time});
      if (path) await putJson('/api/app/journey', {pace: {sessions: days.length || sessions, session_minutes: minutes}});
      setEditing(false);
      onSaved();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Не удалось сохранить план.');
    } finally {
      setBusy(false);
    }
  }
  function pickSessions(n: number) { setSessions(n); setDays(DAYS_FOR[n]); }
  function toggleDay(d: number) { setDays(list => { const next = list.includes(d) ? list.filter(x => x !== d) : [...list, d].sort(); setSessions(next.length || 1); return next; }); }

  return (
    <section className="dash-card dash-calendar" aria-labelledby="calendar-title">
      <div className="dash-card-head">
        <h2 id="calendar-title">План занятий</h2>
        <button type="button" className="link-button" aria-expanded={editing} onClick={() => setEditing(e => !e)}>{editing ? 'Готово' : 'Настроить'}</button>
      </div>
      <p className="dash-note">
        {plan.days.length ? `${formatDays(plan.days)} в ${plan.time}` : `Дни не выбраны — показываем ${formatDays(studyDays)}`}
        {pace ? ` · ${pace.sessions} × ${pace.session_minutes} мин в неделю` : ''}
        {times ? ` · финиш пути — ${dateIn(times.weeks, 'long')}` : ''}
      </p>

      {editing && (
        <div className="dash-plan-edit">
          <div className="dash-plan-row"><span>Занятий в неделю</span>
            <div className="dash-chips">{[1, 2, 3, 4, 5, 6, 7].map(n => <button key={n} type="button" aria-pressed={sessions === n} onClick={() => pickSessions(n)}>{n}</button>)}</div></div>
          <div className="dash-plan-row"><span>Дни</span>
            <div className="dash-chips">{DAYS_SHORT.map((name, i) => <button key={name} type="button" aria-pressed={days.includes(i + 1)} onClick={() => toggleDay(i + 1)}>{name}</button>)}</div></div>
          <div className="dash-plan-row"><span>Минут за занятие</span>
            <div className="dash-chips">{MINUTES.map(m => <button key={m} type="button" aria-pressed={minutes === m} onClick={() => setMinutes(m)}>{m}</button>)}</div></div>
          <div className="dash-plan-row"><span>Время</span>
            <div className="dash-chips">{TIMES.map(t => <button key={t} type="button" aria-pressed={time === t} onClick={() => setTime(t)}>{t}</button>)}</div></div>
          <div className="dash-plan-actions">
            <button type="button" className="button" disabled={busy || !days.length} onClick={save}>{busy ? 'Сохраняем…' : 'Сохранить план'}</button>
            {error && <span className="small plan-error" role="alert">{error}</span>}
          </div>
        </div>
      )}

      <ol className="dash-week" aria-label="Две недели занятий">
        {cells.map(({date, study, lessons}) => {
          const key = iso(date), past = date < today, isToday = key === iso(today), count = done.get(key);
          return (
            <li key={key} className={(past ? 'is-past' : '') + (isToday ? ' is-today' : '') + (study ? ' is-study' : '') + (count != null ? ' is-active' : '')}>
              <span className="dash-day">{DAYS_SHORT[(date.getDay() || 7) - 1]} <b>{date.getDate()}</b></span>
              {past || (isToday && count != null) ? (
                count != null ? <span className="dash-did">✓ {count ? `${count} ${plural(count, 'урок', 'урока', 'уроков')}` : 'было занятие'}</span> : study && since && key > since ? <span className="dash-missed">пропуск</span> : null
              ) : lessons.length > 0 ? (
                <ul>{lessons.slice(0, 2).map(i => <li key={i.lesson.key}>{i.lesson.url ? <AppLink to={i.lesson.url}>{i.lesson.title}</AppLink> : i.lesson.title}</li>)}
                  {lessons.length > 2 && <li className="dash-more-lessons">+ ещё {lessons.length - 2}</li>}</ul>
              ) : study ? <span className="dash-free">{plan.time}</span> : null}
            </li>
          );
        })}
      </ol>

      <div className="dash-activity">
        <div className="dash-heat" role="img" aria-label={`За 12 недель: ${activeDays} ${plural(activeDays, 'день', 'дня', 'дней')} занятий, ${lessonsDone} ${plural(lessonsDone, 'урок', 'урока', 'уроков')}`}>
          {weeks.map((column, w) => (
            <span key={w}>{column.map(c => <i key={c.day} title={c.future ? '' : `${c.day}: ${c.active ? (c.lessons ? `${c.lessons} ${plural(c.lessons, 'урок', 'урока', 'уроков')}` : 'занятие') : 'нет занятий'}`}
              className={c.future ? 'is-future' : c.lessons >= 3 ? 'is-3' : c.lessons === 2 ? 'is-2' : c.active ? 'is-1' : ''} />)}</span>
          ))}
        </div>
        <p><strong>{activeDays}</strong> {plural(activeDays, 'день', 'дня', 'дней')} занятий и <strong>{lessonsDone}</strong> {plural(lessonsDone, 'урок', 'урока', 'уроков')} за 12 недель</p>
      </div>
      {plan.days.length > 0 && <CalendarLinks plan={plan} />}
    </section>
  );
}

export default function Dashboard({home, journey}: {home: HomeData; journey: JourneyData | null}) {
  useTitle('Главная');
  const revalidator = useRevalidator();
  const path = journey?.path ?? null;
  const plan = useMemo(() => (path ? planOf(path) : null), [path]);
  const name = bootstrap.user?.name.split(' ')[0] ?? '';
  const [focus, setFocus] = useState<string | null>(null);

  // The steps ahead: path lessons not done yet, in order.
  const ahead = plan?.lessons.filter(item => item.lesson.state !== 'done') ?? [];
  const steps = ahead.slice(0, STEPS);
  // The lesson to jump into: an unfinished one first, then the first lesson ahead that is here already, then the server's pick.
  const briefing = home.briefing;
  const first = ahead.find(item => item.lesson.url && !['coming', 'locked'].includes(item.lesson.state));
  const jump = briefing
    ? {title: briefing.title, url: briefing.url, note: `${briefing.course}${briefing.step ? ` · шаг ${briefing.step.index} из ${briefing.step.total}` : ''}`, again: true}
    : first ? {title: first.lesson.title, url: first.lesson.url!, note: `${first.lesson.course_title ?? 'Курс'} · ${first.lesson.module_title} · ${first.lesson.minutes} мин`, again: false}
    : home.next ? {title: home.next.title, url: home.next.url, note: 'Следующий урок', again: false} : null;
  const colour = new Map(path?.goals.map(g => [g.id, g.color]) ?? []);

  const allCourses: TreeCourse[] = home.tree.topics.flatMap(t => t.courses);
  const courses = allCourses.filter(c => c.done > 0 && c.done < c.total).sort((a, b) => Number(b.current) - Number(a.current));
  // Milestones ahead on the courses of the path (or the ones started): the next one of each, with how far along it is.
  const pathCourses = new Set(path?.lessons.map(l => l.course) ?? []);
  const order = (id: string) => { const i = [...pathCourses].indexOf(id); return i < 0 ? 99 : i; };
  const milestones = allCourses.filter(c => pathCourses.has(c.id) || c.done > 0).flatMap(c => {
    const stone = (c.milestones ?? []).find(m => m.state !== 'reached');
    return stone ? [{course: c, stone, value: stone.lessons ? stone.done / stone.lessons : 0, reached: (c.milestones ?? []).filter(m => m.state === 'reached').length}] : [];
  }).sort((a, b) => b.value - a.value || order(a.course.id) - order(b.course.id)).slice(0, 5);

  const jumpCard = jump && (
    <section className="dash-card dash-jump" aria-labelledby="jump-title">
      <p className="dash-kicker">{jump.again ? 'Продолжить с того места' : 'Следующий шаг'}</p>
      <h2 id="jump-title">{jump.title}</h2>
      <p className="dash-note">{jump.note}</p>
      <AppLink className="button" to={jump.url}>{jump.again ? 'Продолжить →' : 'Начать →'}</AppLink>
    </section>
  );
  const invite = (
    <section className="dash-card dash-invite" aria-labelledby="invite-title">
      <p className="dash-kicker">Мой путь</p>
      <h2 id="invite-title">Собери маршрут под свои цели</h2>
      <p>Выбери до трёх целей, отметь, что уже умеешь, и сколько времени есть в неделю — мы проложим по карте путь из уроков, с датами.</p>
      <AppLink className="button" to="/onboarding?step=goals">{journey?.status === 'draft' ? 'Продолжить знакомство →' : 'Выбрать цели · 2 минуты →'}</AppLink>
    </section>
  );
  const milestonesCard = milestones.length > 0 && (
    <section className="dash-card dash-milestones" aria-labelledby="milestones-title">
      <div className="dash-card-head"><h2 id="milestones-title">Майлстоуны</h2><AppLink to="/path">на карте →</AppLink></div>
      <ul>
        {milestones.map(({course, stone, value, reached: got}) => (
          <li key={course.id} style={{'--value': value} as React.CSSProperties}>
            <span className="dash-milestone-name"><strong>{course.title}</strong><b>{Math.round(value * 100)}%</b></span>
            <span className="dash-goal-bar is-solid"><b /></span>
            <small>Майлстоун {stone.number} «{stone.name}» · {stone.state === 'coming' ? 'уроки ещё готовятся' : `ещё ${stone.left} ${plural(stone.left, 'урок', 'урока', 'уроков')}`}{got ? ` · пройдено майлстоунов: ${got}` : ''}</small>
          </li>
        ))}
      </ul>
    </section>
  );
  const focused = path?.goals.find(g => g.id === focus) ?? null;
  const goalsCard = path && plan && journey && (
    <section className="dash-card dash-goals" aria-labelledby="goals-title">
      <div className="dash-card-head">
        <h2 id="goals-title">Твои цели</h2>
        <AppLink to="/onboarding?step=goals">изменить</AppLink>
      </div>
      <div className="dash-goals-body">
        <SkillRadar skills={journey.options.skills} goals={path.goals} start={path.start} focus={focus} label="Навыки сейчас и нужные для целей" />
        <div className="dash-goals-side">
          <ul>
            {path.goals.map(goal => {
              const now = reached(path, goal.targets), at = plan.finish[goal.id];
              const by = at != null ? plan.lessons[at].to : null;
              return (
                // the bar: the part the learner's own level already covers (hatched, from the onboarding answers and
                // finished lessons); the lessons ahead close the rest
                <li key={goal.id} style={{'--goal': goal.color, '--value': now} as React.CSSProperties}>
                  <button type="button" className={'dash-goal' + (focus === goal.id ? ' is-on' : '')} aria-pressed={focus === goal.id}
                    onClick={() => setFocus(f => (f === goal.id ? null : goal.id))}>
                    <span className="dash-goal-name"><i />{goal.title}</span>
                    <span className="dash-goal-bar" title={`Уже есть по твоему уровню: ${Math.round(now * 100)}%`}><b /></span>
                    <small>{goal.lessons} {plural(goal.lessons, 'урок', 'урока', 'уроков')} впереди · {by != null ? `цель к ${dateIn(by, 'long')}` : 'часть уроков ещё готовится'}
                      {goal.deadline && by != null ? (by <= goal.deadline ? ' · в срок' : ' · позже срока') : ''}</small>
                  </button>
                </li>
              );
            })}
          </ul>
          {focused ? (
            <div className="dash-skills" style={{'--goal': focused.color} as React.CSSProperties}>
              <p className="dash-kicker">Что нужно для «{focused.title}»</p>
              <ul>
                {Object.entries(focused.targets).sort((a, b) => b[1] - a[1]).map(([id, target]) => {
                  const now = Math.min(path.start[id] ?? 0, target);
                  return (
                    <li key={id}>
                      <span>{journey.options.skills.find(s => s.id === id)?.title ?? id}</span>
                      <span className="dash-skill-bar"><b style={{width: `${target}%`}} /><i style={{width: `${now}%`}} /></span>
                      <small>{now >= target ? 'уже есть' : `${Math.round(now)} → ${target}`}</small>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : (
            <p className="dash-goals-note"><i /> Нажми на цель — радар покажет её навыки. Штриховка — что у тебя уже есть: по твоей оценке уровня и пройденным урокам.</p>
          )}
        </div>
      </div>
    </section>
  );
  const stepsCard = steps.length > 0 && (
    <section className="dash-card dash-steps" aria-labelledby="steps-title">
      <div className="dash-card-head">
        <h2 id="steps-title">Ближайшие шаги</h2>
        <AppLink to="/path">Весь путь на карте →</AppLink>
      </div>
      <ol>
        {steps.map(item => (
          <li key={item.lesson.key}>
            <time>{dateIn(item.from)}</time>
            <span className="dash-step-dots" aria-label={`Для целей: ${item.lesson.goals.length}`}>
              {item.lesson.goals.map(id => <i key={id} style={{background: colour.get(id)}} />)}
            </span>
            <div>
              {item.lesson.url ? <AppLink to={item.lesson.url}>{item.lesson.title}</AppLink> : <span>{item.lesson.title}</span>}
              <small>{item.lesson.module_title} · {item.lesson.minutes} мин{item.lesson.state === 'locked' ? ' · в клубе' : item.lesson.state === 'coming' ? ' · готовится' : ''}</small>
            </div>
          </li>
        ))}
      </ol>
      {ahead.length > STEPS && <p className="dash-more">и ещё {ahead.length - STEPS} {plural(ahead.length - STEPS, 'урок', 'урока', 'уроков')} до финиша — {dateIn(plan!.weeks, 'long')}</p>}
    </section>
  );
  const coursesCard = courses.length > 0 && (
    <section className="dash-card dash-courses" aria-labelledby="courses-title">
      <div className="dash-card-head"><h2 id="courses-title">Курсы в процессе</h2></div>
      <ul>
        {courses.slice(0, 4).map(course => (
          <li key={course.id}>
            <AppLink to={course.next?.url ?? course.url ?? `/map#course-${course.id}`}>
              <strong>{course.title}</strong>
              <span className="tree-bar"><span style={{width: `${(100 * course.done) / course.total}%`}} /></span>
              <small>Пройдено {course.done} из {course.total}{course.next ? ` · дальше: ${course.next.title}` : ''}</small>
            </AppLink>
          </li>
        ))}
      </ul>
    </section>
  );

  return (
    <div className="dash">
      <header className="dash-head">
        <p className="eyebrow">Главная</p>
        <h1>{name ? `Привет, ${name}` : 'Привет'}</h1>
        {plan && path && (
          <p className="dash-lead">
            Впереди {ahead.length} {plural(ahead.length, 'урок', 'урока', 'уроков')} · {weeksLabel(Math.ceil(plan.weeks))} в твоём темпе
          </p>
        )}
      </header>
      <div className="dash-grid">
        <div className="dash-wide">{path ? jumpCard : invite}</div>
        <div className="dash-narrow">{milestonesCard || (!path && jumpCard)}</div>
        {home.plan && <div className="dash-full"><StudyCalendar path={path} times={plan} plan={home.plan} activity={home.activity ?? []} onSaved={() => revalidator.revalidate()} /></div>}
        {goalsCard && <div className="dash-full">{goalsCard}</div>}
        <div className={coursesCard ? 'dash-wide' : 'dash-full'}>{stepsCard}</div>
        <div className="dash-narrow">{coursesCard}</div>
      </div>
    </div>
  );
}

