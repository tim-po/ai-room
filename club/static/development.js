(() => {
  const root = document.querySelector('[data-development]');
  if (!root) return;
  const status = document.querySelector('#development-status');
  const el = (tag, text, cls) => {const n=document.createElement(tag);if(text)n.textContent=text;if(cls)n.className=cls;return n;};
  const link = (title,id) => {const a=el('a',title);a.href='/?node='+encodeURIComponent(id);return a;};
  async function api(url,body) {
    const response=await fetch(url,body ? {method:'PUT',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify(body)} : {}).catch(()=>{throw new Error('Нет связи с сервером. Повторите попытку.');});
    if(!response.ok)throw new Error(response.status===401?'Сессия завершилась. Войдите снова.':'Не удалось сохранить или загрузить данные. Повторите попытку.');
    return response.json();
  }
  function character(graph,me) {
    const nodes=new Map(graph.nodes.map(n=>[n.id,n]));
    const coverage=new Map(me.coverage.map(c=>[c.node_id,c]));
    const application=me.application_evidence||[];
    const hasEvidence=me.evidence.length>0||application.length>0;
    const next=document.querySelector('#character-next');next.replaceChildren();
    const latest=me.explorations.find(e=>nodes.has(e.node_id));
    next.append(el('h2',hasEvidence?'Продолжайте развивать свои навыки':'Здесь появятся ваши подтверждённые навыки'));
    next.append(el('p',hasEvidence?'Можно развивать несколько направлений одновременно.':'Пока не собрано свидетельств о ваших знаниях. Исследуйте карту и начните с интересующей темы.'));
    next.append(link(latest?'Вернуться: '+nodes.get(latest.node_id).title:'Исследовать общую основу →',latest?.node_id||graph.root));
    const diagnostic=el('p');const diagnosticLink=el('a','Найти точку старта · необязательная проверка →');diagnosticLink.href='/diagnostic';diagnostic.append(diagnosticLink);next.append(diagnostic);
    const recent=document.querySelector('#character-recent');recent.replaceChildren();recent.hidden=!hasEvidence;
    const dateOf=item=>new Date((item.assessed_at||item.reviewed_at).replace(' ','T').replace(/Z?$/,'Z'));
    function evidenceRow(item){
      const entry=el('li'),title=nodes.get(item.objective_id)?.title||item.objective_id;
      entry.append(link(title,item.objective_id));
      const date=el('time',dateOf(item).toLocaleDateString('ru-RU'));date.dateTime=dateOf(item).toISOString();entry.append(date);
      const result=el('a',item.submission_id?'Проверенная работа →':'Результат проверки →');result.href=item.submission_id?'/practice?submission='+encodeURIComponent(item.submission_id):'/challenges?'+new URLSearchParams({node:item.objective_id,attempt:item.attempt_id});result.setAttribute('aria-label','Результат проверки: '+title);entry.append(result);return entry;
    }
    const ordered=[...me.evidence,...application].sort((a,b)=>dateOf(b)-dateOf(a));
    if(ordered.length){recent.append(el('h2','Недавно подтверждено'));const list=el('ul');for(const item of ordered.slice(0,3))list.append(evidenceRow(item));recent.append(list);}
    const branches=document.querySelector('#character-branches');branches.replaceChildren();
    function understanding(c) {return c.verified?`Понимание: подтверждено ${c.verified} из ${c.eligible}`:c.assessed?'Понимание: проверено, пока не подтверждено':'Понимание: ещё не проверено';}
    function applicationSummary(c) {return c.application_verified?`Применение: подтверждено ${c.application_verified} из ${c.eligible}`:'Применение: ещё не подтверждено';}
    function summary(parent,c) {parent.append(el('p',understanding(c),'branch-strength'),el('p',applicationSummary(c),'small'));}
    function row(node) {
      const c=coverage.get(node.id),r=el('div',null,'ability-coverage');r.append(link(node.title,node.id));
      r.append(el('span',understanding(c)),el('span',applicationSummary(c)));
      if(c.verified){const meter=el('meter');meter.min=0;meter.max=c.eligible;meter.value=c.verified;meter.setAttribute('aria-label',node.title+': подтверждённые навыки');r.append(meter);}
      return r;
    }
    const foundation=el('section',null,'character-branch');foundation.append(el('h2','Базовые знания об AI'));const f=me.foundation_coverage;summary(foundation,f);foundation.append(link('Исследовать основу →',graph.root));branches.append(foundation);
    for(const branch of graph.nodes.filter(n=>n.kind==='branch')) {
      const section=el('section',null,'character-branch family-'+branch.id);section.append(el('h2',branch.title));
      const c=coverage.get(branch.id);
      summary(section,c);
      const details=el('details');details.append(el('summary','Навыки направления'));
      details.append(el('p',`Понимание ещё не проверено у ${c.unknown} из ${c.eligible} навыков`,'small'));
      for(const edge of graph.edges.filter(e=>e.type==='contains'&&e.source===branch.id)) {
        const group=el('div',null,'coverage-group');group.append(row(nodes.get(edge.target)));
        function descendants(id){for(const child of graph.edges.filter(e=>e.type==='contains'&&e.source===id)){group.append(row(nodes.get(child.target)));descendants(child.target);}}descendants(edge.target);
        details.append(group);
      }
      section.append(details);branches.append(section);
    }
    const evidence=document.querySelector('#character-evidence');evidence.replaceChildren();
    if(!me.evidence.length)evidence.append(el('p','Понимание ещё не подтверждено проверкой. Пройденные уроки и практические работы сохраняются отдельно.'));
    for(const item of me.evidence){const p=el('p');p.append(link(nodes.get(item.objective_id)?.title||item.objective_id,item.objective_id));p.append(el('small',` · ${new Date((item.assessed_at||item.reviewed_at).replace(' ','T')+'Z').toLocaleDateString('ru-RU')} · Редакция навыка ${item.objective_revision}`));const result=el('a',' Посмотреть результат →');result.href='/challenges?'+new URLSearchParams({node:item.objective_id,attempt:item.attempt_id});p.append(result);evidence.append(p);}
    const applied=document.querySelector('#character-application');applied.replaceChildren(el('h2','Подтверждённое применение'));
    if(!me.application_evidence?.length)applied.append(el('p','Проверенных практических результатов пока нет.'));
    for(const item of me.application_evidence||[]){const p=el('p');p.append(link(nodes.get(item.objective_id)?.title||item.objective_id,item.objective_id));const a=el('a',' · Работа и решение преподавателя →');a.href='/practice?submission='+encodeURIComponent(item.submission_id);p.append(el('small',' · Проверено '+dateOf(item).toLocaleDateString('ru-RU')+(item.reviewer?.attribution==='recorded_reviewer_alias'?' · '+item.reviewer.display_name+' (псевдоним)':'')),a);applied.append(p);}
    status.textContent='Данные сохранены в вашем аккаунте.';
  }
  function interests(graph,me) {
    const options=document.querySelector('#interest-options');options.replaceChildren();
    for(const branch of graph.nodes.filter(n=>n.kind==='branch')) {
      const label=el('label',null,'interest-option family-'+branch.id),input=el('input');input.type='checkbox';input.value=branch.id;input.name='interest';input.checked=me.interests.includes(branch.id);
      label.append(input,el('span',branch.title));options.append(label);
    }
    const first=document.querySelector('#interest-step'),second=document.querySelector('#pace-step');
    const next=document.querySelector('#interest-next'),save=document.querySelector('#interest-save');
    const message=document.querySelector('#interest-save-status');
    const branchIds=new Set(graph.nodes.filter(n=>n.kind==='branch').map(n=>n.id));
    let saving=false;
    async function saveInterests(targetStatus) {
      if(saving)return false;
      saving=true;next.disabled=true;save.disabled=true;
      const inputs=[...options.querySelectorAll('input')];
      const selected=inputs.filter(n=>n.checked).map(n=>n.value);
      inputs.forEach(n=>n.disabled=true);
      targetStatus.textContent='Сохраняем интересы…';
      try {
        // Preserve current deeper interests that this branch-only editor does not expose.
        const current=await api('/api/skills/me');
        const result=await api('/api/skills/interests',{node_ids:[...current.interests.filter(id=>!branchIds.has(id)),...selected]});
        me.interests=result.interests;
        targetStatus.textContent='Интересы сохранены в аккаунте. Результаты обучения не изменились.';
        return true;
      } catch(error) {
        targetStatus.textContent=error.message+' Ваш выбор остаётся на экране. Повторите сохранение.';
        targetStatus.tabIndex=-1;targetStatus.focus();
        return false;
      } finally {
        saving=false;next.disabled=false;save.disabled=false;
        inputs.forEach(n=>n.disabled=false);
      }
    }
    next.disabled=false;
    next.onclick=async()=>{
      if(!await saveInterests(status))return;
      first.hidden=true;second.hidden=false;
      message.textContent='Интересы сохранены. Теперь можно настроить удобный темп.';
      second.querySelector('legend').focus();
    };
    document.querySelector('#interest-back').onclick=()=>{if(saving)return;second.hidden=true;first.hidden=false;first.querySelector('legend').focus();};
    status.textContent='Интересы сохранятся при нажатии «Сохранить интересы и продолжить».';
    document.querySelector('#interest-form').onsubmit=async event=>{
      event.preventDefault();
      if(await saveInterests(message)){save.disabled=true;event.target.submit();}
    };
  }
  async function load(){try{const [graph,me]=await Promise.all([api('/api/skills/graph'),api('/api/skills/me')]);if(root.dataset.development==='character')character(graph,me);else interests(graph,me);}catch(error){status.replaceChildren(el('span',error.message+' '));const retry=el('button','Повторить');retry.onclick=load;status.append(retry);}}
  load();
})();
