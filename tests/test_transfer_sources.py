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
