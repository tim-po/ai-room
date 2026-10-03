import json
import sqlite3

import pytest

from club.transfer_sources import bound_candidates
from club.transfer_candidates import candidates
from club.skills import form_exposure_keys
from test_learning import app, login
from test_skills import skills


def test_install_retains_private_sources_and_lineage(skills):
    runner = skills.test_cli_runner()
    assert runner.invoke(args=['inspect-transfer-sources']).exit_code != 0
    assert runner.invoke(args=['install-transfer-sources', '--reviewer', 'user-learner']).exit_code != 0
    installed = runner.invoke(args=['install-transfer-sources', '--reviewer', 'user-admin'])
    assert installed.exit_code == 0, installed.output
    assert 'Retained 0' in runner.invoke(args=['install-transfer-sources', '--reviewer', 'user-admin']).output
    preview = runner.invoke(args=['inspect-transfer-sources'])
    assert preview.exit_code == 0, preview.output
    bound = json.loads(preview.output)
    for before, after in zip(candidates(), bound):
        assert form_exposure_keys(before['form']) == form_exposure_keys(after['form'])
        assert before['sha256'] == after['unbound_sha256'] != after['sha256']
        assert after['publication_blockers'] and not after['equivalence']['approved']
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT count(*) FROM skill_transfer_sources').fetchone()[0] == 7
        for table in ['skill_forms', 'skill_evidence', 'skill_application_evidence', 'progress']:
            assert db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0
        with pytest.raises(sqlite3.IntegrityError, match='immutable'):
            db.execute("UPDATE skill_transfer_sources SET body='{}'")
        with pytest.raises(sqlite3.IntegrityError, match='retain'):
            db.execute('DELETE FROM skill_transfer_sources')
        assert len(bound_candidates(db)) == 7
    client = skills.test_client()
    url = bound[0]['form']['items'][0]['source']['snapshot_url']
    assert client.get(url).status_code == 403
    login(client)
    assert client.get(url).status_code == 403
    admin = skills.test_client()
    login(admin, 'admin')
    response = admin.get(url)
    assert response.status_code == 200
    assert response.json == bound[0]['source_snapshot']
    assert 'no-store' in response.headers['Cache-Control']
    assert 'answer' not in response.json
    assert admin.get(url+'/file').status_code == 404
    assert admin.get('/api/skills/editorial-sources/missing/1').status_code == 404


@pytest.mark.parametrize('lesson_id,who', [('foundations-start-01', 'learner'), ('foundations-context-01', 'member')])
def test_reviewed_publication_feedback_and_live_boundaries(skills, lesson_id, who):
    from club.transfer_sources import install_sources, publication_candidate, publish_transfer
    from club.skill_seed import graph_fixture
    from test_learning import post
    with sqlite3.connect(skills.config['DATABASE']) as db:
        install_sources(db, 'user-admin')
        candidate = publication_candidate(db, candidates()[0]['id'], 'reviewed-transfer', lesson_id)
        args = dict(candidate_id=candidate['id'], form_id='reviewed-transfer', lesson_id=lesson_id,
                    graph=graph_fixture(), reviewer='user-admin', reviewed_sha256=candidate['sha256'])
        with pytest.raises(ValueError, match='exact-hash'):
            publish_transfer(db, **args)
        with pytest.raises(ValueError, match='exact-hash'):
            publish_transfer(db, **dict(args, reviewed_sha256='stale'), confirm_reviewed=True)
        db.execute("UPDATE lessons SET status='draft' WHERE id=?", (lesson_id,))
        with pytest.raises(ValueError, match='Published'):
            publish_transfer(db, **args, confirm_reviewed=True)
        db.execute("UPDATE lessons SET status='published' WHERE id=?", (lesson_id,))
        publish_transfer(db, **args, confirm_reviewed=True)
    client = skills.test_client()
    csrf = login(client, who)
    attempt = post(client, '/api/skills/challenges', {'assessment_id':'reviewed-transfer','request_id':'bound-source-attempt'}, csrf)
    assert attempt.status_code == 201
    result = post(client, '/api/skills/challenges/'+attempt.json['id']+'/submit',
                  {'answers':{i['id']:i['answer'] for i in candidate['form']['items']}}, csrf)
    assert result.status_code == 200
    url = result.json['feedback'][0]['source']['snapshot_url']
    source = client.get(url)
    assert source.status_code == 200 and source.json == candidate['source_snapshot']
    assert 'no-store' in source.headers['Cache-Control']
    assert client.get(url.rsplit('/', 1)[0]+'/999').status_code == 404
    private_url = bound_candidates(sqlite3.connect(skills.config['DATABASE']))[0]['form']['items'][0]['source']['snapshot_url']
    assert client.get(private_url).status_code == 403
    if who == 'member':
        assert skills.test_client().get(url).status_code == 403
        with sqlite3.connect(skills.config['DATABASE']) as db:
            db.execute("UPDATE users SET entitlement='revoked' WHERE id='user-member'")
        assert client.get(url).status_code == 403
        with sqlite3.connect(skills.config['DATABASE']) as db:
            db.execute("UPDATE users SET entitlement='member' WHERE id='user-member'")
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute("UPDATE lessons SET body='Changed current teaching' WHERE id=?", (lesson_id,))
    assert client.get(url).json == source.json
    for status in ['draft', 'archived']:
        with sqlite3.connect(skills.config['DATABASE']) as db:
            db.execute('UPDATE lessons SET status=? WHERE id=?', (status, lesson_id))
        assert client.get(url).status_code == 403
        assert client.get('/api/skills/challenges/'+attempt.json['id']).status_code == 403
        assert not client.get('/api/skills/me').json['evidence'][0]['sources']
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute("UPDATE lessons SET status='published' WHERE id=?", (lesson_id,))
    admin = skills.test_client(); token = login(admin, 'admin')
    assert post(admin, '/api/skills/forms/reviewed-transfer/withdraw',
                {'confirm_reviewed':True, 'reason':'Withdraw test source publication'}, token).status_code == 201
    assert client.get(url).status_code == 404
    assert admin.get(url).status_code == 200
