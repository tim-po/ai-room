import {useState} from 'react';
import {useLoaderData, useLocation, useNavigate, type LoaderFunctionArgs} from 'react-router';
import {ApiError, bootstrap, getJson, postJson, withSearch, type Entitlement} from '../api';
import {AppLink, isSpaPath} from '../Shell';
import type {MembershipData} from '../types';
import {useTitle} from '../useTitle';

export const membershipLoader = ({request}: LoaderFunctionArgs) =>
  getJson<MembershipData>(withSearch('/api/app/membership', request), request.signal);

/** Staging only (CLUB_DEMO_CHECKOUT=1): switches the learner's own access without billing. */
export function DemoSwitch({next}: {next: string}) {
  const navigate = useNavigate();
  const {pathname} = useLocation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const member = bootstrap.user?.entitlement === 'member';
  async function toggle() {
    setBusy(true); setError('');
    try {
      const result = await postJson<{entitlement: Entitlement; next: string; message: string}>(
        member ? '/membership/demo/cancel' : '/membership/demo', {next});
      bootstrap.user!.entitlement = result.entitlement;
      if (isSpaPath(result.next)) navigate(result.next, {replace: result.next === pathname, state: {notice: result.message}});
      else window.location.assign(result.next);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Не удалось переключить доступ.');
    } finally {
      setBusy(false);   // returning to this same page keeps the component mounted
    }
  }
  return (
    <>
      <p className="small">Тестовая версия: оплата не подключена, доступ переключается без списаний.</p>
      <button type="button" className={member ? 'button secondary' : 'button'} onClick={toggle} disabled={busy}>
        {member ? 'Выключить демо-доступ' : 'Включить демо-доступ'}
      </button>
      {error && <p className="small" role="alert">{error}</p>}
    </>
  );
}

export default function Membership() {
  const data = useLoaderData() as MembershipData;
  useTitle('Клуб');
  const user = bootstrap.user;
  const member = !!user && (user.entitlement === 'member' || user.role !== 'learner');
  return (
    <section className="membership">
      <h1>{member ? 'Вы в клубе' : 'Клуб AI Room'}</h1>
      <p className="lead">Бесплатные уроки помогают начать. В клубе открыты полные курсы, практика с сохранением и новые материалы.</p>
      <ul className="membership-list">
        <li><strong>{data.member_lessons}</strong> уроков клуба в дополнение к {data.free_lessons} бесплатным</li>
        <li>Работы и прогресс сохраняются в одном месте</li>
        <li>Отменить можно в любой момент — сохранённое останется</li>
      </ul>
      <div className="paywall-offer">
        {!user ? (
          <><p>Войдите, чтобы открыть доступ к клубу.</p><div className="actions"><AppLink className="button" to="/login?next=/membership">Войти</AppLink></div></>
        ) : user.entitlement === 'revoked' ? (
          <p>Доступ этого аккаунта приостановлен. <AppLink to="/help">Написать в поддержку</AppLink></p>
        ) : user.role !== 'learner' ? (
          <p>У вашей роли уже есть доступ ко всем урокам.</p>
        ) : data.demo ? (
          <DemoSwitch next={data.return_to} />
        ) : member ? (
          <p>Доступ активен. <AppLink to="/catalogue">Перейти к урокам →</AppLink></p>
        ) : (
          <p>Оплата в этой версии пока не подключена. Чтобы получить доступ, <AppLink to="/help">напишите нам</AppLink>.</p>
        )}
      </div>
    </section>
  );
}
