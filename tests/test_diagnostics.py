import json
import sqlite3

from club import create_app
from club.skills import publish_reviewed_form
from club.skill_seed import graph_fixture
from test_learning import app, login, post
from test_skills import skills, fixture_form, install_form


def test_persisted_optional_multi_interest_diagnostic(skills):
    install_form(skills)
    c = skills.test_client(); csrf = login(c)
    payload = dict(request_id='diagnostic-1', interests=['coding', 'content'])
    initial = post(c, '/api/skills/diagnostics', payload, csrf)
    assert initial.status_code == 201
    d = initial.json; path = '/api/skills/diagnostics/' + d['id']
    assert d['next']['reason'] == 'foundation'
    assert len(d['unknown_objectives']) == 14
    assert 'answer' not in json.dumps(d)
    assert post(c, '/api/skills/diagnostics', payload, csrf).json == d
    assert post(c, '/api/skills/diagnostics', dict(payload, interests=[]), csrf).status_code == 409
    attempt = post(c, '/api/skills/challenges', dict(assessment_id=d['next']['assessment_id'], request_id='diagnostic-attempt'), csrf).json
    assert c.get(path).json['next']['pending_attempt_id'] == attempt['id']
    assert post(c, path+'/advance', dict(revision=1, attempt_id=attempt['id']), csrf).status_code == 400
    post(c, '/api/skills/challenges/'+attempt['id']+'/submit', dict(answers={'q1':'check','q2':'check'}), csrf)
    done = post(c, path+'/advance', dict(revision=1, attempt_id=attempt['id']), csrf)
    assert done.status_code == 200
    assert done.json['state'] == 'completed'
    assert done.json['verified_objectives'] == ['basic-ai.verification']
    assert len(done.json['unknown_objectives']) == 13
    assert post(c, path+'/advance', dict(revision=1, attempt_id=attempt['id']), csrf).json == done.json
    restarted = create_app(dict(TESTING=True, DATABASE=skills.config['DATABASE'], SECRET_KEY='restart')).test_client()
    login(restarted)
    assert restarted.get(path).json == done.json
    assert restarted.get('/api/skills/me').json['interests'] == []
    other = skills.test_client(); token = login(other, 'member')
    assert other.get(path).status_code == 404
    assert post(other, path+'/advance', dict(revision=2, skip=True), token).status_code == 404
    assert skills.test_client().get(path).status_code == 401


def test_gaps_adaptation_skip_and_entitlement(skills):
    install_form(skills)
    tree = graph_fixture()
    with sqlite3.connect(skills.config['DATABASE']) as db:
        reviewer = db.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
        for node in ['coding.mobile.demonstrate', 'content.writing.demonstrate']:
            form = fixture_form()
            for item in form['items']:
                item['objective_id'] = node
                item['prompt'] += node
            publish_reviewed_form(db, id=node, graph=tree, node_id=node, form=form, access='member', reviewer=reviewer)
    c = skills.test_client(); csrf = login(c,'member')
    d = post(c,'/api/skills/diagnostics',dict(request_id='adaptive-1',interests=['coding','content']),csrf).json
    path = '/api/skills/diagnostics/'+d['id']
    a = post(c,'/api/skills/challenges',dict(assessment_id=d['next']['assessment_id'],request_id='adaptive-attempt'),csrf).json
    post(c,'/api/skills/challenges/'+a['id']+'/submit',dict(answers={'q1':'trust','q2':'trust'}),csrf)
    d = post(c,path+'/advance',dict(revision=1,attempt_id=a['id']),csrf).json
    assert d['next']['assessment_id'] == 'coding.mobile.demonstrate'
    assert d['recommendations'][0]['source']['paragraph'] == 1
    assert not d['verified_objectives']
    assert post(c,path+'/advance',dict(revision=1,skip=True),csrf).status_code == 409
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute("UPDATE users SET entitlement='revoked' WHERE email='member@example.test'")
    assert c.get(path).json['next'] is None
    skipped = post(c,path+'/advance',dict(revision=2,skip=True),csrf).json
    assert skipped['state'] == 'skipped'
    assert c.get('/api/skills/me').json['evidence'] == []
