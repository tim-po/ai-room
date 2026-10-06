import {useEffect, useRef, useState, type FormEvent} from 'react';
import {useBlocker, useLoaderData, useLocation, useRevalidator, type LoaderFunctionArgs} from 'react-router';
import {ApiError, bootstrap, getJson, postJson} from '../api';
import Outline from '../components/Outline';
import {humanTime, plural} from '../format';
import {AppLink} from '../Shell';
import type {LessonData, Practice} from '../types';
import {useTitle} from '../useTitle';

export const lessonLoader = ({params, request}: LoaderFunctionArgs) =>
  getJson<LessonData>(`/api/app/lessons/${encodeURIComponent(params.id!)}`, request.signal);

// A server page load already recorded the visit (spa.html bootstrap); only later in-app
// navigations ask the API to record it.
let serverVisit: string | null = bootstrap.recorded_visit;
function useRecordVisit(lessonId: string, locked: boolean) {
  useEffect(() => {
    if (locked || !bootstrap.user) return;
    if (serverVisit === lessonId) { serverVisit = null; return; }
    serverVisit = null;
    postJson(`/api/app/lessons/${encodeURIComponent(lessonId)}/visit`, {}).catch(() => { /* navigation history only */ });
  }, [lessonId, locked]);
}

/** Highlights the "В этом уроке" step being read. */
function useActiveStep(count: number) {
  const [active, setActive] = useState<string | null>(null);
  useEffect(() => {
    if (!count || !('IntersectionObserver' in window)) return;
    const targets = [...document.querySelectorAll<HTMLElement>('.lesson-rich h2[id^="step-"], #practice')];
    const observer = new IntersectionObserver(entries => {
      const visible = entries.filter(e => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (visible) setActive(visible.target.id);
    }, {rootMargin: '0px 0px -70% 0px'});
    targets.forEach(t => observer.observe(t));
    return () => observer.disconnect();
  }, [count]);
  return active;
}

function Steps({steps, practice, active}: {steps: string[]; practice: boolean; active: string | null}) {
  return (
    <ol>
      {steps.map((step, i) => <li key={i}><a href={`#step-${i + 1}`} aria-current={active === `step-${i + 1}` ? 'true' : undefined}>{step}</a></li>)}
      {practice && <li><a href="#practice" aria-current={active === 'practice' ? 'true' : undefined}>Практика</a></li>}
    </ol>
  );
}

function Video({lessonId, video, resume}: {lessonId: string; video: NonNullable<LessonData['lesson']['video']>; resume: number}) {
  const ref = useRef<HTMLVideoElement>(null);
  const [failed, setFailed] = useState(false);
  const [status, setStatus] = useState('');
  const lastSave = useRef(0);
  async function save(force = false) {
    const element = ref.current;
    if (!element || !bootstrap.user || (!force && Date.now() - lastSave.current < 5000)) return;
    lastSave.current = Date.now();
    try {
      await postJson(`/api/lessons/${encodeURIComponent(lessonId)}/video`, {seconds: element.currentTime});
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
        Видео не поддерживается. Прочитайте текст урока ниже.
      </video>
      {video.fixture && <p className="small">Короткий синтетический видеопример для проверки воспроизведения. Без звука. Содержание доступно текстом ниже.</p>}
      {failed && (
        <div className="notice">
          <p role="status">Видео недоступно. Можно повторить загрузку или продолжить по тексту.</p>
          <div className="actions">
            <button type="button" className="button secondary" onClick={() => { setFailed(false); ref.current?.load(); }}>Повторить загрузку видео</button>
            <a href="#lesson-reading">Перейти к тексту урока ↓</a>
          </div>
        </div>
      )}
      <p className="small" role="status">{status}</p>
    </div>
  );
}

async function copyText(text: string, report: (message: string) => void) {
  try {
    await navigator.clipboard.writeText(text);
    report('Скопировано.');
  } catch {
    report('Не удалось скопировать автоматически. Выделите текст и скопируйте его.');
  }
}

function Body({lesson}: {lesson: LessonData['lesson']}) {
  // Rich lessons are rendered on the server from an escaped Markdown subset (legacy_content.py),
  // so the HTML contains only allowlisted tags, links and media.
  if (lesson.body_html) {
    return (
      <section className="reading lesson-rich" id="lesson-reading" tabIndex={-1}
        onClick={event => {
          const button = (event.target as Element).closest('[data-copy-block]');
          if (!button) return;
          const figure = button.parentElement!;
          const status = figure.querySelector('.copy-status');
          copyText(figure.querySelector('pre')?.textContent || '', message => { if (status) status.textContent = message; });
        }}
        dangerouslySetInnerHTML={{__html: lesson.body_html}} />
    );
  }
  return (
    <section className="reading" id="lesson-reading">
      <h2 tabIndex={-1}>Разбираемся на примере</h2>
      {(lesson.paragraphs || []).map((paragraph, i) => <p key={i} className="preserve">{paragraph}</p>)}
    </section>
  );
}

function PracticePanel({data}: {data: LessonData}) {
  const {lesson} = data;
  const [saved, setSaved] = useState<Practice | null>(data.practice ?? null);
  const [body, setBody] = useState(data.practice?.body ?? '');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('Сохраняйте работу кнопкой ниже. Личные и конфиденциальные данные не нужны.');
  const [confirmed, setConfirmed] = useState(!!data.practice);
  const dirty = body !== (saved?.body ?? '');

  // Unsaved text: ask before leaving the page or the lesson.
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);
  const blocker = useBlocker(({currentLocation, nextLocation}) => dirty && currentLocation.pathname !== nextLocation.pathname);
  useEffect(() => {
    if (blocker.state !== 'blocked') return;
    if (window.confirm('Работа не сохранена. Уйти со страницы?')) blocker.proceed();
    else blocker.reset();
  }, [blocker]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const status = ((event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null)?.value === 'draft' ? 'draft' : 'submitted';
    const text = body;
    setBusy(true); setConfirmed(false); setMessage('Сохраняем…');
    try {
      await postJson(`/api/lessons/${encodeURIComponent(lesson.id)}/practice`, {body: text, status});
      // Read the stored version back so the confirmation reflects what the server keeps.
      const stored = await getJson<Practice | null>(`/api/lessons/${encodeURIComponent(lesson.id)}/practice`);
      if (!stored || stored.body !== text.trim() || stored.status !== status) throw new ApiError(0, 'Не удалось подтвердить сохранённую версию. Текст остаётся в форме.');
      setSaved(stored);
      setBody(stored.body);
      setConfirmed(true);
      setMessage(status === 'draft' ? 'Черновик сохранён' : 'Работа сохранена');
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : 'Не удалось сохранить. Текст остаётся в форме. Повторите попытку.');
    } finally {
      setBusy(false);
    }
  }

  const chip = dirty ? 'Изменения не сохранены' : saved ? (saved.status === 'draft' ? 'Черновик сохранён' : 'Результат сохранён') : 'Пока нет сохранённой работы';
  return (
    <section className="panel practice" id="practice">
      <span className="eyebrow">Примените к своей задаче</span>
      <h2>Небольшая практика</h2>
      <p>{lesson.task}</p>
      <ul>{(lesson.checklist || []).map((item, i) => <li key={i}>{item}</li>)}</ul>
      {bootstrap.user ? (
        <>
          <p className="chip">{chip}</p>
          {saved && <p className="small">Сохранено {humanTime(saved.updated_at)}</p>}
          <form onSubmit={submit}>
            <label htmlFor="practice-body">Ваш результат или ссылка</label>
            <textarea id="practice-body" name="body" rows={7} maxLength={12000} required value={body}
              placeholder="Что вы попробовали? Что получилось и что исправили?"
              onChange={event => { setBody(event.target.value); setConfirmed(false); setMessage('Есть несохранённые изменения. Нажмите кнопку сохранения.'); }} />
            <p className="small" role="status">{message}</p>
            <div className="actions">
              <button className="button secondary" name="status" value="draft" disabled={busy}>Сохранить черновик</button>
              <button className="button" name="status" value="submitted" disabled={busy}>Сохранить результат</button>
            </div>
          </form>
          {confirmed && (
            <section className="practice-confirmation" aria-label="Сохранённая работа">
              <h3>{saved?.status === 'draft' ? 'Черновик сохранён' : 'Работа сохранена'}</h3>
              <p>Она хранится в «Моих работах» — можно вернуться, доработать и сохранить заново.</p>
              <AppLink to="/profile#practice">Открыть мои работы →</AppLink>
              {data.following && !data.following.locked && <p><AppLink to={`/lessons/${data.following.id}`}>Дальше: {data.following.title} →</AppLink></p>}
            </section>
          )}
        </>
      ) : (
        <>
          <p>Войдите, чтобы сохранить практику и продолжить на другом устройстве.</p>
          <a className="button" href={`/login?next=/lessons/${lesson.id}`}>Войти и сохранить</a>
        </>
      )}
    </section>
  );
}

function CompletionPanel({data}: {data: LessonData}) {
  const [completed, setCompleted] = useState(!!data.progress?.completed);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const revalidator = useRevalidator();
  async function toggle() {
    setBusy(true); setError('');
    try {
      await postJson(`/api/lessons/${encodeURIComponent(data.lesson.id)}/completion`, {completed: !completed});
      setCompleted(!completed);
      revalidator.revalidate();   // the course outline shows the new state
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Не удалось сохранить.');
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className={'panel completion' + (data.lesson.task ? ' is-secondary' : '')}>
      <h2>{completed ? 'Урок завершён' : 'Готовы отметить свой шаг?'}</h2>
      <p>{completed ? 'Урок отмечен пройденным на карте.' : 'Отметьте урок пройденным — он отметится на карте. Практика сохраняется отдельно.'}</p>
      {bootstrap.user
        ? <button type="button" className="button" onClick={toggle} disabled={busy}>{completed ? 'Вернуть в работу' : 'Отметить завершённым'}</button>
        : <a href={`/login?next=/lessons/${data.lesson.id}`}>Войти, чтобы сохранять прогресс</a>}
      {error && <p className="small" role="alert">{error}</p>}
    </section>
  );
}

function Sidebar({data, active}: {data: LessonData; active: string | null}) {
  const steps = data.lesson.steps;
  return (
    <aside className="lesson-sidebar">
      {!data.locked && steps.length > 0 && (
        <nav className="lesson-toc" aria-label="В этом уроке">
          <p className="lesson-toc-title">В этом уроке</p>
          <Steps steps={steps} practice={!!data.lesson.task} active={active} />
        </nav>
      )}
      <details className="lesson-outline" open>
        <summary>Программа курса</summary>
        {data.outline && <Outline outline={data.outline} current={data.lesson.id} />}
      </details>
    </aside>
  );
}

function Paywall({data}: {data: LessonData}) {
  const {pathname} = useLocation();
  const entitlement = bootstrap.user?.entitlement;
  const expired = entitlement === 'expired';
  return (
    <div className="lesson-layout">
      <article className="lesson-content paywall">
        <span className="eyebrow">{data.lesson.minutes} минут · Урок клуба</span>
        <h1>{data.lesson.title}</h1>
        <p className="lead">{data.lesson.objective}</p>
        {data.lesson.steps.length > 0 && (
          <section className="paywall-outline"><h2>Что внутри</h2><ol>{data.lesson.steps.map((step, i) => <li key={i}>{step}</li>)}</ol></section>
        )}
        <section className="paywall-offer" aria-labelledby="paywall-title">
          {entitlement === 'revoked' ? (
            <>
              <h2 id="paywall-title">Доступ к клубу приостановлен</h2>
              <p>Материалы клуба для этого аккаунта сейчас закрыты. Напишите нам — разберёмся.</p>
              <div className="actions"><a className="button" href="/help">Написать в поддержку</a></div>
            </>
          ) : (
            <>
              <h2 id="paywall-title">{expired ? 'Доступ к клубу закончился' : 'Этот урок — для участников клуба'}</h2>
              <p>{expired ? 'Продлите участие, чтобы продолжить с того же места. Сохранённые работы никуда не делись.' : 'В клубе открыты все уроки курсов, практика с сохранением и новые материалы каждую неделю.'}</p>
              <div className="actions">
                <a className="button" href={`/membership?next=${pathname}`}>{expired ? 'Продлить доступ' : 'Открыть доступ'}</a>
                {!bootstrap.user && <a className="button secondary" href={`/login?next=${pathname}`}>Я уже в клубе — войти</a>}
              </div>
            </>
          )}
          {data.free_lesson && <p className="paywall-free">Пока можно пройти бесплатный урок этого курса: <AppLink to={`/lessons/${data.free_lesson.id}`}>{data.free_lesson.title} →</AppLink></p>}
        </section>
      </article>
      <Sidebar data={data} active={null} />
    </div>
  );
}

function OpenLesson({data}: {data: LessonData}) {
  const {lesson} = data;
  const active = useActiveStep(lesson.steps.length);
  return (
    <div className="lesson-layout">
      <article className="lesson-content">
        <span className="eyebrow">{lesson.minutes} минут · {lesson.access === 'free' ? 'Бесплатный урок' : 'Урок клуба'}</span>
        <h1>{lesson.title}</h1>
        <p className="lead">{lesson.objective}</p>
        {lesson.steps.length > 0 && (
          <details className="lesson-toc-mobile">
            <summary>В этом уроке · {lesson.steps.length} {plural(lesson.steps.length, 'раздел', 'раздела', 'разделов')}</summary>
            <Steps steps={lesson.steps} practice={!!lesson.task} active={active} />
          </details>
        )}
        {lesson.video && <Video lessonId={lesson.id} video={lesson.video} resume={data.progress?.video_seconds ?? 0} />}
        <Body lesson={lesson} />
        {lesson.prompt && <PromptPanel prompt={lesson.prompt} />}
        {(data.resources?.length ?? 0) > 0 && (
          <section className="materials">
            <h2>Материалы</h2>
            {data.resources!.map(resource => (
              <a key={resource.id} className="resource" href={resource.url}>
                {resource.id === 'checklist' ? '↓ ' : ''}{resource.title}<small>{resource.kind === 'text' ? 'TXT · скачать' : 'Внешний источник ↗'}</small>
              </a>
            ))}
          </section>
        )}
        {lesson.task && <PracticePanel data={data} />}
        <CompletionPanel data={data} />
        <nav className="lesson-nav" aria-label="Соседние уроки курса">
          {data.previous && <AppLink to={`/lessons/${data.previous.id}`}>← Предыдущий урок курса</AppLink>}
          {data.following
            ? <AppLink to={`/lessons/${data.following.id}`}>Следующий урок курса {data.following.locked ? '· клуб ' : ''}→</AppLink>
            : <AppLink to="/profile">К моим результатам →</AppLink>}
        </nav>
        <p><a href={`/help?lesson=${lesson.id}`}>Нужна помощь с этим уроком?</a></p>
      </article>
      <Sidebar data={data} active={active} />
    </div>
  );
}

function PromptPanel({prompt}: {prompt: string}) {
  const [status, setStatus] = useState('');
  return (
    <section className="panel">
      <h2>Запрос для первого шага</h2>
      <p className="preserve">{prompt}</p>
      <button type="button" className="button secondary" onClick={() => copyText(prompt, message => setStatus(message === 'Скопировано.' ? 'Запрос скопирован.' : message))}>Скопировать запрос</button>
      <span className="copy-status" role="status">{status}</span>
    </section>
  );
}

export default function LessonPage() {
  const data = useLoaderData() as LessonData;
  useTitle(data.lesson.title);
  useRecordVisit(data.lesson.id, data.locked);
  // Jump to an anchor (e.g. #practice from "Продолжить черновик") once the page is rendered.
  const {hash} = useLocation();
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView({block: 'start'});
  }, [hash, data.lesson.id]);
  return (
    <>
      <a className="breadcrumb" href={`/courses/${data.course.id}`}>← {data.course.title}</a>
      {data.locked ? <Paywall data={data} /> : <OpenLesson key={data.lesson.id} data={data} />}
    </>
  );
}
