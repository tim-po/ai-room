"""Worker-owned integration regressions for authoring; independent review still required."""
import sqlite3
from pathlib import Path

from test_learning import app, login, post, FREE


def api(client, method, path, csrf=None, data=None):
    return client.open(path, method=method, json=data or {}, headers={'X-CSRF-Token': csrf} if csrf else {})


def save(client, kind, identity, csrf, **data):
    """An admin save with the current revision, as the editor sends it."""
    current = client.get(f'/api/admin/{kind}/{identity}').json
    return api(client, 'PUT', f'/api/admin/{kind}/{identity}', csrf, data | {'revision': current['revision']})


def course_data(**changes):
    return dict(title='Новый учебный курс', description='Самостоятельный маршрут', outcome='Первый проверенный результат', tools='Текстовый AI, бесплатный тариф', prerequisites='Без опыта', author='Редактор', goal='work', level='Начальный', status='draft') | changes


def lesson_data(**changes):
    return dict(title='Новый урок', objective='Получить полезный результат', body='Безопасный текст <script>alert(1)</script>', minutes='10', access='member', video='', prompt='Первый запрос', task='Сохраните текст', checklist='Проверьте факт', status='draft') | changes


def test_complete_authoring_lifecycle_preserves_work(app):
    editor = app.test_client()
    csrf = login(editor, 'editor')
    created = api(editor, 'POST', '/api/admin/courses', csrf, course_data())
    assert created.status_code == 201
    course_id = created.json['course']['id']
    assert api(editor, 'POST', f'/api/admin/courses/{course_id}/modules', csrf, {'title': 'Первый модуль'}).status_code == 200
    db = sqlite3.connect(app.config['DATABASE'])
    module_id = db.execute('SELECT id FROM modules WHERE course_id=?',(course_id,)).fetchone()[0]
    created = api(editor, 'POST', f'/api/admin/modules/{module_id}/lessons', csrf, lesson_data())
    assert created.status_code == 201
    lesson_id = created.json['lesson']['id']
    # The editor's preview renders like the learner page: escaped, and it never records progress.
    preview = api(editor, 'POST', '/api/admin/preview', csrf, {'body': lesson_data()['body'], 'body_format': created.json['lesson']['body_format']})
    assert '&lt;script&gt;' in preview.json['html'] and '<script>alert' not in preview.json['html']
    assert db.execute('SELECT COUNT(*) FROM progress WHERE lesson_id=?',(lesson_id,)).fetchone()[0] == 0
    learner = app.test_client()
    member_csrf = login(learner, 'member')
    assert learner.get('/lessons/'+lesson_id).status_code == 404
    assert api(learner, 'POST', '/api/admin/preview', member_csrf, {'body': 'x'}).status_code == 403
    assert learner.get(f'/api/admin/lessons/{lesson_id}').status_code == 403
    # Course publication requires a published lesson, and a published lesson in a draft course stays private.
    assert save(editor, 'courses', course_id, csrf, **course_data(status='published')).status_code == 400
    assert save(editor, 'lessons', lesson_id, csrf, **lesson_data(status='published')).status_code == 200
    assert learner.get('/lessons/'+lesson_id).status_code == 404
    assert save(editor, 'courses', course_id, csrf, **course_data(status='published')).status_code == 200
    assert learner.get('/lessons/'+lesson_id).status_code == 200
    assert post(learner, '/api/lessons/'+lesson_id+'/completion', {'completed':True}, member_csrf).status_code == 200
    assert post(learner, '/api/lessons/'+lesson_id+'/practice', {'body':'Сохранённая работа'}, member_csrf).status_code == 200
    # Real protected attachments, served as a download.
    assert api(editor, 'POST', f'/api/admin/lessons/{lesson_id}/resources', csrf, {'title':'Рабочий лист','kind':'text','content':'Закрытый материал'}).status_code == 200
    resource_id = db.execute('SELECT id FROM resources WHERE lesson_id=?',(lesson_id,)).fetchone()[0]
    assert learner.get('/resources/'+resource_id).text == 'Закрытый материал'
    anonymous = app.test_client()
    assert anonymous.get('/resources/'+resource_id).status_code == 403
    login(anonymous,'revoked')
    assert anonymous.get('/resources/'+resource_id).status_code == 403
    assert api(editor, 'POST', f'/api/admin/modules/{module_id}/lessons', csrf, lesson_data(title='Второй урок',status='published')).status_code == 201
    assert api(editor, 'POST', f'/api/admin/lessons/{lesson_id}/move', csrf, {'direction':'down'}).status_code == 200
    ids = [r[0] for r in db.execute('SELECT id FROM lessons WHERE module_id=? ORDER BY position,id',(module_id,))]
    assert ids[-1] == lesson_id
    assert db.execute('SELECT completed FROM progress WHERE lesson_id=?',(lesson_id,)).fetchone()[0] == 1
    assert save(editor, 'lessons', lesson_id, csrf, **lesson_data(status='archived')).status_code == 200
    assert learner.get('/resources/'+resource_id).status_code == 404
    assert save(editor, 'lessons', lesson_id, csrf, **lesson_data(status='published')).status_code == 200
    assert learner.get('/api/lessons/'+lesson_id+'/practice').json['body'] == 'Сохранённая работа'
    assert save(editor, 'courses', course_id, csrf, **course_data(status='draft')).status_code == 200
    assert learner.get('/api/lessons/'+lesson_id).status_code == 404
    assert save(editor, 'courses', course_id, csrf, **course_data(status='archived')).status_code == 200
    assert db.execute('SELECT completed FROM progress WHERE lesson_id=?',(lesson_id,)).fetchone()[0] == 1
    db.close()


def test_authoring_validation_csrf_roles_conflict(app):
    client = app.test_client()
    assert client.get('/api/admin/courses').status_code == 401
    csrf = login(client)
    assert api(client, 'POST', '/api/admin/courses', csrf, course_data()).status_code == 403
    csrf = login(client, 'admin')
    path = '/api/admin/lessons/'+FREE
    assert client.put(path, json=lesson_data()).status_code == 400   # no CSRF token
    assert save(client, 'lessons', FREE, csrf, **lesson_data(video='../session.key')).status_code == 400
    assert save(client, 'lessons', FREE, csrf, **lesson_data(minutes='0')).status_code == 400
    assert save(client, 'lessons', FREE, csrf, **lesson_data(task='Практика', checklist='')).status_code == 400
    revision = client.get(path).json['revision']
    assert save(client, 'lessons', FREE, csrf, **lesson_data(title='Новая редакция', status='published', access='free')).status_code == 200
    assert api(client, 'PUT', path, csrf, lesson_data() | {'revision': revision}).status_code == 409
    for url in ['javascript:alert(1)', 'https://user:password@example.com', '//example.com', 'https://example.com/ bad']:
        assert api(client, 'POST', path+'/resources', csrf, {'title':'Источник','kind':'link','content':url}).status_code == 400
    assert api(client, 'POST', path+'/resources', csrf, {'title':'Источник','kind':'link','content':'https://example.com/guide'}).status_code == 200
    db = sqlite3.connect(app.config['DATABASE'])
    resource = db.execute('SELECT id FROM resources').fetchone()[0]
    assert client.get('/resources/'+resource).location == 'https://example.com/guide'
    assert api(client, 'POST', f'/api/admin/resources/{resource}/archive', csrf).status_code == 200
    assert client.get('/resources/'+resource).status_code == 404
    db.close()


def test_schema_upgrade_is_additive_and_repeatable(app):
    db = sqlite3.connect(app.config['DATABASE'])
    db.execute('DROP TABLE resources')
    db.execute('PRAGMA user_version=1')
    db.execute("INSERT INTO progress(user_id,lesson_id,completed) VALUES('user-learner',?,1)",(FREE,))
    db.commit()
    before = db.execute('SELECT * FROM lessons ORDER BY id').fetchall()
    runner = app.test_cli_runner()
    assert runner.invoke(args=['init-db']).exit_code == 0
    assert runner.invoke(args=['init-db']).exit_code == 0
    assert db.execute('PRAGMA user_version').fetchone()[0] == 6
    assert db.execute('SELECT * FROM lessons ORDER BY id').fetchall() == before
    assert db.execute('SELECT completed FROM progress').fetchone()[0] == 1
    db.close()
