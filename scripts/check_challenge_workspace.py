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

out=Path(os.environ.get('CHALLENGE_EVIDENCE','/tmp/challenge-evidence'));out.mkdir(parents=True,exist_ok=True)
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
        for width,case in zip([1440,390,360,768],CASES[:4]):
            page.set_viewport_size({'width':width,'height':900})
            page.goto(origin+'/?node='+case['objective']);page.get_by_role('link',name='Уже знаю тему',exact=False).click()
            page.get_by_role('button',name='Начать проверку').click();page.locator('.challenge-question').first.wait_for()
            saved_url=page.url;assert 'attempt=' in saved_url
            context=browser.new_context();other=context.new_page();login(other)
            other.goto(origin+'/?node='+case['objective']);other.get_by_role('link',name='Продолжить начатую проверку').click();other.locator('.challenge-question').first.wait_for();context.close()
            page.reload();page.locator('.challenge-question').first.wait_for()
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
            page.screenshot(path=str(out/f'questions-{width}.png'),full_page=True)
            page.locator('input[type=radio]').first.focus();page.keyboard.press('Space');page.keyboard.press('ArrowDown')
            assert page.locator('input:checked').count()==1
            assert page.evaluate('document.activeElement.type')=='radio'
            # Server-only fixture keys are used solely by this local test driver.
            items=candidate_form(case)['items']
            for index,item in enumerate(items):
                answer=item['answer'] if width!=1440 or index!=0 else str((int(item['answer'])+1)%3)
                page.locator(f'input[name="{item["id"]}"][value="{answer}"]').check()
            if width==390:
                page.route('**/api/skills/challenges/*/submit',lambda route:route.abort())
                page.get_by_role('button',name='Проверить ответы').click()
                page.get_by_role('alert').filter(has_text='Нет связи с сервером').wait_for()
                assert page.locator('input:checked').count()==3
                page.unroute('**/api/skills/challenges/*/submit')
            page.get_by_role('button',name='Проверить ответы').focus();page.keyboard.press('Enter');page.get_by_text('Результат сохранён',exact=True).wait_for()
            page.get_by_role('heading',name='Есть темы для повторения' if width==1440 else 'Понимание подтверждено',exact=True).wait_for()
            assert page.locator('.challenge-feedback a').count()==3
            if width==390:
                page.goto(origin+'/profile');page.locator('#character-branches .character-branch').first.wait_for();assert '<' not in page.title();assert page.locator('#character-recent li').count()==1;assert page.locator('#character-recent time').first.is_visible();assert page.locator('#character-recent a[href*=attempt]').first.is_visible();page.screenshot(path=str(out/'character-earned.png'),full_page=True)
                page.goto(origin+'/?node='+case['objective']);page.locator('#skill-map .is-verified').first.wait_for();page.screenshot(path=str(out/'map-earned.png'),full_page=True);page.goto(saved_url)
            page.reload();page.get_by_text('Результат сохранён',exact=True).wait_for()
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
            page.screenshot(path=str(out/f'result-{width}.png'),full_page=True)
            if width==390:
                context=browser.new_context();other=context.new_page();login(other)
                other.goto(origin+'/?node='+case['objective']);other.get_by_role('link',name='Сохранённый разбор →',exact=True).click();other.get_by_role('heading',name='Понимание подтверждено',exact=True).wait_for();context.close()
                context=browser.new_context();other=context.new_page();login(other,'member@example.test')
                other.goto(saved_url);other.get_by_role('button',name='Повторить загрузку').wait_for();assert other.locator('.challenge-feedback').count()==0;context.close()
            # A new attempt is visibly practice-only and cannot award fresh credit.
            page.goto(origin+'/?node='+case['objective']);page.get_by_role('link',name='Тренировка · без нового зачёта',exact=False).click()
            page.get_by_role('link',name='Открыть сохранённый разбор →').wait_for()
            page.get_by_text('Знакомые задания доступны как тренировка.',exact=False).wait_for()
            page.screenshot(path=str(out/f'practice-before-start-{width}.png'),full_page=True)
            page.get_by_role('button',name='Начать тренировку').focus();page.keyboard.press('Enter')
            page.get_by_text('Тренировка · без нового зачёта',exact=True).wait_for()
            for item in items:page.locator(f'input[name="{item["id"]}"][value="{item["answer"]}"]').check()
            page.get_by_role('button',name='Проверить ответы').click();page.get_by_role('heading',name='Проверка пройдена · без нового зачёта',exact=True).wait_for()
            evidence['widths'].append({'width':width,'reload':True,'practice_distinct':True,'overflow':False})
        for width in [1440,390,360,768]:
            page.set_viewport_size({'width':width,'height':1000});page.goto(origin+'/profile')
            page.locator('#character-recent li').first.wait_for()
            assert page.locator('#character-recent li').count()==3
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
            page.screenshot(path=str(out/f'character-earned-{width}.png'),full_page=True)
        page.locator('#character-recent a[href*=attempt]').first.click()
        page.get_by_role('heading',name='Понимание подтверждено',exact=True).wait_for()
        evidence['recent_result_navigation']=True
        with sqlite3.connect(database) as db:
            assert db.execute('SELECT COUNT(*) FROM skill_evidence').fetchone()[0]==3
            assert db.execute('SELECT COUNT(*) FROM progress').fetchone()[0]==0
        assert not evidence['errors'],evidence
        browser.close()
    server.shutdown();evidence['saved_evidence']=3;evidence['lesson_progress_rows']=0
    (out/'browser.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2));print(json.dumps(evidence))
