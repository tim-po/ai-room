import json
import sqlite3
from pathlib import Path

import pytest
from club import create_app
from club.skills import publish_reviewed_form, validate_form
from club.skill_seed import graph_fixture
from test_learning import app, login, post, FREE


@pytest.fixture()
def skills(app):
    result = app.test_cli_runner().invoke(args=['init-skills'])
    assert result.exit_code == 0, result.output
    return app


def fixture_form():
    return {'items': [dict(id=f'q{i}', objective_id='basic-ai.verification', type=kind,
        prompt=prompt, choices=[{'id':'check','text':'Проверить первоисточник'}, {'id':'trust','text':'Довериться уверенности ответа'}],
        answer='check', critical=True, rationale='Уверенная формулировка не доказывает достоверность.',
        source={'kind':'synthetic-test-only', 'paragraph':1, 'text':'Ответ модели нужно проверять по первоисточнику.'})
        for i,kind,prompt in [(1,'knowledge','Как проверить утверждение?'), (2,'scenario','AI назвал дату без ссылки. Что сделать перед публикацией?')]]}


def install_form(app):
    with sqlite3.connect(app.config['DATABASE']) as db:
        reviewer = db.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
        publish_reviewed_form(db,id='test-form-v1',graph=graph_fixture(),node_id='basic-ai.verification',form=fixture_form(),access='free',reviewer=reviewer)


def test_additive_migration_preserves_baseline_and_backups(app):
    c = app.test_client(); csrf = login(c)
    post(c,'/api/lessons/'+FREE+'/completion',{'completed':True},csrf)
    post(c,'/api/lessons/'+FREE+'/practice',{'body':'keep me','status':'submitted'},csrf)
    for _ in range(2):
        assert app.test_cli_runner().invoke(args=['init-skills']).exit_code == 0
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT completed FROM progress').fetchone()[0] == 1
        assert db.execute('SELECT body FROM practice').fetchone()[0] == 'keep me'
        assert db.execute('PRAGMA user_version').fetchone()[0] == 6
        assert db.execute('SELECT COUNT(*) FROM skill_evidence').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM skill_releases').fetchone()[0] == 1
    assert len(list(Path(app.config['DATABASE']).parent.glob('*.before-skills-*.sqlite'))) == 2


def test_graph_nonexclusive_interests_restart_and_isolation(skills):
    c = skills.test_client(); csrf = login(c)
    tree = c.get('/api/skills/graph').json
    assert len([n for n in tree['nodes'] if n['kind']=='branch']) == 5
    assert len([n for n in tree['nodes'] if n['kind']=='ability']) == 26
    for node in ['coding.mobile','coding.review','content']:
        assert post(c,'/api/skills/explore',{'node_id':node},csrf).status_code == 200
    assert c.put('/api/skills/interests',json={'node_ids':['coding','content']},headers={'X-CSRF-Token':csrf}).status_code == 200
    c.put('/api/skills/interests',json={'node_ids':[]},headers={'X-CSRF-Token':csrf})
    restarted = create_app(dict(TESTING=True,DATABASE=skills.config['DATABASE'],SECRET_KEY='second')).test_client()
    login(restarted)
    me = restarted.get('/api/skills/me').json
    assert len(me['explorations']) == 3 and me['interests'] == []
    assert me['coverage'][0]['unknown'] == 26
    assert not me['evidence']
    other = skills.test_client(); login(other,'member')
    assert other.get('/api/skills/me').json['explorations'] == []
    assert skills.test_client().get('/api/skills/me').status_code == 401


def test_challenge_keys_replay_credit_retakes_and_isolation(skills):
    install_form(skills)
    c = skills.test_client(); csrf = login(c)
    create = lambda key: post(c,'/api/skills/challenges',{'assessment_id':'test-form-v1','request_id':key},csrf)
    first = create('request-1')
    assert first.status_code == 201
    attempt = first.json
    assert 'answer' not in json.dumps(attempt) and 'rationale' not in json.dumps(attempt)
    assert create('request-1').json == attempt
    assert create('request-2').status_code == 409  # no disclosure via simultaneous practice
    other = skills.test_client(); other_csrf = login(other,'member')
    path = '/api/skills/challenges/'+attempt['id']+'/submit'
    assert post(other,path,{'answers':{'q1':'check','q2':'check'}},other_csrf).status_code == 404
    result = post(c,path,{'answers':{'q1':'check','q2':'check'}},csrf)
    assert result.json['credited'] and result.json['passed']
    assert post(c,path,{'answers':{'q1':'trust','q2':'trust'}},csrf).json == result.json
    repeat = create('request-2').json
    assert repeat['mode'] == 'practice'
    assert not post(c,'/api/skills/challenges/'+repeat['id']+'/submit',{'answers':{'q1':'check','q2':'check'}},csrf).json['credited']
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM skill_evidence').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM progress').fetchone()[0] == 0
    coverage = c.get('/api/skills/me').json['coverage'][0]
    assert coverage['verified'] == 1 and coverage['unknown'] == 25
    assert coverage['application_verified'] == 0


def test_partial_and_insufficient_forms(skills):
    install_form(skills)
    c = skills.test_client(); csrf = login(c)
    attempt = post(c,'/api/skills/challenges',{'assessment_id':'test-form-v1','request_id':'partial-1'},csrf).json
    result = post(c,'/api/skills/challenges/'+attempt['id']+'/submit',{'answers':{'q1':'check','q2':'trust'}},csrf).json
    assert not result['credited'] and not result['passed']
    assert result['feedback'][1]['source']['paragraph'] == 1
    form = fixture_form(); form['items'].pop()
    with pytest.raises(ValueError):
        validate_form(form,graph_fixture())
    assert c.get('/api/skills/me').json['coverage'][0]['assessed'] == 1


def test_paid_form_access_and_immutable_versions(skills):
    with sqlite3.connect(skills.config['DATABASE']) as db:
        reviewer = db.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
        publish_reviewed_form(db,id='paid-v1',graph=graph_fixture(),node_id='basic-ai.verification',form=fixture_form(),access='member',reviewer=reviewer)
    c = skills.test_client(); csrf = login(c)
    assert post(c,'/api/skills/challenges',{'assessment_id':'paid-v1','request_id':'paid-request'},csrf).status_code == 403
    csrf = login(c,'member')
    attempt = post(c,'/api/skills/challenges',{'assessment_id':'paid-v1','request_id':'paid-request'},csrf).json
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute("UPDATE users SET entitlement='revoked' WHERE email='member@example.test'")
    path = '/api/skills/challenges/'+attempt['id']+'/submit'
    assert post(c,path,{'answers':{'q1':'check','q2':'check'}},csrf).status_code == 403
    with sqlite3.connect(skills.config['DATABASE']) as db:
        for sql in ["UPDATE skill_forms SET body='{}'", 'DELETE FROM skill_forms',
                    "UPDATE skill_releases SET body='{}'", 'DELETE FROM skill_attempts']:
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(sql)


def publish_copy(app, form, id='copy', tree=None):
    tree = tree or graph_fixture()
    with sqlite3.connect(app.config['DATABASE']) as db:
        reviewer = db.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
        publish_reviewed_form(db, id=id, graph=tree, node_id='basic-ai.verification', form=form, access='free', reviewer=reviewer)


@pytest.mark.parametrize('variant', ['renamed', 'partial', 'lineage'])
def test_cross_form_exposure_and_pending_race(skills, variant):
    original = fixture_form()
    original['items'][0]['lineage_id'] = 'source-observation-1'
    publish_copy(skills, original, 'original')
    copied = fixture_form()
    for i, item in enumerate(copied['items']):
        item['id'] = 'renamed-' + str(i)
        item['choices'].reverse()
        item['prompt'] = '  ' + item['prompt'].upper() + '  '
    if variant in ('partial', 'lineage'):
        copied['items'][1]['prompt'] = 'A genuinely different second observation'
    if variant == 'lineage':
        copied['items'][0]['prompt'] = 'Paraphrase of original observation'
        copied['items'][0]['lineage_id'] = 'source-observation-1'
    publish_copy(skills, copied)
    c = skills.test_client(); csrf = login(c)
    start = lambda form, key: post(c, '/api/skills/challenges', {'assessment_id':form, 'request_id':key}, csrf)
    first = start('original', 'original-request').json
    assert start('copy', 'copy-request').status_code == 409
    post(c, '/api/skills/challenges/'+first['id']+'/submit', {'answers':{'q1':'trust','q2':'trust'}}, csrf)
    copy = start('copy', 'copy-request').json
    assert copy['mode'] == 'practice'
    result = post(c, '/api/skills/challenges/'+copy['id']+'/submit', {'answers':{i['id']:'check' for i in copied['items']}}, csrf).json
    assert result['passed'] and not result['credited']
    assert c.get('/api/skills/me').json['evidence'] == []


@pytest.mark.parametrize('passed', [True, False])
def test_release_history_retirement_and_resume(skills, passed):
    install_form(skills)
    c = skills.test_client(); csrf = login(c)
    payload = {'assessment_id':'test-form-v1', 'request_id':'pinned-request'}
    attempt = post(c, '/api/skills/challenges', payload, csrf).json
    path = '/api/skills/challenges/' + attempt['id']
    assert c.get(path).json['result'] is None
    other = skills.test_client(); login(other, 'member')
    assert other.get(path).status_code == 404
    tree = graph_fixture(); tree['release'] = 'compatible-release'
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute('INSERT INTO skill_releases(id,body) VALUES(?,?)', (tree['release'], json.dumps(tree)))
        db.execute('UPDATE skill_active SET release_id=?', (tree['release'],))
    assert post(c, '/api/skills/challenges', dict(payload, request_id='new-request'), csrf).status_code == 409
    assert post(c, '/api/skills/challenges', payload, csrf).json == attempt
    answers = {'q1':'check' if passed else 'trust', 'q2':'check' if passed else 'trust'}
    result = post(c, path+'/submit', {'answers':answers}, csrf).json
    assert c.get(path).json['result'] == result
    publish_copy(skills, fixture_form(), tree=tree)
    copy = post(c, '/api/skills/challenges', {'assessment_id':'copy','request_id':'copy-request'}, csrf).json
    assert copy['mode'] == 'practice'
    coverage = c.get('/api/skills/me').json['coverage'][0]
    assert coverage['assessed'] == 1 and coverage['unknown'] == 25
    assert coverage['verified'] == int(passed)
    tree['release'] = 'changed-meaning'
    next(n for n in tree['nodes'] if n['id']=='basic-ai.verification')['revision'] += 1
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute('INSERT INTO skill_releases(id,body) VALUES(?,?)', (tree['release'], json.dumps(tree)))
        db.execute('UPDATE skill_active SET release_id=?', (tree['release'],))
    me = c.get('/api/skills/me').json
    assert me['coverage'][0]['assessed'] == 0 and me['coverage'][0]['unknown'] == 26
    assert len(me['evidence']) == int(passed)


def test_duplicate_observations_rejected_and_public_metadata_safe(skills):
    form = fixture_form()
    form['items'][1]['prompt'] = form['items'][0]['prompt']
    with pytest.raises(ValueError, match='Repeated observation'):
        validate_form(form, graph_fixture())
    form = fixture_form()
    for item in form['items']:
        item['lineage_id'] = 'one-observation'
    with pytest.raises(ValueError, match='Repeated observation'):
        validate_form(form, graph_fixture())
    install_form(skills)
    metadata = skills.test_client().get('/api/skills/nodes/basic-ai.verification').json['assessments'][0]
    assert metadata['item_count'] == 2 and metadata['credit_kind'] == 'understanding'
    assert not {'body','items','answer','rationale','lineage_id'} & metadata.keys()
