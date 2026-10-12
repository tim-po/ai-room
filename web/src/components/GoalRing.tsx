import {useEffect, useRef, useState} from 'react';
import type {JourneyGoalOption} from '../journey';

// Goals as a ring of cards: the one in front is full size, the others turn away around a circle on either
// side (smaller, further back, rotated). Arrows, a swipe, the arrow keys or a click on a side card turn the
// ring; a click on the front card (or its button) chooses it.

export default function GoalRing({goals, chosen, max, onToggle}: {
  goals: JourneyGoalOption[]; chosen: string[]; max: number; onToggle: (id: string) => void;
}) {
  const n = goals.length;
  const [active, setActive] = useState(0);
  const stage = useRef<HTMLDivElement>(null);
  const [radius, setRadius] = useState(420);
  useEffect(() => {
    const node = stage.current;
    if (!node || !('ResizeObserver' in window)) return;
    const observer = new ResizeObserver(() => setRadius(Math.min(440, node.clientWidth * 0.5)));
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  const turn = (step: number) => setActive(a => (a + step + n) % n);
  // A horizontal swipe turns the ring by one card (captured once it's clearly sideways, so the page doesn't pan
  // and the card under the finger isn't clicked).
  const swipe = useRef<{x: number; y: number; id: number; moved: boolean} | null>(null);
  const swiped = useRef(false);
  const goal = goals[active];
  const on = chosen.includes(goal.id);
  const full = !on && chosen.length >= max;

  return (
    <div className="goal-ring">
      <div ref={stage} className="goal-ring-stage" tabIndex={0} role="group" aria-roledescription="карусель" aria-label="Цели"
        onKeyDown={e => {
          if (e.key === 'ArrowRight') { e.preventDefault(); turn(1); }
          if (e.key === 'ArrowLeft') { e.preventDefault(); turn(-1); }
          if ((e.key === 'Enter' || e.key === ' ') && e.target === e.currentTarget) { e.preventDefault(); if (!full) onToggle(goal.id); }
        }}
        onPointerDown={e => { swipe.current = {x: e.clientX, y: e.clientY, id: e.pointerId, moved: false}; swiped.current = false; }}
        onPointerMove={e => {
          const s = swipe.current;
          if (!s || s.id !== e.pointerId || s.moved) return;
          const dx = e.clientX - s.x, dy = e.clientY - s.y;
          if (Math.abs(dx) > 10 && Math.abs(dx) > Math.abs(dy)) { s.moved = true; e.currentTarget.setPointerCapture(e.pointerId); }
        }}
        onPointerUp={e => {
          const s = swipe.current; swipe.current = null;
          if (!s || !s.moved) return;
          swiped.current = true;
          const dx = e.clientX - s.x;
          if (Math.abs(dx) > 30) turn(dx < 0 ? 1 : -1);
        }}
        onPointerCancel={() => { swipe.current = null; }}
        onClickCapture={e => { if (swiped.current) { e.preventDefault(); e.stopPropagation(); swiped.current = false; } }}>
        {goals.map((item, i) => {
          // the shortest way round the ring from the front card
          let d = (i - active + n) % n;
          if (d > n / 2) d -= n;
          // round a circle seen from outside: side cards slide out and back, turned to face the middle
          const angle = d * 30;
          const rad = angle * Math.PI / 180;
          const x = Math.sin(rad) * radius * 1.25, z = (Math.cos(rad) - 1) * radius - Math.abs(d) * 40;
          const picked = chosen.includes(item.id);
          return (
            <button key={item.id} type="button" tabIndex={d === 0 ? 0 : -1} aria-hidden={Math.abs(d) > 2}
              className={'goal-ring-card' + (d === 0 ? ' is-front' : '') + (picked ? ' is-on' : '')}
              style={{transform: `translateX(-50%) translate3d(${x}px,0,${z}px) rotateY(${-angle}deg) scale(${1 - Math.min(2, Math.abs(d)) * 0.06})`, zIndex: 10 - Math.abs(d),
                opacity: Math.abs(d) > 2.5 ? 0 : 1 - Math.abs(d) * 0.18, pointerEvents: Math.abs(d) > 2.5 ? 'none' : undefined}}
              onClick={() => (d === 0 ? (picked || chosen.length < max) && onToggle(item.id) : setActive(i))}>
              {picked && <i aria-hidden="true">{chosen.indexOf(item.id) + 1}</i>}
              <strong>{item.title}</strong>
              <span>{item.text}</span>
              {d === 0 && <em>{picked ? 'Выбрано ✓' : chosen.length >= max ? `Уже ${max} цели` : 'Выбрать'}</em>}
            </button>
          );
        })}
      </div>
      <div className="goal-ring-nav">
        <button type="button" onClick={() => turn(-1)} aria-label="Предыдущая цель">←</button>
        <span className="goal-ring-dots" aria-hidden="true">
          {goals.map((item, i) => <i key={item.id} className={(i === active ? 'is-active' : '') + (chosen.includes(item.id) ? ' is-on' : '')} />)}
        </span>
        <button type="button" onClick={() => turn(1)} aria-label="Следующая цель">→</button>
      </div>
      <div className="goal-ring-chosen" aria-live="polite">
        {chosen.length ? chosen.map((id, i) => {
          const item = goals.find(g => g.id === id);
          return item && (
            <button key={id} type="button" onClick={() => onToggle(id)} aria-label={`Убрать цель: ${item.title}`}>
              <b>{i + 1}</b>{item.title}<span aria-hidden="true">×</span>
            </button>
          );
        }) : <span className="small">Листай цели и выбери до {max}</span>}
      </div>
    </div>
  );
}
