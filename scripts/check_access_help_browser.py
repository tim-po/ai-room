"""Isolated access recovery through actual learner and administrator forms."""
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

out = Path(os.environ.get('CLUB_EVIDENCE_DIR', 'instance/access-help-evidence'))
out.mkdir(parents=True, exist_ok=True)
results = []
with tempfile.TemporaryDirectory(prefix='club-help-check-') as folder:
    password = secrets.token_urlsafe(24)
    os.environ['CLUB_SEED_PASSWORD'] = password
    database = str(Path(folder) / 'check.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text())
        seed_database(db)
    app = create_app({'DATABASE': database, 'SECRET_KEY': secrets.token_hex(32)})
    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=['--no-sandbox'])
            for entitlement in ['free', 'revoked', 'expired']:
                with sqlite3.connect(database) as db:
                    db.execute("UPDATE users SET entitlement=? WHERE id='user-learner'", (entitlement,))
                for width in [390, 1440]:
                    context = browser.new_context(viewport={'width': width, 'height': 900})
                    page = context.new_page()
                    page.goto(base + '/login')
                    page.get_by_label('Почта', exact=True).fill('learner@example.test')
                    page.get_by_label('Пароль', exact=True).fill(password)
                    page.get_by_role('button', name='Войти', exact=True).click()
                    page.wait_for_url(base + '/')
                    assert page.goto(base + '/lessons/foundations-start-04').status == 200
                    page.get_by_role('link', name='Помощь с доступом').click()
                    assert page.get_by_role('heading', name='Задать вопрос').is_visible()
                    question = f'Проверка доступа: {entitlement}, {width}'
                    page.get_by_label('Что не получается?').fill(question)
                    page.get_by_role('button', name='Сохранить вопрос').click()
                    page.get_by_text(question, exact=True).wait_for()
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                    page.screenshot(path=str(out / f'{entitlement}-{width}.png'), full_page=True)
                    assert context.request.get(base + '/api/lessons/foundations-context-01').status == 403
                    results.append({'entitlement': entitlement, 'width': width, 'submitted': True, 'paid_api_denied': True})
                    context.close()
            context = browser.new_context()
            page = context.new_page()
            page.goto(base + '/login')
            page.get_by_label('Почта', exact=True).fill('admin@example.test')
            page.get_by_label('Пароль', exact=True).fill(password)
            page.get_by_role('button', name='Войти', exact=True).click()
            page.wait_for_url(base + '/')
            page.goto(base + '/admin')
            assert page.locator('main').inner_text().count('Проверка доступа:') == 6
            with sqlite3.connect(database) as db:
                assert db.execute("SELECT COUNT(*) FROM help_requests WHERE lesson_id='foundations-context-01'").fetchone()[0] == 6
            browser.close()
    finally:
        server.shutdown()
        thread.join()
(out / 'results.json').write_text(json.dumps({'journeys': results, 'admin_contexts': 6}, ensure_ascii=False, indent=2))
print('PASS: six access recovery journeys and administrator receipt')
