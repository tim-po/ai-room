/* Navigation context only; lesson access and learning evidence remain server-owned. */
(async () => {
  const link = document.querySelector('#ability-return');
  const node = new URL(location).searchParams.get('node');
  if (!link || !node) return;
  try {
    const response = await fetch('/api/skills/nodes/' + encodeURIComponent(node));
    if (!response.ok) return;
    const data = await response.json();
    const lesson = decodeURIComponent(location.pathname.split('/').pop());
    if (!data.content.some(item => item.id === lesson)) return;
    link.textContent = '← ' + data.node.title;
    const source = new URL(location).searchParams;
    const context = new URLSearchParams({node,view:source.get('view')==='list'?'list':'map'});
    if(source.get('q')) context.set('q',source.get('q'));
    link.href = '/?' + context;
    link.hidden = false;
  } catch (_) { /* The course breadcrumb remains available offline. */ }
})();

// Retry only the media request: keep practice, navigation and the document intact.
(() => {
  const video = document.querySelector('video[data-lesson]');
  const retry = document.querySelector('#video-retry');
  const message = document.querySelector('[data-media-message]');
  if (!video || !retry || !message) return;
  let pending = false;
  let timeout;
  const errorPanel = document.querySelector('#video-error');
  const settle = (failed, timedOut = false) => {
    pending = false;
    clearTimeout(timeout);
    retry.setAttribute('aria-busy', 'false');
    retry.setAttribute('aria-disabled', 'false');
    if (failed && errorPanel) errorPanel.hidden = false;
    message.textContent = timedOut
      ? 'Видео загружается дольше обычного. Можно повторить попытку или перейти к тексту; ваш черновик остаётся на месте.'
      : failed
      ? 'Видео пока недоступно. Повторите загрузку или продолжите по тексту.'
      : 'Видео готово к просмотру.';
    // The shared player hides the error panel on success; preserve keyboard focus.
    if (!failed && document.activeElement === retry) video.focus();
  };
  video.addEventListener('error', () => settle(true));
  video.querySelector('source')?.addEventListener('error', () => settle(true));
  video.addEventListener('loadedmetadata', () => settle(false));
  // Initial requests need the same escape hatch as retries, including cached loads.
  const watchInitialLoad = () => {
    if (pending) return;
    clearTimeout(timeout);
    if (video.readyState < video.HAVE_METADATA &&
        video.networkState !== video.NETWORK_NO_SOURCE)
      timeout = setTimeout(() => settle(true, true), 15000);
  };
  video.addEventListener('loadstart', watchInitialLoad);
  watchInitialLoad();
  retry.addEventListener('click', () => {
    if (pending) return;
    pending = true;
    if (Number.isFinite(video.currentTime) && video.currentTime > 0)
      video.dataset.resume = String(video.currentTime);
    retry.setAttribute('aria-busy', 'true');
    retry.setAttribute('aria-disabled', 'true');
    message.textContent = 'Загружаем видео. Ваш текст практики остаётся на месте.';
    timeout = setTimeout(() => settle(true, true), 15000);
    video.load();
  });
  document.querySelector('#video-read')?.addEventListener('click', (event) => {
    event.preventDefault();
    const heading = document.querySelector('#lesson-reading h2');
    heading?.focus({preventScroll: true});
    heading?.scrollIntoView({block: 'start'});
  });
})();
