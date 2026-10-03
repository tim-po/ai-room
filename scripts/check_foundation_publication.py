"""Exercise explicitly published foundation checks using synthetic staging users.

Reads private answer keys only to drive controlled verification; never exports them.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import threading
import uuid
from playwright.sync_api import sync_playwright

p=argparse.ArgumentParser(description=__doc__)
for name in ('source-root','database','credentials','output'): p.add_argument('--'+name,required=True)
p.add_argument('--url')
p.add_argument('--expected-build',default='dae021716ac92abe5fdf1253093f82ac8f3f3286')
a=p.parse_args();sys.path.insert(0,a.source_root)
out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
password=Path(a.credentials).read_text().split('Password: ',1)[1].splitlines()[0]
server=None
if not a.url:
    from club import create_app
    from werkzeug.serving import make_server
    app=create_app({'DATABASE':a.database,'SECRET_KEY':'private-copy-rehearsal','TESTING':True})
    server=make_server('127.0.0.1',0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
    a.url='http://127.0.0.1:'+str(server.server_port)

def snapshot():
    with sqlite3.connect(Path(a.database).resolve().as_uri()+'?mode=ro',uri=True) as db:
        return {t:db.execute('SELECT * FROM '+t+' ORDER BY rowid').fetchall() for t in ('progress','skill_evidence','skill_application_evidence')}
before=snapshot();result=dict(url=a.url,checks=[],self_verification=True)
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    context=browser.new_context(viewport={'width':390,'height':900})
    page=context.new_page()
    def login(page,email):
        page.goto(a.url+'/login');page.get_by_label('Почта',exact=True).fill(email);page.get_by_label('Пароль',exact=True).fill(password)
        page.get_by_role('button',name='Войти',exact=True).click();page.wait_for_url(a.url+'/')
    if not server:
        result['health']=context.request.get(a.url+'/health').json()
        assert a.expected_build in result['health'].values()
    login(page,'learner@example.test')
    def post(path,data):
        response=context.request.post(a.url+path,data=data,headers={'X-CSRF-Token':page.locator('meta[name=csrf-token]').get_attribute('content')})
        assert response.ok,(path,response.status)
        return response.json()
    diagnostic=post('/api/skills/diagnostics',dict(request_id=str(uuid.uuid4()),interests=['coding','content']))
    count=0
    while diagnostic['next']:
        node=diagnostic['next']['node_id'];form_id=diagnostic['next']['assessment_id']
        assert form_id.endswith('-a-v1')
        page.goto(a.url+'/challenges?node='+node+'&assessment='+form_id+'&diagnostic='+diagnostic['id'])
        page.get_by_role('button',name='Начать проверку',exact=True).click()
        page.locator('.challenge-question').first.wait_for()
        attempt=page.evaluate('new URL(location).searchParams.get("attempt")')
        with sqlite3.connect(Path(a.database).resolve().as_uri()+'?mode=ro',uri=True) as db:
            form=json.loads(db.execute('SELECT body FROM skill_forms WHERE id=?',(form_id,)).fetchone()[0])
        dto=context.request.get(a.url+'/api/skills/challenges/'+attempt).json()
        assert all('answer' not in item and 'rationale' not in item for item in dto['items'])
        for item in form['items']: page.locator(f'input[name="{item["id"]}"][value="{item["answer"]}"]').check()
        page.get_by_role('button',name='Проверить ответы',exact=True).click()
        page.get_by_role('link',name='Продолжить поиск точки старта →').wait_for()
        saved=context.request.get(a.url+'/api/skills/challenges/'+attempt).json()['result']
        assert saved['credited'] and saved['mode']=='certification'
        for feedback in saved['feedback']:
            assert context.request.get(a.url+'/lessons/'+feedback['source']['lesson_id']).status==200
        diagnostic=post('/api/skills/diagnostics/'+diagnostic['id']+'/advance',dict(attempt_id=attempt,revision=diagnostic['revision']))
        repeat=post('/api/skills/challenges',dict(assessment_id=form_id,request_id=str(uuid.uuid4())))
        assert repeat['mode']=='practice'
        repeated=post('/api/skills/challenges/'+repeat['id']+'/submit',dict(answers={i['id']:i['answer'] for i in form['items']}))
        assert not repeated['credited']
        result['checks'].append(dict(node=node,credited=True,repeat_credit=False,feedback_access=True,attempt=attempt))
        count+=1
    assert count==3
    other=browser.new_context();otherpage=other.new_page();login(otherpage,'member@example.test')
    for row in result['checks']: assert other.request.get(a.url+'/api/skills/challenges/'+row['attempt']).status==404
    assert other.request.get(a.url+'/api/skills/diagnostics/'+diagnostic['id']).status==404
    other.close()
    page.goto(a.url+'/profile');page.locator('#character-branches > *').first.wait_for();page.screenshot(path=str(out/'profile-390.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1000});page.screenshot(path=str(out/'profile-1440.png'),full_page=True)
    browser.close()
after=snapshot()
assert before['progress']==after['progress']
assert before['skill_application_evidence']==after['skill_application_evidence']
assert len(after['skill_evidence'])-len(before['skill_evidence'])==3
result.update(understanding_added=3,completion_unchanged=True,application_unchanged=True,isolation=True)
(out/'flow.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
if server: server.shutdown()
print(json.dumps(dict(checks=count,understanding_added=3,completion_unchanged=True,application_unchanged=True)))
