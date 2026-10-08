import {cloneElement, useEffect, useId, useLayoutEffect, useRef, useState, type ReactElement, type ReactNode} from 'react';
import {useBlocker} from 'react-router';
import {ApiError} from '../api';
import Select, {type Option} from '../components/Select';
import type {Choice, Source, Status} from './types';

export const STATUS_LABEL: Record<string, string> = {draft: 'Черновик', published: 'Опубликован', archived: 'Архив'};
export const ACCESS_LABEL: Record<string, string> = {free: 'Бесплатно', member: 'Для участников'};
export const ACCESS: readonly Option[] = [['free', 'Бесплатно'], ['member', 'Участникам клуба']];
const MAC = /Mac|iPhone|iPad/.test(navigator.platform);

export function StatusBadge({status}: {status: Status | string}) {
  return <span className={`adm-badge is-${status}`}>{STATUS_LABEL[status] ?? status}</span>;
}

export function Badge({children, tone}: {children: ReactNode; tone?: 'accent' | 'gold' | 'muted'}) {
  return <span className={'adm-badge' + (tone ? ` is-${tone}` : '')}>{children}</span>;
}

export function PageHead({eyebrow, title, children, actions}: {eyebrow?: ReactNode; title: ReactNode; children?: ReactNode; actions?: ReactNode}) {
  return (
    <div className="adm-head">
      <div>
        {eyebrow && <p className="adm-eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {children && <div className="adm-head-sub">{children}</div>}
      </div>
      {actions && <div className="adm-head-actions">{actions}</div>}
    </div>
  );
}

/**
 * An editor's head: where the item sits, then its name as the page's big title, edited in place
 * (one line; long names wrap). It is the form's «Название» field, so there is no second title box.
 */
export function EditorHead({crumbs, title, onTitle, placeholder}: {crumbs: ReactNode; title: string; onTitle: (value: string) => void; placeholder: string}) {
  // Something new starts with its name: the cursor is already there.
  const fresh = useRef(!title);
  const box = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {
    const el = box.current;
    if (!el || CSS.supports('field-sizing', 'content')) return;
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  }, [title]);
  return (
    <div className="adm-head is-editor">
      <nav className="adm-crumbs" aria-label="Где это">{crumbs}</nav>
      <h1 className="adm-title">
        <textarea ref={box} rows={1} value={title} placeholder={placeholder} aria-label="Название" maxLength={200} spellCheck autoFocus={fresh.current}
          onChange={e => onTitle(e.target.value.replace(/\s*\n\s*/g, ' '))}
          onKeyDown={e => { if (e.key === 'Enter') e.preventDefault(); }} />
      </h1>
    </div>
  );
}

export type MenuItem = {label: string; href?: string; onSelect?: () => void; tone?: 'danger'} | false | null | undefined;

/** «⋯»: the actions an item needs now and then (open as learner, take down, archive), out of the way. */
export function Menu({items, label = 'Ещё действия'}: {items: MenuItem[]; label?: string}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const shown = items.filter(Boolean) as Exclude<MenuItem, false | null | undefined>[];
  useEffect(() => {
    if (!open) return;
    const close = (event: Event) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    const key = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setOpen(false); root.current?.querySelector('button')?.focus(); }
    };
    document.addEventListener('pointerdown', close);
    document.addEventListener('keydown', key);
    root.current?.querySelector<HTMLElement>('[role=menuitem]')?.focus();
    return () => { document.removeEventListener('pointerdown', close); document.removeEventListener('keydown', key); };
  }, [open]);
  if (!shown.length) return null;
  function move(event: React.KeyboardEvent) {
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
    event.preventDefault();
    const list = [...(root.current?.querySelectorAll<HTMLElement>('[role=menuitem]') ?? [])];
    const at = list.indexOf(document.activeElement as HTMLElement);
    list[(at + (event.key === 'ArrowDown' ? 1 : -1) + list.length) % list.length]?.focus();
  }
  return (
    <div className="adm-menu" ref={root}>
      <button type="button" className="button secondary adm-menu-button" aria-haspopup="menu" aria-expanded={open} aria-label={label} title={label}
        onClick={() => setOpen(o => !o)}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5" cy="12" r="1.8" /><circle cx="12" cy="12" r="1.8" /><circle cx="19" cy="12" r="1.8" /></svg>
      </button>
      {open && (
        <div className="adm-menu-list" role="menu" aria-label={label} onKeyDown={move}>
          {shown.map(item => item.href
            ? <a key={item.label} role="menuitem" href={item.href} target="_blank" rel="noreferrer" onClick={() => setOpen(false)}>{item.label} <span aria-hidden="true">↗</span></a>
            : <button key={item.label} type="button" role="menuitem" className={item.tone === 'danger' ? 'is-danger' : undefined}
                onClick={() => { setOpen(false); item.onSelect?.(); }}>{item.label}</button>)}
        </div>
      )}
    </div>
  );
}

/** Quiet facts about an item (who uses it, where it comes from), at the end of its settings. */
export function Facts({items}: {items: ReactNode[]}) {
  const shown = items.filter(Boolean);
  if (!shown.length) return null;
  return <ul className="adm-facts">{shown.map((item, i) => <li key={i}>{item}</li>)}</ul>;
}

/** «Убрать» on an optional part (prompt, practice, links): clears what it holds, after asking if it holds anything. */
export function RemovePart({label, filled, onRemove}: {label: string; filled: boolean; onRemove: () => void}) {
  return (
    <button type="button" className="adm-remove" aria-label={`Убрать: ${label}`}
      onClick={() => { if (!filled || window.confirm(`Убрать «${label}»? Текст из этого блока пропадёт после сохранения.`)) onRemove(); }}>
      Убрать
    </button>
  );
}

/** The «⋯» menu entry that brings an imported item back to its file version. */
export function restoreItem(source: Source, noun: string, onRestore: () => Promise<void>): MenuItem {
  return source === 'edited' && {label: 'Вернуть версию из файлов', onSelect: () => {
    if (window.confirm(`Вернуть ${noun} к версии из файлов? Правки, сделанные здесь, пропадут.`)) void onRestore();
  }};
}

/** The «⋯» menu entry that archives an item. */
export function archiveItem(status: Status | null, noun: string, onArchive: () => void): MenuItem {
  return status !== null && status !== 'archived' && {label: 'В архив', tone: 'danger', onSelect: () => {
    if (window.confirm(`Убрать ${noun} в архив? Ученики перестанут его видеть, прогресс сохранится.`)) onArchive();
  }};
}

export function Stat({value, label, hint, tone}: {value: ReactNode; label: string; hint?: ReactNode; tone?: 'accent' | 'gold'}) {
  return (
    <div className={'adm-stat' + (tone ? ` is-${tone}` : '')}>
      <strong>{value}</strong>
      <span>{label}</span>
      {hint && <small>{hint}</small>}
    </div>
  );
}

export function Empty({children}: {children: ReactNode}) {
  return <p className="adm-empty">{children}</p>;
}

/** A labelled control. The hint is a description (aria-describedby), not part of the label, so the name stays short. */
export function Field({label, hint, children, wide}: {label: string; hint?: ReactNode; children: ReactElement<{id?: string; 'aria-describedby'?: string}>; wide?: boolean}) {
  const id = useId();
  return (
    <div className={'adm-field' + (wide ? ' is-wide' : '')}>
      <label className="adm-label" htmlFor={id}>{label}</label>
      {cloneElement(children, {id, 'aria-describedby': hint ? id + '-hint' : undefined})}
      {hint && <span className="adm-hint" id={id + '-hint'}>{hint}</span>}
    </div>
  );
}

export function TextField({label, value, onChange, hint, max, multiline, rows, wide, mono, placeholder, big}: {
  label: string; value: string; onChange: (value: string) => void; hint?: ReactNode; max?: number; multiline?: boolean;
  rows?: number; wide?: boolean; mono?: boolean; placeholder?: string; big?: boolean;
}) {
  const counter = max && value.length > max * 0.8 ? <span className={'adm-count' + (value.length > max ? ' is-over' : '')}>{value.length} / {max}</span> : null;
  return (
    <Field label={label} wide={wide} hint={hint || counter ? <>{hint}{counter}</> : undefined}>
      {multiline
        ? <textarea value={value} rows={rows ?? 3} placeholder={placeholder} className={mono ? 'is-mono' : undefined} onChange={e => onChange(e.target.value)} />
        : <input value={value} placeholder={placeholder} className={big ? 'is-big' : undefined} onChange={e => onChange(e.target.value)} />}
    </Field>
  );
}

export function ChoiceField({label, value, options, onChange}: {label: string; value: string; options: readonly Option[]; onChange: (v: string) => void}) {
  return <div className="adm-field"><Select label={label} value={value} options={options} onChange={onChange} /></div>;
}

export const choices = (list: Choice[]): Option[] => list.map(c => [c.id, c.label] as const);

/** Segmented control for two or three values (access, format, level). */
export function Segmented({label, value, options, onChange, disabled}: {label: string; value: string; options: readonly Option[]; onChange: (v: string) => void; disabled?: boolean}) {
  return (
    <fieldset className="adm-segmented" disabled={disabled}>
      <legend className="adm-label">{label}</legend>
      <div role="radiogroup" aria-label={label}>
        {options.map(([v, text]) => (
          <button type="button" key={v} role="radio" aria-checked={v === value} className={v === value ? 'is-on' : undefined} onClick={() => onChange(v)}>{text}</button>
        ))}
      </div>
    </fieldset>
  );
}

/** Rarely changed fields, folded away; the summary shows what they hold now. */
export function More({summary, children}: {summary: ReactNode; children: ReactNode}) {
  return (
    <details className="adm-more">
      <summary><span>Подробнее</span><small>{summary}</small></summary>
      <div className="adm-more-body">{children}</div>
    </details>
  );
}

/** "+ Промпт", "+ Практика" … : optional parts appear only once they're wanted (or already filled). */
export function AddOns({items}: {items: {label: string; shown: boolean; show: () => void}[]}) {
  const hidden = items.filter(i => !i.shown);
  if (!hidden.length) return null;
  return (
    <div className="adm-addons" role="group" aria-label="Добавить">
      <span className="adm-muted">Добавить:</span>
      {hidden.map(i => <button type="button" key={i.label} className="adm-chip" onClick={i.show}>+ {i.label}</button>)}
    </div>
  );
}

/** Reading time the server would use when no duration is given (club/admin.py estimate). */
export function estimate(body: string, task = '') {
  const words = (body.replace(/!?\[[^\]]*\]\([^)]*\)|@video \S+/g, ' ').match(/[\p{L}\p{N}_]+/gu) || []).length;
  return Math.max(1, Math.min(600, Math.floor(words / 180 + 0.5) + (task ? 5 : 0)));
}

/** Duration: estimated from the text unless the editor sets it. '' means "estimate". */
export function Duration({value, onChange, auto, empty}: {value: string; onChange: (v: string) => void; auto: number; empty?: boolean}) {
  const [manual, setManual] = useState(value !== '');
  if (!manual) {
    return (
      <div className="adm-field">
        <span className="adm-label">Длительность</span>
        <p className="adm-duration">{empty ? <small>посчитается по объёму текста</small> : <>≈ {auto} мин <small>по объёму текста</small></>}
          <button type="button" className="adm-link" onClick={() => { setManual(true); onChange(String(auto)); }}>указать</button></p>
      </div>
    );
  }
  return (
    <Field label="Длительность, мин" hint={<button type="button" className="adm-link" onClick={() => { setManual(false); onChange(''); }}>считать по тексту</button>}>
      <input type="number" min={1} max={600} value={value} onChange={e => onChange(e.target.value)} />
    </Field>
  );
}

/** A form's local copy of server data, with "unsaved changes" tracking and a guard on leaving. */
export function useDraft<T extends object>(initial: T) {
  const [saved, setSaved] = useState(initial);
  const [draft, setDraft] = useState(initial);
  const dirty = JSON.stringify(saved) !== JSON.stringify(draft);
  const set = <K extends keyof T>(key: K) => (value: T[K]) => setDraft(d => ({...d, [key]: value}));
  const reset = (value: T) => { setSaved(value); setDraft(value); };
  const blocker = useBlocker(({currentLocation, nextLocation}) => dirty && currentLocation.pathname !== nextLocation.pathname);
  useEffect(() => {
    if (blocker.state === 'blocked') {
      if (window.confirm('Есть несохранённые изменения. Уйти без сохранения?')) blocker.proceed(); else blocker.reset();
    }
  }, [blocker]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);
  return {draft, set, setDraft, dirty, reset: (value: T) => reset(value), revert: () => setDraft(saved)};
}

export type SaveState = {state: 'idle' | 'saving' | 'saved' | 'error'; message?: string};

/** Runs a save (optionally moving to a new status), keeping a status the bar shows; ⌘S / Ctrl S saves too. */
export function useSave(run: (status?: Status) => Promise<void>, enabled: boolean) {
  const [state, setState] = useState<SaveState>({state: 'idle'});
  const latest = useRef(run);
  latest.current = run;
  async function save(status?: Status) {
    setState({state: 'saving'});
    try {
      await latest.current(status);
      setState({state: 'saved'});
    } catch (error) {
      setState({state: 'error', message: error instanceof ApiError ? error.message : 'Не удалось сохранить. Повторите.'});
    }
  }
  const saveRef = useRef(save);
  saveRef.current = save;
  useEffect(() => {
    if (!enabled) return;
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        void saveRef.current();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [enabled]);
  return {state, save};
}

/**
 * The editor's one place for saving and publishing. Status is an action here, not a form field:
 * a draft is saved or published, a published item is saved or taken down, an archived one restored.
 * `missing` lists what publishing still needs, so the reason a button is disabled is always on screen.
 */
export function PublishBar({current, dirty, state, missing, onSave, onRevert, noun, menu = []}: {
  current: Status | null; dirty: boolean; state: SaveState; missing: string[];
  onSave: (status?: Status) => void; onRevert?: () => void; noun: string; menu?: MenuItem[];
}) {
  const busy = state.state === 'saving';
  const kbd = <kbd aria-hidden="true">{MAC ? '⌘S' : 'Ctrl S'}</kbd>;
  const text = busy ? 'Сохраняю…'
    : state.state === 'error' ? state.message
    : current === null ? 'Черновик можно сохранить с одним названием — остальное позже.'
    : dirty ? 'Есть несохранённые изменения'
    : (state.state === 'saved' ? 'Сохранено. ' : '') + (
      current === 'draft' && missing.length ? `Для публикации не хватает: ${missing.join(', ')}`
      : current === 'published' ? 'Опубликован — ученики видят эту версию'
      : current === 'archived' ? 'В архиве — ученики не видят'
      : 'Черновик — ученики пока не видят');
  return (
    <div className={'adm-savebar' + (dirty ? ' is-dirty' : '') + (state.state === 'error' ? ' is-error' : '')}>
      <p role="status">{text}</p>
      <div>
        {current !== null && <Menu items={[
          dirty && onRevert && {label: 'Отменить несохранённые правки', onSelect: onRevert},
          ...menu.filter(item => !item || item.tone !== 'danger'),
          current === 'published' && {label: 'Снять с публикации', onSelect: () => onSave('draft')},
          ...menu.filter(item => item && item.tone === 'danger'),
        ]} />}
        {current === null && <button type="button" className="button" disabled={busy} onClick={() => onSave('draft')}>Создать {noun}{kbd}</button>}
        {current === 'draft' && <>
          <button type="button" className="button secondary" disabled={busy || !dirty} onClick={() => onSave()}>Сохранить{kbd}</button>
          <button type="button" className="button" disabled={busy || missing.length > 0} title={missing.length ? `Не хватает: ${missing.join(', ')}` : undefined}
            onClick={() => onSave('published')}>Опубликовать</button>
        </>}
        {current === 'published' && <button type="button" className="button" disabled={busy || !dirty} onClick={() => onSave()}>Сохранить{kbd}</button>}
        {current === 'archived' && <button type="button" className="button" disabled={busy} onClick={() => onSave('draft')}>Вернуть в черновики</button>}
      </div>
    </div>
  );
}

/** Small marker in lists. */
export function SourceMark({source}: {source: Source}) {
  if (!source) return null;
  return source === 'edited'
    ? <span className="adm-source-mark is-edited" title="Из файлов контента, изменён в админке">изменён</span>
    : <span className="adm-source-mark" title="Из файлов контента">из файлов</span>;
}

/** Small inline bar chart for daily counts. */
export function Bars({values, labels, height = 64}: {values: number[]; labels?: string[]; height?: number}) {
  const top = Math.max(1, ...values);
  return (
    <div className="adm-bars" style={{height}}>
      {values.map((v, i) => (
        <span key={i} title={labels ? `${labels[i]}: ${v}` : String(v)} style={{height: `${Math.max(v ? 8 : 3, (v / top) * 100)}%`}} className={v ? undefined : 'is-zero'} />
      ))}
    </div>
  );
}

export const shortDate = (value: string) =>
  new Date(value.slice(0, 10) + 'T00:00:00').toLocaleDateString('ru-RU', {day: 'numeric', month: 'short'}).replace('.', '');
