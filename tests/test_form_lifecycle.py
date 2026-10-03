import sqlite3
import pytest
from test_learning import app, login, post
from test_skills import skills, install_form, fixture_form, publish_copy
from test_practical import setup_task, draft, save


def withdraw(c, token, replacement=None, **extra):
    return post(c, '/api/skills/forms/test-form-v1/withdraw',
                dict(reason='Редактор обнаружил неоднозначность вопроса.', replacement_id=replacement,
                     confirm_reviewed=True, **extra), token)


def start(c, token, form='test-form-v1', key='first-request'):
    return post(c, '/api/skills/challenges', dict(assessment_id=form, request_id=key), token)


def finish(c, token, attempt):
    return post(c, '/api/skills/challenges/'+attempt['id']+'/submit',
                {'answers':{i['id']:'check' for i in attempt['items']}}, token)


def test_withdrawal_pending_no_credit_replacement_exposure_and_unseen_variant(skills):
    install_form(skills)
    publish_copy(skills, fixture_form(), 'replacement')
    unseen = fixture_form()
    for i, item in enumerate(unseen['items']):
        item['prompt'] = f'Independent transfer fixture {i}'
        item['lineage_id'] = f'new-transfer-{i}'
    publish_copy(skills, unseen, 'unseen')
    c = skills.test_client(); token = login(c)
    admin = skills.test_client(); at = login(admin, 'admin')
    first = start(c, token).json
    assert withdraw(c, token).status_code == 403
    assert withdraw(admin, at, 'replacement').status_code == 201
    assert withdraw(admin, at, 'replacement').status_code == 200
    assert withdraw(admin, at, 'unseen').status_code == 409
    assert start(c, token, key='blocked-request').status_code == 409
    assert start(c, token).json['lifecycle']['status'] == 'withdrawn'
    result = finish(c, token, first).json
    assert result['passed'] and not result['credited']
    assert result['lifecycle']['replacement_id'] == 'replacement'
    copied = start(c, token, 'replacement', 'replacement-request').json
    assert copied['mode'] == 'practice'
    assert not finish(c, token, copied).json['credited']
    independent = start(c, token, 'unseen', 'unseen-request').json
    assert independent['mode'] == 'certification'
    assert finish(c, token, independent).json['credited']
    assert len(c.get('/api/skills/me').json['evidence']) == 1
    available = c.get('/api/skills/nodes/basic-ai.verification').json['assessments']
    assert 'test-form-v1' not in [f['id'] for f in available]
    with sqlite3.connect(skills.config['DATABASE']) as db:
        for sql in ['DELETE FROM skill_form_withdrawals', "UPDATE skill_form_withdrawals SET reason='changed'"]:
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(sql)


def test_withdrawal_preserves_prior_result_and_evidence(skills):
    install_form(skills)
    c = skills.test_client(); token = login(c)
    first = start(c, token).json
    result = finish(c, token, first).json
    assert result['credited']
    admin = skills.test_client(); at = login(admin, 'admin')
    assert withdraw(admin, at).status_code == 201
    assert finish(c, token, first).json == result
    assert len(c.get('/api/skills/me').json['evidence']) == 1


def test_practical_withdrawal_preserves_work_but_cannot_certify(skills):
    admin, at, task, value = setup_task(skills)
    c = skills.test_client(); token = login(c)
    submission = draft(c, token, task).json
    assert withdraw(admin, at).status_code == 201
    assert post(admin, '/api/skills/practical-tasks', value, at).status_code == 409
    assert draft(c, token, task, 'new-task-request').status_code == 409
    assert draft(c, token, task).json == submission
    assert save(c, token, submission['id'], 1).status_code == 200
    reviewed = post(admin, '/api/skills/practical-submissions/'+submission['id']+'/review',
                    dict(revision=2, ratings={'source':'met','reason':'met'}, feedback='Критерии выполнены, форма отозвана.'), at).json
    assert reviewed['decision']['passed'] and not reviewed['decision']['credited']
    assert reviewed['decision']['lifecycle']['status'] == 'withdrawn'
    assert c.get('/api/skills/practical-tasks').json['tasks'] == []
    assert c.get('/api/skills/me').json['application_evidence'] == []


def test_invalid_replacement_and_diagnostic_withdrawal(skills):
    install_form(skills)
    c = skills.test_client(); token = login(c)
    admin = skills.test_client(); at = login(admin, 'admin')
    diagnostic = post(c, '/api/skills/diagnostics', {'request_id':'diagnostic-request','interests':[]}, token).json
    assert diagnostic['next']['assessment_id'] == 'test-form-v1'
    for replacement in ['test-form-v1', 'missing']:
        assert withdraw(admin, at, replacement).status_code == 409
    assert withdraw(admin, at).status_code == 201
    resumed = c.get('/api/skills/diagnostics/'+diagnostic['id']).json
    assert resumed['next'] is None and resumed['unknown_objectives']


def test_mapping_only_copies_inherit_withdrawal_even_when_issued_earlier(skills):
    install_form(skills)
    copied = dict(fixture_form(), inherited_from_form='test-form-v1')
    publish_copy(skills, copied, 'mapping-copy')
    c = skills.test_client(); token = login(c)
    first = start(c, token, 'mapping-copy').json
    admin = skills.test_client(); at = login(admin, 'admin')
    assert withdraw(admin, at).status_code == 201
    assert not finish(c, token, first).json['credited']
    assert start(c, token, 'mapping-copy', 'copied-new-request').status_code == 409
    publish_copy(skills, dict(fixture_form(), inherited_from_form='mapping-copy'), 'nested-copy')
    assert start(c, token, 'nested-copy', 'nested-new-request').status_code == 409
    assert c.get('/api/skills/nodes/basic-ai.verification').json['assessments'] == []


def test_editor_inventory_filters_replacements_and_protects_metadata(skills):
    install_form(skills)
    publish_copy(skills, fixture_form(), 'replacement')
    publish_copy(skills, dict(fixture_form(), inherited_from_form='test-form-v1'), 'descendant')
    learner = skills.test_client(); login(learner)
    assert learner.get('/api/skills/forms').status_code == 403
    assert learner.get('/admin/assessments').status_code == 403
    admin = skills.test_client(); token = login(admin, 'admin')
    assert admin.get('/admin/assessments').status_code == 200
    inventory = admin.get('/api/skills/forms').json
    original = next(f for f in inventory['forms'] if f['id']=='test-form-v1')
    assert original['eligible_replacements'] == ['replacement']
    assert original['available'] and original['lifecycle']['status']=='active'
    assert 'items' not in original and 'body' not in original
    assert withdraw(admin, token, 'descendant').status_code == 409
    assert withdraw(admin, token, 'replacement').status_code == 201
    original = next(f for f in admin.get('/api/skills/forms').json['forms'] if f['id']=='test-form-v1')
    assert original['lifecycle']['replacement_id']=='replacement'
    assert original['eligible_replacements']==[]
