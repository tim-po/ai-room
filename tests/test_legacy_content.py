import sqlite3

import pytest
from club import create_app
from club.legacy_content import legacy_materials, club_materials, render_blocks
from werkzeug.security import generate_password_hash
from test_learning import app, login, post, token, PASSWORD
from test_skills import skills
from test_onboarding import onboard

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
        # Synthetic materials are archived; the imported free guides and use cases stay published.
        published = {r[0] for r in db.execute("SELECT id FROM materials WHERE status='published'")}
        assert published == {meta['id'] for meta, _ in legacy_materials()} | {i['id'] for i in club_materials()} and published
        # Club materials are listings only: a member page that links to the original, no paid text.
        club = db.execute("SELECT access,body FROM materials WHERE id='claude-za-3-dnya'").fetchone()
        assert club[0] == 'member' and 'app.airoom.club/workshops/claude-za-3-dnya' in club[1] and '## Программа' in club[1]
        free = {meta['id'] for meta, _ in legacy_materials()}
        assert {r[0] for r in db.execute("SELECT DISTINCT access FROM materials WHERE status='published' AND id IN (%s)" % ','.join('?' * len(free)), tuple(free))} == {'free'}


def test_imported_guides_render_and_link_inside_the_platform(legacy):
    c = legacy.test_client()
    guide = c.get('/api/app/materials/claude-for-beginners').json
    assert not guide['locked'] and guide['item']['format'] == 'guide'
    html = guide['item']['body_html']
    assert '<h2 id="step-1">' in html and 'data-copy-block' in html and '<script' not in html
    assert '<a href="/courses/claude-basics">' in html            # the old platform's course link points here now
    assert guide['item']['steps'][0].startswith('01.')
    case = c.get('/api/app/materials/case-higgsfield').json['item']
    assert case['format'] == 'use_case' and 'kinescope.io/embed/' in case['body_html']
    # Old-club promotion (payment links, the old price) is not carried over.
    for meta, body in legacy_materials():
        assert 'tribute' not in body and 'AI Room Club' not in body and '1490 руб' not in body, meta['id']
    shelves = {s['id']: s for s in c.get('/api/app/discover').json['shelves']}
    assert {'guide', 'use_case'} <= set(shelves)
    assert next(i for i in shelves['use_case']['items'] if i['id'] == 'case-higgsfield')['topic_id'] == 'content'


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
    assert c.get('/api/app/membership').json['demo'] is False   # "Оплата в этой версии пока не подключена"


def test_demo_checkout_switches_access_both_ways(legacy):
    app = demo_app(legacy)
    c = app.test_client(); csrf = login(c, learner(app, 'buyer', onboarded=True))
    response = form(c, '/membership/demo', {'next': '/lessons/'+MEMBER}, csrf)
    assert response.status_code == 302 and response.headers['Location'].endswith('/lessons/'+MEMBER)
    assert c.get('/lessons/'+MEMBER).status_code == 200
    response = form(c, '/membership/demo/cancel', {'next': 'https://evil.example/'}, csrf)
    assert response.headers['Location'].endswith('/membership')
    assert c.get('/lessons/'+MEMBER).status_code == 403
    switched = post(c, '/membership/demo', {'next': '/lessons/'+MEMBER}, csrf).json   # the app switches with JSON
    assert switched['entitlement'] == 'member' and switched['next'] == '/lessons/'+MEMBER and 'Оплата не списывалась' in switched['message']
    assert post(c, '/membership/demo/cancel', {}, csrf).json['next'] == '/membership'
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE users SET onboarding_done=1 WHERE id='user-revoked'")
    revoked = app.test_client(); csrf = login(revoked, 'revoked')
    assert form(revoked, '/membership/demo', {}, csrf).status_code == 403
    locked = revoked.get('/api/app/lessons/'+MEMBER).json
    assert locked['locked'] and locked['entitlement'] == 'revoked'   # "Доступ к клубу приостановлен"


def journey(app, who, answers):
    c = app.test_client(); csrf = login(c, learner(app, who))
    return c.post('/api/app/journey/preview', json=answers, headers={'X-CSRF-Token': csrf}).json['path']


def test_paths_follow_goals_through_the_real_lessons(legacy):
    """Onboarding v2: the path for a goal runs through the lessons that teach what it needs, with real titles."""
    creator = journey(legacy, 'novice', {'goals': ['creator'], 'beginner': True})
    assert {'AI-аватар в HeyGen', 'Popcorn: из одного фото целая серия'} <= {l['title'] for l in creator['lessons']}   # the app's real outline
    assert all(l['url'] for l in creator['lessons'] if l['lesson_id'])
    assert creator['goals'][0]['reach'] == 1 and creator['coming'] > 0
    agents = journey(legacy, 'agent-fan', {'goals': ['agentic'], 'beginner': True})
    assert 'Личный ассистент на Hermes' in {l['title'] for l in agents['lessons']}
    # Someone who already works with chats starts further along: a shorter path to the same goal.
    everyday = journey(legacy, 'undecided', {'goals': ['everyday'], 'beginner': True})
    skilled = journey(legacy, 'skilled', {'goals': ['everyday'], 'beginner': False, 'sliders': {'chat': 4}})
    assert 0 < len(skilled['lessons']) < len(everyday['lessons'])


def test_goals_show_across_the_platform_and_guides_join_the_path(legacy):
    """Guides that train what a goal needs are side stops on the path; Обзор marks what serves each goal."""
    c = legacy.test_client(); csrf = login(c, learner(legacy, 'aimer', onboarded=True))
    saved = c.put('/api/app/journey', json={'goals': ['everyday', 'agentic'], 'beginner': True}, headers={'X-CSRF-Token': csrf}).json
    guides = {g['id']: g for g in saved['path']['guides']}
    assert 'what-is-ai-agent' in guides and 'agentic' in guides['what-is-ai-agent']['goals']
    assert all(g['url'].startswith('/materials/') for g in guides.values())
    discover = c.get('/api/app/discover').json
    assert [g['id'] for g in discover['goals']] == ['everyday', 'agentic']
    items = [i for s in discover['shelves'] for i in s['items']]
    assert any(i['id'] == 'claude-first-result' and i.get('goals') for i in items)
    assert discover['shelves'][0]['id'] in ('goals', 'continue') and any(s['id'] == 'goals' for s in discover['shelves'])
    # Without goals nothing is marked.
    other = legacy.test_client(); login(other, learner(legacy, 'nogoals', onboarded=True))
    assert other.get('/api/app/discover').json['goals'] == []
