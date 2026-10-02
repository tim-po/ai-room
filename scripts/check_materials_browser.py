"""Isolated browser evidence for combined discovery and standalone material authoring."""
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import sys
import tempfile
import threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from club import create_app
from club.seed import seed_database
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

out=Path(os.environ.get('CLUB_EVIDENCE_DIR','instance/material-evidence'));out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='club-material-check-') as folder:
    password=secrets.token_urlsafe(24);os.environ['CLUB_SEED_PASSWORD']=password
    database=str(Path(folder)/'check.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text());seed_database(db)
    app=create_app({'DATABASE':database,'SECRET_KEY':secrets.token_hex(32)})
    app.instance_path=folder
    (Path(folder)/'media').mkdir()
    shutil.copyfile('instance/media/fixture.webm',Path(folder)/'media/fixture.webm')
    server=make_server('127.0.0.1',0,app,threaded=True)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    results={'layouts':[],'errors':[]}
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            context=browser.new_context(viewport={'width':1440,'height':1000}, reduced_motion='reduce')
            page=context.new_page();page.on('pageerror',lambda err:results['errors'].append(str(err)))
            def sign_in(who):
                page.goto(base+'/login');page.get_by_label('Почта',exact=True).fill(who+'@example.test')
                page.get_by_label('Пароль',exact=True).fill(password);page.get_by_role('button',name='Войти',exact=True).click();page.wait_for_url(base+'/')
            sign_in('member')
            for width in [360,390,768,1440]:
                page.set_viewport_size({'width':width,'height':1000})
                for route in ['/catalogue','/materials/guide-check-answer','/materials/workshop-prompt-lab','/profile']:
                    assert page.goto(base+route).status==200
                    overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth')
                    results['layouts'].append({'width':width,'route':route,'overflow':overflow})
                    assert not overflow,(width,route)
                if width in [390,1440]:
                    page.goto(base+'/catalogue');page.screenshot(path=str(out/f'catalogue-{width}.png'),full_page=True)
            page.goto(base+'/catalogue')
            page.locator('select[name=format]').select_option('workshop')
            page.locator('select[name=goal]').select_option('work')
            page.get_by_label('Инструмент',exact=True).fill('Текстовый AI')
            page.get_by_role('button',name='Найти',exact=True).click()
            assert page.locator('.card').count()==1
            filter_url=page.url
            page.get_by_role('link',name='Мастерская запросов: учебная запись',exact=True).click()
            video=page.locator('video');video.evaluate('(v)=>v.play()')
            page.wait_for_function('() => document.querySelector("video").currentTime > 1.5')
            video.evaluate('(v)=>v.pause()')
            page.get_by_text('Позиция просмотра сохранена.',exact=True).wait_for()
            position=video.evaluate('(v)=>v.currentTime')
            page.reload();page.wait_for_function('() => document.querySelector("video").currentTime > 1')
            assert abs(video.evaluate('(v)=>v.currentTime')-position)<1
            results['video_playback_and_resume']=True
            page.get_by_role('button',name='В избранное',exact=True).click()
            page.get_by_role('button',name='Убрать из избранного',exact=True).wait_for()
            page.goto(base+'/profile');assert page.locator('a[href="/materials/workshop-prompt-lab"]').count()==1
            results['favourite_in_profile']=True
            page.goto(filter_url);page.get_by_role('link',name='Мастерская запросов: учебная запись',exact=True).click();page.go_back()
            assert page.url==filter_url and page.locator('.card').count()==1
            results['combined_filter_back_navigation']=True
            page.goto(base+'/materials/workshop-prompt-lab')
            with page.expect_download() as download:
                page.get_by_role('link',name='Рабочий чек-лист',exact=False).click()
            assert 'Факты проверены' in Path(download.value.path()).read_text()
            results['protected_download']=True
            (Path(folder)/'media/fixture.webm').unlink()
            page.reload();page.get_by_text('Видео недоступно. Обновите страницу или продолжите по тексту ниже.',exact=True).wait_for()
            results['media_fallback']=True
            shutil.copyfile('instance/media/fixture.webm',Path(folder)/'media/fixture.webm')
            page.get_by_role('button',name='Выйти',exact=True).click();sign_in('editor')
            for width in [360,390,768,1440]:
                page.set_viewport_size({'width':width,'height':1000})
                for route in ['/admin/materials','/admin/materials/workshop-prompt-lab','/admin/materials/workshop-prompt-lab/preview']:
                    assert page.goto(base+route).status==200
                    overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth')
                    results['layouts'].append({'width':width,'route':route,'overflow':overflow})
                    assert not overflow,(width,route)
            page.goto(base+'/admin/materials/workshop-prompt-lab')
            page.get_by_label('Название',exact=True).fill('Мастерская: проверка сохранения')
            context.set_offline(True);page.get_by_role('button',name='Сохранить материал',exact=True).click()
            page.get_by_text('Нет связи с сервером.',exact=False).wait_for()
            assert page.get_by_label('Название',exact=True).input_value()=='Мастерская: проверка сохранения'
            context.set_offline(False);page.get_by_role('button',name='Сохранить материал',exact=True).click()
            page.get_by_text('Материал сохранён. Статус: Опубликован.',exact=True).wait_for()
            results['offline_retry_saved']=True
            page.locator('select[name=status]').select_option('draft')
            page.get_by_role('button',name='Сохранить материал',exact=True).focus();page.keyboard.press('Enter')
            page.get_by_text('Материал сохранён. Статус: Черновик.',exact=True).wait_for()
            page.get_by_role('link',name='Предпросмотр для ученика',exact=True).focus();page.keyboard.press('Enter')
            page.wait_for_url('**/preview');assert page.locator('h1').inner_text()=='Мастерская: проверка сохранения'
            results['keyboard_draft_and_preview']=True
            page.screenshot(path=str(out/'preview-1440.png'),full_page=True)
            assert context.request.get(base+'/materials/workshop-prompt-lab').status==404
            assert not results['errors'],results['errors']
            browser.close()
    finally:
        server.shutdown();thread.join()
    (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(json.dumps(results,ensure_ascii=False))
