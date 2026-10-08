import {useEffect, useState} from 'react';
import {Form, Link, useLoaderData, useNavigation, useSubmit, type LoaderFunctionArgs} from 'react-router';
import {ApiError, getJson, putJson, withSearch} from '../api';
import {humanTime, plural} from '../format';
import {useTitle} from '../useTitle';
import type {People, PersonDetail} from './types';
import Select from '../components/Select';
import {Badge, Empty, PageHead, Segmented, Stat} from './ui';

export const learnersLoader = ({request}: LoaderFunctionArgs) => getJson<People>(withSearch('/api/admin/learners', request), request.signal);
export const learnerLoader = ({params, request}: LoaderFunctionArgs) => getJson<PersonDetail>(`/api/admin/learners/${params.id}`, request.signal);

const initials = (name: string) => name.split(/\s+/).map(w => w[0]).join('').slice(0, 2).toUpperCase();
const lastSeen = (day: string | null) => {
  if (!day) return 'не учился';
  const days = Math.round((Date.now() - new Date(day + 'T12:00:00Z').getTime()) / 86400000);
  return days <= 0 ? 'сегодня' : days === 1 ? 'вчера' : `${days} ${plural(days, 'день', 'дня', 'дней')} назад`;
};

export function Learners() {
  const data = useLoaderData() as People;
  useTitle('Ученики · Админка');
  const submit = useSubmit();
  const navigation = useNavigation();
  const [query, setQuery] = useState(data.query);
  useEffect(() => {
    if (query === data.query) return;
    const timer = window.setTimeout(() => submit(query ? {q: query} : {}, {replace: true}), 250);
    return () => window.clearTimeout(timer);
  }, [query, data.query, submit]);
  return (
    <>
      <PageHead eyebrow="Люди" title="Ученики">
        {data.totals.total} {plural(data.totals.total, 'ученик', 'ученика', 'учеников')}, из них {data.totals.members ?? 0} в клубе.
      </PageHead>
      <Form className="adm-toolbar" role="search" onSubmit={e => e.preventDefault()}>
        <input type="search" name="q" className="adm-search is-wide" placeholder="Имя или почта" value={query} onChange={e => setQuery(e.target.value)} aria-label="Найти ученика" />
        {navigation.state === 'loading' && <span className="adm-muted">Ищу…</span>}
      </Form>
      {data.learners.length ? (
        <div className="adm-table is-people" role="table">
          <div role="row" className="adm-tr is-head">
            <span role="columnheader">Человек</span><span role="columnheader">Доступ</span><span role="columnheader">Уроков</span><span role="columnheader">Учился</span>
          </div>
          {data.learners.map(p => (
            <Link role="row" key={p.id} to={`/admin/learners/${p.id}`} className="adm-tr">
              <span role="cell" className="adm-person">
                <span className="adm-avatar" aria-hidden="true">{initials(p.name)}</span>
                <span className="adm-title-cell"><strong>{p.name}</strong><small>{p.email}</small></span>
              </span>
              <span role="cell">
                <Badge tone={p.entitlement === 'member' ? 'accent' : p.entitlement === 'free' ? undefined : 'gold'}>{data.entitlements[p.entitlement]}</Badge>
                {p.role !== 'learner' && <> <Badge tone="muted">{data.roles[p.role]}</Badge></>}
                {p.open_questions > 0 && <> <Badge tone="gold">вопрос</Badge></>}
              </span>
              <span role="cell" className="adm-num">{p.completed}</span>
              <span role="cell" className="adm-muted">{lastSeen(p.last_active)}</span>
            </Link>
          ))}
        </div>
      ) : <Empty>Никого не нашлось.</Empty>}
    </>
  );
}

const RANK = ['', 'Новичок', 'Практик', 'Профи', 'Мастер'];

export function Learner() {
  const initial = useLoaderData() as PersonDetail;
  const [data, setData] = useState(initial);
  const [error, setError] = useState('');
  const person = data.learner;
  useTitle(`${person.name} · Админка`);
  async function change(field: 'entitlement' | 'role', value: string) {
    if (field === 'role' && !window.confirm(`Сделать ${person.name} — «${data.roles[value]}»?`)) return;
    setError('');
    try {
      setData(await putJson<PersonDetail>(`/api/admin/learners/${person.id}`, {[field]: value}));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Не удалось сохранить.');
    }
  }
  const course = Object.fromEntries(data.courses.map(c => [c.id, c.title]));
  return (
    <>
      <PageHead eyebrow={<Link to="/admin/learners">Ученики</Link>} title={
        <span className="adm-person is-big"><span className="adm-avatar" aria-hidden="true">{initials(person.name)}</span>{person.name}</span>}>
        {person.email} · {lastSeen(person.last_active)}{!person.onboarding_done && ' · не прошёл знакомство'}
      </PageHead>
      <div className="adm-stats">
        <Stat value={person.completed} label="уроков завершено" tone="accent" />
        <Stat value={person.practice} label="практик сдано" />
        <Stat value={data.days_month} label="дней учёбы за месяц" />
        <Stat value={data.ranks.length} label={plural(data.ranks.length, 'звание', 'звания', 'званий')} />
      </div>
      <div className="adm-columns">
        <div>
          <section className="adm-card">
            <header><h2>Курсы</h2></header>
            {data.courses.length ? (
              <ul className="adm-progress">
                {data.courses.map(c => (
                  <li key={c.id}>
                    <Link to={`/admin/courses/${c.id}`}>{c.title}</Link>
                    <span className="adm-meter" aria-label={`${c.done} из ${c.total}`}><span style={{width: `${c.total ? (c.done / c.total) * 100 : 0}%`}} /></span>
                    <small>{c.done} / {c.total}</small>
                  </li>
                ))}
              </ul>
            ) : <Empty>Ещё не начинал курсы.</Empty>}
            {data.ranks.length > 0 && (
              <p className="adm-ranks">{data.ranks.map(r => <Badge key={r.course_id + r.level} tone="gold">{RANK[r.level]} · {course[r.course_id] ?? r.course_id}</Badge>)}</p>
            )}
          </section>
          <section className="adm-card">
            <header><h2>Последние действия</h2></header>
            {data.feed.length ? (
              <ol className="adm-feed">
                {data.feed.map(e => (
                  <li key={e.id}>
                    <span className={`adm-dot is-${e.name}`} aria-hidden="true" />
                    <p>{e.action}{e.lesson_title && <> «{e.lesson_id ? <Link to={`/admin/lessons/${e.lesson_id}`}>{e.lesson_title}</Link> : e.lesson_title}»</>}</p>
                    <time>{humanTime(e.created_at)}</time>
                  </li>
                ))}
              </ol>
            ) : <Empty>Действий пока нет.</Empty>}
          </section>
        </div>
        <div>
          <section className="adm-card adm-form">
            <header><h2>Доступ</h2></header>
            <div className="adm-field">
              <Select label="Тариф" value={person.entitlement} onChange={v => change('entitlement', v)}
                options={(['free', 'member', 'expired', 'revoked'] as const).filter(k => data.entitlements[k]).map(k => [k, data.entitlements[k]] as const)} />
            </div>
            <p className="adm-hint">Меняется сразу. Оплаты в этой версии нет — тариф выставляется вручную.</p>
            {!data.self && (
              <details className="adm-more">
                <summary><span>Роль</span><small>{data.roles[person.role]}</small></summary>
                <div className="adm-more-body">
                  <Segmented label="Роль" value={person.role} options={(['learner', 'editor', 'admin'] as const).map(k => [k, data.roles[k]] as const)}
                    onChange={v => change('role', v)} />
                  <p className="adm-hint">Редактор правит контент и отвечает на вопросы, администратор ещё видит учеников и аналитику.</p>
                </div>
              </details>
            )}
            {error && <p className="adm-warn" role="alert">{error}</p>}
          </section>
          <section className="adm-card">
            <header><h2>Вопросы</h2></header>
            {data.questions.length ? (
              <ul className="adm-list">
                {data.questions.map(q => (
                  <li key={q.id}><Link to={`/admin/questions#q${q.id}`}>
                    <span className="adm-clamp">{q.body}</span>
                    <small>{q.status === 'open' ? 'ждёт ответа' : 'отвечен'} · {humanTime(q.created_at)}</small>
                  </Link></li>
                ))}
              </ul>
            ) : <Empty>Вопросов не задавал.</Empty>}
          </section>
        </div>
      </div>
    </>
  );
}
