import json
import sqlite3
from pathlib import Path

import pytest
from club import create_app
from test_learning import app, login, post, token, PASSWORD, FREE, PAID
from test_skills import skills, install_form


@pytest.fixture()
def onboard(skills):
    result = skills.test_cli_runner().invoke(args=['init-onboarding'])
    assert result.exit_code == 0, result.output
    return skills


def put(c, csrf, state, action, **extra):
    payload = dict(action=action, expected_revision=state['revision'], idempotency_key='request-'+str(state['revision']), **extra)
    return c.put('/api/onboarding', json=payload, headers={'X-CSRF-Token':csrf})


def test_complete_restart_replay_conflict_isolation(onboard):
    c = onboard.test_client(); csrf = login(c)
    state = c.get('/api/onboarding').json
    assert state['status'] == 'not_started'
    first = put(c, csrf, state, 'next')
    assert first.status_code == 200
    assert put(c, csrf, state, 'next').json == first.json
    assert put(c, csrf, state, 'save').status_code == 409
    stale = dict(action='save', expected_revision=0, idempotency_key='other-key')
    assert c.put('/api/onboarding',json=stale,headers={'X-CSRF-Token':csrf}).status_code == 409
    state = put(c, csrf, first.json, 'next', draft={'interests':['coding','content']}).json
    assert state['step'] == 'pace'
    post(c, '/logout', {}, csrf)
    restarted = create_app(dict(TESTING=True, DATABASE=onboard.config['DATABASE'], SECRET_KEY='test-only-key'))
    c = restarted.test_client(); csrf = login(c)
    assert c.get('/api/onboarding').json == state
    state = put(c, csrf, state, 'next', draft={'available_minutes':10}).json
    state = put(c, csrf, state, 'complete').json
    assert state['status'] == 'completed'
    assert c.get('/').location == '/discover' and c.get('/discover').status_code == 200
    assert c.get('/api/skills/me').json['interests'] == ['coding','content']
    other = onboard.test_client(); login(other,'member')
    assert other.get('/api/onboarding').json['draft']['interests'] == []
    with sqlite3.connect(onboard.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM skill_evidence').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM progress').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM onboarding_events_v1').fetchone()[0] == 4
        assert not db.execute("SELECT 1 FROM events WHERE name='onboarding_completed'").fetchone()


def test_edit_cancel_skip_preserve_committed(onboard):
    c = onboard.test_client(); csrf = login(c)
    s = c.get('/api/onboarding').json
    s = put(c, csrf, s, 'next', draft={'interests':['coding']}).json
    s = put(c, csrf, s, 'skip').json
    assert s['status'] == 'skipped' and s['draft']['interests'] == ['coding']
    assert s['committed_preferences']['interests'] == []
    s = put(c, csrf, s, 'edit').json
    s = put(c, csrf, s, 'save', draft={'interests':['content']}).json
    s = put(c, csrf, s, 'cancel').json
    assert s['draft']['interests'] == [] and s['status'] == 'skipped'
    assert c.get('/').location == '/discover' and c.get('/discover').status_code == 200


def test_safe_deeplink_rechecks_revocation_even_on_replay(onboard):
    c = onboard.test_client()
    csrf = token(c)
    r = c.post('/login?next=/lessons/'+PAID, data={'email':'member@example.test','password':PASSWORD,'csrf':csrf})
    assert r.location == '/onboarding'
    with c.session_transaction() as sess:
        csrf = sess['csrf']
    s = c.get('/api/onboarding').json
    assert s['return_to'] == '/lessons/'+PAID
    acknowledged = put(c, csrf, s, 'skip')
    assert acknowledged.json['next_url'] == '/lessons/'+PAID
    with sqlite3.connect(onboard.config['DATABASE']) as db:
        db.execute("UPDATE users SET entitlement='revoked' WHERE email='member@example.test'")
    assert put(c, csrf, s, 'skip').json['next_url'] == '/'
    for target in ['//evil.test', '/%2fevil.test', '/admin', '/lessons/'+PAID]:
        fresh = onboard.test_client()
        r = fresh.post('/login', query_string={'next':target}, data={'email':'member@example.test','password':PASSWORD,'csrf':token(fresh)})
        assert r.location == '/'


def test_roles_csrf_validation_and_unchanged_save_telemetry(onboard):
    c = onboard.test_client()
    assert c.get('/api/onboarding').status_code == 401
    login(c,'admin')
    assert c.get('/api/onboarding').status_code == 200   # staff can walk through it; only learners are sent there
    csrf = login(c)
    assert c.put('/api/onboarding',json={}).status_code == 400
    s = c.get('/api/onboarding').json
    for patch in [{'interests':['nonexistent']}, {'experience':'expert'}, {'available_minutes':True}, {'diagnostic_choice':'auto'}, {'user_id':'member'}]:
        assert put(c,csrf,s,'save',draft=patch).status_code == 400
    assert put(c,csrf,s,'complete').status_code == 400
    s = put(c,csrf,s,'save').json
    s = put(c,csrf,s,'save').json
    with sqlite3.connect(onboard.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM onboarding_events_v1').fetchone()[0] == 0
    assert c.get('/lessons/'+FREE).location == '/onboarding'
    assert c.get('/api/lessons/'+FREE).status_code == 200
    # The app's page data waits for onboarding too; the app follows the redirect.
    for path in ['/api/app/home', '/api/app/catalogue', '/api/app/discover', '/api/app/search?q=x', '/api/app/lessons/'+FREE, '/api/app/profile']:
        response = c.get(path)
        assert response.status_code == 409 and response.json['redirect'] == '/onboarding', path


def test_paired_backup_backfill_and_idempotent_migration(skills, tmp_path):
    c = skills.test_client(); csrf = login(c)
    post(c,'/api/lessons/'+FREE+'/completion',{'completed':True},csrf)
    post(c,'/api/lessons/'+FREE+'/practice',{'body':'retained work','status':'submitted'},csrf)
    install_form(skills)
    attempt = post(c,'/api/skills/challenges',{'assessment_id':'test-form-v1','request_id':'retained'},csrf).json
    post(c,'/api/skills/challenges/'+attempt['id']+'/submit',{'answers':{'q1':'check','q2':'check'}},csrf)
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute("UPDATE users SET onboarding_done=1,weekly_goal=4 WHERE email='learner@example.test'")
        before = {t:db.execute('SELECT * FROM '+t).fetchall() for t in ['users','progress','practice','skill_attempts','skill_results','skill_evidence']}
    # Isolated media fixture; never modify shared retained files.
    skills.instance_path = str(tmp_path/'private-instance')
    media = Path(skills.instance_path)/'media'; media.mkdir(parents=True)
    (media/'fixture.webm').write_bytes(b'labelled test fixture')
    uploads = Path(skills.config['TEACHING_UPLOAD_DIR']); uploads.mkdir(exist_ok=True)
    (uploads/'fixture.txt').write_text('labelled material')
    for _ in range(2):
        result = skills.test_cli_runner().invoke(args=['init-onboarding'])
        assert result.exit_code == 0, result.output
    with sqlite3.connect(skills.config['DATABASE']) as db:
        for table, rows in before.items():
            assert db.execute('SELECT * FROM '+table).fetchall() == rows
        assert db.execute('PRAGMA user_version').fetchone()[0] == 6
    backups = list(tmp_path.glob('before-onboarding-*'))
    assert len(backups) == 2
    assert (backups[0]/'media/fixture.webm').read_bytes() == b'labelled test fixture'
    assert (backups[0]/'teaching-uploads/fixture.txt').read_text() == 'labelled material'
    assert c.get('/api/onboarding').json['status'] == 'completed'
    assert c.get('/').location == '/discover' and c.get('/discover').status_code == 200
    assert c.get('/api/onboarding').json['diagnostic']['available']


def test_legacy_preferences_skip_remains_compatible(onboard):
    c = onboard.test_client(); csrf = login(c)
    s = put(c, csrf, c.get('/api/onboarding').json, 'next').json
    assert s['status'] == 'in_progress'
    assert c.post('/preferences/skip', data={'csrf':csrf}).status_code == 302
    assert c.get('/api/onboarding').json['status'] == 'completed'
    assert c.get('/').location == '/discover' and c.get('/discover').status_code == 200


def test_no_diagnostic_when_all_forms_withdrawn(onboard):
    install_form(onboard)
    c = onboard.test_client(); login(c)
    assert c.get('/api/onboarding').json['diagnostic']['available']
    with sqlite3.connect(onboard.config['DATABASE']) as db:
        reviewer = db.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
        db.execute('INSERT INTO skill_form_withdrawals(form_id,reviewer_id,reason) VALUES(?,?,?)', ('test-form-v1',reviewer,'Synthetic test withdrawal'))
    s = c.get('/api/onboarding').json
    assert not s['diagnostic']['available']
    assert s['recommendation']['url'].startswith('/lessons/')


def test_competing_tabs_only_one_revision_commits(onboard):
    from concurrent.futures import ThreadPoolExecutor
    clients = [onboard.test_client(), onboard.test_client()]
    tokens = [login(c) for c in clients]
    def save(index):
        return clients[index].put('/api/onboarding', json={
            'action':'next', 'expected_revision':0, 'idempotency_key':'parallel-key-'+str(index),
            'draft':{'interests':[['coding'],['content']][index]}},
            headers={'X-CSRF-Token':tokens[index]}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, range(2))) == [200,409]
    state = clients[0].get('/api/onboarding').json
    assert state['revision'] == 1 and state['draft']['interests'] in [['coding'],['content']]
    with sqlite3.connect(onboard.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM onboarding_requests').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM onboarding_events_v1').fetchone()[0] == 1


@pytest.mark.parametrize('writer', ['interests', 'experience', 'same', 'aba'])
def test_legacy_writers_invalidate_open_draft_and_replay(onboard, writer):
    c = onboard.test_client(); csrf = login(c)
    other = onboard.test_client(); other_csrf = login(other)
    s = put(c, csrf, c.get('/api/onboarding').json, 'skip').json
    other.put('/api/skills/interests', json={'node_ids':['agents']}, headers={'X-CSRF-Token':other_csrf})
    s = put(c, csrf, c.get('/api/onboarding').json, 'edit').json
    s = put(c, csrf, s, 'save', draft={'interests':['coding'], 'experience':'beginner'}).json
    if writer == 'experience':
        r = other.post('/preferences', data={'csrf':other_csrf,'goal':'work','experience':'experienced','weekly_goal':'3'})
        assert r.status_code == 302
    else:
        for nodes in ([['automation'], ['agents']] if writer == 'aba' else [['agents']] if writer == 'same' else [['automation']]):
            assert other.put('/api/skills/interests', json={'node_ids':nodes}, headers={'X-CSRF-Token':other_csrf}).status_code == 200
    fresh = c.get('/api/onboarding').json
    assert fresh['revision'] > s['revision']
    assert fresh['committed_revision'] > s['committed_revision']
    assert fresh['draft'] == s['draft']
    assert fresh['committed_preferences']['interests'] == (['automation'] if writer == 'interests' else ['agents'])
    if writer == 'experience':
        assert fresh['committed_preferences']['experience'] == 'experienced'
    rejected = put(c, csrf, s, 'complete')
    assert rejected.status_code == 409
    assert rejected.json['state'] == fresh
    # Replay the acknowledged save from before the legacy write: no mutation,
    # no resurrection of the obsolete committed preferences or revision.
    replay = c.put('/api/onboarding', json={'action':'save','expected_revision':s['revision']-1,
        'idempotency_key':'request-'+str(s['revision']-1),
        'draft':{'interests':['coding'], 'experience':'beginner'}}, headers={'X-CSRF-Token':csrf})
    assert replay.status_code == 200 and replay.json == fresh
    cancelled = put(c, csrf, fresh, 'cancel').json
    assert cancelled['draft'] == fresh['committed_preferences']
    assert c.get('/api/skills/me').json['interests'] == fresh['committed_preferences']['interests']


def test_revision_upgrade_restart_and_transaction_rollback(onboard):
    c = onboard.test_client(); csrf = login(c)
    s = put(c, csrf, c.get('/api/onboarding').json, 'skip').json
    s = put(c, csrf, s, 'edit').json
    with sqlite3.connect(onboard.config['DATABASE']) as db:
        uid = db.execute("SELECT id FROM users WHERE email='learner@example.test'").fetchone()[0]
        db.execute('BEGIN')
        db.execute('INSERT INTO skill_interests VALUES(?,?)', (uid, 'coding'))
        db.rollback()
    assert c.get('/api/onboarding').json == s
    assert c.put('/api/skills/interests', json={'node_ids':['agents']}, headers={'X-CSRF-Token':csrf}).status_code == 200
    current = c.get('/api/onboarding').json
    with sqlite3.connect(onboard.config['DATABASE']) as db:
        tables = ['onboarding_state', 'onboarding_requests', 'onboarding_events_v1', 'committed_preference_revisions']
        before = {t: db.execute('SELECT * FROM '+t).fetchall() for t in tables}
    result = onboard.test_cli_runner().invoke(args=['init-onboarding'])
    assert result.exit_code == 0, result.output
    with sqlite3.connect(onboard.config['DATABASE']) as db:
        assert before == {t: db.execute('SELECT * FROM '+t).fetchall() for t in tables}
    restarted = create_app(dict(TESTING=True, DATABASE=onboard.config['DATABASE'], SECRET_KEY='test-only-key'))
    other = restarted.test_client(); other_csrf = login(other)
    assert other.get('/api/onboarding').json == current
    assert put(other, other_csrf, s, 'complete').status_code == 409
