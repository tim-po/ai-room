import sqlite3

from test_learning import app, login, post, FREE


def put(client, path, data, csrf):
    return client.put(path, json=data, headers={'X-CSRF-Token': csrf})


COURSE = dict(title='Новый курс', description='Описание', outcome='Результат', tools='Браузер', prerequisites='Нет',
              author='Команда', goal='essentials', level='Начальный', status='draft')
LESSON = dict(title='Первый урок', objective='Цель', body='Текст урока', prompt='', task='', checklist='',
              access='free', status='draft', minutes=12, video='')


def test_admin_pages_and_api_respect_roles(app):
    anonymous = app.test_client()
    assert anonymous.get('/admin').status_code == 401
    assert anonymous.get('/api/admin/overview').status_code == 401
    learner = app.test_client(); login(learner)
    for path in ['/admin', '/admin/courses', '/api/admin/overview', '/api/admin/courses', '/api/admin/questions']:
        assert learner.get(path).status_code == 403, path
    editor = app.test_client(); login(editor, 'editor')
    page = editor.get('/admin')
    assert page.status_code == 200 and '/api/admin/overview' in page.text   # data embedded for the first render
    assert editor.get('/api/admin/courses').status_code == 200
    # Accounts and analytics are for administrators only.
    for path in ['/admin/learners', '/api/admin/learners', '/api/admin/analytics', '/admin/analytics']:
        assert editor.get(path).status_code == 403, path
    admin = app.test_client(); login(admin, 'admin')
    assert admin.get('/api/admin/learners').status_code == 200
    analytics = admin.get('/api/admin/analytics').json
    assert analytics['learners'] >= 1 and isinstance(analytics['loop']['features'], list)
    assert admin.get('/admin/workshop').location == '/admin' and admin.get('/admin/assistant').location == '/admin'   # the admin's own assistant is on the overview


def test_course_module_and_lesson_editing_with_revisions(app):
    editor = app.test_client(); csrf = login(editor, 'editor')
    assert post(editor, '/api/admin/courses', COURSE | dict(title=''), csrf).status_code == 400
    refused = post(editor, '/api/admin/courses', COURSE | dict(status='published'), csrf)
    assert refused.status_code == 400 and 'опубликованный урок' in refused.json['message']
    created = post(editor, '/api/admin/courses', COURSE, csrf)
    assert created.status_code == 201
    course = created.json
    identity = course['course']['id']
    course = post(editor, f'/api/admin/courses/{identity}/modules', {'title': 'Модуль 1'}, csrf).json
    module = course['modules'][0]['id']
    lesson = post(editor, f'/api/admin/modules/{module}/lessons', LESSON, csrf)
    assert lesson.status_code == 201
    lesson_id = lesson.json['lesson']['id']
    # A practice task needs success criteria.
    assert put(editor, f'/api/admin/lessons/{lesson_id}', LESSON | dict(task='Сделайте', revision=lesson.json['revision']), csrf).status_code == 400
    saved = put(editor, f'/api/admin/lessons/{lesson_id}', LESSON | dict(status='published', revision=lesson.json['revision']), csrf)
    assert saved.status_code == 200 and saved.json['lesson']['status'] == 'published'
    # The old revision is refused: someone else's save is never overwritten.
    assert put(editor, f'/api/admin/lessons/{lesson_id}', LESSON | dict(revision=lesson.json['revision']), csrf).status_code == 409
    published = put(editor, f'/api/admin/courses/{identity}', COURSE | dict(status='published', revision=course['revision']), csrf)
    assert published.status_code == 200 and published.json['course']['status'] == 'published'
    second = post(editor, f'/api/admin/modules/{module}/lessons', LESSON | dict(title='Второй'), csrf).json['lesson']['id']
    moved = post(editor, f'/api/admin/lessons/{second}/move', {'direction': 'up'}, csrf).json
    assert [l['title'] for l in moved['modules'][0]['lessons']] == ['Второй', 'Первый урок']
    # The learner catalogue sees the published course.
    learner = app.test_client(); login(learner)
    assert learner.get('/api/app/courses/' + identity).status_code == 200


def test_installed_content_is_editable_and_edits_survive_redeploys(app):
    from club.legacy_content import install

    def deploy(retire=False):
        with sqlite3.connect(app.config['DATABASE']) as db:
            db.row_factory = sqlite3.Row
            install(db, retire_synthetic=retire)

    deploy()
    editor = app.test_client(); csrf = login(editor, 'editor')
    installed = next(c for c in editor.get('/api/admin/courses').json['courses'] if c['source'] == 'files')
    detail = editor.get('/api/admin/courses/' + installed['id']).json
    original = detail['course']['title']
    changed = put(editor, '/api/admin/courses/' + installed['id'], detail['course'] | dict(title='Наш курс', revision=detail['revision']), csrf)
    assert changed.status_code == 200 and changed.json['source'] == 'edited'
    first = detail['modules'][0]
    lesson = editor.get('/api/admin/lessons/' + first['lessons'][0]['id']).json
    assert lesson['source'] == 'files'
    edited = put(editor, '/api/admin/lessons/' + lesson['lesson']['id'], lesson['lesson'] | dict(title='Наш урок', revision=lesson['revision']), csrf)
    assert edited.status_code == 200, edited.json
    assert edited.json['source'] == 'edited'
    renamed = put(editor, '/api/admin/modules/' + first['id'], {'title': 'Наш модуль'}, csrf)
    assert renamed.status_code == 200
    material = editor.get('/api/admin/library/claude-for-beginners').json
    put(editor, '/api/admin/library/claude-for-beginners', material['material'] | dict(status='draft', revision=material['revision']), csrf)
    # A deploy reinstalls the files but keeps everything edited in the admin.
    deploy(retire=True)
    after = editor.get('/api/admin/courses/' + installed['id']).json
    assert after['course']['title'] == 'Наш курс' and after['modules'][0]['title'] == 'Наш модуль'
    assert editor.get('/api/admin/lessons/' + lesson['lesson']['id']).json['lesson']['title'] == 'Наш урок'
    assert editor.get('/api/admin/library/claude-for-beginners').json['material']['status'] == 'draft'
    # «Вернуть версию из файлов» brings the repository version back, published.
    restored = post(editor, f"/api/admin/courses/{installed['id']}/restore", {}, csrf)
    assert restored.status_code == 200 and restored.json['source'] == 'files'
    assert restored.json['course']['title'] == original and restored.json['modules'][0]['title'] == first['title']
    assert editor.get('/api/admin/lessons/' + lesson['lesson']['id']).json['lesson']['title'] == 'Наш урок'   # the lesson keeps its own edit
    back = post(editor, '/api/admin/library/claude-for-beginners/restore', {}, csrf).json
    assert back['material']['status'] == 'published' and back['source'] == 'files'
    # Courses made in the admin are never archived by a deploy.
    mine = post(editor, '/api/admin/courses', COURSE, csrf).json['course']['id']
    module = post(editor, f'/api/admin/courses/{mine}/modules', {'title': 'М'}, csrf).json['modules'][0]['id']
    post(editor, f'/api/admin/modules/{module}/lessons', LESSON | dict(status='published'), csrf)
    detail = editor.get('/api/admin/courses/' + mine).json
    assert put(editor, '/api/admin/courses/' + mine, COURSE | dict(status='published', revision=detail['revision']), csrf).status_code == 200
    deploy(retire=True)
    assert editor.get('/api/admin/courses/' + mine).json['course']['status'] == 'published'
    assert post(editor, f'/api/admin/courses/{mine}/restore', {}, csrf).status_code == 404


def test_materials_learners_and_questions(app):
    learner = app.test_client(); learner_csrf = login(learner)
    learner.post('/help', data={'csrf': learner_csrf, 'body': 'Как начать?', 'lesson_id': FREE})
    editor = app.test_client(); csrf = login(editor, 'editor')
    material = post(editor, '/api/admin/library', dict(title='Гайд', description='О чём', outcome='Что получится', tools='Нет',
        prerequisites='Нет', author='Команда', body='Текст', prompt='', format='guide', goal='work', level='Начальный',
        access='free', status='published', minutes=5, video=''), csrf)
    assert material.status_code == 201
    assert any(i['id'] == material.json['material']['id'] for i in editor.get('/api/admin/library').json['items'])
    questions = editor.get('/api/admin/questions').json['questions']
    assert questions and questions[0]['user_name'] and questions[0]['status'] == 'open'
    admin = app.test_client(); admin_csrf = login(admin, 'admin')
    people = admin.get('/api/admin/learners?q=learner@').json['learners']
    assert [p['id'] for p in people] == ['user-learner']
    changed = put(admin, '/api/admin/learners/user-learner', {'entitlement': 'member'}, admin_csrf)
    assert changed.status_code == 200 and changed.json['learner']['entitlement'] == 'member'
    assert put(admin, '/api/admin/learners/user-admin', {'role': 'learner'}, admin_csrf).status_code == 409
    assert put(admin, '/api/admin/learners/user-learner', {'entitlement': 'gold'}, admin_csrf).status_code == 400
    assert put(editor, '/api/admin/learners/user-learner', {'entitlement': 'free'}, csrf).status_code == 403


def test_drafts_need_only_a_title_and_publishing_checks_the_rest(app):
    editor = app.test_client(); csrf = login(editor, 'editor')
    course = post(editor, '/api/admin/courses', {'title': 'Только название'}, csrf)
    assert course.status_code == 201
    created = course.json['course']
    assert created['status'] == 'draft' and created['author'] == 'Редактор' and created['level'] == 'Начальный'
    module = post(editor, f"/api/admin/courses/{created['id']}/modules", {'title': 'М'}, csrf).json['modules'][0]['id']
    lesson = post(editor, f'/api/admin/modules/{module}/lessons', {'title': 'Урок'}, csrf)
    assert lesson.status_code == 201 and lesson.json['lesson']['minutes'] == 1
    refused = put(editor, f"/api/admin/lessons/{lesson.json['lesson']['id']}", {'title': 'Урок', 'status': 'published', 'revision': lesson.json['revision']}, csrf)
    assert refused.status_code == 400 and 'цель урока, текст урока' in refused.json['message']
    words = ' '.join(['слово'] * 900)
    saved = put(editor, f"/api/admin/lessons/{lesson.json['lesson']['id']}", {'title': 'Урок', 'objective': 'Цель', 'body': words,
                'task': 'Сделайте', 'checklist': 'Готово', 'status': 'published', 'minutes': None, 'revision': lesson.json['revision']}, csrf)
    assert saved.status_code == 200 and saved.json['lesson']['minutes'] == 10   # 900 words ≈ 5 min reading + 5 practice
    material = post(editor, '/api/admin/library', {'title': 'Черновик гайда', 'format': 'use_case'}, csrf)
    assert material.status_code == 201 and material.json['material']['format'] == 'use_case'


def test_the_admin_shapes_the_skill_map(app):
    from club.legacy_content import install
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.row_factory = sqlite3.Row
        install(db)
    editor = app.test_client(); csrf = login(editor, 'editor')

    def tree():
        learner = app.test_client(); login(learner, 'member')
        return {c['id']: c | dict(topic=t['id']) for t in learner.get('/api/app/home').json['tree']['topics'] for c in t['courses']}

    # A course made in the admin appears under the topic of its goal, with the rank named here.
    course = post(editor, '/api/admin/courses', COURSE | dict(goal='build', rank='продаж с ИИ'), csrf).json
    identity = course['course']['id']
    assert course['map']['topic'] == 'coding' and course['map']['rank'] == 'продаж с ИИ'
    module = post(editor, f'/api/admin/courses/{identity}/modules', {'title': 'Письма'}, csrf).json['modules'][0]['id']
    post(editor, f'/api/admin/modules/{module}/lessons', LESSON | dict(status='published', title='Письмо'), csrf)
    detail = editor.get('/api/admin/courses/' + identity).json
    put(editor, '/api/admin/courses/' + identity, COURSE | dict(status='published', revision=detail['revision']), csrf)
    placed = tree()[identity]
    assert placed['topic'] == 'coding' and placed['rank_name'] == 'продаж с ИИ' and placed['modules'][0]['title'] == 'Письма'
    # Moved to another topic, then placed first in it and then after a chosen course.
    detail = editor.get('/api/admin/courses/' + identity).json
    put(editor, '/api/admin/courses/' + identity, {'map_topic': 'agents', 'revision': detail['revision']}, csrf)
    assert tree()[identity]['topic'] == 'agents'
    order = lambda: [c['id'] for c in sorted(tree().values(), key=lambda c: 0) if c['topic'] == 'agents']
    others = [c['id'] for c in editor.get('/api/admin/courses/' + identity).json['map']['order']['agents']]
    assert len(others) >= 2 and order()[-1] == identity
    detail = editor.get('/api/admin/courses/' + identity).json
    moved = put(editor, '/api/admin/courses/' + identity, {'map_topic': 'agents', 'map_after': '', 'revision': detail['revision']}, csrf).json
    assert order()[0] == identity and moved['map']['after'] == ''
    moved = put(editor, '/api/admin/courses/' + identity, {'map_after': others[0], 'revision': moved['revision']}, csrf).json
    assert order()[:2] == [others[0], identity] and moved['map']['after'] == others[0]
    detail = editor.get('/api/admin/courses/' + identity).json
    put(editor, '/api/admin/courses/' + identity, {'map_topic': 'hidden', 'revision': detail['revision']}, csrf)
    assert identity not in tree()
    # In an imported course: a renamed module and a lesson added in the admin show on the map,
    # and the catalogue's coming lessons keep their places.
    before = tree()['claude-basics']
    imported = editor.get('/api/admin/courses/claude-basics').json
    first = imported['modules'][0]
    put(editor, '/api/admin/modules/' + first['id'], {'title': 'Первые шаги с Claude'}, csrf)
    post(editor, f"/api/admin/modules/{first['id']}/lessons", LESSON | dict(status='published', title='Новый урок про Claude'), csrf)
    after = tree()['claude-basics']
    titles = [m['title'] for m in after['modules']]
    assert 'Первые шаги с Claude' in titles and 'Старт с Claude' not in titles
    renamed = after['modules'][titles.index('Первые шаги с Claude')]
    assert renamed['lessons'][-1]['title'] == 'Новый урок про Claude'
    assert sum(l['state'] == 'coming' for m in after['modules'] for l in m['lessons']) == \
        sum(l['state'] == 'coming' for m in before['modules'] for l in m['lessons'])
