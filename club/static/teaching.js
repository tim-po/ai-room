(() => {
  const status=document.querySelector('#teacher-status'),jobs=document.querySelector('#teacher-jobs'),review=document.querySelector('#teacher-review');
  const csrf=document.querySelector('meta[name=csrf-token]').content;
  const el=(tag,text)=>{const e=document.createElement(tag);if(text)e.textContent=text;return e;};
  const states={queued:'Ожидает обработки',running:'AI обрабатывает источники',blocked:'Обработка недоступна',failed:'Обработка не завершена',cancelled:'Обработка остановлена',ready:'Готово к проверке'};
  let abilities=[],names=new Map(),current,dirty=false,uploads=new Map(),retained=new Map(),selectedSources=new Set();
  async function api(path,method='GET',body,headers={}){
    let r;try{r=await fetch('/api/teaching/'+path,{method,headers:{'X-CSRF-Token':csrf,...(body instanceof FormData?{}:{'Content-Type':'application/json'}),...headers},...(body?{body:body instanceof FormData?body:JSON.stringify(body)}:{})});}catch{throw new Error('Нет связи с сервером. Ваши изменения остаются на странице.');}
    const data=await r.json().catch(()=>({}));if(!r.ok)throw new Error(r.status===409?'Данные изменились. Откройте сохранённый черновик заново перед повторной правкой.':r.status===403?'Недостаточно прав. Войдите как преподаватель.':data.message||'Не удалось выполнить действие. Повторите попытку.');return data;
  }
  function action(label,fn){const b=el('button',label);b.type='button';b.onclick=async()=>{b.disabled=true;try{await fn();}catch(e){status.textContent=e.message;}finally{b.disabled=false;}};return b;}
  function editable(parent,title,build){const section=el('details');section.className='teacher-edit';section.append(el('summary','Изменить · '+title));build(section);parent.append(section);}
  function field(parent,label,value,change,multiline=false,track=true){const l=el('label',label),input=el(multiline?'textarea':'input');input.value=value;input.oninput=()=>{change(input.value);if(track){dirty=true;status.textContent='Есть несохранённые изменения.';}};l.append(input);parent.append(l);return input;}
  function refs(parent,items,sources){
    const d=el('details');d.append(el('summary','Проверить по источнику'));
    for(const [index,ref] of (items||[]).entries()){
      const label=el('label','Источник · ссылка '+(index+1)),select=el('select'),excerpt=el('p');
      select.setAttribute('aria-label','Источник · ссылка '+(index+1));const anchors=[];
      for(const source of sources)for(const paragraph of source.paragraphs){
        const anchor={source_id:source.source_id,edition:source.edition,sha256:source.sha256,paragraph:paragraph.paragraph};
        const option=el('option',`${source.filename} · абзац ${paragraph.paragraph}${paragraph.start!==undefined?' · '+paragraph.start+' сек.':''}`);
        option.value=String(anchors.length);anchors.push({anchor,text:paragraph.text});select.append(option);
        if(ref.source_id===anchor.source_id&&ref.paragraph===anchor.paragraph)option.selected=true;
      }
      const show=()=>{excerpt.textContent=anchors[Number(select.value)]?.text||'Источник недоступен';};show();
      select.onchange=()=>{items[index]={...anchors[Number(select.value)].anchor};dirty=true;status.textContent='Источник изменён. Сохраните правки.';show();};
      label.append(select);d.append(label,excerpt);
    }parent.append(d);
  }
  async function decision(payload){
    if(dirty)throw new Error('Сначала сохраните или отмените правки. Решение изменит сохранённую версию.');
    const saved=await api(`jobs/${current.job_id}/review`,'POST',{revision:current.revision,action:payload});
    current=saved;dirty=false;render();
    const removed=saved.review_changes?.removed_assessments||[];
    status.textContent='Решение сохранено.'+(removed.length?' Удалены проверки: '+removed.map(id=>names.get(id)||id).join(', ')+'.':'');
    review.querySelector('h2').focus();
  }
  function decisionControl(parent,label,explanation,payload){
    const detail=el('details');detail.className='teacher-edit';detail.append(el('summary',label),el('p',explanation));
    detail.append(action('Подтвердить: '+label.toLowerCase(),()=>decision(typeof payload==='function'?payload():payload)));parent.append(detail);
  }
  function coverage(parent,data){
    const section=el('section');section.className='teacher-coverage';section.setAttribute('aria-label','Результат публикации');
    section.append(el('h3',data.challenge_available?'Урок с проверкой знаний':'Только учебный материал'));
    section.append(el('p',data.mapped?'Урок появится на выбранных навыках.':'Урок появится в каталоге без привязки к карте.'));
    if(!data.challenge_available)section.append(el('p','Публикация не создаст новую проверку и не подтвердит знания ученика.'));
    if(data.unassessed_objectives?.length)section.append(el('p','Без новой проверки: '+data.unassessed_objectives.map(id=>names.get(id)||id).join(', ')+'.'));
    parent.append(section);
  }
  async function list(){const data=await api('jobs');
    retained=new Map(data.jobs.filter(j=>j.error_code==='awaiting_package').map(j=>[j.id,j]));
    selectedSources=new Set([...selectedSources].filter(id=>retained.has(id)));
    const saved=document.querySelector('#teacher-saved-sources');saved.replaceChildren();saved.hidden=!retained.size;
    if(retained.size){saved.append(el('legend','Продолжить незавершённую загрузку'),el('p','Эти файлы уже сохранены. Выберите нужные и при необходимости добавьте недостающие файлы выше.'));
      for(const job of retained.values()){const label=el('label'),check=el('input');check.type='checkbox';check.value=job.id;check.checked=selectedSources.has(job.id);check.onchange=()=>{if(check.checked)selectedSources.add(job.id);else selectedSources.delete(job.id);};label.append(check,el('span',job.filename));saved.append(label);}}
    jobs.replaceChildren();for(const job of data.jobs.filter(j=>!['included_in_package','awaiting_package'].includes(j.error_code))){const row=el('article');row.className='teacher-job';row.append(el('h3',job.filename),el('p',states[job.state]||job.state));if(job.error_code)row.append(el('p',job.error_code==='awaiting_package'?'Источник сохранён. Можно обработать отдельно.':job.state==='blocked'?'Для AI нужен настроенный провайдер. Источник сохранён.':'Источники сохранены; проверьте настройки обработки перед повтором.'));
    if(job.state==='ready')row.append(action('Открыть проверку',()=>open(job.id)));
    if(['queued','running'].includes(job.state))row.append(action('Остановить обработку',async()=>{await api(`jobs/${job.id}/cancel`,'POST',{revision:job.revision});await list();}));
    if(['failed','blocked','cancelled'].includes(job.state)){const label=el('label'),check=el('input');check.type='checkbox';label.append(check,el('span','При повторе возможна повторная оплата запроса к AI'));row.append(label,action('Повторить обработку',async()=>{await api(`jobs/${job.id}/retry`,'POST',{revision:job.revision,acknowledge_possible_charge:check.checked});await list();}));}
    jobs.append(row);}if(!jobs.children.length)jobs.append(el('p','Здесь появятся ваши загруженные материалы и черновики.'));}
  async function open(id){if(dirty){status.textContent='Сначала сохраните открытый черновик или отмените правки.';return;}current=await api(`jobs/${id}/draft`);render();review.querySelector('h2').focus();}
  async function practicalApproval(parent,d,publication){
    const section=el('section');section.className='teacher-preview';parent.append(section);
    section.append(el('h3','Практика с проверкой преподавателем'),el('p','Предложение AI ещё не даёт подтверждения навыка. Проверьте, что работа демонстрирует именно выбранное умение. Для выполнения действий нужны наблюдения и результат, а не только план.'));
    async function skillApi(path,method='GET',value){const r=await fetch('/api/skills/'+path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},...(value?{body:JSON.stringify(value)}:{})});if(!r.ok)throw Error(r.status===409?'Версия навыков изменилась. Обновите страницу перед утверждением.':'Не удалось утвердить задание. Проверьте: инструкция от 30 символов, 2–12 критериев от 10 символов.');return r.json();}
    try{const existing=(await skillApi('practical-tasks')).tasks;
      if(!d.assessments.length){section.append(el('p','Урок опубликован без проверки знаний. Практическую рубрику пока нельзя привязать к проверенному навыку.'));return;}
      for(const [index,form] of d.assessments.entries()){
        const assessmentId=publication.lesson_id+'-form-'+index;
        const approved=existing.find(t=>t.assessment_id===assessmentId&&t.objective_id===form.node_id);
        const card=el('details');card.append(el('summary',names.get(form.node_id)||form.node_id));section.append(card);
        if(approved){const a=el('a','Практическое задание утверждено · открыть →');a.href='/practice?node='+encodeURIComponent(form.node_id);card.append(a);continue;}
        let instructions=d.practice.instructions,criteria=d.practice.checklist.join('\n');
        field(card,'Задание для демонстрации навыка',instructions,v=>instructions=v,true,false);
        field(card,'Критерии наблюдаемого результата — по одному на строку',criteria,v=>criteria=v,true,false);
        const label=el('label'),check=el('input');check.type='checkbox';label.append(check,el('span','Каждый критерий проверяем по работе и относится к этому навыку.'));card.append(label);
        card.append(action('Утвердить практическое задание',async()=>{
          if(!check.checked)throw Error('Подтвердите соответствие критериев навыку.');
          // Reconcile a lost response before issuing a second publication request.
          const saved=(await skillApi('practical-tasks')).tasks.find(t=>t.assessment_id===assessmentId&&t.objective_id===form.node_id);
          if(!saved)await skillApi('practical-tasks','POST',{assessment_id:assessmentId,objective_id:form.node_id,instructions,criteria:criteria.split('\n').map(t=>t.trim()).filter(Boolean).map((text,i)=>({id:'criterion-'+(i+1),text})),confirm_reviewed:true});
          card.replaceChildren(el('summary',names.get(form.node_id)||form.node_id),el('p','Практическое задание утверждено. Ученики могут отправить работу на проверку.'));status.textContent='Рубрика опубликована. Решения по работам доступны в очереди проверки.';
        }));
      }
    }catch(e){section.append(el('p',e.message),action('Повторить загрузку рубрики',async()=>{section.remove();await practicalApproval(parent,d,publication);}));}
  }
  function render(){document.querySelector('#teacher-intake').hidden=true;document.querySelector('#teacher-introduction').hidden=true;review.hidden=false;review.replaceChildren();const d=current.draft;
    review.append(action('← К загрузкам и черновикам',async()=>{if(dirty)throw new Error('Сохраните или отмените правки перед выходом.');review.before(status);review.hidden=true;document.querySelector('#teacher-intake').hidden=false;document.querySelector('#teacher-introduction').hidden=false;current=null;await list();document.querySelector('#teacher-refresh').focus();}));
    const heading=el('h2','Проверка перед публикацией');heading.tabIndex=-1;review.append(heading);if(current.publication){const a=el('a','Открыть опубликованный урок →');a.href='/lessons/'+encodeURIComponent(current.publication.lesson_id);review.append(a,status);practicalApproval(review,d,current.publication);return;}
    const title=el('h3',d.title),summary=el('p',d.summary);review.append(title,summary);coverage(review,current.coverage);
    editable(review,'название и описание',section=>{field(section,'Название урока',d.title,v=>{d.title=v;title.textContent=v;});field(section,'Что узнает ученик',d.summary,v=>{d.summary=v;summary.textContent=v;},true);});
    const placement=el('details');placement.open=true;placement.append(el('summary','Место на карте и учебный результат'));for(const o of d.outcomes){const block=el('div');block.append(el('h3',names.get(o.objective_id)||o.objective_id));const explanation=el('p',o.explanation);block.append(explanation);editable(block,'учебный результат',section=>field(section,'Результат обучения',o.explanation,v=>{o.explanation=v;explanation.textContent=v;},true));refs(block,o.refs,current.sources);
      const mapping=el('details');mapping.className='teacher-edit';mapping.append(el('summary','Изменить навык'));
      const label=el('label','Существующий навык'),select=el('select');
      select.setAttribute('aria-label','Существующий навык');for(const node of abilities.filter(n=>n.id===o.objective_id||!d.outcomes.some(other=>other.objective_id===n.id))){const option=el('option',node.title);option.value=node.id;select.append(option);}select.value=o.objective_id;label.append(select);mapping.append(label,el('p','Смена навыка удалит его текущую проверку: прежние вопросы нельзя автоматически засчитать за другой результат. Урок можно опубликовать без проверки.'));
      mapping.append(action('Сохранить новый навык',()=>{if(select.value===o.objective_id)throw new Error('Выберите другой навык.');return decision({kind:'remap_outcome',objective_id:o.objective_id,target_id:select.value});}));block.append(mapping);
      decisionControl(block,'Отклонить результат','Будут удалены привязка к навыку и его проверка. Если это последний результат, материал останется доступен для публикации в каталоге.',{kind:'reject_outcome',objective_id:o.objective_id});placement.append(block);}for(const p of d.skill_proposals)placement.append(el('p',(p.kind==='new'?'Предложен новый навык (не публикуется автоматически): ':'Используется существующий навык: ')+(names.get(p.objective_id)||p.objective_id)+' — '+p.explanation));const treeLink=el('a','Рассмотреть изменение общего дерева →');treeLink.href='/admin/tree?job='+encodeURIComponent(current.job_id)+'&revision='+current.revision;placement.append(treeLink);review.append(placement);
    const content=el('details');content.append(el('summary','Текст урока и практика'));field(content,'Текст урока',d.body,v=>d.body=v,true);field(content,'Практическое задание',d.practice.instructions,v=>d.practice.instructions=v,true);field(content,'Критерии результата — по одному на строку',d.practice.checklist.join('\n'),v=>d.practice.checklist=v.split('\n').filter(Boolean),true);refs(content,d.practice.refs,current.sources);review.append(content);
    const assessment=el('details');assessment.append(el('summary','Проверить вопросы и правильные ответы'));for(const form of d.assessments){assessment.append(el('h3',names.get(form.node_id)||form.node_id));decisionControl(assessment,'Убрать проверку','Урок сохранится. Эта публикация не создаст проверку по этому навыку.',{kind:'remove_assessment',objective_id:form.node_id});for(const item of form.items){const block=el('fieldset');field(block,'Вопрос',item.prompt,v=>item.prompt=v,true);for(const choice of item.choices)field(block,'Вариант '+choice.id,choice.text,v=>choice.text=v);const label=el('label','Правильный ответ'),select=el('select');for(const choice of item.choices){const opt=el('option',choice.id);opt.value=choice.id;select.append(opt);}select.value=item.answer;select.onchange=()=>{item.answer=select.value;dirty=true;};label.append(select);block.append(label);field(block,'Объяснение ответа',item.rationale,v=>item.rationale=v,true);refs(block,item.refs,current.sources);decisionControl(block,'Отклонить вопрос','Если оставшихся независимых заданий недостаточно, вся проверка навыка будет удалена. Урок и прежняя версия черновика сохранятся.',{kind:'remove_question',objective_id:form.node_id,item_id:item.id});assessment.append(block);}}review.append(assessment);
    for(const warning of d.warnings)review.append(el('p',warning));
    const actions=el('div');actions.className='development-actions teacher-review-actions';actions.append(action('Сохранить правки',async()=>{current=await api(`jobs/${current.job_id}/draft`,'PUT',{revision:current.revision,draft:d});dirty=false;status.textContent='Правки сохранены.';render();}),action('Отменить правки',async()=>{const saved=await api(`jobs/${current.job_id}/draft`);current=saved;dirty=false;status.textContent='Правки отменены.';render();}),action('Предпросмотр ученика',async()=>{if(dirty)throw new Error('Сохраните правки перед предпросмотром.');const data=await api(`jobs/${current.job_id}/preview`);preview.replaceChildren(el('h3',data.title),el('p',data.body));coverage(preview,data.coverage);for(const f of data.assessments)for(const item of f.items){preview.append(el('h4',item.prompt));for(const c of item.choices)preview.append(el('p',c.text));}preview.hidden=false;}));actions.prepend(status);review.append(actions);
    const preview=el('section');preview.hidden=true;preview.className='teacher-preview';review.append(preview);
    const publish=el('form'),access=el('select');access.name='access';for(const [v,t] of [['free','Бесплатно'],['member','Для участников']]){const o=el('option',t);o.value=v;access.append(o);}const al=el('label','Доступ к уроку');al.append(access);publish.append(al);const note=field(publish,'Краткий итог редакторской проверки','',()=>{},true,false);note.required=true;const check=el('input');check.type='checkbox';check.required=true;const label=el('label');label.append(check,el('span','Я проверил источники, учебные результаты и правильность заданий.'));publish.append(label,el('p','Публикация создаст урок с указанным выше покрытием проверок. Новые ветки требуют отдельного рассмотрения.'));const button=el('button','Опубликовать урок');button.type='submit';publish.append(button);publish.onsubmit=async e=>{e.preventDefault();button.disabled=true;try{if(dirty)throw new Error('Сохраните правки перед публикацией.');await api(`jobs/${current.job_id}/publish`,'POST',{revision:current.revision,confirm_reviewed:check.checked,access:access.value,review_note:note.value});status.textContent='Урок опубликован.';await open(current.job_id);await list();}catch(e){status.textContent=e.message;}finally{button.disabled=false;}};const publication=el('details');publication.className='teacher-publication';publication.append(el('summary','Доступ и публикация'),publish);review.append(publication);
  }
  document.querySelector('#teacher-upload').onsubmit=async e=>{e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;try{const files=[...document.querySelector('#teacher-files').files];if(files.length+selectedSources.size>5)throw new Error('Выберите не более пяти файлов, включая сохранённые.');const sources=[...selectedSources].map(id=>retained.get(id));if(!files.length&&!sources.length)throw new Error('Выберите файл или сохранённый источник.');for(const file of files){status.textContent='Сохраняем '+file.name+'…';const key=[file.name,file.size,file.lastModified].join(':');if(!uploads.has(key))uploads.set(key,{key:crypto.randomUUID()});const cached=uploads.get(key);if(!cached.job){const form=new FormData();form.append('file',file);form.append('defer_processing','1');cached.job=await api('uploads','POST',form,{'Idempotency-Key':cached.key});}if(!sources.some(s=>s.upload_id===cached.job.upload_id))sources.push(cached.job);}const first=sources[0];await api(`jobs/${first.id}/package`,'POST',{revision:first.revision,upload_ids:sources.map(s=>s.upload_id)});uploads.clear();selectedSources.clear();e.target.reset();status.textContent='Источники сохранены и переданы на обработку. Можно вернуться к ним позже.';await list();}catch(e){status.textContent=e.message;await list().catch(()=>{});}finally{button.disabled=false;}};
  document.querySelector('#teacher-refresh').onclick=()=>list().catch(e=>status.textContent=e.message);
  window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
  Promise.all([api('capabilities'),fetch('/api/skills/graph').then(r=>r.json())]).then(async([cap,g])=>{abilities=g.nodes.filter(n=>n.kind==='ability');names=new Map(g.nodes.map(n=>[n.id,n.title]));document.querySelector('#teacher-capability').textContent=cap.processing_available?'AI настроен. Обработка выполняется серверной очередью.':'AI пока не настроен. Файлы можно сохранить; создание черновика станет доступно после подключения провайдера.';await list();}).catch(e=>status.textContent=e.message);
})();
