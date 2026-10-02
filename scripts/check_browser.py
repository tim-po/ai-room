"""Local first-slice smoke; independent reviewer testing remains required."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

base = os.environ.get('CLUB_TEST_URL', 'http://127.0.0.1:8098')
out = Path(os.environ.get('CLUB_EVIDENCE_DIR', 'instance/evidence'))
out.mkdir(parents=True, exist_ok=True)
credential = Path('instance/reviewer-credentials.txt').read_text().split('Password: ',1)[1].splitlines()[0]
results = {'base':base,'viewports':[],'errors':[]}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width':1440,'height':1000}, reduced_motion='reduce')
    page = context.new_page()
    page.on('pageerror', lambda error: results['errors'].append(str(error)))
    page.goto(base+'/login')
    page.get_by_label('Почта', exact=True).fill('learner@example.test')
    page.get_by_label('Пароль', exact=True).fill(credential)
    page.get_by_role('button', name='Войти', exact=True).click()
    page.wait_for_url(base+'/')
    for width in [360,390,768,1440]:
        page.set_viewport_size({'width':width,'height':1000})
        for route in ['/', '/catalogue', '/courses/ai-foundations', '/lessons/foundations-start-01', '/profile']:
            page.goto(base+route)
            page.wait_for_load_state('domcontentloaded')
            overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth')
            results['viewports'].append({'width':width,'route':route,'overflow':overflow})
            assert not overflow, (width,route)
        page.goto(base+'/')
        page.screenshot(path=str(out/f'home-{width}.png'),full_page=True)
    page.goto(base+'/lessons/foundations-start-01')
    page.wait_for_function('document.querySelector("video").readyState >= 1')
    duration=page.locator('video').evaluate('(v)=>v.duration')
    assert duration>=19
    page.locator('video').evaluate('(v)=>{v.currentTime=6;return v.play()}')
    page.wait_for_timeout(1500)
    current=page.locator('video').evaluate('(v)=>{v.pause();return v.currentTime}')
    assert current>6
    page.wait_for_timeout(500)
    page.reload()
    page.wait_for_function('document.querySelector("video").currentTime > 6')
    results['video']={'duration':duration,'played_seconds':current,'resumed':True}
    text='Проверка браузером: задача, контекст, формат. Проверил факты отдельно.'
    page.get_by_label('Ваш результат или ссылка',exact=True).fill(text)
    with page.expect_navigation(wait_until='domcontentloaded'):
        page.get_by_role('button',name='Сохранить черновик',exact=True).click()
    page.wait_for_load_state('domcontentloaded')
    page.wait_for_function('document.querySelector("#practice-body").value.includes("Проверка браузером")')
    page.get_by_role('button',name='Отметить завершённым',exact=True).click()
    page.wait_for_load_state('domcontentloaded')
    assert page.get_by_role('button',name='Вернуть в работу',exact=True).is_visible()
    page.screenshot(path=str(out/'lesson-1440.png'),full_page=True)
    page.get_by_role('button',name='Вернуть в работу',exact=True).click()
    page.wait_for_load_state('domcontentloaded')
    assert page.get_by_role('button',name='Отметить завершённым',exact=True).is_visible()
    # Second browser, same identity; no shared browser storage.
    second=browser.new_context()
    check=second.new_page()
    check.goto(base+'/login')
    check.get_by_label('Почта',exact=True).fill('learner@example.test')
    check.get_by_label('Пароль',exact=True).fill(credential)
    check.get_by_role('button',name='Войти',exact=True).click()
    check.goto(base+'/lessons/foundations-start-01')
    assert check.get_by_label('Ваш результат или ссылка',exact=True).input_value()==text
    assert check.get_by_role('button',name='Отметить завершённым',exact=True).is_visible()
    results['practice_cross_context']=True
    results['completion_toggle']=True
    # No privileged account is used in screenshot evidence.
    assert results['errors']==[]
    browser.close()
(out/'browser-smoke.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps(results,ensure_ascii=False,indent=2))
