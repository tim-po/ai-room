"""Optional onboarding v1. No grading, lesson completion or inferred competence."""
import hashlib
import json
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import click
from flask import abort, g, jsonify, redirect, render_template, request, url_for
from jinja2 import TemplateNotFound

STEPS = ('welcome', 'interests', 'pace', 'start')
FIELDS = {'interests', 'experience', 'available_minutes', 'diagnostic_choice'}
SCHEMA = '''
CREATE TABLE IF NOT EXISTS onboarding_state (
 user_id TEXT PRIMARY KEY REFERENCES users(id), body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS onboarding_requests (
 user_id TEXT NOT NULL REFERENCES users(id), request_key TEXT NOT NULL,
 digest TEXT NOT NULL, response TEXT NOT NULL,
 PRIMARY KEY(user_id,request_key)
);
CREATE TABLE IF NOT EXISTS onboarding_events_v1 (
 user_id TEXT NOT NULL REFERENCES users(id), revision INTEGER NOT NULL,
 action TEXT NOT NULL, step TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(user_id,revision)
);
'''


def register_onboarding(app, db, query, require_user):
    def installed():
        return bool(query("SELECT 1 FROM sqlite_master WHERE type='table' AND name='onboarding_state'", one=True))

    def baseline(user):
        interests = [r['node_id'] for r in query('SELECT node_id FROM skill_interests WHERE user_id=? ORDER BY node_id', (user['id'],))]
        prefs = dict(interests=interests, experience=user['experience'], available_minutes=None, diagnostic_choice='unset')
        return dict(flow_version=1, status='completed' if user['onboarding_done'] else 'not_started',
                    step='welcome', draft=prefs.copy(), committed_preferences=prefs,
                    revision=0, return_to='/', updated_at=None, editing=False)

    def state(user):
        row = query('SELECT body FROM onboarding_state WHERE user_id=?', (user['id'],), True)
        value = json.loads(row['body']) if row else baseline(user)
        # Existing preferences/skip POST routes remain compatible during UI rollout.
        if user['onboarding_done'] and value['status'] in ('not_started', 'in_progress'):
            value.update(status='completed', editing=False, revision=value['revision'] + 1,
                         committed_preferences=baseline(user)['committed_preferences'])
        return value

    def persist(user, value):
        db().execute('INSERT INTO onboarding_state VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET body=excluded.body',
                     (user['id'], json.dumps(value, ensure_ascii=False)))

    def permitted(target, user):
        # Explicit route allowlist, no decoding/normalization ambiguities or arbitrary query redirects.
        if not isinstance(target, str) or len(target) > 256:
            return '/'
        if target in ('/', '/catalogue', '/profile', '/preferences', '/practice', '/diagnostic', '/help'):
            return target
        course = re.fullmatch(r'/courses/([A-Za-z0-9_.-]+)', target)
        if course and query("SELECT 1 FROM courses WHERE id=? AND status='published'", (course[1],), True):
            return target
        match = re.fullmatch(r'/lessons/([A-Za-z0-9_.-]+)', target)
        if match:
            row = query("""SELECT l.access FROM lessons l JOIN modules m ON m.id=l.module_id
                JOIN courses c ON c.id=m.course_id WHERE l.id=? AND l.status='published' AND c.status='published'""", (match[1],), True)
            if row and (row['access'] == 'free' or user['entitlement'] == 'member' or user['role'] != 'learner'):
                return target
        return '/'

    def response(value):
        result = json.loads(json.dumps(value))
        result['return_to'] = permitted(value['return_to'], g.user)
        lesson = query("""SELECT l.id,l.title,l.access FROM lessons l JOIN modules m ON m.id=l.module_id
            JOIN courses c ON c.id=m.course_id WHERE l.status='published' AND c.status='published'
            AND (l.access='free' OR ?='member') ORDER BY c.id,m.position,l.position,l.id LIMIT 1""", (g.user['entitlement'],), True)
        result['recommendation'] = dict(lesson_id=lesson['id'], title=lesson['title'], url='/lessons/'+lesson['id'], reason='available_learning') if lesson else None
        from .release_bindings import available_forms
        from .transfer_sources import form_content_access
        from .form_lifecycle import lifecycle
        active = query('SELECT release_id FROM skill_active WHERE singleton=1', one=True)
        available = bool(active and any(lifecycle(query, f['id'])['status'] == 'active' and form_content_access(db(), f, g.user) for f in available_forms(query, active['release_id'])))
        result['diagnostic'] = dict(available=available, start_url='/api/skills/diagnostics' if available else None)
        result['next_url'] = result['return_to'] if value['status'] in ('completed', 'skipped') and not value['editing'] else None
        return result

    @app.cli.command('init-onboarding')
    def migrate():
        """Run quiescent: paired private backup before additive onboarding storage."""
        if not query("SELECT 1 FROM sqlite_master WHERE name='skill_interests'", one=True):
            raise click.ClickException('Run init-skills first.')
        root = Path(app.config['DATABASE']).parent / ('before-onboarding-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f'))
        root.mkdir(mode=0o700)
        with sqlite3.connect(root / 'database.sqlite') as backup:
            db().backup(backup)
        (root / 'database.sqlite').chmod(0o600)
        for label, source in [('media', Path(app.instance_path)/'media'), ('teaching-uploads', Path(app.config['TEACHING_UPLOAD_DIR']))]:
            if source.exists():
                shutil.copytree(source, root/label)
        key = Path(app.instance_path)/'session.key'
        if key.exists():
            shutil.copy2(key, root/'session.key')
            (root/'session.key').chmod(0o600)
        db().executescript(SCHEMA)
        with db():
            for user in query('SELECT * FROM users'):
                if not query('SELECT 1 FROM onboarding_state WHERE user_id=?', (user['id'],), True):
                    persist(user, baseline(user))
        click.echo('Onboarding v1 ready; private paired backup: ' + str(root))

    def login_destination(user, target):
        if user['role'] != 'learner' or not installed():
            return target
        with db():
            db().execute('BEGIN IMMEDIATE')
            value = state(user)
            if value['status'] in ('completed', 'skipped'):
                return permitted(target, user)
            safe = permitted(target, user)
            if safe != '/' and value['return_to'] != safe:
                value['return_to'] = safe
                value['revision'] += 1
                value['updated_at'] = datetime.now(timezone.utc).isoformat()
                persist(user, value)
        return '/onboarding'

    @app.before_request
    def learner_entry():
        if (request.method == 'GET' and g.user and g.user['role'] == 'learner'
                and request.endpoint in {'home', 'catalogue', 'course', 'lesson', 'profile', 'preferences', 'skill_tree'}
                and installed()):
            value = state(g.user)
            if value['status'] not in ('completed', 'skipped'):
                return redirect(login_destination(g.user, request.path))

    def learner():
        if g.user['role'] != 'learner':
            abort(403)
        if not installed():
            abort(503, 'Onboarding storage has not been migrated.')

    @app.get('/onboarding')
    @require_user
    def onboarding():
        learner()
        try:
            return render_template('onboarding.html', onboarding=response(state(g.user)))
        except TemplateNotFound:
            abort(503, 'Onboarding screen is awaiting the UI integration.')

    @app.route('/api/onboarding', methods=['GET', 'PUT'])
    @require_user
    def onboarding_api():
        learner()
        if request.method == 'GET':
            return jsonify(response(state(g.user)))
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or set(payload) - {'action', 'expected_revision', 'idempotency_key', 'draft', 'step'}:
            abort(400)
        action, revision, key = (payload.get(k) for k in ('action', 'expected_revision', 'idempotency_key'))
        if action not in ('save', 'back', 'next', 'complete', 'skip', 'edit', 'cancel') or type(revision) is not int or revision < 0:
            abort(400)
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{8,128}', key):
            abort(400)
        patch = payload.get('draft', {})
        if not isinstance(patch, dict) or set(patch) - FIELDS:
            abort(400)
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with db():
            db().execute('BEGIN IMMEDIATE')
            prior = query('SELECT * FROM onboarding_requests WHERE user_id=? AND request_key=?', (g.user['id'], key), True)
            if prior:
                if prior['digest'] != digest:
                    return jsonify(error='idempotency_conflict', state=response(state(g.user))), 409
                return jsonify(response(json.loads(prior['response'])))
            value = state(g.user)
            if revision != value['revision']:
                return jsonify(error='revision_conflict', state=response(value)), 409
            terminal = value['status'] in ('completed', 'skipped')
            if (terminal and not value['editing'] and action != 'edit') or (action == 'edit' and (not terminal or value['editing'])) or (action == 'cancel' and not value['editing']):
                return jsonify(error='transition_conflict', state=response(value)), 409
            if action in ('edit', 'cancel', 'skip') and patch:
                abort(400)
            proposed = dict(value['draft'], **patch)
            interests = proposed['interests']
            if not isinstance(interests, list) or len(interests) > 100 or any(not isinstance(i, str) for i in interests):
                abort(400)
            if 'interests' in patch or action == 'complete':
                row = query('SELECT r.body FROM skill_releases r JOIN skill_active a ON a.release_id=r.id', one=True)
                ids = {n['id'] for n in json.loads(row['body'])['nodes']} if row else set()
                if set(interests) - ids:
                    abort(400)
            if proposed['experience'] not in (None, 'beginner', 'experienced') or proposed['diagnostic_choice'] not in ('unset', 'skip', 'start'):
                abort(400)
            minutes = proposed['available_minutes']
            if minutes is not None and (type(minutes) is not int or minutes not in (5, 10, 20)):
                abort(400)
            proposed['interests'] = sorted(set(interests))
            step = value['step']
            if action in ('next', 'back'):
                index = STEPS.index(step) + (1 if action == 'next' else -1)
                if not 0 <= index < len(STEPS):
                    abort(400)
                step = STEPS[index]
            elif action == 'edit':
                step = 'interests'
            if 'step' in payload and payload['step'] != step:
                abort(400)
            if action == 'complete' and not value['editing'] and value['step'] != 'start':
                abort(400)
            changed = proposed != value['draft'] or step != value['step'] or action not in ('save',)
            value.update(draft=proposed, step=step)
            if action == 'edit':
                current = baseline(g.user)['committed_preferences']
                value['committed_preferences'].update(interests=current['interests'], experience=current['experience'])
                value.update(editing=True, draft=value['committed_preferences'].copy())
            elif action == 'cancel':
                value.update(editing=False, draft=value['committed_preferences'].copy())
            elif action == 'complete':
                value.update(status='completed', editing=False, committed_preferences=proposed.copy())
                db().execute('DELETE FROM skill_interests WHERE user_id=?', (g.user['id'],))
                db().executemany('INSERT INTO skill_interests VALUES(?,?)', [(g.user['id'], i) for i in proposed['interests']])
                db().execute('UPDATE users SET onboarding_done=1,experience=COALESCE(?,experience) WHERE id=?', (proposed['experience'], g.user['id']))
            elif action == 'skip':
                value.update(status='skipped', editing=False)
                db().execute('UPDATE users SET onboarding_done=1 WHERE id=?', (g.user['id'],))
            elif not value['editing']:
                value['status'] = 'in_progress'
            value['revision'] += 1
            value['updated_at'] = datetime.now(timezone.utc).isoformat()
            persist(g.user, value)
            if changed:
                db().execute('INSERT INTO onboarding_events_v1(user_id,revision,action,step) VALUES(?,?,?,?)', (g.user['id'], value['revision'], action, value['step']))
            db().execute('INSERT INTO onboarding_requests VALUES(?,?,?,?)', (g.user['id'], key, digest, json.dumps(value)))
            return jsonify(response(value))

    return login_destination
