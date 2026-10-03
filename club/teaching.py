"""Private source ingestion and durable processing leases. No generated AI fallback.

Source bytes never enter a public/static directory; download is owner/admin only.
Provider processing uses fenced leases and retains source hashes and reviewed editions.
"""
import hashlib
import json
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

import click
from flask import abort, g, jsonify, request, send_file
from werkzeug.utils import secure_filename

FORMATS = {'.txt': 'text/plain', '.md': 'text/plain', '.wav': 'audio/wav',
           '.mp4': 'video/mp4', '.webm': 'video/webm'}
LIMIT = 25 * 1024 * 1024
TEXT_LIMIT = 200 * 1024
MAX_ATTEMPTS = 3


def source_metadata(path, suffix, digest):
    """Bounded source parsing; media signatures do not promise successful decoding."""
    with path.open('rb') as stream:
        head = stream.read(32)
    if suffix in ('.txt', '.md'):
        if path.stat().st_size > TEXT_LIMIT:
            abort(413, 'Текст: не более 200 КиБ.')
        try:
            text = path.read_text(encoding='utf-8-sig')
        except UnicodeError:
            abort(400, 'Текст должен быть в UTF-8.')
        if not text.strip() or any(ord(c) < 32 and c not in '\n\r\t' for c in text):
            abort(400, 'Пустой текст или бинарные данные.')
        # HTML is not rendered: all contents, including embedded instructions, are data.
        paragraphs = [{'paragraph': i + 1, 'text': p} for i, p in enumerate(text.split('\n\n')) if p.strip()]
        return {'kind': 'document', 'sha256': digest, 'paragraphs': paragraphs}
    valid = ((suffix == '.mp4' and head[4:8] == b'ftyp') or
             (suffix == '.webm' and head[:4] == b'\x1aE\xdf\xa3') or
             (suffix == '.wav' and head[:4] == b'RIFF' and head[8:12] == b'WAVE'))
    if not valid:
        abort(400, 'Содержимое не соответствует формату файла.')
    return {'kind': 'media', 'sha256': digest, 'validation': 'signature_only', 'transcript': None}


def record_event(db, job_id):
    db.execute('''INSERT INTO teaching_job_events(job_id,state,attempt,error_code)
        SELECT id,state,attempt,error_code FROM teaching_jobs WHERE id=?''', (job_id,))


def claim_job(db, *, now=None):
    """Atomic claim; expired work needs explicit retry because a charge may exist."""
    now = int(time.time()) if now is None else now
    with db:
        db.execute('BEGIN IMMEDIATE')
        expired = db.execute("SELECT id FROM teaching_jobs WHERE state='running' AND lease_until<=?", (now,)).fetchall()
        for row in expired:
            db.execute("""UPDATE teaching_jobs SET state='failed',error_code='interrupted_outcome_unknown',
                lease_token=NULL,lease_until=NULL,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?""", (row[0],))
            record_event(db, row[0])
        row = db.execute("SELECT id FROM teaching_jobs WHERE state='queued' AND attempt<? ORDER BY created_at,id LIMIT 1", (MAX_ATTEMPTS,)).fetchone()
        if not row:
            return None
        token = uuid.uuid4().hex
        db.execute("""UPDATE teaching_jobs SET state='running',attempt=attempt+1,revision=revision+1,
            lease_token=?,lease_until=?,error_code=NULL,updated_at=CURRENT_TIMESTAMP WHERE id=?""", (token, now + 900, row[0]))
        record_event(db, row[0])
        return {'id': row[0], 'lease_token': token}


def finish_job(db, claim, *, state, error_code=None):
    if state not in ('blocked', 'failed', 'ready'):
        raise ValueError('Invalid terminal state')
    with db:
        result = db.execute("""UPDATE teaching_jobs SET state=?,error_code=?,lease_token=NULL,lease_until=NULL,
            revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND state='running' AND lease_token=?
            AND lease_until>?""", (state, error_code, claim['id'], claim['lease_token'], int(time.time())))
        if result.rowcount:
            record_event(db, claim['id'])
        return bool(result.rowcount)


def register_teaching(app, db, query):
    app.config.setdefault('TEACHING_UPLOAD_DIR', os.environ.get('CLUB_UPLOAD_DIR', str(Path(app.config['DATABASE']).parent / 'teaching-uploads')))
    app.config.setdefault('TEACHING_UPLOAD_LIMIT', LIMIT)
    app.config.setdefault('TEACHING_OWNER_QUOTA', 250 * 1024 * 1024)

    def storage():
        root = Path(app.config['TEACHING_UPLOAD_DIR']).resolve()
        public = Path(app.static_folder).resolve()
        if root == public or public in root.parents:
            raise RuntimeError('Upload storage must be outside static assets')
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        return root

    def editor(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not g.user:
                abort(401)
            if g.user['role'] not in ('editor', 'admin'):
                abort(403)
            return fn(*args, **kwargs)
        return wrapped

    def owned_job(id):
        row = query('''SELECT j.*,u.owner_id,u.filename,u.media_type,u.size,u.sha256 FROM teaching_jobs j
            JOIN teaching_uploads u ON j.upload_id=u.id WHERE j.id=?''', (id,), True)
        if not row or (row['owner_id'] != g.user['id'] and g.user['role'] != 'admin'):
            abort(404)
        return row

    def dto(row):
        value = {key: row[key] for key in ('id','upload_id','filename','media_type','size','sha256','state',
                                         'attempt','revision','error_code','created_at','updated_at')}
        value['source_ids'] = [s['upload_id'] for s in query(
            'SELECT upload_id FROM teaching_package_sources WHERE job_id=? ORDER BY position', (row['id'],))] or [row['upload_id']]
        draft = query('SELECT MAX(revision) revision FROM teaching_drafts WHERE job_id=?', (row['id'],), True)
        value['draft_revision'] = draft['revision']
        return value

    @app.cli.command('init-teaching')
    def init_teaching():
        database = Path(app.config['DATABASE'])
        backup = database.with_name(database.name + '.before-teaching-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f') + '.sqlite')
        with sqlite3.connect(backup) as dest:
            db().backup(dest)
        backup.chmod(0o600)
        db().executescript(Path(__file__).with_name('teaching_schema.sql').read_text())
        storage()
        click.echo('Private uploads and jobs ready; backup: ' + str(backup))

    from .teaching_provider import configured

    @app.get('/api/teaching/capabilities')
    @editor
    def capabilities():
        return jsonify(extensions=list(FORMATS), max_file_bytes=app.config['TEACHING_UPLOAD_LIMIT'],
                       max_text_bytes=TEXT_LIMIT, max_attempts=MAX_ATTEMPTS, url_import=False,
                       processing_available=configured(), processing_dependency=None if configured() else 'CLUB_AI_APPROVED,CLUB_AI_API_KEY,CLUB_AI_MODEL',
                       source_packages=True, max_package_files=5, draft_schema_version=1)

    @app.post('/api/teaching/uploads')
    @editor
    def upload():
        key = request.headers.get('Idempotency-Key', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,100}', key):
            abort(400, 'Укажите Idempotency-Key (8–100 букв, цифр, _ или -).')
        files = request.files.getlist('file')
        if len(files) != 1 or len(request.files) != 1:
            abort(400, 'Загрузите один файл.')
        item = files[0]
        suffix = Path(item.filename or '').suffix.lower()
        if suffix not in FORMATS:
            abort(400, 'Поддерживаются TXT, MD, WAV, MP4, WebM. Ссылки и архивы пока не поддерживаются.')
        name = secure_filename(item.filename or '')[:180] or ('source' + suffix)
        identity = uuid.uuid4().hex
        target = storage() / identity
        keep = False
        try:
            digest, size = hashlib.sha256(), 0
            with target.open('xb') as out:
                target.chmod(0o600)
                while chunk := item.stream.read(64 * 1024):
                    size += len(chunk)
                    if size > app.config['TEACHING_UPLOAD_LIMIT']:
                        abort(413)
                    digest.update(chunk)
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            if not size:
                abort(400, 'Файл пуст.')
            checksum = digest.hexdigest()
            source = source_metadata(target, suffix, checksum)
            with db():
                db().execute('BEGIN IMMEDIATE')
                old = query('SELECT * FROM teaching_uploads WHERE owner_id=? AND request_id=?', (g.user['id'], key), True)
                if old:
                    if old['sha256'] != checksum or old['media_type'] != FORMATS[suffix]:
                        abort(409, 'Этот ключ уже использован для другого файла.')
                    job = query('SELECT id FROM teaching_jobs WHERE upload_id=?', (old['id'],), True)
                    return jsonify(dto(owned_job(job['id'])))
                used = query('SELECT COALESCE(SUM(size),0) n FROM teaching_uploads WHERE owner_id=?', (g.user['id'],), True)['n']
                if used + size > app.config['TEACHING_OWNER_QUOTA']:
                    abort(413, 'Лимит хранилища автора исчерпан.')
                db().execute('INSERT INTO teaching_uploads(id,owner_id,request_id,filename,media_type,size,sha256) VALUES(?,?,?,?,?,?,?)',
                             (identity,g.user['id'],key,name,FORMATS[suffix],size,checksum))
                deferred = request.form.get('defer_processing') == '1'
                db().execute("INSERT INTO teaching_jobs(id,upload_id,state,error_code) VALUES(?,?,?,?)",
                             (identity,identity,'cancelled' if deferred else 'queued','awaiting_package' if deferred else None))
                db().execute('INSERT INTO teaching_sources(upload_id,body) VALUES(?,?)', (identity,json.dumps(source,ensure_ascii=False)))
                record_event(db(), identity)
            keep = True
            return jsonify(dto(owned_job(identity))), 201
        finally:
            if not keep:
                target.unlink(missing_ok=True)

    @app.get('/api/teaching/jobs')
    @editor
    def jobs():
        rows = query('''SELECT j.*,u.owner_id,u.filename,u.media_type,u.size,u.sha256 FROM teaching_jobs j
            JOIN teaching_uploads u ON u.id=j.upload_id WHERE u.owner_id=? ORDER BY j.created_at DESC,j.id LIMIT 100''', (g.user['id'],))
        return jsonify(jobs=[dto(row) for row in rows])

    @app.get('/api/teaching/jobs/<id>')
    @editor
    def job(id):
        return jsonify(dto(owned_job(id)))

    @app.get('/api/teaching/jobs/<id>/source')
    @editor
    def source(id):
        row = owned_job(id)
        return jsonify(json.loads(query('SELECT body FROM teaching_sources WHERE upload_id=?', (row['upload_id'],), True)['body']))

    @app.get('/api/teaching/jobs/<id>/file')
    @editor
    def download(id):
        row = owned_job(id)
        return send_file(storage() / row['upload_id'], as_attachment=True, download_name=row['filename'],
                         mimetype='application/octet-stream', conditional=True)

    @app.post('/api/teaching/jobs/<id>/<action>')
    @editor
    def transition(id, action):
        if action not in ('retry', 'cancel'):
            abort(404)
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or type(body.get('revision')) is not int:
            abort(400, 'Укажите текущую revision задания.')
        with db():
            db().execute('BEGIN IMMEDIATE')
            row = owned_job(id)
            if row['revision'] != body['revision']:
                abort(409, 'Задание изменилось. Обновите его состояние.')
            if row['error_code'] == 'included_in_package':
                abort(409, 'Источник обрабатывается в составе пакета.')
            if action == 'retry':
                if row['state'] not in ('blocked','failed','cancelled') or row['attempt'] >= MAX_ATTEMPTS:
                    abort(409, 'Повтор сейчас недоступен.')
                if row['error_code'] in ('interrupted_outcome_unknown', 'cancelled_outcome_unknown', 'provider_outcome_unknown') and body.get('acknowledge_possible_charge') is not True:
                    abort(409, 'Исход предыдущей обработки неизвестен; подтвердите возможный повторный расход.')
            elif row['state'] == 'ready':
                abort(409, 'Обработка уже завершена.')
            state = 'queued' if action == 'retry' else 'cancelled'
            error = None if action == 'retry' else row['error_code']
            if action == 'cancel' and row['state'] == 'running':
                error = 'cancelled_outcome_unknown'
            db().execute('''UPDATE teaching_jobs SET state=?,error_code=?,lease_token=NULL,lease_until=NULL,
                revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?''', (state,error,id))
            record_event(db(), id)
        return jsonify(dto(owned_job(id)))

    @app.cli.command('process-teaching-once')
    def process_once():
        claim = claim_job(db())
        if not claim:
            click.echo('No queued work.')
            return
        from .teaching_drafts import process_claim
        click.echo('Job processing: ' + process_claim(app, db(), claim))

    from .teaching_drafts import register_drafts
    register_drafts(app, db, query, editor, owned_job, dto)
    from .teaching_worker import register_worker
    register_worker(app, db)
