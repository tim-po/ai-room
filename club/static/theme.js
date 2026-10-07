'use strict';
// Two product themes: Сумерки (dusk, dark) and Рассвет (dawn, light). The saved choice wins;
// otherwise the system light/dark setting decides. ?theme=<name> previews any palette without
// saving (the older palettes have no sky or glass).
(() => {
  const GLASS = ['dusk', 'dawn'];
  const PREVIEW = ['workshop', 'paper', 'forest', 'graphite', 'midnight', 'aurora', ...GLASS];
  const read = () => { try { return localStorage.getItem('airoom-theme'); } catch (_) { return null; } };
  const param = new URLSearchParams(location.search).get('theme');
  let theme = PREVIEW.includes(param) ? param : read();
  if (!GLASS.includes(theme) && !param) theme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'dawn' : 'dusk';
  const root = document.documentElement;
  function apply(name) {
    if (name === 'workshop') delete root.dataset.theme; else root.dataset.theme = name;
    if (GLASS.includes(name)) root.dataset.glass = ''; else delete root.dataset.glass;
    const toggle = document.querySelector('[data-theme-toggle]');
    if (toggle) toggle.setAttribute('aria-label', name === 'dawn' ? 'Включить тёмную тему «Сумерки»' : 'Включить светлую тему «Рассвет»');
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
    theme = theme === 'dawn' ? 'dusk' : 'dawn';
    try { localStorage.setItem('airoom-theme', theme); } catch (_) { /* private mode: lasts for this page */ }
    // The sun rises or sets for this switch only; ordinary page loads never animate the theme.
    // Where the browser has view transitions, the interface cross-fades from a snapshot while the sky
    // alone animates (.theme-fade, cheap); elsewhere every token animates (.theme-shift).
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    clearTimeout(shiftTimer);
    if (document.startViewTransition && !reduced && GLASS.includes(theme)) {
      root.classList.remove('theme-shift');
      root.classList.add('theme-fade');
      document.startViewTransition(() => apply(theme));
      shiftTimer = setTimeout(() => root.classList.remove('theme-fade'), 2600);
      return;
    }
    root.classList.add('theme-shift');
    apply(theme);
    shiftTimer = setTimeout(() => root.classList.remove('theme-shift'), 3600);
  }
  // Delegated, so a toggle rendered later (the React app) works too.
  document.addEventListener('click', event => { if (event.target.closest && event.target.closest('[data-theme-toggle]')) toggle(); });
  document.addEventListener('DOMContentLoaded', () => apply(theme));
  window.AIRoomTheme = {toggle, get: () => theme};
})();
