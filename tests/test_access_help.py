"""Tester access-help regression, made isolated and extended to privacy/submission."""
import json
import sqlite3
import pytest
from test_learning import app, login, token, PAID


@pytest.mark.parametrize('who', ['learner', 'revoked', 'expired'])
def test_access_help_is_reachable_and_private(app, who):
    if who == 'expired':
        with sqlite3.connect(app.config['DATABASE']) as db:
            db.execute("UPDATE users SET entitlement='expired' WHERE id='user-learner'")
        who = 'learner'
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE lessons SET body='PRIVATE LESSON BODY',prompt='PRIVATE PROMPT',task='PRIVATE PRACTICE' WHERE id=?", (PAID,))
        title = db.execute('SELECT title FROM lessons WHERE id=?', (PAID,)).fetchone()[0]
    client = app.test_client()
    csrf = login(client, who)
    path = '/help?lesson=' + PAID
    response = client.get(path)
    data = client.get('/api/app/help?lesson=' + PAID).json
    assert response.status_code == 200 and data['lesson'] == {'id': PAID, 'title': title}
    for private in ['PRIVATE LESSON BODY', 'PRIVATE PROMPT', 'PRIVATE PRACTICE']:
        assert private not in response.text and private not in json.dumps(data, ensure_ascii=False)
    assert client.post(path, data={'body': 'missing csrf'}).status_code == 400
    assert client.post(path, data={'csrf': csrf, 'body': '  '}).status_code == 400
    question = 'Мой частный вопрос о доступе'
    assert client.post(path, data={'csrf': csrf, 'body': question}).status_code == 302
    assert [t['body'] for t in client.get('/api/app/help').json['tickets']] == [question]
    for boundary in ['/lessons/' + PAID, '/api/lessons/' + PAID,
                     '/lessons/' + PAID + '/media', '/lessons/' + PAID + '/resources/checklist.txt']:
        assert client.get(boundary).status_code == 403
    other = app.test_client()
    login(other, 'member')
    assert other.get('/api/app/help').json['tickets'] == []
    assert client.get('/admin').status_code == 403
    login(other, 'admin')
    inbox = other.get('/admin').text
    assert title in inbox and question in inbox
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT user_id,lesson_id,body FROM help_requests').fetchone() == ('user-' + who, PAID, question)
        assert db.execute("SELECT lesson_id FROM events WHERE name='help_requested'").fetchone() == (PAID,)


@pytest.mark.parametrize('entity', ['lessons', 'courses'])
@pytest.mark.parametrize('status', ['draft', 'archived'])
def test_help_cannot_disclose_unpublished_context(app, entity, status):
    client = app.test_client()
    csrf = login(client)
    with sqlite3.connect(app.config['DATABASE']) as db:
        title = db.execute('SELECT title FROM lessons WHERE id=?', (PAID,)).fetchone()[0]
        db.execute(f'UPDATE {entity} SET status=? WHERE id=?',
                   (status, PAID if entity == 'lessons' else 'ai-foundations'))
    path = '/help?lesson=' + PAID
    response = client.get(path)
    assert response.status_code == 404 and title not in response.text
    assert client.get('/api/app/help?lesson=' + PAID).status_code == 404
    assert client.post(path, data={'csrf': csrf, 'body': 'hidden context'}).status_code == 404
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM help_requests').fetchone()[0] == 0


def test_help_anonymous_and_unknown_context(app):
    client = app.test_client()
    csrf = token(client)
    path = '/help?lesson=' + PAID
    assert client.get(path).status_code == 200
    assert client.post(path, data={'csrf': csrf, 'body': 'anonymous'}).status_code == 401
    assert client.get('/help?lesson=unknown').status_code == 404
