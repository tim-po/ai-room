import {useState, type FormEvent} from 'react';
import {useLoaderData, useLocation, useRevalidator, type LoaderFunctionArgs} from 'react-router';
import {ApiError, bootstrap, getJson, postJson, withSearch} from '../api';
import {humanTime} from '../format';
import {AppLink} from '../Shell';
import type {HelpData, HelpTicket} from '../types';
import {useTitle} from '../useTitle';

export const helpLoader = ({request}: LoaderFunctionArgs) => getJson<HelpData>(withSearch('/api/app/help', request), request.signal);

function Question({data}: {data: HelpData}) {
  const {search} = useLocation();
  const revalidator = useRevalidator();
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{kind: 'success' | 'error'; text: string} | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setMessage(null);
    try {
      await postJson(`/help${search}`, {body});
      setBody('');
      setMessage({kind: 'success', text: 'Вопрос сохранён для администратора. Срок ответа пока не установлен.'});
      revalidator.revalidate();   // the question appears in "Мои вопросы"
    } catch (e) {
      setMessage({kind: 'error', text: e instanceof ApiError ? e.message : 'Не удалось сохранить вопрос. Текст остаётся в форме.'});
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel warm">
      <h2>Задать вопрос</h2>
      {data.lesson && <p>К уроку: {data.lesson.title}</p>}
      {bootstrap.user ? (
        <>
          <form onSubmit={submit}>
            <label>Что не получается?<textarea name="body" required maxLength={4000} rows={5} aria-describedby="help-privacy" value={body} onChange={e => setBody(e.target.value)} /></label>
            <p className="small" id="help-privacy">Не добавляйте пароли и другие секретные данные.</p>
            <button className="button" disabled={busy}>Сохранить вопрос</button>
          </form>
          {message && <p className={'notice ' + message.kind} role="status">{message.text}</p>}
          <p className="small">Вопрос появится у администратора, ответ — на этой странице. Срок ответа пока не установлен.</p>
        </>
      ) : (
        <><p>Войдите, чтобы сохранить вопрос для администратора и прочитать ответ.</p><AppLink className="button" to="/login?next=/help">Войти</AppLink></>
      )}
    </section>
  );
}

function Ticket({ticket}: {ticket: HelpTicket}) {
  return (
    <article className="help-ticket" aria-labelledby={`ticket-title-${ticket.id}`}>
      <header>
        <h3 id={`ticket-title-${ticket.id}`}>Вопрос №{ticket.id}</h3>
        <span className="help-ticket-state">{ticket.response ? 'Ответ записан' : ticket.status === 'open' ? 'Ожидает ответа' : 'Статус уточняется'}</span>
      </header>
      <p className="small">{humanTime(ticket.created_at)}</p>
      <p className="preserve help-question">{ticket.body}</p>
      {ticket.response && (
        <div className="help-answer">
          <h4>Ответ администратора</h4>
          <p className="preserve help-answer-body">{ticket.response}</p>
          {ticket.handled_at && <p className="small help-answer-time">{humanTime(ticket.handled_at)}</p>}
          <p className="small">Если вопрос остался, отправьте новый и укажите номер этого вопроса.</p>
        </div>
      )}
    </article>
  );
}

export default function Help() {
  const data = useLoaderData() as HelpData;
  const revalidator = useRevalidator();
  useTitle('Помощь');
  return (
    <div className="help-workspace">
      <header className="help-heading"><span className="eyebrow">Рядом с обучением</span><h1>Разберёмся вместе</h1><p>Найдите быстрый ответ или оставьте вопрос. Вернуться к переписке можно здесь.</p></header>
      <div className="grid home-panels">
        <section className="panel">
          <h2>Быстрые ответы</h2>
          <details><summary>Не воспроизводится видео</summary><p>Обновите страницу и проверьте подключение. Текст урока и практика доступны ниже видео.</p></details>
          <details><summary>Не вижу сохранённую практику</summary><p>Проверьте, что вошли в тот же аккаунт. После сохранения появляется подтверждение и время сохранения.</p><AppLink to="/profile">Открыть моё обучение →</AppLink></details>
          <details><summary>Урок клуба закрыт</summary><p>Бесплатные уроки доступны всегда. Тестовый доступ участника выдаёт администратор этой среды. Если доступ истёк, сохранённые работы остаются в аккаунте.</p></details>
        </section>
        <Question data={data} />
      </div>
      {bootstrap.user && (
        <section className="help-history" aria-labelledby="help-history-title">
          <div className="help-history-heading">
            <h2 id="help-history-title">Мои вопросы</h2>
            {data.tickets.length > 0 && (
              <button type="button" className="button secondary" onClick={() => revalidator.revalidate()} disabled={revalidator.state === 'loading'}>
                {revalidator.state === 'loading' ? 'Загружаем…' : 'Обновить ответы'}
              </button>
            )}
          </div>
          {data.tickets.length
            ? data.tickets.map(ticket => <Ticket key={ticket.id} ticket={ticket} />)
            : <p>Здесь появятся ваши вопросы и ответы администратора. Если нужна помощь с уроком, откройте помощь из этого урока — его название добавится к вопросу.</p>}
        </section>
      )}
    </div>
  );
}
