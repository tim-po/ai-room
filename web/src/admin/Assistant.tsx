import {useEffect, useRef, useState} from 'react';
import {ApiError, deleteJson, postJson} from '../api';
import {copyAsync} from '../components/AssistantHandoff';
import {humanTime} from '../format';

// The admin's own assistant (club/assist.py), on the overview: Claude Code, Codex or another assistant that
// can send requests works in the admin as a helper — finds and edits any course, lesson or material, creates
// new ones, answers learners and reviews works. It never holds a key: the one-time link sets a cookie that
// ends ten minutes after the helper's last request, and then the person copies a new link.

interface Session {id: string; label: string; created_at: string; last_used_at: string | null; expires_at: string}
interface LinkMade {url: string; message: string; minutes: number; helper_minutes: number}
export interface AssistantData {
  sessions: Session[];
  link_minutes: number;
  helper_minutes: number;
  tools: {name: string; title: string; description: string}[];
}

const SPARK = 'M12 3l1.8 4.6L18.5 9l-4.7 1.4L12 15l-1.8-4.6L5.5 9l4.7-1.4zM18 15l.9 2.1 2.1.9-2.1.9L18 21l-.9-2.1-2.1-.9 2.1-.9z';

/** A short message with a one-time link for the assistant, copied at once; the field stays as a fallback when the clipboard is blocked. */
function LinkButton() {
  const [link, setLink] = useState<LinkMade | null>(null);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const [left, setLeft] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const root = useRef<HTMLSpanElement>(null);
  // The note closes on a click elsewhere, Escape or its own button.
  useEffect(() => {
    if (!status) return;
    const away = (event: Event) => { if (!root.current?.contains(event.target as Node)) setStatus(''); };
    const key = (event: KeyboardEvent) => { if (event.key === 'Escape') setStatus(''); };
    document.addEventListener('pointerdown', away);
    document.addEventListener('keydown', key);
    return () => { document.removeEventListener('pointerdown', away); document.removeEventListener('keydown', key); };
  }, [status]);
  async function make() {
    // The note opens towards the side with room for it.
    const box = button.current?.getBoundingClientRect();
    setLeft(!!box && box.left + 380 < window.innerWidth);
    setBusy(true); setStatus('');
    const made: {link: LinkMade | null} = {link: null};
    try {
      await copyAsync(async () => {
        made.link = await postJson<LinkMade>('/api/admin/assistant/links', {});
        return made.link.message;
      });
      setLink(made.link);
      setStatus('Скопировано — вставьте в чат с ассистентом.');
    } catch (error) {
      if (made.link) {
        setLink(made.link);
        setStatus('Готово — скопируйте текст из поля ниже.');
      } else {
        setStatus(error instanceof ApiError ? error.message : 'Не удалось создать ссылку. Повторите.');
      }
    } finally {
      setBusy(false);
    }
  }
  return (
    <span className="adm-assist" ref={root}>
      <button ref={button} type="button" className="button" disabled={busy} onClick={make}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d={SPARK} /></svg>
        Скопировать ссылку для ассистента
      </button>
      {status && (
        <span className={'adm-assist-pop' + (left ? ' is-left' : '')} role="status">
          <span className="adm-assist-pop-head">{status}
            <button type="button" className="adm-close" aria-label="Закрыть" onClick={() => setStatus('')}>×</button></span>
          {link && <textarea readOnly rows={4} value={link.message} aria-label="Сообщение для ассистента" onFocus={e => e.currentTarget.select()} />}
          {link && <small>Ссылка одноразовая: открыть её нужно в течение {link.minutes} минут.</small>}
        </span>
      )}
    </span>
  );
}

export default function AssistantCard({initial}: {initial: AssistantData}) {
  const [data, setData] = useState(initial);
  async function revoke(id: string) {
    if (!window.confirm('Отключить этого ассистента? Он сразу потеряет доступ.')) return;
    setData(await deleteJson<AssistantData>(`/api/admin/assistant/sessions/${id}`));
  }
  return (
    <section className="adm-card adm-assistant" aria-labelledby="assistant-title">
      <header className="adm-assistant-head">
        <span className="adm-assistant-mark" aria-hidden="true"><svg viewBox="0 0 24 24"><path d={SPARK} /></svg></span>
        <h2 id="assistant-title">ИИ-ассистент</h2>
      </header>
      <p className="adm-assistant-text">Дайте ссылку Claude Code, Codex или другому ассистенту, который умеет отправлять запросы, и работайте из чата:
        он найдёт и поправит любой урок, соберёт курс из ваших материалов, ответит на вопросы и разберёт работы. Новое — черновиком.</p>
      <LinkButton />
      <div className="adm-assistant-foot">
        {data.sessions.length ? (
          <ul className="adm-sessions" aria-label="Подключённые ассистенты">
            {data.sessions.map(s => (
              <li key={s.id}>
                <span className="adm-session-dot" aria-hidden="true" />
                <strong>{s.label}</strong>
                <small>{s.last_used_at ? `работал ${humanTime(s.last_used_at)}` : `подключён ${humanTime(s.created_at)}`}</small>
                <button type="button" className="adm-link" onClick={() => revoke(s.id)}>Отключить</button>
              </li>
            ))}
          </ul>
        ) : null}
        <p className="adm-muted">Доступ закрывается через {data.helper_minutes} минут без запросов — потом скопируйте новую ссылку.</p>
      </div>
    </section>
  );
}
