import {useLoaderData, type LoaderFunctionArgs} from 'react-router';
import {getJson} from '../api';
import {humanTime, plural} from '../format';
import {useTitle} from '../useTitle';
import type {Analytics as Data} from './types';
import {Bars, Empty, PageHead, Stat, shortDate} from './ui';

export const analyticsLoader = ({request}: LoaderFunctionArgs) => getJson<Data>('/api/admin/analytics', request.signal);

const percent = (part: number, whole: number) => (whole ? `${Math.round((part / whole) * 100)}%` : '—');
const duration = (seconds: number | null) => {
  if (seconds === null) return '—';
  if (seconds < 3600) return `${Math.max(1, Math.round(seconds / 60))} мин`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)} ч`;
  return `${Math.round(seconds / 86400)} дн`;
};

const EVENT_LABEL: Record<string, string> = {
  lesson_started: 'Начали урок', lesson_completed: 'Завершили урок', practice_submitted: 'Сдали практику', practice_saved: 'Сохранили практику',
  course_started: 'Начали курс', section_reached: 'Дошли до раздела', meaningful_return: 'Вернулись к учёбе', help_requested: 'Задали вопрос',
  onboarding_completed: 'Прошли знакомство', plan_calendar: 'Добавили план в календарь', continue_opened: 'Пришли по «продолжить»',
  session_connected: 'Подключили ассистента',
};

export default function Analytics() {
  const data = useLoaderData() as Data;
  useTitle('Аналитика · Админка');
  const {loop} = data;
  const active = data.modules.filter(m => m.starters > 0);
  const idle = data.modules.length - active.length;
  return (
    <>
      <PageHead eyebrow="Люди" title="Аналитика">
        Только ученики: редакторы и администраторы в цифры не попадают. Обновлено {humanTime(data.generated_at.replace('T', ' '))}.
      </PageHead>
      <div className="adm-stats">
        <Stat value={data.learners} label="учеников всего" />
        <Stat value={percent(loop.activated, loop.starters)} label="активация" hint={`${loop.activated} из ${loop.starters}: учились в первые сутки`} tone="accent" />
        {loop.returns.map(r => (
          <Stat key={r.days} value={percent(r.returned, r.cohort)} label={`вернулись за ${r.days} ${r.days === 1 ? 'день' : 'дней'}`} hint={r.cohort ? `${r.returned} из ${r.cohort}` : 'пока некого считать'} />
        ))}
        <Stat value={duration(data.median)} label="до первого результата" hint={`медиана по ${data.result_count}`} />
      </div>
      <div className="adm-columns">
        <div>
          <section className="adm-card">
            <header><h2>Учились по неделям</h2><span className="adm-muted">последняя неделя ещё идёт</span></header>
            <Bars values={loop.weekly.map(w => w.learners)} labels={loop.weekly.map(w => 'с ' + shortDate(w.start))} height={110} />
            <div className="adm-bars-axis">{loop.weekly.map(w => <span key={w.start}>{shortDate(w.start)}{w.partial ? '*' : ''}</span>)}</div>
          </section>
          <section className="adm-card">
            <header><h2>Модули: начали → закончили</h2></header>
            {active.length ? (
              <ul className="adm-funnel">
                {active.map(m => (
                  <li key={m.id}>
                    <span className="adm-title-cell"><strong>{m.title}</strong><small>{m.course_title}</small></span>
                    <span className="adm-meter is-two" aria-label={`${m.finishers} из ${m.starters}`}>
                      <span style={{width: `${m.starters ? (m.finishers / m.starters) * 100 : 0}%`}} />
                    </span>
                    <small>{m.finishers} / {m.starters}</small>
                  </li>
                ))}
              </ul>
            ) : <Empty>Пока никто не начал ни одного модуля.</Empty>}
            {idle > 0 && <p className="adm-hint">Ещё {idle} {plural(idle, 'модуль', 'модуля', 'модулей')} без учеников.</p>}
          </section>
        </div>
        <div>
          <section className="adm-card">
            <header><h2>Удержание неделя к неделе</h2></header>
            <ul className="adm-rank is-plain">
              {data.weeks.map(w => (
                <li key={w.start}><span>{shortDate(w.start)} → {shortDate(w.following)}</span><strong>{percent(w.numerator, w.denominator)}</strong>
                  <small>{w.numerator} из {w.denominator}</small></li>
              ))}
            </ul>
          </section>
          <section className="adm-card">
            <header><h2>Чем пользуются</h2></header>
            <ul className="adm-rank is-plain">
              {loop.features.map(f => <li key={f.label}><span>{f.label}</span><strong>{f.learners}</strong></li>)}
            </ul>
            {data.events.length > 0 && <>
              <header className="adm-subhead"><h2>События</h2></header>
              <ul className="adm-rank is-plain">
                {data.events.map(e => <li key={e.name}><span>{EVENT_LABEL[e.name] ?? e.name}</span><strong>{e.n}</strong></li>)}
              </ul>
            </>}
          </section>
        </div>
      </div>
    </>
  );
}
