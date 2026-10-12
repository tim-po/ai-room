import {useEffect, useRef, useState} from 'react';
import {useLoaderData, type LoaderFunctionArgs} from 'react-router';
import {bootstrap, getJson} from '../api';
import type {JourneyData, PathLesson} from '../journey';
import {AppLink} from '../Shell';
import {useTitle} from '../useTitle';

// A lesson that isn't on the platform yet (club/tree.py upcoming): it opens like a lesson, with its place in the
// course, what it will train and an empty page standing in for the content, so links to it work everywhere.

interface UpcomingData {
  title: string; minutes: number | null;
  course: {id: string; title: string; url: string | null; topic: string};
  module: {index: number; title: string; count: number};
  position: number;
  lessons: {title: string; url: string | null; state: string; here: boolean}[];
  skills: {id: string; title: string; points: number}[];
}

export const upcomingLoader = ({request, params}: LoaderFunctionArgs) =>
  getJson<UpcomingData>(`/api/app/upcoming/${params.course}/${params.module}/${params.lesson}`, request.signal);

/** Demo: «finishing» a lesson that isn't here yet shows the finish screen with the next step of the learner's
 *  path (the lesson after this one on it), so a walk through the path doesn't stop at a placeholder.
 *  Nothing is recorded — there is no lesson to mark done. */
function DemoFinish({data, onClose}: {data: UpcomingData; onClose: () => void}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [next, setNext] = useState<PathLesson | null | undefined>(undefined);
  useEffect(() => {
    if (ref.current && !ref.current.open) ref.current.showModal();
    if (!bootstrap.user) { setNext(null); return; }
    getJson<JourneyData>('/api/app/journey').then(journey => {
      const lessons = journey.path?.lessons ?? [];
      const here = lessons.findIndex(l => l.key === `${data.course.id}:${data.module.index}:${data.position}`);
      setNext(lessons.slice(here + 1).find(l => l.state !== 'done' && l.url) ?? null);
    }, () => setNext(null));
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <dialog ref={ref} className="finish-dialog" aria-labelledby="finish-title" onClose={onClose}>
      <button type="button" className="finish-close" aria-label="Закрыть" onClick={() => ref.current?.close()}>×</button>
      <svg className="finish-mark" viewBox="0 0 52 52" aria-hidden="true"><circle cx="26" cy="26" r="23" /><path d="M15.5 27.5l7 7 14-15" /></svg>
      <p className="eyebrow">Урок пройден</p>
      <h2 id="finish-title">{data.title}</h2>
      <p className="finish-what">Демо: урок ещё готовится, поэтому отметка не сохраняется.</p>
      {next ? (
        <section className="finish-next" aria-labelledby="finish-next-title">
          <p className="eyebrow">Дальше по твоему пути</p>
          <h3 id="finish-next-title">{next.title}</h3>
          <p className="small">{[next.course_title, next.module_title, `${next.minutes} мин`].filter(Boolean).join(' · ')}{next.state === 'locked' ? ' · урок клуба' : next.state === 'coming' ? ' · готовится' : ''}</p>
          {next.state === 'locked'
            ? <AppLink className="button" to={`/membership?next=${next.url}`}>Открыть доступ к уроку</AppLink>
            : <AppLink className="button" to={next.url!}>Начать →</AppLink>}
        </section>
      ) : next === null && (
        <section className="finish-next">
          <p className="eyebrow">Дальше</p>
          <p>{bootstrap.user ? 'На твоём пути это последний урок.' : 'Выбери цели — и мы проложим путь из уроков.'}</p>
          <AppLink className="button" to={bootstrap.user ? '/path' : '/login?next=/path'}>Открыть мой путь →</AppLink>
        </section>
      )}
    </dialog>
  );
}

export default function Upcoming() {
  const data = useLoaderData() as UpcomingData;
  useTitle(data.title);
  const [finishing, setFinishing] = useState(false);
  return (
    <article className="upcoming">
      <nav className="upcoming-crumbs" aria-label="Где этот урок">
        <span>{data.course.topic}</span> ›{' '}
        {data.course.url ? <AppLink to={data.course.url}>{data.course.title}</AppLink> : <AppLink to={`/map#course-${data.course.id}`}>{data.course.title}</AppLink>} ›{' '}
        <span>Модуль {data.module.index + 1}. {data.module.title}</span>
      </nav>
      <header className="upcoming-head">
        <p className="upcoming-badge">Урок готовится</p>
        <h1>{data.title}</h1>
        <p className="upcoming-meta">Урок {data.position + 1} из {data.lessons.length}{data.minutes ? ` · около ${data.minutes} мин` : ''}</p>
      </header>

      <div className="upcoming-grid">
        <div className="upcoming-body" aria-label="Содержимое урока появится здесь">
          <div className="upcoming-video"><span>Видео и материалы урока появятся здесь</span></div>
          <div className="upcoming-lines" aria-hidden="true"><i /><i /><i /><i /><i /></div>
          <p className="upcoming-note">Мы ещё собираем этот урок. Он уже стоит на своём месте в курсе и в твоём пути — когда он выйдет, здесь будет полное содержимое.</p>
          <button type="button" className="button" onClick={() => setFinishing(true)}>Завершить урок</button>
        </div>
        <aside className="upcoming-side">
          {data.skills.length > 0 && (
            <section>
              <h2>Что прокачает</h2>
              <ul className="upcoming-skills">
                {data.skills.map(s => <li key={s.id}><span>{s.title}</span><b style={{width: `${Math.min(100, s.points * 8)}%`}} /></li>)}
              </ul>
            </section>
          )}
          <section>
            <h2>Уроки модуля</h2>
            <ol className="upcoming-lessons">
              {data.lessons.map((l, i) => (
                <li key={i} className={(l.here ? 'is-here ' : '') + `is-${l.state}`}>
                  {l.url && !l.here ? <AppLink to={l.url}>{l.title}</AppLink> : <span>{l.title}</span>}
                  {l.state === 'coming' && <small>скоро</small>}
                </li>
              ))}
            </ol>
          </section>
          <AppLink to="/path">Где это на моём пути →</AppLink>
        </aside>
      </div>
      {finishing && <DemoFinish key={data.title} data={data} onClose={() => setFinishing(false)} />}
    </article>
  );
}
