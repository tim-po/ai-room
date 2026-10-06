import {useState} from 'react';
import {ApiError, bootstrap, postJson} from '../api';
import {AppLink} from '../links';
import type {LessonData} from '../types';

// "Ссылка для ассистента": the practice happens in the learner's own assistant, so the learner pastes
// a one-time link into Claude / ChatGPT / Claude Code. The assistant opens it, gets the lesson, the
// task and a key to save the work back (club/attach.py). A plain prompt stays as a fallback for apps
// that can't open links.

export interface Link {
  url: string;
  expires_at: string;
  minutes: number;
}

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

/** Copies text produced by an async step. Safari only allows that through a ClipboardItem promise. */
export async function copyAsync(produce: () => Promise<string>): Promise<string> {
  if (typeof ClipboardItem !== 'undefined' && navigator.clipboard?.write) {
    let resolved = '';
    const text = produce().then(value => { resolved = value; return value; });
    await navigator.clipboard.write([new ClipboardItem({'text/plain': text.then(value => new Blob([value], {type: 'text/plain'}))})]);
    return resolved || text;
  }
  const value = await produce();
  await navigator.clipboard.writeText(value);
  return value;
}

export default function AssistantHandoff({data, section, draft}: {data: LessonData; section?: string; draft?: string}) {
  const [link, setLink] = useState<Link | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('');
  const [showPrompt, setShowPrompt] = useState(false);
  const practice = !!data.lesson.task;
  const unsaved = draft?.trim() && draft.trim() !== (data.practice?.body ?? '').trim() ? draft.trim() : undefined;
  const prompt = buildPrompt(data, {section, draft});

  async function createLink() {
    setBusy(true); setStatus('');
    const made: {link: Link | null} = {link: null};
    const make = async () => {
      made.link = await postJson<Link>('/api/app/attach-links', {lesson_id: data.lesson.id, draft: unsaved});
      return made.link.url;
    };
    try {
      await copyAsync(make);
      setLink(made.link);
      setStatus('Ссылка скопирована — вставьте её в чат с ассистентом.');
    } catch (error) {
      if (made.link) {
        setLink(made.link);
        setStatus('Ссылка готова — скопируйте её из поля ниже.');
      } else {
        setStatus(error instanceof ApiError ? error.message : 'Не удалось создать ссылку. Повторите попытку.');
      }
    } finally {
      setBusy(false);
    }
  }
  function copy(text: string, done: string) {
    navigator.clipboard.writeText(text).then(() => setStatus(done), () => setStatus('Не удалось скопировать автоматически — выделите текст и скопируйте его.'));
  }

  return (
    <section className="assistant-handoff" aria-labelledby="assistant-title">
      <h3 id="assistant-title">{practice ? 'Сделайте практику вместе с вашим ИИ' : 'Разберите урок с вашим ИИ-ассистентом'}</h3>
      {bootstrap.user ? (
        <>
          <p className="small">
            Скопируйте ссылку и вставьте её в чат с Claude, ChatGPT или в Claude Code. Ассистент откроет урок, увидит задание{unsaved ? ' и ваш черновик' : ''}
            {practice ? ' и сможет сохранить вашу работу сюда, в «Мои работы»' : ''}.
          </p>
          <div className="assistant-actions">
            <button type="button" className="button" onClick={createLink} disabled={busy}>{busy ? 'Создаём ссылку…' : link ? 'Новая ссылка' : 'Скопировать ссылку для ассистента'}</button>
            <button type="button" className="link-button" aria-expanded={showPrompt} onClick={() => setShowPrompt(v => !v)}>Нет доступа к ссылкам? Запрос текстом</button>
          </div>
          {link && (
            <div className="assistant-link">
              <input readOnly value={link.url} aria-label="Ссылка для ассистента" onFocus={event => event.currentTarget.select()} />
              <button type="button" className="button secondary" onClick={() => copy(link.url, 'Ссылка скопирована.')}>Скопировать</button>
              <p className="small">
                Ссылка сработает один раз в течение {link.minutes} минут. Ассистент получит доступ к вашему обучению на 7 дней:
                читать уроки и сохранять работу. Отключить можно в <AppLink to="/profile#connections">«Моё обучение» → Подключения</AppLink>.
              </p>
            </div>
          )}
        </>
      ) : (
        <p className="small">
          <AppLink to={`/login?next=/lessons/${data.lesson.id}`}>Войдите</AppLink>, чтобы дать ассистенту ссылку на урок — тогда он сможет сохранить вашу работу сюда.
          Или скопируйте запрос текстом.
        </p>
      )}
      {(showPrompt || !bootstrap.user) && (
        <div className="assistant-prompt">
          <pre className="assistant-preview">{prompt}</pre>
          <button type="button" className="button secondary" onClick={() => copy(prompt, 'Запрос скопирован — вставьте его в чат с ассистентом.')}>Скопировать запрос</button>
        </div>
      )}
      <p className="small" role="status">{status}</p>
    </section>
  );
}
