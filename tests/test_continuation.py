"""Cross-branch resume uses retained state and current authorization."""
import sqlite3
from flask import template_rendered
from club import create_app
from test_learning import app, login, post, FREE

AGENT = 'agent-api-basics'


def context(app, client, path='/'):
    captured = []
    def receive(sender, template, context, **extra):
        captured.append(context)
    with template_rendered.connected_to(receive, app):
        assert client.get(path).status_code == 200
    return captured[-1]


def test_cross_branch_draft_survives_preferences_login_and_restart(app):
    assert app.test_cli_runner().invoke(args=['init-skills']).exit_code == 0
    client = app.test_client(); csrf = login(client)
    post(client, '/api/lessons/'+FREE+'/completion', {'completed': True}, csrf)
    # Saving via API without a visit must still create a continuation.
    assert post(client, '/api/lessons/'+AGENT+'/practice',
                {'body': 'private draft', 'status': 'draft'}, csrf).status_code == 200
    client.post('/preferences', data=dict(csrf=csrf, goal='essentials', experience='beginner', weekly_goal='2'))
    client.post('/routes/path-work/select', data={'csrf': csrf})
    assert client.put('/api/skills/interests', json={'node_ids': ['coding', 'content']},
                      headers={'X-CSRF-Token': csrf}).status_code == 200
    home = context(app, client)
    assert home['next_lesson']['id'] == AGENT
    assert home['started'] is True
    assert home['continuation']['unfinished']['status'] == 'draft'
    assert home['continuation']['last_result']['lesson_id'] == FREE
    assert context(app, client, '/profile')['continuation'] == home['continuation']
    client.post('/logout', data={'csrf': csrf})
    login(client)
    assert context(app, client)['continuation'] == home['continuation']
    restarted = create_app(dict(TESTING=True, DATABASE=app.config['DATABASE'], SECRET_KEY='restart'))
    other_device = restarted.test_client(); login(other_device)
    assert context(restarted, other_device)['continuation'] == home['continuation']
    other = app.test_client(); login(other, 'member')
    assert context(app, other)['continuation']['unfinished'] is None
    assert context(app, app.test_client())['continuation']['last_result'] is None
    assert 'private draft' not in str(home['continuation'])


def test_current_access_and_publication_filter_both_slots(app):
    client = app.test_client(); csrf = login(client, 'member')
    post(client, '/api/lessons/'+AGENT+'/practice', {'body': 'draft', 'status': 'draft'}, csrf)
    post(client, '/api/lessons/'+FREE+'/completion', {'completed': True}, csrf)
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE lessons SET access='member' WHERE id IN (?,?)", (AGENT, FREE))
        db.execute("UPDATE users SET entitlement='expired' WHERE email='member@example.test'")
    assert context(app, client)['continuation'] == dict(version='learning-continuation-v1', unfinished=None, last_result=None)
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE users SET entitlement='member' WHERE email='member@example.test'")
        db.execute("UPDATE lessons SET status='archived' WHERE id=?", (AGENT,))
        db.execute("UPDATE courses SET status='draft' WHERE id='ai-foundations'")
    assert context(app, client)['continuation']['unfinished'] is None
    assert context(app, client)['continuation']['last_result'] is None
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT body FROM practice WHERE lesson_id=?', (AGENT,)).fetchone()[0] == 'draft'
        assert db.execute('SELECT completed FROM progress WHERE lesson_id=?', (FREE,)).fetchone()[0] == 1


def test_latest_timestamps_ties_and_completed_lesson_draft(app):
    client = app.test_client(); csrf = login(client)
    for lesson in [FREE, AGENT]:
        client.get('/lessons/'+lesson)
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE progress SET updated_at='2026-10-01 12:00:00'")
    assert context(app, client)['continuation']['unfinished']['lesson_id'] == AGENT
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE progress SET updated_at='2026-10-02 12:00:00' WHERE lesson_id=?", (FREE,))
    assert context(app, client)['continuation']['unfinished']['lesson_id'] == FREE
    post(client, '/api/lessons/'+AGENT+'/completion', {'completed': True}, csrf)
    post(client, '/api/lessons/'+AGENT+'/practice', {'body': 'revised draft', 'status': 'draft'}, csrf)
    assert context(app, client)['continuation']['unfinished']['lesson_id'] == AGENT
    post(client, '/api/lessons/'+AGENT+'/practice', {'body': 'submitted artifact', 'status': 'submitted'}, csrf)
    result = context(app, client)['continuation']
    assert result['unfinished']['lesson_id'] == FREE
    assert result['last_result']['status'] == 'submitted'
    assert result['last_result']['lesson_id'] == AGENT
