// Shapes of /api/app/journey (club/journey.py): the learner's goals, level, deadlines and pace, and the
// path built from them (club/paths.py).

export interface JourneyGoalOption {id: string; title: string; text: string; targets: Record<string, number>}
export interface JourneyOptions {
  skills: {id: string; title: string; text: string}[];
  goals: JourneyGoalOption[];
  sliders: {id: string; title: string}[];
  deadlines: number[];
  max_goals: number;
}
export interface Pace {sessions: number; session_minutes: number}
export interface JourneyAnswers {
  goals?: string[];
  custom?: string;
  beginner?: boolean;
  sliders?: Record<string, number>;
  deadlines?: Record<string, number>;
  pace?: Pace;
  step?: string;
}
export interface PathGoal {
  id: string; title: string; color: string; reach: number; deadline: number | null; lessons: number; modules: string[];
  targets: Record<string, number>;
}
export interface PathLesson {
  key: string; course: string; module: number; module_title: string; title: string; minutes: number;
  gains: Record<string, number>; goals: string[]; lesson_id: string | null; url: string | null; state: string;
  course_title: string | null; topic: string | null;
}
export interface PlanOption {
  id: string; title: string; sessions: number; session_minutes: number; minutes_per_week: number; weeks: number;
  goals: Record<string, {weeks: number | null; on_time: boolean}>;
}
export interface JourneyPath {
  map: {id: string; title: string; courses: {id: string; title: string; modules: number}[]}[];
  goals: PathGoal[];
  lessons: PathLesson[];
  /** guides and use cases beside a module of the path (optional side stops) */
  guides: {id: string; title: string; format: string; minutes: number | null; url: string; module: string; goals: string[]; club: boolean}[];
  /** modules the learner's level says they know, before lessons the path takes («ты, вероятно, уже знаешь») */
  assumed: {key: string; course: string; module: number; title: string; course_title: string | null; lessons: number}[];
  start: Record<string, number>;
  end: Record<string, number>;
  minutes: number;
  coming: number;
  plans: {options: PlanOption[]; needed_minutes_per_week: number | null};
  timeline: number[] | null;
  pace: (Pace & {minutes_per_week: number; weeks: number; reached: Record<string, number>}) | null;
}
export interface JourneyData {options: JourneyOptions; answers: JourneyAnswers; status: 'new' | 'draft' | 'done' | 'skipped'; path: JourneyPath | null}

/** The colours the server gives the chosen goals, in order (club/journey.py COLORS), for screens before a path exists. */
export const GOAL_COLORS = ['#dfff4f', '#8eb8e0', '#d9b88f'];

export const DEADLINE_LABEL: Record<number, string> = {4: 'Месяц', 13: '3 месяца', 26: 'Полгода', 52: 'Год'};

export function weeksLabel(weeks: number | null | undefined) {
  if (weeks == null) return '—';
  if (weeks <= 1) return 'неделя';
  if (weeks < 9) return `${weeks} ${weeks < 5 ? 'недели' : 'недель'}`;
  const months = Math.round(weeks / 4.35);
  return months >= 12 ? (months >= 18 ? `${Math.round(months / 12)} года` : 'год') : `${months} ${months === 1 ? 'месяц' : months < 5 ? 'месяца' : 'месяцев'}`;
}
