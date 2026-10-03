(() => {
  const atlas = document.querySelector('.atlas');
  if (!atlas) return;
  const map = document.querySelector('#skill-map'), panel = document.querySelector('#node-detail'), status = document.querySelector('#atlas-status');
  const search = document.querySelector('#skill-search');
  let graph, me = {coverage: []}, selected, list = false, detailSequence = 0;
  const names = new Map(), children = new Map(), parents = new Map();
  const art = {
    'basic-ai': '<circle cx="40" cy="34" r="18"/><ellipse cx="40" cy="34" rx="34" ry="10" transform="rotate(-25 40 34)"/><path d="M40 9v8m0 34v8"/>',
    coding: '<rect x="8" y="10" width="64" height="46" rx="5"/><path d="m30 24-10 9 10 9m20-18 10 9-10 9M44 22l-8 24M8 19h64"/>',
    teams: '<circle cx="20" cy="19" r="8"/><circle cx="60" cy="19" r="8"/><circle cx="40" cy="48" r="8"/><path d="M28 19h24M24 27l12 13m20-13L44 40"/>',
    content: '<rect x="8" y="8" width="44" height="35" rx="4"/><path d="m14 34 10-12 10 8 10-14M24 49h44V20M32 57h43V28"/>',
    automation: '<rect x="5" y="23" width="18" height="18" rx="3"/><path d="M23 32h15V13h17M38 32v20h17"/><circle cx="64" cy="13" r="8"/><circle cx="64" cy="52" r="8"/>',
    agents: '<circle cx="40" cy="33" r="25"/><path d="m49 17-4 23-15 9 5-23ZM40 2v7m0 48v7M8 33h7m50 0h7"/>'
  };
  function el(tag, text, cls) { const e = document.createElement(tag); if(text) e.textContent = text; if(cls) e.className = cls; return e; }
  async function api(url, body) {
    const r = await fetch(url, body ? {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify(body)} : {}).catch(()=>{throw new Error("Нет связи с сервером. Повторите попытку.");});
    if(!r.ok) throw new Error(r.status === 401 ? 'Войдите, чтобы сохранять исследованные навыки.' : 'Не удалось загрузить данные. Повторите попытку.');
    return r.json();
  }
  function family(id) { return id.split('.')[0]; }
  function evidenceLabel(coverage, fallback) {
    if(coverage?.verified)return `✓ Понимание подтверждено: ${coverage.verified} из ${coverage.eligible}`;
    if(coverage?.application_verified)return '✓ Применение подтверждено · понимание '+(coverage.assessed?'пока не подтверждено':'ещё не проверено');
    if(coverage?.assessed)return '↗ Проверено · пока не подтверждено';
    return fallback;
  }
  function button(node) {
    const b = el('button', null, `skill-node family-${family(node.id)}`); b.dataset.node = node.id;
    b.setAttribute('aria-pressed', String(selected === node.id));
    if(art[node.id]) { const icon=el('span',null,'branch-art'); icon.innerHTML=`<svg viewBox="0 0 80 66" aria-hidden="true">${art[node.id]}</svg>`; b.append(icon); }
    b.append(el('strong',node.title));
    const coverage=me.coverage.find(c=>c.node_id===node.id);
    b.classList.toggle('is-verified',Boolean(coverage?.verified));
    b.classList.toggle('is-applied',Boolean(coverage?.application_verified));
    b.append(el('small',evidenceLabel(coverage,node.kind==='ability' ? '◯ Ещё не проверено' : node.kind==='root' ? 'Общая основа' : 'Раздел →')));
    b.onclick=()=>choose(node.id); return b;
  }
  function render() {
    map.replaceChildren(); map.classList.toggle('as-list',list); map.classList.remove('sparse-map');
    const q=search.value.trim().toLocaleLowerCase('ru');
    if(q) {
      map.classList.add('as-list');
      const results=graph.nodes.filter(n=>n.title.toLocaleLowerCase('ru').includes(q));
      const ul=el('ul'); for(const n of results){const li=el('li');li.append(button(n));ul.append(li);}map.append(ul);
      status.textContent=`Найдено навыков: ${results.length}`;
      if(!results.length)map.append(el('p','Попробуйте другое название или вернитесь ко всей карте.'));
      return;
    }
    if(list){const ul=el('ul');appendList(ul,graph.root);map.append(ul);status.textContent='Все направления и навыки. Разверните нужный раздел.';return;}
    const focus=selected ? ((children.get(selected)||[]).length ? selected : parents.get(selected)) : graph.root;
    const overview=!selected;
    const ids=overview ? graph.nodes.filter(n=>n.kind==='branch').map(n=>n.id) : (children.get(focus)||[]).filter(id=>focus!==graph.root || names.get(id).kind!=='branch');
    status.textContent=overview ? 'Пять направлений · выбирайте любое' : names.get(focus).title+' · стрелки переключают узлы';
    const crumb=el('div',null,'map-breadcrumb');
    if(!overview){const back=el('button','← '+(focus===graph.root?'Вся карта':names.get(parents.get(focus)||graph.root).title));back.onclick=()=>focus===graph.root?document.querySelector('#map-reset').click():choose(parents.get(focus)||graph.root);crumb.append(back);}
    map.append(crumb); map.classList.toggle('sparse-map', !overview && ids.length <= 2);
    const stage=el('div',null,'spatial-stage');
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 1000 600');svg.setAttribute('preserveAspectRatio','none');svg.setAttribute('aria-hidden','true');svg.classList.add('map-paths');stage.append(svg);
    const positions=new Map();
    // A bounded local neighbourhood: the centre and every direct sibling remain readable.
    positions.set(focus,{x:50,y:48});
    ids.forEach((id,i)=>{const angle=-Math.PI/2+i*2*Math.PI/ids.length;positions.set(id,{x:50+(innerWidth<=800?29:32)*Math.cos(angle),y:48+34*Math.sin(angle)});});
    for(const id of ids){const pos=positions.get(id);const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',`M 500 288 Q ${pos.x*10} 288 ${pos.x*10} ${pos.y*6}`);svg.append(path);}
    for(const [id,pos] of positions){const node=button(names.get(id));node.style.left=pos.x+'%';node.style.top=pos.y+'%';node.classList.add('spatial-node');if(id===focus)node.classList.add('focus-node');stage.append(node);}
    stage.addEventListener('keydown',e=>{
      if(!['ArrowRight','ArrowLeft','ArrowDown','ArrowUp'].includes(e.key))return;
      const nodes=[...stage.querySelectorAll('button')],index=nodes.indexOf(document.activeElement);if(index<0)return;
      e.preventDefault();nodes[(index+(['ArrowRight','ArrowDown'].includes(e.key)?1:nodes.length-1))%nodes.length].focus();
    });
    map.append(stage);
  }
  function appendList(container,id){
    const li=el('li'),node=names.get(id),descendants=children.get(id)||[];
    if(descendants.length){const disclosure=el('details');disclosure.open=id===graph.root || selected===id || selected?.startsWith(id+'.');const summary=el('summary',node.title);disclosure.append(summary,button(node));const ul=el('ul');for(const child of descendants)appendList(ul,child);disclosure.append(ul);li.append(disclosure);}
    else li.append(button(node));container.append(li);
  }
  function close(updateUrl=true) { if(updateUrl){const u=new URL(location);u.searchParams.delete('node');history.replaceState({},'',u);} detailSequence++; panel.hidden=true; document.querySelector(`#skill-map [data-node="${selected}"]`)?.focus(); }
  async function choose(id, push=true) {
    selected=id; panel.hidden=false; if(push) { const u=new URL(location);u.searchParams.set('node',id);history.pushState({node:id},'',u); } render();
    const seq=++detailSequence; panel.hidden=false; panel.replaceChildren();
    const closeButton=el('button','Закрыть ×','detail-close');closeButton.onclick=close; panel.append(closeButton);
    const heading=el('h2',names.get(id).title);heading.id='detail-title';heading.tabIndex=-1; panel.append(el('p', 'ВАША СЛЕДУЮЩАЯ ВОЗМОЖНОСТЬ','eyebrow'),heading); heading.focus({preventScroll:true});
    if(matchMedia('(max-width:800px)').matches) panel.scrollIntoView({block:'start',behavior:'instant'});
    const body=el('div');panel.append(body);body.append(el('p','Загружаем материалы…'));
    try {
      const data=await api('/api/skills/nodes/'+encodeURIComponent(id)); if(seq!==detailSequence)return;
      body.replaceChildren(el('p',data.node.kind==='ability' ? 'Подтвердите этот навык заданием или начните с учебных материалов.' : 'Исследуйте навыки этого направления. Другие ветки всегда остаются открыты.'));
      const coverage=me.coverage.find(c=>c.node_id===id);
      body.append(el('p',evidenceLabel(coverage,'Понимание ещё не проверено'),'evidence-label'));
      if(data.readiness.length){const ready=el('details');ready.append(el('summary','Что поможет начать'));for(const edge of data.readiness)ready.append(el('p',`Будет полезно: ${names.get(edge.source)?.title}. Это рекомендация, не ограничение.`));body.append(ready);}
      if((children.get(id)||[]).length){const more=el('details');more.append(el('summary','Навыки этого раздела'));for(const child of children.get(id))more.append(button(names.get(child)));body.append(more);}
      if(data.content.length) for(const lesson of data.content){const a=el('a',`${lesson.title} · ${lesson.access==='free'?'Бесплатно':'Для участников'}`,'resource-link');a.href='/lessons/'+encodeURIComponent(lesson.id)+'?'+new URLSearchParams({node:id});body.append(a);}

      for(const pending of data.pending_attempts||[]){const a=el('a','Продолжить начатую проверку →','resource-link');a.href='/challenges?'+new URLSearchParams({node:pending.node_id,attempt:pending.id});body.append(a);}
      if(data.latest_completed_attempt){const saved=data.latest_completed_attempt,a=el('a','Сохранённый разбор →','resource-link');a.href='/challenges?'+new URLSearchParams({node:saved.node_id,attempt:saved.id});body.append(a);}
      for(const assessment of data.assessments.filter(a=>!a.pending_attempt)){const a=el('a',`${assessment.start_blocker==='sign_in'?'Войти для проверки':assessment.start_blocker==='access_required'?'Проверка для участников':assessment.start_mode==='practice'?'Тренировка · без нового зачёта':'Уже знаю тему'} → ${assessment.item_count} задания · ${assessment.access==='free'?'Бесплатно':'Для участников'}`,'resource-link');a.href='/challenges?'+new URLSearchParams({node:id,assessment:assessment.id});body.append(a);}
      let hasPractical=false;
      if(atlas.dataset.authenticated==='yes'&&data.node.kind==='ability'){const practical=await api('/api/skills/practical-tasks?node_id='+encodeURIComponent(id));if(seq!==detailSequence)return;if(practical.tasks.length){hasPractical=true;const a=el('a','Показать навык на практике →','resource-link');a.href='/practice?node='+encodeURIComponent(id);body.append(a);}}
      if(!data.content.length&&!data.assessments.length&&!data.pending_attempts?.length&&!hasPractical&&!(children.get(id)||[]).length){
        body.firstChild.textContent='Материалы и задания для этого навыка ещё готовятся.';
        const parent=parents.get(id)||graph.root,back=el('button','← '+names.get(parent).title);back.onclick=()=>choose(parent);body.append(back);
      }
      if((children.get(id)||[]).length){
        const descendants=[];function collect(parent){for(const child of children.get(parent)||[]){if(names.get(child).kind==='ability')descendants.push(child);collect(child);}}collect(id);
        const related=await Promise.all(descendants.slice(0,12).map(child=>api('/api/skills/nodes/'+encodeURIComponent(child))));if(seq!==detailSequence)return;
        const available=related.filter(d=>d.content.length||d.assessments.length).slice(0,3);
        if(available.length){const section=el('section');section.append(el('h3','Начать с навыка'));for(const d of available){const group=el('div');group.append(el('strong',d.node.title));if(d.content[0]){const a=el('a','Изучить →','resource-link');a.href='/lessons/'+encodeURIComponent(d.content[0].id)+'?'+new URLSearchParams({node:d.node.id});group.append(a);}if(d.assessments[0]){const a=el('a',d.assessments[0].pending_attempt?'Продолжить проверку →':d.assessments[0].start_mode==='practice'?'Тренировка · без нового зачёта →':'Проверить понимание →','resource-link');a.href='/challenges?'+new URLSearchParams({node:d.node.id,assessment:d.assessments[0].id});group.append(a);}section.append(group);}body.append(section);}
      }
      if(atlas.dataset.authenticated==='yes') { try {await api('/api/skills/explore',{node_id:id});}catch(e){body.append(el('p','Не удалось сохранить исследование. '+e.message));} }
      else {const a=el('a','Войти и сохранять своё развитие →');a.href='/login';body.append(a);}
    }catch(e){body.replaceChildren(el('p',e.message));const retry=el('button','Повторить');retry.onclick=()=>choose(id,false);body.append(retry);}
    // Loaded content can extend the document beyond the initial loading panel.
    if(seq===detailSequence && document.activeElement===heading && matchMedia('(max-width:800px)').matches) panel.scrollIntoView({block:'start',behavior:'instant'});
  }
  document.querySelector('#map-view').onclick=()=>view(false);
  document.querySelector('#list-view').onclick=()=>view(true);
  function view(value){list=value;document.querySelector('#map-view').setAttribute('aria-pressed',String(!value));document.querySelector('#list-view').setAttribute('aria-pressed',String(value));render();}
  document.querySelector('#map-reset').onclick=()=>{selected=null;search.value='';close();history.pushState({},'',location.pathname);render();};
  search.oninput=()=>{close();render();};document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
  window.addEventListener('popstate',()=>{const id=new URL(location).searchParams.get('node');if(names.has(id))choose(id,false);else{selected=null;close(false);render();}});
  async function load(){try{graph=await api('/api/skills/graph');for(const n of graph.nodes)names.set(n.id,n);for(const e of graph.edges.filter(e=>e.type==='contains')){children.set(e.source,[...(children.get(e.source)||[]),e.target]);parents.set(e.target,e.source);}if(atlas.dataset.authenticated==='yes')me=await api('/api/skills/me');render();const id=new URL(location).searchParams.get('node');if(names.has(id))choose(id,false);}catch(e){status.textContent=e.message;const retry=el('button','Повторить загрузку');retry.onclick=load;map.replaceChildren(retry);}}
  load();
})();
