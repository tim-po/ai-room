"""Actual isolated process restart and backup/restore; no installed data touched."""
import http.cookiejar
import json
import os
from pathlib import Path
import re
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

out = Path(os.environ.get('CLUB_EVIDENCE_DIR', 'instance/operations-evidence'))
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='club-operations-') as folder:
    root = Path(folder)
    database = root/'club.sqlite'
    password = secrets.token_urlsafe(24)
    env = dict(os.environ, CLUB_DATABASE=str(database), CLUB_SECRET_KEY=secrets.token_hex(32),
               CLUB_SEED_PASSWORD=password, CLUB_SECURE_COOKIE='0')
    for command in ['init-db', 'seed']:
        subprocess.run([sys.executable,'-m','flask','--app','club',command], env=env,check=True,capture_output=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def request(path, data=None, token=None):
        headers={}
        if data is not None:
            if token:
                data=json.dumps(data).encode();headers={'Content-Type':'application/json','X-CSRF-Token':token}
            else:
                data=urllib.parse.urlencode(data).encode()
        with opener.open(urllib.request.Request(base+path,data=data,headers=headers),timeout=5) as response:
            return response.read().decode()
    def start():
        process=subprocess.Popen([sys.executable,'-m','gunicorn','--bind',f'127.0.0.1:{port}','club:create_app()'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                request('/health');return process
            except (OSError, urllib.error.URLError):
                time.sleep(.05)
        process.terminate();raise RuntimeError('Server failed to start')
    def stop(process):
        process.terminate();process.wait(timeout=15)
    process=start()
    try:
        csrf=re.search(r'name="csrf-token" content="([^"]+)"',request('/login')).group(1)
        page=request('/login',dict(csrf=csrf,email='member@example.test',password=password))
        csrf=re.search(r'name="csrf-token" content="([^"]+)"',page).group(1)
        lesson='foundations-start-01'
        request('/api/lessons/'+lesson+'/practice',dict(body='Isolated durable practical result',status='draft'),csrf)
        request('/api/lessons/'+lesson+'/completion',dict(completed=True),csrf)
        def completed():
            with sqlite3.connect(database) as connection:
                return connection.execute('SELECT completed FROM progress WHERE lesson_id=?', (lesson,)).fetchone()[0]
        assert completed() == 1
        before=json.loads(request('/api/lessons/'+lesson))
        stop(process);process=start()
        after=json.loads(request('/api/lessons/'+lesson))
        assert before==after
        assert completed() == 1
        assert 'Isolated durable practical result' in request('/profile')
        backup=root/'backup.sqlite'
        with sqlite3.connect(database) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        request('/api/lessons/'+lesson+'/completion',dict(completed=False),csrf)
        assert completed() == 0
        request('/api/lessons/'+lesson+'/practice',dict(body='Post-backup change',status='draft'),csrf)
        stop(process)
        with sqlite3.connect(backup) as source, sqlite3.connect(database) as target:
            source.backup(target)
        process=start()
        assert json.loads(request('/api/lessons/'+lesson))==before
        assert completed() == 1
        assert 'Isolated durable practical result' in request('/profile')
        assert 'Post-backup change' not in request('/profile')
        result=dict(process_restart=True,session_survives=True,draft_survives=True,completion_survives=True,
                    sqlite_backup_restore=True,restored_prior_state=True,installed_database_untouched=True)
        (out/'operations.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result))
    finally:
        if process.poll() is None:stop(process)
