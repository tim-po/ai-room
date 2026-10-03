"""Disposable catalogue fixture: responsive discovery and keyboard filters."""
import json, os, sqlite3, tempfile, threading
from pathlib import Path
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
from club import create_app
from club.seed import seed_database

out = Path(os.environ.get('LIBRARY_EVIDENCE', '/tmp/library-evidence'))
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    os.environ['CLUB_SEED_PASSWORD'] = 'disposable-library-password-928!'
    database = str(Path(tmp)/'review.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text()); seed_database(db)
    app = create_app(dict(TESTING=True, DATABASE=database, SECRET_KEY='disposable-library'))
    server = make_server('127.0.0.1', 0, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    evidence = {'origin':origin, 'widths':[], 'errors':[]}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.on('pageerror', lambda e: evidence['errors'].append(str(e)))
        for width in [360,390,768,1440]:
            page.set_viewport_size({'width':width,'height':844 if width<800 else 1000})
            page.goto(origin+'/catalogue'); page.evaluate('document.fonts.ready')
            assert not page.locator('.library-filters').evaluate('(e)=>e.open')
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
            heading = page.locator('.card h3').first.bounding_box()
            assert heading['y']+heading['height'] < 774, heading
            assert page.locator('.library-art').count()>0
            page.screenshot(path=str(out/f'library-{width}.png'),full_page=True)
            evidence['widths'].append({'width':width,'first_result_heading_bottom':heading['y']+heading['height'],'overflow':False})
        page.set_viewport_size({'width':390,'height':844})
        summary = page.locator('.library-filters summary'); summary.focus(); page.keyboard.press('Enter')
        assert page.locator('.library-filters').evaluate('(e)=>e.open')
        page.get_by_label('Цель',exact=True).select_option('essentials')
        page.get_by_label('Уровень',exact=True).select_option('Начальный')
        page.get_by_label('Формат',exact=True).select_option('course')
        page.get_by_role('button',name='Применить фильтры').click()
        page.get_by_text('Фильтры · выбрано 3',exact=True).wait_for()
        filtered_url = page.url
        assert page.locator('.card').count()>0
        assert page.locator('.library-filters').evaluate('(e)=>e.open') is False
        page.locator('.card h3 a').first.click(); page.go_back()
        assert page.url == filtered_url
        assert page.get_by_label('Цель',exact=True).input_value() == 'essentials'
        page.get_by_label('Поиск',exact=True).fill('несуществующий-запрос-xyz')
        page.get_by_role('button',name='Найти',exact=True).click()
        page.get_by_role('heading',name='Ничего не найдено').wait_for()
        assert 'goal=essentials' in page.url and 'format=course' in page.url
        page.get_by_role('link',name='Сбросить всё',exact=True).click()
        assert page.url == origin+'/catalogue' and page.locator('.card').count()>0
        assert not evidence['errors']
        evidence.update(keyboard_disclosure=True,combined_filters=True,back_state=True,search_preserves_filters=True,empty_and_reset=True)
        browser.close()
    server.shutdown()
    (out/'browser.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    print(json.dumps(evidence))
