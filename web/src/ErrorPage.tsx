import {isRouteErrorResponse, useRouteError} from 'react-router';
import {ApiError, bootstrap} from './api';
import {AppLink} from './links';
import {useTitle} from './useTitle';

const TITLES: Record<number, string> = {
  400: 'Не удалось сохранить', 401: 'Нужно войти', 403: 'Этот раздел пока закрыт', 404: 'Страница не найдена',
  409: 'Материал уже изменён', 413: 'Слишком большой запрос', 429: 'Небольшая пауза',
};
const GENERIC = 'Откройте библиотеку или вернитесь к обучению. Если проблема повторяется, сохраните вопрос в разделе помощи.';

/** Error status from the server (page load) or from a page's data request. */
export default function ErrorPage({code, message}: {code: number; message?: string}) {
  useTitle(TITLES[code] ?? 'Ошибка');
  // Server messages are Russian; framework defaults (English) and auth/size errors get the general text.
  const text = message && /[а-яё]/i.test(message) && ![401, 404, 413].includes(code) ? message
    : code ? GENERIC : 'Проверьте подключение и обновите страницу.';
  return (
    <section className="panel narrow error-page">
      <span className="eyebrow">{code || 'Нет связи'}</span>
      <h1>{TITLES[code] ?? 'Не удалось открыть страницу'}</h1>
      <p>{text}</p>
      <div className="actions">
        <AppLink className="button" to="/catalogue">К бесплатным урокам</AppLink>
        {!code && <button type="button" className="button secondary" onClick={() => window.location.reload()}>Обновить</button>}
        <AppLink to="/help">Помощь</AppLink>
        {!bootstrap.user && <AppLink to="/login">Войти</AppLink>}
      </div>
    </section>
  );
}

/** errorElement for routes: a failed loader (ApiError) or an unknown path. */
export function RouteError() {
  const error = useRouteError();
  if (error instanceof ApiError) return <ErrorPage code={error.status} message={error.message} />;
  if (isRouteErrorResponse(error)) return <ErrorPage code={error.status} />;
  return <ErrorPage code={0} />;
}

export function NotFound() {
  return <ErrorPage code={404} />;
}
