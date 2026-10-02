"""Worker-owned integration regressions for authoring; independent review still required."""
import re
import sqlite3
from pathlib import Path

from test_learning import app, login, post, FREE


def form(client, path, csrf, **values):
    page = client.get(path)
    assert page.status_code == 200
    revision = re.search(r'name="revision" value="([^"]*)"', page.text)
    return client.post(path, data={'csrf':csrf, 'revision':revision[1] if revision else '', **values})


def course_data(**changes):
    return dict(title='Новый учебный курс', description='Самостоятельный маршрут', outcome='Первый проверенный результат', tools='Текстовый AI, бесплатный тариф', prerequisites='Без опыта', author='Редактор', goal='work', level='Начальный', status='draft') | changes


def lesson_data(**changes):
    return dict(title='Новый урок', objective='Получить полезный результат', body='Безопасный текст <script>alert(1)</script>', minutes='10', access='member', video='', prompt='Первый запрос', task='Сохраните текст', checklist='Проверьте факт', status='draft') | changes


def test_complete_authoring_lifecycle_preserves_work(app):
    editor = app.test_client()
    csrf = login(editor, 'editor')
    response = form(editor, '/admin/content/courses/new', csrf, **course_data())
    assert response.status_code == 302
    course_path = response.location
    course_id = course_path.rsplit('/', 1)[1]
    assert editor.post(course_path+'/modules', data={'csrf':csrf,'title':'Первый модуль'}).status_code == 302
    db = sqlite3.connect(app.config['DATABASE'])
    module_id = db.execute('SELECT id FROM modules WHERE course_id=?',(course_id,)).fetchone()[0]
    response = form(editor, '/admin/content/modules/'+module_id+'/lessons/new', csrf, **lesson_data())
    assert response.status_code == 302
    lesson_path = response.location
    lesson_id = lesson_path.rsplit('/',1)[1]
    preview = editor.get(lesson_path+'/preview')
    assert preview.status_code == 200
    assert '&lt;script&gt;' in preview.text and '<script>alert' not in preview.text
    assert '/completion' not in preview.text and '/practice"' not in preview.text
    assert db.execute('SELECT COUNT(*) FROM progress WHERE lesson_id=?',(lesson_id,)).fetchone()[0] == 0
    learner = app.test_client()
    member_csrf = login(learner, 'member')
    assert learner.get('/lessons/'+lesson_id).status_code == 404
    assert learner.get(lesson_path+'/preview').status_code == 403
    # Course publication requires a published lesson, and a published lesson in a draft course stays private.
    assert form(editor, course_path, csrf, **course_data(status='published')).status_code == 400
    assert form(editor, lesson_path, csrf, **lesson_data(status='published')).status_code == 302
    assert learner.get('/lessons/'+lesson_id).status_code == 404
    assert form(editor, course_path, csrf, **course_data(status='published')).status_code == 302
    assert learner.get('/lessons/'+lesson_id).status_code == 200
    assert post(learner, '/api/lessons/'+lesson_id+'/completion', {'completed':True}, member_csrf).status_code == 200
    assert post(learner, '/api/lessons/'+lesson_id+'/practice', {'body':'Сохранённая работа'}, member_csrf).status_code == 200
    # Real protected attachments; resource text is escaped in authoring and served as a download.
    assert editor.post(lesson_path+'/resources',data={'csrf':csrf,'title':'Рабочий лист','kind':'text','content':'Закрытый материал'}).status_code == 302
    resource_id = db.execute('SELECT id FROM resources WHERE lesson_id=?',(lesson_id,)).fetchone()[0]
    assert learner.get('/resources/'+resource_id).text == 'Закрытый материал'
    anonymous = app.test_client()
    assert anonymous.get('/resources/'+resource_id).status_code == 403
    login(anonymous,'revoked')
    assert anonymous.get('/resources/'+resource_id).status_code == 403
    assert form(editor, '/admin/content/modules/'+module_id+'/lessons/new', csrf, **lesson_data(title='Второй урок',status='published')).status_code == 302
    assert editor.post(lesson_path+'/move',data={'csrf':csrf,'direction':'down'}).status_code == 302
    ids = [r[0] for r in db.execute('SELECT id FROM lessons WHERE module_id=? ORDER BY position,id',(module_id,))]
    assert ids[-1] == lesson_id
    assert db.execute('SELECT completed FROM progress WHERE lesson_id=?',(lesson_id,)).fetchone()[0] == 1
    assert form(editor, lesson_path, csrf, **lesson_data(status='archived')).status_code == 302
    assert learner.get('/resources/'+resource_id).status_code == 404
    assert form(editor, lesson_path, csrf, **lesson_data(status='published')).status_code == 302
    assert learner.get('/api/lessons/'+lesson_id+'/practice').json['body'] == 'Сохранённая работа'
    assert form(editor, course_path, csrf, **course_data(status='draft')).status_code == 302
    assert learner.get('/api/lessons/'+lesson_id).status_code == 404
    assert form(editor, course_path, csrf, **course_data(status='archived')).status_code == 302
    assert db.execute('SELECT completed FROM progress WHERE lesson_id=?',(lesson_id,)).fetchone()[0] == 1
    db.close()


def test_authoring_validation_csrf_roles_conflict(app):
    client = app.test_client()
    assert client.get('/admin/content/').status_code == 401
    csrf = login(client)
    assert client.post('/admin/content/courses/new',data={'csrf':csrf,**course_data()}).status_code == 403
    csrf = login(client, 'admin')
    path = '/admin/content/lessons/'+FREE
    assert client.post(path, data=lesson_data()).status_code == 400
    assert form(client,path,csrf,**lesson_data(video='../session.key')).status_code == 400
    assert form(client,path,csrf,**lesson_data(minutes='0')).status_code == 400
    assert form(client,path,csrf,**lesson_data(task='Практика',checklist='')).status_code == 400
    page = client.get(path)
    revision = re.search(r'name="revision" value="([^"]*)"', page.text)[1]
    assert form(client,path,csrf,**lesson_data(title='Новая редакция')).status_code == 302
    assert client.post(path,data={'csrf':csrf,'revision':revision,**lesson_data()}).status_code == 409
    for url in ['javascript:alert(1)', 'https://user:password@example.com', '//example.com', 'https://example.com/ bad']:
        assert client.post(path+'/resources',data={'csrf':csrf,'title':'Источник','kind':'link','content':url}).status_code == 400
    assert client.post(path+'/resources',data={'csrf':csrf,'title':'Источник','kind':'link','content':'https://example.com/guide'}).status_code == 302
    db = sqlite3.connect(app.config['DATABASE'])
    resource = db.execute('SELECT id FROM resources').fetchone()[0]
    assert client.get('/admin/content/resources/'+resource+'/preview').location == 'https://example.com/guide'
    assert client.post('/admin/content/resources/'+resource+'/archive',data={'csrf':csrf}).status_code == 302
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
    assert db.execute('PRAGMA user_version').fetchone()[0] == 4
    assert db.execute('SELECT * FROM lessons ORDER BY id').fetchall() == before
    assert db.execute('SELECT completed FROM progress').fetchone()[0] == 1
    db.close()
