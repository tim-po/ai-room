(() => {
  const root = document.querySelector('[data-development]');
  if (!root) return;
  const status = document.querySelector('#development-status');
  const el = (tag, text, cls) => {const n=document.createElement(tag);if(text)n.textContent=text;if(cls)n.className=cls;return n;};
  const link = (title,id) => {const a=el('a',title);a.href='/?node='+encodeURIComponent(id);return a;};
  async function api(url,body) {
    const response=await fetch(url,body ? {method:'PUT',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify(body)} : {});
    if(!response.ok)throw new Error(response.status===401?'Сессия завершилась. Войдите снова.':'Не удалось сохранить или загрузить данные. Повторите попытку.');
    return response.json();
  }
  function character(graph,me) {
    const nodes=new Map(graph.nodes.map(n=>[n.id,n]));
    const coverage=new Map(me.coverage.map(c=>[c.node_id,c]));
    const next=document.querySelector('#character-next');next.replaceChildren();
    const latest=me.explorations.find(e=>nodes.has(e.node_id));
    next.append(el('h2',me.evidence.length?'Продолжайте развивать свои навыки':'Здесь появятся ваши подтверждённые навыки'));
    next.append(el('p',me.evidence.length?'Можно развивать несколько направлений одновременно.':'Пока знаний недостаточно для оценки. Исследуйте карту и начните с интересующей темы.'));
    next.append(link(latest?'Вернуться: '+nodes.get(latest.node_id).title:'Исследовать общую основу →',latest?.node_id||graph.root));
    const branches=document.querySelector('#character-branches');branches.replaceChildren();
    function row(node) {
      const c=coverage.get(node.id),r=el('div',null,'ability-coverage');r.append(link(node.title,node.id));
      r.append(el('span',c.verified?`Подтверждено ${c.verified} из ${c.eligible}`:c.assessed?'Есть проверенные темы; подтверждений пока нет':'Ещё не проверено'));
      if(c.verified){const meter=el('meter');meter.min=0;meter.max=c.eligible;meter.value=c.verified;meter.setAttribute('aria-label',node.title+': подтверждённые навыки');r.append(meter);}
      return r;
    }
    for(const branch of graph.nodes.filter(n=>n.kind==='branch')) {
      const section=el('section',null,'character-branch family-'+branch.id);section.append(el('h2',branch.title));
      const c=coverage.get(branch.id);
      section.append(el('p',c.verified?`${c.verified} из ${c.eligible} навыков подтверждено`:'Знания ещё не подтверждены','branch-strength'));
      const details=el('details');details.append(el('summary','Навыки направления'));
      details.append(el('p',`Не проверено: ${c.unknown} · Применение подтверждено: ${c.application_verified}`,'small'));
      for(const edge of graph.edges.filter(e=>e.type==='contains'&&e.source===branch.id)) {
        const group=el('div',null,'coverage-group');group.append(row(nodes.get(edge.target)));
        for(const child of graph.edges.filter(e=>e.type==='contains'&&e.source===edge.target))group.append(row(nodes.get(child.target)));
        details.append(group);
      }
      section.append(details);branches.append(section);
    }
    const evidence=document.querySelector('#character-evidence');evidence.replaceChildren();
    if(!me.evidence.length)evidence.append(el('p','Пока нет подтверждений. Пройденные уроки и ваши работы сохранены ниже.'));
    for(const item of me.evidence){const p=el('p');p.append(link(nodes.get(item.objective_id)?.title||item.objective_id,item.objective_id));p.append(el('small',` · Редакция навыка ${item.objective_revision}`));evidence.append(p);}
    status.textContent='Данные сохранены в вашем аккаунте.';
  }
  function interests(graph,me) {
    const options=document.querySelector('#interest-options');options.replaceChildren();
    for(const branch of graph.nodes.filter(n=>n.kind==='branch')) {
      const label=el('label',null,'interest-option family-'+branch.id),input=el('input');input.type='checkbox';input.value=branch.id;input.name='interest';input.checked=me.interests.includes(branch.id);
      label.append(input,el('span',branch.title));options.append(label);
    }
    const first=document.querySelector('#interest-step'),second=document.querySelector('#pace-step');
    const next=document.querySelector('#interest-next');next.disabled=false;next.onclick=()=>{first.hidden=true;second.hidden=false;second.querySelector('legend').focus();};
    document.querySelector('#interest-back').onclick=()=>{second.hidden=true;first.hidden=false;next.focus();};
    status.textContent='Интересы можно менять: результаты обучения сохранятся.';
    document.querySelector('#interest-form').onsubmit=async event=>{
      event.preventDefault();const save=document.querySelector('#interest-save'),message=document.querySelector('#interest-save-status');save.disabled=true;message.textContent='Сохраняем интересы…';
      // Preserve deeper interests that this branch-only editor does not expose.
      const branchIds=new Set(graph.nodes.filter(n=>n.kind==='branch').map(n=>n.id));
      const selected=[...options.querySelectorAll('input:checked')].map(n=>n.value);
      try {await api('/api/skills/interests',{node_ids:[...me.interests.filter(id=>!branchIds.has(id)),...selected]});event.target.submit();}
      catch(error){message.textContent=error.message;save.disabled=false;}
    };
  }
  async function load(){try{const [graph,me]=await Promise.all([api('/api/skills/graph'),api('/api/skills/me')]);if(root.dataset.development==='character')character(graph,me);else interests(graph,me);}catch(error){status.replaceChildren(el('span',error.message+' '));const retry=el('button','Повторить');retry.onclick=load;status.append(retry);}}
  load();
})();
