"""Обзор and search: shelves and ranked results over lessons, courses, materials and what's coming,
metadata only. Also the profile's club section, the first page's embedded data and static caching."""

from test_learning import app, login, post
from test_skills import skills
from test_onboarding import onboard
from test_legacy_content import legacy, learner, demo_app, FIRST, MEMBER
from test_spa import bootstrap

PRIVATE = ('body', 'prompt', 'task', 'checklist', 'video')


def shelves(data):
    return {s['id']: s for s in data['shelves']}


def items(data):
    return [i for s in data['shelves'] for i in s['items']] + data['hero']


def test_discover_shows_metadata_only_shelves(legacy):
    data = legacy.test_client().get('/api/app/discover').json
    found = shelves(data)
    assert {'free', 'courses', 'coming', 'club'} <= set(found) and 'continue' not in found
    assert data['hero'] and data['topics'] and {c['id'] for c in data['classes']} >= {'lesson', 'course', 'coming'}
    assert not any(s['style'] == 'top' for s in data['shelves'])           # no ranking without learners
    placed = [(i['kind'], i.get('id') or i['title']) for s in data['shelves'] for i in s['items']]
    assert len(placed) == len(set(placed))                                   # each item on one shelf
    assert FIRST in {i['id'] for i in found['free']['items']}
    assert all(i['state'] == 'locked' for i in found['club']['items']) and MEMBER in {i['id'] for i in found['club']['items']}
    for item in items(data):
        assert not set(PRIVATE) & set(item), item
    assert all(i['kind'] == 'coming' and i['url'].startswith('/map#course-') for i in found['coming']['items'])


def test_discover_continues_where_the_learner_is(legacy):
    c = legacy.test_client(); csrf = login(c, learner(legacy, 'returning', onboarded=True))
    assert post(c, '/api/app/lessons/' + FIRST + '/visit', {}, csrf).status_code == 200
    data = c.get('/api/app/discover').json
    found = shelves(data)
    assert found['continue']['items'][0]['id'] == FIRST and found['continue']['items'][0]['resume'] == 'started'
    assert FIRST not in {i['id'] for i in data['hero']}                       # the hero shows what to start next
    assert FIRST not in {i['id'] for i in found.get('free', {'items': []})['items']}


def test_search_ranks_filters_and_hides_content(legacy):
    c = legacy.test_client()
    agents = c.get('/api/app/search', query_string={'q': 'агенты'}).json
    assert agents['stems'] == ['аген'] and agents['total'] > 3
    assert agents['items'][0]['kind'] in ('course', 'lesson') and 'агент' in agents['items'][0]['title'].lower()
    assert all(i['kind'] == 'course' for i in c.get('/api/app/search', query_string={'q': 'агент', 'class': 'course'}).json['items'])
    free = c.get('/api/app/search', query_string={'access': 'free'}).json['items']
    assert free and all(i['access'] == 'free' for i in free)
    everything = c.get('/api/app/search', query_string={'topic': 'agents'}).json['items']
    assert everything and all(i['topic_id'] == 'agents' for i in everything)
    assert not any(i.get('sub') == 'lesson' for i in everything)                 # coming lessons only for a query
    assert c.get('/api/app/search', query_string={'q': 'zzzzqqq'}).json['total'] == 0
    for item in agents['items']:
        assert not set(PRIVATE) & set(item)


def test_pages_embed_their_first_data(legacy):
    c = legacy.test_client()
    assert bootstrap(c.get('/discover'))['page']['url'] == '/api/app/discover'
    page = bootstrap(c.get('/catalogue?q=%D0%B2%D0%B8%D0%B4%D0%B5%D0%BE'))['page']   # old links show Обзор
    assert page['url'] == '/api/app/search?q=%D0%B2%D0%B8%D0%B4%D0%B5%D0%BE' and page['data']['total'] > 0
    lesson = bootstrap(c.get('/lessons/' + FIRST))['page']
    assert lesson['url'] == '/api/app/lessons/' + FIRST and lesson['data']['lesson']['id'] == FIRST
    assert bootstrap(c.get('/lessons/missing'))['page'] is None
    locked = bootstrap(c.get('/lessons/' + MEMBER))['page']['data']            # the paywall's outline, never content
    assert locked['locked'] and not set(PRIVATE) & set(locked['lesson'])


def test_static_files_are_versioned_and_cached(legacy):
    c = legacy.test_client()
    html = c.get('/discover').text
    assert '/static/ui.css?v=' in html and 'href="/static/fonts/GolosText.woff2"' in html
    url = html.split('/static/ui.css?v=')[1].split('"')[0]
    assert 'immutable' in c.get('/static/ui.css?v=' + url).headers['Cache-Control']
    font = legacy.test_client().get('/static/fonts/GolosText.woff2')
    assert font.headers['Cache-Control'] == 'public, max-age=86400'
    assert 'Set-Cookie' not in font.headers and 'Cookie' not in font.headers.get('Vary', '')   # a cookie would stop edge caching
    assert c.get('/api/app/discover').headers['Cache-Control'] == 'private, no-store'
    assert 'immutable' not in c.get('/static/missing.css?v=1').headers.get('Cache-Control', '')   # errors aren't kept


def test_profile_holds_the_club(legacy):
    app = demo_app(legacy)
    c = app.test_client(); csrf = login(c, learner(app, 'clubber', onboarded=True))
    profile = c.get('/api/app/profile').json
    assert profile['club']['demo'] is True and profile['club']['member_lessons'] > 0
    assert set(profile['stats']) == {'lessons_done', 'works', 'days'}
    switched = post(c, '/membership/demo', {'next': '/profile'}, csrf).json        # switched from the profile, back to it
    assert switched['next'] == '/profile' and c.get('/api/app/profile').json['user']['entitlement'] == 'member'
