import json
import sqlite3

import pytest

from club.curriculum_revisions import prepare, install
from test_learning import app, login, post
from test_skills import skills, install_form


def connect(skills):
    db = sqlite3.connect(skills.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db


def test_reviewed_revision_retains_sources_and_learner_state(skills):
    client = skills.test_client(); csrf = login(client, 'member')
    lesson = 'foundations-context-01'
    post(client, '/api/lessons/'+lesson+'/completion', {'completed': True}, csrf)
    post(client, '/api/lessons/'+lesson+'/video', {'seconds': 7.5}, csrf)
    post(client, '/api/lessons/'+lesson+'/practice', {'body': 'Retain my work', 'status': 'submitted'}, csrf)
    install_form(skills)
    with connect(skills) as db:
        protected = ['progress', 'practice', 'skill_forms', 'skill_evidence', 'skill_application_evidence']
        before = {table: [tuple(r) for r in db.execute('SELECT * FROM '+table)] for table in protected}
        proposal = prepare(db)
        assert len(proposal['manifest']['revisions']) == 2
        for r in proposal['manifest']['revisions']:
            assert len(r['after']['body']) > 1600
            assert r['after']['id'] == r['before']['id']
            assert r['after']['access'] == r['before']['access']
            assert r['before_sha256'] != r['after_sha256']
        assert install(db, reviewer='user-admin', reviewed_sha256=proposal['sha256'], confirm_reviewed=True)
        assert not install(db, reviewer='user-admin', reviewed_sha256=proposal['sha256'], confirm_reviewed=True)
        assert before == {table: [tuple(r) for r in db.execute('SELECT * FROM '+table)] for table in protected}
        retained = json.loads(db.execute('SELECT body FROM skill_curriculum_revisions').fetchone()[0])
        assert retained == proposal['manifest']
        assert db.execute('SELECT count(*) FROM skill_form_bindings').fetchone()[0] == 1
        for r in retained['revisions']:
            assert dict(db.execute('SELECT * FROM lessons WHERE id=?', (r['lesson_id'],)).fetchone()) == r['after']
        with pytest.raises(sqlite3.IntegrityError, match='immutable'):
            db.execute("UPDATE skill_curriculum_revisions SET body='{}'")
        with pytest.raises(sqlite3.IntegrityError, match='retain'):
            db.execute('DELETE FROM skill_curriculum_revisions')
    assert client.get('/api/lessons/'+lesson).status_code == 200
    assert skills.test_client().get('/api/lessons/'+lesson).status_code == 403


@pytest.mark.parametrize('mutation', ['lesson', 'graph', 'role', 'confirmation'])
def test_review_boundaries_reject_without_partial_changes(skills, mutation):
    with connect(skills) as db:
        proposal = prepare(db)
        args = dict(reviewer='user-admin', reviewed_sha256=proposal['sha256'], confirm_reviewed=True)
        if mutation == 'lesson':
            db.execute("UPDATE lessons SET task='Editorial change' WHERE id='foundations-context-01'")
        elif mutation == 'graph':
            body = json.loads(db.execute('SELECT body FROM skill_releases').fetchone()[0])
            body['nodes'][0]['title'] = 'Edited definition'
            db.execute('INSERT INTO skill_releases(id,body) VALUES(?,?)', ('changed', json.dumps(dict(body, release='changed'))))
            db.execute("UPDATE skill_active SET release_id='changed'")
        elif mutation == 'role':
            args['reviewer'] = 'user-learner'
        else:
            args['confirm_reviewed'] = False
        state = [tuple(row) for row in db.execute('SELECT * FROM lessons')]
        with pytest.raises(ValueError):
            install(db, **args)
        assert state == [tuple(row) for row in db.execute('SELECT * FROM lessons')]
        assert db.execute('SELECT count(*) FROM skill_curriculum_revisions').fetchone()[0] == 0


def test_failed_graph_carry_rolls_back_and_replay_preserves_later_edits(skills, monkeypatch):
    import club.curriculum_revisions as module
    with connect(skills) as db:
        proposal = prepare(db)
        args = dict(reviewer='user-admin', reviewed_sha256=proposal['sha256'], confirm_reviewed=True)
        original = module.carry_forms
        def fail(*args):
            raise ValueError('Simulated compatibility failure')
        monkeypatch.setattr(module, 'carry_forms', fail)
        with pytest.raises(ValueError, match='compatibility'):
            install(db, **args)
        assert prepare(db) == proposal
        assert db.execute('SELECT count(*) FROM skill_curriculum_revisions').fetchone()[0] == 0
        monkeypatch.setattr(module, 'carry_forms', original)
        install(db, **args)
        db.execute("UPDATE lessons SET body='Later editorial text' WHERE id='foundations-context-01'")
        assert not install(db, **args)
        assert db.execute("SELECT body FROM lessons WHERE id='foundations-context-01'").fetchone()[0] == 'Later editorial text'


def test_cli_backs_up_before_applying_reviewed_hash(skills):
    import subprocess
    import sys
    from pathlib import Path
    database = skills.config['DATABASE']
    command = [sys.executable, '-m', 'club.curriculum_revisions', '--database', database]
    proposal = json.loads(subprocess.check_output(command, text=True))
    result = json.loads(subprocess.check_output(command + ['--reviewer', 'user-admin',
                        '--reviewed-sha256', proposal['sha256']], text=True))
    assert result['installed'] is True
    backup = Path(result['backup'])
    assert backup.stat().st_mode & 0o777 == 0o600
    with sqlite3.connect(backup) as db:
        assert db.execute('SELECT count(*) FROM skill_curriculum_revisions').fetchone()[0] == 0
        assert prepare(db) == proposal
    with connect(skills) as db:
        release = db.execute('SELECT release_id FROM skill_active').fetchone()[0]
        tree = json.loads(db.execute('SELECT body FROM skill_releases WHERE id=?', (release,)).fetchone()[0])
        rows = [m for m in tree['mappings'] if m['lesson_id'] in ['foundations-context-01', 'foundations-context-02']]
        assert len(rows) == 2
        assert all(m['objective_id'] == 'basic-ai.context' and m['role'] == 'teaches' for m in rows)
        assert all(m['source']['revision_id'] == proposal['sha256'] for m in rows)
