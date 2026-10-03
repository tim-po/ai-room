"""Retained editorial transfer sources. Installation is not publication."""
import copy
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import click
from flask import abort, g, jsonify

from .transfer_candidates import candidates, digest


def install_sources(db, reviewer):
    user = db.execute('SELECT role FROM users WHERE id=?', (reviewer,)).fetchone()
    if not user or user[0] not in ('admin', 'editor'):
        raise ValueError('Existing editor identity required')
    pending = []
    for candidate in candidates():
        source = candidate['source_snapshot']
        body = json.dumps(source, ensure_ascii=False, sort_keys=True)
        row = db.execute('SELECT body FROM skill_transfer_sources WHERE source_id=? AND edition=?',
                         (source['id'], source['edition'])).fetchone()
        if row and row[0] != body:
            raise ValueError('Retained source edition differs; explicit new edition and review required')
        if not row:
            pending.append((source['id'], source['edition'], body, reviewer))
    db.executemany('INSERT INTO skill_transfer_sources(source_id,edition,body,installed_by) VALUES(?,?,?,?)', pending)
    return len(pending)


def bound_candidates(db):
    result = copy.deepcopy(candidates())
    for candidate in result:
        source = candidate['source_snapshot']
        row = db.execute('SELECT body FROM skill_transfer_sources WHERE source_id=? AND edition=?',
                         (source['id'], source['edition'])).fetchone()
        if not row or json.loads(row[0]) != source:
            raise ValueError('Canonical retained transfer source missing or changed')
        for item in candidate['form']['items']:
            item['source']['snapshot_url'] = '/api/skills/editorial-sources/' + source['id'] + '/' + str(source['edition'])
        candidate['unbound_sha256'] = candidate['sha256']
        candidate['sha256'] = digest(candidate['form'])
        candidate['publication_blockers'] = [
            'Independent source/item/construct and equivalence decision on bound form hash',
            'Explicit reviewed learner publication and entitlement binding; source endpoint is editor-only',
        ]
    return result


def register_transfer_sources(app, db):
    @app.cli.command('install-transfer-sources')
    @click.option('--reviewer', required=True)
    def install(reviewer):
        """Back up and retain private sources; no forms, mappings or evidence created."""
        database = Path(app.config['DATABASE'])
        backup = database.with_name(database.name + '.before-transfer-sources-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f'))
        with sqlite3.connect(backup) as destination:
            db().backup(destination)
        backup.chmod(0o600)
        try:
            with db():
                db().execute('BEGIN IMMEDIATE')
                count = install_sources(db(), reviewer)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f'Retained {count} private sources; no publication. Backup: {backup}')

    @app.cli.command('inspect-transfer-sources')
    def inspect():
        """PRIVATE keyed export; never copy into public/static storage."""
        try:
            click.echo(json.dumps(bound_candidates(db()), ensure_ascii=False, indent=2))
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

    @app.get('/api/skills/editorial-sources/<source_id>/<int:edition>')
    def source_snapshot(source_id, edition):
        if not g.user or g.user['role'] not in ('admin', 'editor'):
            abort(403)
        row = db().execute('SELECT body FROM skill_transfer_sources WHERE source_id=? AND edition=?',
                           (source_id, edition)).fetchone()
        if not row:
            abort(404)
        response = jsonify(json.loads(row[0]))
        response.headers['Cache-Control'] = 'private, no-store'
        return response
