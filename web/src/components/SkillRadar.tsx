// The eight skills as a radar: each goal is a coloured shape reaching the points it needs (0–100), and
// «сейчас» — where the learner is — a filled shape inside. Shapes grow out of the centre when they appear.

const SIZE = 360, C = SIZE / 2, R = 128, SIDE = 92;
const point = (i: number, n: number, value: number): [number, number] => {
  const angle = -Math.PI / 2 + (i / n) * Math.PI * 2;
  return [C + Math.cos(angle) * R * value / 100, C + Math.sin(angle) * R * value / 100];
};
const shape = (values: number[]) => values.map((v, i) => point(i, values.length, Math.max(4, v)).join(',')).join(' ');

export default function SkillRadar({skills, goals, start, label, focus}: {
  skills: {id: string; title: string}[];
  goals: {id: string; color: string; targets: Record<string, number>}[];
  start?: Record<string, number>;
  label: string;
  /** one goal brought forward (Главная): the others fade, its points get dots */
  focus?: string | null;
}) {
  const n = skills.length;
  const needed = new Set(goals.flatMap(g => Object.keys(g.targets)));
  return (
    <svg className="skill-radar" viewBox={`${-SIDE} -14 ${SIZE + 2 * SIDE} ${SIZE + 28}`} role="img" aria-label={label}>
      {[25, 50, 75, 100].map(ring => <polygon key={ring} className="skill-radar-ring" points={shape(skills.map(() => ring))} />)}
      {skills.map((_, i) => { const [x, y] = point(i, n, 100); return <line key={i} className="skill-radar-axis" x1={C} y1={C} x2={x} y2={y} />; })}
      {goals.map((goal, gi) => (
        <g key={goal.id} className={'skill-radar-goal' + (focus && focus !== goal.id ? ' is-dim' : '')} style={{animationDelay: `${0.2 + gi * 0.35}s`, color: goal.color}}>
          <polygon className="skill-radar-casing" points={shape(skills.map(s => goal.targets[s.id] ?? 0))} />
          <polygon points={shape(skills.map(s => goal.targets[s.id] ?? 0))} />
          {focus === goal.id && skills.map((s, i) => goal.targets[s.id] ? <circle key={s.id} className="skill-radar-dot" r={5} cx={point(i, n, goal.targets[s.id])[0]} cy={point(i, n, goal.targets[s.id])[1]} /> : null)}
        </g>
      ))}
      {start && Object.values(start).some(Boolean) && (
        <polygon className="skill-radar-now" points={shape(skills.map(s => start[s.id] ?? 0))} />
      )}
      {skills.map((skill, i) => {
        const angle = -Math.PI / 2 + (i / n) * Math.PI * 2;
        const x = C + Math.cos(angle) * (R + 16), y = C + Math.sin(angle) * (R + 16);
        const anchor = Math.abs(Math.cos(angle)) < 0.2 ? 'middle' : Math.cos(angle) > 0 ? 'start' : 'end';
        const words = skill.title.split(' ');
        const lines = words.length > 1 && skill.title.length > 12 ? [words.slice(0, Math.ceil(words.length / 2)).join(' '), words.slice(Math.ceil(words.length / 2)).join(' ')] : [skill.title];
        const dy = Math.sin(angle) < -0.5 ? -(lines.length - 1) * 15 : Math.sin(angle) > 0.5 ? 12 : 4 - (lines.length - 1) * 7;
        return (
          <text key={skill.id} className={'skill-radar-label' + (needed.has(skill.id) ? ' is-needed' : '')} x={x} y={y + dy} textAnchor={anchor}>
            <title>{`${skill.title}: сейчас ${Math.round(start?.[skill.id] ?? 0)}${goals.some(g => g.targets[skill.id]) ? `, нужно до ${Math.max(...goals.map(g => g.targets[skill.id] ?? 0))}` : ''}`}</title>
            {lines.map((line, li) => <tspan key={li} x={x} dy={li ? '1.15em' : 0}>{line}</tspan>)}
          </text>
        );
      })}
    </svg>
  );
}
