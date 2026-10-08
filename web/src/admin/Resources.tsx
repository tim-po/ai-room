import {useState} from 'react';
import {ApiError} from '../api';
import type {Resource} from './types';
import {RemovePart, Segmented} from './ui';

/** Extra files for a lesson or material: a text to download or an HTTPS link. Archived ones stay listed, greyed. */
export function Resources({title: heading = 'Материалы к уроку', items, add, archive, onRemove}: {
  title?: string;
  /** Hides the block again while it holds nothing. */
  onRemove?: () => void;
  items: Resource[];
  add: (resource: {title: string; kind: string; content: string}) => Promise<void>;
  archive: (id: string) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState('link');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit() {
    setBusy(true);
    setError('');
    try {
      await add({title, kind, content});
      setTitle('');
      setContent('');
      setOpen(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Не удалось добавить.');
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className={'adm-card adm-form' + (onRemove && !items.length ? ' has-remove' : '')}>
      {onRemove && !items.length && <RemovePart label={heading} filled={false} onRemove={onRemove} />}
      <header><h2>{heading}</h2></header>
      {items.length ? (
        <ul className="adm-resources">
          {items.map(r => (
            <li key={r.id} className={r.status === 'archived' ? 'is-archived' : undefined}>
              <span className="adm-resource-kind">{r.kind === 'link' ? '↗' : 'TXT'}</span>
              <span className="adm-resource-title">{r.title}<small>{r.kind === 'link' ? r.content : `${r.content.length} символов`}</small></span>
              {r.status === 'archived' ? <small>в архиве</small>
                : <button type="button" className="adm-link" onClick={() => { if (window.confirm(`Убрать «${r.title}» в архив?`)) void archive(r.id); }}>в архив</button>}
            </li>
          ))}
        </ul>
      ) : <p className="adm-hint">Ссылки и файлы, которые ученик заберёт с собой.</p>}
      {open ? (
        <div className="adm-resource-form">
          <Segmented label="Тип" value={kind} options={[['link', 'Ссылка'], ['text', 'Текстовый файл']]} onChange={setKind} />
          <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Название" aria-label="Название" maxLength={200} />
          {kind === 'link'
            ? <input value={content} onChange={e => setContent(e.target.value)} placeholder="https://…" aria-label="Ссылка" inputMode="url" />
            : <textarea value={content} onChange={e => setContent(e.target.value)} rows={4} placeholder="Текст файла" aria-label="Текст файла" />}
          {error && <p className="adm-warn" role="alert">{error}</p>}
          <div className="adm-row">
            <button type="button" className="button secondary" onClick={() => setOpen(false)}>Отмена</button>
            <button type="button" className="button" disabled={busy || !title.trim() || !content.trim()} onClick={submit}>Добавить</button>
          </div>
        </div>
      ) : <button type="button" className="adm-add" onClick={() => setOpen(true)}>+ Ссылка или файл</button>}
    </section>
  );
}
