"""Read-only report rendering against the local independent staging database."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

base = os.environ.get('CLUB_TEST_URL', 'http://127.0.0.1:8098')
out = Path(os.environ.get('CLUB_EVIDENCE_DIR', 'instance/measurement-evidence'))
out.mkdir(parents=True, exist_ok=True)
credential = Path('instance/reviewer-credentials.txt').read_text().split('Password: ',1)[1].splitlines()[0]
result = {'base':base,'errors':[], 'viewports':[]}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440,'height':1000}, reduced_motion='reduce')
    page.on('pageerror', lambda error: result['errors'].append(str(error)))
    page.goto(base+'/login')
    page.get_by_label('Почта',exact=True).fill('admin@example.test')
    page.get_by_label('Пароль',exact=True).fill(credential)
    page.get_by_role('button',name='Войти',exact=True).click()
    page.wait_for_url(base+'/')
    page.goto(base+'/admin')
    page.get_by_role('link',name='Активность и учебные результаты').click()
    page.get_by_role('heading',name='Активность обучения',exact=True).wait_for()
    for width in [360,390,768,1440]:
        page.set_viewport_size({'width':width,'height':1000})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
        page.screenshot(path=str(out/f'measurement-{width}.png'),full_page=True)
        result['viewports'].append({'width':width,'no_overflow':True})
    page.keyboard.press('Control+Home')
    page.keyboard.press('Tab')
    assert page.evaluate("document.activeElement.tagName") == 'A'
    result['keyboard_focus'] = True
    assert not result['errors']
    browser.close()
(out/'browser.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))
