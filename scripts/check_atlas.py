"""Disposable local browser check. No staging or shared learner data."""
import json
import os
import sqlite3
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
    evidence={'widths':[], 'errors':[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:evidence['errors'].append(str(e)))
        page.goto(origin+'/login');page.locator('[name=email]').fill('learner@example.test');page.locator('[name=password]').fill('local-browser-test-only');page.get_by_role('button',name='Войти',exact=True).click()
        page.locator('[data-node=coding]').wait_for()
        for width in [1440,390,360,768]:
            page.set_viewport_size({'width':width,'height':1000});page.goto(origin);page.locator('[data-node=coding]').wait_for();page.evaluate('document.fonts.ready')
            overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth');assert not overflow,width
            page.screenshot(path=str(out/f'map-{width}.png'),full_page=True)
            evidence['widths'].append({'width':width,'overflow':overflow})
        page.set_viewport_size({'width':1440,'height':1000})
        for node in ['coding','coding.mobile','coding.review','content']:
            page.locator('#skill-map [data-node="'+node+'"]').first.click()
            page.locator('#node-detail .evidence-label').wait_for()
            page.keyboard.press('Escape')
            assert page.evaluate('document.activeElement.dataset.node')==node
        page.reload();page.locator('#node-detail .evidence-label').wait_for()
        me=page.evaluate("fetch('/api/skills/me').then(r=>r.json())")
        assert {'coding.mobile','coding.review','content'}.issubset({e['node_id'] for e in me['explorations']})
        page.keyboard.press('Escape');page.locator('#list-view').click();assert page.locator('#skill-map [data-node="coding.mobile.demonstrate"]').count()==1
        page.locator('#skill-search').fill('несуществующий навык');assert page.locator('#atlas-status').inner_text()=='Найдено навыков: 0'
        page.locator('#map-reset').click();page.locator('#map-view').click();page.locator('[data-node=coding]').click();page.locator('#node-detail .evidence-label').wait_for()
        page.screenshot(path=str(out/'detail-1440.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'detail-390.png'),full_page=True)
        page.go_back();page.go_back();page.wait_for_function("document.querySelector('#detail-title')?.textContent==='Создание контента'")
        page.route('**/api/skills/graph',lambda route:route.fulfill(status=503,body='{}'))
        page.goto(origin);page.get_by_role('button',name='Повторить загрузку').wait_for();page.unroute('**/api/skills/graph');page.get_by_role('button',name='Повторить загрузку').click();page.locator('#skill-map [data-node=coding]').wait_for()
        evidence['back_navigation']=True;evidence['error_recovery']=True
        evidence['explorations']=me['explorations'];evidence['fonts']=page.evaluate('[...document.fonts].map(f=>({family:f.family,status:f.status}))')
        assert not evidence['errors'],evidence
        browser.close()
    server.shutdown()
    (out/'browser.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    print(json.dumps(evidence,ensure_ascii=False))
