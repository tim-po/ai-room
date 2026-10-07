import sqlite3
from pathlib import Path
import pytest
from club import create_app
from club.seed import seed_database

FREE = 'foundations-start-01'
PAID = 'foundations-context-01'
PASSWORD = 'independent-test-password'

@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv('CLUB_SEED_PASSWORD', PASSWORD)
    database = str(tmp_path / 'test.sqlite')
    db = sqlite3.connect(database)
    db.executescript(Path('club/schema.sql').read_text())
    seed_database(db)
    db.close()
    return create_app({'TESTING': True, 'DATABASE': database, 'SECRET_KEY': 'test-only-key'})


def token(client):
    client.get('/login')
    with client.session_transaction() as session:
        return session['csrf']


def login(client, who='learner'):
    response = client.post('/login', data={'email':who+'@example.test','password':PASSWORD,'csrf':token(client)})
    assert response.status_code == 302
    with client.session_transaction() as session:
        return session['csrf']


def post(client, path, data, csrf):
    return client.post(path, json=data, headers={'X-CSRF-Token':csrf})


def test_access_is_enforced_at_every_boundary(app):
    c = app.test_client()
    assert c.get('/api/lessons/' + FREE).status_code == 200
    for path in ['/api/lessons/'+PAID, '/lessons/'+PAID, '/lessons/'+PAID+'/resources/checklist.txt', '/lessons/'+PAID+'/media']:
        assert c.get(path).status_code == 403
    csrf = login(c)
    assert c.get('/admin').status_code == 403
    assert post(c, '/api/lessons/'+PAID+'/practice', {'body':'secret','status':'draft'}, csrf).status_code == 403
    login(c,'member')
    assert c.get('/api/lessons/'+PAID).status_code == 200
    assert c.get('/lessons/'+PAID+'/resources/checklist.txt').status_code == 200
    login(c,'revoked')
    assert c.get('/api/lessons/'+PAID).status_code == 403
    login(c,'admin')
    assert c.get('/admin').status_code == 200


def test_practice_progress_restart_and_cross_user_isolation(app):
    c = app.test_client()
    csrf = login(c)
    url = '/api/lessons/'+FREE
    assert post(c,url+'/practice',{'body':'Мой учебный результат','status':'draft'},csrf).status_code == 200
    for _ in range(3):
        assert post(c,url+'/completion',{'completed':True},csrf).status_code == 200
    assert post(c,url+'/video',{'seconds':7.5},csrf).status_code == 200
    db = sqlite3.connect(app.config['DATABASE'])
    assert db.execute("SELECT COUNT(*) FROM events WHERE name='lesson_completed'").fetchone()[0] == 1
    assert db.execute('SELECT completed,video_seconds FROM progress').fetchone() == (1,7.5)
    assert post(c,url+'/completion',{'completed':False},csrf).status_code == 200
    assert post(c,url+'/completion',{'completed':True},csrf).status_code == 200
    assert db.execute("SELECT COUNT(*) FROM events WHERE name='lesson_completed'").fetchone()[0] == 1
    c.post('/logout',data={'csrf':csrf})
    assert c.get(url+'/practice').status_code == 401
    new_app = create_app({'TESTING':True,'DATABASE':app.config['DATABASE'],'SECRET_KEY':'new-process-test'})
    second_device = new_app.test_client()
    login(second_device)
    assert second_device.get(url+'/practice').json['body'] == 'Мой учебный результат'
    assert 'Мой учебный результат' in [w['body'] for w in second_device.get('/api/app/profile').json['practices']]
    other = app.test_client()
    login(other,'member')
    assert other.get(url+'/practice').json is None
    assert other.get('/api/app/profile').json['practices'] == []
    db.close()


def test_csrf_drafts_and_validation(app):
    c = app.test_client()
    csrf = login(c)
    assert c.post('/api/lessons/'+FREE+'/completion',json={'completed':True}).status_code == 400
    assert post(c,'/api/lessons/'+FREE+'/practice',{'body':'x'*12001},csrf).status_code == 400
    assert post(c,'/api/lessons/'+FREE+'/completion',{'completed':'yes'},csrf).status_code == 400
    assert post(c,'/api/lessons/'+FREE+'/video',{'seconds':-1},csrf).status_code == 400
    db = sqlite3.connect(app.config['DATABASE'])
    db.execute("UPDATE lessons SET status='draft' WHERE id=?",(FREE,))
    db.commit()
    assert c.get('/api/lessons/'+FREE).status_code == 404
    assert c.get('/lessons/'+FREE+'/resources/checklist.txt').status_code == 404
    assert post(c,'/api/lessons/'+FREE+'/completion',{'completed':True},csrf).status_code == 404
    db.close()


def test_rendered_learning_journey(app):
    c = app.test_client()
    for path in ['/', '/catalogue', '/catalogue?q=невозможныйзапрос', '/courses/ai-foundations', '/lessons/'+FREE, '/help', '/login']:
        assert c.get(path).status_code == 200, path
    assert c.get('/api/app/home').json['next']['url'] == '/lessons/foundations-start-01'   # welcome page "try a free lesson"
    csrf = login(c)
    assert c.post('/preferences',data={'csrf':csrf,'goal':'work','experience':'beginner','weekly_goal':'0'}).status_code == 302
    assert 'Меньше рутины' in c.get('/routes/path-work').text
    assert c.post('/courses/ai-foundations/favourite',data={'csrf':csrf,'saved':'1'}).status_code == 302
    assert c.post('/help?lesson='+FREE,data={'csrf':csrf,'body':'Нужна помощь с примером'}).status_code == 302
    assert c.get('/api/app/help').json['tickets'][0]['body'] == 'Нужна помощь с примером'
    assert c.get('/profile').status_code == 200
    db = sqlite3.connect(app.config['DATABASE'])
    assert db.execute('SELECT COUNT(*) FROM lessons l JOIN modules m ON l.module_id=m.id WHERE m.course_id=?',('ai-foundations',)).fetchone()[0] == 37
    db.close()
