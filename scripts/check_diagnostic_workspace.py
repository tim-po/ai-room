"""Disposable browser evidence; fixture form publication is NOT editorial acceptance."""
import json
import os
import sqlite3
import subprocess
import tempfile
import threading
from pathlib import Path
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
from club import create_app
from club.seed import seed_database
from club.skill_content import CASES, candidate_form, review_examples

out=Path(os.environ.get('DIAGNOSTIC_EVIDENCE','/tmp/diagnostic-evidence'));out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    os.environ['CLUB_SEED_PASSWORD']='local-browser-test-only'
    database=str(Path(tmp)/'test.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text());seed_database(db)
    app=create_app({'DATABASE':database,'SECRET_KEY':'disposable-challenge-check','TESTING':True})
    for command in ['init-skills','install-skill-examples']:
        result=app.test_cli_runner().invoke(args=[command]);assert result.exit_code==0,result.output
    with sqlite3.connect(database) as db:
        review_examples(db,db.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0])
    server=make_server('127.0.0.1',0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}';evidence={'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source':str(Path.cwd()),'origin':origin,'widths':[],'errors':[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:evidence['errors'].append(str(e)))
        def login(p,email='learner@example.test'):
            p.goto(origin+'/login');p.locator('[name=email]').fill(email);p.locator('[name=password]').fill('local-browser-test-only');p.get_by_role('button',name='Войти',exact=True).click()
        login(page)
        page.goto(origin+'/preferences')
        page.get_by_role('link',name='Необязательная проверка знаний →').click()
        page.locator('.diagnostic-interests input').first.wait_for()
        for width in [1440,390,360,768]:
            page.set_viewport_size({'width':width,'height':900})
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
            page.screenshot(path=str(out/f'diagnostic-start-{width}.png'),full_page=True)
        page.locator('input[value="coding"]').check();page.locator('input[value="content"]').check()
        page.get_by_role('button',name='Начать необязательную проверку').focus();page.keyboard.press('Enter')
        page.get_by_role('link',name='Открыть задания →').wait_for()
        saved_url=page.url
        page.get_by_role('link',name='Открыть задания →').click();page.get_by_role('button',name='Начать проверку').click()
        page.locator('.challenge-question').first.wait_for()
        context=browser.new_context();other=context.new_page();login(other)
        other.goto(saved_url);other.get_by_role('link',name='Продолжить задания →').click()
        other.locator('.challenge-question').first.wait_for();context.close()
        page.reload();page.locator('.challenge-question').first.wait_for()
        node=page.evaluate('new URL(location).searchParams.get("node")')
        case=next(c for c in CASES if c['objective']==node)
        for item in candidate_form(case)['items']:
            page.locator(f'input[name="{item["id"]}"][value="{item["answer"]}"]').check()
        page.get_by_role('button',name='Проверить ответы').click()
        page.get_by_role('link',name='Продолжить поиск точки старта →').click()
        page.get_by_text('Подтверждённые знания · 1',exact=True).wait_for()
        page.reload();page.get_by_text('Подтверждённые знания · 1',exact=True).wait_for()
        for width in [1440,390,360,768]:
            page.set_viewport_size({'width':width,'height':900})
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
            page.screenshot(path=str(out/f'diagnostic-result-{width}.png'),full_page=True)
        page.route('**/api/skills/diagnostics/*/advance',lambda route:route.abort())
        page.get_by_role('button',name='Завершить без следующих заданий').click()
        page.get_by_role('status').filter(has_text='Нет связи').wait_for()
        assert page.get_by_text('Подтверждённые знания · 1',exact=True).is_visible()
        page.unroute('**/api/skills/diagnostics/*/advance')
        page.get_by_role('button',name='Завершить без следующих заданий').click()
        page.get_by_role('status').filter(has_text='Проверка остановлена').wait_for()
        page.reload();page.get_by_role('status').filter(has_text='Проверка остановлена').wait_for()
        context=browser.new_context();other=context.new_page();login(other)
        other.goto(saved_url);other.get_by_text('Подтверждённые знания · 1',exact=True).wait_for();context.close()
        context=browser.new_context();other=context.new_page();login(other,'member@example.test')
        other.goto(saved_url);other.get_by_role('button',name='Повторить загрузку').wait_for()
        assert other.get_by_text('Подтверждённые знания · 1',exact=True).count()==0;context.close()
        # A second learner's partial attempt recommends sources without credit.
        context=browser.new_context();other=context.new_page();login(other,'member@example.test')
        other.goto(origin+'/diagnostic');other.locator('.diagnostic-interests input').first.wait_for()
        other.get_by_role('button',name='Начать необязательную проверку').click()
        other.get_by_role('link',name='Открыть задания →').click()
        other.get_by_role('button',name='Начать проверку').click()
        other.locator('.challenge-question').first.wait_for()
        node=other.evaluate('new URL(location).searchParams.get("node")')
        case=next(c for c in CASES if c['objective']==node)
        for item in candidate_form(case)['items']:
            wrong=next(choice['id'] for choice in item['choices'] if choice['id']!=item['answer'])
            other.locator(f'input[name="{item["id"]}"][value="{wrong}"]').check()
        other.get_by_role('button',name='Проверить ответы').click()
        other.get_by_role('link',name='Продолжить поиск точки старта →').click()
        other.get_by_role('heading',name='Что полезно повторить').wait_for()
        assert other.get_by_role('link',name='Материал',exact=False).count()>0
        assert other.get_by_text('Подтверждений пока нет.',exact=False).count()==1
        context.close()
        page.goto(origin+'/profile');page.get_by_role('link',name='Найти точку старта · необязательная проверка →').click()
        page.get_by_text('Предыдущие результаты',exact=True).click()
        page.get_by_role('link',name='Остановленная проверка →').click()
        page.get_by_role('heading',name='Ваша точка старта').wait_for()
        with sqlite3.connect(database) as db:
            assert db.execute('SELECT COUNT(*) FROM skill_evidence').fetchone()[0]==1
            assert db.execute('SELECT COUNT(*) FROM progress').fetchone()[0]==0
        assert not evidence['errors'],evidence
        evidence.update(resume_second_device=True,skip_preserves_evidence=True,other_user_isolated=True,widths=[1440,390,360,768],network_recovery=True)
        browser.close()
    server.shutdown()
    (out/'browser.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2));print(json.dumps(evidence))
