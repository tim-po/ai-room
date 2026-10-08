import {useLoaderData, useLocation} from 'react-router';
import {getJson} from '../api';
import {plural} from '../format';
import {AppLink} from '../Shell';
import SkillMap from '../tree/SkillMap';
import type {HomeData} from '../types';
import {useTitle} from '../useTitle';

export const homeLoader = ({request}: {request: Request}) => getJson<HomeData>('/api/app/home', request.signal);

function Welcome({data}: {data: HomeData}) {
  useTitle('Учиться и применять');
  const start = data.free_lessons[0]?.url ?? data.next?.url;
  return (
    <>
      <section className="welcome-hero">
        <div>
          <h1>Короткие уроки по&nbsp;ИИ.<br />Три из них — бесплатно.</h1>
          <p className="welcome-lead">Claude, ChatGPT и ИИ-агенты: урок, пример и задание на вашей задаче. Результат сохраняется в аккаунте.</p>
          <div className="welcome-actions">
            {start && <AppLink className="button" to={start}>Начать бесплатный урок →</AppLink>}
            <AppLink className="button secondary" to="/map">Открыть карту навыков</AppLink>
          </div>
          <p className="small">Тестовая версия · доступ по приглашению. <AppLink to="/login">Есть приглашение — войти</AppLink></p>
        </div>
        <div className="welcome-topics" aria-label="Что внутри">
          {data.tree.topics.map(topic => {
            const total = topic.courses.reduce((sum, course) => sum + course.total, 0);
            const open = topic.courses.reduce((sum, course) => sum + course.available, 0);
            return (
              <AppLink key={topic.id} className="welcome-topic" to={`/map#course-${topic.courses[0].id}`}>
                <strong>{topic.title}</strong>
                <span>{topic.subtitle}</span>
                <em className={open ? undefined : 'is-soon'}>
                  {open
                    ? `${open} ${plural(open, 'урок открыт', 'урока открыто', 'уроков открыто')} · ещё ${total - open} скоро`
                    : `Скоро · ${total} ${plural(total, 'урок', 'урока', 'уроков')} в подготовке`}
                </em>
              </AppLink>
            );
          })}
        </div>
      </section>
      {data.free_lessons.length > 0 && (
        <section className="welcome-free" aria-labelledby="free-title">
          <h2 id="free-title">Бесплатные уроки — можно начать сейчас</h2>
          <div className="welcome-free-grid">
            {data.free_lessons.map(lesson => (
              <AppLink key={lesson.id} className="welcome-lesson" to={lesson.url!}>
                <span>{lesson.topic} · {lesson.minutes} мин</span>
                <strong>{lesson.title}</strong>
                <em>{lesson.course}</em>
              </AppLink>
            ))}
          </div>
        </section>
      )}
    </>
  );
}

function MapPage({data}: {data: HomeData}) {
  useTitle('Карта навыков');
  return <SkillMap data={data} />;
}

export default function Home() {
  const data = useLoaderData() as HomeData;
  const {pathname} = useLocation();
  if (pathname !== '/map') return <Welcome data={data} />;
  return <MapPage data={data} />;
}
