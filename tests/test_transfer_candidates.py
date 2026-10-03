"""Private content conversion and runtime exposure checks, not semantic acceptance."""
import copy
import hashlib
import json
import sqlite3

import pytest

from club.transfer_candidates import BLUEPRINTS, candidates
from club.skills import form_exposure_keys, publish_reviewed_form
from club.skill_seed import graph_fixture
from test_learning import app, login, post
from test_skills import skills


def test_conversion_preserves_canonical_sources_and_observations():
    forms = candidates()
    assert len(forms) == 7
    for original, candidate in zip(BLUEPRINTS, forms):
        assert candidate['source_snapshot'] == original['source']
        assert not candidate['equivalence']['approved']
        assert candidate['publication_blockers']
        assert candidate['thresholds']['overall'] == 3
        assert candidate['thresholds']['objectives'] == {original['objective_id']: 3}
        for decision, item in zip(original['decisions'], candidate['form']['items']):
            assert item['lineage_id'] == decision['lineage_id']
            assert item['rationale'] == decision['expected']
            assert item['source']['sha256'] == hashlib.sha256(item['source']['text'].encode()).hexdigest()
            assert next(c['text'] for c in item['choices'] if c['id'] == item['answer']) == decision['expected']
    assert [c['id'] for c in forms if c['practical_proposal']] == ['transfer-B-mobile', 'transfer-B-tools']


def test_source_tamper_fails_without_silent_repin(monkeypatch):
    changed = copy.deepcopy(BLUEPRINTS)
    changed[0]['source']['text'] += ' changed'
    monkeypatch.setattr('club.transfer_candidates.BLUEPRINTS', changed)
    with pytest.raises(ValueError, match='new edition'):
        candidates()


def test_export_is_private_read_only_and_runtime_lineage_survives_repackaging(skills):
    preview = candidates()
    client = skills.test_client()
    assert client.get('/static/transfer_blueprints.json').status_code == 404
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM skill_forms').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM skill_evidence').fetchone()[0] == 0
        # Test-only publication exercises existing engine. No export API publishes.
        form = preview[0]['form']
        publish_reviewed_form(db, id='transfer-test', graph=graph_fixture(), node_id=preview[0]['node_id'],
                              form=form, access='free', reviewer='user-admin')
    token = login(client)
    attempt = post(client, '/api/skills/challenges', {'assessment_id':'transfer-test','request_id':'transfer-first'}, token).json
    public = json.dumps(attempt, ensure_ascii=False)
    for item in form['items']:
        assert 'rationale' not in public
        assert '"answer"' not in public
    result = post(client, '/api/skills/challenges/'+attempt['id']+'/submit',
                  {'answers':{i['id']:i['answer'] for i in form['items']}}, token).json
    assert result['credited']
    repackaged = copy.deepcopy(form)
    for item in repackaged['items']:
        item['id'] += '-new'
        item['prompt'] += ' Выберите решение.'
        item['choices'].reverse()
    assert form_exposure_keys(form) & form_exposure_keys(repackaged)
    with sqlite3.connect(skills.config['DATABASE']) as db:
        publish_reviewed_form(db, id='transfer-repackaged', graph=graph_fixture(), node_id=preview[0]['node_id'],
                              form=repackaged, access='free', reviewer='user-admin')
    repeat = post(client, '/api/skills/challenges', {'assessment_id':'transfer-repackaged','request_id':'transfer-second'}, token).json
    assert repeat['mode'] == 'practice'
    post(client, '/api/skills/challenges/'+repeat['id']+'/submit',
         {'answers':{i['id']:i['answer'] for i in repackaged['items']}}, token)
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM skill_evidence').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM skill_application_evidence').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM progress').fetchone()[0] == 0
