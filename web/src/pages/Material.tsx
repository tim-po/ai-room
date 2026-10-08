import {useState} from 'react';
import {useLoaderData, useLocation, type LoaderFunctionArgs} from 'react-router';
import {ApiError, bootstrap, getJson, postJson} from '../api';
import {PromptPanel, Resources, RichBody, Video} from '../components/Media';
import {humanDate} from '../format';
import {AppLink} from '../Shell';
import type {MaterialData} from '../types';
import {useTitle} from '../useTitle';

export const materialLoader = ({params, request}: LoaderFunctionArgs) =>
  getJson<MaterialData>(`/api/app/materials/${encodeURIComponent(params.id!)}`, request.signal);

function Favourite({id, initial}: {id: string; initial: boolean}) {
  const [saved, setSaved] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function toggle() {
    setBusy(true); setError('');
    try {
      const result = await postJson<{favourite: boolean}>(`/materials/${encodeURIComponent(id)}/favourite`, {saved: !saved});
      setSaved(result.favourite);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Не удалось сохранить.');
    } finally {
      setBusy(false);
    }
  }
  return (
    <p className="actions">
      <button type="button" className="button secondary" onClick={toggle} disabled={busy} aria-pressed={saved}>{saved ? 'Убрать из избранного' : 'В избранное'}</button>
      {error && <span className="small" role="alert">{error}</span>}
    </p>
  );
}

export default function Material() {
  const data = useLoaderData() as MaterialData;
  const {item} = data;
  const {pathname} = useLocation();
  useTitle(item.title);
  return (
    <>
      <AppLink className="breadcrumb" to={`/discover?class=${item.format}`}>← {item.format_label === 'Кейс' ? 'Все кейсы' : item.format_label === 'Воркшоп' ? 'Все воркшопы' : 'Все гайды'}</AppLink>
      <article className="material-content">
        <span className="chip">{item.format_label} · {item.access === 'free' ? 'Бесплатно' : 'Материал клуба'}</span>
        <h1>{item.title}</h1>
        <p className="lead">{item.description}</p>
        <p className="metadata">{item.level} · {item.minutes} мин · {item.author} · обновлено {humanDate(item.updated_at)}</p>
        <section className="panel warm">
          <h2>Что получится</h2>
          <p>{item.outcome}</p>
          {item.prerequisites && <p><strong>Перед началом:</strong> {item.prerequisites}</p>}
          {item.tools && <p><strong>Инструменты и расходы:</strong> {item.tools}</p>}
        </section>
        {data.locked ? (
          <section className="paywall-offer" aria-labelledby="paywall-title">
            <h2 id="paywall-title">{bootstrap.user?.entitlement === 'revoked' ? 'Доступ к клубу приостановлен' : 'Этот материал — для участников клуба'}</h2>
            {bootstrap.user?.entitlement === 'revoked' ? (
              <><p>Материалы клуба для этого аккаунта сейчас закрыты. Напишите нам — разберёмся.</p><div className="actions"><AppLink className="button" to="/help">Написать в поддержку</AppLink></div></>
            ) : (
              <>
                <p>В клубе открыты все уроки курсов, гайды и записи воркшопов.</p>
                <div className="actions">
                  <AppLink className="button" to={`/membership?next=${pathname}`}>Открыть доступ</AppLink>
                  {!bootstrap.user && <AppLink className="button secondary" to={`/login?next=${pathname}`}>Я уже в клубе — войти</AppLink>}
                </div>
              </>
            )}
            <p className="paywall-free">Бесплатные материалы — в <AppLink to="/discover?access=free">обзоре →</AppLink></p>
          </section>
        ) : (
          <>
            {item.video && <Video video={item.video} resume={data.seconds ?? 0} saveUrl={`/api/materials/${encodeURIComponent(item.id)}/video`} readingAnchor="material-reading" />}
            {item.body_html ? <RichBody id="material-reading" html={item.body_html} /> : (
              <section className="reading" id="material-reading">
                <h2>Разбираем задачу</h2>
                {(item.paragraphs ?? []).map((paragraph, i) => <p key={i} className="preserve">{paragraph}</p>)}
              </section>
            )}
            {item.prompt && <PromptPanel prompt={item.prompt} title="Запрос для вашей задачи" />}
            <Resources resources={data.resources ?? []} title="Ресурсы" />
            {bootstrap.user
              ? <Favourite id={item.id} initial={!!data.favourite} />
              : <p><AppLink to={`/login?next=${pathname}`}>Войдите, чтобы сохранить в избранном</AppLink></p>}
            <p className="small">Самостоятельные материалы не меняют завершение уроков. Избранное находится в профиле.</p>
            <AppLink to="/help">Нужна помощь?</AppLink>
          </>
        )}
      </article>
    </>
  );
}
