import {useEffect, useId, useState} from 'react';
import {postJson} from '../api';
import {RichBody} from '../components/Media';

// The lesson or material text, with a «Как увидит ученик» tab: the server renders it exactly as the
// learner page does (club/admin.py /api/admin/preview), unsaved edits included.

export default function BodyEditor({label, value, onChange, format, hint}: {
  label: string; value: string; onChange: (value: string) => void; format: string; hint?: string;
}) {
  const id = useId();
  const [tab, setTab] = useState<'text' | 'preview'>('text');
  const [html, setHtml] = useState<string | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    if (tab !== 'preview') return;
    let live = true;
    const timer = window.setTimeout(() => {
      postJson<{html: string}>('/api/admin/preview', {body: value, body_format: format})
        .then(r => { if (live) { setHtml(r.html); setError(false); } }, () => { if (live) setError(true); });
    }, 150);
    return () => { live = false; window.clearTimeout(timer); };
  }, [tab, value, format]);
  const words = value.trim() ? value.trim().split(/\s+/).length : 0;
  return (
    <div className="adm-field adm-body">
      <div className="adm-body-head">
        <label className="adm-label" htmlFor={id}>{label}</label>
        <div className="adm-body-tabs" role="tablist" aria-label="Вид текста">
          <button type="button" role="tab" aria-selected={tab === 'text'} className={tab === 'text' ? 'is-on' : undefined} onClick={() => setTab('text')}>Текст</button>
          <button type="button" role="tab" aria-selected={tab === 'preview'} className={tab === 'preview' ? 'is-on' : undefined} onClick={() => setTab('preview')}>Как увидит ученик</button>
        </div>
      </div>
      {tab === 'text' ? (
        <textarea id={id} value={value} rows={16} className={format === 'blocks' ? 'is-mono' : undefined} aria-describedby={id + '-hint'}
          onChange={e => onChange(e.target.value)} />
      ) : (
        <div className="adm-body-preview">
          {error ? <p className="adm-warn">Не удалось показать предпросмотр.</p>
            : html === null ? <p className="adm-muted">Готовлю предпросмотр…</p>
            : html ? <RichBody id={id + '-preview'} html={html} /> : <p className="adm-muted">Текста пока нет.</p>}
        </div>
      )}
      <span className="adm-hint" id={id + '-hint'}>
        {words} слов · {format === 'blocks' ? 'Markdown: ## заголовок, - список, **жирный**, @video ссылка Kinescope' : 'абзацы через пустую строку'}{hint ? ` · ${hint}` : ''}
      </span>
    </div>
  );
}
