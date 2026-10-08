import {useState} from 'react';
import {useLoaderData, type LoaderFunctionArgs} from 'react-router';
import {ApiError, getJson, postJson} from '../api';
import {AppLink} from '../links';
import {useTitle} from '../useTitle';

// OAuth consent for a connector (claude.ai, ChatGPT…): club/oauth.py. The pending request lives in
// the server session; this page only shows it and sends the learner's answer.

interface ConsentData {
  client: string;
  label: string;
  redirect_host: string;
  learner: string;
  access_days: number;
  /** learning: the learner's own lessons; content: editing in the admin (editors and admins only). */
  scope: 'learning' | 'content';
  allowed: boolean;
}

export const consentLoader = ({request}: LoaderFunctionArgs) => getJson<ConsentData>('/api/app/oauth/consent', request.signal);

export default function Consent() {
  const data = useLoaderData() as ConsentData;
  useTitle('Подключение ассистента');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function decide(approve: boolean) {
    setBusy(true); setError('');
    try {
      const {redirect} = await postJson<{redirect: string}>('/api/app/oauth/consent', {approve});
      window.location.assign(redirect);   // back to the assistant
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Не удалось ответить. Повторите попытку.');
      setBusy(false);
    }
  }
  if (data.scope === 'content') return <ContentConsent data={data} busy={busy} error={error} decide={decide} />;
  return (
    <section className="consent">
      <p className="eyebrow">Подключение ИИ-ассистента</p>
      <h1>Разрешить «{data.client}» доступ к вашему обучению?</h1>
      <p className="lead">Ассистент сможет помогать с уроками прямо в чате — и сохранять результат сюда, в AI Room.</p>
      <div className="consent-grid">
        <section className="panel">
          <h2>Сможет</h2>
          <ul>
            <li>видеть ваши уроки, задания и где вы остановились;</li>
            <li>сохранять вашу работу в «Мои работы» — с пометкой, что её сохранил ассистент;</li>
            <li>отмечать разделы урока, до которых вы дошли.</li>
          </ul>
        </section>
        <section className="panel">
          <h2>Не сможет</h2>
          <ul>
            <li>завершать уроки за вас;</li>
            <li>менять план, доступ к клубу и данные аккаунта;</li>
            <li>видеть уроки клуба, если у вас нет доступа.</li>
          </ul>
        </section>
      </div>
      <p className="small">
        После ответа вы вернётесь в {data.redirect_host}. Доступ продлевается, пока ассистент им пользуется, и заканчивается через {data.access_days} дней без использования.
        Отключить можно в любой момент: <AppLink to="/profile#connections">«Профиль» → Подключения</AppLink>.
      </p>
      {error && <p className="notice error" role="alert">{error}</p>}
      <div className="actions">
        <button type="button" className="button" onClick={() => decide(true)} disabled={busy}>Разрешить</button>
        <button type="button" className="button secondary" onClick={() => decide(false)} disabled={busy}>Отклонить</button>
      </div>
    </section>
  );
}

function ContentConsent({data, busy, error, decide}: {data: ConsentData; busy: boolean; error: string; decide: (approve: boolean) => void}) {
  return (
    <section className="consent">
      <p className="eyebrow">Подключение ИИ-ассистента к админке</p>
      <h1>{data.allowed ? `Разрешить «${data.client}» править контент AI Room?` : 'Это подключение — для редакторов'}</h1>
      {data.allowed ? (
        <>
          <p className="lead">Ассистент будет работать от вашего имени ({data.learner}) — как вы в админке.</p>
          <div className="consent-grid">
            <section className="panel">
              <h2>Сможет</h2>
              <ul>
                <li>читать и править курсы, модули, уроки и материалы библиотеки;</li>
                <li>создавать новые — черновиками;</li>
                <li>публиковать, отвечать на вопросы и писать отзывы на работы — когда вы попросите.</li>
              </ul>
            </section>
            <section className="panel">
              <h2>Не сможет</h2>
              <ul>
                <li>видеть почту и аккаунты учеников и аналитику;</li>
                <li>менять доступы и роли;</li>
                <li>перезаписать чужие свежие правки — такие сохранения отклоняются.</li>
              </ul>
            </section>
          </div>
          <p className="small">
            После ответа вы вернётесь в {data.redirect_host}. Отключить можно в любой момент: <a href="/admin/assistant">«Админка» → Ассистент</a>.
          </p>
        </>
      ) : (
        <p className="lead">Подключить ассистента к админке могут только редакторы и администраторы. Для учёбы добавьте коннектор по обычному адресу AI Room.</p>
      )}
      {error && <p className="notice error" role="alert">{error}</p>}
      <div className="actions">
        {data.allowed && <button type="button" className="button" onClick={() => decide(true)} disabled={busy}>Разрешить</button>}
        <button type="button" className="button secondary" onClick={() => decide(false)} disabled={busy}>{data.allowed ? 'Отклонить' : 'Вернуться в ассистента'}</button>
      </div>
    </section>
  );
}
