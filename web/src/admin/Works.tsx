import {useState} from 'react';
import {Link, useLoaderData, type LoaderFunctionArgs} from 'react-router';
import {ApiError, bootstrap, getJson, postJson} from '../api';
import {humanTime} from '../format';
import {useTitle} from '../useTitle';
import {Badge, Empty, PageHead} from './ui';

// Learners' practice results (club/works.py): the lesson's task and criteria next to the work, and one
// note of feedback the learner reads on the lesson and in «Мои работы».

export interface Work {
  user_id: string; user_name: string; entitlement: string;
  lesson_id: string; lesson_title: string; course_id: string; course_title: string;
  task: string | null; checklist: string[]; body: string; status: string; updated_at: string;
  review: string | null; reviewed_at: string | null; reviewer: string | null;
  waiting: boolean; changed: boolean;
}

export const worksLoader = ({request}: LoaderFunctionArgs) => getJson<{works: Work[]; waiting: number}>('/api/admin/works', request.signal);

export default function Works() {
  const data = useLoaderData() as {works: Work[]; waiting: number};
  useTitle('Работы · Админка');
  const [items, setItems] = useState(data.works);
  const [tab, setTab] = useState<'waiting' | 'all'>(data.waiting ? 'waiting' : 'all');
  // Reviewed here stay in view until the tab changes, so a sent note never just vanishes.
  const [done, setDone] = useState<string[]>([]);
  const key = (w: Work) => w.user_id + '/' + w.lesson_id;
  const waiting = items.filter(w => w.waiting).length;
  const shown = tab === 'waiting' ? items.filter(w => w.waiting || done.includes(key(w))) : items;
  const switchTo = (next: 'waiting' | 'all') => { setTab(next); setDone([]); };
  return (
    <>
      <PageHead eyebrow="Люди" title="Работы учеников">
        Результаты практики из уроков. Отзыв ученик увидит в уроке и в «Моих работах».
      </PageHead>
      <div className="adm-toolbar">
        <div className="adm-tabs" role="tablist">
          <button role="tab" aria-selected={tab === 'waiting'} className={tab === 'waiting' ? 'is-on' : undefined} onClick={() => switchTo('waiting')}>Ждут отзыва<span>{waiting}</span></button>
          <button role="tab" aria-selected={tab === 'all'} className={tab === 'all' ? 'is-on' : undefined} onClick={() => switchTo('all')}>Все<span>{items.length}</span></button>
        </div>
      </div>
      {shown.length ? (
        <div className="adm-questions">
          {shown.map(w => <WorkCard key={key(w)} work={w} onSaved={next => { setDone(d => [...d, key(next)]); setItems(list => list.map(i => key(i) === key(next) ? next : i)); }} />)}
        </div>
      ) : <Empty>{tab === 'waiting' ? 'Все работы разобраны.' : 'Сданных работ пока нет.'}</Empty>}
    </>
  );
}

function WorkCard({work, onSaved}: {work: Work; onSaved: (w: Work) => void}) {
  const [text, setText] = useState(work.review ?? '');
  const [editing, setEditing] = useState(!work.review);
  const [state, setState] = useState({busy: false, error: ''});
  async function send() {
    setState({busy: true, error: ''});
    try {
      onSaved(await postJson<Work>(`/api/admin/works/${work.user_id}/${work.lesson_id}/review`, {body: text}));
      setEditing(false);
      setState({busy: false, error: ''});
    } catch (e) {
      setState({busy: false, error: e instanceof ApiError ? e.message : 'Не удалось сохранить отзыв.'});
    }
  }
  const admin = bootstrap.user?.role === 'admin';
  return (
    <article className={'adm-card adm-ticket' + (work.waiting ? ' is-open' : '')}>
      <header>
        <p>
          {admin ? <Link to={`/admin/learners/${work.user_id}`}><strong>{work.user_name}</strong></Link> : <strong>{work.user_name}</strong>}
          <span className="adm-muted"> · {humanTime(work.updated_at)}</span>
        </p>
        {work.changed ? <Badge tone="gold">изменена после отзыва</Badge> : work.waiting ? <Badge tone="gold">ждёт отзыва</Badge> : <Badge>есть отзыв</Badge>}
      </header>
      <p className="adm-ticket-context">
        <Link to={`/admin/lessons/${work.lesson_id}`}>{work.lesson_title}</Link> · {work.course_title}
      </p>
      {(work.task || work.checklist.length > 0) && (
        <details className="adm-more">
          <summary><span>Задание и критерии</span><small>{work.checklist.length} критериев</small></summary>
          <div className="adm-more-body">
            {work.task && <p className="adm-text">{work.task}</p>}
            {work.checklist.length > 0 && <ul className="adm-criteria">{work.checklist.map(c => <li key={c}>{c}</li>)}</ul>}
          </div>
        </details>
      )}
      <blockquote>{work.body}</blockquote>
      {editing ? (
        <div className="adm-reply">
          <textarea value={text} onChange={e => setText(e.target.value)} rows={4} maxLength={4000}
            placeholder="Что получилось, что улучшить — по критериям урока" aria-label="Отзыв ученику" />
          {state.error && <p className="adm-warn" role="alert">{state.error}</p>}
          <div className="adm-row">
            {work.review && <button type="button" className="button secondary" onClick={() => { setText(work.review ?? ''); setEditing(false); }}>Отмена</button>}
            <button type="button" className="button" disabled={state.busy || !text.trim()} onClick={send}>{work.review ? 'Обновить отзыв' : 'Отправить отзыв'}</button>
          </div>
        </div>
      ) : (
        <div className="adm-answer">
          <p className="preserve">{work.review}</p>
          <small>{work.reviewer} · {work.reviewed_at && humanTime(work.reviewed_at)} · <button type="button" className="adm-link" onClick={() => setEditing(true)}>изменить</button></small>
        </div>
      )}
    </article>
  );
}
