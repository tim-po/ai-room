import {useEffect, useRef} from 'react';
import {postJson} from '../api';
import {plural} from '../format';
import {AppLink} from '../links';
import type {Achievement, Standing} from '../types';

// Ranks and control points (club/ranks.py): a medal per rank, the moment a new one is earned (on the
// map and in the finish dialog), and the list in Профиль. Each new one is celebrated once.

/** A medal: copper Новичок, silver Практик, gold Профи, amber Мастер (map.css .is-level-N). */
export function Medal({level, flag = false}: {level: number; flag?: boolean}) {
  return (
    <svg className={`medal is-level-${level}`} viewBox="0 0 64 64" aria-hidden="true">
      <path className="ribbon" d="M22 36 14 60l9-4 5 7 6-22M42 36l8 24-9-4-5 7-6-22" />
      <circle className="ring" cx="32" cy="27" r="22" />
      <circle className="face" cx="32" cy="27" r="16" />
      {flag
        ? <path className="star" d="M27 37V17m0 1h12l-3 5 3 5H27" strokeWidth="2.4" strokeLinejoin="round" stroke="var(--medal)" />
        : <path className="star" d="m32 15 3.5 7.4 8 1.1-5.8 5.6 1.4 8L32 33.3 24.9 37l1.4-8-5.8-5.6 8-1.1Z" />}
      {level === 4 && <path className="star" d="M24 7l4 4 4-6 4 6 4-4-2 7H26Z" />}
    </svg>
  );
}

export function AchievementView({item}: {item: Achievement}) {
  if (item.kind === 'rank') {
    return (
      <div className="achievement is-rank">
        <Medal level={item.level} />
        <div>
          <p className="achievement-kicker">{item.level === 4 ? 'Высшее звание курса' : 'Новое звание'}</p>
          <p className="achievement-title">{item.title}</p>
          <p className="achievement-next">{item.next}</p>
        </div>
      </div>
    );
  }
  return (
    <div className="achievement is-checkpoint">
      <Medal level={3} flag />
      <div>
        <p className="achievement-kicker">Контрольная точка {item.number} из {item.of}</p>
        <p className="achievement-title">{item.module}</p>
        <p className="achievement-next">{item.course_title}</p>
      </div>
    </div>
  );
}

export const markSeen = (items: Achievement[]) => {
  if (items.length) postJson('/api/app/achievements/seen', {ids: items.map(i => i.id)}).catch(() => { /* shown again next time */ });
};

/** On the map: what was earned since the last visit; ranks first. */
export function MapCelebration({items, onClose}: {items: Achievement[]; onClose: () => void}) {
  const button = useRef<HTMLButtonElement>(null);
  useEffect(() => { button.current?.focus({preventScroll: true}); }, []);
  const ordered = [...items].sort((a, b) => (a.kind === b.kind ? 0 : a.kind === 'rank' ? -1 : 1)).slice(0, 3);
  function close() { markSeen(items); onClose(); }
  return (
    <section className="map-celebrate" role="dialog" aria-labelledby="celebrate-title" onKeyDown={e => { if (e.key === 'Escape') close(); }}>
      <h2 id="celebrate-title" className="visually-hidden">Новые достижения</h2>
      {ordered.map(item => <AchievementView key={item.id} item={item} />)}
      {items.length > ordered.length && <p className="small">И ещё {items.length - ordered.length} — в профиле.</p>}
      <div className="map-celebrate-actions">
        <button ref={button} type="button" className="button" onClick={close}>Отлично</button>
        <AppLink className="button secondary" to="/profile#ranks" onClick={() => markSeen(items)}>Мои звания</AppLink>
      </div>
    </section>
  );
}

/** Профиль: the rank on each course started, with the way to the next one. */
export function RanksPanel({ranks}: {ranks: (Standing & {course: string; course_title: string})[]}) {
  return (
    <section className="me-panel" id="ranks" aria-labelledby="ranks-title">
      <h2 id="ranks-title">Звания</h2>
      {ranks.length ? (
        <ul className="rank-list">
          {ranks.map(r => (
            <li key={r.course}>
              <Medal level={r.level} />
              <div>
                <strong>{r.title ?? r.course_title}</strong>
                <span>{r.reached} из {r.checkpoints} {plural(r.checkpoints, 'контрольной точки', 'контрольных точек', 'контрольных точек')} · {r.next}</span>
                <span className="rank-meter" aria-hidden="true"><span style={{width: `${r.checkpoints ? (100 * r.reached) / r.checkpoints : 0}%`}} /></span>
              </div>
            </li>
          ))}
        </ul>
      ) : <p className="me-note">Пройдите первый урок курса — появится звание. Каждый модуль — контрольная точка на пути к «Мастеру».</p>}
    </section>
  );
}
