import {useState} from 'react';
import {flushSync} from 'react-dom';
import {Link, useLoaderData, useNavigate, type LoaderFunctionArgs} from 'react-router';
import {getJson, postJson, putJson} from '../api';
import {humanTime} from '../format';
import {useTitle} from '../useTitle';
import BodyEditor from './BodyEditor';
import {Resources} from './Resources';
import type {MaterialDetail, MaterialFields, MaterialRow, Options} from './types';
import {ACCESS, ACCESS_LABEL, AddOns, ChoiceField, Duration, EditorHead, Empty, Facts, More, PageHead, PublishBar, Segmented, SourceMark, StatusBadge,
  RemovePart, TextField, archiveItem, choices, estimate, restoreItem, useDraft, useSave} from './ui';

export const libraryLoader = ({request}: LoaderFunctionArgs) =>
  getJson<{items: MaterialRow[]; options: Options}>('/api/admin/library', request.signal);
export const materialLoader = ({params, request}: LoaderFunctionArgs) =>
  getJson<MaterialDetail>(`/api/admin/library/${params.id}${new URL(request.url).search}`, request.signal);

export function Library() {
  const {items, options} = useLoaderData() as {items: MaterialRow[]; options: Options};
  useTitle('Библиотека · Админка');
  const [format, setFormat] = useState('all');
  const [query, setQuery] = useState('');
  const label = Object.fromEntries(options.formats.map(f => [f.id, f.label]));
  const shown = items.filter(i => (format === 'all' || i.format === format) && i.title.toLowerCase().includes(query.trim().toLowerCase()));
  return (
    <>
      <PageHead eyebrow="Контент" title="Библиотека"
        actions={<Link className="button" to={`/admin/library/new${format !== 'all' ? `?format=${format}` : ''}`}>Новый материал</Link>}>
        Гайды, кейсы и воркшопы вне курсов.
      </PageHead>
      <div className="adm-toolbar">
        <div className="adm-tabs" role="tablist">
          {[['all', 'Все'] as const, ...options.formats.map(f => [f.id, f.label] as const)].map(([id, text]) => (
            <button key={id} role="tab" aria-selected={format === id} className={format === id ? 'is-on' : undefined} onClick={() => setFormat(id)}>
              {text}<span>{id === 'all' ? items.length : items.filter(i => i.format === id).length}</span>
            </button>
          ))}
        </div>
        <input type="search" className="adm-search" placeholder="Найти материал" value={query} onChange={e => setQuery(e.target.value)} aria-label="Найти материал" />
      </div>
      {shown.length ? (
        <div className="adm-table is-library" role="table">
          <div role="row" className="adm-tr is-head">
            <span role="columnheader">Материал</span><span role="columnheader">Статус</span><span role="columnheader">Сохранили</span><span role="columnheader">Обновлён</span>
          </div>
          {shown.map(i => (
            <Link role="row" key={i.id} to={`/admin/library/${i.id}`} className="adm-tr">
              <span role="cell" className="adm-title-cell">
                <strong>{i.title}</strong>
                <small>{label[i.format]} · {i.minutes} мин · {ACCESS_LABEL[i.access]}{i.source && <> · <SourceMark source={i.source} /></>}</small>
              </span>
              <span role="cell"><StatusBadge status={i.status} /></span>
              <span role="cell" className="adm-num">{i.saved}</span>
              <span role="cell" className="adm-muted">{humanTime(i.updated_at)}</span>
            </Link>
          ))}
        </div>
      ) : <Empty>{items.length ? 'Ничего не нашлось.' : 'Материалов пока нет.'}</Empty>}
    </>
  );
}

const editable = (m: MaterialFields) => ({title: m.title, description: m.description, outcome: m.outcome, tools: m.tools,
  prerequisites: m.prerequisites, author: m.author, body: m.body, prompt: m.prompt ?? '', format: m.format, goal: m.goal,
  level: m.level, access: m.access, video: m.video ?? '', minutes: !m.id || m.minutes === estimate(m.body) ? '' : String(m.minutes)});

export function MaterialEditor() {
  const initial = useLoaderData() as MaterialDetail;
  const [data, setData] = useState(initial);
  const navigate = useNavigate();
  const isNew = !data.material.id;
  const form = useDraft(editable(data.material));
  const {draft, set} = form;
  const options = data.options;
  const format = Object.fromEntries(options.formats.map(f => [f.id, f.label]));
  const [shown, setShown] = useState({prompt: !!draft.prompt, video: !!draft.video, files: data.resources.length > 0});
  const show = (key: keyof typeof shown) => () => setShown(s => ({...s, [key]: true}));
  const hide = (key: keyof typeof shown, clear: Partial<typeof draft> = {}) => {
    form.setDraft(d => ({...d, ...clear}));
    setShown(s => ({...s, [key]: false}));
  };
  useTitle(`${draft.title || 'Новый материал'} · Админка`);
  const missing = [!draft.title.trim() && 'название', !draft.description.trim() && 'описание', !draft.outcome.trim() && 'что получится',
    !draft.body.trim() && 'текст'].filter(Boolean) as string[];
  const {state, save} = useSave(async status => {
    const body = {...draft, minutes: draft.minutes === '' ? null : Number(draft.minutes), status: status ?? data.material.status};
    if (isNew) {
      const created = await postJson<MaterialDetail>('/api/admin/library', body);
      flushSync(() => form.reset(editable(created.material)));
      navigate(`/admin/library/${created.material.id}`, {replace: true});
      return;
    }
    const updated = await putJson<MaterialDetail>(`/api/admin/library/${data.material.id}`, {...body, revision: data.revision});
    setData(updated);
    form.reset(editable(updated.material));
  }, true);
  async function restore() {
    const next = await postJson<MaterialDetail>(`/api/admin/library/${data.material.id}/restore`, {});
    setData(next);
    form.reset(editable(next.material));
  }

  return (
    <>
      <EditorHead title={draft.title} onTitle={set('title')} placeholder="Название материала"
        crumbs={<><Link to="/admin/library">Библиотека</Link><span>{format[draft.format]}</span></>} />
      <div className="adm-editor is-lesson">
        <div className="adm-stack">
          <section className="adm-card adm-form">
            <TextField label="Описание" value={draft.description} onChange={set('description')} max={2000} multiline rows={2}
              hint="Подпись на карточке в Обзоре." />
            <TextField label="Что получится" value={draft.outcome} onChange={set('outcome')} max={2000} multiline rows={2} />
            <BodyEditor label="Текст" value={draft.body} onChange={set('body')} format={data.material.body_format} />
            <AddOns items={[
              {label: 'Промпт', shown: shown.prompt, show: show('prompt')},
              {label: 'Видео', shown: shown.video || !options.media.length, show: show('video')},
              {label: 'Ссылка или файл', shown: shown.files || isNew, show: show('files')},
            ]} />
          </section>
          {shown.prompt && (
            <section className="adm-card adm-form has-remove">
              <RemovePart label="Промпт" filled={!!draft.prompt.trim()} onRemove={() => hide('prompt', {prompt: ''})} />
              <TextField label="Промпт" value={draft.prompt} onChange={set('prompt')} max={6000} multiline rows={4} mono
                hint="Ученик увидит его с кнопкой «Скопировать»." />
            </section>
          )}
          {shown.files && !isNew && <Resources title="Файлы и ссылки" items={data.resources} onRemove={() => hide('files')}
            add={r => postJson<MaterialDetail>(`/api/admin/library/${data.material.id}/resources`, r).then(next => setData(next))}
            archive={id => postJson<MaterialDetail>(`/api/admin/library/resources/${id}/archive`, {}).then(next => setData(next))} />}
        </div>
        <aside className="adm-aside">
          <section className="adm-card adm-form">
            <Segmented label="Формат" value={draft.format} options={choices(options.formats)} onChange={set('format')} />
            <Segmented label="Доступ" value={draft.access} options={ACCESS} onChange={v => set('access')(v as typeof draft.access)} />
            <ChoiceField label="Тема" value={draft.goal} options={choices(options.goals)} onChange={set('goal')} />
            <Duration value={draft.minutes} onChange={set('minutes')} empty={!draft.body.trim()} auto={estimate(draft.body)} />
            {shown.video && (
              <ChoiceField label="Видео" value={draft.video} options={[['', 'Без видео'], ...options.media.map(m => [m, m] as const)]} onChange={set('video')} />
            )}
            <More summary={[draft.level, draft.author].filter(Boolean).join(' · ')}>
              <Segmented label="Уровень" value={draft.level} options={options.levels.map(l => [l, l] as const)} onChange={set('level')} />
              <TextField label="Инструменты и расходы" value={draft.tools} onChange={set('tools')} max={1000} />
              <TextField label="Что нужно заранее" value={draft.prerequisites} onChange={set('prerequisites')} max={1000} />
              <TextField label="Автор" value={draft.author} onChange={set('author')} max={200} />
            </More>
            <Facts items={[!isNew && `Сохранили в избранное: ${data.saved}`]} />
          </section>
        </aside>
      </div>
      <PublishBar noun="материал" current={isNew ? null : data.material.status} dirty={form.dirty} state={state} missing={missing}
        onSave={save} onRevert={form.revert} menu={[
          data.material.status === 'published' && {label: 'Открыть как ученик', href: `/materials/${data.material.id}`},
          restoreItem(data.source, 'материал', restore),
          archiveItem(isNew ? null : data.material.status, 'материал', () => save('archived')),
        ]} />
    </>
  );
}
