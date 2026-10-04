"""Support v1: private responses, append-only audit, optimistic concurrency."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import click
from flask import abort, g, jsonify, request

SCHEMA = '''CREATE TABLE IF NOT EXISTS support_responses (
 ticket_id INTEGER NOT NULL REFERENCES help_requests(id),
 revision INTEGER NOT NULL, response TEXT NOT NULL,
 handler_id TEXT NOT NULL REFERENCES users(id),
 handled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(ticket_id,revision)
);'''


def register_support(app, db, query, require_user):
    @app.cli.command('init-support')
    def migrate():
        """Add response audit storage after a private SQLite backup; no media writes."""
        root = Path(app.config['DATABASE']).parent / ('before-support-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f'))
        root.mkdir(mode=0o700)
        backup_path = root / 'database.sqlite'
        with sqlite3.connect(backup_path) as backup:
            db().backup(backup)
        backup_path.chmod(0o600)
        db().executescript(SCHEMA)
        click.echo('Support v1 ready; private database backup: ' + str(root))

    def ready():
        if not query("SELECT 1 FROM sqlite_master WHERE name='support_responses' AND type='table'", one=True):
            abort(503, 'Support storage requires init-support.')

    def ticket(ticket_id):
        row = query('SELECT * FROM help_requests WHERE id=?', (ticket_id,), True)
        if not row or (g.user['role'] not in ('editor', 'admin') and row['user_id'] != g.user['id']):
            abort(404)
        reply = query('SELECT revision,response,handled_at FROM support_responses WHERE ticket_id=? ORDER BY revision DESC LIMIT 1', (ticket_id,), True)
        result = {k: row[k] for k in ('id', 'lesson_id', 'body', 'created_at', 'status')}
        result.update(dict(reply) if reply else dict(revision=0, response=None, handled_at=None))
        return result

    @app.get('/api/support/tickets')
    @require_user
    def support_tickets():
        ready()
        rows = query('SELECT id FROM help_requests ORDER BY id DESC') if g.user['role'] in ('editor', 'admin') else query('SELECT id FROM help_requests WHERE user_id=? ORDER BY id DESC', (g.user['id'],))
        return jsonify(version=1, tickets=[ticket(row['id']) for row in rows])

    @app.get('/api/support/tickets/<int:ticket_id>')
    @require_user
    def support_ticket(ticket_id):
        ready()
        return jsonify(version=1, ticket=ticket(ticket_id))

    @app.post('/api/support/tickets/<int:ticket_id>/handle')
    @require_user
    def support_handle(ticket_id):
        if g.user['role'] not in ('editor', 'admin'):
            abort(403)
        ready()
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or set(payload) != {'revision', 'response'}:
            abort(400)
        revision, response = payload['revision'], payload['response']
        if type(revision) is not int or revision < 0 or not isinstance(response, str) or not 1 <= len(response.strip()) <= 4000:
            abort(400)
        response = response.strip()
        with db():
            db().execute('BEGIN IMMEDIATE')
            current = ticket(ticket_id)
            if revision > current['revision']:
                abort(409, 'Вопрос изменился. Сохраните свой текст и загрузите текущий ответ.')
            if current['response'] == response:
                return jsonify(version=1, ticket=current)
            if revision != current['revision']:
                abort(409, 'На вопрос уже ответили. Ваш текст сохранён в форме; загрузите текущий ответ перед изменением.')
            db().execute('INSERT INTO support_responses(ticket_id,revision,response,handler_id) VALUES(?,?,?,?)',
                         (ticket_id, revision + 1, response, g.user['id']))
            db().execute("UPDATE help_requests SET status='handled' WHERE id=?", (ticket_id,))
            result = ticket(ticket_id)
        return jsonify(version=1, ticket=result)
