// The learner's plan: chosen weekdays and time (club/learning_loop.py). Times are local.
import type {Plan} from './types';
import {plural} from './format';

export const DAYS_SHORT = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс'];   // index = ISO weekday - 1
const DAYS_ON = ['в понедельник', 'во вторник', 'в среду', 'в четверг', 'в пятницу', 'в субботу', 'в воскресенье'];

/** "вт и чт", "пн, ср и пт", "каждый день". */
export function formatDays(days: number[]): string {
  if (days.length === 7) return 'каждый день';
  const names = [...days].sort().map(d => DAYS_SHORT[d - 1]);
  return names.length > 1 ? `${names.slice(0, -1).join(', ')} и ${names[names.length - 1]}` : names[0] ?? '';
}

export function planSummary(plan: Pick<Plan, 'days' | 'time'>, minutes = 20): string {
  const n = plan.days.length;
  if (!n) return 'Без плана — учусь, когда удобно';
  return `${n} ${plural(n, 'занятие', 'занятия', 'занятий')} в неделю · ${formatDays(plan.days)} в ${plan.time} · около ${minutes} минут`;
}

/** The next planned session after `from` (local time), or null without a plan. */
export function nextSession(plan: Pick<Plan, 'days' | 'time'>, from = new Date()): Date | null {
  if (!plan.days.length) return null;
  const [hours, minutes] = plan.time.split(':').map(Number);
  for (let i = 0; i < 8; i++) {
    const day = new Date(from.getFullYear(), from.getMonth(), from.getDate() + i, hours, minutes);
    if (plan.days.includes(day.getDay() || 7) && day > from) return day;
  }
  return null;
}

/** "сегодня в 19:30", "завтра в 19:30", "в четверг, 8 окт, в 19:30". */
export function formatSession(when: Date, now = new Date()): string {
  const time = when.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
  const day = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diff = Math.round((day(when) - day(now)) / 86400000);
  if (diff === 0) return `сегодня в ${time}`;
  if (diff === 1) return `завтра в ${time}`;
  const date = when.toLocaleDateString('ru-RU', {day: 'numeric', month: 'short'}).replace('.', '');
  return `${DAYS_ON[(when.getDay() || 7) - 1]}, ${date}, в ${time}`;
}

const pad = (n: number) => String(n).padStart(2, '0');
const stamp = (d: Date) => `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}T${pad(d.getHours())}${pad(d.getMinutes())}00`;

/** Google Calendar "create event" link: a weekly repeat on the chosen days, in the viewer's time zone. */
export function googleCalendarUrl(plan: Plan): string | null {
  const start = nextSession(plan);
  if (!start) return null;
  const end = new Date(start.getTime() + plan.minutes * 60000);
  const days = plan.days.map(d => ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU'][d - 1]).join(',');
  const link = `${window.location.origin}/continue`;
  const params = new URLSearchParams({
    action: 'TEMPLATE', text: `AI Room: урок (~${plan.minutes} минут)`, dates: `${stamp(start)}/${stamp(end)}`,
    recur: `RRULE:FREQ=WEEKLY;BYDAY=${days}`, details: `Продолжить с того места, где вы остановились: ${link}`,
  });
  return `https://calendar.google.com/calendar/render?${params}`;
}
