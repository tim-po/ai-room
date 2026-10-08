import {useState} from 'react';
import {flushSync} from 'react-dom';
import {Link, useLoaderData, useNavigate, type LoaderFunctionArgs} from 'react-router';
import {getJson, postJson, putJson} from '../api';
import {plural} from '../format';
import {useTitle} from '../useTitle';
import type {CourseDetail, CourseFields, CourseRow, MapPlace, Options} from './types';
import {ChoiceField, EditorHead, Empty, More, PageHead, PublishBar, Segmented, SourceMark, StatusBadge, TextField, archiveItem, choices,
  restoreItem, useDraft, useSave} from './ui';

export const coursesLoader = ({request}: LoaderFunctionArgs) =>
  getJson<{courses: CourseRow[]; options: Options}>('/api/admin/courses', request.signal);
export const courseLoader = ({params, request}: LoaderFunctionArgs) =>
  getJson<CourseDetail>(`/api/admin/courses/${params.id}`, request.signal);

const FILTERS = [['all', 'Все'], ['published', 'Опубликованные'], ['draft', 'Черновики'], ['archived', 'Архив']] as const;

export function Courses() {
  const {courses, options} = useLoaderData() as {courses: CourseRow[]; options: Options};
  useTitle('Курсы · Админка');
  const [filter, setFilter] = useState<string>('all');
  const [query, setQuery] = useState('');
  const goal = Object.fromEntries(options.goals.map(g => [g.id, g.label]));
  const shown = courses.filter(c => (filter === 'all' || c.status === filter) && c.title.toLowerCase().includes(query.trim().toLowerCase()));
  return (
    <>
      <PageHead eyebrow="Контент" title="Курсы и уроки" actions={<Link className="button" to="/admin/courses/new">Новый курс</Link>}>
        Курс → модули → уроки.
      </PageHead>
      <div className="adm-toolbar">
        <div className="adm-tabs" role="tablist">
          {FILTERS.map(([id, label]) => (
            <button key={id} role="tab" aria-selected={filter === id} className={filter === id ? 'is-on' : undefined} onClick={() => setFilter(id)}>
              {label}<span>{id === 'all' ? courses.length : courses.filter(c => c.status === id).length}</span>
            </button>
          ))}
        </div>
        <input type="search" className="adm-search" placeholder="Найти курс" value={query} onChange={e => setQuery(e.target.value)} aria-label="Найти курс" />
      </div>
      {shown.length ? (
        <div className="adm-table" role="table">
          <div role="row" className="adm-tr is-head">
            <span role="columnheader">Курс</span><span role="columnheader">Статус</span><span role="columnheader">Уроки</span><span role="columnheader">Ученики</span>
          </div>
          {shown.map(c => (
            <Link role="row" key={c.id} to={`/admin/courses/${c.id}`} className="adm-tr">
              <span role="cell" className="adm-title-cell">
                <strong>{c.title}</strong>
                <small>{goal[c.goal] ?? c.goal} · {c.modules} {plural(c.modules, 'модуль', 'модуля', 'модулей')}{c.source && <> · <SourceMark source={c.source} /></>}</small>
              </span>
              <span role="cell"><StatusBadge status={c.status} /></span>
              <span role="cell" className="adm-num">{c.published}<small> / {c.lessons}</small></span>
              <span role="cell" className="adm-num">{c.learners}</span>
            </Link>
          ))}
        </div>
      ) : <Empty>{courses.length ? 'Ничего не нашлось.' : 'Курсов пока нет — создайте первый.'}</Empty>}
    </>
  );
}

const editable = (c: CourseFields, map: MapPlace) => ({title: c.title, description: c.description, outcome: c.outcome, tools: c.tools,
  prerequisites: c.prerequisites, author: c.author, goal: c.goal, level: c.level, map_topic: map.topic, map_after: map.after});

export function CourseEditor() {
  const initial = useLoaderData() as CourseDetail;
  const [data, setData] = useState(initial);
  const navigate = useNavigate();
  const isNew = !data.course.id;
  const form = useDraft(editable(data.course, data.map));
  const {draft, set} = form;
  const options = data.options;
  useTitle(`${draft.title || 'Новый курс'} · Админка`);
  const hasPublishedLesson = data.modules.some(m => m.lessons.some(l => l.status === 'published'));
  const missing = [
    !draft.title.trim() && 'название', !draft.description.trim() && 'описание', !draft.outcome.trim() && 'что получится',
    !hasPublishedLesson && 'опубликованный урок',
  ].filter(Boolean) as string[];

  const {state, save} = useSave(async status => {
    const body = {...draft, status: status ?? data.course.status};
    if (isNew) {
      const created = await postJson<CourseDetail>('/api/admin/courses', body);
      flushSync(() => form.reset(editable(created.course, created.map)));
      navigate(`/admin/courses/${created.course.id}`, {replace: true});
      return;
    }
    const updated = await putJson<CourseDetail>(`/api/admin/courses/${data.course.id}`, {...body, revision: data.revision});
    setData(updated);
    form.reset(editable(updated.course, updated.map));
  }, true);

  const [moduleTitle, setModuleTitle] = useState('');
  const [busy, setBusy] = useState(false);
  async function structure(run: () => Promise<CourseDetail>) {
    setBusy(true);
    try {
      const next = await run();
      // Structure changes touch the course's updated_at: keep the newest revision for the next save.
      setData(d => ({...next, options: d.options}));
    } finally {
      setBusy(false);
    }
  }

  const about = (
    <section className={'adm-card adm-form' + (isNew ? ' is-narrow' : '')}>
      <TextField label="Описание" value={draft.description} onChange={set('description')} max={2000} multiline rows={3}
        hint="Видно в Обзоре и на странице курса." />
      <TextField label="Что получится" value={draft.outcome} onChange={set('outcome')} max={2000} multiline rows={2}
        hint="Что ученик сможет сделать после курса." />
      <div className="adm-pair">
        <ChoiceField label="Раздел карты навыков" value={draft.map_topic}
          onChange={topic => form.setDraft(d => ({...d, map_topic: topic, map_after: data.map.order[topic]?.at(-1)?.id ?? ''}))}
          options={[...data.map.topics.map(t => [t.id, t.title] as const), ['hidden', 'Не показывать на карте'] as const]} />
        {draft.map_topic !== 'hidden' && (
          <ChoiceField label="Место в разделе" value={draft.map_after} onChange={set('map_after')}
            options={[['', 'Первым'] as const, ...(data.map.order[draft.map_topic] ?? []).map(c => [c.id, `После «${c.title}»`] as const)]} />
        )}
      </div>
      <More summary={[options.goals.find(g => g.id === draft.goal)?.label, draft.level, draft.author].filter(Boolean).join(' · ')}>
        <ChoiceField label="Цель ученика (для рекомендаций)" value={draft.goal} options={choices(options.goals)} onChange={set('goal')} />
        <Segmented label="Уровень" value={draft.level} options={options.levels.map(l => [l, l] as const)} onChange={set('level')} />
        <TextField label="Инструменты и расходы" value={draft.tools} onChange={set('tools')} max={1000} placeholder="Например, Claude — хватит бесплатного тарифа" />
        <TextField label="Что нужно заранее" value={draft.prerequisites} onChange={set('prerequisites')} max={1000} placeholder="Пусто — «ничего, начнём с нуля»" />
        <TextField label="Автор" value={draft.author} onChange={set('author')} max={200} />
      </More>
    </section>
  );
  async function restore() {
    const next = await postJson<CourseDetail>(`/api/admin/courses/${data.course.id}/restore`, {});
    setData(next);
    form.reset(editable(next.course, next.map));
  }
  const live = data.course.status === 'published';

  return (
    <>
      <EditorHead title={draft.title} onTitle={set('title')} placeholder="Название курса"
        crumbs={<><Link to="/admin/courses">Курсы</Link><span>{isNew ? 'Новый курс' : 'Курс'}</span></>} />
      {isNew ? about : (
        <div className="adm-editor is-course">
          <section className="adm-card adm-structure">
            <header>
              <h2>Модули и уроки</h2>
              <span className="adm-muted">{data.modules.length} {plural(data.modules.length, 'модуль', 'модуля', 'модулей')} · {data.learners} {plural(data.learners, 'ученик', 'ученика', 'учеников')}</span>
            </header>
            {data.modules.map((m, mi) => (
              <div className="adm-module" key={m.id} id={m.id}>
                <div className="adm-module-head">
                  <span className="adm-module-n">{mi + 1}</span>
                  <ModuleTitle title={m.title} busy={busy} onSave={title => structure(() => putJson(`/api/admin/modules/${m.id}`, {title}))} />
                  <span className="adm-move">
                    <button type="button" aria-label="Модуль выше" disabled={busy || mi === 0} onClick={() => structure(() => postJson(`/api/admin/modules/${m.id}/move`, {direction: 'up'}))}>↑</button>
                    <button type="button" aria-label="Модуль ниже" disabled={busy || mi === data.modules.length - 1} onClick={() => structure(() => postJson(`/api/admin/modules/${m.id}/move`, {direction: 'down'}))}>↓</button>
                  </span>
                </div>
                <ol className="adm-lessons">
                  {m.lessons.map((l, li) => (
                    <li key={l.id}>
                      <Link to={`/admin/lessons/${l.id}`}>
                        <span className="adm-lesson-title">{l.title}</span>
                        <span className="adm-lesson-meta">
                          {l.status !== 'published' && <StatusBadge status={l.status} />}
                          {l.access === 'member' && <span title="Для участников клуба" aria-label="Для участников клуба">🔒</span>}
                          <span>{l.minutes} мин</span>
                          {l.completions > 0 && <span title="Завершили">{l.completions} ✓</span>}
                        </span>
                      </Link>
                      <span className="adm-move">
                        <button type="button" aria-label="Урок выше" disabled={busy || li === 0} onClick={() => structure(() => postJson(`/api/admin/lessons/${l.id}/move`, {direction: 'up'}))}>↑</button>
                        <button type="button" aria-label="Урок ниже" disabled={busy || li === m.lessons.length - 1} onClick={() => structure(() => postJson(`/api/admin/lessons/${l.id}/move`, {direction: 'down'}))}>↓</button>
                      </span>
                    </li>
                  ))}
                  {!m.lessons.length && <li className="adm-muted">В модуле пока нет уроков.</li>}
                </ol>
                <Link className="adm-add" to={`/admin/lessons/new?module=${m.id}`}>+ Урок</Link>
              </div>
            ))}
            {!data.modules.length && <Empty>Добавьте первый модуль — например, «Первые шаги».</Empty>}
            <form className="adm-inline-form" onSubmit={e => {
              e.preventDefault();
              if (!moduleTitle.trim()) return;
              void structure(() => postJson(`/api/admin/courses/${data.course.id}/modules`, {title: moduleTitle})).then(() => setModuleTitle(''));
            }}>
              <input value={moduleTitle} onChange={e => setModuleTitle(e.target.value)} placeholder="Название нового модуля" aria-label="Название нового модуля" maxLength={200} />
              <button className="button secondary" disabled={busy || !moduleTitle.trim()}>Добавить модуль</button>
            </form>
          </section>
          {about}
        </div>
      )}
      <PublishBar noun="курс" current={isNew ? null : data.course.status} dirty={form.dirty} state={state} missing={missing}
        onSave={save} onRevert={form.revert} menu={[
          live && {label: 'Открыть как ученик', href: `/courses/${data.course.id}`},
          live && !!data.map.url && data.map.topic !== 'hidden' && {label: 'Показать на карте', href: data.map.url},
          restoreItem(data.source, 'курс', restore),
          archiveItem(isNew ? null : data.course.status, 'курс', () => save('archived')),
        ]} />
    </>
  );
}

function ModuleTitle({title, busy, onSave}: {title: string; busy: boolean; onSave: (title: string) => Promise<void>}) {
  const [value, setValue] = useState(title);
  const [editing, setEditing] = useState(false);
  if (!editing) {
    return (
      <h3 className="adm-module-title">
        <button type="button" disabled={busy} title="Переименовать" onClick={() => { setValue(title); setEditing(true); }}>
          {title}
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16zM13.5 6.5l4 4" /></svg>
          <span className="visually-hidden">— переименовать</span>
        </button>
      </h3>
    );
  }
  return (
    <form className="adm-module-rename" onSubmit={e => { e.preventDefault(); void onSave(value).then(() => setEditing(false)); }}>
      <input value={value} autoFocus maxLength={200} onChange={e => setValue(e.target.value)} aria-label="Название модуля"
        onKeyDown={e => { if (e.key === 'Escape') setEditing(false); }} />
      <button className="button secondary" disabled={!value.trim()}>Сохранить</button>
    </form>
  );
}
