import {useEffect, useMemo, useRef, useState} from 'react';
import {useLoaderData, useNavigate, type LoaderFunctionArgs} from 'react-router';
import {ApiError, getJson, postJson, putJson} from '../api';
import {CalendarLinks} from '../components/PlanEditor';
import GoalRing from '../components/GoalRing';
import SkillRadar from '../components/SkillRadar';
import {DEADLINE_LABEL, GOAL_COLORS, weeksLabel, type JourneyAnswers, type JourneyData, type JourneyGoalOption, type JourneyOptions, type JourneyPath, type Pace} from '../journey';
import {DAYS_SHORT} from '../plan';
import type {Plan} from '../types';
import {useTitle} from '../useTitle';

// Onboarding v2 (club/journey.py): getting to know the learner and building their path.
// hello → goals → «Строим твой путь» → level and deadlines (with a first look at the path) → plan and calendar.
// Answers are saved as the learner goes; finishing (or skipping) opens the rest of the site.

export const onboardingLoader = ({request}: LoaderFunctionArgs) => getJson<JourneyData>('/api/app/journey', request.signal);

type Step = 'hello' | 'goals' | 'building' | 'level' | 'plan';
const STEP_NUMBER: Record<Step, number> = {hello: 1, goals: 2, building: 2, level: 3, plan: 4};
const LEVELS = [
  ['start', 'Только начинаю'],
  ['sometimes', 'Иногда пользуюсь'],
  ['work', 'Использую в работе'],
  ['build', 'Делаю на ИИ проекты'],
] as const;
// Study days suggested for a number of sessions a week (ISO weekdays).
const DAYS_FOR: Record<number, number[]> = {1: [3], 2: [2, 4], 3: [1, 3, 5], 4: [1, 2, 4, 6], 5: [1, 2, 3, 4, 5], 6: [1, 2, 3, 4, 5, 6], 7: [1, 2, 3, 4, 5, 6, 7]};
const BUILDING_LINES = ['Смотрим, какие навыки нужны твоим целям', 'Подбираем уроки и их порядок', 'Считаем, сколько времени займёт путь'];

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export default function Onboarding() {
  const initial = useLoaderData() as JourneyData;
  const navigate = useNavigate();
  const {options} = initial;
  const [answers, setAnswers] = useState<JourneyAnswers>({beginner: true, sliders: {}, deadlines: {}, ...initial.answers});
  const [step, setStep] = useState<Step>(() => (initial.answers.step as Step) && initial.answers.step !== 'building' && initial.answers.goals?.length ? initial.answers.step as Step : 'hello');
  const [path, setPath] = useState<JourneyPath | null>(initial.path);
  const [error, setError] = useState('');
  useTitle('Знакомство');
  const goals = answers.goals ?? [];
  const number = STEP_NUMBER[step];

  async function save(patch: JourneyAnswers & {status?: string}) {
    setAnswers(a => ({...a, ...patch}));
    try {
      await putJson('/api/app/journey', patch);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Не удалось сохранить. Проверьте соединение.');
    }
  }
  async function skip() {
    await putJson('/api/app/journey', {status: 'skipped'}).catch(() => undefined);
    navigate('/');
  }
  async function build() {
    setStep('building');
    setError('');
    const started = Date.now();
    try {
      const [{path: next}] = await Promise.all([
        postJson<{path: JourneyPath}>('/api/app/journey/preview', {...answers, goals}),
        putJson('/api/app/journey', {goals, custom: answers.custom ?? '', step: 'level'}),
      ]);
      await delay(Math.max(0, 3200 - (Date.now() - started)));
      setPath(next);
      setStep('level');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Не удалось построить путь. Попробуйте ещё раз.');
      setStep('goals');
    }
  }

  return (
    <div className="journey">
      <div className="journey-progress" aria-label={`Шаг ${number} из 4`}>
        {[1, 2, 3, 4].map(n => <span key={n} className={n <= number ? 'is-on' : undefined} />)}
      </div>
      {error && <p className="notice error" role="alert">{error}</p>}
      {step === 'hello' && <Hello onNext={() => { setStep('goals'); void save({step: 'goals'}); }} onSkip={skip} />}
      {step === 'goals' && (
        <Goals data={initial} answers={answers} onChange={patch => setAnswers(a => ({...a, ...patch}))} onNext={build}
          onBack={() => setStep('hello')} />
      )}
      {step === 'building' && <Building skills={options.skills} goals={goals.map(id => options.goals.find(g => g.id === id)).filter(g => !!g)} />}
      {step === 'level' && path && (
        <Level data={initial} answers={answers} path={path} onPath={setPath} onChange={patch => setAnswers(a => ({...a, ...patch}))}
          onBack={() => setStep('goals')}
          onNext={() => { setStep('plan'); void save({beginner: answers.beginner, sliders: answers.sliders, deadlines: answers.deadlines, step: 'plan'}); }} />
      )}
      {step === 'plan' && path && (
        <Schedule answers={answers} path={path} onBack={() => setStep('level')}
          onDone={async pace => {
            await putJson('/api/app/journey', {pace, status: 'done', step: 'done'});
            navigate('/path');
          }} />
      )}
    </div>
  );
}

function Hello({onNext, onSkip}: {onNext: () => void; onSkip: () => void}) {
  return (
    <section className="journey-hello">
      <h1>Давай познакомимся и&nbsp;сделаем твой путь персональным</h1>
      <p className="journey-lead">
        Расскажи, к чему ты идёшь и с чем уже знаком, — мы соберём из уроков AI Room маршрут под тебя: какие навыки прокачать,
        в каком порядке и сколько времени это займёт. Ответы сохранятся в твоём профиле и будут влиять на рекомендации и цели.
        Их всегда можно изменить в настройках, а путь перестроится сам.
      </p>
      <div className="journey-actions">
        <button type="button" className="button" onClick={onNext}>Начнём →</button>
        <button type="button" className="link-button" onClick={onSkip}>Пропустить</button>
      </div>
    </section>
  );
}

function Goals({data, answers, onChange, onNext, onBack}: {
  data: JourneyData; answers: JourneyAnswers; onChange: (patch: JourneyAnswers) => void; onNext: () => void; onBack: () => void;
}) {
  const chosen = answers.goals ?? [];
  const max = data.options.max_goals;
  const [customNote, setCustomNote] = useState('');
  function toggle(id: string) {
    if (chosen.includes(id)) onChange({goals: chosen.filter(g => g !== id)});
    else if (chosen.length < max) onChange({goals: [...chosen, id]});
  }
  async function analyse() {
    try {
      await getJson('/api/app/journey/custom');
    } catch (e) {
      setCustomNote(e instanceof ApiError ? e.message : 'Нужна подписка для анализа');
    }
  }
  return (
    <section className="journey-goals">
      <h1>Ради чего ты здесь?</h1>
      <p className="journey-lead">Выбери до {max} целей. Лучше выбрать близкие к твоим, даже если они совпадают не на&nbsp;100%, — так путь получится точнее, чем без цели.</p>
      <GoalRing goals={data.options.goals} chosen={chosen} max={max} onToggle={toggle} />
      <div className="journey-custom">
        <label htmlFor="custom-goal">Или опиши свою цель</label>
        <textarea id="custom-goal" rows={2} maxLength={600} value={answers.custom ?? ''} placeholder="Например: хочу открыть студию ИИ-видео для свадеб"
          onChange={event => onChange({custom: event.target.value})} />
        <p className="small">Сохраним её в профиле. {answers.custom?.trim() && <button type="button" className="link-button" onClick={analyse}>Построить путь по своей цели</button>}</p>
        {customNote && <p className="journey-paywall" role="status"><strong>{customNote}</strong> Персональный путь по своей цели собирается в подписке. Пока выбери близкие цели из списка.</p>}
      </div>
      <div className="journey-actions">
        <button type="button" className="button" disabled={!chosen.length} onClick={onNext}>Построить мой путь →</button>
        <button type="button" className="link-button" onClick={onBack}>Назад</button>
      </div>
    </section>
  );
}

// The eight skills as a radar, each chosen goal's shape growing to the points it needs.
function Building({goals, skills}: {goals: JourneyGoalOption[]; skills: JourneyOptions['skills']}) {
  const [line, setLine] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setLine(i => Math.min(i + 1, BUILDING_LINES.length - 1)), 1050);
    return () => clearInterval(timer);
  }, []);
  return (
    <section className="journey-building" aria-live="polite">
      <div className="journey-building-art" aria-hidden="true">
        <div className="journey-building-goals">{goals.map((g, i) => <span key={g.id} style={{animationDelay: `${i * .2}s`}}>{g.title}</span>)}</div>
        <SkillRadar skills={skills} goals={goals.map((g, i) => ({id: g.id, color: GOAL_COLORS[i % GOAL_COLORS.length], targets: g.targets}))}
          label={`Навыки для целей: ${goals.map(g => g.title).join(', ')}`} />
      </div>
      <h1>Строим твой путь</h1>
      <p className="journey-lead">{BUILDING_LINES[line]}…</p>
    </section>
  );
}

function Level({data, answers, path, onPath, onChange, onNext, onBack}: {
  data: JourneyData; answers: JourneyAnswers; path: JourneyPath; onPath: (p: JourneyPath) => void;
  onChange: (patch: JourneyAnswers) => void; onNext: () => void; onBack: () => void;
}) {
  const [level, setLevel] = useState<string>(answers.beginner === false ? 'work' : 'start');
  const sliders = answers.sliders ?? {};
  const deadlines = answers.deadlines ?? {};
  // The path follows every answer (a short pause, then one request).
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    const timer = setTimeout(() => {
      postJson<{path: JourneyPath}>('/api/app/journey/preview', {goals: answers.goals, beginner: answers.beginner, sliders, deadlines})
        .then(r => onPath(r.path), () => undefined);
    }, 350);
    return () => clearTimeout(timer);
  }, [answers.beginner, JSON.stringify(sliders), JSON.stringify(deadlines)]);  // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <section className="journey-level">
      <div className="journey-level-map">
        <SkillRadar skills={data.options.skills} goals={path.goals} start={path.start}
          label={`Навыки: где ты сейчас и что нужно для целей ${path.goals.map(g => g.title).join(', ')}`} />
        <ul className="journey-legend">
          <li><i className="is-now" />Ты сейчас{Object.values(path.start).some(Boolean) ? '' : ' — с нуля'}</li>
          {path.goals.map(g => <li key={g.id}><i style={{background: g.color}} />{g.title} · {g.lessons} уроков</li>)}
        </ul>
        <p className="small">Твой путь: {path.lessons.length} уроков, около {Math.round(path.minutes / 60)} часов{path.coming ? ` · ${path.coming} из них откроются позже` : ''}.</p>
      </div>
      <div className="journey-level-questions">
        <h1>Почти готово</h1>
        <fieldset className="journey-question">
          <legend>Какой у тебя опыт с ИИ?</legend>
          <div className="journey-options">
            {LEVELS.map(([id, label]) => (
              <button key={id} type="button" aria-pressed={level === id} className={level === id ? 'is-on' : undefined}
                onClick={() => { setLevel(id); onChange({beginner: id === 'start'}); }}>{label}</button>
            ))}
          </div>
          {level !== 'start' && (
            <div className="journey-sliders">
              <p className="small">Оцени себя от 0 до 5 — так путь не будет повторять то, что ты уже умеешь.</p>
              {data.options.sliders.map(s => (
                <label key={s.id} className="journey-slider">
                  <span>{s.title}</span>
                  <input type="range" min={0} max={5} step={1} value={sliders[s.id] ?? 0}
                    onChange={event => onChange({sliders: {...sliders, [s.id]: Number(event.target.value)}})} />
                  <output>{sliders[s.id] ?? 0}</output>
                </label>
              ))}
            </div>
          )}
        </fieldset>
        <fieldset className="journey-question">
          <legend>За какое время хочешь прийти к целям?</legend>
          {path.goals.map(goal => (
            <div key={goal.id} className="journey-deadline">
              <span><i style={{background: goal.color}} />{goal.title}</span>
              <div className="journey-options is-small">
                {data.options.deadlines.map(weeks => (
                  <button key={weeks} type="button" aria-pressed={deadlines[goal.id] === weeks} className={deadlines[goal.id] === weeks ? 'is-on' : undefined}
                    onClick={() => onChange({deadlines: {...deadlines, [goal.id]: weeks}})}>{DEADLINE_LABEL[weeks]}</button>
                ))}
              </div>
            </div>
          ))}
        </fieldset>
        <div className="journey-actions">
          <button type="button" className="button" onClick={onNext}>Подобрать расписание →</button>
          <button type="button" className="link-button" onClick={onBack}>Назад к целям</button>
        </div>
      </div>
    </section>
  );
}

function Schedule({answers, path, onBack, onDone}: {answers: JourneyAnswers; path: JourneyPath; onBack: () => void; onDone: (pace: Pace) => Promise<void>}) {
  const options = path.plans.options;
  const needed = path.plans.needed_minutes_per_week;
  const recommended = needed ? options.find(o => o.minutes_per_week >= needed)?.id ?? 'intense' : 'steady';
  const [choice, setChoice] = useState<string>(answers.pace ? 'custom' : recommended);
  const [custom, setCustom] = useState<Pace>(answers.pace ?? {sessions: 3, session_minutes: 30});
  const [customPath, setCustomPath] = useState<JourneyPath | null>(null);
  const [time, setTime] = useState('19:00');
  const [plan, setPlan] = useState<Plan | null>(null);
  const [busy, setBusy] = useState(false);
  const pace: Pace = choice === 'custom' ? custom : (({sessions, session_minutes}) => ({sessions, session_minutes}))(options.find(o => o.id === choice)!);
  const days = DAYS_FOR[pace.sessions];
  useEffect(() => {
    if (choice !== 'custom') return;
    const timer = setTimeout(() => {
      postJson<{path: JourneyPath}>('/api/app/journey/preview', {pace: custom}).then(r => setCustomPath(r.path), () => undefined);
    }, 250);
    return () => clearTimeout(timer);
  }, [choice, custom.sessions, custom.session_minutes]);  // eslint-disable-line react-hooks/exhaustive-deps
  const goalTitle = useMemo(() => Object.fromEntries(path.goals.map(g => [g.id, g])), [path]);

  async function addToCalendar() {
    setBusy(true);
    try {
      setPlan(await putJson<Plan>('/api/app/plan', {days, time}));
    } finally {
      setBusy(false);
    }
  }
  const verdict = (weeks: number | null, goalId: string) => {
    const deadline = goalTitle[goalId]?.deadline;
    if (weeks == null) return <span className="is-late">часть уроков ещё готовится</span>;
    return <span className={deadline && weeks > deadline ? 'is-late' : 'is-ok'}>{weeksLabel(weeks)}{deadline ? (weeks <= deadline ? ' ✓' : ` — позже срока (${DEADLINE_LABEL[deadline]?.toLowerCase()})`) : ''}</span>;
  };
  return (
    <section className="journey-plan">
      <h1>Как будем учиться?</h1>
      <p className="journey-lead">Три расписания под твой путь. Выбери то, что выдержишь, — регулярность важнее скорости.
        {needed ? ` Чтобы успеть ко всем срокам, нужно около ${needed} минут в неделю.` : ''}</p>
      <div className="journey-plan-options" role="radiogroup" aria-label="Расписание">
        {options.map(o => (
          <button key={o.id} type="button" role="radio" aria-checked={choice === o.id} className={'journey-plan-card' + (choice === o.id ? ' is-on' : '')}
            onClick={() => setChoice(o.id)}>
            <strong>{o.title}{o.id === recommended && <em>советуем</em>}</strong>
            <span className="journey-plan-pace">{o.sessions} × {o.session_minutes} мин в неделю</span>
            <ul>{Object.entries(o.goals).map(([id, g]) => <li key={id}><i style={{background: goalTitle[id]?.color}} />{verdict(g.weeks, id)}</li>)}</ul>
          </button>
        ))}
        <div className={'journey-plan-card is-custom' + (choice === 'custom' ? ' is-on' : '')} role="radio" aria-checked={choice === 'custom'} tabIndex={0}
          onClick={() => setChoice('custom')} onKeyDown={e => { if (e.key === ' ' || e.key === 'Enter') setChoice('custom'); }}>
          <strong>Свой темп</strong>
          <label className="journey-slider"><span>Занятий в неделю</span>
            <input type="range" min={1} max={7} value={custom.sessions} onChange={e => { setChoice('custom'); setCustom(c => ({...c, sessions: Number(e.target.value)})); }} />
            <output>{custom.sessions}</output></label>
          <label className="journey-slider"><span>Минут за раз</span>
            <input type="range" min={10} max={90} step={5} value={custom.session_minutes} onChange={e => { setChoice('custom'); setCustom(c => ({...c, session_minutes: Number(e.target.value)})); }} />
            <output>{custom.session_minutes}</output></label>
          {choice === 'custom' && customPath?.pace && (
            <ul>{Object.entries(customPath.pace.reached).map(([id, weeks]) => <li key={id}><i style={{background: goalTitle[id]?.color}} />{verdict(weeks, id)}</li>)}</ul>
          )}
        </div>
      </div>
      <div className="journey-calendar">
        <p><strong>Напоминания в календаре.</strong> {pace.sessions} {pace.sessions === 1 ? 'занятие' : pace.sessions < 5 ? 'занятия' : 'занятий'} в неделю:
          {' '}{days.map(d => DAYS_SHORT[d - 1]).join(', ')} в
          {' '}<select value={time} onChange={e => { setTime(e.target.value); setPlan(null); }} aria-label="Время занятий">
            {['07:00', '08:00', '09:00', '12:00', '13:00', '18:00', '19:00', '20:00', '21:00', '22:00'].map(t => <option key={t}>{t}</option>)}
          </select></p>
        {plan ? <CalendarLinks plan={plan} /> : <button type="button" className="button secondary" disabled={busy} onClick={addToCalendar}>Добавить в календарь</button>}
      </div>
      <div className="journey-actions">
        <button type="button" className="button" onClick={() => onDone(pace)}>Открыть мой путь →</button>
        <button type="button" className="link-button" onClick={onBack}>Назад</button>
      </div>
    </section>
  );
}
