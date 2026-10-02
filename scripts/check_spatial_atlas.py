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
    assert app.test_cli_runner().invoke(args=['install-skill-examples']).exit_code==0
    server=make_server('127.0.0.1',0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}'
    evidence={'source':str(Path.cwd()),'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'origin':origin,'widths':[], 'errors':[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:evidence['errors'].append(str(e)))
        page.goto(origin+'/login');page.locator('[name=email]').fill('learner@example.test');page.locator('[name=password]').fill('local-browser-test-only');page.get_by_role('button',name='Войти',exact=True).click()
        for width in [1440,390,360,768]:
            page.set_viewport_size({'width':width,'height':844 if width<801 else 1000});page.goto(origin);page.locator('#skill-map [data-node=coding]').wait_for();page.evaluate('document.fonts.ready')
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
            top=page.locator('.atlas-workspace').bounding_box()['y']
            assert top < (260 if width<801 else 210), (width,top)
            page.screenshot(path=str(out/f'map-{width}.png'),full_page=True)
            page.locator('#skill-map [data-node=coding]').focus();page.keyboard.press('ArrowRight')
            assert page.evaluate('document.activeElement.dataset.node')!='coding'
            page.locator('#skill-map [data-node=coding]').click();page.locator('#node-detail .evidence-label').wait_for()
            assert page.locator('#skill-map .spatial-node').count()==7
            page.screenshot(path=str(out/f'coding-{width}.png'),full_page=True)
            page.locator('#skill-map [data-node="coding.mobile"]').click();page.locator('#node-detail .evidence-label').wait_for()
            node=page.locator('#skill-map [data-node="coding.mobile"]').bounding_box();detail=page.locator('#node-detail').bounding_box()
            assert node['x']+node['width']<=detail['x'] or node['y']+node['height']<=detail['y']
            if width < 801:
                title=page.locator('#detail-title').bounding_box()
                nav=page.locator('.club-header nav').bounding_box()
                assert 0 <= title['y'] < title['y']+title['height'] < nav['y'], (width,title,nav)
                assert page.locator('#node-detail').evaluate('(e)=>e.scrollHeight===e.clientHeight')
            page.screenshot(path=str(out/f'focus-{width}.png'),full_page=True)
            page.screenshot(path=str(out/f'focus-viewport-{width}.png'))
            page.keyboard.press('Escape');assert 'node=' not in page.url;assert page.evaluate('document.activeElement.dataset.node')=='coding.mobile'
            page.locator('#map-reset').click();page.locator('#skill-map [data-node=content]').click();page.locator('#node-detail .evidence-label').wait_for()
            page.reload();page.locator('#node-detail .evidence-label').wait_for()
            me=page.evaluate("fetch('/api/skills/me').then(r=>r.json())")
            assert {'coding.mobile','content'}.issubset({e['node_id'] for e in me['explorations']})
            page.keyboard.press('Escape');page.locator('#list-view').click()
            assert page.locator('#skill-map ul ul').count()>5
            page.locator('#skill-search').fill('несуществующий навык');assert page.locator('#atlas-status').inner_text()=='Найдено навыков: 0'
            evidence['widths'].append({'width':width,'map_top':top,'overflow':False,'selected_node_visible':True})
        for width in [1440,390,360,768]:
            page.set_viewport_size({'width':width,'height':844 if width<801 else 1000})
            page.goto(origin+'/?node=basic-ai.verification')
            page.locator('#node-detail a[href^="/lessons/"]').first.click()
            page.locator('#ability-return:not([hidden])').wait_for()
            assert 'node=basic-ai.verification' in page.url
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
            page.screenshot(path=str(out/f'lesson-{width}.png'),full_page=True)
            page.locator('#ability-return').click()
            page.locator('#detail-title').wait_for()
            assert 'node=basic-ai.verification' in page.url
        evidence['lesson_return']=True
        assert not evidence['errors'],evidence
        browser.close()
    server.shutdown()
    (out/'browser.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    print(json.dumps(evidence,ensure_ascii=False))
