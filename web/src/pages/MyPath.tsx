import {useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState} from 'react';
import {useLoaderData, type LoaderFunctionArgs} from 'react-router';
import {ApiError, bootstrap, getJson} from '../api';
import PathPlan, {PlanSwiper, PlanTimeline, dateIn, planOf} from '../components/PathPlan';
import {AppLink} from '../Shell';
import SkillMap from '../tree/SkillMap';
import type {JourneyData, JourneyPath} from '../journey';
import type {HomeData} from '../types';
import {useTitle} from '../useTitle';

// «Мой путь»: the skill map is the whole page, the learning plan a panel floating on its right that folds
// into a slim timeline. The goals sit in the plan and switch their paths on the map on and off. Time is the
// plan's scroll (or the timeline, folded): the lesson being read sets the date; the map frames the branch
// of that lesson's course and colours what will be done by then.

// The map and the path are one page: /path for people signed in, /map (the same page) for visitors and old links.
// Without goals yet the map is plain and the panel invites to choose them (or to sign in).
export const myPathLoader = async ({request}: LoaderFunctionArgs) => {
  const [home, journey] = await Promise.all([getJson<HomeData>('/api/app/home', request.signal),
    bootstrap.user ? getJson<JourneyData>('/api/app/journey', request.signal) : Promise.resolve(null)]);
  return {home, journey};
};

/** Each goal's progress once the first `count` lessons are done (as club/paths.py progress). */
/** How far (px) the folded card must be pulled up to open the plan when let go. */
const PULL_TO_OPEN = 90;

function progressAfter(path: JourneyPath, count: number) {
  const points = {...path.start};
  for (const lesson of path.lessons.slice(0, count)) for (const [skill, gain] of Object.entries(lesson.gains)) points[skill] = Math.min(100, (points[skill] ?? 0) + gain);
  const goals: Record<string, number> = {};
  for (const goal of path.goals) {
    let need = 0, got = 0;
    for (const [skill, target] of Object.entries(goal.targets)) {
      const from = Math.min(path.start[skill] ?? 0, target);
      need += target - from;
      got += Math.max(0, Math.min(points[skill] ?? 0, target) - from);
    }
    goals[goal.id] = need ? got / need : 1;
  }
  return goals;
}

// Several goals' colours in equal parts: a striped band (left to right) and a split ring (around a dot).
const parts = (cs: string[]) => cs.map((c, i) => `${c} ${(100 * i / cs.length).toFixed(2)}% ${(100 * (i + 1) / cs.length).toFixed(2)}%`).join(',');
const band = (cs: string[]) => `linear-gradient(90deg,${parts(cs)})`;
const pie = (cs: string[]) => `conic-gradient(${parts(cs)})`;

export default function MyPath() {
  const {home, journey} = useLoaderData() as {home: HomeData; journey: JourneyData | null};
  const path = journey?.path ?? null;
  useTitle(path ? 'Мой путь' : 'Карта навыков');
  const [hidden, setHidden] = useState<string[]>([]);
  const [paywall, setPaywall] = useState('');
  const [open, setOpen] = useState(() => !window.matchMedia('(max-width: 800px)').matches);
  const plan = useMemo(() => (path ? planOf(path) : null), [path]);

  // The page sits right under the header and fills the window.
  const page = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const place = () => {
      const header = document.querySelector('.club-header');
      page.current?.style.setProperty('--top', `${header ? header.getBoundingClientRect().bottom : 0}px`);
    };
    place();
    window.addEventListener('resize', place);
    return () => window.removeEventListener('resize', place);
  }, []);

  // Time is the plan's scroll: the last lesson whose row has passed a line 40% down the panel.
  const scroller = useRef<HTMLDivElement>(null);
  const [reading, setReading] = useState(-1);
  // Phones: how far the folded card is being pulled up.
  const [pull, setPull] = useState(0);

  const [guide, setGuide] = useState<string | null>(null);
  useEffect(() => {
    const box = scroller.current;
    if (!box || !open) return;
    let frame = 0;
    const measure = () => {
      frame = 0;
      const line = box.getBoundingClientRect().top + box.clientHeight * 0.4;
      let index = -1;
      // a guide row past the line (after its module's lessons) puts the map on that guide's island
      let guideAt: string | null = null;
      box.querySelectorAll<HTMLElement>('[data-lesson],[data-guide]').forEach(el => {
        if (el.getBoundingClientRect().top > line) return;
        if (el.dataset.guide) guideAt = el.dataset.guide; else { index = Number(el.dataset.lesson); guideAt = null; }
      });
      setReading(index);
      setGuide(guideAt);
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(measure); };
    box.addEventListener('scroll', schedule, {passive: true});
    window.addEventListener('resize', schedule);
    return () => { box.removeEventListener('scroll', schedule); window.removeEventListener('resize', schedule); if (frame) cancelAnimationFrame(frame); };
  }, [open, plan]);
  // Unfolding after moving along the timeline: the plan opens at that lesson.
  function fold() {
    setOpen(false);
    requestAnimationFrame(() => page.current?.querySelector<HTMLButtonElement>(window.innerWidth <= 800 ? '.plan-swiper-open' : '.plan-timeline-open')?.focus());
  }
  function unfold() {
    setOpen(true);
    requestAnimationFrame(() => {
      page.current?.querySelector<HTMLButtonElement>('.my-path-fold')?.focus();
      const box = scroller.current, row = box?.querySelector<HTMLElement>(`[data-lesson="${reading}"]`);
      if (box && row) box.scrollTop += row.getBoundingClientRect().top - (box.getBoundingClientRect().top + box.clientHeight * 0.4) + 1;
    });
  }

  const item = plan && reading >= 0 ? plan.lessons[reading] : null;
  const week = item ? item.to : 0;
  const progress = useMemo(() => (path ? progressAfter(path, reading + 1) : {}), [path, reading]);
  const known = useMemo(() => {
    const set = new Set(path?.assumed.map(a => a.key) ?? []);
    home.tree.topics.forEach(t => t.courses.forEach(c => c.modules.forEach((m, i) => { if (m.state === 'done') set.add(`${c.id}:${i}`); })));
    return set;
  }, [home, path]);
  // Modules whose path lessons are all done by the lesson being read.
  const doneModules = useMemo(() => {
    const done = new Set<string>(), pending = new Set<string>();
    for (const l of plan?.lessons ?? []) (l.index <= reading ? done : pending).add(l.module);
    for (const key of pending) done.delete(key);
    return done;
  }, [plan, reading]);
  const current = item?.module ?? plan?.lessons[0]?.module ?? null;

  // Colour the map: the path per visible goal, what's probably known, what is done by the date being read,
  // and the module of the lesson being read. Shared by several goals, a module or lesson shows all their colours.
  const decorate = useCallback((root: HTMLElement) => {
    const canvas = root.querySelector('.tree-canvas');
    if (!canvas || !path) return;
    const colour = new Map(path.goals.filter(g => !hidden.includes(g.id)).map(g => [g.id, g.color]));
    const colours = new Map<string, string[]>();
    for (const goal of path.goals) if (colour.has(goal.id)) for (const key of goal.modules) colours.set(key, [...(colours.get(key) ?? []), goal.color]);
    const lessons = new Map(path.lessons.map(l => [l.key, l.goals.filter(id => colour.has(id)).map(id => colour.get(id)!)]));
    const order = new Map(path.lessons.map((l, i) => [l.key, i]));
    canvas.classList.toggle('has-path', colours.size > 0);
    let repaint = false;
    canvas.querySelectorAll<HTMLElement>('[data-module]').forEach(el => {
      const key = el.dataset.module!, on = colours.get(key);
      el.classList.toggle('on-path', !!on);
      el.classList.toggle('path-known', !on && known.has(key));
      el.classList.toggle('path-done', !!on && doneModules.has(key));
      if (el.tagName === 'path') {
        // one line per goal along the branch (the engine draws them; see engine.js lanes)
        const lanes = on?.join(' ') ?? '';
        if ((el.dataset.lanes ?? '') !== lanes) { if (lanes) el.dataset.lanes = lanes; else delete el.dataset.lanes; repaint = true; }
        el.style.setProperty('--lanes-n', String(on?.length ?? 0));
        return;
      }
      el.classList.toggle('path-here', !!on && reading >= 0 && key === current);
      el.style.setProperty('--goal-band', on ? band(on) : '');
      const head = el.querySelector('h3');
      if (head && on && on.length > 1) head.dataset.goals = `${on.length} цели`; else delete head?.dataset.goals;
    });
    canvas.querySelectorAll<HTMLElement>('.tree-lesson[data-key]').forEach(row => {
      const on = lessons.get(row.dataset.key!);
      row.classList.toggle('on-path', !!on?.length);
      // the lesson being read in the plan (or on the timeline), and those done by then
      const at = order.get(row.dataset.key!);
      row.classList.toggle('path-now', !!on?.length && at === reading);
      row.classList.toggle('path-passed', !!on?.length && at != null && at < reading);
      row.style.setProperty('--pie', on?.length ? pie(on) : '');
    });
    canvas.querySelectorAll<HTMLElement>('.tree-island').forEach(isle => {
      const on = (isle.dataset.goals ?? '').split(' ').filter(id => colour.has(id)).map(id => colour.get(id)!);
      isle.classList.toggle('is-dim', !on.length);
      if (on.length) isle.style.setProperty('--goal-band', band(on)); else isle.style.removeProperty('--goal-band');
    });
    if (repaint) root.dispatchEvent(new Event('tree:repaint'));
  }, [path, hidden, known, doneModules, current, reading]);

  // The camera follows the plan, module by module, close in.
  const mapRoot = useRef<HTMLDivElement>(null);
  const shownModule = useRef(current);
  // A guide in the plan (scrolled to or pointed at): the map frames its island; leaving it, back to the module.
  const shownGuide = useRef<string | null>(null);
  useEffect(() => {
    if (guide === shownGuide.current) return;
    const timer = setTimeout(() => {
      const tree = mapRoot.current?.querySelector('.tree');
      if (guide) tree?.dispatchEvent(new CustomEvent('tree:island', {detail: guide}));
      else { tree?.dispatchEvent(new CustomEvent('tree:island', {detail: null})); if (current) tree?.dispatchEvent(new CustomEvent('tree:module', {detail: current})); }
      shownGuide.current = guide;
    }, 180);
    return () => clearTimeout(timer);
  }, [guide]);   // eslint-disable-line react-hooks/exhaustive-deps -- only a change of guide moves the camera here
  useEffect(() => {
    if (!current || current === shownModule.current) return;
    const timer = setTimeout(() => {
      shownModule.current = current;
      mapRoot.current?.querySelector('.tree')?.dispatchEvent(new CustomEvent('tree:module', {detail: current}));
    }, 180);
    return () => clearTimeout(timer);
  }, [current]);
  // Framing centres the branch in the part of the map the panel leaves visible (its width once the fold
  // animation ends; on a phone the panel is a sheet at the bottom and covers no side).
  const openRef = useRef(open);
  openRef.current = open;
  const options = useMemo(() => {
    const islands: Record<string, JourneyPath['guides']> = {};
    for (const guide of path?.guides ?? []) (islands[guide.module] ??= []).push(guide);
    return {fill: true, module: current, islands, inset: () => (window.innerWidth <= 800 || !path ? 0 : openRef.current ? 424 : 80)};
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps -- where the map opens

  async function custom() {
    try {
      await getJson('/api/app/journey/custom');
    } catch (e) {
      setPaywall(e instanceof ApiError ? e.message : 'Нужна подписка для анализа');
    }
  }

  if (!path || !plan) {
    return (
      <div className="my-path is-plain" ref={page}>
        <div className="my-path-map"><SkillMap data={home} options={options} /></div>
        <aside className="my-path-invite" aria-label="Мой путь">
          <p className="eyebrow">Мой путь</p>
          <h2>Карта станет твоим маршрутом</h2>
          <p>Выбери до трёх целей — и мы проложим по карте путь из уроков под тебя: что ты, вероятно, уже знаешь, что изучишь и к какой дате.</p>
          {bootstrap.user
            ? <AppLink className="button" to="/onboarding">{journey?.status === 'draft' ? 'Продолжить знакомство →' : 'Выбрать цели →'}</AppLink>
            : <AppLink className="button" to="/login?next=/path">Войти и выбрать цели →</AppLink>}
        </aside>
      </div>
    );
  }
  return (
    <div className={'my-path' + (open ? ' is-open' : ' is-folded') + (pull ? ' is-pulling' : '')} ref={page}
      style={{'--pull': `${pull}px`} as React.CSSProperties}>
      <div className="my-path-map" ref={mapRoot}>
        <SkillMap data={home} title={item ? `Мой путь · к ${dateIn(week, 'long')}` : 'Мой путь'} decorate={decorate} options={options} />
      </div>
      <aside className="my-path-panel" aria-label="План обучения" onKeyDown={event => { if (event.key === 'Escape' && open) { event.preventDefault(); fold(); } }}>
        {open ? (
          <>
            <button type="button" className="my-path-fold" onClick={fold} aria-label="Свернуть план" title="Свернуть план"><span className="path-fold-desktop">›</span><span className="path-fold-mobile">↓ Назад к карте</span></button>
            <div className="my-path-plan-scroll" ref={scroller}>
              <PathPlan path={path} plan={plan} hidden={hidden} reading={reading} week={week} progress={progress}
                onToggle={id => setHidden(h => (h.includes(id) ? h.filter(x => x !== id) : [...h, id]))}
                custom={journey?.answers.custom?.trim()} onCustom={custom} paywall={paywall} focusGuide={guide} onGuide={setGuide} />
            </div>
          </>
        ) : (
          <>
          <PlanSwiper path={path} plan={plan} reading={reading} onReading={setReading} onOpen={unfold}
            onPull={distance => setPull(distance)} onRelease={distance => { setPull(0); if (distance > PULL_TO_OPEN) unfold(); }} />
          <PlanTimeline path={path} plan={plan} hidden={hidden} reading={reading} onReading={setReading} onOpen={unfold}
            label={item ? dateIn(week) : 'сегодня'} />
          </>
        )}
      </aside>
    </div>
  );
}
