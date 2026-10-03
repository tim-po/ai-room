"""Public exact-build navigation checks; no authentication or content mutation."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--expected-build', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    origin = args.url.rstrip('/')
    args.output.mkdir(parents=True, exist_ok=True)
    result = dict(origin=origin, expected_build=args.expected_build, self_verification=True,
                  authenticated=False, widths=[], errors=[], checks=[])
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(reduced_motion='reduce')
        page = context.new_page()
        page.on('pageerror', lambda e: result['errors'].append(str(e)))

        def health():
            response = context.request.get(origin+'/health')
            require(response.status == 200, 'Health unavailable')
            data = response.json()
            require(args.expected_build in data.values(), 'Staged build changed')
            return data

        try:
            result['before'] = health()
            for width in [360, 390, 768, 1440]:
                page.set_viewport_size(dict(width=width, height=1000 if width > 800 else 844))
                page.goto(origin+'/')
                coding = page.locator('#skill-map [data-node=coding]')
                coding.wait_for()
                coding.focus()
                page.keyboard.press('ArrowRight')
                require(page.evaluate('document.activeElement.dataset.node') != 'coding', 'Arrow navigation failed')
                coding.focus()
                page.keyboard.press('Enter')
                page.locator('#node-detail .evidence-label').wait_for()
                mobile = page.locator('#skill-map [data-node="coding.mobile"]')
                mobile.focus()
                page.keyboard.press('Enter')
                page.locator('#node-detail .evidence-label').wait_for()
                require('node=coding.mobile' in page.url, 'Selection URL missing')
                page.keyboard.press('Escape')
                require(page.evaluate('document.activeElement.dataset.node') == 'coding.mobile', 'Focus not restored')
                page.locator('#map-reset').click()
                page.locator('#list-view').click()
                require(page.locator('#skill-map ul ul').count() > 5, 'Recursive list missing')
                page.locator('#skill-search').fill('несуществующий навык')
                require(page.locator('#atlas-status').inner_text() == 'Найдено навыков: 0', 'Search empty state missing')
                page.locator('#map-reset').click()
                page.locator('#map-view').click()
                page.goto(origin+'/?node=basic-ai.verification')
                page.locator('#node-detail a[href^="/lessons/"]').first.click()
                page.locator('#ability-return:not([hidden])').wait_for()
                require('node=basic-ai.verification' in page.url, 'Lesson lost node context')
                page.locator('#ability-return').click()
                page.locator('#node-detail .evidence-label').wait_for()
                require('node=basic-ai.verification' in page.url, 'Return lost node context')
                require(not page.evaluate('document.documentElement.scrollWidth>innerWidth'), 'Map overflow')
                page.screenshot(path=str(args.output/f'node-return-{width}.png'), full_page=True)
                page.goto(origin+'/catalogue')
                require(not page.locator('.library-filters').evaluate('(e)=>e.open'), 'Filters start expanded')
                page.locator('.library-filters summary').focus()
                page.keyboard.press('Enter')
                page.get_by_label('Цель', exact=True).select_option('essentials')
                page.get_by_label('Уровень', exact=True).select_option('Начальный')
                page.get_by_label('Формат', exact=True).select_option('course')
                page.get_by_role('button', name='Применить фильтры').click()
                page.get_by_text('Фильтры · выбрано 3', exact=True).wait_for()
                filtered = page.url
                page.locator('.card h3 a').first.click()
                page.go_back()
                require(page.url == filtered, 'Back lost filter URL')
                require(page.get_by_label('Цель', exact=True).input_value() == 'essentials', 'Back lost filter selection')
                page.get_by_label('Поиск', exact=True).fill('несуществующий-запрос-xyz')
                page.get_by_role('button', name='Найти', exact=True).click()
                page.get_by_role('heading', name='Ничего не найдено').wait_for()
                require('goal=essentials' in page.url and 'format=course' in page.url, 'Search lost filters')
                page.get_by_role('link', name='Сбросить всё', exact=True).click()
                require(page.url == origin+'/catalogue' and page.locator('.card').count() > 0, 'Reset failed')
                require(not page.evaluate('document.documentElement.scrollWidth>innerWidth'), 'Catalogue overflow')
                page.screenshot(path=str(args.output/f'catalogue-reset-{width}.png'), full_page=True)
                result['widths'].append(width)
            result['checks'] = ['map arrow and Enter navigation', 'Escape restores node focus', 'recursive list',
                                'empty skill search', 'lesson node context and return', 'keyboard filter disclosure',
                                'three combined filters', 'course back retains filters', 'empty search retains filters', 'reset']
            require(not result['errors'], 'Browser JavaScript errors')
            result['passed'] = True
        except Exception as error:
            result['passed'] = False
            result['failure'] = str(error)
            page.screenshot(path=str(args.output/'failure.png'), full_page=True)
            raise
        finally:
            try:
                result['after'] = health()
            finally:
                (args.output/'navigation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
                browser.close()
    print(json.dumps(dict(passed=result['passed'], widths=result['widths'], build=args.expected_build)))


if __name__ == '__main__':
    main()
