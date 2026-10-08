"""The admin's own assistant: a helper that finds and edits any course, lesson or material through the
admin's operations. It never holds a key: its one-time link sets a cookie that works on the admin API
until ten minutes pass without a request. Kept apart from learners' learning connections."""
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

from test_learning import app, login, post
from test_oauth import CALLBACK, authorize, pkce, register, token


def connect(app, who='editor'):
    """The person copies a link in the admin; their assistant opens it with a client that keeps cookies.
    Returns (the assistant's client, the briefing, the person's browser, its CSRF token)."""
    browser = app.test_client()
    csrf = login(browser, who)
    link = post(browser, '/api/admin/assistant/links', {}, csrf)
    assert link.status_code == 200, link.json
    assert link.json['url'] in link.json['message'] and 'cookies' in link.json['message']
    agent = app.test_client()
    briefing = agent.get(urlsplit(link.json['url']).path, headers={'Accept': 'text/markdown'})
    assert briefing.status_code == 200 and briefing.mimetype == 'text/markdown'
    assert 'as_' not in briefing.text and 'Bearer' not in briefing.text      # no key anywhere: the access is the cookie
    return agent, briefing.text, browser, csrf


def tool(agent, name, **arguments):
    reply = agent.post('/api/admin/tools/' + name, json=arguments)
    return (reply.json if reply.status_code == 200 else reply.json['message']), reply.status_code != 200


def mcp(client, key, method, params=None, path='/mcp/admin'):
    return client.post(path, json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}},
                       headers={'Authorization': 'Bearer ' + key})


def ends_at(app):
    with sqlite3.connect(app.config['DATABASE']) as db:
        value = db.execute("SELECT expires_at FROM connected_sessions WHERE scope='content' ORDER BY created_at DESC LIMIT 1").fetchone()[0]
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)


def test_an_editor_drafts_a_course_with_their_assistant(app):
    from club.legacy_content import ensure_schema
    with sqlite3.connect(app.config['DATABASE']) as db:
        ensure_schema(db)   # a real installation has the Markdown body format (install-legacy-lessons adds it)
    agent, briefing, _, _ = connect(app)
    assert '/api/admin/tools' in briefing and 'черновик' in briefing and '@video' in briefing and '10 минут' in briefing
    index = agent.get('/api/admin/tools').json
    assert 'Редактор' in index['instructions']
    assert {'overview', 'search', 'create_lesson', 'update_lesson', 'answer_question'} <= {t['name'] for t in index['tools']}
    overview, error = tool(agent, 'overview')
    assert not error and 'courses' in overview
    course, _ = tool(agent, 'create_course', title='Claude для продаж')
    assert course['status'] == 'draft' and course['admin_url'].endswith('/admin/courses/' + course['id'])
    course, _ = tool(agent, 'add_module', course_id=course['id'], title='Письма')
    module = course['modules'][0]['id']
    lesson, _ = tool(agent, 'create_lesson', module_id=module, title='Письмо после звонка', objective='Написать письмо',
                     body='## Зачем\n\nПисьмо закрепляет договорённости.\n\n- Кратко\n- По делу')
    assert lesson['status'] == 'draft' and lesson['body_format'] == 'blocks'
    # Only the fields named change; a stale revision is refused, never overwritten.
    edited, _ = tool(agent, 'update_lesson', lesson_id=lesson['id'], revision=lesson['revision'], title='Письмо клиенту')
    assert edited['title'] == 'Письмо клиенту' and edited['body'] == lesson['body']
    refused, error = tool(agent, 'update_lesson', lesson_id=lesson['id'], revision=lesson['revision'], title='Старое')
    assert error and 'другой' in refused
    published, error = tool(agent, 'update_lesson', lesson_id=lesson['id'], status='published')
    assert not error and published['status'] == 'published'
    assert tool(agent, 'no_such_tool')[1]
    # The admin JSON API takes the same cookie, without the browser's CSRF token…
    listed = agent.get('/api/admin/courses')
    assert listed.status_code == 200 and any(c['id'] == course['id'] for c in listed.json['courses'])
    assert agent.post('/api/admin/courses', json={'title': 'Ещё курс'}).status_code == 201
    # …but links and connections are managed only by the person, in the browser.
    assert agent.post('/api/admin/assistant/links', json={}).status_code == 403


def test_the_helper_ends_ten_minutes_after_its_last_request(app):
    browser = app.test_client(); csrf = login(browser, 'editor')
    url = urlsplit(post(browser, '/api/admin/assistant/links', {}, csrf).json['url']).path
    # The person opening their own link (signed in here) doesn't use it up.
    mistake = browser.get(url)
    assert mistake.status_code == 200 and 'для вашего ИИ-ассистента' in mistake.text and not browser.get_cookie('airoom_helper', path='/api/admin/')
    agent = app.test_client()
    assert agent.get(url).status_code == 200
    assert app.test_client().get(url).status_code == 409            # one-time
    cookie = agent.get_cookie('airoom_helper', path='/api/admin/')
    assert cookie and cookie.http_only and cookie.same_site == 'Strict'
    # Each request moves the end ten minutes on, and the cookie with it.
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE connected_sessions SET expires_at=datetime('now','+2 minutes') WHERE scope='content'")
    answer = agent.get('/api/admin/tools')
    assert answer.status_code == 200 and 'Max-Age=600' in answer.headers['Set-Cookie']
    assert ends_at(app) > datetime.now(timezone.utc) + timedelta(minutes=9)
    # Ten quiet minutes, and it is over.
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE connected_sessions SET expires_at=datetime('now','-1 second') WHERE scope='content'")
    assert agent.get('/api/admin/tools').status_code == 401
    # The cookie is not a key: sent as a header, it opens nothing.
    assert app.test_client().get('/api/admin/courses', headers={'Authorization': 'Bearer ' + cookie.value}).status_code == 401


def test_content_and_learning_access_never_cross(app):
    agent, _, editor, csrf = connect(app)
    assert agent.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}).status_code == 401   # not the learner
    assert agent.get('/api/agent/status').status_code == 401
    learner = app.test_client(); learner_csrf = login(learner)
    assert post(learner, '/api/admin/assistant/links', {}, learner_csrf).status_code == 403
    link = post(learner, '/api/app/attach-links', {}, learner_csrf).json['url']
    learning = re.search(r'Bearer (as_\S+)', app.test_client().get(urlsplit(link).path).text)[1]
    assert mcp(agent, learning, 'tools/list').status_code == 401                # a learning key can't edit content
    assert agent.get('/api/admin/courses', headers={'Authorization': 'Bearer ' + learning}).status_code == 401
    # A person signed in here always acts as themselves, even with a helper's cookie in their browser.
    editor.set_cookie('airoom_helper', agent.get_cookie('airoom_helper', path='/api/admin/').value, path='/api/admin/')
    assert editor.post('/api/admin/courses', json={'title': 'Без CSRF'}).status_code == 400
    # The learner's «Подключения» lists only learning connections; the admin's card lists the helper.
    assert all(c['label'] for c in learner.get('/api/app/connections').json['connections'])
    sessions = editor.get('/api/admin/assistant').json['sessions']
    assert len(sessions) == 1 and editor.get('/api/app/connections').json['connections'] == []
    assert editor.get('/api/admin/overview').json['assistant']['sessions'] == sessions
    assert 'assistant' not in agent.get('/api/admin/overview').json
    # Disconnecting stops it at once.
    assert editor.delete('/api/admin/assistant/sessions/' + sessions[0]['id'], headers={'X-CSRF-Token': csrf}).status_code == 200
    assert agent.get('/api/admin/tools').status_code == 401


def test_a_demoted_editor_loses_the_helper(app):
    agent, _, _, _ = connect(app)
    assert agent.get('/api/admin/tools').status_code == 200
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE users SET role='learner' WHERE id='user-editor'")
    assert agent.get('/api/admin/tools').status_code == 403
    assert agent.get('/api/admin/courses').status_code == 403


def test_the_assistant_finds_and_edits_anything(app):
    browser = app.test_client(); csrf = login(browser, 'editor')
    course = post(browser, '/api/admin/courses', {'title': 'Курс'}, csrf).json['course']['id']
    module = post(browser, f'/api/admin/courses/{course}/modules', {'title': 'Модуль писем'}, csrf).json['modules'][0]['id']
    lesson = post(browser, f'/api/admin/modules/{module}/lessons', {'title': 'Урок', 'body': 'Особый текст про Ёлку'}, csrf).json['lesson']['id']
    agent, briefing, _, _ = connect(app)
    assert 'search' in briefing and 'list_learners' not in briefing      # an editor's assistant: content, not people
    # Any lesson, draft or not, by words from its text; modules too.
    found, error = tool(agent, 'search', text='особый ёлку')
    assert not error and (found[0]['kind'], found[0]['id']) == ('lesson', lesson) and 'Ёлку' in found[0]['snippet']
    assert found[0]['admin_url'].endswith('/admin/lessons/' + lesson)
    assert tool(agent, 'search', text='модуль писем')[0][0]['kind'] == 'module'
    # Links and files, with the editor's own checks.
    with_file, _ = tool(agent, 'add_file', to='lesson', id=lesson, title='Шаблон', kind='link', content='https://example.com/t')
    resource = with_file['resources'][0]
    refused, error = tool(agent, 'add_file', to='lesson', id=lesson, title='Шаблон', kind='link', content='http://example.com/t')
    assert error and 'HTTPS' in refused
    archived, _ = tool(agent, 'archive_file', to='lesson', resource_id=resource['id'])
    assert archived['resources'][0]['status'] == 'archived'
    refused, error = tool(agent, 'restore_from_files', kind='lesson', id=lesson)
    assert error and 'версии из файлов' in refused
    # Learners and analytics are an admin's: not listed for an editor, refused if called anyway.
    assert 'list_learners' not in {t['name'] for t in agent.get('/api/admin/tools').json['tools']}
    assert tool(agent, 'list_learners')[1]
    agent, briefing, _, _ = connect(app, 'admin')
    assert 'list_learners' in briefing
    people, error = tool(agent, 'list_learners')
    assert not error and people and all('email' not in p for p in people)
    one, _ = tool(agent, 'get_learner', user_id='user-learner')
    assert one['learner']['id'] == 'user-learner' and 'email' not in one['learner']
    stats, error = tool(agent, 'analytics')
    assert not error and 'loop' in stats


def test_claude_ai_connector_for_the_admin(app):
    machine = app.test_client()
    client_id = register(machine).json['client_id']
    assert machine.get('/.well-known/oauth-protected-resource/mcp/admin').json['scopes_supported'] == ['content']
    challenge = machine.post('/mcp/admin', json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'})
    assert 'oauth-protected-resource/mcp/admin' in challenge.headers['WWW-Authenticate']
    # A learner can't approve an admin connection.
    verifier, code_challenge = pkce()
    learner = app.test_client(); learner_csrf = login(learner)
    authorize(learner, client_id, code_challenge, scope='content', resource='http://localhost/mcp/admin')
    consent = learner.get('/api/app/oauth/consent').json
    assert consent['scope'] == 'content' and consent['allowed'] is False
    denied = post(learner, '/api/app/oauth/consent', {'approve': True}, learner_csrf).json['redirect']
    assert parse_qs(urlsplit(denied).query)['error'] == ['access_denied']
    # An editor can.
    editor = app.test_client(); csrf = login(editor, 'editor')
    authorize(editor, client_id, code_challenge, scope='content', resource='http://localhost/mcp/admin')
    assert editor.get('/api/app/oauth/consent').json['allowed'] is True
    code = parse_qs(urlsplit(post(editor, '/api/app/oauth/consent', {'approve': True}, csrf).json['redirect']).query)['code'][0]
    issued = token(machine, grant_type='authorization_code', code=code, redirect_uri=CALLBACK, client_id=client_id, code_verifier=verifier).json
    assert issued['scope'] == 'content'
    assert mcp(machine, issued['access_token'], 'tools/list').status_code == 200
    assert mcp(machine, issued['access_token'], 'tools/list', path='/mcp').status_code == 401
    refreshed = token(machine, grant_type='refresh_token', refresh_token=issued['refresh_token'], client_id=client_id).json
    assert refreshed['scope'] == 'content' and mcp(machine, refreshed['access_token'], 'tools/list').status_code == 200


def test_works_get_feedback_from_the_team_and_the_assistant(app):
    from test_learning import FREE
    learner = app.test_client(); learner_csrf = login(learner)
    post(learner, f'/api/lessons/{FREE}/practice', {'body': 'Мой первый результат', 'status': 'submitted'}, learner_csrf)
    editor = app.test_client(); csrf = login(editor, 'editor')
    waiting = editor.get('/api/admin/works').json
    assert waiting['waiting'] == 1 and waiting['works'][0]['body'] == 'Мой первый результат'
    assert editor.get('/api/admin/overview').json['counts']['works_waiting'] == 1
    assert post(learner, f'/api/admin/works/user-learner/{FREE}/review', {'body': 'x'}, learner_csrf).status_code == 403
    reviewed = post(editor, f'/api/admin/works/user-learner/{FREE}/review', {'body': 'Хорошо! Добавьте пример.'}, csrf).json
    assert reviewed['review'] == 'Хорошо! Добавьте пример.' and not reviewed['waiting']
    # The learner reads it on the lesson and in «Мои работы».
    assert learner.get(f'/api/app/lessons/{FREE}').json['practice']['review']['body'] == 'Хорошо! Добавьте пример.'
    assert learner.get('/api/app/profile').json['practices'][0]['review']['reviewer'] == 'Редактор'
    # Changing the work puts it back in the queue, with the old feedback still shown.
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE practice_reviews SET updated_at=datetime('now','-1 hour')")
    post(learner, f'/api/lessons/{FREE}/practice', {'body': 'Исправленный результат', 'status': 'submitted'}, learner_csrf)
    again = editor.get('/api/admin/works').json['works'][0]
    assert again['waiting'] and again['changed'] and again['review']
    # The editor's assistant can list works and leave feedback too.
    agent, _, _, _ = connect(app)
    listed, _ = tool(agent, 'list_works')
    assert listed[0]['body'] == 'Исправленный результат'
    done, error = tool(agent, 'review_work', user_id='user-learner', lesson_id=FREE, feedback='Теперь отлично.')
    assert not error and done['review'] == 'Теперь отлично.' and not done['waiting']
