import {useRef, useState} from 'react';
import {bootstrap, postJson} from '../api';

export async function copyText(text: string, report: (message: string) => void) {
  try {
    await navigator.clipboard.writeText(text);
    report('Скопировано.');
  } catch {
    report('Не удалось скопировать автоматически. Выделите текст и скопируйте его.');
  }
}

export interface VideoSource {
  url: string;
  type: string;
  fixture: boolean;
}

/** Lesson or material video: resumes where the learner stopped and saves the position (signed-in only). */
export function Video({video, resume, saveUrl, readingAnchor}: {video: VideoSource; resume: number; saveUrl: string; readingAnchor: string}) {
  const ref = useRef<HTMLVideoElement>(null);
  const [failed, setFailed] = useState(false);
  const [status, setStatus] = useState('');
  const lastSave = useRef(0);
  async function save(force = false) {
    const element = ref.current;
    if (!element || !bootstrap.user || (!force && Date.now() - lastSave.current < 5000)) return;
    lastSave.current = Date.now();
    try {
      await postJson(saveUrl, {seconds: element.currentTime});
      setStatus('Позиция просмотра сохранена.');
    } catch {
      setStatus('Позиция не сохранена. Проверьте подключение.');
    }
  }
  return (
    <div className="video-wrap">
      <video ref={ref} controls preload="metadata" playsInline
        onLoadedMetadata={event => { setFailed(false); const v = event.currentTarget; if (resume > 0 && resume < v.duration - 1) v.currentTime = resume; }}
        onError={() => setFailed(true)} onTimeUpdate={() => save()} onPause={() => save(true)} onEnded={() => save(true)}>
        <source src={video.url} type={video.type} onError={() => setFailed(true)} />
        Видео не поддерживается. Прочитайте текст ниже.
      </video>
      {video.fixture && <p className="small">Короткий синтетический видеопример для проверки воспроизведения. Без звука. Содержание доступно текстом ниже.</p>}
      {failed && (
        <div className="notice">
          <p role="status">Видео недоступно. Можно повторить загрузку или продолжить по тексту.</p>
          <div className="actions">
            <button type="button" className="button secondary" onClick={() => { setFailed(false); ref.current?.load(); }}>Повторить загрузку видео</button>
            <a href={`#${readingAnchor}`}>Перейти к тексту ↓</a>
          </div>
        </div>
      )}
      <p className="small" role="status">{status}</p>
    </div>
  );
}

export function PromptPanel({prompt, title = 'Запрос для первого шага'}: {prompt: string; title?: string}) {
  const [status, setStatus] = useState('');
  return (
    <section className="panel">
      <h2>{title}</h2>
      <p className="preserve">{prompt}</p>
      <button type="button" className="button secondary" onClick={() => copyText(prompt, message => setStatus(message === 'Скопировано.' ? 'Запрос скопирован.' : message))}>Скопировать запрос</button>
      <span className="copy-status" role="status">{status}</span>
    </section>
  );
}

export function Resources({resources, title}: {resources: {id: string; title: string; kind: string; url: string}[]; title: string}) {
  if (!resources.length) return null;
  return (
    <section className="materials">
      <h2>{title}</h2>
      {resources.map(resource => (
        <a key={resource.id} className="resource" href={resource.url}>
          {resource.id === 'checklist' ? '↓ ' : ''}{resource.title}<small>{resource.kind === 'text' ? 'TXT · скачать' : 'Внешний источник ↗'}</small>
        </a>
      ))}
    </section>
  );
}

/**
 * A rich lesson or guide body, rendered on the server from an escaped Markdown subset
 * (legacy_content.py), so the HTML holds only allowlisted tags, links and media. Prompt blocks get
 * a copy button.
 */
export function RichBody({id, html}: {id: string; html: string}) {
  return (
    <section className="reading lesson-rich" id={id} tabIndex={-1}
      onClick={event => {
        const button = (event.target as Element).closest('[data-copy-block]');
        if (!button) return;
        const figure = button.parentElement!;
        const status = figure.querySelector('.copy-status');
        copyText(figure.querySelector('pre')?.textContent || '', message => { if (status) status.textContent = message; });
      }}
      dangerouslySetInnerHTML={{__html: html}} />
  );
}
