import copy
import json
import sqlite3

import pytest
from club.graph_review import validate_graph
from club.skill_seed import graph_fixture
from test_learning import app, login, post
from test_skills import skills, install_form


def addition(tree):
    candidate = copy.deepcopy(tree)
    candidate['nodes'].append(dict(id='coding.mobile.permissions', title='Проверить отзыв разрешения', kind='ability', revision=1))
    candidate['edges'].append(dict(source='coding.mobile', target='coding.mobile.permissions', type='contains', advisory=True))
    return candidate


def create(admin, token, graph):
    return post(admin, '/api/skills/graph-proposals', dict(base_release=graph['release'], graph=addition(graph), note='Проверены цель и отсутствие дублей.'), token)


def test_graph_review_activation_rollback_and_history_preserve_attempts(skills):
    install_form(skills)
    learner = skills.test_client(); lt = login(learner)
    attempt = post(learner, '/api/skills/challenges', dict(assessment_id='test-form-v1', request_id='graph-history-attempt'), lt)
    assert attempt.status_code == 201
    result = post(learner, '/api/skills/challenges/'+attempt.json['id']+'/submit', dict(answers={'q1':'check','q2':'check'}), lt)
    assert result.json['credited']
    admin = skills.test_client(); token = login(admin, 'admin')
    base = graph_fixture()
    response = create(admin, token, base)
    assert response.status_code == 201, response.json
    p = response.json; path = '/api/skills/graph-proposals/'+p['id']
    assert p['diff']['added_nodes'][0]['id'] == 'coding.mobile.permissions'
    assert admin.get('/api/skills/graph').json['release'] == base['release']
    assert learner.get(path).status_code == 403
    review = dict(revision=1, note='Проверены новые способности и связи.', confirm_reviewed=True)
    assert post(learner, path+'/activate', review, lt).status_code == 403
    assert post(admin, path+'/activate', dict(review, confirm_reviewed=False), token).status_code == 400
    assert post(admin, path+'/activate', review, token).json['state'] == 'active'
    assert learner.get('/api/skills/graph').json['release'] == p['id']
    assert post(admin, path+'/activate', review, token).status_code == 409
    assert post(admin, path+'/rollback', review, token).json['state'] == 'rolled_back'
    assert learner.get('/api/skills/graph').json['release'] == base['release']
    assert len(admin.get('/api/skills/graph-history').json['events']) == 2
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM skill_evidence').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM skill_results').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM skill_attempts').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM skill_forms').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM skill_releases').fetchone()[0] == 2
        for sql in ['DELETE FROM skill_graph_editions', "UPDATE skill_graph_events SET note='rewrite'"]:
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(sql)


def test_proposal_edits_conflicts_rejection_and_later_release_guard(skills):
    admin = skills.test_client(); token = login(admin, 'admin')
    a = create(admin, token, graph_fixture()).json
    b = create(admin, token, graph_fixture()).json
    path = '/api/skills/graph-proposals/'+a['id']
    edit = dict(revision=1, graph=a['graph'], note='Уточнено название новой способности.')
    edit['graph']['nodes'][-1]['title'] = 'Проверить отказ после отзыва разрешения'
    assert admin.put(path, json=edit, headers={'X-CSRF-Token':token}).json['revision'] == 2
    assert admin.put(path, json=edit, headers={'X-CSRF-Token':token}).status_code == 409
    review = dict(revision=2, note='Редакционное ревью завершено.', confirm_reviewed=True)
    assert post(admin, path+'/activate', review, token).status_code == 200
    assert post(admin, '/api/skills/graph-proposals/'+b['id']+'/activate', dict(review, revision=1), token).status_code == 409
    assert post(admin, '/api/skills/graph-proposals/'+b['id']+'/reject', dict(review, revision=1), token).json['state'] == 'rejected'
    with sqlite3.connect(skills.config['DATABASE']) as db:
        newer = copy.deepcopy(a['graph']); newer['release'] = 'external-content-release'
        db.execute('INSERT INTO skill_releases(id,body) VALUES(?,?)', (newer['release'],json.dumps(newer)))
        db.execute('UPDATE skill_active SET release_id=?', (newer['release'],))
    assert post(admin, path+'/rollback', review, token).status_code == 409


@pytest.mark.parametrize('mutation', ['cycle','prerequisite_cycle','second_root','orphan','semantic','missing','gate','mapping','duplicate'])
def test_invalid_graph_boundaries(mutation):
    base = graph_fixture(); candidate = addition(base)
    if mutation == 'cycle':
        candidate['edges'] = [e for e in candidate['edges'] if not (e['type']=='contains' and e['target']=='coding')]
        candidate['edges'].append(dict(source='coding.mobile', target='coding', type='contains', advisory=True))
    elif mutation == 'prerequisite_cycle':
        candidate['edges'] += [dict(source=a, target=b, type='prerequisite', advisory=True) for a,b in [('coding','teams'),('teams','coding')]]
    elif mutation == 'second_root':
        candidate['nodes'][-1]['kind'] = 'root'
    elif mutation == 'orphan':
        candidate['edges'].pop()
    elif mutation == 'semantic':
        candidate['nodes'][1]['title'] = 'Иная способность'
    elif mutation == 'missing':
        candidate['nodes'].pop(1)
    elif mutation == 'gate':
        candidate['edges'][-1]['advisory'] = False
    elif mutation == 'mapping':
        candidate['mappings'] = [dict(lesson_id='invented')]
    elif mutation == 'duplicate':
        candidate['nodes'].append(candidate['nodes'][0])
    with pytest.raises(ValueError):
        validate_graph(candidate, base)


def test_rolled_back_identity_cannot_be_repurposed(skills):
    admin = skills.test_client(); token = login(admin, 'admin')
    p = create(admin, token, graph_fixture()).json
    review = dict(revision=1, note='Подтверждены структура и смысл.', confirm_reviewed=True)
    path = '/api/skills/graph-proposals/'+p['id']
    assert post(admin, path+'/activate', review, token).status_code == 200
    assert post(admin, path+'/rollback', review, token).status_code == 200
    candidate = addition(graph_fixture()); candidate['nodes'][-1]['title'] = 'Подмена смысла исторического ID'
    assert post(admin, '/api/skills/graph-proposals', dict(base_release=graph_fixture()['release'], graph=candidate, note='Повторное предложение способности.'), token).status_code == 400


from test_teaching import teaching, upload
from test_teaching_pipeline import pipeline, process


def test_source_draft_is_pinned_and_private(pipeline):
    editor = pipeline.test_client(); token = login(editor, 'editor')
    job = upload(editor, token).json
    process(pipeline)
    value = dict(base_release=graph_fixture()['release'], job_id=job['id'], draft_revision=1, note='Предложение из загруженного источника.')
    response = post(editor, '/api/skills/graph-proposals', value, token)
    assert response.status_code == 201, response.json
    assert response.json['source']['draft_revision'] == 1
    assert response.json['source']['proposals'][0]['kind'] == 'reuse'
    assert response.json['source']['sources'][0]['sha256']
    # A separate editor cannot read or import another editor's draft.
    with sqlite3.connect(pipeline.config['DATABASE']) as db:
        db.execute("UPDATE users SET role='editor' WHERE email='member@example.test'")
    other = pipeline.test_client(); ot = login(other, 'member')
    assert other.get('/api/skills/graph-proposals/'+response.json['id']).status_code == 404
    assert post(other, '/api/skills/graph-proposals', value, ot).status_code == 404
