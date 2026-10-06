'use strict';
// Custom dropdown for learner pages. The native <select> stays in the form (hidden, still submitted)
// and remains the source of truth; the button + listbox mirror it. Keyboard: arrows, Home/End,
// Enter/Space, Escape, Tab, and type-ahead. Editor pages keep native selects.
(() => {
  if (!document.body.classList.contains('learner-surface')) return;
  let uid = 0;

  function labelText(select) {
    if (select.getAttribute('aria-label')) return select.getAttribute('aria-label');
    const label = select.closest('label') || (select.id && document.querySelector(`label[for="${select.id}"]`));
    if (!label) return '';
    return [...label.childNodes].filter(n => n.nodeType === Node.TEXT_NODE || (n.nodeType === 1 && !n.matches('select,.select'))).map(n => n.textContent).join(' ').trim();
  }

  function enhance(select) {
    if (select.multiple || select.dataset.native !== undefined || select.closest('.select')) return;
    const id = 'select-' + (++uid);
    const wrap = document.createElement('div');
    wrap.className = 'select';
    select.before(wrap);
    wrap.append(select);
    select.classList.add('select-native');
    select.tabIndex = -1;
    select.setAttribute('aria-hidden', 'true');

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'select-button';
    button.setAttribute('aria-haspopup', 'listbox');
    button.setAttribute('aria-expanded', 'false');
    button.setAttribute('aria-controls', id + '-list');
    const value = document.createElement('span');
    value.className = 'select-value';
    button.append(value);

    const list = document.createElement('ul');
    list.className = 'select-list';
    list.id = id + '-list';
    list.setAttribute('role', 'listbox');
    list.tabIndex = -1;
    list.hidden = true;
    const name = labelText(select);
    if (name) list.setAttribute('aria-label', name);
    wrap.append(button, list);

    let options = [], active = -1, typed = '', typedAt = 0;
    function build() {
      list.replaceChildren();
      options = [...select.options].map((option, i) => {
        const item = document.createElement('li');
        item.className = 'select-option';
        item.id = `${id}-opt-${i}`;
        item.setAttribute('role', 'option');
        item.textContent = option.textContent;
        if (option.disabled) item.setAttribute('aria-disabled', 'true');
        item.addEventListener('mousedown', event => event.preventDefault());
        item.addEventListener('click', () => { if (!option.disabled) { choose(i); close(true); } });
        item.addEventListener('mousemove', () => setActive(i, false));
        list.append(item);
        return item;
      });
      sync();
    }
    function sync() {
      const current = select.selectedIndex;
      options.forEach((item, i) => item.setAttribute('aria-selected', String(i === current)));
      const text = current >= 0 ? select.options[current].textContent : '';
      value.textContent = text;
      button.setAttribute('aria-label', name ? `${name}: ${text}` : text);
    }
    function setActive(i, scroll = true) {
      if (i < 0 || i >= options.length) return;
      options[active]?.classList.remove('is-active');
      active = i;
      options[i].classList.add('is-active');
      list.setAttribute('aria-activedescendant', options[i].id);
      if (scroll) options[i].scrollIntoView({block: 'nearest'});
    }
    function choose(i) {
      if (select.selectedIndex === i) return;
      select.selectedIndex = i;
      sync();
      select.dispatchEvent(new Event('input', {bubbles: true}));
      select.dispatchEvent(new Event('change', {bubbles: true}));
    }
    function open() {
      if (wrap.classList.contains('is-open')) return;
      document.querySelectorAll('.select.is-open').forEach(other => other !== wrap && other.dispatchEvent(new Event('select:close')));
      const below = window.innerHeight - button.getBoundingClientRect().bottom;
      list.classList.toggle('is-up', below < 300 && button.getBoundingClientRect().top > below);
      list.hidden = false;
      wrap.classList.add('is-open');
      button.setAttribute('aria-expanded', 'true');
      setActive(Math.max(0, select.selectedIndex));
      list.focus({preventScroll: true});
    }
    function close(refocus) {
      if (!wrap.classList.contains('is-open')) return;
      wrap.classList.remove('is-open');
      button.setAttribute('aria-expanded', 'false');
      list.removeAttribute('aria-activedescendant');
      setTimeout(() => { if (!wrap.classList.contains('is-open')) list.hidden = true; }, 160);
      if (refocus) button.focus({preventScroll: true});
    }
    function step(delta) {
      let i = active;
      do { i += delta; } while (i >= 0 && i < options.length && select.options[i].disabled);
      if (i >= 0 && i < options.length) setActive(i);
    }

    button.addEventListener('click', () => wrap.classList.contains('is-open') ? close(true) : open());
    button.addEventListener('keydown', event => {
      if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(event.key)) { event.preventDefault(); open(); }
    });
    list.addEventListener('keydown', event => {
      const key = event.key;
      if (key === 'ArrowDown') { event.preventDefault(); step(1); }
      else if (key === 'ArrowUp') { event.preventDefault(); step(-1); }
      else if (key === 'Home') { event.preventDefault(); setActive(0); }
      else if (key === 'End') { event.preventDefault(); setActive(options.length - 1); }
      else if (key === 'Enter' || key === ' ') { event.preventDefault(); if (!select.options[active]?.disabled) choose(active); close(true); }
      else if (key === 'Escape') { event.preventDefault(); close(true); }
      else if (key === 'Tab') { choose(active); close(false); }
      else if (key.length === 1) {
        const now = Date.now();
        typed = (now - typedAt > 700 ? '' : typed) + key.toLowerCase(); typedAt = now;
        const match = options.findIndex(o => o.textContent.toLowerCase().startsWith(typed));
        if (match >= 0) setActive(match);
      }
    });
    list.addEventListener('blur', event => { if (!wrap.contains(event.relatedTarget)) close(false); });
    wrap.addEventListener('select:close', () => close(false));
    // The field usually sits inside its <label>: keep clicks in the dropdown from re-triggering the
    // label (which would focus the hidden select and close the list).
    wrap.addEventListener('click', event => event.preventDefault());
    // A click on the label text focuses the hidden native select: hand focus to the visible control.
    select.addEventListener('focus', () => (wrap.classList.contains('is-open') ? list : button).focus({preventScroll: true}));
    select.addEventListener('change', sync);
    select.form?.addEventListener('reset', () => setTimeout(sync));
    build();
  }

  document.querySelectorAll('select').forEach(enhance);
  document.addEventListener('pointerdown', event => {
    document.querySelectorAll('.select.is-open').forEach(wrap => { if (!wrap.contains(event.target)) wrap.dispatchEvent(new Event('select:close')); });
  });
})();
