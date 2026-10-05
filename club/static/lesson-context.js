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
