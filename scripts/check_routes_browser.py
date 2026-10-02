"""Isolated HTTP/browser route verification; writes no shared learner records."""
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys
import tempfile
import threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from club import create_app
from club.seed import seed_database
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

out=Path(os.environ.get('CLUB_EVIDENCE_DIR','instance/route-evidence'));out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='club-route-check-') as folder:
    password=secrets.token_urlsafe(24);os.environ['CLUB_SEED_PASSWORD']=password
    database=str(Path(folder)/'check.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text());seed_database(db)
    app=create_app({'DATABASE':database,'SECRET_KEY':secrets.token_hex(32)})
    server=make_server('127.0.0.1',0,app,threaded=True)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    results={'layouts':[],'errors':[]}
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            context=browser.new_context(viewport={'width':1440,'height':1000})
            page=context.new_page();page.on('pageerror',lambda err:results['errors'].append(str(err)))
            def sign_in(who):
                page.goto(base+'/login')
                page.get_by_label('Почта',exact=True).fill(who+'@example.test')
                page.get_by_label('Пароль',exact=True).fill(password)
                page.get_by_role('button',name='Войти',exact=True).click();page.wait_for_url(base+'/')
            sign_in('learner')
            page.goto(base+'/preferences')
            page.locator('[name=goal]').select_option('agents')
            page.locator('[name=experience]').select_option('beginner')
            page.locator('main button[type=submit], main button').first.click();page.wait_for_url(base+'/')
            assert page.locator('.hero a.button').get_attribute('href')=='/lessons/foundations-start-01'
            assert 'Сначала основы' in page.locator('.hero').inner_text()
            for width in [360,390,768,1440]:
                page.set_viewport_size({'width':width,'height':1000})
                for route in ['/','/routes','/routes/path-agents','/profile']:
                    assert page.goto(base+route).status==200
                    overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth')
                    results['layouts'].append({'width':width,'route':route,'overflow':overflow})
                    assert not overflow,(width,route)
                page.goto(base+'/routes/path-agents');page.screenshot(path=str(out/f'route-{width}.png'),full_page=True)
            page.goto(base+'/routes/path-work')
            page.get_by_role('button',name='Выбрать этот маршрут').click();page.wait_for_url(base+'/')
            assert 'AI для работы' in page.locator('.home-panels').inner_text()
            results['beginner_and_switch']=True
            for goal, target in [('work','everyday-ai-intro-01'),('agents','agent-api-basics')]:
                page.goto(base+'/routes/path-'+goal)
                select_route = page.get_by_role('button',name='Выбрать этот маршрут')
                if select_route.count():
                    select_route.click();page.wait_for_url(base+'/')
                else:
                    assert page.get_by_text('Ваш выбранный маршрут',exact=True).is_visible()
                for identity in ['foundations-start-01','foundations-start-02']:
                    page.goto(base+'/lessons/'+identity)
                    complete = page.get_by_role('button',name='Отметить завершённым',exact=True)
                    if complete.count():
                        complete.click();page.get_by_role('button',name='Вернуть в работу',exact=True).wait_for()
                for width in [360,390,768,1440]:
                    page.set_viewport_size({'width':width,'height':1000})
                    page.goto(base+'/lessons/foundations-start-02')
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                    next_step=page.get_by_role('link',name='Следующий шаг маршрута:',exact=False)
                    assert next_step.get_attribute('href')=='/lessons/'+target
                    next_step.focus();page.keyboard.press('Enter');page.wait_for_url(base+'/lessons/'+target)
                page.screenshot(path=str(out/f'route-transition-{goal}.png'),full_page=True)
            results['route_bridge_keyboard_transitions']=True
            page.get_by_role('button',name='Выйти',exact=True).click()
            sign_in('editor')
            for width in [360,390,768,1440]:
                page.set_viewport_size({'width':width,'height':1000})
                for route in ['/admin/routes','/admin/routes/path-agents','/admin/routes/path-agents/preview']:
                    assert page.goto(base+route).status==200
                    overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth')
                    results['layouts'].append({'width':width,'route':route,'overflow':overflow})
                    assert not overflow,(width,route)
            page.goto(base+'/admin/routes/path-agents')
            page.get_by_label('Название',exact=True).fill('Агенты: проверка сохранения')
            context.set_offline(True)
            page.get_by_role('button',name='Сохранить маршрут',exact=True).click()
            page.get_by_text('Нет связи с сервером.',exact=False).wait_for()
            assert page.get_by_label('Название',exact=True).input_value()=='Агенты: проверка сохранения'
            context.set_offline(False)
            page.get_by_role('button',name='Сохранить маршрут',exact=True).click()
            page.get_by_text('Маршрут сохранён. Прогресс общих уроков сохранён.',exact=True).wait_for()
            page.screenshot(path=str(out/'editor-1440.png'),full_page=True)
            results['offline_retry_saved']=True
            page.locator('summary').focus();page.keyboard.press('Enter')
            assert page.locator('details').get_attribute('open') is not None
            results['keyboard_disclosure']=True
            assert not results['errors'],results['errors']
            browser.close()
    finally:
        server.shutdown();thread.join()
    (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(json.dumps(results,ensure_ascii=False))
