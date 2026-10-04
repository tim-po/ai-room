(() => {
  const body=document.querySelector('#diagnostic-body'),status=document.querySelector('#diagnostic-status');
  const params=new URL(location).searchParams;
  let graph,names,current;
  const requests=new Map();
  const el=(tag,text)=>{const e=document.createElement(tag);if(text)e.textContent=text;return e;};
  const link=(text,url)=>{const a=el('a',text);a.href=url;return a;};
  async function api(path,value){
    let response;try{response=await fetch('/api/skills/'+path,value?{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name=csrf-token]').content},body:JSON.stringify(value)}:{});}catch{throw new Error('Нет связи с сервером. Повторите действие; сохранённая проверка останется в аккаунте.');}
    if(!response.ok)throw new Error(response.status===409?'Проверка изменилась в другой вкладке. Обновите сохранённое состояние.':response.status===401?'Войдите снова, чтобы продолжить проверку.':'Не удалось загрузить или сохранить проверку. Повторите действие.');
    return response.json();
  }
  function button(text,fn){const b=el('button',text);b.type='button';b.onclick=async()=>{b.disabled=true;try{await fn();}catch(e){status.textContent=e.message;}finally{b.disabled=false;}};return b;}
  function navigate(data){current=data;const url=new URL(location);url.search='';url.searchParams.set('id',data.id);history.replaceState({},'',url);render();document.querySelector('#diagnostic-title').focus();}
  function abilityList(title,ids){if(!ids.length)return;const details=el('details');details.append(el('summary',title+' · '+ids.length));const list=el('ul');for(const id of ids){const li=el('li');li.append(link(names.get(id)||id,'/?'+new URLSearchParams({node:id})));list.append(li);}details.append(list);body.append(details);}
  function render(){
    body.replaceChildren();const d=current;
    document.querySelector('#diagnostic-intro').textContent='Вся карта открыта. Можно учиться в нескольких направлениях и вернуться к проверке позже.';
    status.textContent=d.state==='active'?'Проверка сохранена. Можно вернуться позже.':d.state==='skipped'?'Проверка остановлена. Полученные подтверждения сохранены.':d.observations.length?'Доступные проверки завершены.':'Проверка сейчас недоступна. Результатов пока нет.';
    if(d.next){body.append(el('h2',names.get(d.next.node_id)||d.next.node_id),el('p',d.next.reason==='foundation'?'Начнём с общей основы: она пригодится в любом направлении.':'Следующий шаг связан с выбранными вами интересами.'));
      const query=new URLSearchParams({node:d.next.node_id,assessment:d.next.assessment_id,diagnostic:d.id});if(d.next.pending_attempt_id)query.set('attempt',d.next.pending_attempt_id);
      body.append(link(d.next.pending_attempt_id?'Продолжить задания →':'Открыть задания →','/challenges?'+query));
    }else body.append(link('Выбрать доступный урок →','/catalogue'),el('h2','Ваша точка старта'),el('p','Подтверждены только проверенные знания. Остальные темы можно изучать или проверить позже, когда появятся подходящие задания. Это не общий уровень владения AI.'));
    abilityList('Подтверждённые знания',d.verified_objectives);
    if(!d.verified_objectives.length)body.append(el('p','Подтверждений пока нет. Самооценка и выбранные интересы не дают зачёт.'));
    if(d.recommendations.length){const section=el('section');section.append(el('h2','Что полезно повторить'));const seen=new Set();for(const recommendation of d.recommendations){const key=JSON.stringify([recommendation.objective_id,recommendation.source]);if(seen.has(key))continue;seen.add(key);const p=el('p');p.append(link(names.get(recommendation.objective_id)||recommendation.objective_id,'/?'+new URLSearchParams({node:recommendation.objective_id})));section.append(p);window.appendAssessmentSource(section,recommendation.source);}body.append(section);}
    abilityList('Ещё не проверено',d.unknown_objectives);
    if(d.observations.length){const details=el('details');details.append(el('summary','Пройденные проверки'));for(const observation of d.observations){const p=el('p');p.append(link(observation.credited?'Знания зачтены →':observation.passed?'Тренировка без нового зачёта →':'Разобрать ответы →','/challenges?'+new URLSearchParams({attempt:observation.attempt_id,diagnostic:d.id})));details.append(p);}body.append(details);}
    const actions=el('div');actions.className='development-actions';actions.append(link('Исследовать карту →','/'),link('Моё развитие →','/profile'));
    if(d.state==='active')actions.append(button('Завершить без следующих заданий',async()=>navigate(await api(`diagnostics/${d.id}/advance`,{revision:d.revision,skip:true}))));
    actions.append(button('Обновить состояние',async()=>navigate(await api('diagnostics/'+d.id))));body.append(actions);
  }
  function setup(me,history){
    body.replaceChildren();status.textContent='Выберите несколько направлений или проверьте только основу.';
    for(const d of history.diagnostics.filter(d=>d.state==='active')){const p=el('p');p.append(link('Продолжить сохранённую проверку →','/diagnostic?'+new URLSearchParams({id:d.id})));body.append(p);}
    const field=el('fieldset');field.className='diagnostic-interests';field.append(el('legend','Что вам интересно?'));
    for(const node of graph.nodes.filter(n=>n.kind==='branch')){const label=el('label');label.className='interest-option family-'+node.id;const input=el('input');input.type='checkbox';input.value=node.id;input.checked=me.interests.includes(node.id);label.append(input,el('span',node.title));field.append(label);}body.append(field);
    body.append(el('p','До восьми проверок. Следующие темы зависят от уже подтверждённых знаний. Интересы этой проверки не меняют ваши настройки.'));
    body.append(button('Начать необязательную проверку',async()=>{const interests=[...field.querySelectorAll('input:checked')].map(i=>i.value);const key=JSON.stringify(interests);if(!requests.has(key))requests.set(key,crypto.randomUUID());navigate(await api('diagnostics',{request_id:requests.get(key),interests}));}));
    if(history.diagnostics.some(d=>d.state!=='active')){const details=el('details');details.append(el('summary','Предыдущие результаты'));for(const d of history.diagnostics.filter(d=>d.state!=='active')){const p=el('p');p.append(link(d.state==='skipped'?'Остановленная проверка →':'Результаты проверки →','/diagnostic?'+new URLSearchParams({id:d.id})));details.append(p);}body.append(details);}
  }
  async function load(){try{graph=await api('graph');names=new Map(graph.nodes.map(n=>[n.id,n.title]));if(params.get('id')){const d=await api('diagnostics/'+encodeURIComponent(params.get('id')));navigate(params.get('attempt')?await api(`diagnostics/${d.id}/advance`,{revision:d.revision,attempt_id:params.get('attempt')}):d);}else{const [me,history]=await Promise.all([api('me'),api('diagnostics')]);setup(me,history);}}catch(e){status.textContent=e.message;body.replaceChildren(button('Повторить загрузку',load),link('К карте навыков →','/'));}}
  load();
})();
