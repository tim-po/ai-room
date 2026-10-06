import {useLoaderData} from 'react-router';
import {getJson} from '../api';
import {humanTime, plural} from '../format';
import {AppLink} from '../Shell';
import type {CourseProgress, ProfileData} from '../types';
import {useTitle} from '../useTitle';

export const profileLoader = ({request}: {request: Request}) => getJson<ProfileData>('/api/app/profile', request.signal);

const ACCESS_LABEL: Record<string, string> = {free: 'Бесплатный доступ', member: 'Участник клуба', revoked: 'Доступ приостановлен', expired: 'Доступ закончился'};
const ACCESS_TEXT: Record<string, string> = {
  free: 'Бесплатные уроки открыты.', member: 'Уроки клуба доступны.',
  revoked: 'Доступ участника отозван. Бесплатные уроки остаются доступны.', expired: 'Срок доступа истёк. Бесплатные уроки остаются доступны.',
};

function CourseRow({course, entitlement}: {course: CourseProgress; entitlement: string}) {
  const remaining = course.done < course.total;
  return (
    <div className={'me-course' + (remaining ? '' : ' is-complete')}>
      <div className="me-course-main">
        <a className="me-course-title" href={`/courses/${course.id}`}>{course.title}</a>
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
          ? <a className="button secondary" href={`/membership?next=/lessons/${course.next_locked.id}`}>Открыть доступ</a>
          : <a className="button secondary" href={`/courses/${course.id}`}>Открыть курс</a>)}
    </div>
  );
}

export default function Profile() {
  const data = useLoaderData() as ProfileData;
  useTitle('Моё обучение');
  const {user} = data;
  const unfinished = data.continuation.unfinished;
  return (
    <div className="me">
      <header className="me-head">
        <div><p className="eyebrow">Моё обучение</p><h1>{user.name}</h1></div>
        <p className="me-head-links"><a href="/onboarding">Интересы и темп</a><a href="/membership">{ACCESS_LABEL[user.entitlement]}</a></p>
      </header>
      <div className="me-grid">
        <div className="me-main">
          {unfinished ? (
            <AppLink className="me-continue" to={unfinished.url + (unfinished.status === 'draft' ? '#practice' : '')} aria-label={`Продолжить: ${unfinished.title}`}>
              <span className="me-continue-label">{unfinished.status === 'draft' ? 'Черновик ждёт вас' : 'Продолжить урок'}</span>
              <strong>{unfinished.title}</strong>
              <span className="me-continue-action">Продолжить →</span>
            </AppLink>
          ) : data.active_courses.length || data.practices.length ? (
            <div className="me-empty"><p>Сейчас нет начатого урока. Выберите следующий шаг на карте.</p><AppLink className="button" to="/">Открыть карту навыков →</AppLink></div>
          ) : (
            <div className="me-empty"><h2>Здесь будет ваш прогресс</h2><p>Откройте первый урок — курс, прогресс и сохранённые работы появятся на этой странице.</p><AppLink className="button" to="/">Выбрать урок на карте →</AppLink></div>
          )}

          <section className="me-section" id="practice" aria-labelledby="practice-title">
            <h2 id="practice-title">Мои работы{data.practices.length > 0 && <span>{data.practices.length}</span>}</h2>
            {data.practices.length ? data.practices.map(p => (
              <article key={p.lesson_id} className="me-work">
                <div className="me-work-head">
                  <AppLink to={`/lessons/${p.lesson_id}#practice`}>{p.title}</AppLink>
                  <span className={'me-chip ' + (p.status === 'draft' ? 'is-draft' : 'is-saved')}>{p.status === 'draft' ? 'Черновик' : 'Результат'}</span>
                </div>
                <p className="preserve">{p.body.length > 280 ? p.body.slice(0, 277) + '…' : p.body}</p>
                <p className="me-work-date">Сохранено {humanTime(p.updated_at)}</p>
              </article>
            )) : <p className="me-note">Сохраните практику в уроке — она появится здесь, и к ней можно будет вернуться с любого устройства.</p>}
          </section>

          <section className="me-section" aria-labelledby="active-learning">
            <h2 id="active-learning">Курсы в работе{data.active_courses.length > 0 && <span>{data.active_courses.length}</span>}</h2>
            {data.active_courses.length
              ? data.active_courses.map(course => <CourseRow key={course.id} course={course} entitlement={user.entitlement} />)
              : <p className="me-note">Пока нет курсов в работе. Откройте интересующий урок — здесь появится ваш прогресс.</p>}
          </section>

          <section className="me-section" aria-labelledby="completed-learning">
            <h2 id="completed-learning">Завершённые курсы{data.completed_courses.length > 0 && <span>{data.completed_courses.length}</span>}</h2>
            {data.completed_courses.length
              ? data.completed_courses.map(course => <CourseRow key={course.id} course={course} entitlement={user.entitlement} />)
              : <p className="me-note">Здесь появятся курсы, которые вы завершите.</p>}
          </section>
        </div>

        <aside className="me-side">
          <section className="me-panel" aria-labelledby="pace-title">
            <h2 id="pace-title">Темп</h2>
            <div className="weekly-goal">
              {user.weekly_goal ? (
                <>
                  <p><strong>Недельная цель: {data.weekly} из {user.weekly_goal}</strong></p>
                  <progress aria-label="Недельная цель" value={Math.min(data.weekly, user.weekly_goal)} max={user.weekly_goal} />
                  {data.weekly >= user.weekly_goal && <p>Цель достигнута. Продолжайте в удобном темпе.</p>}
                </>
              ) : <p><strong>Недельная цель на паузе.</strong> Возвращайтесь, когда удобно.</p>}
              <p className="small">Пройдено за последние 7 дней: {data.weekly} {plural(data.weekly, 'урок', 'урока', 'уроков')}.</p>
              <a href="/preferences">Изменить цель и темп →</a>
            </div>
          </section>
          <section className="me-panel" aria-labelledby="access-title">
            <h2 id="access-title">Доступ</h2>
            <p>{ACCESS_TEXT[user.entitlement]}</p>
            <p className="me-note">{user.email}</p>
            {user.entitlement !== 'member' ? <a href="/membership">Подробнее о клубе →</a> : <a href="/help">Вопрос по доступу →</a>}
          </section>
          {(data.favourites.length > 0 || data.material_favourites.length > 0) && (
            <section className="me-panel" aria-labelledby="fav-title">
              <h2 id="fav-title">Избранное</h2>
              {data.material_favourites.map(m => <p key={m.id}><a href={`/materials/${m.id}`}>{m.title}</a></p>)}
              {data.favourites.map(c => <p key={c.id}><a href={`/courses/${c.id}`}>{c.title}</a></p>)}
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}
