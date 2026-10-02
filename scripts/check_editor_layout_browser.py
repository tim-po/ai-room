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
            page.goto(base+'/login')
            page.get_by_label('Почта', exact=True).fill('editor@example.test')
            page.get_by_label('Пароль', exact=True).fill(password)
            page.get_by_role('button', name='Войти', exact=True).click()
            page.wait_for_url(base+'/')
            for width in [360,390,768,1440]:
                page.set_viewport_size({'width':width,'height':900})
                page.goto(base+'/admin/content/courses/ai-foundations')
                modules=page.locator('.editor-module')
                assert modules.count()==9
                assert page.locator('.editor-module[open]').count()==1
                last=modules.last
                identity=last.get_attribute('id')
                summary=last.locator('summary')
                summary.focus();page.keyboard.press('Enter')
                last.get_by_label('Название модуля',exact=True).fill('Длинное название модуля для проверки редактора')
                last.get_by_role('button',name='Сохранить название',exact=True).click()
                page.wait_for_url('**/ai-foundations#'+identity)
                page.wait_for_function("(id) => document.getElementById(id).open",arg=identity)
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                page.screenshot(path=str(out/f'course-{width}.png'),full_page=True)
                page.goto(base+'/admin/routes/path-essentials')
                steps=page.locator('[data-route-step]')
                assert steps.count()>=37
                first=steps.nth(0).locator('select').input_value()
                second=steps.nth(1).locator('select').input_value()
                steps.nth(1).get_by_role('button',name='Поднять шаг 2',exact=True).focus()
                page.keyboard.press('Enter')
                assert steps.nth(0).locator('select').input_value()==second
                assert steps.nth(1).locator('select').input_value()==first
                assert steps.nth(0).locator('.selected-step strong').inner_text() in steps.nth(0).locator('select').inner_text()
                assert page.locator('[data-save-status]').inner_text().startswith('Есть несохранённые')
                with page.expect_navigation(wait_until='networkidle'):
                    page.get_by_role('button',name='Сохранить маршрут',exact=True).click()
                assert steps.nth(0).locator('select').input_value()==second
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                steps.nth(0).scroll_into_view_if_needed()
                page.screenshot(path=str(out/f'route-{width}.png'))
                results['layouts'].append({'width':width,'module_rename_location':True,'route_keyboard_reorder_persisted':True,'overflow':False})
            assert not results['errors']
            browser.close()
    finally:
        server.shutdown()
    (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
