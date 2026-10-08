// Skill map canvas, desktop: a round tree. AI Room in the centre, the directions (topics) around it,
// and every course growing outward as an arm of modules and milestones. All arms curl the same way,
// like a spiral galaxy, so they never cross however long a course grows.
//
// Three levels of detail (far / mid / near). Nodes are smaller zoomed out, so the arms are laid out
// for every level up front and stretch between them on a change of detail, while the point under the
// cursor stays where it is. Camera moves (buttons, clicks) fly. Phones get the trail (TrailMap.tsx).
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
  const PAD = 120;
  const WIDTH = {hub: 300, topic: 320, course: 320, module: 250, milestone: 190};
  const RADIUS = {topic: 470, course: 960};   // from the centre to a topic, and to its courses
  const SPREAD = 0.52;   // radians between the arms of one topic
  const CURL = 0.16;     // how much an arm turns per 1000px, the same way for every arm
  const GAP = {far: 44, mid: 60, near: 76};   // between consecutive nodes along an arm
  const STATE = {done: 'Пройден', progress: 'В процессе', open: 'Доступен', locked: 'Урок клуба', coming: 'Скоро'};
  const NS = 'http://www.w3.org/2000/svg';

  const easeOut = t => 1 - Math.pow(1 - t, 3);
  const easeInOut = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  const lerp = (a, b, t) => a + (b - a) * t;
  const clampK = k => Math.min(1.6, Math.max(0.06, k));
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const plural = (n, one, few, many) => n % 10 === 1 && n % 100 !== 11 ? one : (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20) ? few : many);

  // ---- nodes and edges -------------------------------------------------
  const svg = document.createElementNS(NS, 'svg');
  svg.classList.add('tree-edges'); svg.setAttribute('aria-hidden', 'true');
  canvas.append(svg);
  const nodes = [], edges = [], nodeOf = new WeakMap();
  function add(element, kind) {
    element.classList.add('tree-node', 'is-' + kind + '-node');
    element.style.width = WIDTH[kind] + 'px';
    canvas.append(element);
    const node = {el: element, kind, w: WIDTH[kind]};
    nodes.push(node); nodeOf.set(element, node);
    return node;
  }
  function link(from, to, cls) {
    const path = document.createElementNS(NS, 'path');
    path.setAttribute('class', cls); svg.append(path);
    edges.push({from, to, path});
  }

  const MILESTONE_NOTE = {reached: 'Веха пройдена', coming: 'Скоро откроется'};
  function milestone(stone, course) {
    const box = el('div', `tree-milestone is-${stone.state} is-level-${stone.rank}`);
    const badge = el('span', 'tree-milestone-badge');
    badge.innerHTML = stone.state === 'reached'
      ? '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>'
      : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 21V4m0 1h11l-3 4.5 3 4.5H7"/></svg>';
    const note = stone.state === 'next' || stone.state === 'ahead'
      ? `ещё ${stone.left} ${plural(stone.left, 'урок', 'урока', 'уроков')}` : MILESTONE_NOTE[stone.state];
    box.append(badge, el('span', 'tree-milestone-kicker', `Веха ${stone.number}`), el('strong', null, stone.name),
      el('span', 'tree-milestone-course', course.rank_name || course.title), el('span', 'tree-milestone-note', note));
    if (stone.state === 'next') {
      const meter = el('span', 'tree-milestone-meter'), fill = el('span');
      fill.style.width = (stone.lessons ? 100 * stone.done / stone.lessons : 0) + '%'; meter.append(fill); box.append(meter);
    }
    box.title = `${stone.title} — ${stone.state === 'coming' ? 'откроется, когда появятся новые уроки' : note}`;
    return box;
  }

  function moduleBox(module, index) {
    const box = el('section', 'tree-module is-' + module.state);
    box.title = module.title;
    const head = el('h3');
    head.append(el('span', 'tree-module-index', String(index + 1)), el('span', 'tree-module-title', module.title));
    const list = el('ul');
    for (const lesson of module.lessons) {
      const row = el(lesson.url ? 'a' : 'span', `tree-lesson is-${lesson.state}` + (lesson.current ? ' is-current' : ''));
      if (lesson.url) row.href = lesson.url;
      row.title = `${lesson.title} — ${STATE[lesson.state]}`;
      row.append(el('span', 'tree-dot'), el('span', 'tree-title', lesson.title));
      if (lesson.state === 'locked') row.append(el('span', 'tree-tag', 'Клуб'));
      else if (lesson.minutes && lesson.state !== 'coming') row.append(el('span', 'tree-tag', lesson.minutes + ' мин'));
      row.append(el('span', 'visually-hidden', ` (${STATE[lesson.state]})`));
      const item = el('li'); item.append(row); list.append(item);
    }
    box.append(head, list);
    return box;
  }

  const hubEl = el('div', 'tree-root');
  const hub = add(hubEl, 'hub');
  let totalLessons = 0, totalCourses = 0;
  const count = data.topics.length;
  const topics = data.topics.map((topic, t) => {
    // Directions around the centre, the first one up and to the left.
    const angle = -3 * Math.PI / 4 + t * 2 * Math.PI / count;
    const box = el('div', 'tree-topic' + (topic.interest ? ' is-interest' : ''));
    box.append(el('strong', null, topic.title), el('span', null, topic.subtitle));
    if (topic.interest) box.append(el('em', null, 'Ваш интерес'));
    const node = add(box, 'topic');
    link(hub, node, 'trunk');
    const lanes = topic.courses.map((course, c) => {
      totalCourses++; totalLessons += course.total;
      const card = el(course.url ? 'a' : 'div', 'tree-course' + (course.current ? ' is-current' : ''));
      if (course.url) card.href = course.url;
      card.id = 'course-' + course.id;
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
      const cardNode = add(card, 'course');
      link(node, cardNode, 'branch');
      // The arm: modules in order, each milestone right after the module it follows.
      let previous = cardNode;
      const chain = [];
      course.modules.forEach((module, index) => {
        const moduleNode = add(moduleBox(module, index), 'module');
        link(previous, moduleNode, 'path is-' + module.state);
        chain.push(moduleNode); previous = moduleNode;
        for (const stone of (course.milestones || []).filter(m => m.after === index)) {
          const stoneNode = add(milestone(stone, course), 'milestone');
          link(previous, stoneNode, 'path is-' + (stone.state === 'reached' ? 'done' : 'active') + ' is-to-milestone');
          chain.push(stoneNode); previous = stoneNode;
        }
      });
      const offset = topic.courses.length > 1 ? (c - (topic.courses.length - 1) / 2) * SPREAD : 0;
      return {card: cardNode, chain, course, topic, angle: angle + offset};
    });
    return {node, lanes, angle, topic};
  });
  hubEl.append(el('strong', null, 'AI Room'), el('span', null, `${data.topics.length} направления · ${totalCourses} ${plural(totalCourses, 'курс', 'курса', 'курсов')} · ${totalLessons} ${plural(totalLessons, 'урок', 'урока', 'уроков')}`));
  const allLanes = topics.flatMap(t => t.lanes);
  const laneOf = node => allLanes.find(l => l.card === node || l.chain.includes(node));

  // ---- layouts: one per level of detail, measured up front ----------------
  const layouts = {};
  function measure() {
    canvas.classList.add('is-measuring');
    for (const n of nodes) n.el.style.height = '';
    const heights = {};
    for (const level of ['far', 'mid', 'near']) {
      canvas.dataset.lod = canvas.dataset.detail = level;
      heights[level] = new Map(nodes.map(n => [n, n.el.offsetHeight]));
    }
    canvas.dataset.lod = canvas.dataset.detail = lod || 'far';
    void canvas.offsetHeight;   // apply the restored level while transitions are still off
    canvas.classList.remove('is-measuring');
    for (const level of ['far', 'mid', 'near']) layouts[level] = layout(level, heights[level]);
  }
  // Half the length of a box measured along a direction: how far it reaches towards its neighbour.
  const reach = (w, h, c, s) => (Math.abs(c) * w + Math.abs(s) * h) / 2;
  function layout(level, height) {
    const centre = new Map([[hub, [0, 0]]]);
    for (const topic of topics) {
      centre.set(topic.node, [Math.cos(topic.angle) * RADIUS.topic, Math.sin(topic.angle) * RADIUS.topic]);
      for (const lane of topic.lanes) {
        let cx = Math.cos(lane.angle) * RADIUS.course, cy = Math.sin(lane.angle) * RADIUS.course, travelled = 0;
        centre.set(lane.card, [cx, cy]);
        let previous = lane.card;
        for (const n of lane.chain) {
          const theta = lane.angle + CURL * travelled / 1000, c = Math.cos(theta), s = Math.sin(theta);
          const step = reach(previous.w, height.get(previous), c, s) + GAP[level] + reach(n.w, height.get(n), c, s);
          cx += c * step; cy += s * step; travelled += step;
          centre.set(n, [cx, cy]); previous = n;
        }
      }
    }
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of nodes) {
      const [cx, cy] = centre.get(n), h = height.get(n);
      minX = Math.min(minX, cx - n.w / 2); maxX = Math.max(maxX, cx + n.w / 2);
      minY = Math.min(minY, cy - h / 2); maxY = Math.max(maxY, cy + h / 2);
    }
    const pos = new Map(nodes.map(n => {
      const [cx, cy] = centre.get(n), h = height.get(n);
      return [n, {x: cx - n.w / 2 - minX + PAD, y: cy - h / 2 - minY + PAD, h}];
    }));
    return {pos, width: maxX - minX + 2 * PAD, height: maxY - minY + 2 * PAD};
  }
  const copy = l => ({pos: new Map([...l.pos].map(([n, p]) => [n, {...p}])), width: l.width, height: l.height});

  // ---- painting ----------------------------------------------------------
  let shown = null;
  const centreOf = n => { const p = shown.pos.get(n); return [p.x + n.w / 2, p.y + p.h / 2]; };
  function paint() {
    for (const n of nodes) {
      const p = shown.pos.get(n);
      n.el.style.transform = `translate3d(${p.x.toFixed(2)}px,${p.y.toFixed(2)}px,0)`;
      n.el.style.height = p.h.toFixed(2) + 'px';
    }
    // Edges leave and arrive along the direction away from the centre, so branches flow outward.
    const [hx, hy] = centreOf(hub);
    const outward = (x, y, fallback) => {
      const dx = x - hx, dy = y - hy, d = Math.hypot(dx, dy);
      return d > 1 ? [dx / d, dy / d] : fallback;
    };
    for (const e of edges) {
      const [x1, y1] = centreOf(e.from), [x2, y2] = centreOf(e.to), len = Math.hypot(x2 - x1, y2 - y1);
      const d2 = outward(x2, y2, [1, 0]), d1 = outward(x1, y1, d2), k = len * 0.38;
      e.path.setAttribute('d', `M${x1.toFixed(1)},${y1.toFixed(1)} C${(x1 + d1[0] * k).toFixed(1)},${(y1 + d1[1] * k).toFixed(1)} `
        + `${(x2 - d2[0] * k).toFixed(1)},${(y2 - d2[1] * k).toFixed(1)} ${x2.toFixed(1)},${y2.toFixed(1)}`);
    }
    canvas.style.width = shown.width + 'px'; canvas.style.height = shown.height + 'px';
    svg.setAttribute('width', shown.width); svg.setAttribute('height', shown.height);
  }

  // ---- camera ------------------------------------------------------------
  const view = {x: 0, y: 0, k: 0.3};
  let lod = null, tween = null, anchor = null, flight = null, frame = 0, fadeTimer = 0;
  function applyView() {
    canvas.style.transform = `translate3d(${view.x}px,${view.y}px,0) scale(${view.k})`;
    zoomLabel.textContent = Math.round(view.k * 100) + '%';
    whereAmI();
  }
  // Hysteresis: thresholds overlap so the level does not flicker at a boundary.
  function levelFor(k) {
    if (lod === 'far') return k > 0.5 ? (k > 0.8 ? 'near' : 'mid') : 'far';
    if (lod === 'mid') return k < 0.44 ? 'far' : k > 0.8 ? 'near' : 'mid';
    if (lod === 'near') return k < 0.72 ? (k < 0.44 ? 'far' : 'mid') : 'near';
    return k < 0.47 ? 'far' : k < 0.76 ? 'mid' : 'near';
  }
  // An anchor ties a point on a node (fractions of its box, which may lie outside it) to a screen
  // point. While the arms stretch, the camera follows it, so what you are looking at stays put.
  function pickAnchor(sx, sy) {
    const cx = (sx - view.x) / view.k, cy = (sy - view.y) / view.k;
    let best = null, bestD = Infinity;
    for (const n of nodes) {
      const [x, y] = centreOf(n), d = Math.hypot(x - cx, y - cy);
      if (d < bestD) { bestD = d; best = n; }
    }
    const p = shown.pos.get(best);
    return {node: best, fx: (cx - p.x) / best.w, fy: (cy - p.y) / p.h, sx, sy};
  }
  const anchorPoint = a => { const p = shown.pos.get(a.node); return [p.x + a.fx * a.node.w, p.y + a.fy * p.h]; };
  function setLod(next) {
    if (next === lod) return;
    lod = next;
    canvas.dataset.lod = next;
    if (!MS.layout) { canvas.dataset.detail = next; shown = copy(layouts[next]); paint(); return; }
    tween = {from: copy(shown), to: layouts[next], start: performance.now()};
    // Contents swap behind a short fade while the arms stretch.
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
        shown.pos.set(n, {x: lerp(a.x, b.x, e), y: lerp(a.y, b.y, e), h: lerp(a.h, b.h, e)});
      }
      shown.width = lerp(tween.from.width, tween.to.width, e);
      shown.height = lerp(tween.from.height, tween.to.height, e);
      if (t >= 1) tween = null;
      paint();
    }
    if (flight) {
      const e = easeInOut(flightT), [wx, wy] = anchorPoint(flight);
      view.x = lerp(flight.from.sx, flight.to.sx, e) - wx * view.k;
      view.y = lerp(flight.from.sy, flight.to.sy, e) - wy * view.k;
      if (flightT >= 1) flight = null;
    } else if (anchor) {
      const [wx, wy] = anchorPoint(anchor);
      view.x = anchor.sx - wx * view.k; view.y = anchor.sy - wy * view.k;
    }
    if (!tween) anchor = null;
    applyView();
    if (tween || flight) schedule();
  }
  // Fly so that a point on `node` (fractions fx, fy of its box) ends at screen (sx, sy) at zoom k.
  function flyTo(node, k, {fx = .5, fy = .5, sx = viewport.clientWidth / 2, sy = viewport.clientHeight / 2, dur = MS.fly} = {}) {
    const target = {node, fx, fy};
    const [wx, wy] = anchorPoint(target);
    flight = {...target, start: performance.now(), dur,
      from: {k: view.k, sx: view.x + wx * view.k, sy: view.y + wy * view.k}, to: {k: clampK(k), sx, sy}};
    anchor = null;
    if (!dur) tick(performance.now()); else schedule();
  }
  // A course: its card a little towards the centre, so its arm fills the rest of the frame.
  function flyToCourse(card, k, dur) {
    const lane = laneOf(card), vw = viewport.clientWidth, vh = viewport.clientHeight;
    flyTo(card, k, {sx: vw / 2 - Math.cos(lane.angle) * vw * 0.3, sy: vh / 2 - Math.sin(lane.angle) * vh * 0.3, dur});
  }
  // Frame a set of nodes (in the zoomed-out layout), the hub held as the reference point.
  function frameNodes(set, dur = MS.fly, limit = 0.6) {
    const L = layouts.far, vw = viewport.clientWidth, vh = viewport.clientHeight;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of set) {
      const p = L.pos.get(n);
      minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x + n.w); minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y + p.h);
    }
    const k = clampK(Math.min(vw / (maxX - minX + 80), vh / (maxY - minY + 80), limit));
    const hp = L.pos.get(hub);
    flyTo(hub, k, {sx: vw / 2 + (hp.x + hub.w / 2 - (minX + maxX) / 2) * k, sy: vh / 2 + (hp.y + hp.h / 2 - (minY + maxY) / 2) * k, dur});
  }
  const fit = dur => frameNodes(nodes, dur);
  // The heart of the map: the centre, the directions, the course cards and the start of every arm.
  const home = dur => frameNodes([hub, ...topics.flatMap(t => [t.node, ...t.lanes.flatMap(l => [l.card, ...l.chain.slice(0, 1)])])], dur, 0.42);
  // Wheel and pinch zoom keep the node point under the cursor in place, also while the arms stretch.
  function zoomAt(k, sx, sy) {
    flight = null;
    const a = pickAnchor(sx, sy);
    view.k = clampK(k);
    setLod(levelFor(view.k));
    const [wx, wy] = anchorPoint(a);
    view.x = sx - wx * view.k; view.y = sy - wy * view.k;
    anchor = tween ? a : null;
    applyView();
  }
  function panBy(dx, dy) {
    flight = null;
    view.x += dx; view.y += dy;
    if (anchor) { anchor.sx += dx; anchor.sy += dy; }
    applyView();
  }

  // ---- where am I: the course nearest the middle of the frame, named in its corner ---------------
  const context = el('button', 'tree-here-label');
  context.type = 'button'; context.tabIndex = -1; context.setAttribute('aria-hidden', 'true');
  viewport.append(context);
  let named = null;
  function whereAmI() {
    let lane = null;
    if (view.k >= 0.3) {
      const mx = (viewport.clientWidth / 2 - view.x) / view.k, my = (viewport.clientHeight / 2 - view.y) / view.k;
      let best = Infinity;
      for (const l of allLanes) for (const n of [l.card, ...l.chain]) {
        const [x, y] = centreOf(n), d = Math.hypot(x - mx, y - my);
        if (d < best) { best = d; lane = l; }
      }
      if (best > 900) lane = null;
    }
    if (lane === named) return;
    named = lane;
    context.classList.toggle('is-shown', !!lane);
    if (!lane) return;
    context.replaceChildren(el('span', 'tree-here-topic', lane.topic.title), el('strong', null, lane.course.title));
    const standing = lane.course.standing;
    if (standing && standing.level) context.append(el('em', `tree-rank is-level-${standing.level}`, standing.rank));
  }
  context.addEventListener('pointerdown', event => event.stopPropagation(), on);
  context.addEventListener('click', () => named && flyToCourse(named.card, Math.max(view.k, 0.62)), on);

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
    if (!node) return;
    event.preventDefault();
    if (node.kind === 'hub') home();
    else if (node.kind === 'module' || node.kind === 'milestone') flyTo(node, 0.95);
    else if (node.kind === 'course') flyToCourse(node, lod === 'far' ? 0.55 : 0.95);
    else {
      // A direction: its courses' arms in view.
      const topic = topics.find(t => t.node === node);
      frameNodes([node, ...topic.lanes.flatMap(l => [l.card, ...l.chain])], MS.fly, 0.42);
    }
  }, on);
  // Keyboard focus brings the focused item into view.
  canvas.addEventListener('focusin', event => {
    if (!event.target.matches(':focus-visible')) return;
    const r = event.target.getBoundingClientRect(), v = viewport.getBoundingClientRect(), m = 40;
    if (r.left > v.left + m && r.right < v.right - m && r.top > v.top + m && r.bottom < v.bottom - m) return;
    const node = nodeOf.get(event.target.closest('.tree-node'));
    if (node) flyTo(node, Math.max(view.k, 0.85));
  }, on);

  // +/− keep whatever is at the centre of the frame in the centre.
  function zoomButton(factor) {
    const sx = viewport.clientWidth / 2, sy = viewport.clientHeight / 2, a = pickAnchor(sx, sy);
    flyTo(a.node, view.k * factor, {fx: a.fx, fy: a.fy, sx, sy});
  }
  root.querySelector('[data-zoom-in]').addEventListener('click', () => zoomButton(1.35), on);
  root.querySelector('[data-zoom-out]').addEventListener('click', () => zoomButton(1 / 1.35), on);
  root.querySelector('[data-fit]').addEventListener('click', () => fit(), on);
  const here = canvas.querySelector('.tree-lesson.is-current') || canvas.querySelector('.tree-course.is-current');
  const hereNode = here && nodeOf.get(here.closest('.tree-node'));
  const hereButton = root.querySelector('[data-here]');
  if (hereNode) hereButton.addEventListener('click', () => hereNode.kind === 'course' ? flyToCourse(hereNode, 0.95) : flyTo(hereNode, 1), on);
  else hereButton.hidden = true;

  // ---- sizing and start ----------------------------------------------------
  // The canvas fills the rest of the window, so the page itself never needs to scroll past it.
  function size() {
    // Nearly the window's height: scrolled to the bottom, the map fills the screen under the sticky
    // header, with the same small gap the card has at its sides.
    const header = document.querySelector('.club-header'), nav = header && header.querySelector('nav');
    const bar = nav && getComputedStyle(nav).position === 'fixed' ? nav.offsetHeight : 0;
    const top = header && getComputedStyle(header).position === 'sticky' ? header.offsetHeight : 0;
    const gap = document.documentElement.hasAttribute('data-glass') ? 16 : 64;
    document.documentElement.style.setProperty('--map-nav-bar', bar + 'px');
    viewport.style.height = Math.max(420, window.innerHeight - top - bar - 2 * gap) + 'px';
  }
  // Until the card has scrolled fully into view, the wheel scrolls the page down to it instead of
  // panning the map. The rest of that gesture (trackpad momentum) is absorbed rather than flinging the map.
  let pageScrolledAt = -1e9;
  function pageFirst(event) {
    if (event.ctrlKey || event.metaKey || event.deltaY <= 0 || Math.abs(event.deltaX) > Math.abs(event.deltaY)) return false;
    const header = document.querySelector('.club-header');
    const top = header && getComputedStyle(header).position === 'sticky' ? header.offsetHeight : 0;
    const left = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
    return left > 1 && viewport.getBoundingClientRect().top > top + 8;
  }
  // New sizes (fonts arriving): re-measure and re-lay out, keeping the middle of the frame in place.
  function remeasure() {
    if (tween || flight) return;
    const a = pickAnchor(viewport.clientWidth / 2, viewport.clientHeight / 2);
    measure(); shown = copy(layouts[lod]); paint();
    const [wx, wy] = anchorPoint(a);
    view.x = a.sx - wx * view.k; view.y = a.sy - wy * view.k;
    applyView();
  }
  size();
  measure();
  const linked = location.hash.startsWith('#course-') && document.getElementById(location.hash.slice(1));
  // A learner with a course under way starts on it, readable; everyone else gets the whole map.
  const current = !linked && canvas.querySelector('.tree-course.is-current');
  const start = linked || current;
  // Choose the starting zoom first, so the first frame is already at the right level of detail.
  lod = start ? levelFor(0.62) : 'far';
  canvas.dataset.lod = canvas.dataset.detail = lod;
  shown = copy(layouts[lod]); paint();
  if (start) {
    flyToCourse(nodeOf.get(start), 0.62, 0);
    if (linked) linked.classList.add('is-linked');
  } else {
    home(0);
  }
  const onResize = () => { size(); remeasure(); };
  window.addEventListener('resize', onResize, on);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { if (!destroyed) { size(); remeasure(); } });
  // The toolbar above can change height (fonts arriving, wrapping): keep the card's bottom in place.
  const above = 'ResizeObserver' in window ? new ResizeObserver(() => { if (!destroyed) size(); }) : null;
  root.querySelectorAll('.tree-bar-top').forEach(node => above && above.observe(node));
  root.classList.add('is-ready');
  return () => {
    destroyed = true;
    listeners.abort();
    if (above) above.disconnect();
    canvas.replaceChildren();
    context.remove();
    if (frame) cancelAnimationFrame(frame);
    clearTimeout(fadeTimer);
  };
}
