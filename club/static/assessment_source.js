// Source text is untrusted content. Render only text and fetch on every opening.
window.appendAssessmentSource = (parent, source) => {
  if (!source) return;
  const el = (tag, text) => { const node = document.createElement(tag); node.textContent = text; return node; };
  if (source.lesson_id) {
    const link = el('a', `Открыть источник${source.paragraph ? ' · абзац ' + source.paragraph : ''}${source.edition ? ' · редакция ' + source.edition : ''}`);
    link.href = '/lessons/' + encodeURIComponent(source.lesson_id);
    parent.append(link);
  }
  if (!source.snapshot_url) return;
  let url;
  try { url = new URL(source.snapshot_url, location.origin); } catch { return; }
  if (url.origin !== location.origin || !/^\/api\/(skills\/forms\/[^/]+\/sources\/[^/]+\/\d+|teaching\/published\/[^/]+\/sources\/[^/]+)$/.test(url.pathname)) return;
  const disclosure = el('details', '');
  disclosure.className = 'assessment-source';
  const summary = el('summary', 'Источник этой проверки' + (source.edition ? ' · редакция ' + source.edition : ''));
  const content = el('div', '');
  const status = el('p', ''); status.setAttribute('role', 'status');
  disclosure.append(summary, status, content); parent.append(disclosure);
  let sequence = 0;
  async function load() {
    const current = ++sequence;
    content.replaceChildren(); status.textContent = 'Загружаем источник…';
    try {
      const response = await fetch(url.href, {cache: 'no-store'});
      if (!response.ok) throw new Error(response.status === 401 ? 'Войдите снова, чтобы открыть источник.' : response.status === 403 ? 'Проверьте доступ к материалу в профиле.' : response.status === 404 ? 'Источник больше недоступен. Вернитесь к навыку, чтобы выбрать материал.' : 'Не удалось открыть источник. Повторите попытку.');
      const data = await response.json();
      if (current !== sequence || !disclosure.open) return;
      const paragraphs = Array.isArray(data.paragraphs) ? data.paragraphs : typeof data.text === 'string' ? [{paragraph: data.paragraph, text: data.text}] : [];
      if (!paragraphs.length) throw new Error('Текст источника недоступен. Откройте связанный урок.');
      status.textContent = 'Сохранённый источник, использованный в этой проверке.';
      for (const paragraph of paragraphs) {
        if (typeof paragraph.text !== 'string') continue;
        const block = el('section', '');
        if (paragraph.paragraph) block.append(el('strong', 'Абзац ' + paragraph.paragraph));
        block.append(el('p', paragraph.text)); content.append(block);
      }
    } catch (error) {
      if (current !== sequence || !disclosure.open) return;
      status.textContent = error instanceof TypeError ? 'Нет связи с сервером. Повторите попытку.' : error.message;
      const retry = el('button', 'Повторить загрузку источника'); retry.type = 'button'; retry.onclick = load; content.append(retry);
    }
  }
  disclosure.addEventListener('toggle', () => {
    if (disclosure.open) load();
    else { sequence++; content.replaceChildren(); status.textContent = ''; }
  });
};
