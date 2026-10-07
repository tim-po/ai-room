"""Personal learning and first-completion goal regression coverage (Моё обучение data)."""
import sqlite3
from test_learning import app, login, post, FREE


def profile(client):
    response = client.get('/api/app/profile')
    assert response.status_code == 200
    return response.json


def ids(data, key):
    return [course['id'] for course in data[key]]


def test_personal_learning_lifecycle_and_new_content(app):
    client = app.test_client()
    csrf = login(client, 'member')
    assert client.get('/profile').status_code == 200
    data = profile(client)
    assert data['active_courses'] == [] and data['completed_courses'] == []
    client.get('/lessons/' + FREE)
    data = profile(client)
    assert 'ai-foundations' in ids(data, 'active_courses')
    assert 'everyday-ai' not in ids(data, 'active_courses')
    with sqlite3.connect(app.config['DATABASE']) as db:
        lessons = db.execute("SELECT l.id FROM lessons l JOIN modules m ON m.id=l.module_id WHERE m.course_id='ai-foundations' AND l.status='published'").fetchall()
    for (identity,) in lessons:
        assert post(client, '/api/lessons/'+identity+'/completion', {'completed':True}, csrf).status_code == 200
    data = profile(client)
    assert 'ai-foundations' in ids(data, 'completed_courses')
    assert 'ai-foundations' not in ids(data, 'active_courses')
    post(client, '/api/lessons/'+FREE+'/completion', {'completed':False}, csrf)
    assert 'ai-foundations' in ids(profile(client), 'active_courses')
    post(client, '/api/lessons/'+FREE+'/completion', {'completed':True}, csrf)
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("INSERT INTO lessons(id,module_id,title,objective,body,minutes,position,access) SELECT 'profile-added',module_id,'Новый урок','Цель','Текст',5,100,'free' FROM lessons WHERE id=?", (FREE,))
    course = next(c for c in profile(client)['active_courses'] if c['id'] == 'ai-foundations')
    assert (course['done'], course['total']) == (37, 38)
    assert course['next']['id'] == 'profile-added'
    other = app.test_client()
    login(other)
    assert profile(other)['active_courses'] == []


def test_weekly_goal_unique_history_pause_and_rolling_window(app):
    client = app.test_client()
    csrf = login(client)
    for value in [True, True, False, True]:
        post(client, '/api/lessons/'+FREE+'/completion', {'completed':value}, csrf)
    data = profile(client)
    assert (data['weekly'], data['user']['weekly_goal']) == (1, 2)   # "Недельная цель: 1 из 2"
    assert client.post('/preferences',data={'csrf':csrf,'goal':'essentials','experience':'beginner','weekly_goal':'1'}).status_code == 302
    data = profile(client)
    assert data['weekly'] >= data['user']['weekly_goal'] == 1        # "Цель достигнута"
    client.post('/preferences',data={'csrf':csrf,'goal':'essentials','experience':'beginner','weekly_goal':'0'})
    data = profile(client)
    assert (data['user']['weekly_goal'], data['weekly']) == (0, 1)   # paused; "за последние 7 дней: 1 урок"
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE events SET created_at=datetime('now','-8 days') WHERE name='lesson_completed'")
    post(client, '/api/lessons/'+FREE+'/completion', {'completed':False}, csrf)
    post(client, '/api/lessons/'+FREE+'/completion', {'completed':True}, csrf)
    assert profile(client)['weekly'] == 0
    plural=app.jinja_env.filters['plural_ru']
    assert [plural(n,'урок','урока','уроков') for n in [0,1,2,5,11,12,14,21,22,25,111]] == ['уроков','урок','урока','уроков','уроков','уроков','уроков','урок','урока','уроков','уроков']
