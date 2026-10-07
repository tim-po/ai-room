// Skill tree canvas: AI Room -> topics -> courses -> a left-to-right path of modules per course.
//
// Three levels of detail (far / mid / near). Columns are fixed, so a change of detail never moves a
// node sideways: layouts for every level are measured up front, and rows tween between them while
// the point under the cursor stays where it is. Camera moves (buttons, search, clicks) fly.
// Mounted by SkillMap.tsx into its own markup; returns a cleanup function.
export function mountTree(root, data) {
  let destroyed = false;
  // Every listener is registered with this signal, so cleanup removes all of them.
  const listeners = new AbortController();
  const on = {signal: listeners.signal};
  const viewport = root.querySelector('.tree-viewport');
  const canvas = root.querySelector('.tree-canvas');
  const zoomLabel = root.querySelector('[data-zoom-level]');
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const MS = {layout: reduced ? 0 : 420, fly: reduced ? 0 : 560, fade: reduced ? 0 : 110};
  const PAD = 48;
  const WIDTH = {hub: 280, topic: 320, course: 320, module: 250};
  const COL = {hub: PAD};
  COL.topic = COL.hub + WIDTH.hub + 90;
  COL.course = COL.topic + WIDTH.topic + 80;
  COL.module = COL.course + WIDTH.course + 64;
  const MODULE_STEP = WIDTH.module + 44;
  const SPACING = {far: {lane: 26, topic: 72, wave: 10}, mid: {lane: 34, topic: 84, wave: 16}, near: {lane: 44, topic: 100, wave: 22}};
  const STATE = {done: 'Пройден', progress: 'В процессе', open: 'Доступен', locked: 'Урок клуба', coming: 'Скоро'};
  const NS = 'http://www.w3.org/2000/svg';

  const easeOut = t => 1 - Math.pow(1 - t, 3);
  const easeInOut = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  const lerp = (a, b, t) => a + (b - a) * t;
  const clampK = k => Math.min(1.6, Math.max(0.15, k));
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const plural = (n, one, few, many) => n % 10 === 1 && n % 100 !== 11 ? one : (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20) ? few : many);

  // ---- nodes and edges -------------------------------------------------
  const svg = document.createElementNS(NS, 'svg');
  svg.classList.add('tree-edges'); svg.setAttribute('aria-hidden', 'true');
  canvas.append(svg);
  const nodes = [], edges = [], nodeOf = new WeakMap();
  function add(element, kind, x) {
    element.classList.add('tree-node');
    element.style.width = WIDTH[kind] + 'px';
    canvas.append(element);
    const node = {el: element, kind, x, w: WIDTH[kind]};
    nodes.push(node); nodeOf.set(element, node);
    return node;
  }
  function link(from, to, cls) {
    const path = document.createElementNS(NS, 'path');
    path.setAttribute('class', cls); svg.append(path);
    edges.push({from, to, path});
  }

  const hubEl = el('div', 'tree-root');
  const hub = add(hubEl, 'hub', COL.hub);
  let totalLessons = 0, totalCourses = 0, width = 0;
  const topics = data.topics.map(topic => {
    const box = el('div', 'tree-topic' + (topic.interest ? ' is-interest' : ''));
    box.append(el('strong', null, topic.title), el('span', null, topic.subtitle));
    if (topic.interest) box.append(el('em', null, 'Ваш интерес'));
    const node = add(box, 'topic', COL.topic);
    link(hub, node, 'trunk');
    const lanes = topic.courses.map(course => {
      totalCourses++; totalLessons += course.total;
      const card = el(course.url ? 'a' : 'div', 'tree-course' + (course.current ? ' is-current' : ''));
      if (course.url) card.href = course.url;
      card.id = 'course-' + course.id;
      card.dataset.search = course.title.toLowerCase();
      const bar = el('span', 'tree-bar'), fill = el('span');
      fill.style.width = (course.total ? 100 * course.done / course.total : 0) + '%'; bar.append(fill);
      card.append(el('span', 'tree-level', course.level), el('strong', null, course.title), bar,
        el('span', 'tree-course-meta', `Пройдено ${course.done} из ${course.total}` + (course.available < course.total ? ` · открыто ${course.available}` : '')));
      // Rank on the course (club/ranks.py): a badge on the card, the full title for screen readers.
      const standing = course.standing;
      if (standing && standing.level) {
        const badge = el('em', `tree-rank is-level-${standing.level}`, standing.rank);
        badge.title = `${standing.title}. ${standing.next}`;
        card.append(badge, el('span', 'visually-hidden', ` Ваше звание: ${standing.title}.`));
      }
      const cardNode = add(card, 'course', COL.course);
      link(node, cardNode, 'branch');
      let previous = cardNode;
      const modules = course.modules.map((module, index) => {
        const box = el('section', 'tree-module is-' + module.state);
        box.title = module.title;
        const head = el('h3');
        head.append(el('span', 'tree-module-index', String(index + 1)), el('span', 'tree-module-title', module.title));
        const list = el('ul');
        for (const lesson of module.lessons) {
          const row = el(lesson.url ? 'a' : 'span', `tree-lesson is-${lesson.state}` + (lesson.current ? ' is-current' : ''));
          if (lesson.url) row.href = lesson.url;
          row.title = `${lesson.title} — ${STATE[lesson.state]}`;
          row.dataset.search = lesson.title.toLowerCase();
          row.append(el('span', 'tree-dot'), el('span', 'tree-title', lesson.title));
          if (lesson.state === 'locked') row.append(el('span', 'tree-tag', 'Клуб'));
          else if (lesson.minutes && lesson.state !== 'coming') row.append(el('span', 'tree-tag', lesson.minutes + ' мин'));
          row.append(el('span', 'visually-hidden', ` (${STATE[lesson.state]})`));
          const item = el('li'); item.append(row); list.append(item);
        }
        box.append(head, list);
        // Every module is a control point: a flag that lights up once all its lessons are done.
        const flag = document.createElementNS(NS, 'svg');
        flag.setAttribute('viewBox', '0 0 16 16'); flag.setAttribute('class', 'tree-flag' + (module.checkpoint ? ' is-reached' : module.state === 'coming' ? ' is-coming' : ''));
        flag.innerHTML = '<path d="M4.5 14V2.5M4.5 3h7.5l-2 3 2 3H4.5"/>';
        const flagLabel = el('span', 'visually-hidden', module.checkpoint ? ` Контрольная точка ${index + 1} пройдена.` : ` Контрольная точка ${index + 1}.`);
        box.append(flag, flagLabel);
        const moduleNode = add(box, 'module', COL.module + index * MODULE_STEP);
        link(previous, moduleNode, 'path is-' + module.state);
        previous = moduleNode;
        return moduleNode;
      });
      width = Math.max(width, previous.x + previous.w + PAD);
      return {card: cardNode, modules, course, topic};
    });
    return {node, lanes};
  });
  hubEl.append(el('strong', null, 'AI Room'), el('span', null, `${data.topics.length} направления · ${totalCourses} ${plural(totalCourses, 'курс', 'курса', 'курсов')} · ${totalLessons} ${plural(totalLessons, 'урок', 'урока', 'уроков')}`));
  const laneOf = node => topics.flatMap(t => t.lanes).find(l => l.card === node || l.modules.includes(node));

  // ---- layouts: measured for every level; x never changes ---------------
  const layouts = {};
  let lod = null;
  function layout(level) {
    const sp = SPACING[level], height = new Map(nodes.map(n => [n, n.el.offsetHeight]));
    const pos = new Map();
    let y = PAD;
    for (const topic of topics) {
      const top = y;
      for (const lane of topic.lanes) {
        const tallest = Math.max(height.get(lane.card), ...lane.modules.map(m => height.get(m) + 2 * sp.wave));
        const centre = y + tallest / 2;
        pos.set(lane.card, {y: centre - height.get(lane.card) / 2, h: height.get(lane.card)});
        // Modules sway gently up and down along the path.
        lane.modules.forEach((m, i) => {
          const sway = lane.modules.length > 1 ? Math.sin(i * 1.3 + 0.6) * sp.wave : 0;
          pos.set(m, {y: centre + sway - height.get(m) / 2, h: height.get(m)});
        });
        y += tallest + sp.lane;
      }
      const centre = (top + y - sp.lane) / 2;
      pos.set(topic.node, {y: centre - height.get(topic.node) / 2, h: height.get(topic.node)});
      y += sp.topic - sp.lane;
    }
    const total = y - sp.topic + sp.lane + PAD;
    pos.set(hub, {y: total / 2 - height.get(hub) / 2, h: height.get(hub)});
    return {pos, height: total};
  }
  function measure() {
    canvas.classList.add('is-measuring');
    for (const n of nodes) n.el.style.height = '';
    for (const level of ['far', 'mid', 'near']) {
      canvas.dataset.lod = canvas.dataset.detail = level;
      layouts[level] = layout(level);
    }
    canvas.dataset.lod = canvas.dataset.detail = lod || 'far';
    void canvas.offsetHeight;   // apply the restored level while transitions are still off
    canvas.classList.remove('is-measuring');
  }
  const copy = l => ({pos: new Map([...l.pos].map(([n, p]) => [n, {...p}])), height: l.height});

  // ---- painting ----------------------------------------------------------
  let shown = null;
  function paint() {
    for (const n of nodes) {
      const p = shown.pos.get(n);
      n.el.style.transform = `translate3d(${n.x}px,${p.y.toFixed(2)}px,0)`;
      n.el.style.height = p.h.toFixed(2) + 'px';
    }
    for (const e of edges) {
      const a = shown.pos.get(e.from), b = shown.pos.get(e.to);
      const x1 = e.from.x + e.from.w, y1 = (a.y + a.h / 2).toFixed(1), x2 = e.to.x, y2 = (b.y + b.h / 2).toFixed(1), m = (x2 - x1) / 2;
      e.path.setAttribute('d', `M${x1},${y1} C${x1 + m},${y1} ${x2 - m},${y2} ${x2},${y2}`);
    }
    canvas.style.width = width + 'px'; canvas.style.height = shown.height + 'px';
    svg.setAttribute('width', width); svg.setAttribute('height', shown.height);
  }

  // ---- camera ------------------------------------------------------------
  const view = {x: 0, y: 0, k: 0.3};
  let pins = null;   // labels for rows whose course is off screen; built below
  function applyView() {
    canvas.style.transform = `translate3d(${view.x}px,${view.y}px,0) scale(${view.k})`;
    zoomLabel.textContent = Math.round(view.k * 100) + '%';
    if (pins) placePins();
  }

  // ---- where am I: once a course's card is off the left edge, its row keeps a label there --------
  const context = el('div', 'tree-context');
  context.setAttribute('aria-hidden', 'true');   // a pointer shortcut; the cards themselves stay in the tab order
  viewport.append(context);
  pins = topics.flatMap(topic => topic.lanes.map(lane => {
    const pin = el('button', 'tree-pin');
    pin.type = 'button'; pin.tabIndex = -1;
    pin.append(el('span', 'tree-pin-topic', lane.topic.title), el('strong', null, lane.course.title));
    if (lane.course.standing && lane.course.standing.level) pin.append(el('em', `tree-rank is-level-${lane.course.standing.level}`, lane.course.standing.rank));
    pin.addEventListener('pointerdown', event => event.stopPropagation(), on);
    pin.addEventListener('click', () => flyToCourse(lane.card, Math.max(view.k, 0.62)), on);
    context.append(pin);
    return {lane, pin, shown: false};
  }));
  function placePins() {
    const vh = viewport.clientHeight, k = view.k, taken = [];
    for (const item of pins) {
      const {card, modules} = item.lane, p = shown.pos.get(card);
      let show = view.x + (card.x + card.w * 0.6) * k < 0, y = 0;
      if (show) {
        let top = p.y, bottom = p.y + p.h;
        for (const m of modules) { const q = shown.pos.get(m); top = Math.min(top, q.y); bottom = Math.max(bottom, q.y + q.h); }
        const sTop = view.y + top * k, sBottom = view.y + bottom * k;
        y = Math.min(Math.max(view.y + (p.y + p.h / 2) * k, sTop + 24, 34), sBottom - 24, vh - 80);
        show = sBottom > 40 && sTop < vh - 80 && taken.every(other => Math.abs(other - y) > 52);
        if (show) taken.push(y);
      }
      if (show !== item.shown) { item.pin.classList.toggle('is-shown', show); item.shown = show; }
      if (show) item.pin.style.transform = `translate3d(0,${y.toFixed(1)}px,0) translateY(-50%)`;
    }
  }
  // Hysteresis: thresholds overlap so the level does not flicker at a boundary.
  function levelFor(k) {
    if (lod === 'far') return k > 0.5 ? (k > 0.8 ? 'near' : 'mid') : 'far';
    if (lod === 'mid') return k < 0.44 ? 'far' : k > 0.8 ? 'near' : 'mid';
    if (lod === 'near') return k < 0.72 ? (k < 0.44 ? 'far' : 'mid') : 'near';
    return k < 0.47 ? 'far' : k < 0.76 ? 'mid' : 'near';
  }

  // An anchor ties a point on a node (fraction of its height, plus an offset past an edge) to a
  // screen y. While rows tween, the camera follows it, so what you are looking at stays put.
  function pickAnchor(sx, sy) {
    const cx = (sx - view.x) / view.k, cy = (sy - view.y) / view.k;
    let best = null, bestD = Infinity;
    for (const n of nodes) {
      const p = shown.pos.get(n);
      const dx = cx < n.x ? n.x - cx : cx > n.x + n.w ? cx - n.x - n.w : 0;
      const dy = cy < p.y ? p.y - cy : cy > p.y + p.h ? cy - p.y - p.h : 0;
      const d = dx * dx * 4 + dy * dy;   // prefer nodes in the same column
      if (d < bestD) { bestD = d; best = n; }
    }
    const p = shown.pos.get(best);
    const f = Math.min(1, Math.max(0, (cy - p.y) / p.h));
    return {node: best, f, off: cy - (p.y + f * p.h), sy};
  }
  const anchorY = a => { const p = shown.pos.get(a.node); return p.y + a.f * p.h + a.off; };

  let tween = null, anchor = null, flight = null, frame = 0, fadeTimer = 0;
  function setLod(next) {
    if (next === lod) return;
    lod = next;
    canvas.dataset.lod = next;   // titles start their size transition together with the row tween
    if (!MS.layout) { canvas.dataset.detail = next; shown = copy(layouts[next]); paint(); return; }
    tween = {from: copy(shown), to: layouts[next], start: performance.now()};
    // Module contents swap behind a short fade.
    canvas.classList.add('lod-fade');
    clearTimeout(fadeTimer);
    fadeTimer = setTimeout(() => { canvas.dataset.detail = lod; canvas.classList.remove('lod-fade'); }, MS.fade);
    schedule();
  }
  function schedule() { if (!frame) { frame = requestAnimationFrame(tick); document.dispatchEvent(new Event('tree:moving')); } }
  function tick(now) {
    frame = 0;
    const flightT = flight ? (flight.dur ? Math.min(1, (now - flight.start) / flight.dur) : 1) : 0;
    if (flight) {
      view.k = Math.exp(lerp(Math.log(flight.from.k), Math.log(flight.to.k), easeInOut(flightT)));
      setLod(levelFor(view.k));
    }
    if (tween) {
      const t = Math.min(1, (now - tween.start) / MS.layout), e = easeOut(t);
      for (const n of nodes) {
        const a = tween.from.pos.get(n), b = tween.to.pos.get(n);
        shown.pos.set(n, {y: lerp(a.y, b.y, e), h: lerp(a.h, b.h, e)});
      }
      shown.height = lerp(tween.from.height, tween.to.height, e);
      if (t >= 1) tween = null;
      paint();
    }
    if (flight) {
      const e = easeInOut(flightT), p = shown.pos.get(flight.node);
      view.x = lerp(flight.from.sx, flight.to.sx, e) - (flight.node.x + flight.fx * flight.node.w) * view.k;
      view.y = lerp(flight.from.sy, flight.to.sy, e) - (p.y + flight.fy * p.h) * view.k;
      if (flightT >= 1) flight = null;
    } else if (anchor) {
      view.y = anchor.sy - anchorY(anchor) * view.k;
    }
    if (!tween) anchor = null;
    applyView();
    if (tween || flight) schedule();
  }

  // Fly so that a point on `node` (fx, fy as fractions) ends at screen (sx, sy) at zoom k.
  function flyTo(node, k, {fx = .5, fy = .5, sx = viewport.clientWidth / 2, sy = viewport.clientHeight / 2, dur = MS.fly} = {}) {
    const p = shown.pos.get(node);
    flight = {node, fx, fy, start: performance.now(), dur,
      from: {k: view.k, sx: view.x + (node.x + fx * node.w) * view.k, sy: view.y + (p.y + fy * p.h) * view.k},
      to: {k: clampK(k), sx, sy}};
    anchor = null;
    if (!dur) tick(performance.now()); else schedule();
  }
  // Show a course with its topic column on the left.
  const flyToCourse = (node, k, dur) => flyTo(node, k, {fx: 0, sx: 24 + (node.x - COL.topic) * clampK(k), dur});
  function fit(dur = MS.fly) {
    const L = layouts.far, vw = viewport.clientWidth, vh = viewport.clientHeight;
    const k = clampK(Math.min(vw / width, vh / L.height, 0.43));
    const vx = (vw - width * k) / 2, vy = Math.max(12, (vh - L.height * k) / 2), hp = L.pos.get(hub);
    flyTo(hub, k, {fx: 0, fy: .5, sx: vx + hub.x * k, sy: vy + (hp.y + hp.h / 2) * k, dur});
  }
  // Wheel and pinch zoom keep the node point under the cursor in place, also while rows tween.
  function zoomAt(k, sx, sy) {
    flight = null;
    const cx = (sx - view.x) / view.k, a = pickAnchor(sx, sy);
    view.k = clampK(k);
    view.x = sx - cx * view.k;
    setLod(levelFor(view.k));
    view.y = a.sy - anchorY(a) * view.k;
    anchor = tween ? a : null;
    applyView();
  }
  function panBy(dx, dy) {
    flight = null;
    view.x += dx; view.y += dy;
    if (anchor) anchor.sy += dy;
    applyView();
  }

  // ---- input -------------------------------------------------------------
  viewport.addEventListener('wheel', event => {
    if (pageFirst(event)) { pageScrolledAt = event.timeStamp; return; }
    event.preventDefault();
    if (event.timeStamp - pageScrolledAt < 220) { pageScrolledAt = event.timeStamp; return; }
    const box = viewport.getBoundingClientRect();
    if (event.ctrlKey || event.metaKey) zoomAt(view.k * Math.exp(-event.deltaY * 0.01), event.clientX - box.left, event.clientY - box.top);
    else panBy(-event.deltaX, -event.deltaY);
  }, {passive: false, signal: listeners.signal});

  const pointers = new Map(); let drag = null, pinch = null, moved = false;
  viewport.addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    pointers.set(event.pointerId, {x: event.clientX, y: event.clientY});
    moved = false;
    if (pointers.size === 1) drag = {x: event.clientX, y: event.clientY};
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      pinch = {d: Math.hypot(a.x - b.x, a.y - b.y), k: view.k}; drag = null;
    }
  }, on);
  viewport.addEventListener('pointermove', event => {
    if (!pointers.has(event.pointerId)) return;
    pointers.set(event.pointerId, {x: event.clientX, y: event.clientY});
    if (pinch && pointers.size === 2) {
      const [a, b] = [...pointers.values()], box = viewport.getBoundingClientRect();
      zoomAt(pinch.k * Math.hypot(a.x - b.x, a.y - b.y) / pinch.d, (a.x + b.x) / 2 - box.left, (a.y + b.y) / 2 - box.top);
      moved = true;
    } else if (drag) {
      const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
      if (!moved && Math.hypot(dx, dy) < 5) return;
      if (!moved) { moved = true; viewport.setPointerCapture(event.pointerId); viewport.classList.add('is-dragging'); }
      drag.x = event.clientX; drag.y = event.clientY;
      panBy(dx, dy);
    }
  }, on);
  const release = event => {
    pointers.delete(event.pointerId);
    if (pointers.size < 2) pinch = null;
    if (!pointers.size) { drag = null; viewport.classList.remove('is-dragging'); }
  };
  viewport.addEventListener('pointerup', release, on);
  viewport.addEventListener('pointercancel', release, on);
  // A drag that started on a link must not open it or fly anywhere.
  viewport.addEventListener('click', event => { if (moved) { event.preventDefault(); event.stopPropagation(); moved = false; } }, {capture: true, signal: listeners.signal});

  // Zoomed out, a click flies to what was clicked; zoomed in, links open as usual.
  canvas.addEventListener('click', event => {
    if (lod === 'near') return;
    const target = event.target.closest('.tree-node'), node = target && nodeOf.get(target);
    if (!node || node.kind === 'hub') return;
    event.preventDefault();
    if (node.kind === 'module') flyTo(node, 0.95);
    else if (node.kind === 'course') flyToCourse(node, lod === 'far' ? 0.62 : 0.95);
    else flyToCourse(topics.find(t => t.node === node).lanes[0].card, 0.62);
  }, on);
  // Keyboard focus brings the focused item into view.
  canvas.addEventListener('focusin', event => {
    if (!event.target.matches(':focus-visible')) return;
    const r = event.target.getBoundingClientRect(), v = viewport.getBoundingClientRect(), m = 40;
    if (r.left > v.left + m && r.right < v.right - m && r.top > v.top + m && r.bottom < v.bottom - m) return;
    const node = nodeOf.get(event.target.closest('.tree-node'));
    if (node) flyTo(node, Math.max(view.k, 0.85));
  }, on);

  const centre = () => [viewport.clientWidth / 2, viewport.clientHeight / 2];
  // +/− keep whatever is at the centre of the frame in the centre.
  function zoomButton(factor) {
    const [sx, sy] = centre(), a = pickAnchor(sx, sy), p = shown.pos.get(a.node);
    const fx = ((sx - view.x) / view.k - a.node.x) / a.node.w;
    flyTo(a.node, view.k * factor, {fx, fy: (anchorY(a) - p.y) / p.h, sx, sy});
  }
  root.querySelector('[data-zoom-in]').addEventListener('click', () => zoomButton(1.35), on);
  root.querySelector('[data-zoom-out]').addEventListener('click', () => zoomButton(1 / 1.35), on);
  root.querySelector('[data-fit]').addEventListener('click', () => fit(), on);
  const here = canvas.querySelector('.tree-lesson.is-current') || canvas.querySelector('.tree-course.is-current');
  const hereNode = here && nodeOf.get(here.closest('.tree-node'));
  const hereButton = root.querySelector('[data-here]');
  if (hereNode) hereButton.addEventListener('click', () => hereNode.kind === 'course' ? flyToCourse(hereNode, 0.95) : flyTo(hereNode, 1), on);
  else hereButton.hidden = true;

  // ---- search ------------------------------------------------------------
  const search = root.querySelector('[data-tree-search]'), status = root.querySelector('[data-tree-status]');
  let matches = [], cursor = 0;
  const showMatch = match => { const node = nodeOf.get(match.closest('.tree-node')); if (node) flyTo(node, Math.max(view.k, 0.9)); };
  search.addEventListener('input', () => {
    const q = search.value.trim().toLowerCase();
    canvas.querySelectorAll('.is-match').forEach(n => n.classList.remove('is-match'));
    canvas.classList.toggle('has-search', q.length > 1);
    matches = q.length > 1 ? [...canvas.querySelectorAll('[data-search]')].filter(n => n.dataset.search.includes(q)) : [];
    matches.forEach(n => n.classList.add('is-match')); cursor = 0;
    status.textContent = q.length > 1 ? (matches.length ? `Найдено: ${matches.length}. Enter — к следующему.` : 'Ничего не нашлось') : '';
    if (matches.length) showMatch(matches[0]);
  }, on);
  search.addEventListener('keydown', event => {
    if (event.key === 'Enter' && matches.length) { event.preventDefault(); cursor = (cursor + 1) % matches.length; showMatch(matches[cursor]); }
    if (event.key === 'Escape') { search.value = ''; search.dispatchEvent(new Event('input')); }
  }, on);

  // ---- sizing and start ----------------------------------------------------
  // The canvas fills the rest of the window, so the page itself never needs to scroll past it.
  function size() {
    // Nearly the window's height: scrolled to the bottom, the map fills the screen under the sticky
    // header, with the same small gap the card has at its sides. On phones the navigation is a
    // fixed bar at the bottom: the card stops above it (--map-nav-bar keeps room for it below the page).
    const header = document.querySelector('.club-header'), nav = header && header.querySelector('nav');
    const bar = nav && getComputedStyle(nav).position === 'fixed' ? nav.offsetHeight : 0;
    const top = header && getComputedStyle(header).position === 'sticky' ? header.offsetHeight : 0;
    const gap = document.documentElement.hasAttribute('data-glass') ? 16 : 64;
    document.documentElement.style.setProperty('--map-nav-bar', bar + 'px');
    // Phones pan the map with every touch, so there the page doesn't scroll: the card fills the
    // rest of the screen from where it starts.
    const below = window.matchMedia('(max-width: 800px)').matches ? viewport.getBoundingClientRect().top + window.scrollY : top + gap;
    viewport.style.height = Math.max(420, window.innerHeight - below - bar - gap) + 'px';
  }
  // Until the card has scrolled fully into view, the wheel scrolls the page down to it instead of
  // panning the map.
  // The rest of that gesture (trackpad momentum) is absorbed rather than flinging the map.
  let pageScrolledAt = -1e9;
  function pageFirst(event) {
    if (event.ctrlKey || event.metaKey || event.deltaY <= 0 || Math.abs(event.deltaX) > Math.abs(event.deltaY)) return false;
    const header = document.querySelector('.club-header');
    const top = header && getComputedStyle(header).position === 'sticky' ? header.offsetHeight : 0;
    const left = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
    return left > 1 && viewport.getBoundingClientRect().top > top + 8;
  }
  function remeasure() {
    if (tween || flight) return;
    const [sx, sy] = centre(), a = pickAnchor(sx, sy);
    measure(); shown = copy(layouts[lod]); paint();
    view.y = a.sy - anchorY(a) * view.k;
    applyView();
  }
  size();
  measure();
  const phone = window.matchMedia('(max-width: 700px)').matches;
  const linked = location.hash.startsWith('#course-') && document.getElementById(location.hash.slice(1));
  // Choose the starting zoom first, so the first frame is already at the right level of detail.
  const startCourse = linked ? nodeOf.get(linked)
    : phone && hereNode ? laneOf(hereNode).card
    : phone ? (topics.find(t => t.node.el.classList.contains('is-interest')) || topics[0]).lanes[0].card
    : null;
  if (startCourse) {
    const k = linked && !phone ? 0.62 : 0.45;
    lod = levelFor(k); canvas.dataset.lod = canvas.dataset.detail = lod;
    shown = copy(layouts[lod]); paint();
    flyToCourse(startCourse, k, 0);
    if (linked) linked.classList.add('is-linked');
  } else {
    lod = 'far'; canvas.dataset.lod = canvas.dataset.detail = lod;
    shown = copy(layouts.far); paint();
    fit(0);
  }
  const onResize = () => { size(); remeasure(); };
  window.addEventListener('resize', onResize, on);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { if (!destroyed) { size(); remeasure(); } });
  // The toolbar above can change height (fonts arriving, the continue strip wrapping): keep the card's bottom in place.
  const above = 'ResizeObserver' in window ? new ResizeObserver(() => { if (!destroyed) size(); }) : null;
  root.querySelectorAll('.tree-bar-top, .resume-strip').forEach(node => above && above.observe(node));
  root.classList.add('is-ready');
  return () => {
    destroyed = true;
    listeners.abort();
    if (above) above.disconnect();
    canvas.replaceChildren();
    if (frame) cancelAnimationFrame(frame);
    clearTimeout(fadeTimer);
  };
}
