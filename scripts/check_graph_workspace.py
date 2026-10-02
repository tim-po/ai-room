"""Disposable graph editorial browser journey; no staging or provider access."""
import json, os, sqlite3, subprocess, sys, tempfile, threading
from pathlib import Path
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
from club import create_app
from club.seed import seed_database
sys.path.insert(0,str(Path('tests').resolve()))
from test_teaching_pipeline import MockProvider
out=Path(os.environ.get('GRAPH_EVIDENCE','/tmp/graph-review-evidence'));out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    os.environ['CLUB_SEED_PASSWORD']='local-browser-test-only'
    database=str(Path(tmp)/'test.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text());seed_database(db)
    app=create_app({'DATABASE':database,'SECRET_KEY':'disposable-graph','TESTING':True,'TEACHING_UPLOAD_DIR':str(Path(tmp)/'uploads'),'TEACHING_PROVIDER_FACTORY':MockProvider})
    for command in ['init-skills','init-teaching']:
        result=app.test_cli_runner().invoke(args=[command]);assert result.exit_code==0,result.output
    server=make_server('127.0.0.1',0,app);threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}';errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(origin+'/login');page.locator('[name=email]').fill('editor@example.test');page.locator('[name=password]').fill('local-browser-test-only');page.get_by_role('button',name='Войти',exact=True).click()
        page.goto(origin+'/admin')
        page.locator('#teacher-files').set_input_files({'name':'source.md','mimeType':'text/markdown','buffer':b'Check claims against the original source and document uncertainty.'})
        page.get_by_role('button',name='Загрузить видео и материалы').click();page.get_by_text('Ожидает обработки',exact=True).wait_for()
        result=app.test_cli_runner().invoke(args=['process-teaching-once']);assert result.exit_code==0,result.output
        page.reload();page.get_by_role('button',name='Открыть проверку').click();page.get_by_role('link',name='Рассмотреть изменение общего дерева →',exact=True).click()
        page.get_by_label('Зачем изменить дерево').fill('Проверить предложения из сохранённого источника.')
        page.get_by_role('button',name='Создать предложение из материала').click()
        page.get_by_text('Предложения из материала',exact=True).click()
        page.get_by_text('source.md · редакция 1',exact=True).click()
        page.get_by_text('Абзац 1 — Check claims against the original source and document uncertainty.',exact=True).wait_for()
        page.goto(origin+'/admin/tree')
        page.get_by_label('Зачем изменить дерево').fill('Добавить проверку отзыва разрешения без изменения существующих способностей.')
        page.get_by_role('button',name='Создать предложение',exact=True).click()
        page.get_by_text('Добавить способность или раздел',exact=True).click()
        page.get_by_label('Название новой способности',exact=True).fill('Проверить отзыв разрешения')
        page.get_by_label('Родительский раздел',exact=True).select_option('coding.mobile')
        page.get_by_role('button',name='Добавить и сохранить',exact=True).focus();page.keyboard.press('Enter')
        page.get_by_text('Новая способность или раздел: Проверить отзыв разрешения',exact=True).wait_for()
        saved=page.url;page.reload();page.get_by_text('Новая способность или раздел: Проверить отзыв разрешения',exact=True).wait_for()
        page.get_by_text('Изменить место или название',exact=True).click()
        page.get_by_label('Навык или раздел',exact=True).select_option(label='Проверить отзыв разрешения')
        page.get_by_label('Название',exact=True).fill('Проверить отказ после отзыва разрешения')
        page.get_by_role('button',name='Сохранить место и название',exact=True).click()
        page.get_by_text('Новая способность или раздел: Проверить отказ после отзыва разрешения',exact=True).wait_for()
        for width in [360,390,768,1440]:
            page.set_viewport_size({'width':width,'height':1000});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth');page.screenshot(path=str(out/f'graph-review-{width}.png'),full_page=True)
        page.get_by_role('button',name='Утвердить дерево',exact=True).click();page.get_by_text('Подтвердите редакторскую проверку.',exact=True).wait_for()
        page.get_by_label('Я проверил смысл, отсутствие дублей и влияние на обучение').check()
        page.get_by_role('button',name='Утвердить дерево',exact=True).click();page.get_by_role('button',name='Вернуть прежнее дерево',exact=True).wait_for()
        assert any(n['title']=='Проверить отказ после отзыва разрешения' for n in page.request.get(origin+'/api/skills/graph').json()['nodes'])
        page.get_by_role('button',name='Вернуть прежнее дерево',exact=True).click();page.get_by_text('Отменено',exact=True).wait_for()
        assert not any(n['title']=='Проверить отказ после отзыва разрешения' for n in page.request.get(origin+'/api/skills/graph').json()['nodes'])
        page.goto(origin+'/admin/tree');page.get_by_label('Зачем изменить дерево').fill('Проверить отклонение дублирующего предложения.')
        page.get_by_role('button',name='Создать предложение',exact=True).click();page.get_by_role('button',name='Отклонить предложение',exact=True).click();page.get_by_text('Отклонено',exact=True).wait_for()
        assert not errors,errors
        browser.close()
    server.shutdown();(out/'browser.json').write_text(json.dumps({'source':str(Path.cwd()),'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'origin':origin,'create_edit_refresh_activate_rollback_reject':True,'keyboard_save':True,'widths':[360,390,768,1440],'errors':errors},ensure_ascii=False,indent=2))
