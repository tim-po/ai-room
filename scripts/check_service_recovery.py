"""Disposable process/lease/paired-state drill. Runs ~15 minutes, no AI calls.

A test-only hook pauses processing AFTER the real worker persists its claim.
SIGKILL then exercises the real 900-second lease without editing lease timestamps.
Only child processes and temporary DB/media/code exports are modified.
"""
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import re
import secrets
import signal
import shutil
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

SOURCE = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('CLUB_EVIDENCE_DIR', 'instance/service-recovery-evidence')).resolve()
OUT.mkdir(parents=True, exist_ok=True)
COMMIT = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip()
ROLLBACK = '1bd6b76cb3e265302f6fb922c5f6c64abd232a7c'
events = []
children = []

def record(action, **details):
    event = dict(action=action, utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **details)
    events.append(event)
    (OUT/'events.json').write_text(json.dumps(events, indent=2))
    print(json.dumps(event), flush=True)

with tempfile.TemporaryDirectory(prefix='club-service-recovery-') as folder:
    root = Path(folder)
    root.chmod(0o700)
    database = root/'club.sqlite'
    uploads = root/'uploads'
    uploads.mkdir(mode=0o700)
    password = secrets.token_urlsafe(24)
    env = dict(os.environ, CLUB_DATABASE=str(database), CLUB_UPLOAD_DIR=str(uploads),
               CLUB_SECRET_KEY=secrets.token_hex(32), CLUB_SEED_PASSWORD=password,
               CLUB_SECURE_COOKIE='0', CLUB_BUILD_ID=COMMIT, PYTHONUNBUFFERED='1')
    for key in ('CLUB_AI_APPROVED', 'CLUB_AI_API_KEY', 'CLUB_AI_MODEL', 'PYTHONPATH'):
        env.pop(key, None)
    def cli(*args, cwd=SOURCE):
        result = subprocess.run([sys.executable, '-m', 'flask', '--app', 'club', *args],
                                cwd=cwd, env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        return result.stdout
    def spawn(args, cwd=SOURCE):
        log = root/f'process-{len(children)}.log'
        with log.open('w') as output:
            proc = subprocess.Popen([sys.executable, *args], cwd=cwd, env=env,
                                    stdout=output, stderr=output, start_new_session=True)
        proc.drill_log = log
        children.append(proc)
        return proc
    def stop(proc):
        proc.terminate()
        assert proc.wait(timeout=15) == 0
    def dbrow(sql, params=()):
        with sqlite3.connect(database) as db:
            return db.execute(sql, params).fetchone()
    for command in ('init-db', 'seed', 'init-skills', 'init-teaching'):
        cli(command)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    origin = f'http://127.0.0.1:{port}'
    learner = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    teacher = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def request(client, path, data=None, csrf=None, headers=None):
        headers = dict(headers or {})
        if isinstance(data, dict):
            if csrf:
                data = json.dumps(data).encode()
                headers['Content-Type'] = 'application/json'
            else:
                data = urllib.parse.urlencode(data).encode()
        if csrf:
            headers['X-CSRF-Token'] = csrf
        with client.open(urllib.request.Request(origin+path, data=data, headers=headers), timeout=10) as response:
            return response.read()
    def start_web(cwd=SOURCE, build=COMMIT):
        env['CLUB_BUILD_ID'] = build
        proc = spawn(['-m', 'gunicorn', '--bind', f'127.0.0.1:{port}', 'club:create_app()'], cwd)
        for _ in range(100):
            try:
                health = json.loads(request(learner, '/health'))
                assert health['build'] == build, health
                record('web_started', pid=proc.pid, build=build, origin=origin)
                return proc
            except (OSError, urllib.error.URLError):
                assert proc.poll() is None
                time.sleep(.1)
        raise AssertionError('web startup timeout')
    def login(client, role):
        page = request(client, '/login').decode()
        csrf = re.search(r'name="csrf-token" content="([^"]+)"', page)[1]
        page = request(client, '/login', dict(csrf=csrf, email=f'{role}@example.test', password=password)).decode()
        return re.search(r'name="csrf-token" content="([^"]+)"', page)[1]
    def worker(cwd=SOURCE):
        proc = spawn(['-m', 'flask', '--app', 'club', 'process-teaching-worker', '--poll-seconds', '1'], cwd)
        for _ in range(150):
            if 'Teaching worker started' in proc.drill_log.read_text():
                return proc
            assert proc.poll() is None, proc.drill_log.read_text()
            time.sleep(.1)
        raise AssertionError('queue startup timeout')
    def wait_state(job, state, timeout=15):
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            row = dbrow('SELECT state,error_code,attempt,lease_until FROM teaching_jobs WHERE id=?', (job,))
            if row[0] == state:
                return row
            time.sleep(.1)
        raise AssertionError(f'Expected {state}, got {row}')
    try:
        web = start_web()
        lc = login(learner, 'member')
        tc = login(teacher, 'editor')
        lesson = '/api/lessons/foundations-start-01'
        request(learner, lesson+'/practice', dict(body='Before snapshot', status='draft'), lc)
        request(learner, lesson+'/completion', dict(completed=True), lc)
        boundary = '----club-drill-'+secrets.token_hex(12)
        source_bytes = b'Original synthetic teaching source. Verify outputs before sharing.'
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="source.txt"\r\nContent-Type: text/plain\r\n\r\n'.encode()+source_bytes+f'\r\n--{boundary}--\r\n'.encode())
        job = json.loads(request(teacher, '/api/teaching/uploads', body, tc,
                                {'Content-Type':f'multipart/form-data; boundary={boundary}', 'Idempotency-Key':'service-recovery-drill'}))
        path = '/api/teaching/jobs/'+job['id']
        assert request(teacher, path+'/file') == source_bytes
        # Actual registered queue worker, with a deterministic pause at the provider boundary.
        hook = """import time
from flask.cli import cli
import club.teaching_worker as worker
worker.process_claim = lambda *args: time.sleep(1800)
cli.main(args=['--app', 'club', 'process-teaching-worker', '--poll-seconds', '1'])
"""
        interrupted = spawn(['-c', hook])
        running = wait_state(job['id'], 'running')
        interrupted.kill()
        assert interrupted.wait(timeout=5) < 0
        lease_until = running[3]
        record('worker_killed_after_persisted_claim', pid=interrupted.pid, lease_until=lease_until,
               hook='pause before provider, no provider call; real claim/worker/SIGKILL', natural_expiry=True)
        queue = worker()
        stop(web)
        stop(queue)
        record('both_writers_stopped', web_pid=web.pid, worker_pid=queue.pid)
        snapshot = root/'paired-snapshot'
        snapshot.mkdir(mode=0o700)
        with sqlite3.connect(database) as src, sqlite3.connect(snapshot/'club.sqlite') as dst:
            src.backup(dst)
        (snapshot/'club.sqlite').chmod(0o600)
        shutil.copytree(uploads, snapshot/'uploads')
        file_hash = hashlib.sha256((uploads/job['upload_id']).read_bytes()).hexdigest()
        assert hashlib.sha256((snapshot/'uploads'/job['upload_id']).read_bytes()).hexdigest() == file_hash
        record('paired_snapshot', protected_media_sha256=file_hash, running_claim_preserved=True)
        for command in ('init-db', 'init-skills', 'init-teaching'):
            cli(command)
        assert dbrow('PRAGMA integrity_check')[0] == 'ok'
        record('additive_migrations_passed')
        web = start_web()
        queue = worker()
        assert request(teacher, path+'/file') == source_bytes
        assert 'Before snapshot' in request(learner, '/profile').decode()
        # A later learner write MUST survive compatible code rollback.
        request(learner, lesson+'/practice', dict(body='After snapshot retained across code rollback', status='draft'), lc)
        request(learner, lesson+'/completion', dict(completed=False), lc)
        stop(queue)
        stop(web)
        rollback_source = root/'rollback-source'
        rollback_source.mkdir()
        archive = root/'rollback.tar'
        with archive.open('wb') as output:
            subprocess.run(['git', 'archive', ROLLBACK], cwd=SOURCE, stdout=output, check=True)
        with tarfile.open(archive) as bundle:
            bundle.extractall(rollback_source, filter='data')
        web = start_web(rollback_source, ROLLBACK)
        queue = worker(rollback_source)
        assert 'After snapshot retained across code rollback' in request(learner, '/profile').decode()
        assert dbrow('SELECT completed FROM progress WHERE lesson_id=?', ('foundations-start-01',))[0] == 0
        assert request(teacher, path+'/file') == source_bytes
        record('compatible_code_rollback_passed', rollback_commit=ROLLBACK, later_learner_writes_preserved=True)
        stop(queue)
        stop(web)
        # Restore BOTH halves while quiescent. This explicitly discards disposable post-snapshot writes.
        with sqlite3.connect(snapshot/'club.sqlite') as src, sqlite3.connect(database) as dst:
            src.backup(dst)
        shutil.rmtree(uploads)
        shutil.copytree(snapshot/'uploads', uploads)
        web = start_web()
        queue = worker()
        assert request(teacher, path+'/file') == source_bytes
        assert 'Before snapshot' in request(learner, '/profile').decode()
        assert 'After snapshot retained' not in request(learner, '/profile').decode()
        assert dbrow('SELECT completed FROM progress WHERE lesson_id=?', ('foundations-start-01',))[0] == 1
        record('paired_restore_passed', disposable_later_writes_intentionally_discarded=True,
               production_policy='prefer compatible code rollback; data restore requires write reconciliation')
        while time.time() <= lease_until+3:
            assert queue.poll() is None and web.poll() is None
            remaining = max(0, int(lease_until-time.time()))
            record('waiting_for_unmodified_lease', remaining_seconds=remaining)
            time.sleep(min(30, max(1, remaining)))
        failed = wait_state(job['id'], 'failed')
        assert failed[1] == 'interrupted_outcome_unknown' and failed[2] == 1
        current = json.loads(request(teacher, path))
        try:
            request(teacher, path+'/retry', {'revision':current['revision']}, tc)
            raise AssertionError('Unacknowledged retry allowed')
        except urllib.error.HTTPError as error:
            assert error.code == 409
        request(teacher, path+'/retry', dict(revision=current['revision'], acknowledge_possible_charge=True), tc)
        blocked = wait_state(job['id'], 'blocked')
        assert blocked[1] == 'provider_approved_configuration_required' and blocked[2] == 2
        record('natural_lease_recovery_passed', lease_seconds=900, unacknowledged_retry_status=409,
               acknowledged_retry='blocked honestly without provider configuration', duplicate_drafts=dbrow('SELECT COUNT(*) FROM teaching_drafts')[0])
        assert dbrow('SELECT COUNT(*) FROM teaching_drafts')[0] == 0
        stop(queue)
        stop(web)
        record('clean_shutdown')
        (OUT/'result.json').write_text(json.dumps(dict(commit=COMMIT, source=str(SOURCE), rollback_commit=ROLLBACK,
            origin=origin, passed=True, events=events, provider_acceptance=False, shared_staging_modified=False,
            limitation='Child-process supervision only; no shared systemd units installed. Fault hook pauses before provider; no live in-flight charge.'), indent=2))
    finally:
        for proc in children:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=5)
