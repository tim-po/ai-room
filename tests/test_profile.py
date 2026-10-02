"""Personal learning and first-completion goal regression coverage."""
import sqlite3
from test_learning import app, login, post, FREE


def section(html, identity):
    return html.split(f'aria-labelledby="{identity}"', 1)[1].split('</section>', 1)[0]


def test_personal_learning_lifecycle_and_new_content(app):
    client = app.test_client()
    csrf = login(client, 'member')
    html = client.get('/profile').text
    assert 'Пока нет курсов в работе' in html
    assert 'class="card"' not in html
    client.get('/lessons/' + FREE)
    html = client.get('/profile').text
    assert '/courses/ai-foundations' in section(html, 'active-learning')
    assert '/courses/everyday-ai' not in section(html, 'active-learning')
    with sqlite3.connect(app.config['DATABASE']) as db:
        lessons = db.execute("SELECT l.id FROM lessons l JOIN modules m ON m.id=l.module_id WHERE m.course_id='ai-foundations' AND l.status='published'").fetchall()
    for (identity,) in lessons:
        assert post(client, '/api/lessons/'+identity+'/completion', {'completed':True}, csrf).status_code == 200
    html = client.get('/profile').text
    assert '/courses/ai-foundations' in section(html, 'completed-learning')
    assert '/courses/ai-foundations' not in section(html, 'active-learning')
    post(client, '/api/lessons/'+FREE+'/completion', {'completed':False}, csrf)
    assert '/courses/ai-foundations' in section(client.get('/profile').text, 'active-learning')
    post(client, '/api/lessons/'+FREE+'/completion', {'completed':True}, csrf)
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("INSERT INTO lessons(id,module_id,title,objective,body,minutes,position,access) SELECT 'profile-added',module_id,'Новый урок','Цель','Текст',5,100,'free' FROM lessons WHERE id=?", (FREE,))
    html = client.get('/profile').text
    assert '/courses/ai-foundations' in section(html, 'active-learning')
    assert '37 / 38' in html
    other = app.test_client()
    login(other)
    assert 'class="card"' not in other.get('/profile').text
    assert html.index('id="practice"') < html.index('id="active-learning"')


def test_weekly_goal_unique_history_pause_and_rolling_window(app):
    client = app.test_client()
    csrf = login(client)
    for value in [True, True, False, True]:
        post(client, '/api/lessons/'+FREE+'/completion', {'completed':value}, csrf)
    for path in ['/profile']:
        assert 'Недельная цель: 1 из 2' in client.get(path).text
    assert 'id="practice"' in client.get('/profile').text
    assert client.post('/preferences',data={'csrf':csrf,'goal':'essentials','experience':'beginner','weekly_goal':'1'}).status_code == 302
    assert 'Цель достигнута' in client.get('/profile').text
    client.post('/preferences',data={'csrf':csrf,'goal':'essentials','experience':'beginner','weekly_goal':'0'})
    for path in ['/profile']:
        html=client.get(path).text
        assert 'Недельная цель на паузе' in html
        assert 'aria-label="Недельная цель"' not in html
        assert 'за последние 7 дней: 1 урок.' in html
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE events SET created_at=datetime('now','-8 days') WHERE name='lesson_completed'")
    post(client, '/api/lessons/'+FREE+'/completion', {'completed':False}, csrf)
    post(client, '/api/lessons/'+FREE+'/completion', {'completed':True}, csrf)
    assert 'за последние 7 дней: 0 уроков.' in client.get('/profile').text
    plural=app.jinja_env.filters['plural_ru']
    assert [plural(n,'урок','урока','уроков') for n in [0,1,2,5,11,12,14,21,22,25,111]] == ['уроков','урок','урока','уроков','уроков','уроков','уроков','урок','урока','уроков','уроков']
