/* Support v1. Failed saves never replace the editor's text. */
(() => {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
  document.querySelectorAll('.support-ticket').forEach(card => {
    const form = card.querySelector('form'), input = form.elements.response;
    const submit = form.querySelector('button'), refresh = card.querySelector('.support-refresh');
    const status = card.querySelector('.support-status'), current = card.querySelector('.support-current');
    const url = `/api/support/tickets/${card.dataset.ticketId}`;
    let revision = null;
    async function call(path, options) {
      const result = await fetch(path, options);
      const data = await result.json();
      if (!result.ok) throw new Error(data.message || 'Не удалось сохранить ответ. Повторите попытку.');
      return data.ticket;
    }
    function show(ticket) {
      revision = ticket.revision;
      current.textContent = ticket.response ? `Обработан · ${ticket.handled_at} UTC\nОтвет: ${ticket.response}` : 'Открыт · ожидает ответа';
      input.disabled = false; submit.disabled = false;
    }
    async function load() {
      refresh.disabled = true;
      try { show(await call(url)); status.textContent = 'Текущий ответ загружен. Ваш текст в форме сохранён.'; }
      catch (_) { status.textContent = 'Не удалось загрузить ответ. Повторите загрузку; ваш текст сохранён.'; }
      finally { refresh.disabled = false; }
    }
    refresh.addEventListener('click', load);
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (revision === null) return;
      submit.disabled = true; refresh.disabled = true; input.readOnly = true;
      try {
        show(await call(url + '/handle', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf}, body: JSON.stringify({revision, response: input.value})}));
        status.textContent = 'Ответ сохранён. Вопрос отмечен обработанным.';
      } catch (error) { status.textContent = error.message; }
      finally { submit.disabled = false; refresh.disabled = false; input.readOnly = false; }
    });
    load();
  });
})();
