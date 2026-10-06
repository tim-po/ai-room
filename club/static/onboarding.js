(() => {
  let state = JSON.parse(document.querySelector('#onboarding-state').textContent), busy = false, pending = null;
  const body = document.querySelector('#onboarding-body'), actions = document.querySelector('#onboarding-actions'), status = document.querySelector('#onboarding-status'), title = document.querySelector('#onboarding-title');
  const steps = ['welcome','interests','pace','start'];
  function recommendationReason(r) {
    const parts=[];const reasons=r.reasons||[];
    const branch=(branches.find(([id])=>id===r.branch)||[])[1];
    if(reasons.includes('interest') && branch) parts.push(`Под ваш интерес «${branch}»`);
    else if(reasons.includes('foundation')) parts.push('Общая основа для любого направления');
    if(reasons.includes('level')) parts.push('для начинающих');
    if(r.minutes) parts.push(`${r.minutes} минут`+(reasons.includes('time')?' — укладывается в ваше время':''));
    return parts.join(' · ');
  }
  const branches = [['basic-ai','Основы: Claude и ChatGPT'],['coding','Код: сайты и инструменты'],['content','Контент: картинки и видео'],['agents','ИИ-агенты']];
  const el = (tag,text) => {const e=document.createElement(tag);if(text)e.textContent=text;return e;};
  const link = (text,url) => {const a=el('a',text);a.href=url;return a;};
  // style: false = primary, true = secondary, 'quiet' = text-style action (Назад, Пропустить).
  function button(text,fn,secondary=false) {const b=el('button',text);b.type='button';b.className=secondary==='quiet'?'link-button':secondary?'button secondary':'button';b.onclick=fn;return b;}
  function progressBar(index) {
    let bar=document.querySelector('.onb-steps');
    if(!bar){bar=el('div');bar.className='onb-steps';bar.setAttribute('aria-hidden','true');for(let i=0;i<steps.length;i++)bar.append(el('span'));document.querySelector('#onboarding-progress').after(bar);}
    [...bar.children].forEach((segment,i)=>segment.classList.toggle('is-done',i<=index));bar.hidden=index<0;
    document.querySelector('.onboarding').dataset.step=index<0?'done':steps[index];
  }
  function draft() {
    if(state.step==='interests') {
      const other=state.draft.interests.filter(id=>!branches.some(([branch])=>branch===id));
      return {interests:[...other,...[...body.querySelectorAll('input:checked')].map(i=>i.value)]};
    }
    if(state.step==='pace')return {experience:body.querySelector('[name=experience]:checked')?.value || null,available_minutes:Number(body.querySelector('[name=minutes]:checked')?.value)||null};
    return {};
  }
  async function send(action, extra={}, destination=null, recordHistory=true) {
    if(busy)return;busy=true;let conflicted=false, sessionExpired=false;
    const payload={action,expected_revision:state.revision,draft:['edit','cancel','skip'].includes(action)?{}:{...draft(),...extra}};
    const signature=JSON.stringify(payload);
    if(!pending || pending.signature!==signature)pending={signature,payload:{...payload,idempotency_key:crypto.randomUUID()}};
    document.querySelectorAll('.onboarding button,.onboarding input').forEach(e=>e.disabled=true);status.textContent='Сохраняем…';
    const controller=new AbortController(), timeout=setTimeout(()=>controller.abort(),15000);
    try {
      const response=await fetch('/api/onboarding',{method:'PUT',signal:controller.signal,headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:JSON.stringify(pending.payload)});
      sessionExpired=response.status===401;
      if(sessionExpired)throw new Error('Сессия завершена. Войдите снова: сохранённые шаги останутся в аккаунте.');
      let data;
      try {data=await response.json();} catch(error) {if(error.name==='AbortError')throw error;throw new Error('Сервер не подтвердил сохранение. Ваш выбор остаётся на экране. Повторите действие.');}
      if(response.status===409){conflicted=true;pending=null;status.replaceChildren(el('span','Настройки изменились в другой вкладке. Загрузите сохранённую версию перед продолжением. '),button('Загрузить сохранённую версию',()=>location.reload()));status.focus();return;}
      if(!response.ok)throw new Error(response.status===401?'Сессия завершена. Войдите снова: сохранённые шаги останутся в аккаунте.':'Не удалось сохранить. Ваш выбор остаётся на экране. Повторите действие.');
      state=data;pending=null;
      if(['complete','skip','cancel'].includes(action)){location.assign(destination || state.next_url || '/');return;}
      render();if(recordHistory)history.pushState({onboarding:true,step:state.step},'',location.pathname);title.focus();return true;
    } catch(e) {status.textContent=e.name==='AbortError'?'Сервер пока не подтвердил сохранение. Ваш выбор остаётся на экране. Повторите действие.':e instanceof TypeError?'Нет связи с сервером. Ваш выбор остаётся на экране. Повторите действие.':e.message;if(sessionExpired)status.append(' ',link('Войти снова','/login'));status.focus();}
    finally {clearTimeout(timeout);busy=false;document.querySelectorAll('.onboarding button,.onboarding input').forEach(e=>e.disabled=conflicted&&!status.contains(e));}
  }
  const footer=document.querySelector('.onboarding-footer');
  new ResizeObserver(()=>{document.documentElement.style.scrollPaddingBottom=`${footer.offsetHeight+24}px`;}).observe(footer);
  body.addEventListener('change',()=>{status.textContent='Есть несохранённые изменения. Сохраните выбор, чтобы продолжить.';});
  function choices(legend,name,options,selected) {
    const field=el('fieldset');field.append(el('legend',legend));
    for(const [value,label] of options){const l=el('label');l.className='onboarding-choice';const input=el('input');input.type=name==='interests'?'checkbox':'radio';input.name=name;input.value=value;input.checked=Array.isArray(selected)?selected.includes(value):String(selected??'')===value;l.append(input,el('span',label));field.append(l);}
    body.append(field);
  }
  function render() {
    body.replaceChildren();actions.replaceChildren();status.textContent='';
    if(['completed','skipped'].includes(state.status)&&!state.editing){
      title.textContent='Ваше начало — в вашем темпе';document.querySelector('#onboarding-progress').textContent='Настройки обучения';progressBar(-1);
      body.append(el('p','Можно изменить интересы и время. Уроки, работы и результаты сохранятся.'));
      actions.append(button('Изменить интересы и темп',()=>send('edit')),link('Вернуться к обучению',state.return_to || '/'),link('Недельная цель и аккаунт','/preferences'));return;
    }
    document.querySelector('#onboarding-progress').textContent=`${state.editing?'Настройки · ':''}Шаг ${steps.indexOf(state.step)+1} из 4`;progressBar(steps.indexOf(state.step));
    if(state.step==='welcome') {title.textContent='Небольшой шаг. Полезный результат.';body.append(el('p','Разберите одну идею, попробуйте её на своей задаче и сохраните работу. Здесь можно учиться сразу в нескольких направлениях.'),el('p','Пара необязательных вопросов поможет сохранить ваши пожелания. Их можно изменить позже.'));}
    if(state.step==='interests') {title.textContent='Что хочется попробовать?';body.append(el('p','Выберите несколько направлений или ни одного. Вся карта останется открытой.'));choices('Ваши интересы','interests',branches,state.draft.interests);}
    if(state.step==='pace') {title.textContent='Сколько места для нового?';choices('Опыт работы с ИИ','experience',[['','Пока не хочу выбирать'],['beginner','Начинаю разбираться'],['experienced','Уже использую в работе']],state.draft.experience);choices('Время на один подход','minutes',[['','Без плана'],['5','5 минут'],['10','10 минут'],['20','20 минут']],state.draft.available_minutes);body.append(el('p','Это пожелание, а не обязательство. Пропуски не обнуляют обучение.'));}
    if(state.step==='start') {
      title.textContent='Начните с одной идеи';body.append(el('p','Этот доступный урок — отправная точка. Это не оценка ваших знаний и не ограничение выбранными интересами.'));
      if(state.recommendation){const returning=state.return_to && state.return_to!=='/';const pick=el('div');pick.className='onb-pick';pick.append(el('span',returning?'Продолжим':'Ваш первый урок'),el('strong',returning?'Продолжим с того, что вы открывали':state.recommendation.title));if(!returning)pick.append(el('p',recommendationReason(state.recommendation)));body.append(pick);actions.append(button(state.editing?'Сохранить настройки':returning?'Сохранить и продолжить →':'Открыть первый урок →',()=>send('complete',{diagnostic_choice:'skip'},state.editing?null:returning?state.return_to:state.recommendation.url)));}
      else {body.append(el('p','Сейчас нет доступного стартового урока. Можно исследовать карту и вернуться позже.'));actions.append(button('Сохранить и открыть карту',()=>send('complete',{},'/')));}
      if(state.diagnostic.available){body.append(el('p','Уже знакомы с темой? Можно начать с необязательной проверки знаний.'));actions.append(button('Сначала проверить знания',()=>send('complete',{diagnostic_choice:'start'},'/diagnostic'),true));}
    } else actions.append(button(state.step==='welcome'?'Найти своё начало →':'Сохранить и дальше →',()=>send('next')));
    if(state.step!=='welcome')actions.append(button('← Назад',()=>send('back'),'quiet'));
    actions.append(button(state.editing?'Отменить изменения':'Пропустить настройку',()=>send(state.editing?'cancel':'skip'),'quiet'));
  }
  // Store orientation only. Historical entries never contain old revisions or request bodies.
  history.replaceState({onboarding:true,step:state.step},'',location.pathname);
  addEventListener('popstate',async event=>{
    if(!event.state?.onboarding)return;
    const target=event.state.step;
    if(busy || pending || !steps.includes(target)) {
      history.pushState({onboarding:true,step:state.step},'',location.pathname);
      if(!busy)status.textContent='Сначала повторите сохранение текущего шага: сервер ещё не подтвердил его.';
      return;
    }
    // Each transition is a new navigation intent, with current choices and revision.
    while(state.step!==target) {
      const action=steps.indexOf(target)<steps.indexOf(state.step)?'back':'next';
      if(!await send(action,{},null,false)) {
        history.replaceState({onboarding:true,step:state.step},'',location.pathname);
        break;
      }
    }
  });
  render();
})();
