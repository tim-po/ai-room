import {useEffect, useRef, useState} from 'react';
import {ApiError, putJson} from '../api';
import {DAYS_SHORT, googleCalendarUrl, planSummary} from '../plan';
import type {Plan} from '../types';
import Select from './Select';

const TIMES = Array.from({length: 36}, (_, i) => {
  const minutes = 6 * 60 + i * 30;   // 06:00 … 23:30
  const value = `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;
  return [value, value] as const;
});

/** "Add to calendar": a weekly event whose link (/continue) opens wherever the learner stopped. */
export function CalendarLinks({plan}: {plan: Plan}) {
  const google = googleCalendarUrl(plan);
  if (!google) return null;
  return (
    <div className="calendar-links">
      <span className="small">Добавить в календарь:</span>
      <a className="button secondary" href={google} target="_blank" rel="noopener noreferrer">Google Календарь ↗</a>
      <a className="button secondary" href="/plan.ics" download>Apple, Яндекс, Outlook (.ics)</a>
    </div>
  );
}

/** Choose study days and a time. The plan is the weekly goal with days attached (no days = no plan). */
export default function PlanEditor({initial, onSaved, compact = false}: {initial: Plan; onSaved?: (plan: Plan) => void; compact?: boolean}) {
  const [saved, setSaved] = useState(initial);
  const [days, setDays] = useState(initial.days);
  const [time, setTime] = useState(initial.time);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{kind: 'success' | 'error'; text: string} | null>(null);
  const dirty = days.join() !== saved.days.join() || time !== saved.time;
  const calendar = useRef<HTMLDivElement>(null);
  const [justSaved, setJustSaved] = useState(false);
  // Right after saving, the calendar buttons are the next step: bring them into view.
  useEffect(() => {
    if (justSaved) calendar.current?.scrollIntoView({block: 'nearest', behavior: 'smooth'});
  }, [justSaved]);

  function toggle(day: number) {
    setDays(current => (current.includes(day) ? current.filter(d => d !== day) : [...current, day].sort()));
    setMessage(null); setJustSaved(false);
  }
  async function save() {
    setBusy(true); setMessage(null);
    try {
      const plan = await putJson<Plan>('/api/app/plan', {days, time});
      setSaved(plan); setDays(plan.days); setTime(plan.time);
      setMessage({kind: 'success', text: plan.days.length ? 'План закреплён. Добавьте занятия в календарь — так проще не забыть.' : 'План снят. Учитесь, когда удобно.'});
      setJustSaved(plan.days.length > 0);
      onSaved?.(plan);
    } catch (e) {
      setMessage({kind: 'error', text: e instanceof ApiError ? e.message : 'Не удалось сохранить план.'});
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={'plan-editor' + (compact ? ' is-compact' : '')}>
      <fieldset className="plan-days">
        <legend>Дни занятий</legend>
        <div className="plan-day-row">
          {DAYS_SHORT.map((name, i) => (
            <button key={name} type="button" className="plan-day" aria-pressed={days.includes(i + 1)} onClick={() => toggle(i + 1)}>{name}</button>
          ))}
        </div>
      </fieldset>
      <Select label="Время" value={time} options={TIMES} onChange={value => { setTime(value); setMessage(null); }} />
      <p className="plan-summary">{planSummary({days, time}, saved.minutes)}</p>
      {!(compact && !dirty && saved.days.length) && (
        <div className="actions">
          <button type="button" className="button" disabled={busy || !dirty} onClick={save}>
            {busy ? 'Сохраняем…' : !days.length && saved.days.length ? 'Снять план' : 'Закрепить план'}
          </button>
        </div>
      )}
      {message && (compact
        ? <p className={message.kind === 'error' ? 'small plan-error' : 'small'} role="status">{message.kind === 'success' && saved.days.length ? 'План закреплён.' : message.text}</p>
        : <p className={`notice ${message.kind}`} role="status">{message.text}</p>)}
      {!dirty && saved.days.length > 0 && <div ref={calendar}><CalendarLinks plan={saved} /></div>}
    </div>
  );
}
