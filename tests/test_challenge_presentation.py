"""Synthetic local publications test delivery, not editorial acceptance."""
import json
import sqlite3
import uuid

import pytest

from club import create_app
from club.skill_seed import graph_fixture
from club.skills import form_exposure_keys
from club.transfer_candidates import candidates
from club.transfer_sources import install_sources, publication_candidate, publish_transfer
from test_learning import app, login, post
from test_skills import skills, install_form, fixture_form


@pytest.mark.parametrize('candidate_id', [c['id'] for c in candidates()])
def test_exact_preanswer_case_and_stable_restart_presentation(skills, candidate_id):
    with sqlite3.connect(skills.config['DATABASE']) as db:
        install_sources(db, 'user-admin')
        candidate = publication_candidate(db, candidate_id, 'presentation-fixture', 'foundations-start-01')
        publish_transfer(db, candidate_id=candidate_id, form_id='presentation-fixture',
                         lesson_id='foundations-start-01', graph=graph_fixture(), reviewer='user-admin',
                         reviewed_sha256=candidate['sha256'], confirm_reviewed=True)
        original = db.execute("SELECT body FROM skill_forms WHERE id='presentation-fixture'").fetchone()[0]
    client = skills.test_client()
    csrf = login(client)
    payload = {'assessment_id': 'presentation-fixture', 'request_id': 'presentation-request'}
    response = post(client, '/api/skills/challenges', payload, csrf)
    assert response.status_code == 201
    attempt = response.json
    assert attempt['id'].startswith('p1-')
    assert post(client, '/api/skills/challenges', payload, csrf).json == attempt
    for public, private in zip(attempt['items'], candidate['form']['items']):
        assert public['case']['text'] == candidate['source_snapshot']['text']
        assert public['case']['sha256'] == private['source']['sha256']
        assert set(public) == {'id', 'prompt', 'type', 'objective_id', 'choices', 'case'}
        assert set(public['case']) == {'source_id', 'edition', 'paragraph', 'text', 'sha256'}
        assert sorted(public['choices'], key=lambda c: c['id']) == private['choices']
        assert all(set(choice) == {'id', 'text'} for choice in public['choices'])
    assert form_exposure_keys({'items': attempt['items']}) <= form_exposure_keys(candidate['form'])
    restarted = create_app(dict(TESTING=True, DATABASE=skills.config['DATABASE'], SECRET_KEY='new-process'))
    new_client = restarted.test_client()
    login(new_client)
    path = '/api/skills/challenges/' + attempt['id']
    assert new_client.get(path).json['items'] == attempt['items']
    other = skills.test_client(); login(other, 'member')
    assert other.get(path).status_code == 404
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute("UPDATE lessons SET access='member' WHERE id='foundations-start-01'")
    assert new_client.get(path).status_code == 403
    assert post(client, '/api/skills/challenges', payload, csrf).status_code == 403
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute("UPDATE lessons SET access='free' WHERE id='foundations-start-01'")
    result = post(client, path + '/submit', {'answers': {i['id']: i['answer'] for i in candidate['form']['items']}}, csrf)
    assert result.status_code == 200 and result.json['credited']
    assert client.get(path).json['items'] == attempt['items']
    repeat = post(client, '/api/skills/challenges', dict(payload, request_id='presentation-repeat'), csrf).json
    assert repeat['mode'] == 'practice'
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute("SELECT body FROM skill_forms WHERE id='presentation-fixture'").fetchone()[0] == original
        assert db.execute('SELECT count(*) FROM skill_evidence').fetchone()[0] == 1
        assert db.execute('SELECT count(*) FROM progress').fetchone()[0] == 0


def test_legacy_attempt_order_and_result_remain_unchanged(skills):
    install_form(skills)
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute("INSERT INTO skill_attempts(id,user_id,form_id,request_id,mode) VALUES('historical-uuid','user-learner','test-form-v1','old-request','certification')")
    client = skills.test_client(); csrf = login(client)
    path = '/api/skills/challenges/historical-uuid'
    before = client.get(path).json
    assert [i['choices'] for i in before['items']] == [i['choices'] for i in fixture_form()['items']]
    assert all('case' not in i for i in before['items'])
    result = post(client, path + '/submit', {'answers': {'q1': 'check', 'q2': 'check'}}, csrf)
    assert result.json['credited']
    assert client.get(path).json['items'] == before['items']
    assert client.get(path).json['result'] == result.json


def test_new_attempts_vary_display_without_mutating_choice_ids(skills, monkeypatch):
    identities = iter(uuid.UUID(int=n) for n in range(1, 13))
    monkeypatch.setattr('club.skills.uuid.uuid4', lambda: next(identities))
    install_form(skills)
    client = skills.test_client(); csrf = login(client)
    orders = set()
    for n in range(12):
        attempt = post(client, '/api/skills/challenges', {'assessment_id': 'test-form-v1', 'request_id': f'varied-order-{n}'}, csrf).json
        orders.add(tuple(tuple(c['id'] for c in i['choices']) for i in attempt['items']))
        result = post(client, '/api/skills/challenges/' + attempt['id'] + '/submit', {'answers': {'q1': 'check', 'q2': 'check'}}, csrf)
        assert result.json['credited'] == (n == 0)
    assert len(orders) > 1


@pytest.mark.parametrize('broken', ['missing', 'hash'])
def test_invalid_case_binding_fails_closed_and_rolls_back_attempt(skills, broken):
    from club.skills import publish_reviewed_form
    with sqlite3.connect(skills.config['DATABASE']) as db:
        install_sources(db, 'user-admin')
        candidate = publication_candidate(db, candidates()[0]['id'], 'invalid-binding', 'foundations-start-01')
        form = candidate['form']
        for item in form['items']:
            item['source']['source_id' if broken == 'missing' else 'sha256'] = 'invalid'
        publish_reviewed_form(db, id='invalid-binding', graph=graph_fixture(),
                              node_id=candidate['node_id'], form=form, access='free', reviewer='user-admin')
    client = skills.test_client(); csrf = login(client)
    response = post(client, '/api/skills/challenges',
                    {'assessment_id': 'invalid-binding', 'request_id': 'invalid-binding-request'}, csrf)
    assert response.status_code == 409
    assert candidate['source_snapshot']['text'] not in response.get_data(as_text=True)
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT count(*) FROM skill_attempts').fetchone()[0] == 0
