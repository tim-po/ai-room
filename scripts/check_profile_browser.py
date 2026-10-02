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

out = Path(os.environ.get('CLUB_EVIDENCE_DIR', 'instance/profile-evidence'))
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='club-profile-') as folder:
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
            page = browser.new_page()
            page.on('pageerror', lambda err: results['errors'].append(str(err)))
            page.goto(base+'/login')
            page.get_by_label('Почта', exact=True).fill('learner@example.test')
            page.get_by_label('Пароль', exact=True).fill(password)
            page.get_by_role('button', name='Войти', exact=True).click()
            page.wait_for_url(base+'/')
            for width in [360,390,768,1440]:
                page.set_viewport_size({'width':width,'height':900})
                page.goto(base+'/profile')
                assert page.locator('.card').count() == 0
                assert 'Пока нет курсов в работе' in page.locator('main').inner_text()
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                page.screenshot(path=str(out/f'empty-{width}.png'),full_page=True)
                results['layouts'].append({'width':width,'state':'empty','overflow':False})
            page.goto(base+'/lessons/foundations-start-01')
            page.get_by_label('Ваш результат или ссылка',exact=True).fill('Моя сохранённая практика')
            page.get_by_role('button',name='Сохранить результат',exact=True).click()
            page.get_by_role('button',name='Отметить завершённым',exact=True).click()
            page.get_by_role('button',name='Вернуть в работу',exact=True).wait_for()
            for width in [360,390,768,1440]:
                page.set_viewport_size({'width':width,'height':900})
                page.goto(base+'/')
                assert 'Недельная цель: 1 из 2' in page.locator('.weekly-goal').inner_text()
                link = page.get_by_role('link',name='Мои результаты →',exact=True)
                link.focus();page.keyboard.press('Enter');page.wait_for_url(base+'/profile#practice')
                page.wait_for_function("() => Math.abs(document.getElementById('practice').getBoundingClientRect().top) < 150")
                assert 'Моя сохранённая практика' in page.locator('main').inner_text()
                assert page.locator('[aria-labelledby="active-learning"] .card').count()==1
                assert page.locator('[aria-labelledby="completed-learning"] .card').count()==0
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                page.screenshot(path=str(out/f'active-{width}.png'),full_page=True)
                results['layouts'].append({'width':width,'state':'active','overflow':False})
            page.goto(base+'/preferences')
            page.locator('[name=weekly_goal]').select_option('0')
            page.get_by_role('button',name='Сохранить маршрут',exact=True).click()
            page.wait_for_url(base+'/')
            assert 'Недельная цель на паузе' in page.locator('.weekly-goal').inner_text()
            results['keyboard_results_anchor']=True
            results['practice_completion_and_pause']=True
            assert not results['errors']
            browser.close()
    finally:
        server.shutdown()
    (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
