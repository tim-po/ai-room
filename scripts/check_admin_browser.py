"""Admin app checks against an isolated real HTTP application: every screen in both glass themes at
desktop and phone widths (no script errors, no horizontal scroll, every control named), the main
editing flows, and full-page screenshots plus a form-field census for review.

    CLUB_EVIDENCE_DIR=<private-output-directory> .venv/bin/python scripts/check_admin_browser.py
"""
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from club import create_app
from club.legacy_content import install
from club.seed import seed_database
from club.support_admin import SCHEMA as SUPPORT_SCHEMA
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

out = Path(os.environ.get('CLUB_EVIDENCE_DIR', 'instance/admin-evidence'))
out.mkdir(parents=True, exist_ok=True)
WIDTHS = [1440, 390]
THEMES = ['dusk', 'dawn']

# Counts what a person has to look at on a screen: text inputs, text areas, dropdowns and choice groups.
CENSUS = """() => {
  const visible = el => el.checkVisibility({visibilityProperty: true}) && !el.closest('details:not([open]) > :not(summary)');
  const main = document.querySelector('.adm-main');
  if (!main) return null;
  const fields = [...main.querySelectorAll('input:not([type=hidden]):not([type=search]),textarea,.select > button,[role=radiogroup]')].filter(visible);
  const unnamed = [...main.querySelectorAll('input:not([type=hidden]),textarea,button,a[href]')].filter(visible).filter(el => {
    const name = (el.getAttribute('aria-label') || el.labels?.[0]?.textContent || el.textContent || el.getAttribute('title') || el.getAttribute('placeholder') || '').trim();
    return !name;
  }).map(el => el.outerHTML.slice(0, 120));
  return {fields: fields.length, unnamed, overflow: document.documentElement.scrollWidth > innerWidth + 1};
}"""

with tempfile.TemporaryDirectory(prefix='club-admin-') as folder:
    password = secrets.token_urlsafe(24)
    os.environ['CLUB_SEED_PASSWORD'] = password
    database = str(Path(folder) / 'test.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text())
        seed_database(db)
        db.executescript(SUPPORT_SCHEMA)   # what `flask init-support` adds on a real installation
        db.row_factory = sqlite3.Row
        install(db)
    app = create_app({'DATABASE': database, 'SECRET_KEY': secrets.token_hex(32)})
    # Some learner activity so the overview, feed, questions and learner page have something to show.
    learner = app.test_client()
    learner.get('/login')
    with learner.session_transaction() as session:
        token = session['csrf']
    learner.post('/login', data={'email': 'learner@example.test', 'password': password, 'csrf': token})
    with learner.session_transaction() as session:
        token = session['csrf']
    headers = {'X-CSRF-Token': token}
    lesson = 'foundations-start-01'
    learner.get('/lessons/' + lesson)
    learner.post(f'/api/lessons/{lesson}/practice', json={'body': 'Мой результат', 'status': 'submitted'}, headers=headers)
    learner.post(f'/api/lessons/{lesson}/completion', json={'completed': True}, headers=headers)
    learner.post('/help', data={'csrf': token, 'body': 'Не понимаю, как сохранить промпт в Claude. Подскажете?', 'lesson_id': lesson})

    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    results = {'screens': [], 'flows': {}, 'errors': [], 'failed_requests': []}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
            context = browser.new_context(viewport={'width': 1440, 'height': 900}, reduced_motion='reduce',
                                          permissions=['clipboard-read', 'clipboard-write'])
            page = context.new_page()
            page.on('pageerror', lambda err: results['errors'].append(f'{page.url}: {err}'))
            page.on('response', lambda r: r.status >= 500 and results['failed_requests'].append(f'{r.status} {r.url}'))
            page.goto(base + '/login?next=/admin')
            page.get_by_label('Почта', exact=True).fill('admin@example.test')
            page.get_by_label('Пароль', exact=True).fill(password)
            page.get_by_role('button', name='Войти', exact=True).click()
            page.wait_for_url(base + '/admin')

            course = 'claude-basics'
            first_lesson = page.evaluate(f"fetch('/api/admin/courses/{course}').then(r => r.json()).then(d => d.modules[0].lessons[0].id)")
            screens = {
                'overview': '/admin', 'courses': '/admin/courses', 'course-installed': f'/admin/courses/{course}',
                'course-new': '/admin/courses/new', 'lesson-new': '/admin/lessons/new?module=claude-basics-m1', 'lesson-installed': f'/admin/lessons/{first_lesson}',
                'library': '/admin/library', 'material-new': '/admin/library/new', 'material-installed': '/admin/library/claude-for-beginners',
                'learners': '/admin/learners', 'learner': '/admin/learners/user-learner', 'questions': '/admin/questions', 'works': '/admin/works',
                'analytics': '/admin/analytics',
            }
            for theme in THEMES:
                page.evaluate(f"localStorage.setItem('airoom-theme', '{theme}')")
                for width in WIDTHS:
                    page.set_viewport_size({'width': width, 'height': 900})
                    for name, path in screens.items():
                        page.goto(base + path)
                        page.locator('.adm-main h1').first.wait_for()
                        census = page.evaluate(CENSUS)
                        assert census, name
                        page.screenshot(path=str(out / f'{name}-{theme}-{width}.png'), full_page=True)
                        results['screens'].append(dict(screen=name, theme=theme, width=width, **census))

            # Flow: a course needs only a name to start; a lesson is written and published; then the course.
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(base + '/admin/courses/new')
            page.get_by_label('Название', exact=True).fill('Промпты для отдела продаж')
            page.get_by_role('button', name='Создать курс').click()
            page.wait_for_url(lambda url: '/admin/courses/course-' in url)
            course_url = page.url
            page.get_by_label('Название нового модуля').fill('Первые письма')
            page.get_by_role('button', name='Добавить модуль').click()
            page.get_by_role('link', name='+ Урок').click()
            page.wait_for_url(lambda url: '/admin/lessons/new' in url)
            page.get_by_label('Название', exact=True).fill('Письмо после звонка')
            page.get_by_role('button', name='Создать урок').click()
            page.wait_for_url(lambda url: '/admin/lessons/lesson-' in url)
            assert page.get_by_role('button', name='Опубликовать').is_disabled()
            page.get_by_label('Цель урока', exact=True).fill('Написать письмо клиенту за пять минут')
            page.get_by_label('Текст урока', exact=True).fill('После звонка клиент ждёт письмо.\n\nПопросите Claude собрать его из заметок.')
            page.get_by_role('button', name='Опубликовать').click()
            page.get_by_text('Опубликован — ученики видят эту версию').wait_for()
            page.screenshot(path=str(out / 'flow-lesson-published.png'), full_page=True)
            page.goto(course_url)
            page.get_by_label('Описание', exact=True).fill('Письма и ответы клиентам с Claude.')
            page.get_by_label('Что получится', exact=True).fill('Шаблон письма, который работает.')
            page.get_by_role('button', name='Опубликовать').click()
            page.get_by_text('Опубликован — ученики видят эту версию').wait_for()
            page.screenshot(path=str(out / 'flow-course-published.png'), full_page=True)
            results['flows']['course_and_lesson_published'] = True

            # Flow: answer the learner's question.
            page.goto(base + '/admin/questions')
            page.get_by_label('Ответ ученику').first.fill('Нажмите «Скопировать» под промптом и вставьте его в Claude.')
            page.get_by_role('button', name='Ответить').first.click()
            page.locator('.adm-answer').first.wait_for()
            results['flows']['question_answered'] = True

            # Flow: feedback on the learner's practice result.
            page.goto(base + '/admin/works')
            page.get_by_label('Отзыв ученику').first.fill('Хорошо получилось. Добавьте пример письма.')
            page.get_by_role('button', name='Отправить отзыв').first.click()
            page.locator('.adm-answer').first.wait_for()
            results['flows']['work_reviewed'] = True

            # Flow: the admin copies a message with a one-time link; an assistant follows it with plain curl and a
            # cookie file, the way the message says, and works without ever seeing a key.
            page.goto(base + '/admin')
            page.get_by_role('button', name='Скопировать ссылку для ассистента').click()
            page.locator('.adm-assist-pop textarea').wait_for()
            message = page.locator('.adm-assist-pop textarea').input_value()
            page.screenshot(path=str(out / 'flow-assist-link.png'))
            link = re.search(r"'(http[^']+/attach/al_[^']+)'", message)[1]
            jar = str(Path(folder) / 'airoom-cookies.txt')
            curl = lambda *args: subprocess.run(['curl', '-sS', '-c', jar, '-b', jar, *args], capture_output=True, text=True, check=True).stdout
            briefing = curl(link)
            assert '/api/admin/tools' in briefing and 'as_' not in briefing, briefing[:300]
            overview = json.loads(curl('-X', 'POST', '-H', 'Content-Type: application/json', '-d', '{}', base + '/api/admin/tools/overview'))
            found = json.loads(curl('-X', 'POST', '-H', 'Content-Type: application/json', '-d', '{"text": "Claude"}', base + '/api/admin/tools/search'))
            assert overview['courses'] and found, (overview, found)
            page.goto(base + '/admin')
            page.locator('.adm-sessions li').first.wait_for()
            results['flows']['assistant_link'] = dict(courses=len(overview['courses']), found=len(found))

            # The learner's view of the text, inside the editor; the rarer actions sit in «⋯»; old admin addresses land here.
            page.goto(base + f'/admin/lessons/{first_lesson}')
            page.get_by_role('tab', name='Как увидит ученик').click()
            page.locator('.adm-body-preview .lesson-rich').wait_for()
            results['flows']['preview_tab'] = True
            page.get_by_role('button', name='Ещё действия').click()
            items = [i.replace('\n↗', '').strip() for i in page.get_by_role('menuitem').all_inner_texts()]
            assert 'Открыть как ученик' in items and 'Снять с публикации' in items and 'В архив' in items, items
            page.screenshot(path=str(out / 'flow-menu.png'))
            page.keyboard.press('Escape')
            assert page.get_by_role('menu').count() == 0
            results['flows']['menu'] = items
            for old, new in [('/admin/content/', '/admin/courses'), ('/admin/materials', '/admin/library'), ('/admin/workshop', '/admin'),
                             ('/admin/assistant', '/admin'), ('/admin/measurement', '/admin/analytics'), ('/admin/tree', '/admin/works')]:
                page.goto(base + old)
                page.wait_for_url(base + new)
            results['flows']['old_addresses_redirect'] = True

            # Flow: give the learner a membership.
            page.goto(base + '/admin/learners/user-learner')
            page.locator('.adm-main .select > button').first.click()
            page.get_by_role('option', name='Участник клуба').click()
            page.wait_for_function("() => document.querySelector('.adm-main .select > button')?.innerText.includes('Участник клуба')")
            results['flows']['membership_granted'] = True

            # Flow: imported content is edited here; «⋯» then offers the file version back, which restores it.
            page.on('dialog', lambda dialog: dialog.accept())
            page.goto(base + f'/admin/courses/{course}')
            original = page.get_by_label('Название', exact=True).input_value()
            page.get_by_label('Название', exact=True).fill('Claude для нашей команды')
            page.get_by_role('button', name='Сохранить').click()
            page.get_by_text('Опубликован — ученики видят эту версию').wait_for()
            page.screenshot(path=str(out / 'flow-installed-edited.png'), full_page=True)
            page.get_by_role('button', name='Ещё действия').click()
            page.get_by_role('menuitem', name='Вернуть версию из файлов').click()
            page.wait_for_function(f"() => document.querySelector('.adm-title textarea')?.value === {json.dumps(original)}")
            results['flows']['installed_edited_and_restored'] = True

            # An editor sees content and questions, not accounts or analytics.
            editor = browser.new_context(viewport={'width': 1440, 'height': 900}).new_page()
            editor.goto(base + '/login?next=/admin')
            editor.get_by_label('Почта', exact=True).fill('editor@example.test')
            editor.get_by_label('Пароль', exact=True).fill(password)
            editor.get_by_role('button', name='Войти', exact=True).click()
            editor.wait_for_url(base + '/admin')
            nav = editor.locator('.adm-side nav').inner_text()
            results['flows']['editor_nav'] = nav.split('\n')
            assert 'Ученики' not in nav and 'Аналитика' not in nav
            browser.close()
    finally:
        server.shutdown()
    (out / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
    problems = [s for s in results['screens'] if s['overflow'] or s['unnamed']]
    print(json.dumps(dict(errors=results['errors'], failed=results['failed_requests'], flows=results['flows'], problems=problems,
                          fields={s['screen']: s['fields'] for s in results['screens'] if s['width'] == 1440 and s['theme'] == 'dusk'}),
                     ensure_ascii=False, indent=1))
