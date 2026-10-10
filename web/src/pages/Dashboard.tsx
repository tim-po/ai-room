import {useMemo} from 'react';
import {bootstrap} from '../api';
import {dateIn, planOf} from '../components/PathPlan';
import SkillRadar from '../components/SkillRadar';
import {plural} from '../format';
import {weeksLabel, type JourneyData, type JourneyPath} from '../journey';
import {AppLink} from '../Shell';
import type {HomeData, TreeCourse} from '../types';
import {useTitle} from '../useTitle';

// Главная for people signed in: what to do now. The lesson to jump into, the next few steps of the path with
// their dates, how far each goal has come, courses in progress and guides along the way. Without goals yet,
// an invitation to choose them takes the place of the path.

/** How far a goal is from the learner's level now (0–1): the share of its target points already there. */
function reached(path: JourneyPath, targets: Record<string, number>) {
  let need = 0, got = 0;
  for (const [skill, target] of Object.entries(targets)) { need += target; got += Math.min(path.start[skill] ?? 0, target); }
  return need ? got / need : 1;
}

const STEPS = 5;

export default function Dashboard({home, journey}: {home: HomeData; journey: JourneyData | null}) {
  useTitle('Главная');
  const path = journey?.path ?? null;
  const plan = useMemo(() => (path ? planOf(path) : null), [path]);
  const name = bootstrap.user?.name.split(' ')[0] ?? '';

  // The steps ahead: path lessons not done yet, in order.
  const ahead = plan?.lessons.filter(item => item.lesson.state !== 'done') ?? [];
  const steps = ahead.slice(0, STEPS);
  // The lesson to jump into: an unfinished one first, then the first open lesson ahead on the path, then the server's pick.
  const briefing = home.briefing;
  const first = ahead.find(item => item.lesson.url && !['coming', 'locked'].includes(item.lesson.state));
  const jump = briefing
    ? {title: briefing.title, url: briefing.url, note: `${briefing.course}${briefing.step ? ` · шаг ${briefing.step.index} из ${briefing.step.total}` : ''}`, again: true}
    : first ? {title: first.lesson.title, url: first.lesson.url!, note: `${first.lesson.course_title ?? 'Курс'} · ${first.lesson.module_title} · ${first.lesson.minutes} мин`, again: false}
    : home.next ? {title: home.next.title, url: home.next.url, note: 'Следующий урок', again: false} : null;
  const colour = new Map(path?.goals.map(g => [g.id, g.color]) ?? []);

  const courses: TreeCourse[] = home.tree.topics.flatMap(t => t.courses).filter(c => c.done > 0 && c.done < c.total)
    .sort((a, b) => Number(b.current) - Number(a.current));
  const soon = new Set(steps.map(s => s.module));
  const guides = (path?.guides ?? []).filter(g => soon.has(g.module)).concat((path?.guides ?? []).filter(g => !soon.has(g.module))).slice(0, 3);

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
      <AppLink className="button" to="/onboarding">{journey?.status === 'draft' ? 'Продолжить знакомство →' : 'Выбрать цели · 2 минуты →'}</AppLink>
    </section>
  );
  const goalsCard = path && plan && (
    <section className="dash-card dash-goals" aria-labelledby="goals-title">
      <div className="dash-card-head">
        <h2 id="goals-title">Твои цели</h2>
        <AppLink to="/onboarding">изменить</AppLink>
      </div>
      <ul>
        {path.goals.map(goal => {
          const now = reached(path, goal.targets), at = plan.finish[goal.id];
          const by = at != null ? plan.lessons[at].to : null;
          // the bar: the part the learner's own level already covers (hatched, from the onboarding answers and
          // finished lessons), then the path's lessons still to take; nothing here claims progress not made
          return (
            <li key={goal.id} style={{'--goal': goal.color, '--value': now} as React.CSSProperties}>
              <span className="dash-goal-name"><i />{goal.title}</span>
              <span className="dash-goal-bar" title={`Уже есть по твоему уровню: ${Math.round(now * 100)}%`}><b /></span>
              <small>{goal.lessons} {plural(goal.lessons, 'урок', 'урока', 'уроков')} впереди · {by != null ? `цель к ${dateIn(by, 'long')}` : 'часть уроков ещё готовится'}
                {goal.deadline && by != null ? (by <= goal.deadline ? ' · в срок' : ' · позже срока') : ''}</small>
            </li>
          );
        })}
      </ul>
      <p className="dash-goals-note"><i /> штриховка — что у тебя уже есть: по твоей оценке уровня и пройденным урокам. Остальное закроют уроки впереди</p>
      {journey && <SkillRadar skills={journey.options.skills} goals={path.goals} start={path.start} label="Навыки сейчас и нужные для целей" />}
    </section>
  );
  const stepsCard = steps.length > 0 && (
    <section className="dash-card dash-steps" aria-labelledby="steps-title">
      <div className="dash-card-head">
        <h2 id="steps-title">Ближайшие шаги</h2>
        <AppLink to="/path">Весь путь на карте →</AppLink>
      </div>
      <ol>
        {steps.map(item => {
          const open = item.lesson.url && !['coming', 'locked'].includes(item.lesson.state);
          return (
            <li key={item.lesson.key}>
              <time>{dateIn(item.from)}</time>
              <span className="dash-step-dots" aria-label={`Для целей: ${item.lesson.goals.length}`}>
                {item.lesson.goals.map(id => <i key={id} style={{background: colour.get(id)}} />)}
              </span>
              <div>
                {open ? <AppLink to={item.lesson.url!}>{item.lesson.title}</AppLink> : <span>{item.lesson.title}</span>}
                <small>{item.lesson.module_title} · {item.lesson.minutes} мин{item.lesson.state === 'locked' ? ' · в клубе' : item.lesson.state === 'coming' ? ' · скоро' : ''}</small>
              </div>
            </li>
          );
        })}
      </ol>
      {ahead.length > STEPS && <p className="dash-more">и ещё {ahead.length - STEPS} {plural(ahead.length - STEPS, 'урок', 'урока', 'уроков')} до финиша — {dateIn(plan!.weeks, 'long')}</p>}
    </section>
  );
  const guidesCard = guides.length > 0 && (
    <section className="dash-card dash-guides" aria-labelledby="guides-title">
      <div className="dash-card-head"><h2 id="guides-title">По пути</h2><AppLink to="/discover">Обзор →</AppLink></div>
      <ul>
        {guides.map(guide => (
          <li key={guide.id}>
            <AppLink to={guide.url}>
              <em>{guide.format === 'use_case' ? 'Кейс' : 'Гайд'}{guide.minutes ? ` · ${guide.minutes} мин` : ''} · {guide.club ? 'в клубе' : 'бесплатно'}</em>
              <span>{guide.title}</span>
              <span className="dash-step-dots">{guide.goals.map(id => <i key={id} style={{background: colour.get(id)}} />)}</span>
            </AppLink>
          </li>
        ))}
      </ul>
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
  const mapCard = (
    <AppLink className="dash-card dash-map" to="/path">
      <p className="dash-kicker">Карта</p>
      <strong>{path ? 'Твой путь на карте навыков' : 'Карта навыков'}</strong>
      <span>{path ? 'Каждая цель — своя линия: где они идут вместе, что уже знаешь и где гайды по пути.' : 'Все направления, курсы и уроки клуба на одной карте.'}</span>
    </AppLink>
  );

  return (
    <div className="dash">
      <header className="dash-head">
        <p className="eyebrow">Главная</p>
        <h1>{name ? `Привет, ${name}` : 'Привет'}</h1>
        {plan && path && (
          <p className="dash-lead">
            Впереди {ahead.length} {plural(ahead.length, 'урок', 'урока', 'уроков')} · {weeksLabel(Math.ceil(plan.weeks))} в твоём темпе
            {path.pace ? ` · ${path.pace.sessions} × ${path.pace.session_minutes} мин в неделю` : ''}
          </p>
        )}
      </header>
      {/* the main column: what to do; the side: where it leads */}
      <div className="dash-grid">
        <div className="dash-col">{path ? null : invite}{jumpCard}{stepsCard}{coursesCard}</div>
        <div className="dash-col">{goalsCard}{guidesCard}{mapCard}</div>
      </div>
    </div>
  );
}
