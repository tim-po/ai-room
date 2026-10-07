import {useState} from 'react';
import {useLoaderData, type LoaderFunctionArgs} from 'react-router';
import {ApiError, bootstrap, getJson, postJson} from '../api';
import Outline from '../components/Outline';
import {plural} from '../format';
import {AppLink} from '../Shell';
import type {CourseData, CourseLesson} from '../types';
import {useTitle} from '../useTitle';

export const courseLoader = ({params, request}: LoaderFunctionArgs) =>
  getJson<CourseData>(`/api/app/courses/${encodeURIComponent(params.id!)}`, request.signal);

function Favourite({courseId, initial}: {courseId: string; initial: boolean}) {
  const [saved, setSaved] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function toggle() {
    setBusy(true); setError('');
    try {
      const result = await postJson<{favourite: boolean}>(`/courses/${encodeURIComponent(courseId)}/favourite`, {saved: !saved});
      setSaved(result.favourite);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Не удалось сохранить.');
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <button type="button" className="button secondary" onClick={toggle} disabled={busy} aria-pressed={saved}>{saved ? 'Убрать из избранного' : 'В избранное'}</button>
      {error && <span className="small" role="alert">{error}</span>}
    </>
  );
}

/** Lesson list for courses that aren't in the catalogue (no map outline). */
function Curriculum({lessons}: {lessons: CourseLesson[]}) {
  const modules: {id: string; title: string; lessons: CourseLesson[]}[] = [];
  for (const lesson of lessons) {
    const last = modules[modules.length - 1];
    if (last?.id === lesson.module_id) last.lessons.push(lesson);
    else modules.push({id: lesson.module_id, title: lesson.module_title, lessons: [lesson]});
  }
  return (
    <>
      {modules.map((module, index) => (
        <details key={module.id} className="module" open={index === 0}>
          <summary>{module.title}</summary>
          <div className="curriculum">
            {module.lessons.map(l => (
              <AppLink key={l.id} className="lesson-row" to={`/lessons/${l.id}`}>
                <span className="lesson-marker" aria-hidden="true">{l.completed ? '✓' : l.locked ? '○' : '↗'}</span>
                <span>
                  {l.title}
                  <small>
                    {l.minutes} мин · {l.video ? 'Видео + текст' : 'Текст'} · {l.access === 'free' ? 'Бесплатно' : 'Клуб'}
                    {l.completed && ' · Завершён'}{l.locked && ' · Нужен доступ'}
                  </small>
                </span>
              </AppLink>
            ))}
          </div>
        </details>
      ))}
    </>
  );
}

export default function Course() {
  const data = useLoaderData() as CourseData;
  const {course, outline} = data;
  useTitle(course.title);
  const partial = outline && outline.total > outline.available;
  return (
    <>
      <AppLink className="breadcrumb" to="/catalogue">← Библиотека</AppLink>
      <section className="course-intro">
        <div>
          <span className="chip">{course.topic} · {course.level}</span>
          <h1>{course.title}</h1>
          <p className="lead">{course.outcome}</p>
          <p className="course-meta">
            {partial
              ? `Открыто ${outline.available} из ${outline.total} ${plural(outline.total, 'урока', 'уроков', 'уроков')} · остальные скоро`
              : `${data.lessons.length} ${plural(data.lessons.length, 'урок', 'урока', 'уроков')} · ${data.minutes} минут`}
            {' · '}{data.done} пройдено
          </p>
          <div className="actions">
            {data.first
              ? <AppLink className="button" to={`/lessons/${data.first.id}`}>{data.started || data.done ? 'Продолжить' : 'Начать курс'} →</AppLink>
              : <p className="notice">Все доступные уроки пройдены. Можно вернуться к любому уроку ниже.</p>}
            {bootstrap.user && <Favourite courseId={course.id} initial={data.favourite} />}
            {outline && <AppLink className="course-map-link" to={`/?view=map#course-${course.id}`}>Показать на карте →</AppLink>}
          </div>
        </div>
        <aside className="panel warm">
          <h2>Перед началом</h2>
          <p><strong>Что уже нужно знать</strong><br />{course.prerequisites}</p>
          <p><strong>Инструменты и расходы</strong><br />{course.tools}</p>
          <p className="small">{course.author} · обновлено {course.updated_at}</p>
        </aside>
      </section>
      <h2>Программа курса</h2>
      <p>Бесплатные уроки открыты всем. Уроки клуба требуют доступа участника{partial && '; уроки с пометкой «Скоро» появятся позже'}.</p>
      {outline ? <Outline outline={outline} /> : <Curriculum lessons={data.lessons} />}
    </>
  );
}
