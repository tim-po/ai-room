import {useLoaderData, useLocation} from 'react-router';
import {getJson} from '../api';
import {plural} from '../format';
import {AppLink} from '../Shell';
import SkillMap from '../tree/SkillMap';
import type {HomeData} from '../types';
import {useTitle} from '../useTitle';

export const homeLoader = ({request}: {request: Request}) => getJson<HomeData>('/api/app/home', request.signal);

// The words are the club's own, from airoom.club: what the club is, how it works, the first month.
const PILLARS = [
  ['01', 'Быть в контексте', 'Понимать, что происходит в ИИ, и сразу видеть, что применять в работе. Канал отбирает главное, чат помогает превратить информацию в следующий рабочий шаг.'],
  ['02', 'Перенимать опыт', 'Практические курсы и гайды на основе опыта и пройденного пути. Выбираешь цель → проходишь короткий маршрут → сразу применяешь знания в работе.'],
  ['03', 'Делать вместе', 'Онлайн-эфиры и регулярные воркшопы, после которых появляется результат: от вопроса → к рабочему решению на экране.'],
] as const;
const WEEKS = [
  ['01 неделя', 'Осваиваешь ChatGPT и Claude', 'Собираешь первого рабочего помощника'],
  ['02 неделя', 'Находишь, какие задачи автоматизировать', 'Видишь, где ИИ возвращает время'],
  ['03 неделя', 'Создаёшь AI-агента или целую команду агентов', 'Передаёшь системе отдельные функции'],
  ['04 неделя', 'Связываешь созданных агентов и разработки', 'Собираешь собственный рабочий контур'],
] as const;

function Welcome({data}: {data: HomeData}) {
  useTitle('ИИ, который работает на тебя');
  const start = data.free_lessons[0]?.url ?? data.next?.url;
  return (
    <>
      <section className="welcome-hero">
        <div>
          <p className="eyebrow">AI Room Club</p>
          <h1>Преврати ИИ из поискового чата в&nbsp;рабочий инструмент для&nbsp;бизнеса</h1>
          <p className="welcome-lead">Среда, материалы и люди, с которыми ИИ становится частью работы, проектов и бизнеса → от первого запроса до собственной системы.</p>
          <div className="welcome-actions">
            {start && <AppLink className="button" to={start}>Попробовать бесплатно →</AppLink>}
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

      <section className="welcome-block" aria-labelledby="inside-title">
        <p className="eyebrow">Внутри клуба</p>
        <h2 id="inside-title">Не очередной курс, а рабочая среда для изучения ИИ</h2>
        <p className="welcome-sub">Вместо хаоса каналов, сохранёнок и случайных сервисов → контекст, понятная система и люди, которые уже прошли этот путь.</p>
        <ol className="welcome-pillars">
          {PILLARS.map(([n, title, text]) => <li key={n}><span>{n}</span><strong>{title}</strong><p>{text}</p></li>)}
        </ol>
      </section>

      {data.free_lessons.length > 0 && (
        <section className="welcome-free" aria-labelledby="free-title">
          <h2 id="free-title">Начни бесплатно — прямо сейчас</h2>
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

      <section className="welcome-block" aria-labelledby="weeks-title">
        <h2 id="weeks-title">Как пройдут твои первые 30 дней</h2>
        <p className="welcome-sub">Каждая неделя заканчивается новым рабочим уровнем → от уверенного диалога с ИИ до связанной системы агентов и разработок.</p>
        <ol className="welcome-weeks">
          {WEEKS.map(([week, title, result]) => <li key={week}><span>{week}</span><strong>{title}</strong><p>{result}</p></li>)}
        </ol>
      </section>

      <section className="welcome-final">
        <h2>Место твоего развития в ИИ</h2>
        <p>Не нужно осваивать всё сразу. Начни с одной задачи, собери рабочую связку и постепенно преврати её в собственную систему.</p>
        {start && <AppLink className="button" to={start}>Попробовать бесплатно →</AppLink>}
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
  const {pathname} = useLocation();
  if (pathname !== '/map') return <Welcome data={data} />;
  return <MapPage data={data} />;
}
