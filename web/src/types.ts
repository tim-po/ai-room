// Shapes returned by /api/app/* (see club/__init__.py: home_data, lesson_data, profile_data).

export type LessonState = 'done' | 'progress' | 'open' | 'locked' | 'coming';

export interface TreeLesson {
  id: string | null;
  title: string;
  state: LessonState;
  minutes?: number;
  url?: string;
  current?: boolean;
}

export interface TreeModule {
  title: string;
  state: 'done' | 'active' | 'coming';
  lessons: TreeLesson[];
}

export interface TreeCourse {
  id: string;
  title: string;
  level: string;
  url: string | null;
  modules: TreeModule[];
  total: number;
  done: number;
  available: number;
  next: {title: string; url: string} | null;
  current: boolean;
  topic?: string;
}

export interface TreeTopic {
  id: string;
  title: string;
  subtitle: string;
  interest: boolean;
  courses: TreeCourse[];
}

export interface Unfinished {
  lesson_id: string;
  title: string;
  url: string;
  status: 'draft' | 'in_progress';
}

export interface Continuation {
  version: string;
  unfinished: Unfinished | null;
  last_result: (Unfinished & {status: 'submitted' | 'completed'}) | null;
}

/** The learner's chosen days (ISO weekday 1 = Monday) and time; no days = no plan. */
export interface Plan {
  days: number[];
  time: string;
  minutes: number;
}

/** Where the learner stopped (club/learning_loop.py briefing); `returning` after a break of 3+ days. */
export interface Briefing {
  lesson_id: string;
  title: string;
  course: string;
  status: 'draft' | 'in_progress';
  url: string;
  step: {index: number; total: number; title: string} | null;
  steps: string[];
  minutes: number;
  away_days: number | null;
  returning: boolean;
  practice: {excerpt: string; status: 'draft' | 'submitted'; updated_at: string} | null;
}

export interface HomeData {
  tree: {topics: TreeTopic[]};
  continuation: Continuation;
  briefing: Briefing | null;
  next: {id: string; title: string; url: string} | null;
  free_lessons: (TreeLesson & {course: string; topic: string})[];
}

export interface LessonInfo {
  id: string;
  title: string;
  objective: string;
  minutes: number;
  access: 'free' | 'member';
  steps: string[];
  body_html?: string | null;
  paragraphs?: string[] | null;
  prompt?: string | null;
  task?: string | null;
  checklist?: string[];
  video?: {url: string; type: string; fixture: boolean} | null;
}

export interface Neighbour {
  id: string;
  title: string;
  locked: boolean;
  minutes: number;
  objective: string;
}

export interface Practice {
  body: string;
  status: 'draft' | 'submitted';
  updated_at: string;
}

export interface LessonData {
  locked: boolean;
  lesson: LessonInfo;
  course: {id: string; title: string};
  outline: TreeCourse | null;
  // open lessons
  resources?: {id: string; title: string; kind: 'text' | 'link'; url: string}[];
  progress?: {completed: number; video_seconds: number} | null;
  practice?: Practice | null;
  previous?: Neighbour | null;
  following?: Neighbour | null;
  /** Section titles (the lesson's h2 steps) plus "Практика" when there is a task. */
  checkpoints?: string[];
  step_progress?: {furthest: number; last: number; updated_at: string} | null;
  plan?: Plan | null;
  // locked lessons
  entitlement?: string | null;
  free_lesson?: {id: string; title: string} | null;
}

export interface CourseProgress {
  id: string;
  title: string;
  done: number;
  total: number;
  next: {id: string; title: string} | null;
  next_locked: {id: string; title: string} | null;
}

export interface ProfileData {
  user: {name: string; email: string; entitlement: string; weekly_goal: number};
  continuation: Continuation;
  briefing: Briefing | null;
  plan: Plan;
  weekly: number;
  practices: (Practice & {lesson_id: string; title: string; course_id: string})[];
  active_courses: CourseProgress[];
  completed_courses: CourseProgress[];
  favourites: {id: string; title: string}[];
  material_favourites: {id: string; title: string}[];
}

// Library (/api/app/catalogue)
export interface CourseCard {
  id: string;
  title: string;
  description: string;
  goal: string;
  level: string;
  topic: string;
  total: number;
  catalog_total: number;
  minutes: number;
  free: number;
  done: number;
}

export interface MaterialCard {
  id: string;
  title: string;
  description: string;
  outcome: string;
  format: string;
  goal: string;
  level: string;
  tools: string;
  minutes: number;
  access: 'free' | 'member';
}

export interface ComingCourse {
  id: string;
  title: string;
  topic: string;
  level: string;
  modules: number;
  total: number | null;
}

export interface CatalogueData {
  courses: CourseCard[];
  materials: MaterialCard[];
  coming: ComingCourse[];
  filters: {goals: [string, string][]; levels: string[]; formats: [string, string][]};
}

// Course page (/api/app/courses/<id>)
export interface CourseLesson {
  id: string;
  title: string;
  minutes: number;
  access: 'free' | 'member';
  video: boolean;
  module_id: string;
  module_title: string;
  completed: boolean;
  locked: boolean;
}

export interface CourseData {
  course: {id: string; title: string; outcome: string; level: string; goal: string; topic: string;
    prerequisites: string; tools: string; author: string; updated_at: string};
  lessons: CourseLesson[];
  first: {id: string; title: string} | null;
  started: boolean;
  favourite: boolean;
  outline: TreeCourse | null;
  done: number;
  minutes: number;
}

// Material page (/api/app/materials/<id>)
export interface MaterialInfo {
  id: string;
  title: string;
  description: string;
  outcome: string;
  format: string;
  format_label: string;
  level: string;
  minutes: number;
  access: 'free' | 'member';
  tools: string;
  prerequisites: string;
  author: string;
  updated_at: string;
  paragraphs?: string[];
  prompt?: string | null;
  video?: {url: string; type: string; fixture: boolean} | null;
}

export interface MaterialData {
  locked: boolean;
  item: MaterialInfo;
  resources?: {id: string; title: string; kind: 'text' | 'link'; url: string}[];
  favourite?: boolean;
  seconds?: number;
}

export interface MembershipData {
  member_lessons: number;
  free_lessons: number;
  demo: boolean;
  return_to: string;
}

export interface PreferencesData {
  goal: string;
  experience: 'beginner' | 'experienced';
  weekly_goal: number;
  plan: Plan;
}

export interface HelpTicket {
  id: number;
  body: string;
  created_at: string;
  status: 'open' | 'handled' | string;
  response: string | null;
  handled_at: string | null;
}

export interface HelpData {
  lesson: {id: string; title: string} | null;
  tickets: HelpTicket[];
}

// Onboarding (/api/onboarding, club/onboarding.py)
export type OnboardingStep = 'welcome' | 'interests' | 'pace' | 'start';

export interface OnboardingPrefs {
  interests: string[];
  experience: 'beginner' | 'experienced' | null;
  available_minutes: 5 | 10 | 20 | null;
  diagnostic_choice: 'unset' | 'skip' | 'start';
}

export interface OnboardingState {
  status: 'not_started' | 'in_progress' | 'completed' | 'skipped';
  step: OnboardingStep;
  draft: OnboardingPrefs;
  committed_preferences: OnboardingPrefs;
  revision: number;
  return_to: string;
  editing: boolean;
  next_url: string | null;
  recommendation: {lesson_id: string; title: string; url: string; minutes: number; branch: string | null; reasons: string[]} | null;
  diagnostic: {available: boolean; start_url: string | null};
}
