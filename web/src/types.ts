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

export interface HomeData {
  tree: {topics: TreeTopic[]};
  continuation: Continuation;
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
  weekly: number;
  practices: (Practice & {lesson_id: string; title: string; course_id: string})[];
  active_courses: CourseProgress[];
  completed_courses: CourseProgress[];
  favourites: {id: string; title: string}[];
  material_favourites: {id: string; title: string}[];
}
