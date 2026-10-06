"""The React learner app: Flask serves the shell (with redirects and status codes) and JSON data."""
import json
import re
import sqlite3

from test_learning import app, login, post, FREE, PAID, PASSWORD


def bootstrap(response):
    return json.loads(re.search(r'<script type="application/json" id="bootstrap">(.*?)</script>', response.text, re.S).group(1))


def test_shell_carries_session_and_status(app):
    anonymous = app.test_client()
    page = anonymous.get('/')
    assert page.status_code == 200 and '<div id="root">' in page.text
    assert bootstrap(page)['user'] is None
    assert anonymous.get('/lessons/' + PAID).status_code == 403
    assert anonymous.get('/lessons/missing').status_code == 404
    assert anonymous.get('/profile').status_code == 302   # login first
    client = app.test_client(); login(client)
    data = bootstrap(client.get('/profile'))
    assert data['user']['name'] and data['csrf'] and 'password' not in json.dumps(data)


def test_page_load_records_visit_once_and_app_records_later_visits(app):
    client = app.test_client(); csrf = login(client)
    page = client.get('/lessons/' + FREE)
    assert bootstrap(page)['recorded_visit'] == FREE      # the app skips its own call for this load
    assert client.get('/api/app/lessons/foundations-start-02').status_code == 200
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute("SELECT COUNT(*) FROM lesson_visits WHERE lesson_id='foundations-start-02'").fetchone()[0] == 0   # reading data is not a visit
    assert post(client, '/api/app/lessons/foundations-start-02/visit', {}, csrf).status_code == 200
    assert client.get('/api/app/home').json['continuation']['unfinished']['lesson_id'] == 'foundations-start-02'
    assert client.post('/api/app/lessons/foundations-start-02/visit', json={}).status_code == 400   # CSRF required
    assert post(client, '/api/app/lessons/' + PAID + '/visit', {}, csrf).status_code == 403


def test_locked_lesson_data_has_no_content(app):
    client = app.test_client(); login(client)
    data = client.get('/api/app/lessons/' + PAID).json
    assert data['locked'] and set(data['lesson']) == {'id', 'title', 'objective', 'minutes', 'access', 'steps'}
    with sqlite3.connect(app.config['DATABASE']) as db:
        body, prompt = db.execute('SELECT body,prompt FROM lessons WHERE id=?', (PAID,)).fetchone()
    assert body not in json.dumps(data, ensure_ascii=False) and prompt not in json.dumps(data, ensure_ascii=False)


def test_every_learner_page_is_the_app_with_the_right_status(app):
    anonymous = app.test_client()
    for path, status in [('/catalogue', 200), ('/catalogue?q=x', 200), ('/courses/ai-foundations', 200), ('/membership', 200),
                         ('/help', 200), ('/login', 200), ('/materials/guide-check-answer', 200),
                         ('/materials/workshop-prompt-lab', 403), ('/courses/missing', 404), ('/materials/missing', 404),
                         ('/help?lesson=missing', 404), ('/no-such-page', 404)]:
        response = anonymous.get(path)
        assert response.status_code == status and '<div id="root">' in response.text, path
    assert bootstrap(anonymous.get('/courses/missing'))['error']['code'] == 404
    assert bootstrap(anonymous.get('/catalogue'))['error'] is None
    for path in ['/preferences', '/onboarding', '/profile']:
        assert anonymous.get(path).status_code == 302, path


def test_login_with_json_and_with_a_form(app):
    client = app.test_client(); csrf = bootstrap(client.get('/login'))['csrf']
    wrong = post(client, '/login', {'email': 'learner@example.test', 'password': 'nope'}, csrf)
    assert wrong.status_code == 401 and wrong.json['message'] == 'Не удалось войти. Проверьте почту и пароль.'
    assert client.post('/login', json={'email': 'learner@example.test', 'password': PASSWORD}).status_code == 400   # CSRF
    right = post(client, '/login?next=/catalogue', {'email': 'learner@example.test', 'password': PASSWORD}, csrf)
    assert right.status_code == 200 and right.json == {'next': '/catalogue'}
    assert bootstrap(client.get('/profile'))['csrf'] != csrf   # a new session gets a new token
    other = app.test_client(); token = bootstrap(other.get('/login'))['csrf']
    failed = other.post('/login', data={'csrf': token, 'email': 'learner@example.test', 'password': 'nope'})
    assert failed.status_code == 401 and bootstrap(failed)['notices'] == [{'kind': 'error', 'text': 'Не удалось войти. Проверьте почту и пароль.'}]
    assert post(other, '/login?next=//evil.example', {'email': 'learner@example.test', 'password': PASSWORD}, token).json['next'] == '/'


def test_flashed_notices_reach_the_app_once(app):
    client = app.test_client(); csrf = login(client)
    assert client.post('/preferences', data={'csrf': csrf, 'goal': 'work', 'experience': 'beginner', 'weekly_goal': '3'}).status_code == 302
    assert bootstrap(client.get('/profile'))['notices'] == [{'kind': 'success', 'text': 'Настройки сохранены.'}]
    assert bootstrap(client.get('/profile'))['notices'] == []
    assert post(client, '/preferences', {'goal': 'work', 'experience': 'experienced', 'weekly_goal': 5}, csrf).json == {'ok': True}
    assert client.get('/api/app/preferences').json == {'goal': 'work', 'experience': 'experienced', 'weekly_goal': 5}
    assert post(client, '/preferences', {'goal': 'work', 'experience': 'expert', 'weekly_goal': 5}, csrf).status_code == 400


def test_course_material_and_favourites_data(app):
    client = app.test_client(); csrf = login(client)
    course = client.get('/api/app/courses/ai-foundations').json
    assert course['course']['title'] and course['first'] and not course['favourite']
    assert course['outline'] is None and len(course['lessons']) == 37   # synthetic course: plain lesson list
    assert post(client, '/courses/ai-foundations/favourite', {'saved': True}, csrf).json == {'favourite': True}
    assert client.get('/api/app/courses/ai-foundations').json['favourite']
    assert post(client, '/courses/ai-foundations/favourite', {'saved': False}, csrf).json == {'favourite': False}
    assert client.get('/api/app/courses/missing').status_code == 404
    locked = app.test_client().get('/api/app/materials/workshop-prompt-lab').json
    assert locked['locked'] and 'paragraphs' not in locked['item'] and 'prompt' not in locked['item']
    with sqlite3.connect(app.config['DATABASE']) as db:
        body, prompt = db.execute("SELECT body,prompt FROM materials WHERE id='workshop-prompt-lab'").fetchone()
    assert body not in json.dumps(locked, ensure_ascii=False) and prompt not in json.dumps(locked, ensure_ascii=False)
    free = client.get('/api/app/materials/guide-check-answer').json
    assert not free['locked'] and free['item']['paragraphs'] and free['favourite'] is False
    assert post(client, '/materials/guide-check-answer/favourite', {'saved': True}, csrf).json == {'favourite': True}
    assert post(client, '/materials/guide-check-answer/favourite', {'saved': 'maybe'}, csrf).status_code == 400


def test_help_and_membership_data(app):
    client = app.test_client(); csrf = login(client)
    assert post(client, '/help?lesson=' + FREE, {'body': 'Вопрос из приложения'}, csrf).json == {'ok': True}
    assert post(client, '/help', {'body': '   '}, csrf).status_code == 400
    tickets = client.get('/api/app/help').json['tickets']
    assert [t['body'] for t in tickets] == ['Вопрос из приложения'] and tickets[0]['response'] is None
    assert app.test_client().get('/api/app/help').json == {'lesson': None, 'tickets': []}
    data = client.get('/api/app/membership?next=/lessons/' + PAID).json
    assert data['return_to'] == '/lessons/' + PAID and data['demo'] is False and data['member_lessons'] > 0
    assert client.get('/api/app/membership?next=https://evil.example').json['return_to'] == '/membership'
