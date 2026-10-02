"""Profile and weekly goal checks against an isolated real HTTP application."""
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys
import tempfile
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from club import create_app
from club.seed import seed_database
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

out = Path(os.environ.get('CLUB_EVIDENCE_DIR', 'instance/editor-layout-evidence'))
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='club-editor-') as folder:
    password = secrets.token_urlsafe(24)
    os.environ['CLUB_SEED_PASSWORD'] = password
    database = str(Path(folder) / 'test.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text())
        seed_database(db)
    app = create_app({'DATABASE': database, 'SECRET_KEY': secrets.token_hex(32)})
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    results = {'layouts': [], 'errors': []}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
            page = browser.new_page(reduced_motion='reduce')
            page.on('pageerror', lambda err: results['errors'].append(str(err)))
            for role in ['learner', 'editor', 'admin']:
                for width, height in [(1280,720),(1280,600),(390,844)]:
                    for method in ['pointer','keyboard']:
                        page.set_viewport_size({'width':width,'height':height})
                        page.goto(base+'/login')
                        page.get_by_label('Почта',exact=True).fill(role+'@example.test')
                        page.get_by_label('Пароль',exact=True).fill(password)
                        page.get_by_role('button',name='Войти',exact=True).click()
                        page.wait_for_url(base+'/')
                        logout=page.get_by_role('button',name='Выйти',exact=True)
                        if method=='keyboard':
                            page.locator('.brand').focus()
                            for _ in range(30):
                                if logout.evaluate('(e)=>e===document.activeElement'): break
                                page.keyboard.press('Tab')
                            assert logout.evaluate('(e)=>e===document.activeElement')
                            rect=logout.bounding_box()
                            assert rect['y']>=0 and rect['y']+rect['height']<=height
                            with page.expect_navigation():
                                page.keyboard.press('Enter')
                        else:
                            with page.expect_navigation():
                                logout.click()
                        page.wait_for_url(base+'/')
                        assert page.get_by_role('link',name='Войти',exact=True).count()==1
                        results['layouts'].append(dict(role=role,width=width,height=height,logout=method))
            page.goto(base+'/login')
            page.get_by_label('Почта',exact=True).fill('member@example.test')
            page.get_by_label('Пароль',exact=True).fill(password)
            page.get_by_role('button',name='Войти',exact=True).click()
            page.wait_for_url(base+'/')
            with sqlite3.connect(database) as db:
                ids=[r[0] for r in db.execute("SELECT lesson_id FROM route_steps WHERE route_id='path-essentials' ORDER BY position")]
                user=db.execute("SELECT id FROM users WHERE email='member@example.test'").fetchone()[0]
                db.executemany('INSERT INTO progress(user_id,lesson_id,completed) VALUES(?,?,1)',[(user,i) for i in ids[:28]])
            page.goto(base+'/lessons/'+ids[32])
            for width in [390,1440]:
                page.set_viewport_size({'width':width,'height':900})
                page.goto(base+'/routes/path-essentials')
                link=page.locator('section[aria-label="Продолжить маршрут"] a.button')
                assert link.get_attribute('href')=='/lessons/'+ids[32]
                assert page.locator('.route-group').count()==9
                assert page.locator('.route-group[open]').count()==1
                assert page.locator('.route-group[open] [aria-current="step"]').get_attribute('href')=='/lessons/'+ids[32]
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                page.screenshot(path=str(out/f'resume-{width}.png'),full_page=True)
                link.focus();page.keyboard.press('Enter')
                page.wait_for_url(base+'/lessons/'+ids[32])
                results['layouts'].append(dict(width=width,late_route_resume=True,groups=9))
            assert not results['errors']
            browser.close()
    finally:
        server.shutdown()
    (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(json.dumps(results,ensure_ascii=False))
