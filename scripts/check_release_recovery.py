"""Local fixture integration: live availability preview and replacement navigation."""
import json, os, sqlite3, subprocess, sys, tempfile, threading
from pathlib import Path
from urllib.parse import urlencode
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
from club import create_app
from club.seed import seed_database
sys.path.insert(0, str(Path('tests').resolve()))
from test_learning import PASSWORD, login, post
from test_skills import fixture_form, publish_copy
from test_practical import setup_task
from test_form_lifecycle import withdraw

out = Path(os.environ.get('RECOVERY_EVIDENCE', '/tmp/release-recovery'))
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    os.environ['CLUB_SEED_PASSWORD'] = PASSWORD
    database = str(Path(tmp) / 'test.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text()); seed_database(db)
    app = create_app(dict(TESTING=True, DATABASE=database, SECRET_KEY='disposable-recovery', TEACHING_UPLOAD_DIR=str(Path(tmp)/'uploads')))
    for command in ['init-skills', 'init-teaching', 'init-skills']:
        result = app.test_cli_runner().invoke(args=[command]); assert result.exit_code == 0, result.output
    backups = list(Path(tmp).glob('*.before-skills-*.sqlite'))
    assert len(backups) == 2 and all(p.stat().st_mode & 0o777 == 0o600 for p in backups)
    admin, token, task, _ = setup_task(app)
    publish_copy(app, fixture_form(), 'replacement')
    server = make_server('127.0.0.1', 0, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        def page_for(who):
            page = browser.new_page(viewport={'width':390,'height':844})
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(origin+'/login'); page.locator('[name=email]').fill(who+'@example.test')
            page.locator('[name=password]').fill(PASSWORD); page.get_by_role('button',name='Войти',exact=True).click()
            return page
        editor = page_for('admin')
        editor.goto(origin+'/admin/tree'); editor.get_by_label('Зачем изменить дерево').fill('Проверить сохранение доступных заданий после изменения дерева.')
        editor.get_by_role('button',name='Создать предложение',exact=True).click()
        editor.get_by_text('Изменить место или название',exact=True).click()
        editor.get_by_label('Навык или раздел',exact=True).select_option('coding.mobile')
        editor.get_by_label('Название',exact=True).fill('Мобильные приложения с AI')
        editor.get_by_role('button',name='Сохранить место и название',exact=True).click()
        editor.get_by_text('Правки сохранены. Проверьте обновлённое сравнение перед утверждением.',exact=True).wait_for()
        editor.get_by_text('Проверки понимания: сохраняются 2, добавляются 0, недоступны 0',exact=True).click()
        editor.get_by_text('test-form-v1',exact=True).wait_for()
        editor.get_by_text('Практические задания: сохраняются 1, добавляются 0, недоступны 0',exact=True).click()
        editor.get_by_text(task['id'],exact=True).wait_for()
        assert not editor.evaluate('document.documentElement.scrollWidth>innerWidth')
        editor.screenshot(path=str(out/'availability-390.png'),full_page=True)
        editor.get_by_label('Я проверил смысл, отсутствие дублей и влияние на обучение').check()
        editor.get_by_role('button',name='Утвердить дерево',exact=True).click()
        editor.get_by_role('heading',name='Доступность после возврата',exact=True).wait_for()
        editor.get_by_role('button',name='Вернуть прежнее дерево',exact=True).click()
        editor.get_by_text('Отменено',exact=True).wait_for()
        learner = page_for('learner')
        learner.goto(origin+'/challenges?'+urlencode(dict(node='basic-ai.verification',assessment='test-form-v1')))
        learner.get_by_role('button',name='Начать проверку').click()
        learner.locator('.challenge-question').first.wait_for(); pending_url = learner.url
        assert withdraw(admin,token,'replacement').status_code == 201
        learner.reload()
        learner.get_by_text('Сначала завершите начатую проверку ниже',exact=False).wait_for()
        assert learner.get_by_role('link',name='Открыть актуальную проверку →').count() == 0
        assert learner.get_by_text('Для зачёта:',exact=False).count() == 0
        learner.get_by_role('button',name='Перейти к ответам').click()
        assert learner.locator('#challenge-body input').first.evaluate('e=>e===document.activeElement')
        learner.screenshot(path=str(out/'withdrawn-pending-390.png'),full_page=True)
        for item in fixture_form()['items']:
            learner.locator(f'input[name="{item["id"]}"][value="check"]').check()
        learner.get_by_role('button',name='Проверить ответы').click()
        learner.get_by_role('heading',name='Проверка пройдена · без нового зачёта',exact=True).wait_for()
        learner.get_by_role('link',name='Открыть актуальную проверку →').click()
        learner.get_by_role('button',name='Начать проверку').wait_for()
        assert 'assessment=replacement' in learner.url
        learner.goto(pending_url)
        learner.get_by_role('link',name='Открыть актуальную проверку →').wait_for()
        assert post(admin,'/api/skills/forms/replacement/withdraw',dict(reason='Заменяющая форма также требует исправления.',confirm_reviewed=True),token).status_code == 201
        learner.get_by_role('link',name='Открыть актуальную проверку →').click()
        learner.get_by_text('Замена больше недоступна. Вернитесь к навыку, чтобы выбрать следующий шаг.',exact=True).wait_for()
        learner.reload(); learner.get_by_role('heading',name='Проверка отозвана',exact=True).wait_for()
        assert learner.get_by_role('link',name='Открыть актуальную проверку →').count() == 0
        learner.screenshot(path=str(out/'withdrawn-result-390.png'),full_page=True)
        learner.goto(origin+'/?node=basic-ai.verification')
        learner.get_by_text('↗ Проверено · пока не подтверждено',exact=True).first.wait_for()
        learner.goto(origin+'/?node=coding.mobile.demonstrate')
        learner.get_by_text('Материалы и задания для этого навыка ещё готовятся.',exact=True).wait_for()
        learner.locator('#node-detail').get_by_role('button',name='← Мобильные приложения',exact=True).click()
        learner.get_by_role('heading',name='Мобильные приложения',exact=True).wait_for()
        assert 'node=coding.mobile' in learner.url
        editor.goto(origin+'/admin/measurement')
        editor.get_by_text('Навыки, диагностика и работа преподавателей',exact=True).click()
        editor.get_by_role('link',name='Открыть агрегаты за последние 30 календарных дат (JSON) →').click()
        result = json.loads(editor.locator('body').inner_text())
        assert result['semantics'] == 'created_in_window_current_outcome'
        assert not errors, errors
        browser.close()
    server.shutdown()
    evidence = dict(source=str(Path.cwd()),commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),origin=origin,private_backups=len(backups),pending_overlap_explained_without_loop=True,completed_replacement_link_followed=True,withdrawn_replacement_rechecked_on_click=True,graph_inventory_preview=True,measurement_link=True,assessed_unverified_label=True,empty_node_parent_recovery=True,errors=errors,scope='Synthetic local fixture, not provider or editorial acceptance')
    (out/'browser.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    print(json.dumps(evidence))
