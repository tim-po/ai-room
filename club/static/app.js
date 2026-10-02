'use strict';
const token = document.querySelector('meta[name="csrf-token"]').content;
const sidebar = document.querySelector('.lesson-sidebar > details');
if (sidebar && window.matchMedia('(max-width: 1100px)').matches) sidebar.open = false;
for (const button of document.querySelectorAll('[data-copy]')) {
  button.addEventListener('click', async () => {
    const status = button.parentElement.querySelector('.copy-status');
    try {
      await navigator.clipboard.writeText(document.getElementById(button.dataset.copy).textContent);
      status.textContent = 'Запрос скопирован.';
    } catch (_) { status.textContent = 'Не удалось скопировать автоматически. Выделите текст запроса и скопируйте его.'; }
  });
}
let dirty = false;
for (const form of document.querySelectorAll('[data-dirty-form]')) {
  form.addEventListener('input', () => {
    dirty = true;
    form.querySelector('[data-save-status]').textContent = 'Есть несохранённые изменения. Нажмите кнопку сохранения.';
  });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const status = form.querySelector('[data-save-status]');
    status.setAttribute('role', 'status');
    const data = Object.fromEntries(new FormData(form));
    const editor = form.hasAttribute('data-editor-form');
    if (!editor) data.status = event.submitter.value;
    const buttons = [...form.querySelectorAll('button')];
    buttons.forEach(b => b.disabled = true);
    status.textContent = 'Сохраняем…';
    try {
      const options = editor
        ? {method:'POST', headers:{'X-Editor-Save':'1'}, body:new FormData(form)}
        : {method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:JSON.stringify(data)};
      const response = await fetch(form.action, options);
      if (!response.ok) {
        if (editor && response.status === 400) {
          const page = new DOMParser().parseFromString(await response.text(), 'text/html');
          throw new Error(page.querySelector('[role="alert"]')?.textContent || 'Проверьте поля формы.');
        }
        if (response.status === 409) throw new Error('Материал уже изменён. Скопируйте свой текст и откройте актуальную версию в новой вкладке.');
        throw new Error('Не удалось сохранить. Текст остаётся в форме. Проверьте подключение и повторите попытку.');
      }
      dirty = false;
      if (editor) location.assign(response.url);
      else location.reload();
    } catch (error) {
      status.textContent = error.message === 'Failed to fetch' ? 'Нет связи с сервером. Текст остаётся в форме; повторите сохранение.' : error.message;
      buttons.forEach(b => b.disabled = false);
    }
  });
}
window.addEventListener('beforeunload', e => { if (dirty) { e.preventDefault(); e.returnValue = ''; } });
const video = document.querySelector('video[data-lesson], video[data-material]');
if (video) {
  const error = document.getElementById('video-error');
  video.addEventListener('error', () => error.hidden = false);
  video.querySelector('source').addEventListener('error', () => error.hidden = false);
  video.addEventListener('loadedmetadata', () => {
    const position = Number(video.dataset.resume);
    if (position > 0 && position < video.duration - 1) video.currentTime = position;
  });
  let lastSave = 0;
  async function savePosition(force = false) {
    if (video.dataset.auth !== '1' || (!force && Date.now() - lastSave < 5000)) return;
    lastSave = Date.now();
    try {
      const response = await fetch((video.dataset.material ? `/api/materials/${video.dataset.material}/video` : `/api/lessons/${video.dataset.lesson}/video`), {method:'POST',keepalive:true,headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:JSON.stringify({seconds:video.currentTime})});
      if (!response.ok) throw new Error('save');
      document.getElementById('video-status').textContent = 'Позиция просмотра сохранена.';
    } catch (_) { document.getElementById('video-status').textContent = 'Позиция не сохранена. Проверьте подключение.'; }
  }
  video.addEventListener('timeupdate', () => savePosition());
  video.addEventListener('pause', () => savePosition(true));
  video.addEventListener('ended', () => savePosition(true));
}
