import {useEffect, useId, useRef, useState, type KeyboardEvent} from 'react';
import {flushSync} from 'react-dom';

export type Option = readonly [value: string, label: string];

/**
 * Custom dropdown (the native one doesn't fit the glass UI). Same markup and styles as
 * club/static/select.js, which still enhances server pages: a button plus a listbox with
 * arrow keys, Home/End, Enter/Space, Escape, Tab and type-ahead.
 */
export default function Select({label, value, options, onChange, hideLabel = false}: {
  label: string;
  value: string;
  options: readonly Option[];
  onChange: (value: string) => void;
  hideLabel?: boolean;
}) {
  const id = useId();
  const button = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const [open, setOpen] = useState(false);
  const [up, setUp] = useState(false);
  const [active, setActive] = useState(0);
  const typed = useRef({text: '', at: 0});
  const selected = Math.max(0, options.findIndex(([v]) => v === value));
  const text = options[selected]?.[1] ?? '';

  useEffect(() => {
    if (open) list.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({block: 'nearest'});
  }, [open, active]);

  function show() {
    const box = button.current!.getBoundingClientRect();
    const below = window.innerHeight - box.bottom;
    // Render the list open right away so it can take focus (and the next key press) immediately.
    flushSync(() => {
      setUp(below < 300 && box.top > below);
      setActive(selected);
      setOpen(true);
    });
    list.current?.focus({preventScroll: true});
  }
  function hide(refocus: boolean) {
    setOpen(false);
    if (refocus) button.current?.focus({preventScroll: true});
  }
  function choose(index: number) {
    const option = options[index];
    if (option && option[0] !== value) onChange(option[0]);
  }
  function onListKey(event: KeyboardEvent) {
    const key = event.key;
    if (key === 'ArrowDown') { event.preventDefault(); setActive(i => Math.min(options.length - 1, i + 1)); }
    else if (key === 'ArrowUp') { event.preventDefault(); setActive(i => Math.max(0, i - 1)); }
    else if (key === 'Home') { event.preventDefault(); setActive(0); }
    else if (key === 'End') { event.preventDefault(); setActive(options.length - 1); }
    else if (key === 'Enter' || key === ' ') { event.preventDefault(); choose(active); hide(true); }
    else if (key === 'Escape') { event.preventDefault(); hide(true); }
    else if (key === 'Tab') { choose(active); hide(false); }
    else if (key.length === 1) {
      const now = Date.now();
      typed.current = {text: (now - typed.current.at > 700 ? '' : typed.current.text) + key.toLowerCase(), at: now};
      const match = options.findIndex(([, l]) => l.toLowerCase().startsWith(typed.current.text));
      if (match >= 0) setActive(match);
    }
  }

  return (
    <div className="select-field">
      <span className={hideLabel ? 'visually-hidden' : 'select-label'} id={`${id}-label`}>{label}</span>
      <div className={'select' + (open ? ' is-open' : '')}>
        <button ref={button} type="button" className="select-button" aria-haspopup="listbox" aria-expanded={open}
          aria-controls={`${id}-list`} aria-label={`${label}: ${text}`}
          onClick={() => (open ? hide(true) : show())}
          onKeyDown={event => { if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(event.key)) { event.preventDefault(); show(); } }}>
          <span className="select-value">{text}</span>
        </button>
        <ul ref={list} id={`${id}-list`} className={'select-list' + (up ? ' is-up' : '')} role="listbox" tabIndex={-1}
          aria-labelledby={`${id}-label`} hidden={!open} aria-activedescendant={open ? `${id}-opt-${active}` : undefined}
          onKeyDown={onListKey} onBlur={event => { if (!event.currentTarget.parentElement!.contains(event.relatedTarget)) hide(false); }}>
          {options.map(([v, l], i) => (
            <li key={v} id={`${id}-opt-${i}`} data-index={i} role="option" aria-selected={i === selected}
              className={'select-option' + (open && i === active ? ' is-active' : '')}
              onMouseDown={event => event.preventDefault()}
              onMouseMove={() => setActive(i)}
              onClick={() => { choose(i); hide(true); }}>
              {l}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
