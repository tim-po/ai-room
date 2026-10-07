"""Attached sessions: one-time links a learner pastes into their AI assistant, and the scoped keys
those links hand out (HTTP /api/agent/* and MCP /mcp)."""
import json
import re
import sqlite3

from test_learning import app, login, post, FREE, PAID, PASSWORD
from test_skills import skills
from test_onboarding import onboard
from test_legacy_content import legacy, learner

LESSON = 'claude-first-result'
CLUB = 'claude-basics-context'


def new_link(client, csrf, **body):
    response = post(client, '/api/app/attach-links', body, csrf)
    assert response.status_code == 200, response.json
    return response.json['url'].replace('http://localhost', '')


def claim(app, path, **headers):
    return app.test_client().get(path, headers={'User-Agent': 'Claude-User/1.0', **headers})


def key_of(document):
    return re.search(r'Authorization: Bearer (as_\w+_[\w-]+)', document)[1]


def agent(app, key):
    client = app.test_client()
    client.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + key
    return client


def rpc(client, method, params=None, ident=1):
    return client.post('/mcp', json={'jsonrpc': '2.0', 'id': ident, 'method': method, 'params': params or {}})


def test_link_works_once_and_previews_do_not_use_it(legacy):
    c = legacy.test_client(); csrf = login(c, learner(legacy, 'linker', onboarded=True))
    path = new_link(c, csrf, lesson_id=LESSON, draft='Мой несохранённый черновик')
    assert re.fullmatch(r'/attach/al_[0-9a-f]{12}_[\w-]+', path)
    guest = legacy.test_client()
    assert guest.head(path).status_code == 200                                              # HEAD validates only
    assert 'учебная ссылка' in guest.get(path, headers={'User-Agent': 'TelegramBot (like TwitterBot)'}).text   # preview stub
    document = claim(legacy, path)
    assert document.status_code == 200 and document.mimetype == 'text/markdown'
    text = document.text
    assert 'Урок: Первый полезный результат за 20 минут' in text and 'Мой несохранённый черновик' in text
    assert '### Критерии хорошего результата' in text and '## Текст урока' in text and key_of(text)
    assert claim(legacy, path).status_code == 409 and guest.head(path).status_code == 409
    assert legacy.test_client().get(path.replace('al_', 'al_0')).status_code == 404
    with sqlite3.connect(legacy.config['DATABASE']) as db:
        stored = json.dumps(db.execute('SELECT * FROM attach_links').fetchall() + db.execute('SELECT * FROM connected_sessions').fetchall())
        assert path.rsplit('/', 1)[1] not in stored and key_of(text) not in stored          # hashes only
        assert 'Мой несохранённый черновик' not in stored                                     # dropped once delivered
        db.execute("UPDATE attach_links SET expires_at='2000-01-01 00:00:00'")
    second = new_link(c, csrf)
    with sqlite3.connect(legacy.config['DATABASE']) as db:
        db.execute("UPDATE attach_links SET expires_at='2000-01-01 00:00:00'")
    assert claim(legacy, second).status_code == 410


def test_link_creation_rules(legacy):
    c = legacy.test_client(); csrf = login(c, learner(legacy, 'maker', onboarded=True))
    assert legacy.test_client().post('/api/app/attach-links', json={}).status_code in (400, 401)
    assert c.post('/api/app/attach-links', json={}).status_code == 400                     # CSRF
    assert post(c, '/api/app/attach-links', {'lesson_id': CLUB}, csrf).status_code == 403   # club lesson, free learner
    assert post(c, '/api/app/attach-links', {'lesson_id': 'missing'}, csrf).status_code == 404
    for _ in range(5):
        new_link(c, csrf)
    assert post(c, '/api/app/attach-links', {}, csrf).status_code == 429                   # too many unused links


def test_key_reads_and_writes_only_what_the_learner_can(legacy):
    c = legacy.test_client(); csrf = login(c, learner(legacy, 'keyholder', onboarded=True))
    c.get('/lessons/' + LESSON)
    key = key_of(claim(legacy, new_link(c, csrf, lesson_id=LESSON)).text)
    bot = agent(legacy, key)
    status = bot.get('/api/agent/status').json
    assert status['learner'] == 'keyholder' and status['current_lesson']['id'] == LESSON and status['next_url'].endswith('/lessons/' + LESSON)
    lesson = bot.get('/api/agent/lessons/' + LESSON).json
    assert lesson['task'] and lesson['checklist'] and lesson['sections'][-1]['title'] == 'Практика' and lesson['text']
    assert bot.get('/api/agent/lessons/' + CLUB).status_code == 403
    saved = bot.post(f'/api/agent/lessons/{LESSON}/practice', json={'body': 'Итог из Claude', 'status': 'submitted'})
    assert saved.status_code == 200 and saved.json['saved']['status'] == 'submitted'       # no CSRF: key, not cookies
    assert bot.post(f'/api/agent/lessons/{LESSON}/practice', json={'body': ' '}).status_code == 400
    assert bot.post(f'/api/agent/lessons/{LESSON}/step', json={'section': 2}).json['last'] == 2
    assert bot.post(f'/api/agent/lessons/{LESSON}/step', json={'section': 99}).status_code == 400
    assert bot.post(f'/api/lessons/{LESSON}/completion', json={'completed': True}).status_code == 400   # web API: no key access
    works = c.get('/api/app/profile').json['practices']
    assert works[0]['body'] == 'Итог из Claude' and works[0]['via'] == 'Claude'
    assert c.get('/api/app/lessons/' + LESSON).json['practice']['via'] == 'Claude'
    assert post(c, f'/api/lessons/{LESSON}/practice', {'body': 'Доработал сам', 'status': 'submitted'}, csrf).status_code == 200
    assert c.get('/api/app/lessons/' + LESSON).json['practice']['via'] is None               # the learner's own save replaces it
    # cookies never authenticate the agent API, and a web session never needs the key
    assert c.get('/api/agent/status').status_code == 401
    assert legacy.test_client().get('/api/agent/status', headers={'Authorization': 'Bearer as_000000000000_' + 'x' * 40}).status_code == 401


def test_revoked_or_expired_keys_stop_and_entitlements_are_live(legacy):
    c = legacy.test_client(); csrf = login(c, learner(legacy, 'revoker', onboarded=True))
    key = key_of(claim(legacy, new_link(c, csrf)).text)
    bot = agent(legacy, key)
    assert bot.get('/api/agent/status').status_code == 200
    connections = c.get('/api/app/connections').json['connections']
    assert len(connections) == 1 and connections[0]['label'] == 'Claude'
    assert c.delete('/api/app/connections/' + connections[0]['id']).status_code == 400          # CSRF
    other = legacy.test_client(); other_csrf = login(other, learner(legacy, 'stranger', onboarded=True))
    assert other.delete('/api/app/connections/' + connections[0]['id'], headers={'X-CSRF-Token': other_csrf}).status_code == 404
    assert c.delete('/api/app/connections/' + connections[0]['id'], headers={'X-CSRF-Token': csrf}).json['connections'] == []
    assert bot.get('/api/agent/status').status_code == 401
    key = key_of(claim(legacy, new_link(c, csrf)).text)
    with sqlite3.connect(legacy.config['DATABASE']) as db:
        db.execute("UPDATE connected_sessions SET expires_at='2000-01-01 00:00:00'")
    assert agent(legacy, key).get('/api/agent/status').status_code == 401
    # a member's key loses club lessons the moment the membership ends
    with sqlite3.connect(legacy.config['DATABASE']) as db:
        db.execute("UPDATE users SET entitlement='member' WHERE id='user-revoker'")
    key = key_of(claim(legacy, new_link(c, csrf)).text)
    member_bot = agent(legacy, key)
    assert member_bot.get('/api/agent/lessons/' + CLUB).status_code == 200
    with sqlite3.connect(legacy.config['DATABASE']) as db:
        db.execute("UPDATE users SET entitlement='expired' WHERE id='user-revoker'")
    assert member_bot.get('/api/agent/lessons/' + CLUB).status_code == 403


def test_mcp_tools(legacy):
    c = legacy.test_client(); csrf = login(c, learner(legacy, 'mcp', onboarded=True))
    c.get('/lessons/' + LESSON)
    bot = agent(legacy, key_of(claim(legacy, new_link(c, csrf, lesson_id=LESSON), **{'User-Agent': 'curl/8.7'}).text))
    assert legacy.test_client().post('/mcp', json={}).status_code == 401
    assert bot.get('/mcp').status_code == 405
    init = rpc(bot, 'initialize', {'protocolVersion': '2025-06-18', 'clientInfo': {'name': 'claude-code', 'version': '2'}, 'capabilities': {}}).json
    assert init['result']['serverInfo']['name'] == 'ai-room' and init['result']['protocolVersion'] == '2025-06-18'
    assert c.get('/api/app/connections').json['connections'][0]['label'] == 'Claude Code'
    assert bot.post('/mcp', json={'jsonrpc': '2.0', 'method': 'notifications/initialized'}).status_code == 202
    names = {t['name'] for t in rpc(bot, 'tools/list').json['result']['tools']}
    assert names == {'learning_status', 'get_lesson', 'next_step', 'save_practice', 'mark_section', 'review_checklist'}
    lesson = rpc(bot, 'tools/call', {'name': 'get_lesson', 'arguments': {}}).json['result']
    assert not lesson['isError'] and json.loads(lesson['content'][0]['text'])['id'] == LESSON
    saved = rpc(bot, 'tools/call', {'name': 'save_practice', 'arguments': {'lesson_id': LESSON, 'body': 'Черновик из MCP'}}).json['result']
    assert not saved['isError'] and c.get('/api/app/lessons/' + LESSON).json['practice']['body'] == 'Черновик из MCP'
    locked = rpc(bot, 'tools/call', {'name': 'get_lesson', 'arguments': {'lesson_id': CLUB}}).json['result']
    assert locked['isError'] and 'клуба' in locked['content'][0]['text']
    assert rpc(bot, 'resources/list').json['error']['code'] == -32601
    batch = bot.post('/mcp', json=[{'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}, {'jsonrpc': '2.0', 'method': 'notifications/x'}]).json
    assert batch == [{'jsonrpc': '2.0', 'id': 1, 'result': {}}]


def test_link_without_lesson_falls_back_to_status(app):
    c = app.test_client(); csrf = login(c)
    text = claim(app, new_link(c, csrf)).text
    assert 'нет начатого урока' in text and '/api/agent/status' in text


BROWSER = {'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8', 'Sec-Fetch-Mode': 'navigate',
           'User-Agent': 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141 Safari/537.36'}


def test_browsing_assistant_gets_a_page_and_can_save_with_the_form(legacy):
    # Assistants often open links in a real browser (the Claude app does): it must work there too.
    c = legacy.test_client(); csrf = login(c, learner(legacy, 'browser', onboarded=True))
    path = new_link(c, csrf, lesson_id=LESSON)
    page = legacy.test_client().get(path, headers=BROWSER)
    assert page.status_code == 200 and page.mimetype == 'text/html'
    html = page.text
    assert 'Первый полезный результат за 20 минут' in html and 'Критерии хорошего результата' in html and 'Текст урока' in html
    assert f'action="/api/agent/lessons/{LESSON}/practice"' in html
    key = re.search(r'name="key" value="(as_[\w-]+)"', html)[1]
    assert legacy.test_client().get(path, headers=BROWSER).status_code == 409          # used up by the browser visit
    saved = legacy.test_client().post(f'/api/agent/lessons/{LESSON}/practice', data={'key': key, 'body': 'Итог из браузера', 'status': 'submitted'})
    assert saved.status_code == 200 and 'Работа сохранена' in saved.text
    practice = c.get('/api/app/lessons/' + LESSON).json['practice']
    assert practice['body'] == 'Итог из браузера' and practice['status'] == 'submitted' and practice['via'] == 'ИИ-ассистент'
    # the form needs the key: the learner's own cookies don't count on agent endpoints
    assert c.post(f'/api/agent/lessons/{LESSON}/practice', data={'body': 'x', 'status': 'draft', 'csrf': csrf}).status_code == 401
    assert legacy.test_client().post(f'/api/agent/lessons/{LESSON}/practice', data={'key': key[:-3] + 'abc', 'body': 'x'}).status_code == 401
