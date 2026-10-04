(() => {
  const body=document.querySelector('#graph-body'),status=document.querySelector('#graph-status'),recovery=document.querySelector('#graph-recovery');
  const params=new URLSearchParams(location.search),states={draft:'Черновик',active:'Опубликовано',rejected:'Отклонено',rolled_back:'Отменено'};
  let dirty=false;
  const el=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
  const link=(text,url)=>{const n=el('a',text);n.href=url;return n;};
  async function api(path,method='GET',value){let r;try{r=await fetch('/api/skills/'+path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name=csrf-token]').content},...(value?{body:JSON.stringify(value)}:{})});}catch{throw Error('Нет связи. Правки остаются на странице. Повторите действие.');}if(r.status===409&&params.has('proposal'))recovery.hidden=false;if(!r.ok)throw Error(r.status===409?(params.has('proposal')?'Версия изменилась. Ваши правки остаются на странице. Скопируйте нужный текст, затем загрузите сохранённую версию кнопкой ниже. Для устаревшего дерева создайте новое предложение.':'Дерево изменилось. Скопируйте пояснение и обновите страницу, чтобы создать предложение от текущего дерева.'):r.status===400?'Проверьте название, связи и пояснение. Дерево должно оставаться связным, без циклов и дубликатов.':r.status===401?'Войдите снова, чтобы продолжить.':'Не удалось выполнить действие. Проверьте доступ и повторите попытку.');return r.json();}
  const action=(text,fn)=>{const b=el('button',text);b.type='button';b.onclick=async()=>{b.disabled=true;try{await fn();}catch(e){status.textContent=e.message;status.focus();}finally{b.disabled=false;}};return b;};
  function field(parent,title,value='',tag='input'){const l=el('label',title),n=el(tag);n.setAttribute('aria-label',title);n.value=value;n.oninput=()=>dirty=true;l.append(n);parent.append(l);return n;}
  function select(parent,title,options,value){const s=field(parent,title,'','select');for(const [id,text] of options){const o=el('option',text);o.value=id;s.append(o);}if(value)s.value=value;return s;}
  function disclosure(title,parent=body){const d=el('details');d.append(el('summary',title));parent.append(d);return d;}
  function availability(value,title){
    const section=el('section');section.className='practical-rubric';section.append(el('h3',title));
    if(!value){section.append(el('p','Не удалось получить влияние на проверки. Обновите страницу перед решением.'));return section;}
    for(const [key,label] of [['assessments','Проверки понимания'],['practical_tasks','Практические задания']]){
      const inventory=value[key],details=disclosure(label,section);
      details.querySelector('summary').textContent=`${label}: сохраняются ${inventory.unchanged.length}, добавляются ${inventory.added.length}, недоступны ${inventory.removed.length}`;
      for(const [state,name] of [['unchanged','Сохраняются'],['added','Добавляются'],['removed','Станут недоступны для новых попыток']]){
        details.append(el('p',name+': '+inventory[state].length));
        const list=el('ul');for(const id of inventory[state])list.append(el('li',id));details.append(list);
      }
    }
    section.append(el('p','Начатые работы и история сохраняются. Отозванные проверки не возвращаются: '+value.withdrawn_assessments.length+'.'));
    return section;
  }
  async function open(id){const p=await api('graph-proposals/'+encodeURIComponent(id)),history=await api('graph-history');body.replaceChildren();recovery.hidden=true;dirty=false;status.textContent=states[p.state]+(p.state==='draft'&&p.stale?' · основано на прежней версии дерева':'');
    const graph=structuredClone(p.graph),names=new Map(graph.nodes.map(n=>[n.id,n.title]));const title=id=>names.get(id)||id;
    body.append(link('← Все предложения','/admin/tree'),el('h2','Проверка изменений'),el('p',p.note),el('p','История попыток и подтверждений сохраняется. Новые способности начнут без подтверждённого уровня.'));
    if(p.source.proposals){const d=disclosure('Предложения из материала');for(const suggestion of p.source.proposals)d.append(el('p',title(suggestion.objective_id)+' — '+suggestion.explanation));for(const source of p.source.sources||[]){const excerpt=disclosure(source.filename+' · редакция '+source.edition,d);for(const paragraph of source.paragraphs||[])excerpt.append(el('p','Абзац '+paragraph.paragraph+(paragraph.start!==undefined?' · '+paragraph.start+' сек.':'')+' — '+paragraph.text));}d.append(link('Вернуться к материалам','/admin'));}
    const diff=el('section');diff.className='practical-rubric';diff.append(el('h3','До → после'));
    for(const n of p.diff.added_nodes)diff.append(el('p','Новая способность или раздел: '+n.title));
    for(const n of p.diff.changed_nodes)diff.append(el('p',n.before.title+' → '+n.after.title));
    const types={contains:'Раздел',prerequisite:'Подготовка',related:'Связь'};
    for(const [key,label] of [['removed_edges','Убрано'],['added_edges','Добавлено']])for(const e of p.diff[key])diff.append(el('p',label+': '+types[e.type]+' · '+title(e.source)+' → '+title(e.target)));
    if(!p.diff.added_nodes.length&&!p.diff.changed_nodes.length&&!p.diff.added_edges.length&&!p.diff.removed_edges.length)diff.append(el('p','Сохранённых изменений пока нет.'));
    body.append(diff);const impact=disclosure('Затронутые навыки и материалы');for(const id of p.diff.affected_nodes)impact.append(el('p',title(id)));for(const id of p.diff.affected_lessons)impact.append(link('Урок · '+id,'/lessons/'+encodeURIComponent(id)));if(!p.diff.affected_lessons.length)impact.append(el('p','Существующие уроки не затронуты.'));
    body.append(availability(p.diff.availability,'Доступность после утверждения'));
    const note=field(body,'Пояснение редактора',p.note,'textarea');note.maxLength=2000;note.readOnly=p.state!=='draft'&&!(p.state==='active'&&history.active_release===p.id);
    async function save(){await api('graph-proposals/'+p.id,'PUT',{revision:p.revision,graph,note:note.value});dirty=false;await open(p.id);status.textContent='Правки сохранены. Проверьте обновлённое сравнение перед утверждением.';}
    if(p.state==='draft'){
      const add=disclosure('Добавить способность или раздел');
      add.append(el('p','Сначала проверьте существующие названия. Не создавайте новый навык для другой формулировки той же способности.'));
      const name=field(add,'Название новой способности'),kind=select(add,'Тип',[['ability','Проверяемая способность'],['category','Раздел']]);
      if(p.source.proposals?.length){const suggestion=select(add,'Предложение из материала',[['','Выбрать предложение'],...p.source.proposals.map((s,i)=>[String(i),title(s.objective_id)+' — '+s.explanation])]);suggestion.onchange=()=>{if(suggestion.value==='')return;const selected=p.source.proposals[Number(suggestion.value)];if(names.has(selected.objective_id)){status.textContent='Этот навык уже есть на карте. Используйте его при редактировании материала.';return;}name.value=selected.title||selected.explanation;dirty=true;};}
      const parent=select(add,'Родительский раздел',graph.nodes.filter(n=>n.kind!=='ability').map(n=>[n.id,n.title]));
      add.append(action('Добавить и сохранить',async()=>{if(!name.value.trim())throw Error('Введите название.');const id='ability-'+crypto.randomUUID();graph.nodes.push({id,title:name.value.trim(),kind:kind.value,revision:1});graph.edges.push({source:parent.value,target:id,type:'contains',advisory:true});try{await save();}catch(e){graph.nodes.pop();graph.edges.pop();throw e;}}));
      const edit=disclosure('Изменить место или название');const node=select(edit,'Навык или раздел',graph.nodes.filter(n=>n.kind!=='root'&&n.kind!=='branch').map(n=>[n.id,n.title]));const label=field(edit,'Название'),container=select(edit,'Новое место',graph.nodes.filter(n=>n.kind!=='ability').map(n=>[n.id,n.title]));
      function choose(){const n=graph.nodes.find(n=>n.id===node.value);label.value=n.title;label.disabled=n.kind==='ability'&&!p.diff.added_nodes.some(a=>a.id===n.id);container.value=graph.edges.find(e=>e.type==='contains'&&e.target===n.id).source;}node.onchange=choose;choose();
      edit.append(el('p','Смысл уже существующей способности неизменен. Для нового результата создайте новую способность.'),action('Сохранить место и название',async()=>{const n=graph.nodes.find(n=>n.id===node.value),edge=graph.edges.find(e=>e.type==='contains'&&e.target===n.id),oldTitle=n.title,oldParent=edge.source;n.title=label.value;edge.source=container.value;try{await save();}catch(e){n.title=oldTitle;edge.source=oldParent;throw e;}}));
      const connections=disclosure('Связи с другими навыками');const options=graph.nodes.map(n=>[n.id,n.title]);
      const from=select(connections,'От навыка',options),to=select(connections,'К навыку',options),relation=select(connections,'Вид связи',[['prerequisite','Рекомендуемая подготовка'],['related','Связанная тема']]);
      connections.append(el('p','Подготовка помогает выбрать следующий шаг и не закрывает доступ к ветке.'),action('Добавить связь и сохранить',async()=>{graph.edges.push({source:from.value,target:to.value,type:relation.value,advisory:true});try{await save();}catch(e){graph.edges.pop();throw e;}}));
      for(const edge of graph.edges.filter(e=>e.type!=='contains')){const row=el('p',types[edge.type]+' · '+title(edge.source)+' → '+title(edge.target));row.append(action('Убрать связь',async()=>{const index=graph.edges.indexOf(edge);graph.edges.splice(index,1);try{await save();}catch(e){graph.edges.splice(index,0,edge);throw e;}}));connections.append(row);}
      const confirm=field(body,'Я проверил смысл, отсутствие дублей и влияние на обучение');confirm.type='checkbox';
      body.append(action('Сохранить пояснение',save),action('Утвердить дерево',async()=>{if(dirty)throw Error('Сохраните пояснение и правки перед утверждением.');if(!confirm.checked)throw Error('Подтвердите редакторскую проверку.');await decide('activate');}),action('Отклонить предложение',()=>decide('reject')));confirm.oninput=()=>{};
      if(p.stale)body.append(el('p','Это предложение нельзя утвердить: дерево уже изменилось. Сохраните нужное пояснение и создайте предложение от текущего дерева.'));
    }
    async function decide(action){await api('graph-proposals/'+p.id+'/'+action,'POST',{revision:p.revision,note:note.value,confirm_reviewed:action==='activate'});dirty=false;await open(p.id);}
    if(p.state==='active'&&history.active_release===p.id){body.append(availability(p.rollback_availability,'Доступность после возврата'),el('p','Отмена вернёт прежнее дерево. Выполненные работы и подтверждения останутся в истории.'),action('Вернуть прежнее дерево',()=>decide('rollback')));}
    const editions=disclosure('История решений');for(const edition of p.editions)editions.append(el('p','Редакция '+edition.revision+' · '+edition.note));for(const event of history.events.filter(e=>e.proposal_id===p.id))editions.append(el('p',({activate:'Утверждено',reject:'Отклонено',rollback:'Возвращена прежняя версия'})[event.action]+' · '+event.note));
  }
  async function load(){if(params.has('proposal'))return open(params.get('proposal'));const [items,graph]=await Promise.all([api('graph-proposals'),api('graph')]);body.replaceChildren();const note=field(body,'Зачем изменить дерево','','textarea');body.append(action(params.has('job')?'Создать предложение из материала':'Создать предложение',async()=>{const p=await api('graph-proposals','POST',{base_release:graph.release,note:note.value,...(params.has('job')?{job_id:params.get('job'),draft_revision:Number(params.get('revision'))}:{})});dirty=false;location.href='/admin/tree?proposal='+encodeURIComponent(p.id);}));body.append(el('h2','Предложения и решения'));for(const p of items.proposals){const row=el('p');row.append(link(states[p.state]+' · '+p.note,'/admin/tree?proposal='+encodeURIComponent(p.id)));body.append(row);}if(!items.proposals.length)body.append(el('p','Предложений пока нет. Обычная публикация урока не требует изменения дерева.'));status.textContent='Изменения дерева проверяются отдельно от публикации уроков.';}
  recovery.append(el('p','Загрузка сохранённой версии заменит несохранённые поля. До нажатия кнопки их можно скопировать.'),action('Отменить несохранённые правки и загрузить сохранённую версию',async()=>{await open(params.get('proposal'));status.textContent+=' · Загружена сохранённая версия.';status.focus();}));
  window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});load().catch(e=>{status.textContent=e.message;body.append(action('Повторить загрузку',load));});
})();
