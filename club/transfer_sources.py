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


def publication_candidate(db, candidate_id, form_id, lesson_id):
    """Prepare exact keyed review bytes without publication."""
    candidate = next((c for c in bound_candidates(db) if c['id'] == candidate_id), None)
    if not candidate:
        raise ValueError('Unknown transfer candidate')
    lesson = db.execute('SELECT access FROM lessons WHERE id=?', (lesson_id,)).fetchone()
    if not lesson:
        raise ValueError('Existing lesson binding required')
    if not form_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in form_id):
        raise ValueError('Invalid publication ID')
    form = candidate['form']
    form['transfer_publication'] = dict(lesson_id=lesson_id, form_id=form_id, access=lesson[0],
                                      candidate_sha256=candidate['sha256'])
    for item in form['items']:
        source = item['source']
        source['snapshot_url'] = f"/api/skills/forms/{form_id}/sources/{source['source_id']}/{source['edition']}"
    return dict(candidate, form=form, sha256=digest(form), access=lesson[0])


def publish_transfer(db, *, candidate_id, form_id, lesson_id, graph, reviewer,
                     reviewed_sha256, confirm_reviewed=False):
    """Caller supplies a transaction; review names final bound hash."""
    from .skills import publish_reviewed_form
    candidate = publication_candidate(db, candidate_id, form_id, lesson_id)
    if confirm_reviewed is not True or reviewed_sha256 != candidate['sha256']:
        raise ValueError('Explicit exact-hash source, item and lesson-binding review required')
    row = db.execute("""SELECT l.status,c.status FROM lessons l JOIN modules m ON m.id=l.module_id
                        JOIN courses c ON c.id=m.course_id WHERE l.id=?""", (lesson_id,)).fetchone()
    if not row or tuple(row) != ('published', 'published'):
        raise ValueError('Published lesson and course required')
    publish_reviewed_form(db, id=form_id, graph=graph, node_id=candidate['node_id'],
                          form=candidate['form'], access=candidate['access'], reviewer=reviewer)
    return candidate['sha256']


def transfer_access(db, form, user):
    """Current lesson state fences retained source and feedback."""
    binding = json.loads(form['body']).get('transfer_publication')
    if not binding or (user and user['role'] in ('editor', 'admin')):
        return True
    row = db.execute("""SELECT l.status,l.access,c.status FROM lessons l
                        JOIN modules m ON m.id=l.module_id JOIN courses c ON c.id=m.course_id
                        WHERE l.id=?""", (binding['lesson_id'],)).fetchone()
    return bool(row and row[0] == row[2] == 'published' and
                (row[1] == 'free' or (user and user['entitlement'] == 'member')))


def form_content_access(db, form, user):
    """Authorize the original form tier AND its current bound content.

    Callers must supply the parent form body, not a result or rubric body.
    """
    return bool((form['access'] == 'free' or
                 (user and (user['entitlement'] == 'member' or user['role'] in ('editor', 'admin'))))
                and transfer_access(db, form, user))


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

    @app.get('/api/skills/forms/<form_id>/sources/<source_id>/<int:edition>')
    def published_snapshot(form_id, source_id, edition):
        from .form_lifecycle import lifecycle
        def query(sql, args=(), one=False):
            cursor = db().execute(sql, args)
            return cursor.fetchone() if one else cursor.fetchall()
        form = query('SELECT * FROM skill_forms WHERE id=?', (form_id,), True)
        if not form or not json.loads(form['body']).get('transfer_publication'):
            abort(404)
        staff = g.user and g.user['role'] in ('editor', 'admin')
        if not staff and lifecycle(query, form_id)['status'] != 'active':
            abort(404)
        if not transfer_access(db(), form, g.user):
            abort(403)
        if not staff and form['access'] != 'free' and (not g.user or g.user['entitlement'] != 'member'):
            abort(403)
        sources = [i['source'] for i in json.loads(form['body'])['items']]
        ref = next((s for s in sources if s.get('source_id') == source_id and s.get('edition') == edition), None)
        if not ref:
            abort(404)
        row = query('SELECT body FROM skill_transfer_sources WHERE source_id=? AND edition=?', (source_id, edition), True)
        if not row:
            abort(404)
        source = json.loads(row['body'])
        if source['sha256'] != ref['sha256']:
            abort(409)
        response = jsonify(source)
        response.headers['Cache-Control'] = 'private, no-store'
        return response
