"""Process restart tests use no provider credentials; ready-path mocks are labelled."""
import os
from pathlib import Path
import selectors
import signal
import sqlite3
import subprocess
import sys
import threading

import pytest

from club.teaching_worker import run_worker
from test_learning import app, login, post
from test_teaching import teaching, upload
from test_teaching_pipeline import pipeline, MockProvider


def environment(app):
    env = dict(os.environ, CLUB_DATABASE=app.config['DATABASE'],
               CLUB_UPLOAD_DIR=app.config['TEACHING_UPLOAD_DIR'],
               CLUB_SECRET_KEY='process-test-only', PYTHONUNBUFFERED='1')
    for key in ('CLUB_AI_APPROVED', 'CLUB_AI_API_KEY', 'CLUB_AI_MODEL'):
        env.pop(key, None)
    return env


def spawn(app, *args):
    return subprocess.Popen([sys.executable, '-m', 'flask', '--app', 'club',
                             'process-teaching-worker', *args], env=environment(app),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def wait_line(process):
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        assert selector.select(10), 'Worker failed to announce startup'
        return process.stdout.readline()


def test_real_process_reopens_queue_and_does_not_retry_blocked(teaching):
    c = teaching.test_client(); csrf = login(c, 'editor')
    job = upload(c, csrf).json; path = '/api/teaching/jobs/' + job['id']
    result = teaching.test_cli_runner().invoke(args=['process-teaching-once'])
    assert result.exit_code == 0
    blocked = c.get(path).json
    assert blocked['state'] == 'blocked' and blocked['attempt'] == 0
    process = spawn(teaching, '--poll-seconds', '60')
    try:
        assert 'worker started' in wait_line(process)
        process.send_signal(signal.SIGTERM)
        out, err = process.communicate(timeout=5)
        assert process.returncode == 0, err
        assert 'jobs processed: 0' in out
    finally:
        if process.poll() is None:
            process.kill(); process.communicate()
    assert c.get(path).json == blocked
    assert post(c, path + '/retry', {'revision': blocked['revision']}, csrf).status_code == 409
    assert c.get(path).json == blocked


def test_killed_claim_recovers_only_with_charge_acknowledgement(teaching, monkeypatch):
    monkeypatch.setattr('club.teaching_provider.configured', lambda: True)
    c = teaching.test_client(); csrf = login(c, 'editor')
    job = upload(c, csrf).json; path = '/api/teaching/jobs/' + job['id']
    # Simulate abrupt death at the persisted claim boundary in a real process.
    code = """import os, sqlite3, time
from club.teaching import claim_job
import club.teaching_provider
club.teaching_provider.configured = lambda: True
connection = sqlite3.connect(os.environ['CLUB_DATABASE'])
assert claim_job(connection)
print('claimed', flush=True)
time.sleep(60)
"""
    process = subprocess.Popen([sys.executable, '-c', code], env=environment(teaching),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert 'claimed' in wait_line(process)
    finally:
        process.kill(); process.communicate(timeout=5)
    assert c.get(path).json['state'] == 'running'
    # Advance persisted lease expiry instead of waiting fifteen minutes.
    with sqlite3.connect(teaching.config['DATABASE']) as db:
        db.execute('UPDATE teaching_jobs SET lease_until=0 WHERE id=?', (job['id'],))
    recovery = teaching.test_cli_runner().invoke(args=['process-teaching-once'])
    assert recovery.exit_code == 0, recovery.exception
    failed = c.get(path).json
    assert failed['state'] == 'failed' and failed['error_code'] == 'interrupted_outcome_unknown'
    assert post(c, path + '/retry', {'revision': failed['revision']}, csrf).status_code == 409
    assert post(c, path + '/retry', {'revision': failed['revision'],
                                    'acknowledge_possible_charge': True}, csrf).status_code == 200


def test_worker_ready_once_and_stop_after_inflight_mock(pipeline):
    c = pipeline.test_client(); csrf = login(c, 'editor')
    first = upload(c, csrf).json
    second = upload(c, csrf, key='request-second').json
    stopped = threading.Event()

    class StoppingProvider(MockProvider):
        def generate(self, sources, graph):
            stopped.set()
            return super().generate(sources, graph)

    pipeline.config['TEACHING_PROVIDER_FACTORY'] = StoppingProvider
    connections = []
    def database():
        # Match the app's context-managed connection lifecycle.
        from flask import g
        g.db = sqlite3.connect(pipeline.config['DATABASE'])
        connections.append(g.db)
        return g.db

    logs = []
    assert run_worker(pipeline, database, poll_seconds=1, max_jobs=0,
                      stop=stopped, emit=logs.append) == 1
    assert logs == ['Job processing: ready']
    with pytest.raises(sqlite3.ProgrammingError):
        connections[0].execute('SELECT 1')
    with sqlite3.connect(pipeline.config['DATABASE']) as db:
        assert db.execute("SELECT COUNT(*) FROM teaching_jobs WHERE state='queued'").fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM teaching_drafts').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM teaching_publications').fetchone()[0] == 0
    pipeline.config['TEACHING_PROVIDER_FACTORY'] = MockProvider
    result = pipeline.test_cli_runner().invoke(args=['process-teaching-worker', '--max-jobs', '1'])
    assert result.exit_code == 0, result.exception
    assert 'jobs processed: 1' in result.output
    for job in (first, second):
        assert c.get('/api/teaching/jobs/' + job['id']).json['state'] == 'ready'
    with sqlite3.connect(pipeline.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM teaching_drafts').fetchone()[0] == 2


def test_missing_media_blocks_one_job_without_stopping_queue(pipeline):
    class ReadingProvider(MockProvider):
        def transcribe(self, path, filename):
            path.read_bytes()
            return super().transcribe(path, filename)

    pipeline.config['TEACHING_PROVIDER_FACTORY'] = ReadingProvider
    c = pipeline.test_client(); csrf = login(c, 'editor')
    media = upload(c, csrf, b'\0\0\0\x18ftypmp42' + b'\0'*32, 'lesson.mp4').json
    Path(pipeline.config['TEACHING_UPLOAD_DIR'], media['upload_id']).unlink()
    text = upload(c, csrf, key='request-text').json
    result = pipeline.test_cli_runner().invoke(args=['process-teaching-worker', '--max-jobs', '2'])
    assert result.exit_code == 0, result.exception
    assert 'source_storage_unavailable' in result.output
    assert c.get('/api/teaching/jobs/' + media['id']).json['state'] == 'blocked'
    assert c.get('/api/teaching/jobs/' + text['id']).json['state'] == 'ready'


def test_cancellation_during_transcription_retains_no_stale_output(pipeline):
    class CancellingTranscriber(MockProvider):
        def transcribe(self, path, filename):
            with sqlite3.connect(pipeline.config['DATABASE']) as db:
                db.execute("UPDATE teaching_jobs SET state='cancelled', lease_token=NULL WHERE state='running'")
            return super().transcribe(path, filename)

    pipeline.config['TEACHING_PROVIDER_FACTORY'] = CancellingTranscriber
    c = pipeline.test_client(); csrf = login(c, 'editor')
    job = upload(c, csrf, b'RIFF' + b'\0'*4 + b'WAVE' + b'\0'*20, 'voice.wav').json
    result = pipeline.test_cli_runner().invoke(args=['process-teaching-worker', '--max-jobs', '1'])
    assert result.exit_code == 0, result.exception
    assert 'lease_lost' in result.output
    assert c.get('/api/teaching/jobs/' + job['id']).json['state'] == 'cancelled'
    with sqlite3.connect(pipeline.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM teaching_transcripts').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM teaching_drafts').fetchone()[0] == 0
    assert MockProvider.calls == ['transcribe']
