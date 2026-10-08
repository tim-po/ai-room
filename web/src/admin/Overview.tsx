import {Link, useLoaderData, type LoaderFunctionArgs} from 'react-router';
import {bootstrap, getJson} from '../api';
import {humanTime, plural} from '../format';
import {useTitle} from '../useTitle';
import AssistantCard from './Assistant';
import type {Overview as Data} from './types';
import {Empty, PageHead} from './ui';

export const overviewLoader = ({request}: LoaderFunctionArgs) => getJson<Data>('/api/admin/overview', request.signal);

const greeting = () => {
  const h = new Date().getHours();
  return h < 5 ? 'Доброй ночи' : h < 12 ? 'Доброе утро' : h < 18 ? 'Добрый день' : 'Добрый вечер';
};

export default function Overview() {
  const data = useLoaderData() as Data;
  useTitle('Админка');
  const {counts} = data;
  const name = bootstrap.user?.name?.split(' ')[0];
  const waiting = counts.open_questions + counts.works_waiting;
  return (
    <>
      <PageHead title={`${greeting()}${name ? ', ' + name : ''}`}
        actions={<>
          <Link className="button secondary" to="/admin/library/new">Новый материал</Link>
          <Link className="button" to="/admin/courses/new">Новый курс</Link>
        </>}>
        За неделю учились {counts.active_week} из {counts.learners} {plural(counts.learners, 'ученика', 'учеников', 'учеников')},
        завершено {counts.completions_week} {plural(counts.completions_week, 'урок', 'урока', 'уроков')}
        {counts.drafts > 0 && <> · <Link to="/admin/courses">{counts.drafts} {plural(counts.drafts, 'черновик', 'черновика', 'черновиков')}</Link></>}
      </PageHead>

      <div className="adm-columns">
        <div>
          <section className="adm-card">
            <header>
              <h2>Ждут вас{waiting > 0 && <span className="adm-count-pill">{waiting}</span>}</h2>
              <Waiting questions={counts.open_questions} works={counts.works_waiting} />
            </header>
            {data.questions.length ? (
              <ul className="adm-list">
                {data.questions.map(q => (
                  <li key={q.id}>
                    <Link to={`/admin/questions#q${q.id}`}>
                      <strong>{q.user_name}</strong>
                      <span className="adm-clamp">{q.body}</span>
                      <small>{q.lesson_title ?? 'Общий вопрос'} · {humanTime(q.created_at)}</small>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : <Empty>{counts.works_waiting ? 'Вопросов нет — остались работы учеников.' : 'Все вопросы и работы учеников разобраны.'}</Empty>}
          </section>

          <section className="adm-card">
            <header><h2>Что происходит</h2></header>
            {data.feed.length ? (
              <ol className="adm-feed">
                {data.feed.map(e => (
                  <li key={e.id}>
                    <span className={`adm-dot is-${e.name}`} aria-hidden="true" />
                    <p>
                      {data.role === 'admin' && e.user_id ? <Link to={`/admin/learners/${e.user_id}`}>{e.user_name}</Link> : <strong>{e.user_name}</strong>}
                      {' '}{e.action}{e.lesson_title && <> «{e.lesson_id ? <Link to={`/admin/lessons/${e.lesson_id}`}>{e.lesson_title}</Link> : e.lesson_title}»</>}
                    </p>
                    <time>{humanTime(e.created_at)}</time>
                  </li>
                ))}
              </ol>
            ) : <Empty>Ученики пока ничего не делали.</Empty>}
          </section>
        </div>

        <div>
          {data.assistant && <AssistantCard initial={data.assistant} />}
          <section className="adm-card">
            <header><h2>Популярное за месяц</h2></header>
            {data.popular.length ? (
              <ol className="adm-rank">
                {data.popular.map(p => (
                  <li key={p.id}>
                    <Link to={`/admin/lessons/${p.id}`}><strong>{p.title}</strong><small>{p.course_title}</small></Link>
                    <span title="Завершили за 30 дней">{p.completions} ✓</span>
                  </li>
                ))}
              </ol>
            ) : <Empty>Пока никто не завершил урок.</Empty>}
          </section>
        </div>
      </div>
    </>
  );
}

function Waiting({questions, works}: {questions: number; works: number}) {
  const parts = [
    questions > 0 && <Link key="q" to="/admin/questions">{questions} {plural(questions, 'вопрос', 'вопроса', 'вопросов')}</Link>,
    works > 0 && <Link key="w" to="/admin/works">{works} {plural(works, 'работа', 'работы', 'работ')}</Link>,
  ].filter(Boolean);
  if (!parts.length) return null;
  return <span className="adm-muted">{parts.length === 2 ? <>{parts[0]} · {parts[1]}</> : parts[0]}</span>;
}
