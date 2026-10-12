"""Onboarding v2 (club/onboarding.py, club/journey.py): who is sent there, and the answers that build a path."""
import sqlite3

import pytest
from werkzeug.security import generate_password_hash

from test_learning import app, login, post, token, PASSWORD, FREE, PAID
from test_skills import skills


@pytest.fixture()
def onboard(skills):
    result = skills.test_cli_runner().invoke(args=['init-onboarding'])
    assert result.exit_code == 0, result.output
    return skills


def put(c, csrf, data):
    return c.put('/api/app/journey', json=data, headers={'X-CSRF-Token': csrf})


def newcomer(app, name='newcomer', role='learner', entitlement='free'):
    """A real account (not a seeded fixture): it hasn't been through the onboarding."""
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute('INSERT INTO users(id,email,password_hash,name,role,entitlement) VALUES(?,?,?,?,?,?)',
                   ('user-' + name, name + '@example.test', generate_password_hash(PASSWORD), name.title(), role, entitlement))
    return name


def test_newcomers_meet_the_onboarding_first_but_links_still_open(app):
    c = app.test_client()
    response = c.post('/login', data={'email': newcomer(app) + '@example.test', 'password': PASSWORD, 'csrf': token(c)})
    assert response.location == '/onboarding'
    assert c.get('/discover').location == '/onboarding' and c.get('/map').location == '/onboarding'
    assert c.get('/api/app/discover').status_code == 409
    assert c.get('/lessons/' + FREE).status_code == 200            # a shared link never lands on a questionnaire
    assert c.get('/onboarding').status_code == 200
    # Someone who logs in from a lesson link goes back to the lesson.
    other = app.test_client()
    response = other.post('/login', query_string={'next': '/lessons/' + FREE},
                          data={'email': newcomer(app, 'linked') + '@example.test', 'password': PASSWORD, 'csrf': token(other)})
    assert response.location == '/lessons/' + FREE
    # Editors and admins are never sent there, but can open it.
    staff = app.test_client(); login(staff, 'admin')
    assert staff.get('/discover').status_code == 200 and staff.get('/onboarding').status_code == 200


def test_goals_level_deadlines_and_pace_build_and_save_a_path(app):
    c = app.test_client(); csrf = login(c, newcomer(app))
    options = c.get('/api/app/journey').json
    assert options['status'] == 'new' and len(options['options']['goals']) == 10 and options['path'] is None
    preview = lambda body: c.post('/api/app/journey/preview', json=body, headers={'X-CSRF-Token': csrf})
    assert preview({'goals': []}).status_code == 400
    assert preview({'goals': ['startup', 'creator', 'lead', 'it']}).status_code == 400          # up to three
    assert preview({'goals': ['no-such-goal']}).status_code == 400
    path = preview({'goals': ['startup', 'creator'], 'beginner': True, 'deadlines': {'creator': 4, 'startup': 52}}).json['path']
    assert [g['id'] for g in path['goals']] == ['creator', 'startup']                            # the sooner deadline first
    assert path['goals'][0]['color'] != path['goals'][1]['color'] and all(g['modules'] for g in path['goals'])
    assert len(path['plans']['options']) == 3 and path['plans']['needed_minutes_per_week']
    # A learner who already works with images starts further along the creator goal.
    skilled = preview({'goals': ['creator'], 'beginner': False, 'sliders': {'media': 4}}).json['path']
    beginner = preview({'goals': ['creator'], 'beginner': True}).json['path']
    assert len(skilled['lessons']) < len(beginner['lessons'])
    # Drafts are saved step by step; finishing unlocks the site.
    assert put(c, csrf, {'goals': ['startup'], 'step': 'level'}).json['status'] == 'draft'
    assert c.get('/discover').location == '/onboarding'
    assert put(c, csrf, {'pace': {'sessions': 9, 'session_minutes': 30}}).status_code == 400
    done = put(c, csrf, {'pace': {'sessions': 4, 'session_minutes': 30}, 'status': 'done'}).json
    assert done['status'] == 'done' and done['path']['timeline'] and done['answers']['goals'] == ['startup']
    assert c.get('/discover').status_code == 200 and c.get('/path').status_code == 200
    assert c.get('/api/app/journey').json['path']['goals'][0]['id'] == 'startup'
    # The chosen pace is the study plan until days are picked: 4 sessions of 30 minutes.
    assert c.get('/api/app/plan').json == {'days': [1, 2, 4, 6], 'time': '19:00', 'minutes': 30}
    plan = c.put('/api/app/plan', json={'days': [2, 5], 'time': '08:00'}, headers={'X-CSRF-Token': csrf}).json
    assert plan == {'days': [2, 5], 'time': '08:00', 'minutes': 30}


def test_skipping_and_a_goal_in_own_words(app):
    c = app.test_client(); csrf = login(c, newcomer(app))
    assert put(c, csrf, {'custom': 'Хочу открыть студию ИИ-видео для свадеб'}).status_code == 200
    custom = c.get('/api/app/journey/custom')
    assert custom.status_code == 402 and custom.json['message'] == 'Нужна подписка для анализа'
    assert custom.json['custom'].startswith('Хочу открыть')
    assert put(c, csrf, {'status': 'skipped'}).json['status'] == 'skipped'
    assert c.get('/discover').status_code == 200
    # Without goals there is nothing to finish.
    other = app.test_client(); other_csrf = login(other, newcomer(app, 'empty'))
    assert put(other, other_csrf, {'status': 'done'}).status_code == 400


def test_journey_needs_an_account_and_csrf(app):
    c = app.test_client()
    assert c.get('/api/app/journey').status_code == 401
    login(c, newcomer(app))
    assert c.put('/api/app/journey', json={'goals': ['startup']}).status_code == 400   # no CSRF token
