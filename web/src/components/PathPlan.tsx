import {Fragment, useRef} from 'react';
import {AppLink} from '../Shell';
import {weeksLabel, type JourneyPath, type PathGoal, type PathLesson} from '../journey';

// The learning plan in the panel over the map. On top, the date being read and the goals (each can be
// switched off) with how far they will have come by then; «Ты, вероятно, уже знаешь»; then «Ты изучишь»:
// lesson by lesson under their modules, as a metro line — every goal a coloured rail alongside, a dot on
// the rails of the goals a lesson moves forward, a rail ending where its goal is reached. Scrolling is
// moving through time: the lesson being read sets the date the map shows.

export interface PlanLesson {lesson: PathLesson; index: number; module: string; from: number; to: number}
export interface PlanModule {key: string; title: string; course: string; course_title: string | null; again: boolean; lessons: PlanLesson[]}
export interface Plan {modules: PlanModule[]; lessons: PlanLesson[]; finish: Record<string, number>; weeks: number}

export const dateIn = (weeks: number, month: 'short' | 'long' = 'short') =>
  new Date(Date.now() + weeks * 7 * 86400000).toLocaleDateString('ru-RU', {day: 'numeric', month}).replace('.', '');

/** The path at its pace: each lesson's weeks, grouped into runs of one module, and the lesson after which
 *  each goal is reached (the same measure as club/paths.py progress). */
export function planOf(path: JourneyPath): Plan {
  const perWeek = path.pace?.minutes_per_week ?? 120;
  const modules: PlanModule[] = [], lessons: PlanLesson[] = [];
  const points = {...path.start};
  const finish: Record<string, number> = {};
  let spent = 0;
  path.lessons.forEach((lesson, index) => {
    const key = `${lesson.course}:${lesson.module}`;
    let module = modules[modules.length - 1];
    if (!module || module.key !== key) {
      module = {key, title: lesson.module_title, course: lesson.course, course_title: lesson.course_title, again: modules.some(m => m.key === key), lessons: []};
      modules.push(module);
    }
    const item = {lesson, index, module: key, from: spent / perWeek, to: (spent + lesson.minutes) / perWeek};
    spent += lesson.minutes;
    module.lessons.push(item);
    lessons.push(item);
    for (const [skill, gain] of Object.entries(lesson.gains)) points[skill] = Math.min(100, (points[skill] ?? 0) + gain);
    for (const goal of path.goals) {
      if (finish[goal.id] != null) continue;
      let need = 0, got = 0;
      for (const [skill, target] of Object.entries(goal.targets)) {
        const from = Math.min(path.start[skill] ?? 0, target);
        need += target - from;
        got += Math.max(0, Math.min(points[skill] ?? 0, target) - from);
      }
      if (!need || got / need >= 0.999) finish[goal.id] = index;
    }
  });
  return {modules, lessons, finish, weeks: spent / perWeek};
}

const minutes = (n: number) => (n >= 60 ? `${Math.floor(n / 60)} ч${n % 60 ? ` ${n % 60} мин` : ''}` : `${n} мин`);

export default function PathPlan({path, plan, hidden, onToggle, reading, week, progress, custom, onCustom, paywall, focusGuide, onGuide}: {
  path: JourneyPath; plan: Plan; hidden: string[]; onToggle: (id: string) => void;
  reading: number; week: number; progress: Record<string, number>; custom?: string; onCustom: () => void; paywall: string;
  /** the guide the map is showing (scrolled to, pointed at or focused in the plan) */
  focusGuide?: string | null; onGuide?: (id: string) => void;
}) {
  const goals = path.goals.filter(g => !hidden.includes(g.id));
  const known = new Map<string, {title: string; modules: string[]}>();
  for (const module of path.assumed) {
    const entry = known.get(module.course) ?? {title: module.course_title ?? 'Курс', modules: []};
    entry.modules.push(module.title);
    known.set(module.course, entry);
  }
  // rails beside a row: a goal's rail runs until the lesson that reaches it
  const rails = (index: number, dots: string[] = [], end?: PathGoal) => goals.map(g => {
    const over = plan.finish[g.id] != null && plan.finish[g.id] < index;
    return <i key={g.id} className={(over ? 'is-over' : '') + (dots.includes(g.id) ? ' is-stop' : '') + (end?.id === g.id ? ' is-end' : '')} style={{background: g.color, color: g.color}} />;
  });

  return (
    <div className="path-plan">
      <div className="path-plan-head">
        <p className="path-plan-when">{reading < 0 ? 'Сегодня' : <>К {dateIn(week, 'long')} <small>через {weeksLabel(Math.max(1, Math.round(week)))}</small></>}</p>
        <div className="path-plan-goals" role="group" aria-label="Цели на карте">
          {path.goals.map(goal => {
            const on = !hidden.includes(goal.id);
            const value = progress[goal.id] ?? 0;
            return (
              <button key={goal.id} type="button" className={'path-plan-goal' + (on ? ' is-on' : '')} aria-pressed={on} onClick={() => onToggle(goal.id)}
                title={`${goal.title} — ${on ? 'скрыть на карте' : 'показать на карте'}`} style={{'--goal': goal.color, '--value': value} as React.CSSProperties}>
                <i />
                <span>{goal.title}</span>
                <b>{Math.round(value * 100)}%</b>
              </button>
            );
          })}
          {custom && (
            <button type="button" className="path-plan-goal is-custom" onClick={onCustom} title={custom}>
              <i /><span>{custom}</span><b>{paywall ? '🔒' : ''}</b>
            </button>
          )}
        </div>
        {paywall && <p className="journey-paywall" role="status"><strong>{paywall}.</strong> Путь по своей цели собирается в подписке.</p>}
      </div>

      {known.size > 0 && (
        <section className="path-plan-known" aria-labelledby="plan-known">
          <h3 id="plan-known">Ты, вероятно, уже знаешь</h3>
          <p>По твоему уровню это можно пропустить — на карте подсвечено серым.</p>
          <ul>
            {[...known.entries()].map(([id, entry]) => (
              <li key={id}><strong>{entry.title}</strong><span>{entry.modules.join(' · ')}</span></li>
            ))}
          </ul>
        </section>
      )}

      <section className="path-plan-learn" aria-labelledby="plan-learn">
        <h3 id="plan-learn">Ты изучишь <small>{plan.lessons.length} уроков · {weeksLabel(Math.ceil(plan.weeks))}</small></h3>
        <ol className="metro" style={{'--lanes': goals.length} as React.CSSProperties}>
          {plan.modules.map((module, mi) => {
            const first = module.lessons[0], last = module.lessons[module.lessons.length - 1];
            return (
              <Fragment key={module.key + mi}>
                <li className="metro-module" data-module={module.key}>
                  <span className="metro-rails" aria-hidden="true">{rails(first.index)}</span>
                  <div>
                    <strong>{module.title}{module.again && <em> · продолжение</em>}</strong>
                    <small>{module.course_title ?? 'Курс'} · {dateIn(first.from)} — {dateIn(Math.max(last.to, first.from + 1 / 7))}</small>
                  </div>
                </li>
                {module.lessons.map(item => {
                  const ends = goals.filter(g => plan.finish[g.id] === item.index);
                  const state = item.index < reading ? ' is-done' : item.index === reading ? ' is-now' : '';
                  const open = item.lesson.url && !['coming', 'locked'].includes(item.lesson.state);
                  const dots = item.lesson.goals.filter(id => goals.some(g => g.id === id));
                  return (
                    <Fragment key={item.lesson.key}>
                      <li className={'metro-lesson' + state + (item.lesson.state === 'done' ? ' is-passed' : '')} data-lesson={item.index}>
                        <span className="metro-rails" aria-hidden="true">
                          {rails(item.index, dots)}
                          {dots.length > 1 && <b className="metro-interchange" style={{
                            left: `calc(${goals.findIndex(g => dots.includes(g.id))} * var(--lane) - 1px)`,
                            width: `calc(${goals.map(g => dots.includes(g.id)).lastIndexOf(true) - goals.findIndex(g => dots.includes(g.id)) + 1} * var(--lane) + 2px)`}} />}
                        </span>
                        <div>
                          {open ? <AppLink to={item.lesson.url!}>{item.lesson.title}</AppLink> : <span>{item.lesson.title}</span>}
                          <small>{dateIn(item.from)} · {minutes(item.lesson.minutes)}{item.lesson.state === 'coming' ? ' · скоро' : item.lesson.state === 'locked' ? ' · в клубе' : ''}</small>
                        </div>
                      </li>
                      {ends.map(g => (
                        <li key={'end' + g.id} className="metro-finish">
                          <span className="metro-rails" aria-hidden="true">{rails(item.index, [], g)}</span>
                          <span><strong>Цель: {g.title}</strong> · {dateIn(item.to, 'long')}{g.deadline ? (item.to <= g.deadline ? ' · в срок ✓' : ` · позже срока на ${weeksLabel(Math.ceil(item.to - g.deadline))}`) : ''}</span>
                        </li>
                      ))}
                    </Fragment>
                  );
                })}
                {/* side stops: guides and use cases for this module (only where the path first reaches it) */}
                {!module.again && (path.guides ?? []).filter(g => g.module === module.key).map(guide => (
                  <li key={'guide' + guide.id} className={'metro-guide' + (guide.id === focusGuide ? ' is-now' : '')} data-guide={guide.id}
                    onPointerEnter={() => onGuide?.(guide.id)} onFocus={() => onGuide?.(guide.id)}>
                    <span className="metro-rails" aria-hidden="true">{rails(last.index)}</span>
                    <AppLink to={guide.url}>
                      <em>{[guide.format === 'use_case' ? 'Кейс' : 'Гайд', guide.minutes ? `${guide.minutes} мин` : null, guide.club ? 'в клубе' : 'бесплатно', 'по желанию'].filter(Boolean).join(' · ')}</em>
                      <span>{guide.title}</span>
                    </AppLink>
                  </li>
                ))}
              </Fragment>
            );
          })}
        </ol>
      </section>
      <p className="path-plan-pace">{path.pace ? `${path.pace.sessions} × ${path.pace.session_minutes} мин в неделю` : 'Темп не выбран'} · <AppLink to="/onboarding">изменить цели и темп</AppLink></p>
    </div>
  );
}

/** The plan folded away: a slim timeline from today to the end of the path — a rail per goal ending at its
 *  goal, and a knob with the date being read. Click, drag, the mouse wheel or the arrow keys move through time. */
export function PlanTimeline({path, plan, hidden, reading, onReading, onOpen, label}: {
  path: JourneyPath; plan: Plan; hidden: string[]; reading: number; onReading: (index: number) => void; onOpen: () => void; label: string;
}) {
  // the wheel moves a lesson per notch (trackpads send many small deltas: add them up)
  const wheel = useRef(0);
  const goals = path.goals.filter(g => !hidden.includes(g.id));
  const span = Math.max(plan.weeks, 1);
  const at = reading >= 0 ? plan.lessons[reading].to / span : 0;
  function pick(clientY: number, box: HTMLElement) {
    const rect = box.getBoundingClientRect();
    const week = Math.max(0, Math.min(1, (clientY - rect.top) / rect.height)) * span;
    let index = -1;
    for (const item of plan.lessons) if (item.to <= week + 1e-6) index = item.index;
    onReading(index);
  }
  const months = Array.from({length: Math.floor(span / 4.35)}, (_, i) => ((i + 1) * 4.35) / span);
  return (
    <div className="plan-timeline">
      <button type="button" className="plan-timeline-open" onClick={onOpen} aria-label="Развернуть план">‹</button>
      <div className="plan-timeline-track" role="slider" tabIndex={0} aria-label="Время" aria-valuemin={0} aria-valuemax={plan.lessons.length - 1} aria-valuenow={reading}
        aria-valuetext={reading < 0 ? 'Сегодня' : `К ${dateIn(plan.lessons[reading].to, 'long')}`}
        onPointerDown={e => { e.currentTarget.setPointerCapture(e.pointerId); pick(e.clientY, e.currentTarget); }}
        onPointerMove={e => { if (e.buttons) pick(e.clientY, e.currentTarget); }}
        onWheel={e => {
          wheel.current += e.deltaY;
          const steps = Math.trunc(wheel.current / 40);
          if (!steps) return;
          wheel.current -= steps * 40;
          onReading(Math.max(-1, Math.min(plan.lessons.length - 1, reading + steps)));
        }}
        onKeyDown={e => {
          if (e.key === 'ArrowDown') { e.preventDefault(); onReading(Math.min(plan.lessons.length - 1, reading + 1)); }
          if (e.key === 'ArrowUp') { e.preventDefault(); onReading(Math.max(-1, reading - 1)); }
        }}>
        {months.map(m => <span key={m} className="plan-timeline-month" style={{top: `${m * 100}%`}} />)}
        {goals.map((g, i) => {
          const end = plan.finish[g.id] != null ? plan.lessons[plan.finish[g.id]].to / span : 1;
          return <i key={g.id} className="plan-timeline-rail" style={{left: `calc(50% + ${(i - (goals.length - 1) / 2) * 7}px)`, height: `${end * 100}%`, background: g.color, color: g.color}} />;
        })}
        <b className="plan-timeline-knob" style={{top: `${at * 100}%`}}><span>{label}</span></b>
      </div>
    </div>
  );
}
