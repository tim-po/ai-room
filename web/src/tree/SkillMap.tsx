import {useEffect, useRef, useState} from 'react';
import {ReturnBriefing, stepLabel} from '../components/Briefing';
import {MapCelebration} from '../components/Ranks';
import {AppLink} from '../Shell';
import type {HomeData} from '../types';
// The canvas engine is imperative DOM code (layout, pan/zoom, level-of-detail tweens); React owns
// the surrounding markup and mounts it once per data set.
import {mountTree} from './engine.js';

const LEGEND: [string, string][] = [['done', 'Пройден'], ['progress', 'В процессе'], ['open', 'Доступен'], ['locked', 'Урок клуба'], ['coming', 'Скоро']];

export default function SkillMap({data}: {data: HomeData}) {
  const root = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!root.current) return;
    return mountTree(root.current, data.tree);
  }, [data]);

  const unfinished = data.continuation.unfinished;
  const briefing = data.briefing;
  // After a break the strip opens into a briefing over the map; hiding it lasts for this visit.
  const hideKey = `briefing-hidden:${briefing?.lesson_id}`;
  const [briefingHidden, setBriefingHidden] = useState(() => { try { return sessionStorage.getItem(hideKey) === '1'; } catch { return false; } });
  // A new rank or control point since the last visit is celebrated once, before the briefing.
  const [celebrating, setCelebrating] = useState(() => (data.achievements ?? []).length > 0);
  const showBriefing = !!briefing?.returning && !briefingHidden && !celebrating;
  const step = stepLabel(briefing);
  const resume = unfinished
    ? {label: unfinished.status === 'draft' ? 'Черновик ждёт вас' : 'Вы остановились на уроке', title: unfinished.title + (step ? ` · ${step}` : ''),
       url: briefing?.url ?? unfinished.url + (unfinished.status === 'draft' ? '#practice' : ''), action: 'Продолжить →', aria: 'Продолжить обучение'}
    : data.next
      ? {label: 'Следующий шаг', title: data.next.title, url: data.next.url, action: 'Открыть урок →', aria: 'Следующий шаг'}
      : null;

  return (
    <section className="tree" ref={root} aria-labelledby="tree-title">
      <div className="tree-bar-top">
        <div><h1 id="tree-title">Карта навыков</h1></div>
        <div className="tree-tools">
          <label><span className="visually-hidden">Найти урок или курс</span><input type="search" placeholder="Найти урок или курс" data-tree-search /></label>
          <span className="tree-zoom">
            <button type="button" data-zoom-out aria-label="Уменьшить">−</button>
            <span data-zoom-level aria-live="off">100%</span>
            <button type="button" data-zoom-in aria-label="Увеличить">+</button>
          </span>
          <button type="button" data-fit>Показать всё</button>
          <button type="button" data-here>Моё место</button>
        </div>
      </div>
      {resume && (
        <section className="resume-strip" aria-label={resume.aria}>
          <div><p>{resume.label}</p><h2>{resume.title}</h2></div>
          <AppLink className="button" to={resume.url}>{resume.action}</AppLink>
        </section>
      )}
      <p className="tree-status" role="status" data-tree-status />
      <div className="tree-viewport"><div className="tree-canvas" /></div>
      {celebrating && <MapCelebration items={data.achievements} onClose={() => setCelebrating(false)} />}
      {showBriefing && (
        <ReturnBriefing briefing={briefing!} className="map-briefing"
          onHide={() => { setBriefingHidden(true); try { sessionStorage.setItem(hideKey, '1'); } catch { /* per-visit nicety only */ } }} />
      )}
      <ul className="tree-legend" aria-label="Обозначения">
        {LEGEND.map(([state, label]) => (
          <li key={state}><span className={`tree-lesson is-${state}`}><span className="tree-dot" /></span>{label}</li>
        ))}
        <li><span className="legend-flag"><svg viewBox="0 0 16 16"><path d="M4.5 14V2.5M4.5 3h7.5l-2 3 2 3H4.5" /></svg></span>Контрольная точка</li>
      </ul>
    </section>
  );
}
