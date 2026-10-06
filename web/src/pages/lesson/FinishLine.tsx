// A lesson's finish line: how far the learner is (sections reached), where they stopped last time,
// and the finish moment that leads to the next lesson and the plan.
import {useEffect, useRef, useState} from 'react';
import {useLocation, useRevalidator} from 'react-router';
import {ApiError, bootstrap, postJson} from '../../api';
import PlanEditor from '../../components/PlanEditor';
import {plural} from '../../format';
import {AppLink} from '../../links';
import {formatSession, nextSession} from '../../plan';
import type {LessonData, Plan} from '../../types';

export interface Checkpoints {
  titles: string[];
  total: number;
  /** Section being read now (1-based; 0 while still above the first one). */
  current: number;
  /** Furthest section ever reached, including earlier visits. */
  furthest: number;
  anchor: (index: number) => string;
}

/** Tracks the section being read (its heading has passed the upper third of the screen) and saves it. */
export function useCheckpoints(data: LessonData): Checkpoints {
  const steps = data.lesson.steps.length;
  // Only lessons with real sections get a rail; "Практика" alone isn't a journey.
  const titles = steps ? data.checkpoints ?? [] : [];
  const total = titles.length;
  const anchor = (index: number) => (index <= steps ? `step-${index}` : 'practice');
  const [current, setCurrent] = useState(0);
  const [furthest, setFurthest] = useState(Math.min(data.step_progress?.furthest ?? 0, total));
  const saved = useRef(data.step_progress?.last ?? 0);

  useEffect(() => {
    if (!total) return;
    const elements = Array.from({length: total}, (_, i) => document.getElementById(anchor(i + 1))).filter((e): e is HTMLElement => !!e);
    const indexOf = (element: HTMLElement) => (element.id === 'practice' ? total : Number(element.id.slice(5)));
    let frame = 0;
    function update() {
      frame = 0;
      const line = window.innerHeight * 0.35;
      let at = 0;
      for (const element of elements) if (element.getBoundingClientRect().top <= line) at = indexOf(element);
      // At the very bottom, a heading that can no longer scroll up to the line still counts.
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) {
        for (const element of elements) if (element.getBoundingClientRect().top < window.innerHeight) at = Math.max(at, indexOf(element));
      }
      setCurrent(at);
    }
    const schedule = () => { if (!frame) frame = requestAnimationFrame(update); };
    update();
    window.addEventListener('scroll', schedule, {passive: true});
    window.addEventListener('resize', schedule);
    return () => { cancelAnimationFrame(frame); window.removeEventListener('scroll', schedule); window.removeEventListener('resize', schedule); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [total, data.lesson.id]);

  useEffect(() => { if (current > furthest) setFurthest(current); }, [current, furthest]);

  // Save where the learner is once they settle there (not on every heading scrolled past).
  useEffect(() => {
    if (!bootstrap.user || !current || current === saved.current) return;
    const timer = setTimeout(() => {
      saved.current = current;
      postJson(`/api/lessons/${encodeURIComponent(data.lesson.id)}/step`, {step: current}).catch(() => { /* resume point only */ });
    }, 1500);
    return () => clearTimeout(timer);
  }, [current, data.lesson.id]);

  return {titles, total, current, furthest, anchor};
}

function Meter({value, total}: {value: number; total: number}) {
  return <span className="lesson-meter" aria-hidden="true"><span style={{width: `${total ? (100 * value) / total : 0}%`}} /></span>;
}

/** "В этом уроке" list: reached sections are ticked, the one being read is highlighted. */
export function CheckpointList({points}: {points: Checkpoints}) {
  return (
    <ol className="checkpoints">
      {points.titles.map((title, i) => {
        const index = i + 1;
        return (
          <li key={index} className={index <= points.furthest ? 'is-reached' : undefined}>
            <a href={`#${points.anchor(index)}`} aria-current={index === points.current ? 'true' : undefined}>{title}</a>
          </li>
        );
      })}
    </ol>
  );
}

export function TocHeading({points}: {points: Checkpoints}) {
  return (
    <>
      <p className="lesson-toc-title">В этом уроке <span className="lesson-toc-count">{points.furthest} / {points.total}</span></p>
      <Meter value={points.furthest} total={points.total} />
    </>
  );
}

/** Phones and tablets (the sidebar sits above the lesson there): a slim bar that follows the reader. */
export function ProgressBar({points}: {points: Checkpoints}) {
  if (!points.total) return null;
  const index = Math.max(points.current, 1);
  function openContents() {
    const toc = document.querySelector<HTMLDetailsElement>('.lesson-toc-mobile');
    if (!toc) return;
    toc.open = true;
    toc.scrollIntoView({block: 'start'});
  }
  return (
    <div className={'lesson-progress' + (points.current ? ' is-visible' : '')}>
      <button type="button" onClick={openContents} aria-label={`Раздел ${index} из ${points.total}. Открыть содержание урока`}>
        <span className="lesson-progress-count">{index} / {points.total}</span>
        <span className="lesson-progress-title">{points.titles[index - 1]}</span>
      </button>
      <Meter value={points.furthest} total={points.total} />
    </div>
  );
}

/** "Вы остановились здесь": on reopening a lesson that was left halfway. */
export function ResumeBanner({data, points}: {data: LessonData; points: Checkpoints}) {
  const {hash} = useLocation();
  const [hidden, setHidden] = useState(false);
  const last = Math.min(data.step_progress?.last ?? 0, points.total);
  if (hidden || hash || last < 2 || data.progress?.completed) return null;
  return (
    <div className="resume-banner" role="note">
      <p><span className="eyebrow">Вы остановились здесь</span><strong>Раздел {last} из {points.total}: {points.titles[last - 1]}</strong></p>
      <div className="actions">
        <AppLink className="button" to={`#${points.anchor(last)}`} onClick={() => setHidden(true)}>Продолжить отсюда ↓</AppLink>
        <button type="button" className="link-button" onClick={() => setHidden(true)}>Читать с начала</button>
      </div>
    </div>
  );
}

function PlanNote({plan}: {plan: Plan}) {
  // A plan chosen right here keeps the editor open: its calendar links are the next step.
  const [hadPlan] = useState(plan.days.length > 0);
  const [current, setCurrent] = useState(plan);
  const next = nextSession(current);
  if (hadPlan && next) {
    return (
      <section className="finish-plan" aria-label="План занятий">
        <p>По плану следующее занятие — <strong>{formatSession(next)}</strong>. <AppLink to="/preferences#plan">Изменить план</AppLink></p>
      </section>
    );
  }
  return (
    <section className="finish-plan" aria-labelledby="finish-plan-title">
      <h3 id="finish-plan-title">{next ? `Следующее занятие — ${formatSession(next)}` : 'Когда следующий урок?'}</h3>
      {!next && <p className="small">Выберите дни — добавим занятия в ваш календарь. Пропуск ничего не обнуляет.</p>}
      <PlanEditor initial={current} compact onSaved={setCurrent} />
    </section>
  );
}

/** The finish moment: what was done, course progress, the next lesson and when it will happen. */
function FinishDialog({data, points, practiceSaved, onClose}: {data: LessonData; points: Checkpoints; practiceSaved: boolean; onClose: () => void}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [filled, setFilled] = useState(false);
  useEffect(() => {
    const dialog = ref.current;
    if (dialog && !dialog.open) dialog.showModal();
    const frame = requestAnimationFrame(() => setFilled(true));   // let the course bar grow into place
    return () => cancelAnimationFrame(frame);
  }, []);
  const {lesson, outline, following} = data;
  const lessons = outline ? outline.modules.flatMap(m => m.lessons) : [];
  const done = lessons.filter(l => l.state === 'done' || l.id === lesson.id).length;
  const available = outline?.available ?? 0;
  const sections = points.total ? `${Math.max(points.furthest, 1)} из ${points.total} ${plural(points.total, 'раздела', 'разделов', 'разделов')}` : '';
  return (
    <dialog ref={ref} className="finish-dialog" aria-labelledby="finish-title" onClose={onClose}>
      <button type="button" className="finish-close" aria-label="Закрыть" onClick={() => ref.current?.close()}>×</button>
      <svg className="finish-mark" viewBox="0 0 52 52" aria-hidden="true"><circle cx="26" cy="26" r="23" /><path d="M15.5 27.5l7 7 14-15" /></svg>
      <p className="eyebrow">Урок пройден</p>
      <h2 id="finish-title">{lesson.title}</h2>
      <p className="finish-what">
        {sections && `Вы прошли ${sections}`}{sections && practiceSaved ? ' и сохранили практику' : !sections && practiceSaved ? 'Практика сохранена' : ''}.
        {' '}Урок отмечен на карте.
      </p>
      {outline && available > 0 && (
        <div className="finish-course">
          <p><span>{data.course.title}</span><span>{Math.min(done, available)} из {available} {plural(available, 'открытого урока', 'открытых уроков', 'открытых уроков')}</span></p>
          <span className="lesson-meter"><span style={{width: `${(100 * (filled ? done : Math.max(done - 1, 0))) / available}%`}} /></span>
        </div>
      )}
      {following ? (
        <section className="finish-next" aria-labelledby="finish-next-title">
          <p className="eyebrow">Дальше</p>
          <h3 id="finish-next-title">{following.title}</h3>
          <p>{following.objective}</p>
          <p className="small">{following.minutes} минут{following.locked ? ' · урок клуба' : ''}</p>
          {following.locked
            ? <AppLink className="button" to={`/membership?next=/lessons/${following.id}`}>Открыть доступ к уроку</AppLink>
            : <AppLink className="button" to={`/lessons/${following.id}`} autoFocus>Начать сейчас →</AppLink>}
        </section>
      ) : (
        <section className="finish-next">
          <p className="eyebrow">Дальше</p>
          <p>Это последний открытый урок курса.</p>
          <AppLink className="button" to={`/?view=map#course-${data.course.id}`}>Выбрать следующий шаг на карте →</AppLink>
        </section>
      )}
      {data.plan && <PlanNote plan={data.plan} />}
    </dialog>
  );
}

/** End of the lesson: a checklist of what's done and "Завершить урок", then the finish moment. */
export function FinishPanel({data, points, practiceSaved}: {data: LessonData; points: Checkpoints; practiceSaved: boolean}) {
  const [completed, setCompleted] = useState(!!data.progress?.completed);
  const [celebrate, setCelebrate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const revalidator = useRevalidator();
  async function mark(value: boolean) {
    setBusy(true); setError('');
    try {
      await postJson(`/api/lessons/${encodeURIComponent(data.lesson.id)}/completion`, {completed: value});
      setCompleted(value);
      setCelebrate(value);
      revalidator.revalidate();   // course outline and map states
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Не удалось сохранить.');
    } finally {
      setBusy(false);
    }
  }
  if (!bootstrap.user) {
    return (
      <section className="panel finish">
        <h2>Финиш урока</h2>
        <p>Войдите, чтобы отмечать пройденные уроки и продолжать с того же места на любом устройстве.</p>
        <AppLink className="button" to={`/login?next=/lessons/${data.lesson.id}`}>Войти</AppLink>
      </section>
    );
  }
  const allRead = points.total > 0 && points.furthest >= points.total;
  const following = data.following;
  return (
    <section className={'panel finish' + (completed ? ' is-done' : '')} id="finish" aria-labelledby="finish-heading">
      {completed ? (
        <>
          <p className="eyebrow">Финиш урока</p>
          <h2 id="finish-heading"><span className="finish-tick" aria-hidden="true">✓</span> Урок пройден</h2>
          <p>
            Отмечен на карте.{' '}
            {following && !following.locked
              ? <>Дальше: <AppLink to={`/lessons/${following.id}`}>{following.title} →</AppLink></>
              : following ? <>Дальше — урок клуба: <AppLink to={`/lessons/${following.id}`}>{following.title}</AppLink></> : 'Это последний открытый урок курса.'}
          </p>
          <button type="button" className="link-button" onClick={() => mark(false)} disabled={busy}>Вернуть в работу</button>
        </>
      ) : (
        <>
          <p className="eyebrow">Финиш урока</p>
          <h2 id="finish-heading">{allRead && (practiceSaved || !data.lesson.task) ? 'Всё готово — завершите урок' : 'Готовы завершить?'}</h2>
          <ul className="finish-checks">
            {points.total > 0 && <li className={allRead ? 'is-done' : undefined}>Разделы урока: {Math.min(points.furthest, points.total)} из {points.total}</li>}
            {data.lesson.task && <li className={practiceSaved ? 'is-done' : undefined}>{practiceSaved ? 'Практика сохранена' : 'Практика ещё не сохранена — можно вернуться к ней позже'}</li>}
          </ul>
          <button type="button" className="button" onClick={() => mark(true)} disabled={busy}>Завершить урок</button>
        </>
      )}
      {error && <p className="small" role="alert">{error}</p>}
      {celebrate && <FinishDialog data={data} points={points} practiceSaved={practiceSaved} onClose={() => setCelebrate(false)} />}
    </section>
  );
}
