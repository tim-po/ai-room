"""Authoring browser verification against the independent local staging instance."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

base = os.environ.get('CLUB_TEST_URL', 'http://127.0.0.1:8098')
out = Path(os.environ.get('CLUB_EVIDENCE_DIR', 'instance/authoring-evidence'))
out.mkdir(parents=True, exist_ok=True)
credential = Path('instance/reviewer-credentials.txt').read_text().split('Password: ',1)[1].splitlines()[0]
result = {'base':base,'errors':[], 'viewports':[]}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    page = context.new_page()
    page.on('pageerror', lambda error: result['errors'].append(str(error)))
    page.goto(base+'/login')
    page.get_by_label('Почта',exact=True).fill('editor@example.test')
    page.get_by_label('Пароль',exact=True).fill(credential)
    page.get_by_role('button',name='Войти',exact=True).click()
    page.wait_for_url(base+'/')
    page.goto(base+'/admin/content/courses/new')
    for label, value in [('Название','Браузерная проверка редактора'),('Краткое описание','Независимый тестовый курс'),('Что получится у ученика','Проверенный результат'),('Что нужно знать до старта','Опыт не нужен'),('Инструменты и возможные расходы','Любой текстовый AI, бесплатно'),('Автор / ответственный за актуальность','Учебный редактор')]:
        page.get_by_label(label, exact=True).fill(value)
    # Server validation is visible and typed text remains available.
    page.locator('select[name=status]').select_option('published')
    page.get_by_role('button',name='Сохранить курс',exact=True).click()
    page.wait_for_function("() => document.querySelector('[data-save-status]').textContent.includes('Перед публикацией')")
    assert page.get_by_label('Название',exact=True).input_value() == 'Браузерная проверка редактора'
    result['validation_preserves_input'] = True
    page.locator('select[name=status]').select_option('draft')
    page.get_by_role('button',name='Сохранить курс',exact=True).click()
    page.wait_for_url('**/admin/content/courses/course-*')
    course_url = page.url
    page.get_by_label('Название нового модуля',exact=True).fill('Первый шаг')
    page.get_by_role('button',name='Добавить модуль',exact=True).click()
    page.get_by_role('link',name='Добавить урок',exact=True).click()
    page.get_by_label('Название урока',exact=True).fill('Проверка текста, видео и практики')
    page.get_by_label('Цель урока',exact=True).fill('Сохранить свой первый результат')
    page.get_by_label('Текст урока / расшифровка видео',exact=True).fill('Синтетический учебный текст. Видео — тестовый пример без звука.')
    page.locator('select[name=video]').select_option('fixture.webm')
    page.get_by_label('Практика: цель и инструкция (необязательно)',exact=True).fill('Опишите результат.')
    page.get_by_label('Критерии успеха — по одному на строку',exact=True).fill('Проверены факты\nУказано ограничение')
    page.get_by_role('button',name='Сохранить урок',exact=True).click()
    page.wait_for_url('**/admin/content/lessons/lesson-*')
    lesson_url=page.url
    # Offline save keeps input and provides an actionable retry state.
    page.get_by_label('Название урока',exact=True).fill('Проверка сохранения после сбоя сети')
    context.set_offline(True)
    page.get_by_role('button',name='Сохранить урок',exact=True).click()
    page.wait_for_function("() => document.querySelector('[data-save-status]').textContent.includes('Нет связи')")
    assert page.get_by_label('Название урока',exact=True).input_value() == 'Проверка сохранения после сбоя сети'
    context.set_offline(False)
    page.get_by_role('button',name='Сохранить урок',exact=True).click()
    page.wait_for_load_state('networkidle')
    result['offline_retry'] = True
    page.get_by_label('Название материала',exact=True).fill('Рабочий лист')
    page.get_by_label('Содержимое файла или HTTPS-ссылка',exact=True).fill('Проверочный файл урока')
    page.get_by_role('button',name='Добавить материал',exact=True).click()
    page.get_by_role('link',name='Предпросмотр ученика',exact=True).click()
    page.wait_for_function('() => document.querySelector("video").readyState >= 1')
    page.locator('video').evaluate('(v)=>v.play()')
    page.wait_for_timeout(350)
    assert page.locator('video').evaluate('(v)=>v.currentTime') > 0
    page.locator('video').evaluate('(v)=>v.pause()')
    assert not page.locator('form[action$="/completion"]').count()
    with page.expect_download() as download:
        page.get_by_role('link',name='Рабочий лист TXT · скачать').click()
    assert Path(download.value.path()).read_text() == 'Проверочный файл урока'
    result['preview_media_and_download'] = True
    for width in [360,390,768,1440]:
        page.set_viewport_size({'width':width,'height':1000})
        for name,url in [('course',course_url),('lesson',lesson_url),('preview',lesson_url+'/preview')]:
            page.goto(url)
            overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth')
            assert not overflow, (width,name)
            result['viewports'].append({'width':width,'page':name,'overflow':overflow})
            if width in (390,1440):
                page.screenshot(path=str(out/f'authoring-{name}-{width}.png'),full_page=True)
    # Keep browser fixture archived; no public catalogue pollution.
    page.goto(course_url)
    page.locator('select[name=status]').select_option('archived')
    page.get_by_role('button',name='Сохранить курс',exact=True).click()
    page.wait_for_load_state('networkidle')
    assert page.locator('select[name=status]').input_value() == 'archived'
    result['fixture_archived'] = True
    assert result['errors'] == []
    browser.close()
(out/'authoring-browser.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
