import sqlite3

import pytest
from club import create_app
from club.legacy_content import render_blocks
from werkzeug.security import generate_password_hash
from test_learning import app, login, post, token, PASSWORD
from test_skills import skills
from test_onboarding import onboard, put

FIRST = 'claude-first-result'
MEMBER = 'claude-basics-context'


@pytest.fixture()
def legacy(onboard):
    result = onboard.test_cli_runner().invoke(args=['install-legacy-lessons'])
    assert result.exit_code == 0, result.output
    return onboard


def learner(app, name, onboarded=False):
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("INSERT INTO users(id,email,password_hash,name,onboarding_done) VALUES(?,?,?,?,?)",
                   ('user-'+name, name+'@example.test', generate_password_hash(PASSWORD), name, int(onboarded)))
    return name


def form(client, path, data, csrf):
    return client.post(path, data=dict(data, csrf=csrf))


def demo_app(legacy):
    return create_app(dict(TESTING=True, DATABASE=legacy.config['DATABASE'], SECRET_KEY='test-only-key', DEMO_CHECKOUT=True))


def test_install_is_repeatable_and_keeps_learner_work(legacy):
    c = legacy.test_client(); csrf = login(c)
    assert post(c, '/api/lessons/'+FIRST+'/practice', {'body': 'мой рабочий запрос', 'status': 'submitted'}, csrf).status_code == 200
    assert legacy.test_cli_runner().invoke(args=['install-legacy-lessons', '--retire-synthetic']).exit_code == 0
    with sqlite3.connect(legacy.config['DATABASE']) as db:
        assert db.execute('SELECT body FROM practice WHERE lesson_id=?', (FIRST,)).fetchone()[0] == 'мой рабочий запрос'
        assert db.execute("SELECT status FROM courses WHERE id='ai-foundations'").fetchone()[0] == 'archived'
        assert db.execute("SELECT COUNT(*) FROM lessons WHERE access='member' AND id IN (SELECT lesson_id FROM lesson_profiles WHERE demo=0)").fetchone()[0] == 0


def test_rich_lesson_renders_blocks_and_embeds(legacy):
    c = legacy.test_client()
    page = c.get('/lessons/'+FIRST)
    assert page.status_code == 200
    assert 'https://airoom-storage.s3.twcstorage.ru' in page.headers['Content-Security-Policy']
    lesson = c.get('/api/app/lessons/'+FIRST).json['lesson']
    assert '<h2 id="step-1">Шаг 1. Достаём задачу (2 минуты)</h2>' in lesson['body_html']
    assert lesson['steps'][0] == 'Шаг 1. Достаём задачу (2 минуты)' and lesson['task']   # "В этом уроке" + Практика
    assert 'class="lesson-example"' in lesson['body_html'] and 'https://kinescope.io/embed/' in lesson['body_html']
    assert lesson['paragraphs'] is None   # no plain-text "Разбираемся на примере" section


def test_renderer_escapes_and_drops_unlisted_sources():
    html = render_blocks('<script>x</script> **жирный** [ok](https://example.com) [bad](javascript:alert(1))\n\n'
                         '![](https://evil.example/x.png)\n\n@video https://evil.example/embed/1\n\n```\n<b>prompt</b>\n```')
    assert '&lt;script&gt;' in html and '<strong>жирный</strong>' in html
    assert 'href="https://example.com"' in html and 'href="javascript' not in html
    assert 'evil.example' not in html
    assert '<pre>&lt;b&gt;prompt&lt;/b&gt;</pre>' in html


def test_paywall_shows_outline_and_offer_without_content(legacy):
    anonymous = legacy.test_client()
    assert anonymous.get('/lessons/'+MEMBER).status_code == 403
    data = anonymous.get('/api/app/lessons/'+MEMBER).json
    assert data['locked'] and 'Четыре слоя контекста' in data['lesson']['steps']
    assert 'Демонстрационный текст раздела' not in str(data) and 'body_html' not in data['lesson']
    assert data['entitlement'] is None and data['free_lesson']['id'] == FIRST   # "Я уже в клубе — войти" + free lesson link
    c = legacy.test_client(); login(c)
    assert c.get('/api/lessons/'+MEMBER).status_code == 403


def test_demo_checkout_is_off_unless_configured(legacy):
    c = legacy.test_client(); csrf = login(c)
    assert form(c, '/membership/demo', {'next': '/lessons/'+MEMBER}, csrf).status_code == 404
    assert 'Оплата в этой версии пока не подключена' in c.get('/membership').text


def test_demo_checkout_switches_access_both_ways(legacy):
    app = demo_app(legacy)
    c = app.test_client(); csrf = login(c, learner(app, 'buyer', onboarded=True))
    response = form(c, '/membership/demo', {'next': '/lessons/'+MEMBER}, csrf)
    assert response.status_code == 302 and response.headers['Location'].endswith('/lessons/'+MEMBER)
    assert c.get('/lessons/'+MEMBER).status_code == 200
    response = form(c, '/membership/demo/cancel', {'next': 'https://evil.example/'}, csrf)
    assert response.headers['Location'].endswith('/membership')
    assert c.get('/lessons/'+MEMBER).status_code == 403
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE users SET onboarding_done=1 WHERE id='user-revoked'")
    revoked = app.test_client(); csrf = login(revoked, 'revoked')
    assert form(revoked, '/membership/demo', {}, csrf).status_code == 403
    locked = revoked.get('/api/app/lessons/'+MEMBER).json
    assert locked['locked'] and locked['entitlement'] == 'revoked'   # "Доступ к клубу приостановлен"


def recommendation(app, who, draft):
    c = app.test_client(); csrf = login(c, learner(app, who))
    state = c.get('/api/onboarding').json
    state = put(c, csrf, state, 'next').json
    assert 'revision' in state, state
    state = put(c, csrf, state, 'next', draft={'interests': draft.get('interests', [])}).json
    state = put(c, csrf, state, 'next', draft={k: v for k, v in draft.items() if k != 'interests'}).json
    return state['recommendation']


def test_recommendation_follows_interests_level_and_time(legacy):
    pick = recommendation(legacy, 'novice', {'interests': ['content', 'automation'], 'experience': 'beginner', 'available_minutes': 5})
    assert pick['lesson_id'] == 'chatcut-video-editing' and 'interest' in pick['reasons']
    assert recommendation(legacy, 'agent-fan', {'interests': ['agents']})['lesson_id'] == 'what-is-ai-agent'
    assert recommendation(legacy, 'undecided', {})['lesson_id'] == FIRST
