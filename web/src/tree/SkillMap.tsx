import {useEffect, useRef, useState} from 'react';
import {ReturnBriefing} from '../components/Briefing';
import {MapCelebration} from '../components/Ranks';
import type {HomeData} from '../types';
// On a wide screen the map is a round tree on a pan-and-zoom canvas: imperative DOM code (engine.js)
// that React mounts once per data set. On a phone it is a trail you scroll down (TrailMap.tsx).
import {mountTree} from './engine.js';
import TrailMap from './TrailMap';

const PHONE = '(max-width: 700px)';

function usePhone() {
  const [phone, setPhone] = useState(() => window.matchMedia(PHONE).matches);
  useEffect(() => {
    const query = window.matchMedia(PHONE), update = () => setPhone(query.matches);
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);
  return phone;
}

const LEGEND: [string, string][] = [['done', 'Пройден'], ['progress', 'В процессе'], ['open', 'Доступен'], ['locked', 'Урок клуба'], ['coming', 'Скоро']];

export default function SkillMap({data}: {data: HomeData}) {
  const root = useRef<HTMLElement>(null);
  const phone = usePhone();
  useEffect(() => {
    if (!root.current || phone) return;
    return mountTree(root.current, data.tree);
  }, [data, phone]);

  const briefing = data.briefing;
  // After a break a briefing opens over the map; hiding it lasts for this visit.
  const hideKey = `briefing-hidden:${briefing?.lesson_id}`;
  const [briefingHidden, setBriefingHidden] = useState(() => { try { return sessionStorage.getItem(hideKey) === '1'; } catch { return false; } });
  // A new rank (a milestone reached) since the last visit is celebrated once, before the briefing.
  const [celebrating, setCelebrating] = useState(() => (data.achievements ?? []).length > 0);
  const showBriefing = !!briefing?.returning && !briefingHidden && !celebrating;

  const overlays = (
    <>
      {celebrating && <MapCelebration items={data.achievements} onClose={() => setCelebrating(false)} />}
      {showBriefing && (
        <ReturnBriefing briefing={briefing!} className="map-briefing"
          onHide={() => { setBriefingHidden(true); try { sessionStorage.setItem(hideKey, '1'); } catch { /* per-visit nicety only */ } }} />
      )}
    </>
  );
  if (phone) {
    return (
      <section className="tree is-trail" aria-labelledby="tree-title">
        <div className="tree-bar-top"><div><h1 id="tree-title">Карта навыков</h1></div></div>
        {overlays}
        <TrailMap topics={data.tree.topics} />
      </section>
    );
  }
  return (
    <section className="tree" ref={root} aria-labelledby="tree-title">
      <div className="tree-bar-top">
        <div><h1 id="tree-title">Карта навыков</h1></div>
        <div className="tree-tools">
          <span className="tree-zoom">
            <button type="button" data-zoom-out aria-label="Уменьшить">−</button>
            <span data-zoom-level aria-live="off">100%</span>
            <button type="button" data-zoom-in aria-label="Увеличить">+</button>
          </span>
          <button type="button" data-fit>Показать всё</button>
          <button type="button" data-here>Моё место</button>
        </div>
      </div>
      <div className="tree-viewport"><div className="tree-canvas" /></div>
      {overlays}
      <ul className="tree-legend" aria-label="Обозначения">
        {LEGEND.map(([state, label]) => (
          <li key={state}><span className={`tree-lesson is-${state}`}><span className="tree-dot" /></span>{label}</li>
        ))}
        <li><span className="legend-milestone" aria-hidden="true"><svg viewBox="0 0 16 16"><path d="M4.5 14V2.5M4.5 3h7.5l-2 3 2 3H4.5" /></svg></span>Веха — новое звание</li>
      </ul>
    </section>
  );
}
