import {useEffect, useState} from 'react';
import {Link, useLoaderData, useLocation, type LoaderFunctionArgs} from 'react-router';
import {ApiError, bootstrap, getJson, postJson} from '../api';
import {humanTime} from '../format';
import {useTitle} from '../useTitle';
import type {Question} from './types';
import {Badge, Empty, PageHead} from './ui';

export const questionsLoader = ({request}: LoaderFunctionArgs) =>
  getJson<{questions: Question[]; ready: boolean}>('/api/admin/questions', request.signal);

export default function Questions() {
  const data = useLoaderData() as {questions: Question[]; ready: boolean};
  useTitle('Вопросы · Админка');
  const [items, setItems] = useState(data.questions);
  const [tab, setTab] = useState<'open' | 'all'>(data.questions.some(q => q.status === 'open') ? 'open' : 'all');
  const {hash} = useLocation();
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView({block: 'center'});
  }, [hash]);
  // Answered here stay in view (showing the answer) until the tab changes, so a reply never just vanishes.
  const [answered, setAnswered] = useState<number[]>([]);
  const open = items.filter(q => q.status === 'open').length;
  const shown = tab === 'open' ? items.filter(q => q.status === 'open' || answered.includes(q.id) || '#q' + q.id === hash) : items;
  const switchTo = (next: 'open' | 'all') => { setTab(next); setAnswered([]); };
  return (
    <>
      <PageHead eyebrow="Люди" title="Вопросы учеников">
        Ответ появится у ученика на странице «Помощь». Внешних уведомлений нет.
      </PageHead>
      {!data.ready && <p className="adm-warn">Хранилище ответов не подготовлено: выполните на сервере <code>flask --app club init-support</code>.</p>}
      <div className="adm-toolbar">
        <div className="adm-tabs" role="tablist">
          <button role="tab" aria-selected={tab === 'open'} className={tab === 'open' ? 'is-on' : undefined} onClick={() => switchTo('open')}>Ждут ответа<span>{open}</span></button>
          <button role="tab" aria-selected={tab === 'all'} className={tab === 'all' ? 'is-on' : undefined} onClick={() => switchTo('all')}>Все<span>{items.length}</span></button>
        </div>
      </div>
      {shown.length ? (
        <div className="adm-questions">
          {shown.map(q => <Ticket key={q.id} q={q} ready={data.ready} onSaved={next => { setAnswered(a => [...a, next.id]); setItems(list => list.map(i => i.id === next.id ? next : i)); }} />)}
        </div>
      ) : <Empty>{tab === 'open' ? 'Все вопросы разобраны. 🎉' : 'Вопросов пока не было.'}</Empty>}
    </>
  );
}

function Ticket({q, ready, onSaved}: {q: Question; ready: boolean; onSaved: (q: Question) => void}) {
  const [text, setText] = useState(q.response ?? '');
  const [editing, setEditing] = useState(!q.response);
  const [state, setState] = useState<{busy: boolean; error: string}>({busy: false, error: ''});
  const {hash} = useLocation();
  async function send() {
    setState({busy: true, error: ''});
    try {
      const result = await postJson<{ticket: {revision: number; response: string; handled_at: string; status: string}}>(
        `/api/support/tickets/${q.id}/handle`, {revision: q.revision, response: text});
      onSaved({...q, ...result.ticket});
      setEditing(false);
      setState({busy: false, error: ''});
    } catch (e) {
      setState({busy: false, error: e instanceof ApiError ? e.message : 'Не удалось сохранить ответ.'});
    }
  }
  const staffAdmin = bootstrap.user?.role === 'admin';
  return (
    <article id={`q${q.id}`} className={'adm-card adm-ticket' + (q.status === 'open' ? ' is-open' : '') + (hash === `#q${q.id}` ? ' is-target' : '')}>
      <header>
        <p>
          {staffAdmin ? <Link to={`/admin/learners/${q.user_id}`}><strong>{q.user_name}</strong></Link> : <strong>{q.user_name}</strong>}
          {q.entitlement === 'member' && <> <Badge tone="accent">в клубе</Badge></>}
          <span className="adm-muted"> · {humanTime(q.created_at)}</span>
        </p>
        {q.status === 'open' ? <Badge tone="gold">ждёт ответа</Badge> : <Badge>отвечен</Badge>}
      </header>
      <p className="adm-ticket-context">{q.lesson_id ? <>Урок: <Link to={`/admin/lessons/${q.lesson_id}`}>{q.lesson_title}</Link></> : 'Общий вопрос'}</p>
      <blockquote>{q.body}</blockquote>
      {editing ? (
        <div className="adm-reply">
          <textarea value={text} onChange={e => setText(e.target.value)} rows={4} maxLength={4000} placeholder="Ответ ученику" aria-label="Ответ ученику" disabled={!ready} />
          {state.error && <p className="adm-warn" role="alert">{state.error}</p>}
          <div className="adm-row">
            {q.response && <button type="button" className="button secondary" onClick={() => { setText(q.response ?? ''); setEditing(false); }}>Отмена</button>}
            <button type="button" className="button" disabled={!ready || state.busy || !text.trim()} onClick={send}>{q.response ? 'Обновить ответ' : 'Ответить'}</button>
          </div>
        </div>
      ) : (
        <div className="adm-answer">
          <p className="preserve">{q.response}</p>
          <small>{q.handled_at && `Ответ ${humanTime(q.handled_at)}`} · <button type="button" className="adm-link" onClick={() => setEditing(true)}>изменить</button></small>
        </div>
      )}
    </article>
  );
}
