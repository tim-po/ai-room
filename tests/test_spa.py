"""The React learner app: Flask serves the shell (with redirects and status codes) and JSON data."""
import json
import re
import sqlite3

from test_learning import app, login, post, FREE, PAID


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
