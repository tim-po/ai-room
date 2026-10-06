import {humanTime, plural} from '../format';
import {AppLink} from '../links';
import type {Briefing} from '../types';

/** The steps around where the learner stopped: up to two done, then the current one. */
function Recap({briefing}: {briefing: Briefing}) {
  const step = briefing.step;
  if (!step) return null;
  const first = Math.max(1, step.index - 2);
  const items = briefing.steps.slice(first - 1, step.index);
  const left = step.total - step.index;
  return (
    <ol className="briefing-recap" aria-label="Где вы остановились">
      {items.map((title, i) => {
        const index = first + i;
        const current = index === step.index;
        return <li key={index} className={current ? 'is-current' : 'is-done'}><span>{title}{current && <em> ← здесь</em>}</span></li>;
      })}
      {left > 0 && <li className="is-left">ещё {left} {plural(left, 'раздел', 'раздела', 'разделов')}</li>}
    </ol>
  );
}

/** "С возвращением": shown after a break of a few days, on the map and in Моё обучение. */
export function ReturnBriefing({briefing, onHide, className = ''}: {briefing: Briefing; onHide?: () => void; className?: string}) {
  const draft = briefing.status === 'draft';
  const away = briefing.away_days ?? 0;
  const action = draft ? 'Вернуться к черновику →' : briefing.step ? `Продолжить с раздела ${briefing.step.index} →` : 'Продолжить урок →';
  return (
    <section className={`return-briefing ${className}`} aria-labelledby="briefing-title">
      <p className="eyebrow">С возвращением</p>
      <h2 id="briefing-title">{away >= 7 ? 'Давно не виделись — продолжим с того же места' : 'Продолжим с того же места'}</h2>
      <p className="briefing-lesson">
        <strong>{briefing.title}</strong>
        <span>{briefing.course} · {briefing.minutes} мин{away ? ` · вас не было ${away} ${plural(away, 'день', 'дня', 'дней')}` : ''}</span>
      </p>
      {draft && briefing.practice
        ? <blockquote className="briefing-draft"><span className="small">Ваш черновик · {humanTime(briefing.practice.updated_at)}</span>{briefing.practice.excerpt}</blockquote>
        : <Recap briefing={briefing} />}
      <div className="actions">
        <AppLink className="button" to={briefing.url}>{action}</AppLink>
        {onHide && <button type="button" className="link-button" onClick={onHide}>Скрыть</button>}
      </div>
    </section>
  );
}

/** One line for the compact "Продолжить" strip: lesson title plus the section reached. */
export function stepLabel(briefing: Briefing | null) {
  return briefing?.step && briefing.status !== 'draft' ? `раздел ${briefing.step.index} из ${briefing.step.total}` : '';
}
