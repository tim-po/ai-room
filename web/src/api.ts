import {redirect} from 'react-router';

// Talks to the Flask backend (same origin, session cookie). Mutations send the CSRF token that
// spa.html embeds in the bootstrap JSON.

export type Role = 'learner' | 'editor' | 'admin';
export type Entitlement = 'free' | 'member' | 'revoked' | 'expired';

export interface SessionUser {
  id: string;
  name: string;
  role: Role;
  entitlement: Entitlement;
}

export interface Notice {
  kind: 'success' | 'error' | string;
  text: string;
}

export interface Bootstrap {
  csrf: string;
  demo_checkout: boolean;
  user: SessionUser | null;
  recorded_visit: string | null;
  /** Flashed by a server redirect (e.g. after a plain form post); shown on the first page. */
  notices: Notice[];
  /** Set when the server answered this page load with an error status. */
  error: {code: number; description: string} | null;
}

const element = document.getElementById('bootstrap');
export const bootstrap: Bootstrap = {csrf: '', demo_checkout: false, user: null, recorded_visit: null, notices: [], error: null,
  ...(element ? JSON.parse(element.textContent || '{}') : {})};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

interface Options {
  /** false for sign-in itself, where 401 means "wrong password", not "session ended". */
  loginOn401?: boolean;
}

async function request<T>(path: string, init: RequestInit = {}, {loginOn401 = true}: Options = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {credentials: 'same-origin', ...init, headers: {Accept: 'application/json', ...(init.headers || {})}});
  } catch {
    throw new ApiError(0, 'Нет связи с сервером. Проверьте подключение и повторите.');
  }
  if (response.status === 401 && loginOn401) {
    // Session ended: the login page brings the learner back here afterwards.
    window.location.assign(`/login?next=${encodeURIComponent(window.location.pathname)}`);
    throw new ApiError(401, 'Сессия завершена.');
  }
  if (!response.ok) {
    let message = 'Не удалось выполнить действие. Повторите попытку.';
    let body: {message?: unknown; redirect?: unknown} | null = null;
    try {
      body = await response.json();
    } catch {
      /* not JSON: keep the generic message */
    }
    // Page data the learner can't see yet (onboarding first): loaders follow the redirect.
    if (typeof body?.redirect === 'string' && body.redirect.startsWith('/')) throw redirect(body.redirect);
    if (typeof body?.message === 'string') message = body.message;
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export const getJson = <T>(path: string, signal?: AbortSignal) => request<T>(path, {signal});

const send = <T>(method: string, path: string, body: unknown, options?: Options) =>
  request<T>(path, {method, headers: {'Content-Type': 'application/json', 'X-CSRF-Token': bootstrap.csrf}, body: JSON.stringify(body)}, options);

export const postJson = <T>(path: string, body: unknown, options?: Options) => send<T>('POST', path, body, options);
export const putJson = <T>(path: string, body: unknown, options?: Options) => send<T>('PUT', path, body, options);

/** Loader helper: the page's API path with the page's own query string. */
export const withSearch = (path: string, request: Request) => path + new URL(request.url).search;
