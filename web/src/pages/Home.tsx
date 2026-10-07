import {useLoaderData, useSearchParams} from 'react-router';
import {bootstrap, getJson} from '../api';
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
          <p className="eyebrow">AI Room · учиться через практику</p>
          <h1>От первого<br />«а что, если»<br /><em>к своей работе.</em></h1>
          <p className="welcome-lead">Короткие практические уроки по ИИ: делаете на своей задаче, сохраняете результат, возвращаетесь, когда удобно.</p>
          <div className="welcome-actions">
            {start && <AppLink className="button" to={start}>Попробовать бесплатный урок →</AppLink>}
            <AppLink className="button secondary" to="/?view=map">Открыть карту навыков</AppLink>
          </div>
          <p className="small">Тестовая версия · доступ по приглашению. <AppLink to="/login">Есть приглашение — войти</AppLink></p>
        </div>
        <div className="welcome-topics" aria-label="Что внутри">
          {data.tree.topics.map(topic => {
            const lessons = topic.courses.reduce((sum, course) => sum + course.total, 0);
            return (
              <AppLink key={topic.id} className="welcome-topic" to={`/?view=map#course-${topic.courses[0].id}`}>
                <strong>{topic.title}</strong>
                <span>{topic.subtitle}</span>
                <em>{topic.courses.length} {plural(topic.courses.length, 'курс', 'курса', 'курсов')} · {lessons} {plural(lessons, 'урок', 'урока', 'уроков')}</em>
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
      <section className="welcome-principles" aria-label="Как устроено обучение">
        <div><span className="eyebrow">01 / Поймите</span><h2>Одна идея за раз</h2><p>Объяснение, пример и задание рядом.</p></div>
        <div><span className="eyebrow">02 / Попробуйте</span><h2>Сделайте что-то своё</h2><p>Сохраните работу и вернитесь к ней позже.</p></div>
        <div><span className="eyebrow">03 / Выбирайте</span><h2>Интересов может быть много</h2><p><AppLink to="/?view=map">Все направления на карте →</AppLink></p></div>
      </section>
    </>
  );
}

function MapPage({data}: {data: HomeData}) {
  useTitle('Карта навыков');
  return <SkillMap data={data} />;
}

export default function Home() {
  const data = useLoaderData() as HomeData;
  const [params] = useSearchParams();
  if (!bootstrap.user && params.get('view') !== 'map') return <Welcome data={data} />;
  return <MapPage data={data} />;
}
