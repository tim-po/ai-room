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
  /** The first page's data (what its loader would fetch), so a fresh load renders without waiting. */
  page: {url: string; data: unknown} | null;
}

const element = document.getElementById('bootstrap');
export const bootstrap: Bootstrap = {csrf: '', demo_checkout: false, user: null, recorded_visit: null, notices: [], error: null, page: null,
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

const fetchJson = (path: string, init: RequestInit = {}) =>
  fetch(path, {credentials: 'same-origin', ...init, headers: {Accept: 'application/json', ...(init.headers || {})}});

async function request<T>(path: string, init: RequestInit = {}, options: Options = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetchJson(path, init);
  } catch {
    throw new ApiError(0, 'Нет связи с сервером. Проверьте подключение и повторите.');
  }
  return handle<T>(response, options);
}

async function handle<T>(response: Response, {loginOn401 = true}: Options = {}): Promise<T> {
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

// Page data fetched ahead: when the pointer rests on a link (or a finger touches it), its page's data
// starts loading, and the loader picks it up if the learner follows within half a minute. Any change
// the learner makes drops what was fetched ahead, so a page never shows data from before it.
const PREFETCH_MS = 30_000;
const ahead = new Map<string, {at: number; response: Promise<Response | null>}>();

export function prefetchJson(path: string) {
  const hit = ahead.get(path);
  if (hit && Date.now() - hit.at < PREFETCH_MS) return;
  ahead.set(path, {at: Date.now(), response: fetchJson(path).catch(() => null)});
}

export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  // The first page's data came with the page itself.
  if (bootstrap.page?.url === path) {
    const data = bootstrap.page.data as T;
    bootstrap.page = null;
    return data;
  }
  const hit = ahead.get(path);
  ahead.delete(path);
  if (hit && Date.now() - hit.at < PREFETCH_MS) {
    const response = await hit.response;
    if (response) return handle<T>(response);
  }
  return request<T>(path, {signal});
}

const send = <T>(method: string, path: string, body: unknown, options?: Options) => {
  ahead.clear();
  return request<T>(path, {method, headers: {'Content-Type': 'application/json', 'X-CSRF-Token': bootstrap.csrf}, body: JSON.stringify(body)}, options);
};

export const postJson = <T>(path: string, body: unknown, options?: Options) => send<T>('POST', path, body, options);
export const putJson = <T>(path: string, body: unknown, options?: Options) => send<T>('PUT', path, body, options);
export const deleteJson = <T>(path: string) => send<T>('DELETE', path, {});

/** Loader helper: the page's API path with the page's own query string. */
export const withSearch = (path: string, request: Request) => path + new URL(request.url).search;
