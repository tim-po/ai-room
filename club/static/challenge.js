(() => {
  const body=document.querySelector('#challenge-body'), status=document.querySelector('#challenge-status');
  const params=new URL(location).searchParams, node=params.get('node'), assessment=params.get('assessment');
  const back=document.querySelector('#challenge-back');
  const diagnostic=params.get('diagnostic');
  if(node)back.href='/?'+new URLSearchParams({node});
  if(diagnostic){back.href='/diagnostic?'+new URLSearchParams({id:diagnostic});back.textContent='← К точке старта';}
  let attempt, detail, requestId=crypto.randomUUID();
  const el=(tag,text,cls)=>{const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e;};
  async function api(url,value){
    const response=await fetch(url,value ? {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name=csrf-token]').content},body:JSON.stringify(value)}:{}).catch(()=>{throw new Error('Нет связи с сервером. Повторите попытку; ваши ответы остаются в форме.');});
    const data=await response.json();
    if(response.status===409 && data.pending_attempt)return api(data.pending_attempt.resume_url);
    if(!response.ok)throw new Error(response.status===401 ? 'Сессия завершена. Войдите снова и откройте эту ссылку.' : response.status===403 ? 'Эта проверка доступна участникам с действующим доступом.' : data.message || 'Не удалось открыть проверку. Вернитесь к навыку и попробуйте ещё раз.');
    return data;
  }
  function focusTitle(){document.querySelector('#challenge-title').focus({preventScroll:true});}
  function showLifecycle(lifecycle){
    if(lifecycle?.status!=='withdrawn')return;
    body.append(el('h2','Проверка отозвана'),el('p',lifecycle.reason),el('p','Ответы и разбор сохраняются. Новая отправка по этой проверке не даёт зачёт навыка; ранее полученный зачёт сохраняется.'));
    if(!lifecycle.replacement_id||!node)return;
    const recovery=el('p');body.append(recovery);
    async function currentReplacement(){const current=await api('/api/skills/nodes/'+encodeURIComponent(node));return current.assessments.find(a=>a.id===lifecycle.replacement_id);}
    currentReplacement().then(replacement=>{
      if(!recovery.isConnected||!replacement)return;
      if(!attempt.result && replacement.pending_attempt?.id===attempt.id){
        recovery.textContent='Сначала завершите начатую проверку ниже для обратной связи. Затем можно открыть замену; знакомые задания не дают нового зачёта.';
        const finish=el('button','Перейти к ответам');finish.type='button';finish.onclick=()=>body.querySelector('input')?.focus();const actions=el('div',null,'development-actions');actions.append(finish);recovery.append(actions);return;
      }
      const a=el('a','Открыть актуальную проверку →');a.href='/challenges?'+new URLSearchParams({node,assessment:replacement.id});
      a.onclick=async event=>{event.preventDefault();try{if(await currentReplacement())location.assign(a.href);else recovery.textContent='Замена больше недоступна. Вернитесь к навыку, чтобы выбрать следующий шаг.';}catch(e){recovery.textContent=e.message;}};
      recovery.append(a);
    }).catch(()=>{if(recovery.isConnected)recovery.textContent='Не удалось проверить доступность замены. Обновите страницу, чтобы повторить.';});
  }
  function showResult(result){
    attempt.result=result;
    body.replaceChildren();status.textContent='Результат сохранён';showLifecycle(result.lifecycle||attempt.lifecycle);
    body.append(el('h2',result.credited ? 'Понимание подтверждено' : result.passed ? 'Проверка пройдена · без нового зачёта' : 'Есть темы для повторения'));
    body.append(el('p',`${result.points} из ${attempt.items.length} верных ответов.`));
    body.append(el('p',result.credited ? 'Знание зачтено в вашем профиле. Просмотр урока и практическое выполнение отмечаются отдельно.' : result.mode==='practice' ? 'Знакомые вопросы помогают потренироваться. Эта попытка не добавляет подтверждённых навыков.' : 'Эта попытка не подтверждает навык целиком. Разберите ответы и связанные материалы.'));
    for(const feedback of result.feedback){
      const item=attempt.items.find(i=>i.id===feedback.item_id), section=el('section',null,'challenge-feedback');
      section.append(el('h3',(feedback.correct?'✓ ':'↗ ')+(item?.prompt || 'Разбор ответа')),el('p',feedback.rationale));
      const source=feedback.source;
      if(source?.lesson_id){const a=el('a',`Открыть источник${source.paragraph?' · абзац '+source.paragraph:''}${source.edition?' · редакция '+source.edition:''}`);a.href='/lessons/'+encodeURIComponent(source.lesson_id);section.append(a);}
      body.append(section);
    }
    const actions=el('div',null,'development-actions'), profile=el('a','Моё развитие →');profile.href='/profile';actions.append(profile);if(diagnostic){const next=el('a','Продолжить поиск точки старта →');next.href='/diagnostic?'+new URLSearchParams({id:diagnostic,attempt:attempt.id});actions.prepend(next);}body.append(actions);focusTitle();
  }
  function showAttempt(data){
    attempt=data;
    if(data.result){showResult(data.result);return;}
    status.textContent=data.lifecycle?.status==='withdrawn'?'Обратная связь · без нового зачёта':data.mode==='practice'?'Тренировка · без нового зачёта':'Проверка понимания · практическое выполнение оценивается отдельно';
    body.replaceChildren();showLifecycle(data.lifecycle);
    body.append(el('p',data.mode==='practice'||data.lifecycle?.status==='withdrawn' ? 'Ответьте на задания для обратной связи. Эта попытка не даёт нового зачёта. Ответы отправятся только после нажатия «Проверить ответы».' : `Для зачёта: минимум ${data.thresholds.overall} из ${data.items.length}, порог по каждой теме и все обязательные вопросы. Ответы отправятся только после нажатия «Проверить ответы».`));
    if(detail?.content.length){const sources=el('details');sources.append(el('summary','Учебный случай · открыть материалы'));for(const lesson of detail.content){const a=el('a',lesson.title+' ↗ (новая вкладка)');a.href='/lessons/'+encodeURIComponent(lesson.id);a.target='_blank';a.rel='noopener';sources.append(a);}body.append(sources);}
    const form=el('form');
    data.items.forEach((item,index)=>{
      const fieldset=el('fieldset',null,'challenge-question');fieldset.append(el('legend',`${index+1}. ${item.prompt}${data.thresholds.critical_required.includes(item.id)?' · Обязательный вопрос':''}`));
      for(const choice of item.choices){const label=el('label',null,'challenge-choice'),input=el('input');input.type='radio';input.name=item.id;input.value=choice.id;input.required=true;label.append(input,el('span',choice.text));fieldset.append(label);}
      form.append(fieldset);
    });
    const submit=el('button','Проверить ответы');submit.type='submit';const error=el('p');error.setAttribute('role','alert');form.append(error,submit);
    form.onsubmit=async event=>{event.preventDefault();submit.disabled=true;error.textContent='';status.textContent='Сохраняем ответы…';
      try{showResult(await api('/api/skills/challenges/'+encodeURIComponent(data.id)+'/submit',{answers:Object.fromEntries(new FormData(form))}));}
      catch(e){error.textContent=e.message;status.textContent='Не удалось подтвердить сохранение. Повторите отправку; выбранные варианты остаются на странице.';submit.disabled=false;}
    };
    body.append(form);focusTitle();
  }
  async function start(button){
    button.disabled=true;status.textContent='Открываем задания…';
    try{
      const data=await api('/api/skills/challenges',{assessment_id:assessment,request_id:requestId});
      const url=new URL(location);url.searchParams.set('attempt',data.id);history.replaceState({},'',url);
      showAttempt(data);
    }catch(e){status.textContent=e.message;button.disabled=false;}
  }
  async function load(){
    try{
      if(node){try{detail=await api('/api/skills/nodes/'+encodeURIComponent(node));document.querySelector('#challenge-title').textContent=detail.node.title;}catch(e){if(!params.get('attempt'))throw e;}}
      if(params.get('attempt')){showAttempt(await api('/api/skills/challenges/'+encodeURIComponent(params.get('attempt'))));return;}
      if(!node||!assessment)throw new Error('Выберите проверку на карте навыков.');
      if(!detail)throw new Error('Не удалось загрузить навык.');
      const form=detail.assessments.find(a=>a.id===assessment);if(!form)throw new Error('Проверка обновилась. Вернитесь к навыку и откройте актуальную версию.');
      if(form.pending_attempt){showAttempt(await api(form.pending_attempt.resume_url));return;}
      document.querySelector('#challenge-title').textContent=detail.node.title;
      status.textContent=`${form.item_count} задания · ${form.access==='free'?'Бесплатно':'Для участников'}`;
      body.replaceChildren(el('p','Можно подтвердить понимание темы, не отмечая урок просмотренным. После отправки вы увидите разбор и ссылки на источники. Повтор знакомых заданий доступен как тренировка.'));
      if(detail.content.length){body.append(el('p','Задания ссылаются на учебный случай. Его можно открыть перед проверкой:'));for(const lesson of detail.content){const link=el('a',lesson.title);link.href='/lessons/'+encodeURIComponent(lesson.id);link.target='_blank';link.rel='noopener';link.append(el('span',' ↗ (новая вкладка)'));body.append(link);}}
      const button=el('button','Начать проверку');button.onclick=()=>start(button);body.append(button);
    }catch(e){status.textContent=e.message;body.replaceChildren();const retry=el('button','Повторить загрузку');retry.onclick=load;body.append(retry);}
  }
  load();
})();
