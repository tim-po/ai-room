import {useState} from 'react';
import type {LessonData} from '../types';

// "Продолжить в Claude / ChatGPT": the practice happens in the learner's own assistant, so hand it
// the lesson context as a ready prompt. Nothing is sent anywhere until the learner clicks; the
// prompt is copied, and a new chat opens (prefilled where the service supports it).

const ASSISTANTS = [
  {name: 'Claude', url: 'https://claude.ai/new', param: 'q'},
  {name: 'ChatGPT', url: 'https://chatgpt.com/', param: 'q'},
] as const;
// Prefill only while the link stays short; the clipboard always has the full prompt.
const MAX_LINK = 6000;

export function buildPrompt(data: LessonData, {section, draft}: {section?: string; draft?: string}): string {
  const {lesson, course} = data;
  const lines = [`Я прохожу урок «${lesson.title}» в AI Room (курс «${course.title}»).`, `Цель урока: ${lesson.objective}`, ''];
  if (lesson.task) {
    lines.push('Задание:', lesson.task, '');
    if (lesson.checklist?.length) lines.push('Критерии хорошего результата:', ...lesson.checklist.map(item => `- ${item}`), '');
    if (draft?.trim()) lines.push('Мой черновик:', '"""', draft.trim(), '"""', '');
    lines.push(
      'Помоги мне выполнить задание на моей собственной задаче:',
      '1. Сначала задай 2–3 коротких вопроса о моей ситуации — по одному за раз.',
      '2. Затем помогай шаг за шагом; не делай всё за меня.',
      '3. В конце проверь результат по критериям выше и скажи, что улучшить.',
      '4. Дай итоговую версию одним блоком — я сохраню её в AI Room.',
    );
  } else {
    if (lesson.steps.length) lines.push('Разделы урока:', ...lesson.steps.map((s, i) => `${i + 1}. ${s}`), '');
    if (section) lines.push(`Сейчас я на разделе «${section}».`, '');
    lines.push('Помоги мне применить этот урок к моей задаче: сначала спроси, над чем я работаю, затем объясни главное из урока на моём примере. Вопросы задавай по одному.');
  }
  return lines.join('\n');
}

export default function AssistantHandoff({data, section, draft}: {data: LessonData; section?: string; draft?: string}) {
  const [withDraft, setWithDraft] = useState(true);
  const [preview, setPreview] = useState(false);
  const [status, setStatus] = useState('');
  const hasDraft = !!draft?.trim();
  const prompt = buildPrompt(data, {section, draft: hasDraft && withDraft ? draft : undefined});
  const practice = !!data.lesson.task;

  function copy(opened?: string) {
    // Started inside the click, before the new tab takes focus (clipboard needs a focused page).
    navigator.clipboard.writeText(prompt).then(
      () => setStatus(opened ? `Запрос скопирован. Если в ${opened} он не появился сам — вставьте его в чат: ⌘V или Ctrl+V.` : 'Запрос скопирован.'),
      () => setStatus('Не удалось скопировать автоматически. Откройте «Показать запрос» и скопируйте текст вручную.'),
    );
  }
  function link(assistant: typeof ASSISTANTS[number]) {
    const prefilled = `${assistant.url}?${assistant.param}=${encodeURIComponent(prompt)}`;
    return prefilled.length <= MAX_LINK ? prefilled : assistant.url;
  }

  return (
    <section className="assistant-handoff" aria-labelledby="assistant-title">
      <h3 id="assistant-title">{practice ? 'Сделайте практику вместе с ИИ' : 'Разберите урок с ИИ-ассистентом'}</h3>
      <p className="small">
        {practice
          ? 'Откроем новый чат с готовым запросом: задание урока, критерии проверки' + (hasDraft ? ' и ваш черновик' : '') + '. Итог вставьте ниже и сохраните.'
          : 'Откроем новый чат с готовым запросом о вашем уроке — ассистент поможет применить его к вашей задаче.'}
        {' '}ChatGPT отправляет запрос сразу, в Claude его можно поправить перед отправкой.
      </p>
      <div className="assistant-actions">
        {ASSISTANTS.map(assistant => (
          <a key={assistant.name} className="button secondary" href={link(assistant)} target="_blank" rel="noopener noreferrer" onClick={() => copy(assistant.name)}>
            Открыть в {assistant.name} ↗
          </a>
        ))}
        <button type="button" className="link-button" onClick={() => copy()}>Скопировать запрос</button>
        <button type="button" className="link-button" aria-expanded={preview} onClick={() => setPreview(v => !v)}>{preview ? 'Скрыть запрос' : 'Показать запрос'}</button>
      </div>
      {hasDraft && (
        <label className="assistant-draft">
          <input type="checkbox" checked={withDraft} onChange={e => setWithDraft(e.target.checked)} /> Добавить мой черновик в запрос
        </label>
      )}
      {preview && <pre className="assistant-preview">{prompt}</pre>}
      <p className="small" role="status">{status}</p>
    </section>
  );
}
