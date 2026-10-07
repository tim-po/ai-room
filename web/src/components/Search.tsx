import {useEffect, useId, useMemo, useRef, useState, type KeyboardEvent} from 'react';
import {useNavigate} from 'react-router';
import {getJson} from '../api';
import {prefetchPage} from '../prefetch';
import {plural} from '../format';
import type {DiscoverItem, DiscoverTopic, ItemKind, SearchData} from '../types';
import {Cover, highlight, kicker, subline} from './Items';

// Search as you type, everywhere: the header button (or / and ⌘K) opens it as a dialog, and Обзор
// has it inline. Results come grouped by class with the matched words marked; Enter opens the
// highlighted one, or all results. Recent searches stay on this device.

const RECENT_KEY = 'airoom-recent-searches';
const ORDER: ItemKind[] = ['lesson', 'course', 'guide', 'use_case', 'workshop', 'coming'];
const GROUP: Record<ItemKind, string> = {lesson: 'Уроки', course: 'Курсы', guide: 'Гайды', use_case: 'Кейсы', workshop: 'Воркшопы', coming: 'Скоро на платформе'};
const PER_GROUP = 4;

export function recentSearches(): string[] {
  try {
    const value = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
    return Array.isArray(value) ? value.filter(v => typeof v === 'string').slice(0, 6) : [];
  } catch {
    return [];
  }
}

export function rememberSearch(query: string) {
  const value = query.trim();
  if (value.length < 2) return;
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify([value, ...recentSearches().filter(v => v.toLowerCase() !== value.toLowerCase())].slice(0, 6)));
  } catch {
    /* private mode: nothing to remember */
  }
}

const cache = new Map<string, SearchData>();
let meta: Promise<SearchData> | null = null;

/** Topics and suggested queries for the empty state, fetched once. */
function useMeta(enabled: boolean) {
  const [data, setData] = useState<SearchData | null>(null);
  useEffect(() => {
    if (!enabled) return;
    meta ??= getJson<SearchData>('/api/app/search?limit=1');
    meta.then(setData, () => { meta = null; });
  }, [enabled]);
  return data;
}

function useResults(query: string, enabled: boolean) {
  const key = enabled ? query.trim() : '';
  const [data, setData] = useState<SearchData | null>(() => cache.get(key) ?? null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (key.length < 2) { setData(null); setLoading(false); return; }
    const cached = cache.get(key);
    if (cached) { setData(cached); setLoading(false); return; }
    const controller = new AbortController();
    setLoading(true);
    const timer = window.setTimeout(() => {
      getJson<SearchData>(`/api/app/search?limit=40&q=${encodeURIComponent(key)}`, controller.signal)
        .then(result => { cache.set(key, result); setData(result); setLoading(false); })
        .catch(() => { if (!controller.signal.aborted) setLoading(false); });
    }, 110);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [key]);
  return {data: key.length < 2 ? null : data, loading};
}

type Option = {type: 'item'; item: DiscoverItem} | {type: 'all'} | {type: 'query'; query: string} | {type: 'topic'; topic: DiscoverTopic};

function badge(item: DiscoverItem) {
  if (item.state === 'done') return <span className="badge is-done">Пройдено</span>;
  if (item.state === 'locked') return <span className="badge is-club">Клуб</span>;
  if (item.kind === 'coming') return <span className="badge is-coming">Скоро</span>;
  if (item.access === 'free') return <span className="badge is-free">Бесплатно</span>;
  return null;
}

export function SearchBox({variant, onDone, autoFocus, initial = ''}: {variant: 'dialog' | 'inline'; onDone?: () => void; autoFocus?: boolean; initial?: string}) {
  const navigate = useNavigate();
  const [query, setQuery] = useState(initial);
  const [open, setOpen] = useState(variant === 'dialog');
  const [active, setActive] = useState(0);
  const [recent, setRecent] = useState(recentSearches);
  const {data, loading} = useResults(query, open);
  const info = useMeta(open);
  const input = useRef<HTMLInputElement>(null);
  const listId = useId();
  const typed = query.trim().length >= 2;

  // Groups in a fixed order, a few items each; the flat list drives the keyboard.
  const {groups, options} = useMemo(() => {
    const options: Option[] = [];
    const groups: {title: string; start: number; count: number}[] = [];
    if (typed && data) {
      for (const kind of ORDER) {
        const items = data.items.filter(i => i.kind === kind).slice(0, PER_GROUP);
        if (!items.length) continue;
        groups.push({title: GROUP[kind], start: options.length, count: items.length});
        options.push(...items.map(item => ({type: 'item', item}) as Option));
      }
      options.push({type: 'all'});
    } else if (!typed) {
      for (const q of recent) options.push({type: 'query', query: q});
      for (const q of info?.suggestions ?? []) if (!recent.some(r => r.toLowerCase() === q.toLowerCase())) options.push({type: 'query', query: q});
      for (const topic of info?.topics ?? []) options.push({type: 'topic', topic});
    }
    return {groups, options};
  }, [typed, data, recent, info]);

  useEffect(() => { setActive(0); }, [query, data]);
  // The highlighted result's page starts loading, so Enter opens it at once.
  useEffect(() => {
    const option = options[active];
    if (!expanded || option?.type !== 'item') return;
    const timer = window.setTimeout(() => prefetchPage(option.item.url), 150);
    return () => window.clearTimeout(timer);
  });
  useEffect(() => { if (autoFocus) input.current?.focus(); }, [autoFocus]);

  function finish(to: string) {
    rememberSearch(query);
    setRecent(recentSearches());
    setOpen(variant === 'dialog');
    input.current?.blur();
    onDone?.();
    navigate(to);
  }
  function choose(option: Option | undefined) {
    if (!option) return;
    if (option.type === 'item') finish(option.item.url);
    else if (option.type === 'all') finish(`/discover?q=${encodeURIComponent(query.trim())}`);
    else if (option.type === 'topic') finish(`/discover?topic=${option.topic.id}`);
    else { setQuery(option.query); input.current?.focus(); }
  }
  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      setOpen(true);
      if (options.length) setActive(i => (i + (event.key === 'ArrowDown' ? 1 : options.length - 1)) % options.length);
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (typed && (!data || loading)) finish(`/discover?q=${encodeURIComponent(query.trim())}`);
      else choose(options[active]);
    } else if (event.key === 'Escape') {
      if (query && variant === 'inline') { setQuery(''); return; }
      setOpen(false);
      onDone?.();
    }
  }

  const expanded = open && (options.length > 0 || typed);
  const optionId = (i: number) => `${listId}-o${i}`;
  const empty = typed && data && !loading && data.items.length === 0;
  const rows = (from: number, to: number) => options.slice(from, to).map((option, offset) => {
    const i = from + offset;
    const props = {id: optionId(i), role: 'option', 'aria-selected': i === active, onMouseMove: () => setActive(i),
      onMouseDown: (e: React.MouseEvent) => e.preventDefault(), onClick: () => choose(option)} as const;
    if (option.type === 'item') {
      const item = option.item;
      return (
        <li key={i} {...props} className={'search-option' + (i === active ? ' is-active' : '')}>
          <span className="search-thumb"><Cover item={item} /></span>
          <span className="search-text"><strong>{highlight(item.title, data?.stems)}</strong><span>{kicker(item)}{subline(item) ? ` · ${subline(item)}` : ''}</span></span>
          {badge(item)}
        </li>
      );
    }
    if (option.type === 'all') {
      return <li key={i} {...props} className={'search-option search-all' + (i === active ? ' is-active' : '')}>Все результаты{data ? ` · ${data.total}` : ''} <span aria-hidden="true">→</span></li>;
    }
    if (option.type === 'topic') {
      return (
        <li key={i} {...props} className={'search-option search-topic' + (i === active ? ' is-active' : '')}>
          <span className="search-thumb"><Cover topic={option.topic.id} /></span>
          <span className="search-text"><strong>{option.topic.title}</strong><span>{option.topic.subtitle}</span></span>
        </li>
      );
    }
    return <li key={i} {...props} className={'search-chip' + (i === active ? ' is-active' : '')}>{option.query}</li>;
  });

  const recentCount = !typed ? recent.length : 0;
  const suggestionCount = !typed ? options.filter(o => o.type === 'query').length - recentCount : 0;
  return (
    <div className={`search search-${variant}` + (expanded ? ' is-open' : '')}>
      <div className="search-field">
        <svg className="search-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4.5 4.5" /></svg>
        <input ref={input} type="search" role="combobox" aria-expanded={expanded} aria-controls={listId} aria-autocomplete="list"
          aria-activedescendant={expanded && options[active] ? optionId(active) : undefined} aria-label="Поиск по урокам, курсам и материалам"
          placeholder={variant === 'dialog' ? 'Уроки, курсы, инструменты…' : 'Что хотите сделать с ИИ? Например, «видео» или «агент»'}
          value={query} maxLength={120} autoComplete="off" spellCheck={false}
          onChange={e => { setQuery(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)}
          onBlur={() => { if (variant === 'inline') setOpen(false); }} onKeyDown={onKeyDown} />
        {loading && <span className="search-spinner" aria-hidden="true" />}
        {variant === 'dialog' && <kbd className="search-esc">Esc</kbd>}
      </div>
      <div className="search-panel" hidden={!expanded}>
        <ul id={listId} role="listbox" aria-label="Результаты поиска" className="search-list">
          {typed ? (
            <>
              {groups.map(group => (
                <li key={group.title} role="presentation" className="search-group">
                  <span className="search-group-title" aria-hidden="true">{group.title}</span>
                  <ul role="group" aria-label={group.title}>{rows(group.start, group.start + group.count)}</ul>
                </li>
              ))}
              {data && rows(options.length - 1, options.length)}
            </>
          ) : (
            <>
              {recentCount > 0 && <li role="presentation" className="search-group"><span className="search-group-title" aria-hidden="true">Недавние</span><ul role="group" aria-label="Недавние" className="search-chips">{rows(0, recentCount)}</ul></li>}
              {suggestionCount > 0 && <li role="presentation" className="search-group"><span className="search-group-title" aria-hidden="true">Попробуйте</span><ul role="group" aria-label="Попробуйте" className="search-chips">{rows(recentCount, recentCount + suggestionCount)}</ul></li>}
              {info && info.topics.length > 0 && <li role="presentation" className="search-group"><span className="search-group-title" aria-hidden="true">Направления</span><ul role="group" aria-label="Направления" className="search-topics">{rows(recentCount + suggestionCount, options.length)}</ul></li>}
            </>
          )}
        </ul>
        {empty && (
          <p className="search-empty" role="status">
            По запросу «{query.trim()}» ничего нет. Попробуйте короче или другое слово
            {info?.suggestions.length ? <> — например, «{info.suggestions[0]}»</> : null}.
          </p>
        )}
        {typed && data && !empty && <p className="visually-hidden" role="status">Найдено: {data.total} {plural(data.total, 'результат', 'результата', 'результатов')}</p>}
      </div>
    </div>
  );
}

/** The header's search: a modal dialog (top layer, focus kept inside, Esc closes). */
export function SearchDialog({open, onClose}: {open: boolean; onClose: () => void}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = dialog.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);
  return (
    <dialog ref={dialog} className="search-dialog" aria-label="Поиск" onClose={onClose} onCancel={onClose}
      onClick={event => { if (event.target === dialog.current) onClose(); }}>
      {open && <SearchBox variant="dialog" autoFocus onDone={onClose} />}
    </dialog>
  );
}

/** "/" or ⌘K / Ctrl+K opens search, unless the learner is typing somewhere. */
export function useSearchShortcut(open: () => void) {
  useEffect(() => {
    function onKey(event: globalThis.KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing = !!target?.closest?.('input, textarea, select, [contenteditable="true"]');
      if ((event.key === 'k' || event.key === 'K' || event.key === 'л' || event.key === 'Л') && (event.metaKey || event.ctrlKey)) { event.preventDefault(); open(); }
      else if (event.key === '/' && !typing && !event.metaKey && !event.ctrlKey && !event.altKey) { event.preventDefault(); open(); }
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);
}

