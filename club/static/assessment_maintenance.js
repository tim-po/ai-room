(() => {
  const body=document.querySelector('#forms-body'), status=document.querySelector('#forms-status');
  const el=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
  let forms=[],dirty=false;
  async function api(path,method='GET',value){
    let response;try{response=await fetch('/api/skills/forms'+path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name=csrf-token]').content},...(value?{body:JSON.stringify(value)}:{})});}catch{throw Error('Нет связи. Причина и выбранная замена остаются на странице. Повторите действие.');}
    if(!response.ok)throw Error(response.status===409?'Состояние проверки или замены изменилось. Обновите список перед новым решением.':response.status===400?'Укажите причину от 10 до 2000 символов и подтвердите последствия.':'Не удалось выполнить действие. Проверьте доступ и повторите попытку.');
    return response.json();
  }
  function button(text,fn){const b=el('button',text);b.type='button';b.onclick=async()=>{b.disabled=true;try{await fn();}catch(e){status.textContent=e.message;status.focus();}finally{b.disabled=false;}};return b;}
  const label=f=>`${f.title} · ${f.item_count} задания · ${f.id}`;
  function open(f){
    body.replaceChildren();dirty=false;status.textContent='Проверьте последствия перед решением.';const heading=el('h2',f.title);heading.tabIndex=-1;
    body.append(button('← К списку проверок',load),heading,el('p',`${f.id} · ${f.access==='free'?'Бесплатно':'По подписке'}`));
    if(f.lifecycle.status==='withdrawn'){
      body.append(el('p','Отозвана · '+f.lifecycle.created_at),el('p',f.lifecycle.reason));
      const replacement=forms.find(r=>r.id===f.lifecycle.replacement_id);
      if(replacement)body.append(el('p','Замена: '+label(replacement)+(replacement.lifecycle.status==='withdrawn'?' · тоже отозвана':'')));
      heading.focus();return;
    }
    body.append(el('h3','Что изменится'),el('p','Новые попытки и связанные практические задания станут недоступны. Начатые работы можно завершить для обратной связи, без нового зачёта. Ответы, результаты и ранее полученный зачёт сохранятся.'),el('p','Отзыв необратим. Замена не переносит ответы и не начисляет зачёт автоматически. Уже знакомые вопросы останутся тренировкой.'));
    const form=el('form'),reasonLabel=el('label','Причина для учеников'),reason=el('textarea');
    reason.required=true;reason.minLength=10;reason.maxLength=2000;reasonLabel.append(reason);
    const replacementLabel=el('label','Проверенная замена'),replacement=el('select'),none=el('option','Без замены');none.value='';replacement.append(none);
    for(const id of f.eligible_replacements){const target=forms.find(r=>r.id===id),o=el('option',label(target));o.value=id;replacement.append(o);}
    replacementLabel.append(replacement);
    const confirmLabel=el('label','Я проверил причину, замену и последствия отзыва'),confirm=el('input');confirm.type='checkbox';confirm.required=true;confirmLabel.prepend(confirm);
    form.append(reasonLabel,el('p','Не указывайте ответы на задания или личные данные. Причину увидят ученики.'),replacementLabel);
    if(!f.eligible_replacements.length)form.append(el('p','Совместимых опубликованных замен пока нет. Проверку можно отозвать без замены.'));
    const submit=el('button','Отозвать проверку');submit.type='submit';form.append(confirmLabel,submit);
    form.oninput=()=>dirty=true;
    form.onsubmit=async e=>{e.preventDefault();if(!form.reportValidity())return;submit.disabled=true;try{const result=await api('/'+encodeURIComponent(f.id)+'/withdraw','POST',{reason:reason.value.trim(),replacement_id:replacement.value||null,confirm_reviewed:confirm.checked});f.lifecycle=result;dirty=false;open(f);status.textContent='Проверка отозвана. История и ранее полученный зачёт сохранены.';status.focus();}catch(e){status.textContent=e.message;status.focus();}finally{submit.disabled=false;}};
    body.append(form);heading.focus();
  }
  async function load(){
    if(dirty&&!window.confirm('Вернуться к списку без сохранения причины отзыва?'))return;
    const data=await api('');forms=data.forms;dirty=false;body.replaceChildren();
    const active=el('section'),history=el('details');active.append(el('h2','Доступны ученикам'));history.append(el('summary','Отозванные и прежние редакции'));
    for(const f of forms){const row=el('p');row.append(button(label(f)+(f.lifecycle.status==='withdrawn'?' · отозвана':''),()=>open(f)));(f.available&&f.lifecycle.status==='active'?active:history).append(row);}
    if(!active.querySelector('button'))active.append(el('p','Доступных проверок пока нет.'));
    body.append(active,history);status.textContent='Выберите проверку, чтобы увидеть последствия отзыва.';
  }
  window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
  body.append(button('Обновить список',load));load().catch(e=>status.textContent=e.message);
})();
