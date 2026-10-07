import {AppLink} from '../Shell';
import type {TreeCourse} from '../types';

const STATE_LABEL: Record<string, string> = {done: 'Пройден', progress: 'В процессе', locked: 'Клуб', coming: 'Скоро'};

/** Full course outline from the catalogue: every module and lesson with the learner's state. */
export default function Outline({outline, current}: {outline: TreeCourse; current?: string}) {
  return (
    <div className="outline">
      {outline.modules.map((module, index) => {
        const hasCurrent = !!current && module.lessons.some(lesson => lesson.id === current);
        const open = hasCurrent || (!current && module.state !== 'coming' && index < 2);
        return (
          <details key={index} className={`outline-module is-${module.state}`} open={open}>
            <summary>
              <span className="outline-index">{index + 1}</span>
              <span className="outline-title">{module.title}</span>
              <span className="outline-count">{module.lessons.length}</span>
            </summary>
            <ul>
              {module.lessons.map((lesson, i) => {
                const inner = (
                  <>
                    <span className="tree-dot" aria-hidden="true" />
                    <span className="outline-name">{lesson.title}</span>
                    <span className="outline-meta">{STATE_LABEL[lesson.state] ?? `${lesson.minutes} мин`}</span>
                  </>
                );
                return (
                  <li key={lesson.id ?? `coming-${i}`}>
                    {lesson.url
                      ? <AppLink className={`outline-lesson is-${lesson.state}`} to={lesson.url} aria-current={lesson.id === current ? 'page' : undefined}>{inner}</AppLink>
                      : <span className="outline-lesson is-coming">{inner}</span>}
                  </li>
                );
              })}
            </ul>
          </details>
        );
      })}
    </div>
  );
}
