"""Disposable UI contract check with explicit mock AI; never live-provider acceptance."""
import json, os, sqlite3, subprocess, sys, tempfile, threading
from pathlib import Path
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
from club import create_app
from club.seed import seed_database
sys.path.insert(0,str(Path('tests').resolve()))
from test_teaching_pipeline import MockProvider
out=Path(os.environ.get('TEACHER_EVIDENCE','/tmp/teacher-evidence'));out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    os.environ['CLUB_SEED_PASSWORD']='local-browser-test-only'
    database=str(Path(tmp)/'test.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text());seed_database(db)
    app=create_app({'DATABASE':database,'SECRET_KEY':'disposable-teacher','TESTING':True,'TEACHING_UPLOAD_DIR':str(Path(tmp)/'uploads'),'TEACHING_PROVIDER_FACTORY':MockProvider})
    for command in ['init-skills','init-teaching']:
        result=app.test_cli_runner().invoke(args=[command]);assert result.exit_code==0,result.output
    server=make_server('127.0.0.1',0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}';errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(origin+'/login');page.locator('[name=email]').fill('editor@example.test');page.locator('[name=password]').fill('local-browser-test-only');page.get_by_role('button',name='Войти',exact=True).click();page.goto(origin+'/admin')
        page.locator('#teacher-files').set_input_files([{'name':'synthetic-video.mp4','mimeType':'video/mp4','buffer':b'\0\0\0\x18ftypmp42'+b'\0'*32},{'name':'source-notes.md','mimeType':'text/markdown','buffer':b'Check the original source.'}])
        # Interrupt package assembly after both files have reached protected storage.
        page.route('**/api/teaching/jobs/*/package',lambda route:route.abort())
        page.get_by_role('button',name='Загрузить видео и материалы').click();page.get_by_text('Нет связи с сервером. Ваши изменения остаются на странице.',exact=True).wait_for()
        page.unroute('**/api/teaching/jobs/*/package');page.reload()
        page.locator('#teacher-saved-sources input').first.wait_for()
        assert page.locator('#teacher-saved-sources input').count()==2
        for check in page.locator('#teacher-saved-sources input').all():check.check()
        page.get_by_role('button',name='Загрузить видео и материалы').click();page.get_by_text('Ожидает обработки',exact=True).wait_for()
        with sqlite3.connect(database) as db:
            assert db.execute('SELECT COUNT(*) FROM teaching_uploads').fetchone()[0]==2
            assert db.execute('SELECT COUNT(*) FROM teaching_package_sources').fetchone()[0]==2
        assert page.locator('#teacher-saved-sources').is_hidden()
        page.screenshot(path=str(out/'teacher-upload.png'),full_page=True)
        result=app.test_cli_runner().invoke(args=['process-teaching-once']);assert result.exit_code==0,result.output;assert 'ready' in result.output,result.output
        page.reload();page.get_by_role('button',name='Открыть проверку').click();page.get_by_label('Название урока',exact=True).fill('Учебный пример: проверка источников');page.get_by_role('button',name='Сохранить правки').click();page.get_by_text('Правки сохранены.',exact=True).wait_for()
        page.get_by_role('button',name='Предпросмотр ученика').click();page.locator('.teacher-preview h3').wait_for();assert page.locator('.teacher-preview').get_by_text('Source supports verification.',exact=True).count()==0
        for width in [1440,390,360,768]:
            page.set_viewport_size({'width':width,'height':1000});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth');page.screenshot(path=str(out/f'teacher-review-{width}.png'),full_page=True)
        page.get_by_label('Краткий итог редакторской проверки').fill('Synthetic mock fixture reviewed for UI verification only.');page.get_by_label('Я проверил источники',exact=False).check();page.get_by_role('button',name='Опубликовать урок',exact=True).click();page.get_by_role('link',name='Открыть опубликованный урок').wait_for();page.get_by_role('link',name='Открыть опубликованный урок').click();page.get_by_role('heading',name='Учебный пример: проверка источников',exact=True).wait_for()
        assert not errors,errors;browser.close()
    server.shutdown();(out/'browser.json').write_text(json.dumps({'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source':str(Path.cwd()),'interrupted_package_recovery':True,'no_duplicate_uploads':True,'provider':'explicit mock only','origin':origin,'upload_package':True,'refresh_resume':True,'correct_preview_publish':True,'widths':[1440,390,360,768],'errors':errors},ensure_ascii=False,indent=2))
