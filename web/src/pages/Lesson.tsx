import {useEffect, useState, type FormEvent} from 'react';
import {useBlocker, useLoaderData, useLocation, type LoaderFunctionArgs} from 'react-router';
import {ApiError, bootstrap, getJson, postJson} from '../api';
import AssistantHandoff from '../components/AssistantHandoff';
import {PromptPanel, Resources, RichBody, Video} from '../components/Media';
import Outline from '../components/Outline';
import {humanTime, plural} from '../format';
import {AppLink} from '../Shell';
import type {LessonData, Practice} from '../types';
import {useTitle} from '../useTitle';
import {CheckpointList, FinishPanel, ProgressBar, ResumeBanner, TocHeading, useCheckpoints, type Checkpoints} from './lesson/FinishLine';

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

function Body({lesson}: {lesson: LessonData['lesson']}) {
  // Rich lessons are rendered on the server from an escaped Markdown subset (legacy_content.py),
  // so the HTML contains only allowlisted tags, links and media.
  if (lesson.body_html) return <RichBody id="lesson-reading" html={lesson.body_html} />;
  return (
    <section className="reading" id="lesson-reading">
      <h2 tabIndex={-1}>Разбираемся на примере</h2>
      {(lesson.paragraphs || []).map((paragraph, i) => <p key={i} className="preserve">{paragraph}</p>)}
    </section>
  );
}

function PracticePanel({data, onSaved}: {data: LessonData; onSaved: () => void}) {
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
      onSaved();
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
      <AssistantHandoff data={data} draft={body} />
      {bootstrap.user ? (
        <>
          <p className="chip">{chip}</p>
          {saved && <p className="small">{saved.via ? `Сохранено ассистентом (${saved.via})` : 'Сохранено'} {humanTime(saved.updated_at)}</p>}
          {saved?.review && (
            <div className="practice-review" role="note">
              <p className="practice-review-head">Отзыв преподавателя · {saved.review.reviewer}, {humanTime(saved.review.updated_at)}</p>
              <p className="preserve">{saved.review.body}</p>
            </div>
          )}
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
            </section>
          )}
        </>
      ) : (
        <>
          <p>Войдите, чтобы сохранить практику и продолжить на другом устройстве.</p>
          <AppLink className="button" to={`/login?next=/lessons/${lesson.id}`}>Войти и сохранить</AppLink>
        </>
      )}
    </section>
  );
}

function Sidebar({data, points}: {data: LessonData; points: Checkpoints | null}) {
  return (
    <aside className="lesson-sidebar">
      {points && points.total > 0 && (
        <nav className="lesson-toc" aria-label="В этом уроке">
          <TocHeading points={points} />
          <CheckpointList points={points} />
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
              <div className="actions"><AppLink className="button" to="/help">Написать в поддержку</AppLink></div>
            </>
          ) : (
            <>
              <h2 id="paywall-title">{expired ? 'Доступ к клубу закончился' : 'Этот урок — для участников клуба'}</h2>
              <p>{expired ? 'Продлите участие, чтобы продолжить с того же места. Сохранённые работы никуда не делись.' : 'В клубе открыты все уроки курсов, практика с сохранением и новые материалы каждую неделю.'}</p>
              <div className="actions">
                <AppLink className="button" to={`/membership?next=${pathname}`}>{expired ? 'Продлить доступ' : 'Открыть доступ'}</AppLink>
                {!bootstrap.user && <AppLink className="button secondary" to={`/login?next=${pathname}`}>Я уже в клубе — войти</AppLink>}
              </div>
            </>
          )}
          {data.free_lesson && <p className="paywall-free">Пока можно пройти бесплатный урок этого курса: <AppLink to={`/lessons/${data.free_lesson.id}`}>{data.free_lesson.title} →</AppLink></p>}
        </section>
      </article>
      <Sidebar data={data} points={null} />
    </div>
  );
}

function OpenLesson({data}: {data: LessonData}) {
  const {lesson} = data;
  const points = useCheckpoints(data);
  const [practiceSaved, setPracticeSaved] = useState(!!data.practice);
  return (
    <div className="lesson-layout">
      <article className="lesson-content">
        <ProgressBar points={points} />
        <span className="eyebrow">{lesson.minutes} минут · {lesson.access === 'free' ? 'Бесплатный урок' : 'Урок клуба'}</span>
        <h1>{lesson.title}</h1>
        <p className="lead">{lesson.objective}</p>
        <ResumeBanner data={data} points={points} />
        {points.total > 0 && (
          <details className="lesson-toc-mobile">
            <summary>В этом уроке · {points.total} {plural(points.total, 'раздел', 'раздела', 'разделов')} · пройдено {points.furthest}</summary>
            <CheckpointList points={points} />
          </details>
        )}
        {lesson.video && <Video video={lesson.video} resume={data.progress?.video_seconds ?? 0} saveUrl={`/api/lessons/${encodeURIComponent(lesson.id)}/video`} readingAnchor="lesson-reading" />}
        <Body lesson={lesson} />
        {lesson.prompt && <PromptPanel prompt={lesson.prompt} />}
        <Resources resources={data.resources ?? []} title="Материалы" />
        {lesson.task
          ? <PracticePanel data={data} onSaved={() => setPracticeSaved(true)} />
          : <AssistantHandoff data={data} section={points.titles[points.current - 1]} />}
        <FinishPanel data={data} points={points} practiceSaved={practiceSaved} />
        <nav className="lesson-nav" aria-label="Соседние уроки курса">
          {data.previous && <AppLink to={`/lessons/${data.previous.id}`}>← Предыдущий урок курса</AppLink>}
          {data.following
            ? <AppLink to={`/lessons/${data.following.id}`}>Следующий урок курса {data.following.locked ? '· клуб ' : ''}→</AppLink>
            : <AppLink to="/profile">К моим результатам →</AppLink>}
        </nav>
        <p><AppLink to={`/help?lesson=${lesson.id}`}>Нужна помощь с этим уроком?</AppLink></p>
      </article>
      <Sidebar data={data} points={points} />
    </div>
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
      <AppLink className="breadcrumb" to={`/courses/${data.course.id}`}>← {data.course.title}</AppLink>
      {data.locked ? <Paywall data={data} /> : <OpenLesson key={data.lesson.id} data={data} />}
    </>
  );
}
