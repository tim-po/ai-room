import {useState, type FormEvent} from 'react';
import {useLocation} from 'react-router';
import {ApiError, postJson} from '../api';
import {AppLink} from '../Shell';
import {useTitle} from '../useTitle';

export default function Login() {
  const {search} = useLocation();
  useTitle('Вход');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError('');
    try {
      // The server keeps ?next= safe and may send a new learner to onboarding first.
      const result = await postJson<{next: string}>(`/login${search}`, {email, password}, {loginOn401: false});
      // A new session means a new CSRF token and user: load the next page from the server.
      window.location.assign(result.next);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Не удалось войти. Повторите попытку.');
      setBusy(false);
    }
  }
  return (
    <div className="login-layout">
      <section>
        <h1>Вход в аккаунт</h1>
        <p className="welcome-lead">Войдите, чтобы сохранять работы и продолжать обучение с другого устройства.</p>
      </section>
      <section className="panel login-form">
        <h2>Войти в AI Room</h2>
        <form method="post" onSubmit={submit}>
          <label>Почта<input name="email" type="email" required autoComplete="username" maxLength={254} value={email} onChange={e => setEmail(e.target.value)} /></label>
          <label>Пароль<input name="password" type="password" required autoComplete="current-password" maxLength={1024} value={password} onChange={e => setPassword(e.target.value)} /></label>
          {error && <p className="notice error" role="alert">{error}</p>}
          <button className="button" disabled={busy}>{busy ? 'Входим…' : 'Войти'}</button>
        </form>
        <p className="small">Доступ по приглашению. Нет доступа или забыли пароль? Обратитесь к тому, кто пригласил вас в AI Room.</p>
        <AppLink to="/catalogue">Посмотреть бесплатные уроки →</AppLink>
      </section>
    </div>
  );
}
