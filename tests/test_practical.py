import json
import sqlite3

import pytest
from club import create_app
from club.skill_seed import graph_fixture
from club.skills import publish_reviewed_form
from test_learning import app, login, post
from test_skills import skills, fixture_form, install_form


def setup_task(skills, access='free'):
    if access == 'free':
        install_form(skills)
    else:
        with sqlite3.connect(skills.config['DATABASE']) as db:
            reviewer = db.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
            publish_reviewed_form(db, id='test-form-v1', graph=graph_fixture(), node_id='basic-ai.verification', form=fixture_form(), access=access, reviewer=reviewer)
    admin = skills.test_client(); token = login(admin, 'admin')
    value = dict(assessment_id='test-form-v1', objective_id='basic-ai.verification',
                 instructions='Проверьте утверждение модели по первоисточнику и сохраните доказательства и вывод.',
                 criteria=[dict(id='source', text='Указан подходящий первоисточник и проверяемая цитата.'),
                           dict(id='reason', text='Вывод сопоставлен с источником, неопределённость обозначена.')], confirm_reviewed=True)
    response = post(admin, '/api/skills/practical-tasks', value, token)
    assert response.status_code == 201, response.json
    return admin, token, response.json, value


def draft(c, token, task, key='practical-request'):
    return post(c, '/api/skills/practical-submissions', dict(task_id=task['id'], request_id=key), token)


def save(c, token, id, revision, body='Мой результат проверки с источником и объяснением.', status='submitted'):
    return c.put('/api/skills/practical-submissions/'+id, json=dict(revision=revision, body=body, status=status), headers={'X-CSRF-Token':token})


def test_practical_persistence_human_review_and_separate_evidence(skills):
    admin, at, task, _ = setup_task(skills)
    c = skills.test_client(); token = login(c)
    assert c.get('/api/skills/practical-tasks?node_id=basic-ai.verification').json['tasks'] == [task]
    s = draft(c, token, task).json; path = '/api/skills/practical-submissions/'+s['id']
    assert draft(c, token, task).json == s
    assert draft(c, token, task, 'second-pending').status_code == 409
    assert save(c, token, s['id'], 1, status='draft').json['revision'] == 2
    restarted = create_app(dict(TESTING=True, DATABASE=skills.config['DATABASE'], SECRET_KEY='restarted')).test_client()
    rt = login(restarted)
    assert restarted.get(path).json['body'].startswith('Мой результат')
    assert save(restarted, rt, s['id'], 1).status_code == 409
    sent = save(restarted, rt, s['id'], 2).json
    assert sent['state'] == 'submitted'
    assert save(restarted, rt, s['id'], 2).json == sent
    assert save(restarted, rt, s['id'], 3, body='changed').status_code == 409
    me = c.get('/api/skills/me').json
    assert me['application_evidence'] == []
    assert admin.get('/api/skills/practical-review').json['submissions'][0]['id'] == s['id']
    review = dict(revision=3, ratings={'source':'met','reason':'met'}, feedback='Источники и аргументация проверены человеком.')
    assert post(c, path+'/review', review, token).status_code == 403
    reviewed = post(admin, path+'/review', review, at)
    assert reviewed.status_code == 200
    assert reviewed.json['decision']['credited']
    assert post(admin, path+'/review', review, at).json == reviewed.json
    assert post(admin, path+'/review', dict(review, feedback='Другой новый отзыв.'), at).status_code == 409
    me = restarted.get('/api/skills/me').json
    assert len(me['application_evidence']) == 1 and not me['evidence']
    assert me['coverage'][0]['application_verified'] == 1
    assert me['coverage'][0]['verified'] == 0 and me['coverage'][0]['unknown'] == 26
    assert not admin.get('/api/skills/practical-review').json['submissions']
    again = draft(c, token, task, 'practical-retake').json
    save(c, token, again['id'], 1)
    result = post(admin, '/api/skills/practical-submissions/'+again['id']+'/review', dict(review, revision=2), at).json
    assert result['decision']['passed'] and not result['decision']['credited']
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM skill_application_evidence').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM progress').fetchone()[0] == 0
        for sql in ["UPDATE skill_practical_tasks SET body='{}'", "DELETE FROM skill_practical_tasks",
                    "UPDATE skill_practical_decisions SET body='{}'", "DELETE FROM skill_practical_decisions",
                    "UPDATE skill_application_evidence SET objective_revision=9", "DELETE FROM skill_application_evidence",
                    "UPDATE skill_practical_submissions SET body='rewritten'", "DELETE FROM skill_practical_submissions"]:
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(sql)


def test_uncertain_incomplete_and_self_reviews_never_certify(skills):
    admin, at, task, _ = setup_task(skills)
    c = skills.test_client(); token = login(c)
    s = draft(c, token, task).json
    path = '/api/skills/practical-submissions/'+s['id']+'/review'
    review = dict(revision=1, ratings={'source':'met','reason':'met'}, feedback='Проверены оба критерия работы.')
    assert admin.get(path.removesuffix('/review')).status_code == 404
    assert post(admin, path, review, at).status_code == 404
    save(c, token, s['id'], 1)
    assert post(admin, path, dict(review, revision=2, ratings={'source':'met'}), at).status_code == 400
    assert post(admin, path, dict(review, revision=2, ratings={'source':'met','reason':{}}), at).status_code == 400
    result = post(admin, path, dict(review, revision=2, ratings={'source':'met','reason':'uncertain'}), at).json
    assert not result['decision']['passed'] and not result['decision']['credited']
    assert c.get('/api/skills/me').json['application_evidence'] == []
    own = draft(admin, at, task).json
    save(admin, at, own['id'], 1)
    assert post(admin, '/api/skills/practical-submissions/'+own['id']+'/review', dict(review, revision=2), at).status_code == 403


def test_practical_entitlement_isolation_validation_and_review_sources(skills):
    admin, at, task, payload = setup_task(skills, 'member')
    c = skills.test_client(); token = login(c, 'member')
    s = draft(c, token, task).json
    path = '/api/skills/practical-submissions/'+s['id']
    assert 'answer' not in json.dumps(task) and 'rationale' not in json.dumps(task)
    assert task['sources'][0]['kind'] == 'synthetic-test-only'
    other = skills.test_client(); ot = login(other)
    assert other.get(path).status_code == 404
    assert save(other, ot, s['id'], 1).status_code == 404
    assert other.get('/api/skills/practical-tasks/'+task['id']).status_code == 403
    assert draft(other, ot, task).status_code == 403
    assert other.get('/api/skills/practical-tasks').json == {'tasks':[]}
    assert other.get('/api/skills/practical-review').status_code == 403
    assert post(other, '/api/skills/practical-tasks', payload, ot).status_code == 403
    assert c.post('/api/skills/practical-submissions', json={}).status_code == 400
    assert skills.test_client().get(path).status_code == 401
    assert save(c, token, s['id'], 1, body=' ').status_code == 400
    assert post(admin, '/api/skills/practical-tasks', dict(payload, confirm_reviewed=False), at).status_code == 400
    assert post(admin, '/api/skills/practical-tasks', dict(payload, objective_id='coding.mobile.demonstrate'), at).status_code == 400
    assert post(admin, '/api/skills/practical-tasks', dict(payload, criteria=[payload['criteria'][0]]*2), at).status_code == 400
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute("UPDATE users SET entitlement='revoked' WHERE email='member@example.test'")
    assert c.get(path).status_code == 403
    assert save(c, token, s['id'], 1).status_code == 403
    assert c.get('/api/skills/practical-submissions').json['submissions'] == [dict(id=s['id'],task_id=task['id'],access_required=True)]


def test_pinned_rubric_survives_graph_change_and_new_attempts_retire(skills):
    admin, at, task, _ = setup_task(skills)
    c = skills.test_client(); token = login(c)
    s = draft(c, token, task).json
    with sqlite3.connect(skills.config['DATABASE']) as db:
        tree = graph_fixture(); tree['release'] = 'next-release'
        for node in tree['nodes']:
            if node['id'] == task['objective_id']:
                node['revision'] += 1
        db.execute('INSERT INTO skill_releases(id,body) VALUES(?,?)', (tree['release'], json.dumps(tree)))
        db.execute('UPDATE skill_active SET release_id=?', (tree['release'],))
    assert c.get('/api/skills/practical-tasks').json['tasks'] == []
    assert draft(c, token, task).json == s
    assert draft(c, token, task, 'new-release-attempt').status_code == 409
    assert save(c, token, s['id'], 1).status_code == 200
    review = dict(revision=2, ratings={'source':'met','reason':'met'}, feedback='Проверена работа по закреплённой рубрике.')
    assert post(admin, '/api/skills/practical-submissions/'+s['id']+'/review', review, at).json['decision']['credited']
    me = c.get('/api/skills/me').json
    assert len(me['application_evidence']) == 1
    assert me['coverage'][0]['application_verified'] == 0  # history isn't mastery of changed objective
    assert c.get('/api/skills/practical-tasks/'+task['id']).json == task


def test_reviewer_attribution_uses_recorded_actor_not_viewer(skills):
    admin, at, task, _ = setup_task(skills)
    c = skills.test_client(); token = login(c)
    alias = task['reviewer']
    assert alias['attribution'] == 'recorded_reviewer_alias'
    with sqlite3.connect(skills.config['DATABASE']) as db:
        actor = db.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
        db.execute("INSERT INTO users(id,email,password_hash,name,role) VALUES(?,?,?,?,?)",
                   ('second-editor', 'private-editor@example.test', 'unused', 'Private name', 'editor'))
    second = skills.test_client()
    with second.session_transaction() as session:
        session['user_id'] = 'second-editor'
    s = draft(c, token, task).json
    path = '/api/skills/practical-submissions/' + s['id']
    assert s['decision'] is None
    save(c, token, s['id'], 1)
    review = dict(revision=2, ratings={'source':'met','reason':'met'}, feedback='Проверены источники и обоснование вывода.')
    result = post(admin, path+'/review', review, at).json
    assert result['decision']['reviewer'] == alias
    assert c.get(path).json['decision']['reviewer'] == alias
    assert second.get(path).json['decision']['reviewer'] == alias
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute("UPDATE users SET name=?,email=?,role='learner' WHERE id=?",
                   ('changed-private-name', 'changed-private@example.test', actor))
    restarted = create_app(dict(TESTING=True, DATABASE=skills.config['DATABASE'], SECRET_KEY='another')).test_client()
    login(restarted)
    assert restarted.get(path).json['decision']['reviewer'] == alias
    evidence = restarted.get('/api/skills/me').json['application_evidence'][0]
    assert evidence['reviewer'] == alias
    assert 'reviewer_id' not in evidence
    assert restarted.get('/api/skills/practical-tasks/'+task['id']).json['reviewer'] == alias
    output = json.dumps([result, evidence, task], ensure_ascii=False)
    for private in ('@', 'password_hash', 'changed-private-name', 'Private name'):
        assert private not in output
    assert skills.test_client().get(path).status_code == 401
