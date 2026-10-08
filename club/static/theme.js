'use strict';
// Day and night: Сумерки (dusk, dark) and Рассвет (dawn, light). The saved choice wins; otherwise
// the system light/dark setting decides (and keeps deciding). On top of that, a palette: «Закат»
// (the default) or «AI Room», the club's official colours (data-palette="club", theme-club.css),
// chosen in Настройки. ?theme=<name> previews any old palette without saving.
(() => {
  const GLASS = ['dusk', 'dawn'];
  const PREVIEW = ['workshop', 'paper', 'forest', 'graphite', 'midnight', 'aurora', ...GLASS];
  const PALETTES = ['sunset', 'club'];
  const read = key => { try { return localStorage.getItem(key); } catch (_) { return null; } };
  const write = (key, value) => { try { if (value === null) localStorage.removeItem(key); else localStorage.setItem(key, value); } catch (_) { /* private mode: lasts for this page */ } };
  const system = window.matchMedia('(prefers-color-scheme: light)');
  const param = new URLSearchParams(location.search).get('theme');
  let theme = PREVIEW.includes(param) ? param : read('airoom-theme');
  if (!GLASS.includes(theme) && !param) theme = system.matches ? 'dawn' : 'dusk';
  let palette = PALETTES.includes(read('airoom-palette')) ? read('airoom-palette') : 'sunset';
  const root = document.documentElement;
  const SAFARI = /^((?!chrome|chromium|crios|fxios|edg|android).)*safari/i.test(navigator.userAgent);
  function apply(name) {
    if (name === 'workshop') delete root.dataset.theme; else root.dataset.theme = name;
    if (palette === 'club') root.dataset.palette = 'club'; else delete root.dataset.palette;
    if (GLASS.includes(name)) root.dataset.glass = ''; else delete root.dataset.glass;
    const toggle = document.querySelector('[data-theme-toggle]');
    if (toggle) toggle.setAttribute('aria-label', name === 'dawn' ? 'Включить ночную тему' : 'Включить дневную тему');
  }
  apply(theme);
  // The sky moves behind live frosted blur, which then has to be redrawn every frame. Hold the sky
  // still while the learner scrolls, drags or zooms, and let it drift again once they pause.
  let stillTimer = 0, shiftTimer = 0;
  const hold = () => {
    if (!root.classList.contains('sky-still')) root.classList.add('sky-still');
    clearTimeout(stillTimer);
    stillTimer = setTimeout(() => root.classList.remove('sky-still'), 1100);
  };
  for (const type of ['scroll', 'wheel', 'pointerdown', 'pointermove', 'touchmove', 'keydown']) {
    window.addEventListener(type, event => { if (type !== 'pointermove' || event.buttons) hold(); }, {passive: true, capture: true});
  }
  document.addEventListener('tree:moving', hold);
  function toggle() {
    write('airoom-theme', theme === 'dawn' ? 'dusk' : 'dawn');
    change(theme === 'dawn' ? 'dusk' : 'dawn');
  }
  function change(next) {
    if (next === theme) return;
    theme = next;
    // The sun rises or sets for this switch only; ordinary page loads never animate the theme.
    // Where the browser has view transitions, the interface cross-fades from a snapshot while the sky
    // alone animates (.theme-fade, cheap); elsewhere every token animates (.theme-shift).
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    clearTimeout(shiftTimer);
    // Safari blinks frosted-glass elements inside view-transition snapshots, so it animates tokens.
    if (document.startViewTransition && !SAFARI && !reduced && GLASS.includes(theme)) {
      root.classList.remove('theme-shift');
      root.classList.add('theme-fade');
      document.startViewTransition(() => apply(theme));
      shiftTimer = setTimeout(() => root.classList.remove('theme-fade'), 1500);
      return;
    }
    root.classList.add('theme-shift');
    apply(theme);
    shiftTimer = setTimeout(() => root.classList.remove('theme-shift'), 1800);
  }
  // Настройки: 'auto' follows the system from now on; 'dawn' or 'dusk' fixes it.
  function setMode(mode) {
    write('airoom-theme', GLASS.includes(mode) ? mode : null);
    change(GLASS.includes(mode) ? mode : (system.matches ? 'dawn' : 'dusk'));
  }
  system.addEventListener('change', () => { if (!read('airoom-theme') && !param) change(system.matches ? 'dawn' : 'dusk'); });
  // A new palette cross-fades (view transitions) or simply switches.
  function setPalette(next) {
    if (!PALETTES.includes(next) || next === palette) return;
    write('airoom-palette', next === 'sunset' ? null : next);
    palette = next;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (document.startViewTransition && !SAFARI && !reduced) document.startViewTransition(() => apply(theme));
    else apply(theme);
  }
  // Delegated, so a toggle rendered later (the React app) works too.
  document.addEventListener('click', event => { if (event.target.closest && event.target.closest('[data-theme-toggle]')) toggle(); });
  document.addEventListener('DOMContentLoaded', () => apply(theme));
  window.AIRoomTheme = {toggle, setMode, setPalette, get: () => theme, palette: () => palette, mode: () => read('airoom-theme') || 'auto'};
})();
