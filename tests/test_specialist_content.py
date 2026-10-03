"""Content installation safety; semantic acceptance belongs to learning review."""
import hashlib
import json
import sqlite3

from club.foundation_content import release_id as foundation_release
from club.skill_content import RELEASE, CASES as EXAMPLES, candidate_form
from club.specialist_content import CASES, COURSE, lesson_id, release_id
from test_learning import app, login, post
from test_skills import skills
from test_skill_content import install, review
from test_foundation_content import foundations


def specialists(app, parent=RELEASE, reviewer='user-admin'):
    return app.test_cli_runner().invoke(args=['install-skill-specialists', '--from-release', parent, '--reviewer', reviewer])


def snapshot(app):
    with sqlite3.connect(app.config['DATABASE']) as db:
        return {table: db.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall()
                for table in ('lessons', 'progress', 'practice', 'skill_forms', 'skill_attempts', 'skill_evidence')}


def test_additive_install_preserves_sources_history_exposure_and_covers_tree(skills):
    install(skills); review(skills)
    assert foundations(skills).exit_code == 0
    parent = foundation_release(RELEASE)
    c = skills.test_client(); token = login(c)
    form_id = 'skill-example-form-verification-v1'
    attempt = post(c, '/api/skills/challenges', dict(assessment_id=form_id, request_id='before-specialists'), token).json
    answers = {i['id']: i['answer'] for i in candidate_form(EXAMPLES[0])['items']}
    result = post(c, '/api/skills/challenges/'+attempt['id']+'/submit', dict(answers=answers), token).json
    assert result['credited']
    post(c, '/api/lessons/foundations-start-01/completion', dict(completed=True), token)
    post(c, '/api/lessons/foundations-start-01/practice', dict(body='Saved original work', status='draft'), token)
    before = snapshot(skills)
    outcome = specialists(skills, parent)
    assert outcome.exit_code == 0, outcome.output
    assert specialists(skills, parent).exit_code == 0
    after = snapshot(skills)
    assert len(after['lessons']) == len(before['lessons']) + 16
    for table, rows in before.items():
        assert all(row in after[table] for row in rows)
        if table != 'lessons':
            assert rows == after[table]
    graph = c.get('/api/skills/graph').json
    assert graph['release'] == release_id(parent)
    abilities = {n['id'] for n in graph['nodes'] if n['kind'] == 'ability'}
    with sqlite3.connect(skills.config['DATABASE']) as db:
        stored = json.loads(db.execute('SELECT body FROM skill_releases WHERE id=?', (graph['release'],)).fetchone()[0])
    assert abilities == {m['objective_id'] for m in stored['mappings']}
    for case in CASES:
        node = c.get('/api/skills/nodes/'+case['objective']).json
        assert len(node['content']) == 1 and node['assessments'] == []
        response = c.get('/api/lessons/'+lesson_id(case))
        assert response.status_code == 200
        assert case['artifact'] in response.json['body']
    assert c.get('/api/skills/challenges/'+attempt['id']).json['result'] == result
    repeat = post(c, '/api/skills/challenges', dict(assessment_id=form_id,request_id='after-specialists'), token).json
    assert repeat['mode'] == 'practice'
    assert c.get('/api/skills/me').json['coverage'][0]['unknown'] == 25


def test_inventory_hashes_pin_actual_persisted_sources_and_practice(skills):
    install(skills)
    assert specialists(skills).exit_code == 0
    output = skills.test_cli_runner().invoke(args=['inspect-skill-specialists'])
    assert output.exit_code == 0, output.output
    inventory = json.loads(output.output)
    assert len(inventory['lessons']) == 16
    with sqlite3.connect(skills.config['DATABASE']) as db:
        for row in inventory['lessons']:
            body = db.execute('SELECT body FROM lessons WHERE id=?', (row['lesson_id'],)).fetchone()[0]
            assert row['body_sha256'] == hashlib.sha256(body.encode()).hexdigest()
            for ref, paragraph in zip(row['sources'], row['paragraphs']):
                assert paragraph in body
                assert ref['sha256'] == hashlib.sha256(paragraph.encode()).hexdigest()
                assert ref['lesson_id'] == row['lesson_id'] and ref['edition'] == 1
            assert row['assessment_published'] is False
        db.execute('UPDATE lessons SET task=? WHERE id=?', ('Different task', lesson_id(CASES[0])))
    assert skills.test_cli_runner().invoke(args=['inspect-skill-specialists']).exit_code != 0


def test_stale_rebase_role_collision_and_changed_semantics_fail_closed(skills):
    install(skills)
    assert specialists(skills, reviewer='user-learner').exit_code != 0
    assert specialists(skills, parent='tree-2026-10-v1').exit_code != 0
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute('''INSERT INTO lessons(id,module_id,title,objective,body,minutes,position,access)
                      SELECT ?,module_id,title,objective,body,minutes,position,access FROM lessons LIMIT 1''', (lesson_id(CASES[-1]),))
    before = snapshot(skills)
    assert specialists(skills).exit_code != 0
    assert snapshot(skills) == before
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM courses WHERE id=?', (COURSE,)).fetchone()[0] == 0
        assert db.execute('SELECT release_id FROM skill_active').fetchone()[0] == RELEASE
        db.execute('DELETE FROM lessons WHERE id=?', (lesson_id(CASES[-1]),))
        graph = json.loads(db.execute('SELECT body FROM skill_releases WHERE id=?', (RELEASE,)).fetchone()[0])
        next(n for n in graph['nodes'] if n['id'] == CASES[0]['objective'])['revision'] = 2
        graph['release'] = 'changed-semantics'
        db.execute('INSERT INTO skill_releases(id,body) VALUES(?,?)', (graph['release'], json.dumps(graph)))
        db.execute('UPDATE skill_active SET release_id=?', (graph['release'],))
    outcome = specialists(skills, parent='changed-semantics')
    assert outcome.exit_code != 0 and 'semantic review' in outcome.output


def test_install_creates_restorable_private_backup(skills):
    from pathlib import Path
    install(skills)
    assert specialists(skills).exit_code == 0
    backups = list(Path(skills.config['DATABASE']).parent.glob('*.before-specialists-*.sqlite'))
    assert len(backups) == 1 and backups[0].stat().st_mode & 0o777 == 0o600
    with sqlite3.connect(backups[0]) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('SELECT release_id FROM skill_active').fetchone()[0] == RELEASE
        assert db.execute('SELECT COUNT(*) FROM courses WHERE id=?', (COURSE,)).fetchone()[0] == 0


def test_debug_source_reproduces_sort_defect_with_valid_json():
    case = next(case for case in CASES if case['slug'] == 'debug')
    raw = case['paragraphs'][0].split('Вход JSON: ', 1)[1].split('. Текущий код', 1)[0]
    rows = json.loads(raw)
    assert [row['id'] for row in sorted(rows, key=lambda row: str(row['priority']))] == ['B', 'A']
    assert [row['id'] for row in sorted(rows, key=lambda row: row['priority'])] == ['A', 'B']


def test_old_installed_pack_requires_reconciliation_without_repinning(skills, monkeypatch):
    import copy
    from club import specialist_content
    install(skills)
    old_cases = copy.deepcopy(CASES)
    debug = next(case for case in old_cases if case['slug'] == 'debug')
    debug['paragraphs'][0] = debug['paragraphs'][0].replace(
        '[{"id":"A","priority":2},{"id":"B","priority":10}]',
        '[{id:A, priority:2}, {id:B, priority:10}]')
    old_hash = hashlib.sha256(json.dumps(old_cases, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    with monkeypatch.context() as old:
        old.setattr(specialist_content, 'CASES', old_cases)
        old.setattr(specialist_content, 'PACK_HASH', old_hash)
        assert specialists(skills).exit_code == 0
        old_release = specialist_content.release_id(RELEASE)
    before = snapshot(skills)
    outcome = specialists(skills, parent=old_release)
    assert outcome.exit_code != 0 and 'explicit reconciliation' in outcome.output
    assert snapshot(skills) == before
    inspection = skills.test_cli_runner().invoke(args=['inspect-skill-specialists'])
    assert inspection.exit_code != 0 and 'new edition and review required' in inspection.output
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT release_id FROM skill_active').fetchone()[0] == old_release
