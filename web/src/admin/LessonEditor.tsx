import {useState} from 'react';
import {flushSync} from 'react-dom';
import {Link, useLoaderData, useNavigate, type LoaderFunctionArgs} from 'react-router';
import {getJson, postJson, putJson} from '../api';
import {useTitle} from '../useTitle';
import BodyEditor from './BodyEditor';
import {Resources} from './Resources';
import type {LessonDetail, LessonFields} from './types';
import {ACCESS, AddOns, ChoiceField, Duration, EditorHead, Facts, PublishBar, RemovePart, Segmented, TextField, archiveItem, estimate,
  restoreItem, useDraft, useSave} from './ui';

export const lessonLoader = ({params, request}: LoaderFunctionArgs) =>
  getJson<LessonDetail>(`/api/admin/lessons/${params.id}${new URL(request.url).search}`, request.signal);

// A stored duration equal to the estimate is treated as "estimated", so it keeps following the text.
const editable = (l: LessonFields) => ({title: l.title, objective: l.objective, body: l.body, prompt: l.prompt ?? '', task: l.task ?? '',
  checklist: l.checklist ?? '', access: l.access, video: l.video ?? '',
  minutes: !l.id || l.minutes === estimate(l.body, l.task ?? '') ? '' : String(l.minutes)});

export default function LessonEditor() {
  const initial = useLoaderData() as LessonDetail;
  const [data, setData] = useState(initial);
  const navigate = useNavigate();
  const isNew = !data.lesson.id;
  const form = useDraft(editable(data.lesson));
  const {draft, set} = form;
  const [shown, setShown] = useState({prompt: !!draft.prompt, practice: !!draft.task, video: !!draft.video, files: data.resources.length > 0});
  const show = (key: keyof typeof shown) => () => setShown(s => ({...s, [key]: true}));
  const hide = (key: keyof typeof shown, clear: Partial<typeof draft> = {}) => {
    form.setDraft(d => ({...d, ...clear}));
    setShown(s => ({...s, [key]: false}));
  };
  useTitle(`${draft.title || 'Новый урок'} · Админка`);
  const missing = [!draft.title.trim() && 'название', !draft.objective.trim() && 'цель урока', !draft.body.trim() && 'текст урока',
    draft.task.trim() && !draft.checklist.trim() && 'критерии практики'].filter(Boolean) as string[];

  const {state, save} = useSave(async status => {
    const body = {...draft, minutes: draft.minutes === '' ? null : Number(draft.minutes), status: status ?? data.lesson.status};
    if (isNew) {
      const created = await postJson<LessonDetail>(`/api/admin/modules/${data.module.id}/lessons`, body);
      flushSync(() => form.reset(editable(created.lesson)));
      navigate(`/admin/lessons/${created.lesson.id}`, {replace: true});
      return;
    }
    const updated = await putJson<LessonDetail>(`/api/admin/lessons/${data.lesson.id}`, {...body, revision: data.revision});
    setData(updated);
    form.reset(editable(updated.lesson));
  }, true);
  async function restore() {
    const next = await postJson<LessonDetail>(`/api/admin/lessons/${data.lesson.id}/restore`, {});
    setData(next);
    form.reset(editable(next.lesson));
  }

  const live = data.lesson.status === 'published';
  return (
    <>
      <EditorHead title={draft.title} onTitle={set('title')} placeholder="Название урока"
        crumbs={<><Link to="/admin/courses">Курсы</Link><Link to={`/admin/courses/${data.course.id}#${data.module.id}`}>{data.course.title}</Link><span>{data.module.title}</span></>} />
      <div className="adm-editor is-lesson">
        <div className="adm-stack">
          <section className="adm-card adm-form">
            <TextField label="Цель урока" value={draft.objective} onChange={set('objective')} max={1000}
              placeholder="Одна фраза: что ученик сделает на этом уроке" />
            <BodyEditor label="Текст урока" value={draft.body} onChange={set('body')} format={data.lesson.body_format} />
            <AddOns items={[
              {label: 'Промпт', shown: shown.prompt, show: show('prompt')},
              {label: 'Практика', shown: shown.practice, show: show('practice')},
              {label: 'Видео', shown: shown.video || !data.options.media.length, show: show('video')},
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
          {shown.practice && (
            <section className="adm-card adm-form has-remove">
              <RemovePart label="Практика" filled={!!(draft.task.trim() || draft.checklist.trim())} onRemove={() => hide('practice', {task: '', checklist: ''})} />
              <TextField label="Практика: что сделать на своей задаче" value={draft.task} onChange={set('task')} max={4000} multiline rows={3} />
              <TextField label="Критерии успеха" value={draft.checklist} onChange={set('checklist')} max={4000} multiline rows={3}
                hint="Каждый с новой строки — ученик отметит их галочками." />
            </section>
          )}
          {shown.files && !isNew && <Resources items={data.resources} onRemove={() => hide('files')}
            add={r => postJson<LessonDetail>(`/api/admin/lessons/${data.lesson.id}/resources`, r).then(next => setData(next))}
            archive={id => postJson<LessonDetail>(`/api/admin/resources/${id}/archive`, {}).then(next => setData(next))} />}
        </div>
        <aside className="adm-aside">
          <section className="adm-card adm-form">
            <Segmented label="Доступ" value={draft.access} options={ACCESS} onChange={v => set('access')(v as typeof draft.access)} />
            <Duration value={draft.minutes} onChange={set('minutes')} empty={!draft.body.trim()} auto={estimate(draft.body, draft.task)} />
            {shown.video && (
              <ChoiceField label="Видео" value={draft.video} options={[['', 'Без видео'], ...data.options.media.map(m => [m, m] as const)]} onChange={set('video')} />
            )}
            <Facts items={[!isNew && `Начали ${data.stats.started} · завершили ${data.stats.completed}`]} />
          </section>
        </aside>
      </div>
      <PublishBar noun="урок" current={isNew ? null : data.lesson.status} dirty={form.dirty} state={state} missing={missing}
        onSave={save} onRevert={form.revert} menu={[
          live && {label: 'Открыть как ученик', href: `/lessons/${data.lesson.id}`},
          restoreItem(data.source, 'урок', restore),
          archiveItem(isNew ? null : data.lesson.status, 'урок', () => save('archived')),
        ]} />
    </>
  );
}
