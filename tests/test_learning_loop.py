"""The loop around lessons: sections reached, the learner's plan and calendar, the return briefing."""
import sqlite3

from test_learning import app, login, post
from test_skills import skills
from test_onboarding import onboard
from test_legacy_content import legacy, learner, MEMBER

LESSON = 'claude-first-result'   # rich lesson with sections and a practice task


def step(client, csrf, lesson, value):
    return post(client, f'/api/lessons/{lesson}/step', {'step': value}, csrf)


def put_plan(client, csrf, **plan):
    return client.put('/api/app/plan', json=plan, headers={'X-CSRF-Token': csrf})


def test_sections_reached_are_kept_and_offered_for_resuming(legacy):
    c = legacy.test_client(); csrf = login(c, learner(legacy, 'reader', onboarded=True))
    assert c.get('/lessons/' + LESSON).status_code == 200   # opening the lesson starts it
    data = c.get('/api/app/lessons/' + LESSON).json
    total = len(data['checkpoints'])
    assert data['checkpoints'][-1] == 'Практика' and data['checkpoints'][:-1] == data['lesson']['steps']
    assert data['step_progress'] is None
    assert step(c, csrf, LESSON, 4).json['furthest'] == 4
    back = step(c, csrf, LESSON, 2).json
    assert (back['furthest'], back['last']) == (4, 2)   # going back keeps the furthest point
    for bad in [0, total + 1, '3', 2.5, None]:
        assert step(c, csrf, LESSON, bad).status_code == 400
    assert step(c, csrf, MEMBER, 1).status_code == 403   # club lesson for a free learner
    assert c.post(f'/api/lessons/{LESSON}/step', json={'step': 1}).status_code == 400   # CSRF
    assert legacy.test_client().post(f'/api/lessons/{LESSON}/step', json={'step': 1}).status_code in (400, 401)
    briefing = c.get('/api/app/home').json['briefing']
    assert briefing['url'] == f'/lessons/{LESSON}#step-2' and briefing['step'] == {'index': 2, 'total': total, 'title': data['checkpoints'][1]}
    assert c.get('/continue').location.endswith(f'/lessons/{LESSON}#step-2')
    step(c, csrf, LESSON, total)
    assert c.get('/api/app/home').json['briefing']['url'] == f'/lessons/{LESSON}#practice'
    assert post(c, f'/api/lessons/{LESSON}/practice', {'body': 'черновик', 'status': 'draft'}, csrf).status_code == 200
    draft = c.get('/api/app/profile').json['briefing']
    assert draft['status'] == 'draft' and draft['url'].endswith('#practice') and draft['practice']['excerpt'] == 'черновик'


def test_briefing_turns_into_a_welcome_back_after_a_break(legacy):
    c = legacy.test_client(); csrf = login(c, learner(legacy, 'away', onboarded=True))
    assert c.get('/api/app/home').json['briefing'] is None   # nothing started yet
    c.get('/lessons/' + LESSON)                              # a visit is a learning day
    step(c, csrf, LESSON, 3)
    assert c.get('/api/app/home').json['briefing']['returning'] is False
    with sqlite3.connect(legacy.config['DATABASE']) as db:
        db.execute("UPDATE learning_days SET day=date('now','-5 days') WHERE user_id='user-away'")
        db.execute("UPDATE visit_days SET day=date('now','-5 days') WHERE user_id='user-away'")   # a visit counts as being here
    briefing = c.get('/api/app/home').json['briefing']
    assert briefing['returning'] and briefing['away_days'] == 5 and briefing['steps'][2] == briefing['step']['title']
    assert legacy.test_client().get('/api/app/home').json['briefing'] is None


def test_plan_sets_the_weekly_goal_and_exports_a_calendar(legacy):
    c = legacy.test_client(); csrf = login(c, learner(legacy, 'planner', onboarded=True))
    assert c.get('/api/app/plan').json == {'days': [], 'time': '19:00', 'minutes': 20}
    assert c.get('/plan.ics').status_code == 404   # no days chosen yet
    for bad in [dict(days=[0], time='19:00'), dict(days=[8], time='19:00'), dict(days=[2, 2], time='19:00'),
                dict(days=['2'], time='19:00'), dict(days=[2], time='7pm'), dict(days=[2], time='24:00'), dict(days=[2])]:
        assert put_plan(c, csrf, **bad).status_code == 400, bad
    assert c.put('/api/app/plan', json=dict(days=[2], time='19:00')).status_code == 400   # CSRF
    assert put_plan(c, csrf, days=[4, 2], time='07:30').json == {'days': [2, 4], 'time': '07:30', 'minutes': 20}
    assert c.get('/api/app/preferences').json['weekly_goal'] == 2
    assert c.get('/api/app/profile').json['plan']['days'] == [2, 4]
    ics = c.get('/plan.ics')
    lines = ics.text.split('\r\n')
    assert ics.mimetype == 'text/calendar' and 'attachment' in ics.headers['Content-Disposition']
    assert 'RRULE:FREQ=WEEKLY;BYDAY=TU,TH' in lines and 'URL:http://localhost/continue' in lines
    start = next(l for l in lines if l.startswith('DTSTART:'))
    assert start.endswith('T073000') and not start.endswith('Z')   # floating local time
    assert all(len(l.encode()) <= 75 for l in lines)
    assert put_plan(c, csrf, days=[], time='07:30').json['days'] == []   # no plan: "when it suits me"
    assert c.get('/api/app/preferences').json['weekly_goal'] == 0
    with sqlite3.connect(legacy.config['DATABASE']) as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE user_id='user-planner' AND name='plan_saved'").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM events WHERE user_id='user-planner' AND name='plan_calendar'").fetchone()[0] == 1
    assert legacy.test_client().get('/plan.ics').status_code == 302   # sign in first


def test_lesson_data_offers_the_next_lesson_for_the_finish_moment(legacy):
    c = legacy.test_client(); login(c, learner(legacy, 'finisher', onboarded=True))
    following = c.get('/api/app/lessons/' + LESSON).json['following']
    assert following['objective'] and following['minutes'] > 0 and following['locked']   # next one is a club lesson
    assert c.get('/continue').location == c.get('/api/app/home').json['next']['url']   # nothing started: the recommended lesson


def test_preferences_accept_any_number_of_plan_days(app):
    c = app.test_client(); csrf = login(c)
    assert c.post('/preferences', data={'csrf': csrf, 'goal': 'work', 'experience': 'beginner', 'weekly_goal': '4'}).status_code == 302
    assert c.post('/preferences', data={'csrf': csrf, 'goal': 'work', 'experience': 'beginner', 'weekly_goal': '8'}).status_code == 400


def test_sections_and_continue_count_as_learning_and_show_on_the_dashboard(legacy):
    c = legacy.test_client(); csrf = login(c, learner(legacy, 'counted', onboarded=True))
    c.get('/lessons/' + LESSON)
    with sqlite3.connect(legacy.config['DATABASE']) as db:
        assert db.execute("SELECT COUNT(*) FROM learning_days WHERE user_id='user-counted'").fetchone()[0] == 0   # a visit isn't learning
    step(c, csrf, LESSON, 2); step(c, csrf, LESSON, 1); step(c, csrf, LESSON, 2)
    put_plan(c, csrf, days=[1], time='08:00'); c.get('/plan.ics'); c.get('/continue')
    with sqlite3.connect(legacy.config['DATABASE']) as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE user_id='user-counted' AND name='section_reached'").fetchone()[0] == 1   # new sections only
        assert db.execute("SELECT COUNT(*) FROM learning_days WHERE user_id='user-counted'").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM events WHERE user_id='user-counted' AND name='continue_opened'").fetchone()[0] == 1
    admin = legacy.test_client(); login(admin, 'admin')
    report = admin.get('/api/admin/analytics').json
    assert {f['label']: f['learners'] for f in report['loop']['features']}['Выбрали план занятий'] == 1
