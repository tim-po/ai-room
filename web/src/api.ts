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

export interface Bootstrap {
  csrf: string;
  demo_checkout: boolean;
  user: SessionUser | null;
  recorded_visit: string | null;
}

const element = document.getElementById('bootstrap');
export const bootstrap: Bootstrap = element ? JSON.parse(element.textContent || '{}') : {csrf: '', demo_checkout: false, user: null, recorded_visit: null};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {credentials: 'same-origin', ...init, headers: {Accept: 'application/json', ...(init.headers || {})}});
  } catch {
    throw new ApiError(0, 'Нет связи с сервером. Проверьте подключение и повторите.');
  }
  if (response.status === 401) {
    // Session ended: the login page brings the learner back here afterwards.
    window.location.assign(`/login?next=${encodeURIComponent(window.location.pathname)}`);
    throw new ApiError(401, 'Сессия завершена.');
  }
  if (!response.ok) {
    let message = 'Не удалось выполнить действие. Повторите попытку.';
    try {
      const body = await response.json();
      if (body && typeof body.message === 'string') message = body.message;
    } catch {
      /* not JSON: keep the generic message */
    }
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export const getJson = <T>(path: string, signal?: AbortSignal) => request<T>(path, {signal});

export const postJson = <T>(path: string, body: unknown) =>
  request<T>(path, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': bootstrap.csrf}, body: JSON.stringify(body)});
