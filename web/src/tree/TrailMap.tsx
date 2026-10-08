import {useEffect, useMemo, useRef, useState} from 'react';
import {AppLink} from '../links';
import type {Milestone, TreeCourse, TreeLesson, TreeModule, TreeTopic} from '../types';

// The skill map on phones: one direction at a time, each course a winding trail you scroll down —
// lesson stones, module signposts and milestone medallions (club/ranks.py) along one path. The
// desktop round tree (engine.js) shows the same data.

type Slot =
  | {kind: 'module'; module: TreeModule; index: number}
  | {kind: 'lesson'; lesson: TreeLesson}
  | {kind: 'coming'; count: number}
  | {kind: 'milestone'; stone: Milestone};

const SLOT = 92;       // px per stop on the trail
const SWAY = 22;       // % of the width the trail swings to each side
const STATE: Record<string, string> = {done: 'Пройден', progress: 'В процессе', open: 'Доступен', locked: 'Урок клуба', coming: 'Скоро'};
const plural = (n: number, one: string, few: string, many: string) =>
  n % 10 === 1 && n % 100 !== 11 ? one : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20) ? few : many;
const sway = (i: number) => 50 + Math.sin(i * 0.85 + 0.4) * SWAY;
const reachedState = (slot: Slot) =>
  slot.kind === 'lesson' ? slot.lesson.state === 'done' : slot.kind === 'milestone' ? slot.stone.state === 'reached' : slot.kind === 'module' ? slot.module.state === 'done' : false;

function slotsOf(course: TreeCourse): Slot[] {
  const slots: Slot[] = [];
  course.modules.forEach((module, index) => {
    slots.push({kind: 'module', module, index});
    let coming = 0;
    for (const lesson of module.lessons) {
      // Lessons not on the platform yet gather into one stop, so the trail stays walkable.
      if (lesson.state === 'coming') { coming++; continue; }
      if (coming) { slots.push({kind: 'coming', count: coming}); coming = 0; }
      slots.push({kind: 'lesson', lesson});
    }
    if (coming) slots.push({kind: 'coming', count: coming});
    for (const stone of (course.milestones ?? []).filter(m => m.after === index)) slots.push({kind: 'milestone', stone});
  });
  return slots;
}

function Trail({course}: {course: TreeCourse}) {
  const slots = useMemo(() => slotsOf(course), [course]);
  const height = slots.length * SLOT;
  const points = slots.map((_, i) => [sway(i), i * SLOT + SLOT / 2] as const);
  // The trail between stops; walked stretches are drawn solid.
  const segments = points.slice(1).map((p, i) => {
    const [x1, y1] = points[i], [x2, y2] = p, m = (y2 - y1) / 2;
    return {d: `M${x1},${y1} C${x1},${y1 + m} ${x2},${y2 - m} ${x2},${y2}`, walked: reachedState(slots[i]) && reachedState(slots[i + 1])};
  });
  return (
    <ol className="trail-path" style={{height}}>
      <svg className="trail-line" viewBox={`0 0 100 ${height}`} preserveAspectRatio="none" aria-hidden="true">
        {segments.map((s, i) => <path key={i} d={s.d} className={s.walked ? 'is-walked' : undefined} vectorEffect="non-scaling-stroke" />)}
      </svg>
      {slots.map((slot, i) => {
        const x = sway(i), side = x > 50 ? 'is-left' : 'is-right';   // the label goes to the roomier side
        const style = {top: i * SLOT, left: `${x}%`};
        if (slot.kind === 'module') {
          return (
            <li key={'m' + slot.index} className={`trail-stop trail-module is-${slot.module.state}`} style={style}>
              <span>{slot.index + 1}. {slot.module.title}</span>
            </li>
          );
        }
        if (slot.kind === 'coming') {
          return (
            <li key={'c' + i} className={`trail-stop trail-coming ${side}`} style={style}>
              <span className="trail-stone" aria-hidden="true">{Array.from({length: Math.min(slot.count, 3)}, (_, d) => <i key={d} />)}</span>
              <span className="trail-label"><strong>Скоро</strong><small>ещё {slot.count} {plural(slot.count, 'урок', 'урока', 'уроков')}</small></span>
            </li>
          );
        }
        if (slot.kind === 'milestone') {
          const stone = slot.stone;
          const note = stone.state === 'reached' ? 'Веха пройдена' : stone.state === 'coming' ? 'Скоро откроется'
            : `ещё ${stone.left} ${plural(stone.left, 'урок', 'урока', 'уроков')}`;
          return (
            <li key={'s' + stone.number} className={`trail-stop trail-milestone is-${stone.state} is-level-${stone.rank} ${side}`} style={style}>
              <span className="trail-stone" aria-hidden="true">
                {stone.state === 'reached'
                  ? <svg viewBox="0 0 24 24"><path d="m5 12.5 4.5 4.5L19 7.5" /></svg>
                  : <svg viewBox="0 0 24 24"><path d="M7 21V4m0 1h11l-3 4.5 3 4.5H7" /></svg>}
              </span>
              <span className="trail-label"><small>Веха {stone.number}</small><strong>{stone.title}</strong><small>{note}</small></span>
            </li>
          );
        }
        const lesson = slot.lesson;
        const label = (
          <>
            <span className="trail-stone" aria-hidden="true">
              {lesson.state === 'done' ? <svg viewBox="0 0 24 24"><path d="m5 12.5 4.5 4.5L19 7.5" /></svg>
                : lesson.state === 'locked' ? <svg viewBox="0 0 24 24"><rect x="5.5" y="10.5" width="13" height="9" rx="2" /><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5" /></svg>
                : <svg viewBox="0 0 24 24"><path d="M9 7.5v9l7.5-4.5z" /></svg>}
            </span>
            <span className="trail-label">
              {lesson.current && <em>Вы здесь</em>}
              <strong>{lesson.title}</strong>
              <small>{lesson.state === 'locked' ? 'Урок клуба' : lesson.minutes ? `${lesson.minutes} мин` : STATE[lesson.state]}</small>
            </span>
            <span className="visually-hidden"> ({STATE[lesson.state]})</span>
          </>
        );
        return (
          <li key={lesson.id ?? 'l' + i} className={`trail-stop trail-lesson is-${lesson.state} ${side}` + (lesson.current ? ' is-current' : '')} style={style}>
            {lesson.url ? <AppLink to={lesson.url}>{label}</AppLink> : <span>{label}</span>}
          </li>
        );
      })}
    </ol>
  );
}

const startTopic = (topics: TreeTopic[]) => {
  const current = topics.findIndex(t => t.courses.some(c => c.current));
  if (current >= 0) return current;
  const interest = topics.findIndex(t => t.interest);
  return interest >= 0 ? interest : 0;
};

export default function TrailMap({topics}: {topics: TreeTopic[]}) {
  const [active, setActive] = useState(() => {
    try {
      const saved = Number(sessionStorage.getItem('trail-topic'));
      if (Number.isInteger(saved) && saved >= 0 && saved < topics.length && sessionStorage.getItem('trail-topic') !== null) return saved;
    } catch { /* per-visit nicety only */ }
    return startTopic(topics);
  });
  const root = useRef<HTMLDivElement>(null);
  const topic = topics[active] ?? topics[0];
  // Opening the map lands on the lesson you're on.
  useEffect(() => {
    root.current?.querySelector('.trail-lesson.is-current')?.scrollIntoView({block: 'center'});
  }, []);
  function choose(index: number) {
    setActive(index);
    try { sessionStorage.setItem('trail-topic', String(index)); } catch { /* per-visit nicety only */ }
  }
  return (
    <div className="trail" ref={root}>
      <div className="trail-tabs" role="tablist" aria-label="Направления">
        {topics.map((t, i) => {
          const total = t.courses.reduce((n, c) => n + c.total, 0), done = t.courses.reduce((n, c) => n + c.done, 0);
          return (
            <button key={t.id} type="button" role="tab" aria-selected={i === active} className={i === active ? 'is-on' : undefined} onClick={() => choose(i)}>
              {t.title}<small>{done}/{total}</small>
            </button>
          );
        })}
      </div>
      {topic.courses.map(course => (
        <section key={course.id} className={'trail-course' + (course.current ? ' is-current' : '')} id={`trail-${course.id}`}>
          <header>
            <span className="trail-course-level">{course.level}</span>
            {course.url ? <AppLink to={course.url}><h2>{course.title}</h2></AppLink> : <h2>{course.title}</h2>}
            <span className="trail-course-meta">
              {course.standing && course.standing.level > 0 && <em className={`tree-rank is-level-${course.standing.level}`}>{course.standing.rank}</em>}
              Пройдено {course.done} из {course.total}
            </span>
            {course.standing && <p className="trail-course-next">{course.standing.next}</p>}
          </header>
          <Trail course={course} />
        </section>
      ))}
    </div>
  );
}
