import {useEffect, useRef} from 'react';
import {AppLink} from '../Shell';
import type {HomeData} from '../types';
// The canvas engine is imperative DOM code (layout, pan/zoom, level-of-detail tweens); React owns
// the surrounding markup and mounts it once per data set.
import {mountTree} from './engine.js';

const LEGEND: [string, string][] = [['done', 'Пройден'], ['progress', 'В процессе'], ['open', 'Доступен'], ['locked', 'Урок клуба'], ['coming', 'Скоро']];

export default function SkillMap({data}: {data: HomeData}) {
  const root = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!root.current) return;
    return mountTree(root.current, data.tree);
  }, [data]);

  const unfinished = data.continuation.unfinished;
  const resume = unfinished
    ? {label: unfinished.status === 'draft' ? 'Черновик ждёт вас' : 'Вы остановились на уроке', title: unfinished.title, url: unfinished.url + (unfinished.status === 'draft' ? '#practice' : ''), action: 'Продолжить →', aria: 'Продолжить обучение'}
    : data.next
      ? {label: 'Следующий шаг', title: data.next.title, url: data.next.url, action: 'Открыть урок →', aria: 'Следующий шаг'}
      : null;

  return (
    <section className="tree" ref={root} aria-labelledby="tree-title">
      <div className="tree-bar-top">
        <div><h1 id="tree-title">Карта навыков</h1></div>
        <div className="tree-tools">
          <label><span className="visually-hidden">Найти урок или курс</span><input type="search" placeholder="Найти урок или курс" data-tree-search /></label>
          <span className="tree-zoom">
            <button type="button" data-zoom-out aria-label="Уменьшить">−</button>
            <span data-zoom-level aria-live="off">100%</span>
            <button type="button" data-zoom-in aria-label="Увеличить">+</button>
          </span>
          <button type="button" data-fit>Показать всё</button>
          <button type="button" data-here>Моё место</button>
        </div>
      </div>
      {resume && (
        <section className="resume-strip" aria-label={resume.aria}>
          <div><p>{resume.label}</p><h2>{resume.title}</h2></div>
          <AppLink className="button" to={resume.url}>{resume.action}</AppLink>
        </section>
      )}
      <p className="tree-status" role="status" data-tree-status />
      <div className="tree-viewport"><div className="tree-canvas" /></div>
      <ul className="tree-legend" aria-label="Обозначения">
        {LEGEND.map(([state, label]) => (
          <li key={state}><span className={`tree-lesson is-${state}`}><span className="tree-dot" /></span>{label}</li>
        ))}
      </ul>
    </section>
  );
}
