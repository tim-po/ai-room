// Shapes of the /api/admin/* responses (club/admin.py).

export type Status = 'draft' | 'published' | 'archived';
export type Access = 'free' | 'member';
/** null: made in the admin; 'files': installed from the repository, untouched; 'edited': installed, then changed here. */
export type Source = null | 'files' | 'edited';

export interface Choice {id: string; label: string}
export interface Options {
  goals: Choice[];
  levels: string[];
  statuses: Choice[];
  formats: Choice[];
  media: string[];
}

export interface FeedItem {
  id: number;
  name: string;
  action: string;
  created_at: string;
  user_id?: string;
  user_name?: string;
  lesson_id: string | null;
  lesson_title: string | null;
}

export interface Question {
  id: number;
  body: string;
  created_at: string;
  status: 'open' | 'handled' | string;
  user_id: string;
  user_name: string;
  entitlement: string;
  lesson_id: string | null;
  lesson_title: string | null;
  response: string | null;
  handled_at: string | null;
  revision: number;
}

export interface Overview {
  role: 'editor' | 'admin';
  assistant?: import('./Assistant').AssistantData;
  counts: {learners: number; members: number; active_week: number; completions_week: number; open_questions: number; works_waiting: number; drafts: number};
  activity: {day: string; learners: number}[];
  feed: FeedItem[];
  popular: {id: string; title: string; course_title: string; completions: number}[];
  questions: Question[];
}

export interface CourseRow {
  id: string; title: string; status: Status; goal: string; updated_at: string;
  modules: number; lessons: number; published: number; learners: number; source: Source;
}

export interface LessonRow {id: string; title: string; status: Status; access: Access; minutes: number; completions: number}
export interface ModuleRow {id: string; title: string; lessons: LessonRow[]}

export interface CourseFields {
  id: string | null; title: string; description: string; outcome: string; tools: string; prerequisites: string;
  author: string; goal: string; level: string; status: Status;
}

export interface MapPlace {
  /** A topic id from the catalogue, or 'hidden' to leave the course off the map. */
  topic: string;
  /** The course it follows in its topic ('' for first). */
  after: string;
  rank: string;
  topics: {id: string; title: string}[];
  /** Each topic's other courses, in map order. */
  order: Record<string, {id: string; title: string}[]>;
  url: string | null;
}

export interface CourseDetail {
  course: CourseFields;
  revision: string;
  modules: ModuleRow[];
  source: Source;
  map: MapPlace;
  learners: number;
  options: Options;
}

export interface Resource {id: string; title: string; kind: 'text' | 'link'; content: string; status: 'published' | 'archived'}

export interface LessonFields {
  id: string | null; title: string; objective: string; body: string; prompt: string | null; task: string | null;
  checklist: string | null; access: Access; status: Status; minutes: number; video: string | null; body_format: string;
}

export interface LessonDetail {
  lesson: LessonFields;
  revision: string;
  module: {id: string; title: string};
  course: {id: string; title: string};
  source: Source;
  resources: Resource[];
  stats: {started: number; completed: number};
  options: Options;
}

export interface MaterialRow {
  id: string; title: string; format: string; status: Status; access: Access; minutes: number; updated_at: string; saved: number; source: Source;
}

export interface MaterialFields {
  id: string | null; title: string; description: string; outcome: string; tools: string; prerequisites: string; author: string;
  body: string; prompt: string | null; format: string; goal: string; level: string; access: Access; status: Status;
  minutes: number; video: string | null; updated_at: string | null; body_format: string;
}

export interface MaterialDetail {
  material: MaterialFields;
  revision: string;
  source: Source;
  saved: number;
  resources: Resource[];
  options: Options;
}

export interface Person {
  id: string; name: string; email: string; role: 'learner' | 'editor' | 'admin'; entitlement: string; onboarding_done: number;
  last_active: string | null; completed: number; practice: number; open_questions: number;
}

export interface People {
  learners: Person[];
  query: string;
  entitlements: Record<string, string>;
  roles: Record<string, string>;
  totals: {total: number; members: number | null};
}

export interface PersonDetail {
  learner: Person;
  courses: {id: string; title: string; started: string; total: number; done: number}[];
  ranks: {course_id: string; level: number; earned_at: string}[];
  feed: FeedItem[];
  days_month: number;
  questions: Question[];
  entitlements: Record<string, string>;
  roles: Record<string, string>;
  self: boolean;
}

export interface Analytics {
  learners: number;
  activated: number;
  median: number | null;
  result_count: number;
  modules: {id: string; title: string; course_title: string; starters: number; finishers: number}[];
  weeks: {start: string; following: string; denominator: number; numerator: number}[];
  events: {name: string; n: number}[];
  loop: {
    starters: number; activated: number;
    returns: {days: number; cohort: number; returned: number}[];
    weekly: {start: string; learners: number; partial: boolean}[];
    features: {label: string; learners: number}[];
  };
  generated_at: string;
}
