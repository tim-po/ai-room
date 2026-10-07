// Russian plurals and human dates ("сегодня в 14:05", "вчера в 09:30", "3 окт в 18:00").

export function plural(n: number, one: string, few: string, many: string): string {
  const a = Math.abs(n) % 100, b = a % 10;
  if (a >= 11 && a <= 14) return many;
  if (b === 1) return one;
  if (b >= 2 && b <= 4) return few;
  return many;
}

/** Server timestamps are UTC "YYYY-MM-DD HH:MM:SS". */
export function humanTime(value: string): string {
  const moment = new Date(value.replace(' ', 'T').slice(0, 19) + 'Z');
  if (Number.isNaN(moment.getTime())) return value;
  const time = moment.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
  const day = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diff = Math.round((day(new Date()) - day(moment)) / 86400000);
  if (diff === 0) return `сегодня в ${time}`;
  if (diff === 1) return `вчера в ${time}`;
  const sameYear = moment.getFullYear() === new Date().getFullYear();
  const date = moment.toLocaleDateString('ru-RU', {day: 'numeric', month: 'short', year: sameYear ? undefined : 'numeric'});
  return `${date.replace('.', '')} в ${time}`;
}
