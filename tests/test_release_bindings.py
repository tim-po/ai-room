"""Cross-feature regressions for editorial structural release transitions."""
import copy
import json
import sqlite3

import pytest
from club import create_app
from club.skills import publish_reviewed_form
from test_learning import app, login, post
from test_skills import skills, fixture_form, publish_copy
from test_graph_review import addition
from test_practical import setup_task, draft, save
from test_form_lifecycle import start, finish, withdraw


def propose(admin, token, mutation):
    base = admin.get('/api/skills/graph').json
    tree = dict(copy.deepcopy(base), mappings=[])
    if mutation == 'add':
        tree = addition(tree)
    elif mutation == 'rename':
        next(n for n in tree['nodes'] if n['kind'] == 'category')['title'] = 'Новое название категории'
    else:
        next(e for e in tree['edges'] if e['type'] == 'contains' and e['target'] == 'basic-ai.verification')['source'] = 'coding.mobile'
    response = post(admin, '/api/skills/graph-proposals', dict(base_release=base['release'], graph=tree, note='Проверены структура и совместимость.'), token)
    assert response.status_code == 201, response.json
    return response.json


def transition(admin, token, proposal, action='activate'):
    response = post(admin, '/api/skills/graph-proposals/'+proposal['id']+'/'+action,
                    dict(revision=1, note='Подтверждена совместимость редакции.', confirm_reviewed=True), token)
    assert response.status_code == 200, response.json
    return response.json


@pytest.mark.parametrize('mutation', ['add', 'rename', 'reparent'])
def test_pending_new_work_diagnostic_restart_rollback_and_exposure(skills, mutation):
    admin, at, task, rubric = setup_task(skills)
    c = skills.test_client(); token = login(c)
    pending = start(c, token).json
    submission = draft(c, token, task).json
    diagnostic = post(c, '/api/skills/diagnostics', dict(request_id='placement-before', interests=[]), token).json
    p = propose(admin, at, mutation)
    impact = p['diff']['availability']
    assert impact['assessments'] == dict(unchanged=['test-form-v1'], added=[], removed=[])
    assert impact['practical_tasks'] == dict(unchanged=[task['id']], added=[], removed=[])
    transition(admin, at, p)
    forms = c.get('/api/skills/nodes/basic-ai.verification').json['assessments']
    assert [f['id'] for f in forms] == ['test-form-v1']
    assert forms[0]['pending_attempt']['id'] == pending['id']
    assert c.get('/api/skills/practical-tasks').json['tasks'] == [task]
    assert c.get('/api/skills/diagnostics/'+diagnostic['id']).json['next']['assessment_id'] == 'test-form-v1'
    assert start(c, token, key='second-pending').status_code == 409
    other = skills.test_client(); ot = login(other, 'member')
    assert start(other, ot).status_code == 201
    assert draft(other, ot, task).status_code == 201
    # Restart keeps availability and original pinned provenance intact.
    restarted = create_app(dict(TESTING=True, DATABASE=skills.config['DATABASE'], SECRET_KEY='restart')).test_client()
    rt = login(restarted)
    assert restarted.get('/api/skills/practical-tasks').json['tasks'] == [task]
    assert finish(restarted, rt, pending).json['credited']
    transition(admin, at, p, 'rollback')
    assert save(restarted, rt, submission['id'], 1).status_code == 200
    path = '/api/skills/practical-submissions/'+submission['id']+'/review'
    assert post(admin, path, dict(revision=2, ratings={'source':'met','reason':'met'}, feedback='Результат проверен после отката.'), at).json['decision']['credited']
    retake = start(restarted, rt, key='after-rollback').json
    assert retake['mode'] == 'practice'
    assert not finish(restarted, rt, retake).json['credited']
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM skill_forms').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM skill_evidence').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM skill_application_evidence').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM progress').fetchone()[0] == 0
        for sql in ['DELETE FROM skill_form_bindings', "UPDATE skill_form_bindings SET reviewed_by='changed'"]:
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(sql)


@pytest.mark.parametrize('when', ['before', 'active', 'rollback'])
def test_withdrawn_ancestry_is_never_reactivated(skills, when):
    admin, at, task, _ = setup_task(skills)
    publish_copy(skills, dict(fixture_form(), inherited_from_form='test-form-v1'), 'old-mapping-copy')
    c = skills.test_client(); token = login(c)
    pending = start(c, token, 'old-mapping-copy').json
    submission = draft(c, token, task).json
    p = propose(admin, at, 'rename')
    if when == 'before':
        withdraw(admin, at)
    transition(admin, at, p)
    if when == 'active':
        withdraw(admin, at)
    transition(admin, at, p, 'rollback')
    if when == 'rollback':
        withdraw(admin, at)
    assert not finish(c, token, pending).json['credited']
    assert start(c, token, 'old-mapping-copy', 'withdrawn-copy').status_code == 409
    assert c.get('/api/skills/nodes/basic-ai.verification').json['assessments'] == []
    assert c.get('/api/skills/practical-tasks').json['tasks'] == []
    assert draft(c, token, task, 'withdrawn-task').status_code == 409
    save(c, token, submission['id'], 1)
    result = post(admin, '/api/skills/practical-submissions/'+submission['id']+'/review',
                  dict(revision=2, ratings={'source':'met','reason':'met'}, feedback='Работа проверена, форма уже отозвана.'), at).json
    assert not result['decision']['credited']
    fresh = propose(admin, at, 'add')
    assert fresh['diff']['availability']['assessments']['unchanged'] == []
    assert fresh['diff']['availability']['withdrawn_assessments'] == ['old-mapping-copy','test-form-v1']
    transition(admin, at, fresh)
    assert c.get('/api/skills/practical-tasks').json['tasks'] == []


def test_rollback_filters_new_abilities_but_retains_new_compatible_inventory(skills):
    admin, at, task, rubric = setup_task(skills)
    p = propose(admin, at, 'add'); transition(admin, at, p)
    tree = admin.get('/api/skills/graph').json
    with sqlite3.connect(skills.config['DATABASE']) as db:
        reviewer = db.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
        for id, objective in [('new-compatible','basic-ai.verification'), ('new-ability','coding.mobile.permissions')]:
            form = fixture_form()
            for item in form['items']:
                item['objective_id'] = objective
                item['prompt'] += ' ' + id
            publish_reviewed_form(db, id=id, graph=tree, node_id=objective, form=form, access='free', reviewer=reviewer)
    new_task = post(admin, '/api/skills/practical-tasks', dict(rubric, assessment_id='new-compatible'), at).json
    removed_task = post(admin, '/api/skills/practical-tasks', dict(rubric, assessment_id='new-ability', objective_id='coding.mobile.permissions'), at).json
    preview = admin.get('/api/skills/graph-proposals/'+p['id']).json['rollback_availability']
    assert preview['assessments']['removed'] == ['new-ability']
    assert preview['practical_tasks']['removed'] == [removed_task['id']]
    transition(admin, at, p, 'rollback')
    c = skills.test_client(); token = login(c)
    assert start(c, token, 'new-ability').status_code == 409
    assert start(c, token, 'new-compatible').status_code == 201
    assert draft(c, token, new_task).status_code == 201
    assert draft(c, token, removed_task, 'removed-task').status_code == 409


def test_paid_access_and_additive_repair_of_pre_fix_activated_edition(skills):
    admin, at, task, _ = setup_task(skills, access='member')
    p = propose(admin, at, 'rename'); transition(admin, at, p)
    # Disposable DB: emulate a pre-fix deployment with reviewed graph history.
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute('DROP TABLE skill_form_bindings')
    for _ in range(2):
        result = skills.test_cli_runner().invoke(args=['init-skills'])
        assert result.exit_code == 0, result.output
    c = skills.test_client(); token = login(c)
    assert c.get('/api/skills/practical-tasks').json['tasks'] == []
    assert start(c, token).status_code == 403
    assert draft(c, token, task).status_code == 403
    member = skills.test_client(); mt = login(member, 'member')
    assert start(member, mt).status_code == 201
    assert draft(member, mt, task).status_code == 201
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM skill_form_bindings').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM skill_forms').fetchone()[0] == 1


from test_teaching import teaching, upload
from test_teaching_pipeline import pipeline, process


def test_teaching_publication_after_structural_change_retains_rubric_and_exposure(pipeline):
    admin, at, task, _ = setup_task(pipeline)
    c = pipeline.test_client(); token = login(c)
    completed = start(c, token).json
    assert finish(c, token, completed).json['credited']
    p = propose(admin, at, 'rename'); transition(admin, at, p)
    job = upload(admin, at).json
    assert 'ready' in process(pipeline)
    published = post(admin, '/api/teaching/jobs/'+job['id']+'/publish',
                     dict(revision=1, confirm_reviewed=True, access='free', review_note='Reviewed synthetic fixture.'), at)
    assert published.status_code == 201, published.json
    assert c.get('/api/skills/practical-tasks').json['tasks'] == [task]
    assert draft(c, token, task).status_code == 201
    repeated = start(c, token, key='after-teaching').json
    assert repeated['mode'] == 'practice'
    assert not finish(c, token, repeated).json['credited']
    with sqlite3.connect(pipeline.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM skill_forms').fetchone()[0] == 2
        assert db.execute('SELECT COUNT(*) FROM skill_evidence').fetchone()[0] == 1
    assert withdraw(admin, at).status_code == 201
    assert c.get('/api/skills/practical-tasks').json['tasks'] == []


def test_incompatible_semantics_and_scores_do_not_receive_bindings(skills):
    from club.release_bindings import compatible
    setup_task(skills)
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.row_factory = sqlite3.Row
        def query(sql, args=(), one=False):
            rows = db.execute(sql, args)
            return rows.fetchone() if one else rows.fetchall()
        form = query('SELECT * FROM skill_forms', one=True)
        original = json.loads(query('SELECT body FROM skill_releases', one=True)['body'])
        for mutation in ['revision', 'title', 'score_rule', 'missing']:
            target = copy.deepcopy(original)
            node = next(n for n in target['nodes'] if n['id']=='basic-ai.verification')
            if mutation == 'revision':
                node['revision'] += 1
            elif mutation == 'title':
                node['title'] = 'Different meaning'
            elif mutation == 'missing':
                target['nodes'].remove(node)
            else:
                target['score_rule'] = 'different-scoring'
            assert not compatible(query, form, target)
