import {useLoaderData} from 'react-router';
import type {ReactNode} from 'react';
import {getJson} from '../api';
import {humanTime} from '../format';
import type {JourneyData} from '../journey';
import {AppLink, ThemeToggle} from '../Shell';
import type {ProfileData} from '../types';
import {useTitle} from '../useTitle';

// Профиль: the account. Who you are and what you're learning for («О себе»), the subscription, how you sign in
// (Telegram, email), help; saved works and favourites when there are any. The study plan, courses
// and progress live on Главная.

export const profileLoader = async ({request}: {request: Request}) => {
  const [profile, journey] = await Promise.all([getJson<ProfileData>('/api/app/profile', request.signal), getJson<JourneyData>('/api/app/journey', request.signal)]);
  return {profile, journey};
};

const ACCESS_LABEL: Record<string, string> = {free: 'Без подписки', member: 'Подписка активна', revoked: 'Доступ приостановлен', expired: 'Подписка закончилась'};
const ACCESS_TEXT: Record<string, string> = {free: 'Неактивна', member: 'Активна', revoked: 'Приостановлена', expired: 'Закончилась'};

const ICONS: Record<string, ReactNode> = {
  card: <path d="M3.5 7.5h17M5 5h14a1.5 1.5 0 0 1 1.5 1.5v11A1.5 1.5 0 0 1 19 19H5a1.5 1.5 0 0 1-1.5-1.5v-11A1.5 1.5 0 0 1 5 5Z" />,
  telegram: <path d="m21 4-18 7.5 6.5 2L12 20l3-4.5 4.5 3.5L21 4Zm-11.5 9.5L21 4" />,
  mail: <path d="M4 6h16v12H4zM4 7l8 6 8-6" />,
  bot: <path d="M8 9h8a3 3 0 0 1 3 3v4a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3v-4a3 3 0 0 1 3-3Zm4-4v4M9.5 14h.01M14.5 14h.01" />,
  help: <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-5a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM5.6 5.6l3.6 3.6m5.6 5.6 3.6 3.6m0-12.8-3.6 3.6m-5.6 5.6-3.6 3.6" />,
};

/** One row of the profile: an icon, what it is, its state, and an action on the right. */
function Row({icon, title, sub, children, id}: {icon: string; title: string; sub?: ReactNode; children?: ReactNode; id?: string}) {
  return (
    <div className="pf-row" id={id}>
      <span className="pf-icon" aria-hidden="true"><svg viewBox="0 0 24 24">{ICONS[icon]}</svg></span>
      <div className="pf-row-main"><strong>{title}</strong>{sub && <span>{sub}</span>}</div>
      {children && <div className="pf-row-actions">{children}</div>}
    </div>
  );
}

const masked = (email: string) => { const [name, domain] = email.split('@'); return domain ? `${name[0] ?? ''}•••@${domain}` : email; };

export default function Profile() {
  const {profile: data, journey} = useLoaderData() as {profile: ProfileData; journey: JourneyData};
  useTitle('Профиль');
  const {user} = data;
  const staff = user.role !== 'learner';
  const member = user.entitlement === 'member' || staff;
  const goals = journey.path?.goals ?? [];
  return (
    <div className="pf">
      <header className="pf-hero">
        <span className="pf-avatar" aria-hidden="true">{(user.name.trim()[0] ?? '·').toUpperCase()}</span>
        <div className="pf-id">
          <h1>{user.name}</h1>
          <span className={'pf-status' + (member ? ' is-member' : '')}>{staff ? 'Полный доступ' : ACCESS_LABEL[user.entitlement]}</span>
        </div>
        <span className="pf-theme"><ThemeToggle /></span>
        <AppLink className="pf-settings" to="/preferences" aria-label="Настройки" title="Настройки">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 15.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4Z" /><path d="M19.4 13.5a7.6 7.6 0 0 0 0-3l2-1.5-2-3.4-2.3.9a7.5 7.5 0 0 0-2.6-1.5L14.1 2.5h-4.2l-.4 2.5a7.5 7.5 0 0 0-2.6 1.5l-2.3-.9-2 3.4 2 1.5a7.6 7.6 0 0 0 0 3l-2 1.5 2 3.4 2.3-.9a7.5 7.5 0 0 0 2.6 1.5l.4 2.5h4.2l.4-2.5a7.5 7.5 0 0 0 2.6-1.5l2.3.9 2-3.4z" /></svg>
        </AppLink>
      </header>

      <section className="pf-about" aria-labelledby="about-title">
        <div>
          <p className="pf-label" id="about-title">О себе</p>
          {goals.length ? (
            <p className="pf-goals">{goals.map(g => <span key={g.id}><i style={{background: g.color}} />{g.title}</span>)}</p>
          ) : <p>Расскажи о себе — подберём путь и материалы под твой уровень и цели.</p>}
        </div>
        <AppLink className="button" to="/onboarding?step=goals">{goals.length ? 'Изменить' : 'Заполнить'}</AppLink>
      </section>

      <section className="pf-section" aria-labelledby="sub-title">
        <h2 className="pf-label" id="sub-title">Подписка</h2>
        <Row icon="card" title="Подписка" sub={staff ? 'Полный доступ по роли' : ACCESS_TEXT[user.entitlement]} id="club">
          {staff ? null : user.entitlement === 'revoked' ? <AppLink className="button secondary" to="/help">Написать в поддержку</AppLink>
            : member ? <AppLink className="button secondary" to="/membership">Управлять</AppLink>
            : <AppLink className="button" to="/membership">Купить подписку</AppLink>}
        </Row>
      </section>

      <section className="pf-section" aria-labelledby="access-title">
        <h2 className="pf-label" id="access-title">Доступ и вход</h2>
        <Row icon="telegram" title="Telegram" sub="Не привязан">
          <span className="pf-chip is-muted">Скоро</span>
        </Row>
        <Row icon="mail" title="Почта" sub={masked(user.email)} />
      </section>

      <section className="pf-section" aria-labelledby="help-title">
        <h2 className="pf-label" id="help-title">Помощь</h2>
        <Row icon="help" title="Служба заботы" sub="Поможем с подпиской, оплатой и доступом">
          <AppLink className="button secondary" to="/help">Написать</AppLink>
        </Row>
      </section>

      {data.practices.length > 0 && (
        <section className="pf-section" id="practice" aria-labelledby="practice-title">
          <h2 className="pf-label" id="practice-title">Мои работы · {data.practices.length}</h2>
          {data.practices.map(p => (
            <article key={p.lesson_id} className="me-work">
              <div className="me-work-head">
                <AppLink to={`/lessons/${p.lesson_id}#practice`}>{p.title}</AppLink>
                <span className="me-chips">
                  {p.via && <span className="me-chip is-via">из {p.via}</span>}
                  {p.review && <span className="me-chip is-review">есть отзыв</span>}
                  <span className={'me-chip ' + (p.status === 'draft' ? 'is-draft' : 'is-saved')}>{p.status === 'draft' ? 'Черновик' : 'Результат'}</span>
                </span>
              </div>
              <p className="preserve">{p.body.length > 280 ? p.body.slice(0, 277) + '…' : p.body}</p>
              <p className="me-work-date">Сохранено {humanTime(p.updated_at)}</p>
              {p.review && (
                <div className="practice-review">
                  <p className="practice-review-head">Отзыв · {p.review.reviewer}, {humanTime(p.review.updated_at)}</p>
                  <p className="preserve">{p.review.body}</p>
                </div>
              )}
            </article>
          ))}
        </section>
      )}

      {(data.favourites.length > 0 || data.material_favourites.length > 0) && (
        <section className="pf-section" aria-labelledby="fav-title">
          <h2 className="pf-label" id="fav-title">Избранное</h2>
          <div className="pf-favs">
            {data.material_favourites.map(m => <AppLink key={m.id} to={`/materials/${m.id}`}>{m.title}</AppLink>)}
            {data.favourites.map(c => <AppLink key={c.id} to={`/courses/${c.id}`}>{c.title}</AppLink>)}
          </div>
        </section>
      )}
    </div>
  );
}
