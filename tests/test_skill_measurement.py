import json
import sqlite3

from test_learning import app, login, post
from test_skills import skills, install_form, fixture_form
from club.skills import publish_reviewed_form
from club.skill_seed import graph_fixture

URL = '/api/admin/measurement/skills?start=2020-01-01&end=2020-02-01'


def setup(skills):
    assert skills.test_cli_runner().invoke(args=['init-teaching']).exit_code == 0
    install_form(skills)


def report(client):
    login(client, 'admin')
    response = client.get('/api/admin/measurement/skills')
    assert response.status_code == 200, response.data
    return response.json


def test_access_dates_initialization_and_empty_denominators(app, skills):
    c = skills.test_client()
    assert c.get(URL).status_code == 401
    login(c)
    assert c.get(URL).status_code == 403
    login(c, 'editor')
    assert c.get(URL).status_code == 403
    login(c, 'admin')
    assert c.get(URL).status_code == 503
    setup(skills)
    for suffix in ('?start=garbage', '?start=2020-01-01&end=2022-01-01', '?start=2020-01-01&end=2020-01-01'):
        assert c.get('/api/admin/measurement/skills'+suffix).status_code == 400
    data = c.get(URL).json
    assert data['placement']['completion'] == dict(numerator=0, denominator=0, rate=None)
    assert data['cross_branch']['rate'] is None
    assert data['publication']['rate'] is None


def test_real_attempts_placement_exposure_credit_and_exploration(skills):
    setup(skills)
    c = skills.test_client(); csrf = login(c)
    d = post(c, '/api/skills/diagnostics', dict(request_id='metric-diagnostic', interests=[]), csrf).json
    a = post(c, '/api/skills/challenges', dict(assessment_id='test-form-v1', request_id='metric-attempt'), csrf).json
    for _ in range(2):
        assert post(c, '/api/skills/challenges/'+a['id']+'/submit', dict(answers={'q1':'check','q2':'check'}), csrf).status_code == 200
    assert post(c, '/api/skills/diagnostics/'+d['id']+'/advance', dict(revision=1, attempt_id=a['id']), csrf).status_code == 200
    b = post(c, '/api/skills/challenges', dict(assessment_id='test-form-v1', request_id='metric-practice'), csrf).json
    assert b['mode'] == 'practice'
    post(c, '/api/skills/challenges/'+b['id']+'/submit', dict(answers={'q1':'check','q2':'check'}), csrf)
    other = skills.test_client(); token = login(other, 'member')
    stopped = post(other, '/api/skills/diagnostics', dict(request_id='metric-stopped', interests=[]), token).json
    post(other, '/api/skills/diagnostics/'+stopped['id']+'/advance', dict(revision=1, skip=True), token)
    post(other, '/api/skills/diagnostics', dict(request_id='metric-unfinished', interests=[]), token)
    with sqlite3.connect(skills.config['DATABASE']) as db:
        for node in ('coding', 'content'):
            db.execute('INSERT INTO skill_explorations(user_id,node_id) VALUES(?,?)', ('user-member', node))
    data = report(c)
    assert data['placement'] == dict(started=3, completed=1, stopped=1, unfinished=1, unavailable=0,
                                    completion=dict(numerator=1, denominator=3, rate=1/3))
    assert data['challenges']['certification'] == dict(started=1, completed=1, unfinished=0, passed=1)
    assert data['challenges']['practice'] == dict(started=1, completed=1, unfinished=0, passed=1)
    assert data['evidence']['understanding'] == dict(unique_objective_revision_credits=1, learners=1)
    assert data['evidence']['application']['unique_objective_revision_credits'] == 0
    assert data['cross_branch']['denominator'] == 1
    assert data['cross_branch']['numerator'] == 0
    assert data['cross_branch']['exploration_learners'] == 1
    assert not any(key in json.dumps(data) for key in ('Проверить первоисточник', 'objective_scores', 'answers', 'user-learner'))


def test_multibranch_attempts_jobs_retries_and_distinct_publication(skills):
    setup(skills)
    with sqlite3.connect(skills.config['DATABASE']) as db:
        for node in ('coding.mobile.demonstrate', 'content.writing.demonstrate'):
            form = fixture_form()
            for item in form['items']:
                item['objective_id'] = node
                item['prompt'] += node
            publish_reviewed_form(db, id=node, graph=graph_fixture(), node_id=node, form=form, access='free', reviewer='user-admin')
        for index, (state, attempt) in enumerate([('ready', 2), ('failed', 3), ('blocked', 1), ('cancelled', 0), ('queued', 0)]):
            key = str(index)
            db.execute('INSERT INTO teaching_uploads(id,owner_id,request_id,filename,media_type,size,sha256) VALUES(?,?,?,?,?,?,?)',
                       (key, 'user-editor', key, 'PRIVATE.txt', 'text/plain', 1, 'hash'))
            db.execute('INSERT INTO teaching_jobs(id,upload_id,state,attempt) VALUES(?,?,?,?)', (key,key,state,attempt))
        for job, revision in [('0',1), ('0',2), ('1',1)]:
            db.execute('INSERT INTO teaching_drafts(job_id,revision,body,sources,release_id,provider,model) VALUES(?,?,?,?,?,?,?)',
                       (job,revision,'PRIVATE SOURCE','PRIVATE SOURCE','tree-2026-10-v1','fixture','fixture'))
        db.execute('INSERT INTO teaching_publications(job_id,draft_revision,lesson_id,release_id,reviewed_by,review_note) VALUES(?,?,?,?,?,?)',
                   ('0',2,'foundations-start-01','tree-2026-10-v1','user-admin','PRIVATE NOTE'))
    c = skills.test_client(); csrf = login(c)
    for node in ('coding.mobile.demonstrate', 'content.writing.demonstrate'):
        assert post(c, '/api/skills/challenges', dict(assessment_id=node,request_id='multi-'+node),csrf).status_code == 201
    data = report(c)
    assert data['cross_branch']['numerator'] == data['cross_branch']['denominator'] == 1
    assert data['challenges']['certification']['unfinished'] == 2
    assert data['processing']['jobs'] == 5
    assert data['processing']['readiness'] == dict(numerator=1,denominator=3,rate=1/3)
    assert data['processing']['retries'] == 3
    assert data['processing']['jobs_retried'] == 2
    assert data['publication'] == dict(numerator=1,denominator=2,rate=.5)
    assert 'PRIVATE' not in json.dumps(data)
    outside = c.get(URL).json
    assert outside['processing']['jobs'] == outside['publication']['denominator'] == 0


def test_application_credit_is_separate_and_retries_do_not_inflate(skills):
    from test_practical import setup_task, draft, save
    assert skills.test_cli_runner().invoke(args=['init-teaching']).exit_code == 0
    admin, at, task, _ = setup_task(skills)
    c = skills.test_client(); token = login(c)
    for index in range(2):
        submission = draft(c, token, task, 'metric-practical-'+str(index)).json
        save(c, token, submission['id'], 1, body='PRIVATE practical evidence')
        review = dict(revision=2, ratings={'source':'met','reason':'met'}, feedback='Проверена работа по критериям.')
        for _ in range(2):
            assert post(admin, '/api/skills/practical-submissions/'+submission['id']+'/review', review, at).status_code == 200
    data = report(admin)
    assert data['evidence']['application'] == dict(unique_objective_revision_credits=1, learners=1)
    assert data['evidence']['understanding']['unique_objective_revision_credits'] == 0
    assert data['challenges']['certification']['started'] == 0
    assert data['cross_branch']['denominator'] == 1
    assert 'PRIVATE' not in json.dumps(data)


def test_half_open_windows_roles_and_unavailable_placement(skills):
    assert skills.test_cli_runner().invoke(args=['init-teaching']).exit_code == 0
    c = skills.test_client(); token = login(c)
    assert post(c, '/api/skills/diagnostics', dict(request_id='no-inventory', interests=[]), token).status_code == 201
    data = report(c)
    assert data['placement']['unavailable'] == 1
    assert data['placement']['completed'] == 0
    with sqlite3.connect(skills.config['DATABASE']) as db:
        for user, lesson, time in [('user-learner','foundations-start-01','2020-01-01 00:00:00'),
                                   ('user-member','foundations-start-01','2020-02-01 00:00:00'),
                                   ('user-editor','foundations-start-01','2020-01-15 00:00:00')]:
            db.execute("INSERT INTO events(user_id,lesson_id,name,created_at) VALUES(?,?,'lesson_started',?)", (user,lesson,time))
    data = c.get(URL).json
    assert data['cross_branch']['denominator'] == 1
    assert data['cross_branch']['activities_without_major_branch'] == 1
    assert data['placement']['started'] == 0
