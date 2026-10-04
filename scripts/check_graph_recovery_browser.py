"""Local synthetic graph lifecycle/conflict check. No AI provider or installed data."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading

from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server
from club import create_app
from club.seed import seed_database

sys.path.insert(0, str(Path('tests').resolve()))
from test_learning import PASSWORD, login, post
from test_skills import install_form

out = Path(os.environ.get('GRAPH_EVIDENCE', '/tmp/graph-recovery-evidence'))
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    os.environ['CLUB_SEED_PASSWORD'] = PASSWORD
    database = str(Path(tmp) / 'test.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text())
        seed_database(db)
    app = create_app(dict(DATABASE=database, SECRET_KEY='disposable-graph-recovery', TESTING=True))
    result = app.test_cli_runner().invoke(args=['init-skills'])
    assert result.exit_code == 0, result.output
    install_form(app)  # Explicit synthetic assessment fixture, not editorial acceptance.
    learner = app.test_client()
    csrf = login(learner)
    attempt = post(learner, '/api/skills/challenges', dict(assessment_id='test-form-v1', request_id='graph-retained'), csrf).json
    result = post(learner, '/api/skills/challenges/' + attempt['id'] + '/submit', dict(answers={'q1':'check', 'q2':'check'}), csrf)
    assert result.json['credited']

    def retained():
        with sqlite3.connect(database) as db:
            return {table: db.execute('SELECT * FROM ' + table + ' ORDER BY rowid').fetchall()
                    for table in ['skill_attempts', 'skill_results', 'skill_evidence', 'skill_forms']}

    before = retained()
    server = make_server('127.0.0.1', 0, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    errors, responses = [], []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            pages = [browser.new_page(viewport={'width':1440, 'height':1000}) for _ in range(2)]
            for page in pages:
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('response', lambda r: responses.append({'path':r.url.split(origin)[-1], 'status':r.status, 'method':r.request.method}) if '/api/skills/graph' in r.url else None)
                page.goto(origin + '/login')
                page.locator('[name=email]').fill('editor@example.test')
                page.locator('[name=password]').fill(PASSWORD)
                page.get_by_role('button', name='Войти', exact=True).click()
                page.goto(origin + '/admin/tree')
            page, other = pages
            initial = page.request.get(origin + '/api/skills/graph').json()
            page.get_by_label('Зачем изменить дерево').fill('Синтетическая проверка сохранения истории.')
            page.get_by_role('button', name='Создать предложение', exact=True).click()
            page.get_by_text('Добавить способность или раздел', exact=True).click()
            page.get_by_label('Название новой способности', exact=True).fill('Синтетический новый навык')
            page.get_by_label('Родительский раздел', exact=True).select_option('coding.mobile')
            page.get_by_role('button', name='Добавить и сохранить', exact=True).click()
            page.get_by_text('Новая способность или раздел: Синтетический новый навык', exact=True).wait_for()
            url = page.url
            other.goto(url)
            other.get_by_label('Пояснение редактора').fill('Сохранено вторым редактором.')
            other.get_by_role('button', name='Сохранить пояснение', exact=True).click()
            expect(other.locator('#graph-status')).to_contain_text('Правки сохранены')
            note = page.get_by_label('Пояснение редактора')
            note.fill('Мои несохранённые правки остаются доступны.')
            page.get_by_role('button', name='Сохранить пояснение', exact=True).click()
            expect(page.locator('#graph-status')).to_contain_text('Версия изменилась')
            expect(note).to_have_value('Мои несохранённые правки остаются доступны.')
            for width in [1440, 390]:
                page.set_viewport_size({'width':width, 'height':1000})
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
                page.screenshot(path=str(out / f'conflict-{width}.png'), full_page=True)
            # Network failure during recovery also leaves current fields intact.
            page.route('**/api/skills/graph-proposals/*', lambda route: route.abort() if route.request.method == 'GET' else route.continue_())
            reload_button = page.get_by_role('button', name='Отменить несохранённые правки и загрузить сохранённую версию', exact=True)
            reload_button.click()
            expect(page.locator('#graph-status')).to_contain_text('Нет связи')
            expect(note).to_have_value('Мои несохранённые правки остаются доступны.')
            page.unroute('**/api/skills/graph-proposals/*')
            reload_button.focus()
            page.keyboard.press('Enter')
            expect(note).to_have_value('Сохранено вторым редактором.')
            expect(page.locator('#graph-recovery')).to_be_hidden()
            page.get_by_role('button', name='Утвердить дерево', exact=True).click()
            expect(page.locator('#graph-status')).to_have_text('Подтвердите редакторскую проверку.')
            page.get_by_label('Я проверил смысл, отсутствие дублей и влияние на обучение').check()
            page.get_by_role('button', name='Утвердить дерево', exact=True).click()
            page.get_by_role('button', name='Вернуть прежнее дерево', exact=True).wait_for()
            activated = page.request.get(origin + '/api/skills/graph').json()
            assert len(activated['nodes']) == len(initial['nodes']) + 1
            assert retained() == before
            page.screenshot(path=str(out / 'active-390.png'), full_page=True)
            page.get_by_role('button', name='Вернуть прежнее дерево', exact=True).click()
            expect(page.locator('#graph-status')).to_have_text('Отменено')
            assert page.request.get(origin + '/api/skills/graph').json()['release'] == initial['release']
            assert retained() == before
            expect(note).to_have_attribute('readonly', '')
            page.reload()
            expect(note).to_have_attribute('readonly', '')
            assert retained() == before
            assert not errors, errors
            version = browser.version
            browser.close()
    finally:
        server.shutdown()
    report = dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  source_hashes={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['club/static/graph_review.js', 'club/templates/graph_review.html']},
                  origin=origin, browser=version, widths=[1440,390], height=1000,
                  graph_release=initial['release'], graph_sha256=hashlib.sha256(json.dumps(initial, sort_keys=True).encode()).hexdigest(),
                  synthetic_fixture='tests.test_skills.install_form; no provider processing',
                  conflict_retains_text=True, recovery_network_error_retains_text=True, keyboard_recovery=True,
                  activation_rollback=True, retained_counts={k:len(v) for k,v in before.items()},
                  exact_retained_rows_unchanged=True, errors=errors, responses=responses)
    (out / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
