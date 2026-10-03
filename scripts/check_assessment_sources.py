"""Disposable source-reader browser check; publication here is not editorial approval."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from club import create_app
from club.seed import seed_database
from club.skill_seed import graph_fixture
from club.transfer_candidates import candidates
from club.transfer_sources import install_sources, publication_candidate, publish_transfer

out = Path(os.environ.get('SOURCE_EVIDENCE', '/tmp/assessment-source-evidence'))
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    os.environ['CLUB_SEED_PASSWORD'] = 'source-browser-fixture-only'
    database = str(Path(tmp) / 'source.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text())
        seed_database(db)
    app = create_app({'TESTING': True, 'DATABASE': database, 'SECRET_KEY': 'source-browser-fixture'})
    result = app.test_cli_runner().invoke(args=['init-skills'])
    assert result.exit_code == 0, result.output
    with sqlite3.connect(database) as db:
        install_sources(db, 'user-admin')
        candidate = publication_candidate(db, candidates()[0]['id'], 'source-browser', 'foundations-start-01')
        publish_transfer(db, candidate_id=candidate['id'], form_id='source-browser', lesson_id='foundations-start-01',
                         graph=graph_fixture(), reviewer='user-admin', reviewed_sha256=candidate['sha256'], confirm_reviewed=True)
    server = make_server('127.0.0.1', 0, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(origin + '/login')
        page.locator('[name=email]').fill('learner@example.test')
        page.locator('[name=password]').fill('source-browser-fixture-only')
        page.get_by_role('button', name='Войти', exact=True).click()
        page.goto(origin + '/challenges?node=basic-ai.verification&assessment=source-browser')
        page.get_by_role('button', name='Начать проверку').click()
        for item in candidate['form']['items']:
            page.locator(f'input[name="{item["id"]}"][value="{item["answer"]}"]').check()
        page.get_by_role('button', name='Проверить ответы').click()
        page.get_by_text('Результат сохранён', exact=True).wait_for()
        with sqlite3.connect(database) as db:
            db.execute("UPDATE lessons SET body='CURRENT LESSON HAS CHANGED' WHERE id='foundations-start-01'")
        source = page.locator('.assessment-source').first
        summary = source.locator('summary')
        for width in [1440, 390, 360, 768]:
            page.set_viewport_size({'width': width, 'height': 900})
            summary.focus(); page.keyboard.press('Enter')
            source.get_by_text(candidate['source_snapshot']['text'], exact=True).wait_for()
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
            assert 'CURRENT LESSON HAS CHANGED' not in source.inner_text()
            page.screenshot(path=str(out / f'source-{width}.png'), full_page=True)
            summary.focus(); page.keyboard.press('Enter')
        url = candidate['form']['items'][0]['source']['snapshot_url']
        page.route('**' + url, lambda route: route.abort())
        summary.click()
        source.get_by_text('Нет связи с сервером. Повторите попытку.', exact=True).wait_for()
        page.unroute('**' + url)
        source.get_by_role('button', name='Повторить загрузку источника').click()
        source.get_by_text(candidate['source_snapshot']['text'], exact=True).wait_for()
        summary.click()
        with sqlite3.connect(database) as db:
            db.execute("UPDATE lessons SET status='draft' WHERE id='foundations-start-01'")
        summary.click()
        source.get_by_text('Проверьте доступ к материалу в профиле.', exact=True).wait_for()
        assert candidate['source_snapshot']['text'] not in source.inner_text()
        # Both consumers load the shared reader, including the diagnostic page.
        page.goto(origin + '/diagnostic')
        page.get_by_text('Выберите несколько направлений или проверьте только основу.', exact=True).wait_for()
        assert page.evaluate('typeof window.appendAssessmentSource') == 'function'
        # Untrusted source text is never interpreted as markup.
        page.evaluate("""() => { window.appendAssessmentSource(document.querySelector('#diagnostic-body'), {snapshot_url:'/api/skills/forms/test/sources/test/1'}); }""")
        page.route('**/api/skills/forms/test/sources/test/1', lambda route: route.fulfill(json={'text':'<img src=x onerror=alert(1)>', 'paragraph':1}))
        page.locator('.assessment-source summary').click()
        page.locator('.assessment-source').get_by_text('<img src=x onerror=alert(1)>', exact=True).wait_for()
        assert page.locator('.assessment-source img').count() == 0
        assert not errors, errors
        browser.close()
    server.shutdown()
(out / 'result.json').write_text(json.dumps({'passed': True, 'widths':[1440,390,360,768], 'checks':['historical text after lesson edit','keyboard disclosure','network retry','fresh access check after close','no overflow','text-only rendering','diagnostic shared reader'], 'errors': errors}, indent=2))
