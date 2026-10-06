// Preserve bookmarked design references after the staging application moves to root.
if (location.pathname === '/' && /^#\/(orbit|campus|studio)\//.test(location.hash)) {
  location.replace('/prototypes/' + location.hash);
}
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
for (const button of document.querySelectorAll('[data-copy-block]')) {
  button.addEventListener('click', async () => {
    const status = button.parentElement.querySelector('.copy-status');
    try {
      await navigator.clipboard.writeText(button.parentElement.querySelector('pre').textContent);
      status.textContent = 'Скопировано.';
    } catch (_) { status.textContent = 'Не удалось скопировать автоматически. Выделите текст и скопируйте его.'; }
  });
}
// Human, local dates: "сегодня в 14:05", "вчера в 09:30", "3 окт в 18:00".
for (const node of document.querySelectorAll('time[data-local-time]')) {
  const moment = new Date(node.getAttribute('datetime'));
  if (Number.isNaN(moment.getTime())) continue;
  const time = moment.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
  const day = d => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diff = Math.round((day(new Date()) - day(moment)) / 86400000);
  const date = moment.toLocaleDateString('ru-RU', {day: 'numeric', month: 'short', year: moment.getFullYear() === new Date().getFullYear() ? undefined : 'numeric'});
  node.textContent = diff === 0 ? `сегодня в ${time}` : diff === 1 ? `вчера в ${time}` : `${date.replace('.', '')} в ${time}`;
}
// "В этом уроке": highlight the step being read.
const tocLinks = [...document.querySelectorAll('.lesson-toc a')];
if (tocLinks.length && 'IntersectionObserver' in window) {
  const targets = tocLinks.map(a => document.getElementById(a.hash.slice(1))).filter(Boolean);
  const mark = id => tocLinks.forEach(a => a.toggleAttribute('aria-current', a.hash === '#' + id));
  const seen = new IntersectionObserver(entries => {
    const visible = entries.filter(e => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
    if (visible) mark(visible.target.id);
  }, {rootMargin: '0px 0px -70% 0px'});
  targets.forEach(t => seen.observe(t));
}
let dirty = false;
for (const form of document.querySelectorAll('[data-dirty-form]')) {
  form.addEventListener('input', () => {
    dirty = true;
    if (form.hasAttribute('data-practice-form')) {
      form.parentElement.querySelector('[data-practice-confirmation]').hidden = true;
      form.parentElement.querySelector('.chip').textContent = 'Изменения не сохранены';
    }
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
    if (form.hasAttribute('data-practice-form')) {
      form.parentElement.querySelector('[data-practice-confirmation]').hidden = true;
      form.parentElement.querySelector('.chip').textContent = 'Сохранение не подтверждено';
    }
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
      if (!form.hasAttribute('data-practice-form')) dirty = false;
      if (editor) {
        if (new URL(response.url).pathname === location.pathname) {
          try { sessionStorage.setItem('editor-return', JSON.stringify({path:location.pathname,y:scrollY})); } catch (_) { /* Storage is optional UI state. */ }
        }
        location.assign(response.url);
      }
      else if (form.hasAttribute('data-practice-form')) {
        const saved = await fetch(form.action, {headers:{'Accept':'application/json'}});
        if (!saved.ok) throw new Error('Работа отправлена, но подтвердить сохранение не удалось. Повторите сохранение.');
        const stored = await saved.json();
        const practice = stored.practice || stored;
        if (practice.body !== data.body || practice.status !== data.status) throw new Error('Не удалось подтвердить сохранённую версию. Текст остаётся в форме.');
        if (new FormData(form).get('body') !== data.body) {
          status.textContent = 'Предыдущая версия сохранена. Новые изменения ещё не сохранены.';
          buttons.forEach(b => b.disabled = false);
          return;
        }
        dirty = false;
        status.textContent = data.status === 'draft' ? 'Черновик сохранён' : 'Работа сохранена';
        const confirmation = form.parentElement.querySelector('[data-practice-confirmation]');
        confirmation.hidden = false;
        confirmation.querySelector('[data-confirmation-title]').textContent = status.textContent;
        form.parentElement.querySelector('.chip').textContent = status.textContent;
        buttons.forEach(b => b.disabled = false);
      } else location.reload();
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
  function showMediaError() { error.hidden = false; }
  video.addEventListener('error', showMediaError);
  video.querySelector('source')?.addEventListener('error', showMediaError);
  // A deferred script may start after a cached/fast source failure or metadata load.
  // Read the current state as well as subscribing to subsequent events.
  function restorePosition() {
    error.hidden = true;
    const position = Number(video.dataset.resume);
    if (position > 0 && position < video.duration - 1) video.currentTime = position;
  }
  video.addEventListener('loadedmetadata', restorePosition);
  if (video.error || video.networkState === video.NETWORK_NO_SOURCE) showMediaError();
  else if (video.readyState >= video.HAVE_METADATA) restorePosition();
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

// Reveal the affected stable module/lesson after a native editorial action.
function revealEditorLocation() {
  const target = document.getElementById(location.hash.slice(1));
  if (!target || !target.closest('.editor-module')) return;
  target.closest('.editor-module').open = true;
  requestAnimationFrame(() => target.scrollIntoView({block:'start'}));
}
revealEditorLocation();
window.addEventListener('hashchange', revealEditorLocation);
const routeSteps = [...document.querySelectorAll('[data-route-step]')];
function describeStep(step) {
  const option = step.querySelector('select').selectedOptions[0];
  const description = step.querySelector('.selected-step');
  const title = document.createElement('strong');
  title.textContent = option.dataset.title || 'Без шага';
  const course = document.createElement('span');
  course.className = 'small'; course.textContent = option.dataset.course || '';
  description.replaceChildren(title, course);
}
routeSteps.forEach((step, index) => {
  step.querySelector('[data-step-moves]').hidden = false;
  const select = step.querySelector('select');
  select.addEventListener('change', () => describeStep(step));
  for (const [selector, offset] of [['[data-step-up]', -1], ['[data-step-down]', 1]]) {
    const button = step.querySelector(selector);
    button.disabled = !routeSteps[index + offset];
    button.addEventListener('click', () => {
      const other = routeSteps[index + offset];
      const otherSelect = other.querySelector('select');
      [select.value, otherSelect.value] = [otherSelect.value, select.value];
      describeStep(step); describeStep(other);
      select.dispatchEvent(new Event('input', {bubbles:true}));
      otherSelect.focus();
      other.scrollIntoView({block:'center'});
    });
  }
});

if (document.querySelector('[data-editor-form]')) {
  try {
    const saved = JSON.parse(sessionStorage.getItem('editor-return') || 'null');
    sessionStorage.removeItem('editor-return');
    if (saved?.path === location.pathname && Number.isFinite(saved.y)) {
      requestAnimationFrame(() => window.scrollTo({top:saved.y,behavior:'instant'}));
    }
  } catch (_) { /* Saving content never depends on browser storage. */ }
}
