import {createContext, useContext} from 'react';

// «Для цели …»: anything on the learner's path (a course, a lesson, a guide) carries the colour dots of the
// goals it serves, wherever it is listed. The page provides the learner's goals (club/journey.py alignment).

export interface GoalMark {id: string; title: string; color: string}
export const GoalsContext = createContext<GoalMark[]>([]);

export default function GoalMarks({ids, compact = false}: {ids?: string[]; compact?: boolean}) {
  const all = useContext(GoalsContext);
  const goals = (ids ?? []).map(id => all.find(g => g.id === id)).filter((g): g is GoalMark => !!g);
  if (!goals.length) return null;
  const label = `Для ${goals.length === 1 ? 'цели' : 'целей'}: ${goals.map(g => g.title).join(', ')}`;
  return (
    <span className={'goal-marks' + (compact ? ' is-compact' : '')} title={label}>
      <span className="goal-marks-dots" aria-hidden="true">{goals.map(g => <i key={g.id} style={{background: g.color}} />)}</span>
      <span className={compact ? 'visually-hidden' : undefined}>{goals.length === 1 ? `для цели «${goals[0].title}»` : `для ${goals.length} целей`}</span>
    </span>
  );
}
