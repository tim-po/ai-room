
from test_learning import app, login, post
from test_skills import skills
from test_onboarding import onboard
from test_legacy_content import legacy, learner


def tree(client):
    assert client.get('/map').status_code == 200
    return client.get('/api/app/home').json['tree']


def lessons(data, course=None):
    return {l['title']: l for t in data['topics'] for c in t['courses'] if course in (None, c['id'])
            for m in c['modules'] for l in m['lessons']}


def test_tree_covers_catalog_and_marks_lesson_states(legacy):
    data = tree(legacy.test_client())
    assert [t['title'] for t in data['topics']] == ['Основы ИИ', 'Код', 'Контент', 'Агенты']
    by_title = lessons(data, 'claude-basics')
    assert by_title['Первый полезный результат за 20 минут']['state'] == 'open'
    assert by_title['Формула рабочего запроса']['state'] == 'locked'
    assert by_title['Инструкции проекта']['state'] == 'coming' and by_title['Инструкции проекта']['id'] is None
    claude = data['topics'][0]['courses'][0]
    assert claude['url'] == '/courses/claude-basics' and claude['available'] == 3 and claude['total'] == 37
    assert data['topics'][1]['courses'][0]['url'] is None


def test_tree_reflects_progress_and_current_lesson(legacy):
    c = legacy.test_client(); csrf = login(c, learner(legacy, 'mapper', onboarded=True))
    c.get('/lessons/what-is-ai-agent')
    post(c, '/api/lessons/claude-first-result/completion', {'completed': True}, csrf)
    by_title = lessons(tree(c))
    assert by_title['Первый полезный результат за 20 минут']['state'] == 'done'
    agent = by_title['Что такое ИИ-агент и как он может работать за тебя']
    assert agent['state'] == 'progress' and agent['current']


def test_course_page_and_library_match_the_map(legacy):
    c = legacy.test_client()
    assert c.get('/courses/claude-basics').status_code == 200
    course = c.get('/api/app/courses/claude-basics').json
    outline = course['outline']
    assert (outline['available'], outline['total']) == (3, 37) and 'Синтетическая' not in str(course)   # "Открыто 3 из 37 уроков"
    assert 'Инструкции проекта' in [l['title'] for m in outline['modules'] for l in m['lessons']]
    library = c.get('/api/app/catalogue').json
    assert 'ChatGPT с 0 до PRO' in [c['title'] for c in library['coming']]   # "Скоро в AI Room"
    card = next(c for c in library['courses'] if c['id'] == 'claude-basics')
    assert (card['total'], card['catalog_total']) == (3, 37)   # "открыто 3 из 37 уроков"


def test_retired_pages_redirect_and_settings_page_is_simple(legacy):
    c = legacy.test_client(); login(c, learner(legacy, 'tidy', onboarded=True))
    for path, target in [('/practice', '/profile#practice'), ('/challenges', '/'), ('/diagnostic', '/'), ('/routes', '/')]:
        response = c.get(path)
        assert response.status_code == 302 and response.headers['Location'].endswith(target)
    assert c.get('/preferences').status_code == 200
    assert set(c.get('/api/app/preferences').json) == {'goal', 'experience', 'weekly_goal', 'plan'}
