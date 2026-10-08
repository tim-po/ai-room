import {useLoaderData} from 'react-router';
import {useState} from 'react';
import {ApiError, bootstrap, deleteJson, getJson, postJson} from '../api';
import {copyAsync, type Link} from '../components/AssistantHandoff';
import {ReturnBriefing, stepLabel} from '../components/Briefing';
import {CalendarLinks} from '../components/PlanEditor';
import {humanTime, plural} from '../format';
import {formatDays, formatSession, nextSession} from '../plan';
import {AppLink} from '../Shell';
import {DemoSwitch} from './Membership';
import {RanksPanel} from '../components/Ranks';
import type {Connection, CourseProgress, ProfileData} from '../types';
import {useTitle} from '../useTitle';

export const profileLoader = ({request}: {request: Request}) => getJson<ProfileData>('/api/app/profile', request.signal);

const ACCESS_LABEL: Record<string, string> = {free: 'Бесплатный доступ', member: 'Участник клуба', revoked: 'Доступ приостановлен', expired: 'Доступ закончился'};
const ACCESS_TEXT: Record<string, string> = {
  free: 'Бесплатные уроки открыты.', member: 'Уроки клуба доступны.',
  revoked: 'Доступ участника отозван. Бесплатные уроки остаются доступны.', expired: 'Срок доступа истёк. Бесплатные уроки остаются доступны.',
};

/** The club page lives here now: status, what the club adds, and the way in (or out). */
function Club({data}: {data: ProfileData}) {
  const {user, club} = data;
  const member = user.entitlement === 'member' || user.role !== 'learner';
  return (
    <section className={'me-panel me-club' + (member ? ' is-member' : '')} id="club" aria-labelledby="club-title">
      <h2 id="club-title">Клуб</h2>
      <p className="me-club-status">{member ? 'Вы в клубе' : ACCESS_LABEL[user.entitlement]}</p>
      <p>{ACCESS_TEXT[user.entitlement]}</p>
      <ul className="me-club-list">
        <li><strong>{club.member_lessons}</strong> {plural(club.member_lessons, 'урок', 'урока', 'уроков')} клуба в дополнение к {club.free_lessons} бесплатным</li>
        <li>Полные курсы, практика с сохранением и новые материалы</li>
        <li>Отменить можно в любой момент — сохранённое останется</li>
      </ul>
      {user.entitlement === 'revoked' ? <AppLink to="/help">Написать в поддержку →</AppLink>
        : user.role !== 'learner' ? <p className="small">У вашей роли есть доступ ко всем урокам.</p>
        : club.demo ? <DemoSwitch next="/profile" />
        : member ? <AppLink to="/help">Вопрос по доступу →</AppLink>
        : <AppLink to="/membership">Как получить доступ →</AppLink>}
    </section>
  );
}

function CourseRow({course, entitlement}: {course: CourseProgress; entitlement: string}) {
  const remaining = course.done < course.total;
  return (
    <div className={'me-course' + (remaining ? '' : ' is-complete')}>
      <div className="me-course-main">
        <AppLink className="me-course-title" to={`/courses/${course.id}`}>{course.title}</AppLink>
        {remaining && <progress className="me-progress" value={course.done} max={course.total || 1} aria-label={`Пройдено ${course.done} из ${course.total}`} />}
        <p className="me-course-meta">
          Пройдено {course.done} / {course.total} {plural(course.total, 'урок', 'урока', 'уроков')}
          {course.next && <> · Дальше: <AppLink to={`/lessons/${course.next.id}`}>{course.next.title}</AppLink></>}
          {!course.next && course.next_locked && <> · Дальше — урок клуба: <AppLink to={`/lessons/${course.next_locked.id}`}>{course.next_locked.title}</AppLink></>}
          {!course.next && !course.next_locked && remaining && ' · Открытые уроки пройдены'}
        </p>
      </div>
      {remaining && (course.next
        ? <AppLink className="button secondary" to={`/lessons/${course.next.id}`}>Продолжить</AppLink>
        : course.next_locked && entitlement !== 'revoked'
          ? <AppLink className="button secondary" to={`/membership?next=/lessons/${course.next_locked.id}`}>Открыть доступ</AppLink>
          : <AppLink className="button secondary" to={`/courses/${course.id}`}>Открыть курс</AppLink>)}
    </div>
  );
}

/** Assistants connected with a link from a lesson; each can be switched off. */
function Connections({initial}: {initial: Connection[]}) {
  const [items, setItems] = useState(initial);
  const [link, setLink] = useState<Link | null>(null);
  const [status, setStatus] = useState('');
  async function revoke(id: string) {
    try {
      setItems((await deleteJson<{connections: Connection[]}>(`/api/app/connections/${id}`)).connections);
      setStatus('Ассистент отключён.');
    } catch (e) {
      setStatus(e instanceof ApiError ? e.message : 'Не удалось отключить. Повторите попытку.');
    }
  }
  async function newLink() {
    const made: {link: Link | null} = {link: null};
    try {
      await copyAsync(async () => (made.link = await postJson<Link>('/api/app/attach-links', {})).url);
      setLink(made.link);
      setStatus('Ссылка скопирована — вставьте её в чат с ассистентом.');
    } catch (e) {
      if (made.link) setLink(made.link);
      setStatus(made.link ? 'Ссылка готова — скопируйте её из поля.' : e instanceof ApiError ? e.message : 'Не удалось создать ссылку.');
    }
  }
  return (
    <section className="me-panel" id="connections" aria-labelledby="connections-title">
      <h2 id="connections-title">Подключения</h2>
      {items.length ? (
        <ul className="connections">
          {items.map(c => (
            <li key={c.id}>
              <span><strong>{c.label}</strong><span className="small">подключён {humanTime(c.created_at)}{c.last_used_at ? ` · был ${humanTime(c.last_used_at)}` : ''}</span></span>
              <button type="button" className="link-button" onClick={() => revoke(c.id)}>Отключить</button>
            </li>
          ))}
        </ul>
      ) : <p className="me-note">Дайте своему ИИ-ассистенту ссылку из урока — он увидит задание и сможет сохранить вашу работу сюда. Подключённые ассистенты появятся здесь.</p>}
      <button type="button" className="button secondary" onClick={newLink}>Ссылка для ассистента</button>
      {link && <input className="connection-link" readOnly value={link.url} aria-label="Ссылка для ассистента" onFocus={e => e.currentTarget.select()} />}
      <p className="small" role="status">{status}</p>
    </section>
  );
}

export default function Profile() {
  const data = useLoaderData() as ProfileData;
  useTitle('Профиль');
  const {user, briefing, plan} = data;
  const unfinished = data.continuation.unfinished;
  const next = nextSession(plan);
  return (
    <div className="me">
      <header className="me-hero">
        <span className="me-avatar" aria-hidden="true">{(user.name.trim()[0] ?? '·').toUpperCase()}</span>
        <div className="me-id">
          <h1>{user.name}</h1>
          <p className="me-id-meta">
            <AppLink to="#club" className={`me-status is-${user.entitlement === 'member' || user.role !== 'learner' ? 'member' : user.entitlement}`}>{user.role !== 'learner' ? 'Полный доступ' : ACCESS_LABEL[user.entitlement]}</AppLink>
            <span>{user.email}</span>
          </p>
        </div>
        <nav className="me-hero-actions" aria-label="Настройки">
          <AppLink className="button secondary" to="/onboarding">Интересы и темп</AppLink>
          <AppLink className="button secondary" to="/preferences">Настройки</AppLink>
          <AppLink className="button secondary" to="/help">Помощь</AppLink>
          <form className="me-logout" method="post" action="/logout">
            <input type="hidden" name="csrf" value={bootstrap.csrf} />
            <button type="submit" className="link-button">Выйти</button>
          </form>
        </nav>
      </header>
      {[[data.stats.lessons_done, plural(data.stats.lessons_done, 'урок пройден', 'урока пройдено', 'уроков пройдено')],
        [data.stats.works, plural(data.stats.works, 'работа сохранена', 'работы сохранено', 'работ сохранено')],
        [data.stats.days, plural(data.stats.days, 'день', 'дня', 'дней') + ' с обучением за месяц'],
        [data.active_courses.length, plural(data.active_courses.length, 'курс', 'курса', 'курсов') + ' в работе'],
      ].some(([n]) => n) && (
        <ul className="me-stats" aria-label="Итоги">
          {[[data.stats.lessons_done, plural(data.stats.lessons_done, 'урок пройден', 'урока пройдено', 'уроков пройдено')],
            [data.stats.works, plural(data.stats.works, 'работа сохранена', 'работы сохранено', 'работ сохранено')],
            [data.stats.days, plural(data.stats.days, 'день', 'дня', 'дней') + ' с обучением за месяц'],
            [data.active_courses.length, plural(data.active_courses.length, 'курс', 'курса', 'курсов') + ' в работе'],
          ].filter(([n]) => n).map(([n, label]) => <li key={String(label)}><strong>{n}</strong><span>{label}</span></li>)}
        </ul>
      )}
      <div className="me-grid">
        <div className="me-main">
          {briefing?.returning ? (
            <ReturnBriefing briefing={briefing} className="me-briefing" />
          ) : unfinished ? (
            <AppLink className="me-continue" to={briefing?.url ?? unfinished.url + (unfinished.status === 'draft' ? '#practice' : '')} aria-label={`Продолжить: ${unfinished.title}`}>
              <span className="me-continue-label">{unfinished.status === 'draft' ? 'Черновик ждёт вас' : 'Продолжить урок'}{stepLabel(briefing) && ` · ${stepLabel(briefing)}`}</span>
              <strong>{unfinished.title}</strong>
              <span className="me-continue-action">Продолжить →</span>
            </AppLink>
          ) : data.active_courses.length || data.practices.length ? (
            <div className="me-empty"><p>Сейчас нет начатого урока. Выберите следующий шаг на карте.</p><AppLink className="button" to="/map">Открыть карту навыков →</AppLink></div>
          ) : (
            <div className="me-empty"><h2>Здесь будет ваш прогресс</h2><p>Откройте первый урок — курс, прогресс и сохранённые работы появятся на этой странице.</p><AppLink className="button" to="/map">Выбрать урок на карте →</AppLink></div>
          )}

          <section className="me-section" id="practice" aria-labelledby="practice-title">
            <h2 id="practice-title">Мои работы{data.practices.length > 0 && <span>{data.practices.length}</span>}</h2>
            {data.practices.length ? data.practices.map(p => (
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
            )) : <p className="me-note">Сохраните практику в уроке — она появится здесь, и к ней можно будет вернуться с любого устройства.</p>}
          </section>

          <section className="me-section" aria-labelledby="active-learning">
            <h2 id="active-learning">Курсы в работе{data.active_courses.length > 0 && <span>{data.active_courses.length}</span>}</h2>
            {data.active_courses.length
              ? data.active_courses.map(course => <CourseRow key={course.id} course={course} entitlement={user.entitlement} />)
              : <p className="me-note">{data.practices.length ? 'Сохранённые работы — выше. Курс появится здесь, когда вы пройдёте урок.' : 'Пока нет курсов в работе. Откройте интересующий урок — здесь появится ваш прогресс.'}</p>}
          </section>

          {data.completed_courses.length > 0 && (
            <section className="me-section" aria-labelledby="completed-learning">
              <h2 id="completed-learning">Завершённые курсы<span>{data.completed_courses.length}</span></h2>
              {data.completed_courses.map(course => <CourseRow key={course.id} course={course} entitlement={user.entitlement} />)}
            </section>
          )}
        </div>

        <aside className="me-side">
          {data.ranks.length > 0 && <RanksPanel ranks={data.ranks} />}
          <section className="me-panel" aria-labelledby="pace-title" id="plan">
            <h2 id="pace-title">План</h2>
            {next ? (
              <div className="weekly-goal">
                <p><strong>{formatDays(plan.days)} в {plan.time}</strong></p>
                <p>Следующее занятие — {formatSession(next)}.</p>
                <p className="small">За последние 7 дней: {data.weekly} из {plan.days.length} {plural(plan.days.length, 'занятия', 'занятий', 'занятий')}.</p>
                <progress aria-label="Занятия за неделю" value={Math.min(data.weekly, plan.days.length)} max={plan.days.length} />
                <CalendarLinks plan={plan} />
                <AppLink to="/preferences#plan">Изменить план →</AppLink>
              </div>
            ) : (
            <div className="weekly-goal">
              <p>Выберите дни занятий — добавим их в ваш календарь, чтобы возвращаться было проще.</p>
              <AppLink className="button secondary" to="/preferences#plan">Выбрать дни →</AppLink>
              {user.weekly_goal ? (
                <>
                  <p><strong>Недельная цель: {data.weekly} из {user.weekly_goal}</strong></p>
                  <progress aria-label="Недельная цель" value={Math.min(data.weekly, user.weekly_goal)} max={user.weekly_goal} />
                  {data.weekly >= user.weekly_goal && <p>Цель достигнута. Продолжайте в удобном темпе.</p>}
                </>
              ) : <p><strong>Недельная цель на паузе.</strong> Возвращайтесь, когда удобно.</p>}
              <p className="small">Пройдено за последние 7 дней: {data.weekly} {plural(data.weekly, 'урок', 'урока', 'уроков')}.</p>
            </div>
            )}
          </section>
          <Club data={data} />
          <Connections initial={data.connections} />
          {(data.favourites.length > 0 || data.material_favourites.length > 0) && (
            <section className="me-panel" aria-labelledby="fav-title">
              <h2 id="fav-title">Избранное</h2>
              {data.material_favourites.map(m => <p key={m.id}><AppLink to={`/materials/${m.id}`}>{m.title}</AppLink></p>)}
              {data.favourites.map(c => <p key={c.id}><AppLink to={`/courses/${c.id}`}>{c.title}</AppLink></p>)}
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}
