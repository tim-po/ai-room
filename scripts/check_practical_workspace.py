"""Isolated practical UI lifecycle; mock provider is not AI acceptance."""
import json, os, sqlite3, subprocess, sys, tempfile, threading
from pathlib import Path
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
from club import create_app
from club.seed import seed_database
sys.path.insert(0,str(Path('tests').resolve()))
from test_teaching_pipeline import MockProvider
out=Path(os.environ.get('PRACTICAL_EVIDENCE','/tmp/practical-evidence'));out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    os.environ['CLUB_SEED_PASSWORD']='local-browser-test-only'
    database=str(Path(tmp)/'test.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text());seed_database(db)
    app=create_app({'DATABASE':database,'SECRET_KEY':'disposable-practical','TESTING':True,'TEACHING_UPLOAD_DIR':str(Path(tmp)/'uploads'),'TEACHING_PROVIDER_FACTORY':MockProvider})
    for command in ['init-skills','init-teaching']:
        result=app.test_cli_runner().invoke(args=[command]);assert result.exit_code==0,result.output
    server=make_server('127.0.0.1',0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}';errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        teacher=browser.new_page(viewport={'width':1440,'height':1000});learner=browser.new_page(viewport={'width':390,'height':900})
        for p in [teacher,learner]:p.on('pageerror',lambda e:errors.append(str(e)))
        def login(p,email):
            p.goto(origin+'/login');p.locator('[name=email]').fill(email);p.locator('[name=password]').fill('local-browser-test-only');p.get_by_role('button',name='Войти',exact=True).click()
        login(teacher,'editor@example.test');teacher.goto(origin+'/admin')
        teacher.locator('#teacher-files').set_input_files({'name':'original-notes.md','mimeType':'text/markdown','buffer':b'Check claims against the original source and document uncertainty.'})
        teacher.get_by_role('button',name='Загрузить видео и материалы').click();teacher.get_by_text('Ожидает обработки',exact=True).wait_for()
        result=app.test_cli_runner().invoke(args=['process-teaching-once']);assert result.exit_code==0 and 'ready' in result.output,result.output
        teacher.reload();teacher.get_by_role('button',name='Открыть проверку').click();teacher.get_by_text('Доступ и публикация',exact=True).click()
        teacher.get_by_label('Краткий итог редакторской проверки').fill('Fixture reviewed for UI workflow only, not learning acceptance.')
        teacher.get_by_label('Я проверил источники',exact=False).check();teacher.get_by_role('button',name='Опубликовать урок',exact=True).click()
        teacher.get_by_role('heading',name='Практика с проверкой преподавателем').wait_for()
        teacher.locator('.teacher-preview summary').click()
        teacher.get_by_label('Задание для демонстрации навыка').fill('Проверьте утверждение по первоисточнику. Приложите цитату, наблюдение и обоснованный вывод с ограничениями.')
        teacher.get_by_label('Критерии наблюдаемого результата').fill('Указаны первоисточник и точная цитата.\nВывод сопоставлен с цитатой, неопределённость обозначена.')
        teacher.get_by_label('Каждый критерий проверяем').check();teacher.get_by_role('button',name='Утвердить практическое задание').click()
        teacher.get_by_text('Практическое задание утверждено. Ученики могут отправить работу на проверку.',exact=True).wait_for()
        teacher.screenshot(path=str(out/'rubric-approved.png'),full_page=True)
        login(learner,'learner@example.test');learner.goto(origin+'/practice');learner.get_by_role('button',name='Открыть задание').click()
        field=learner.get_by_label('Ваш результат: действия, наблюдения и ссылки на доказательства');field.fill('Первый результат: источник найден, но вывод требует уточнения.')
        learner.get_by_role('button',name='Сохранить черновик').focus();learner.keyboard.press('Enter');learner.get_by_text('Черновик сохранён в аккаунте.',exact=True).wait_for();saved=learner.url
        learner.reload();assert field.input_value().startswith('Первый результат')
        second=browser.new_page();login(second,'learner@example.test');second.goto(saved)
        second.get_by_label('Ваш результат: действия, наблюдения и ссылки на доказательства').wait_for()
        assert second.get_by_label('Ваш результат: действия, наблюдения и ссылки на доказательства').input_value().startswith('Первый результат');second.close()
        for width in [360,390,768,1440]:
            learner.set_viewport_size({'width':width,'height':900});assert not learner.evaluate('document.documentElement.scrollWidth>innerWidth');learner.screenshot(path=str(out/f'practical-draft-{width}.png'),full_page=True)
        learner.route('**/api/skills/practical-submissions/*',lambda route:route.abort() if route.request.method=='PUT' else route.continue_())
        field.fill('Исправленный результат с точной цитатой.');learner.get_by_role('button',name='Сохранить черновик').click();learner.get_by_text('Нет связи. Текст остаётся на странице; повторите сохранение.',exact=True).wait_for();assert field.input_value().startswith('Исправленный')
        learner.unroute('**/api/skills/practical-submissions/*');learner.get_by_role('button',name='Отправить преподавателю').click();learner.get_by_text('Ожидает проверки преподавателем',exact=True).wait_for()
        teacher.goto(origin+'/admin/practice');teacher.get_by_role('link',name='Ожидает проверки преподавателем',exact=False).click()
        teacher.locator('#practical-body select').first.wait_for()
        for width in [360,390,768,1440]:
            teacher.set_viewport_size({'width':width,'height':900});assert not teacher.evaluate('document.documentElement.scrollWidth>innerWidth');teacher.screenshot(path=str(out/f'practical-review-{width}.png'),full_page=True)
        teacher.locator('#practical-body select').nth(0).select_option('met');teacher.locator('#practical-body select').nth(1).select_option('uncertain')
        teacher.get_by_label('Обратная связь и следующий шаг').fill('Добавьте наблюдение, которое связывает цитату и вывод.');teacher.get_by_role('button',name='Сохранить решение').click();teacher.get_by_role('heading',name='Работу можно доработать').wait_for()
        learner.goto(saved);learner.get_by_role('heading',name='Работу можно доработать').wait_for();learner.get_by_role('button',name='Создать новую попытку').click()
        learner.wait_for_url(lambda url:str(url)!=saved)
        assert learner.url!=saved
        learner.get_by_label('Ваш результат: действия, наблюдения и ссылки на доказательства').fill('Повторная работа: приведены цитата, наблюдение, вывод и границы достоверности.')
        learner.get_by_text('Другие попытки по этому заданию',exact=True).wait_for()
        learner.get_by_role('button',name='Отправить преподавателю').click();learner.get_by_text('Ожидает проверки преподавателем',exact=True).wait_for();accepted=learner.url
        teacher.goto(origin+'/admin/practice');teacher.get_by_role('link',name='Ожидает проверки преподавателем',exact=False).click()
        teacher.locator('#practical-body select').first.wait_for()
        for select in teacher.locator('#practical-body select').all():select.select_option('met')
        teacher.get_by_label('Обратная связь и следующий шаг').fill('Наблюдаемый результат соответствует всем критериям.')
        teacher.get_by_role('button',name='Сохранить решение').click();teacher.get_by_role('heading',name='Применение подтверждено',exact=True).wait_for()
        learner.goto('/'.join([origin,'profile']));learner.get_by_role('link',name='· Работа и решение преподавателя →',exact=True).click();assert learner.url==accepted
        learner.get_by_role('heading',name='Применение подтверждено',exact=True).wait_for();learner.screenshot(path=str(out/'practical-accepted.png'),full_page=True)
        with sqlite3.connect(database) as db:
            assert db.execute('SELECT COUNT(*) FROM skill_application_evidence').fetchone()[0]==1
            assert db.execute('SELECT COUNT(*) FROM skill_evidence').fetchone()[0]==0
            assert db.execute('SELECT COUNT(*) FROM progress').fetchone()[0]==0
        learner.goto(origin+'/profile');hover=learner.locator('.profile-support summary').first;hover.hover()
        assert hover.evaluate('el=>getComputedStyle(el).color')=='rgb(16, 24, 33)'
        learner.goto(origin+'/?node=coding');disclosure=learner.get_by_text('Навыки этого раздела',exact=True);disclosure.hover()
        assert disclosure.evaluate('el=>getComputedStyle(el).color')=='rgb(16, 24, 33)'
        assert not errors,errors;browser.close()
    server.shutdown();(out/'browser.json').write_text(json.dumps({'source':str(Path.cwd()),'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'origin':origin,'provider':'explicit mock only','rubric_approval':True,'save_refresh_resume':True,'network_failure_retains_text':True,'uncertain_then_revise_then_accept':True,'history_links':True,'application_only_evidence':True,'keyboard_save':True,'second_browser_resume':True,'cream_disclosure_ink':'#101821','widths':[360,390,768,1440],'errors':errors},ensure_ascii=False,indent=2))
