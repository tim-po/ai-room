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
  document.addEventListener('DOMContentLoaded', () => {
    apply(theme);
    const toggle = document.querySelector('[data-theme-toggle]');
    if (!toggle) return;
    toggle.addEventListener('click', () => {
      theme = theme === 'dawn' ? 'dusk' : 'dawn';
      try { localStorage.setItem('airoom-theme', theme); } catch (_) { /* private mode: lasts for this page */ }
      // Tokens are animatable (theme-motion.css), but only while .theme-shift is set: the sun rises
      // or sets for this switch, and ordinary page loads never animate the theme.
      root.classList.add('theme-shift');
      apply(theme);
      clearTimeout(shiftTimer);
      shiftTimer = setTimeout(() => root.classList.remove('theme-shift'), 3600);
    });
  });
})();
