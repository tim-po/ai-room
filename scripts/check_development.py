"""Disposable local browser check. No staging or shared learner data."""
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

out=Path(os.environ.get('ATLAS_EVIDENCE','/tmp/atlas-evidence'));out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    os.environ['CLUB_SEED_PASSWORD']='local-browser-test-only'
    database=str(Path(tmp)/'test.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text());seed_database(db)
    app=create_app({'DATABASE':database,'SECRET_KEY':'disposable-browser-check','TESTING':True})
    assert app.test_cli_runner().invoke(args=['init-skills']).exit_code==0
    server=make_server('127.0.0.1',0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}'
    evidence={'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source':str(Path.cwd()),'origin':origin,'widths':[], 'errors':[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:evidence['errors'].append(str(e)))
        page.goto(origin+'/login');page.locator('[name=email]').fill('learner@example.test');page.locator('[name=password]').fill('local-browser-test-only');page.get_by_role('button',name='Войти',exact=True).click()
        page.goto(origin+'/preferences');page.locator('[name=interest]').first.wait_for()
        page.locator('[name=interest][value=coding]').check();page.locator('[name=interest][value=content]').check()
        for width in [1440,390,360,768]:
            page.set_viewport_size({'width':width,'height':844 if width<801 else 1000});page.evaluate('document.fonts.ready')
            for option in page.locator('[name=interest]').all():
                previous=option.is_checked()
                option.click()
                assert option.is_checked()!=previous
                option.click()
            last=page.locator('.interest-option').last.bounding_box()
            next_button=page.locator('#interest-next').bounding_box()
            assert next_button['y'] >= last['y']+last['height']
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
            page.screenshot(path=str(out/f'interests-{width}.png'),full_page=True)
        page.locator('#interest-next').focus();page.keyboard.press('Enter')
        assert page.evaluate("document.activeElement.tagName")=='LEGEND'
        page.route('**/api/skills/interests',lambda route:route.fulfill(status=503,body='{}'))
        page.locator('#interest-save').click();page.get_by_text('Не удалось сохранить или загрузить данные. Повторите попытку.',exact=True).wait_for()
        assert page.locator('#interest-save').is_enabled()
        page.unroute('**/api/skills/interests');page.locator('#interest-save').click();page.wait_for_url(origin+'/')
        me=page.evaluate("fetch('/api/skills/me').then(r=>r.json())");assert me['interests']==['coding','content']
        page.goto(origin+'/preferences');page.locator('[name=interest][value=coding]:checked').wait_for();assert page.locator('[name=interest][value=content]').is_checked()
        page.get_by_role('button',name='Пропустить и исследовать карту →').click();page.wait_for_url(origin+'/')
        assert page.evaluate("fetch('/api/skills/me').then(r=>r.json()).then(d=>d.interests)")==['coding','content']
        for width in [1440,390,360,768]:
            page.set_viewport_size({'width':width,'height':1000});page.goto(origin+'/profile');page.locator('.character-branch').first.wait_for();page.evaluate('document.fonts.ready')
            assert page.locator('.character-branch').count()==6
            assert page.locator('#character-recent').is_hidden()
            assert page.locator('.profile-collection[open]').count()==0
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
            page.screenshot(path=str(out/f'character-{width}.png'),full_page=True)
            evidence['widths'].append({'width':width,'overflow':False})
        page.locator('.character-branch summary').first.focus();page.keyboard.press('Enter')
        page.get_by_role('link',name='Мобильные приложения',exact=True).wait_for()
        page.get_by_role('link',name='Мобильные приложения',exact=True).click();page.locator('#node-detail .evidence-label').wait_for()
        assert 'coding.mobile' in page.url
        evidence['saved_interests']=me['interests'];evidence['save_failure_recovery']=True;evidence['keyboard_details']=True;evidence['skip_preserves_interests']=True
        assert not evidence['errors'],evidence
        browser.close()
    server.shutdown()
    (out/'browser.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    print(json.dumps(evidence,ensure_ascii=False))
