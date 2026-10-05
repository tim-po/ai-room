/* Support v1: enhance the server-rendered own history without replacing it. */
(() => {
  const refresh = document.querySelector('#support-refresh');
  const status = document.querySelector('#support-status');
  if (!refresh || !status) return;
  const tickets = new Map([...document.querySelectorAll('[data-help-ticket]')]
    .map(node => [Number(node.dataset.helpTicket), node]));
  let loaded = false;
  let loading = false;
  refresh.hidden = false;
  async function load() {
    if (loading) return;
    loading = true;
    // Native disabled drops keyboard focus; retain it without later stealing focus.
    refresh.setAttribute('aria-disabled', 'true');
    refresh.setAttribute('aria-busy', 'true');
    status.textContent = 'Загружаем ответы…';
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch('/api/support/tickets', {signal: controller.signal, headers: {Accept: 'application/json'}, cache: 'no-store'});
      if (!response.ok || response.redirected) throw new Error('unavailable');
      const data = await response.json();
      if (data.version !== 1 || !Array.isArray(data.tickets)) throw new Error('invalid');
      // Validate all matching rows before applying any update. Ignore unrelated IDs.
      const own = data.tickets.filter(ticket => tickets.has(ticket.id));
      if (own.length !== tickets.size || new Set(own.map(t => t.id)).size !== tickets.size || own.some(t =>
        !['open', 'handled'].includes(t.status) || !Number.isInteger(t.revision) || t.revision < 0 ||
        (t.response !== null && typeof t.response !== 'string') ||
        (t.handled_at !== null && typeof t.handled_at !== 'string') ||
        (t.status === 'handled' && (!t.response || !t.handled_at)))) throw new Error('invalid');
      own.forEach(ticket => {
        const node = tickets.get(ticket.id);
        node.querySelector('.help-ticket-state').textContent = ticket.response ? 'Ответ записан' : 'Ожидает ответа';
        node.querySelector('.help-answer-body').textContent = ticket.response || '';
        node.querySelector('.help-answer-time').textContent = ticket.handled_at ? `${ticket.handled_at} UTC` : '';
        node.querySelector('.help-answer').hidden = !ticket.response;
      });
      loaded = true;
      status.textContent = 'Ответы обновлены. Записанный ответ не означает, что ваш вопрос решён.';
      refresh.textContent = 'Обновить ответы';
    } catch (_) {
      status.textContent = loaded
        ? 'Не удалось обновить ответы. Ниже — последняя загруженная версия; ваши вопросы сохранены. Повторите попытку.'
        : 'Не удалось загрузить ответы. Ваши вопросы сохранены. Проверьте подключение и повторите попытку. Если вы вышли из аккаунта, войдите снова.';
      refresh.textContent = 'Повторить загрузку ответов';
    } finally {
      clearTimeout(timeout);
      loading = false;
      refresh.removeAttribute('aria-disabled');
      refresh.removeAttribute('aria-busy');
    }
  }
  refresh.addEventListener('click', load);
  load();
})();
