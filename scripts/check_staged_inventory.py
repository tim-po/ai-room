"""Inspect a pinned staging build without publishing or submitting learner work."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', required=True)
parser.add_argument('--expected-build', required=True)
parser.add_argument('--credentials', type=Path, required=True)
parser.add_argument('--manifest', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
password = args.credentials.read_text().split('Password: ', 1)[1].splitlines()[0]
manifest = json.loads(args.manifest.read_text())
result = dict(url=args.url, expected_build=args.expected_build, pages=[], nodes=[], errors=[], self_verification=True)
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(reduced_motion='reduce')
    page = context.new_page()
    page.on('pageerror', lambda error: result['errors'].append(str(error)))
    def health():
        response = context.request.get(args.url+'/health')
        assert response.status == 200
        value = response.json()
        assert args.expected_build in value.values(), value
        return value
    result['before'] = health()
    for role in ['learner', 'editor']:
        page.goto(args.url+'/login')
        page.get_by_label('Почта', exact=True).fill(role+'@example.test')
        page.get_by_label('Пароль', exact=True).fill(password)
        page.get_by_role('button', name='Войти', exact=True).click()
        page.wait_for_url(args.url+'/')
        routes = ['/', '/profile', '/catalogue'] if role == 'learner' else ['/admin', '/admin/assessments', '/admin/practice']
        for width in [390, 1440]:
            page.set_viewport_size(dict(width=width, height=1000))
            for route in routes:
                response = page.goto(args.url+route)
                assert response.status == 200, (role, route, response.status)
                page.locator('h1').wait_for()
                page.wait_for_load_state('networkidle')
                if route == '/admin/assessments':
                    assert 'Доступных проверок пока нет.' in page.locator('#forms-body').inner_text()
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'), (role,route,width)
                page.keyboard.press('Tab')
                result['pages'].append(dict(role=role, route=route, width=width, status=response.status))
                page.screenshot(path=str(args.output/(role+'-'+route.strip('/').replace('/','-')+f'-{width}.png')), full_page=True)
        if role == 'learner':
            for node in sorted({c['node_id'] for c in manifest['candidates']}):
                response = context.request.get(args.url+'/api/skills/nodes/'+node)
                assert response.status == 200
                data = response.json()
                assert data['assessments'] == [], node
                result['nodes'].append(dict(node=node, assessments=0, content=len(data['content'])))
            for candidate in manifest['candidates']:
                response = page.goto(args.url+candidate['lesson_url'])
                assert response.status == 200, candidate['lesson_id']
                assert 'Источник · абзац 1' in page.locator('body').inner_text()
                result['pages'].append(dict(role=role, route=candidate['lesson_url'], status=200))
        context.clear_cookies()
    result['after'] = health()
    assert not result['errors']
    browser.close()
(args.output/'staged-browser.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(dict(pages=len(result['pages']), nodes=len(result['nodes']), errors=result['errors'], build=args.expected_build)))
