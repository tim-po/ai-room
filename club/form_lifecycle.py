"""Permanent per-form withdrawal, independent of active graph edition."""
import json
from flask import abort, g, jsonify


def lifecycle(query, form_id):
    # Mapping-only publications retain immutable form ancestry. Withdrawal of
    # any ancestor must also fence its copies, including copies already issued.
    seen = set()
    while form_id and form_id not in seen:
        seen.add(form_id)
        row = query('SELECT replacement_id,reason,created_at FROM skill_form_withdrawals WHERE form_id=?', (form_id,), True)
        if row:
            return dict(status='withdrawn', **dict(row))
        form = query('SELECT body FROM skill_forms WHERE id=?', (form_id,), True)
        form_id = json.loads(form['body']).get('inherited_from_form') if form else None
    return dict(status='active')


def register_form_lifecycle(app, db, query, require_user, graph, data):
    @app.post('/api/skills/forms/<form_id>/withdraw')
    @require_user
    def withdraw(form_id):
        if g.user['role'] not in ('editor', 'admin'):
            abort(403)
        value = data()
        reason, replacement = value.get('reason'), value.get('replacement_id')
        if value.get('confirm_reviewed') is not True or not isinstance(reason, str) or not 10 <= len(reason.strip()) <= 2000:
            abort(400)
        if replacement is not None and not isinstance(replacement, str):
            abort(400)
        with db():
            db().execute('BEGIN IMMEDIATE')
            form = query('SELECT * FROM skill_forms WHERE id=?', (form_id,), True)
            if not form:
                abort(404)
            prior = query('SELECT * FROM skill_form_withdrawals WHERE form_id=?', (form_id,), True)
            if prior:
                if prior['reason'] != reason.strip() or prior['replacement_id'] != replacement:
                    abort(409)
                return jsonify(lifecycle(query, form_id))
            if replacement is not None:
                target = query('SELECT * FROM skill_forms WHERE id=?', (replacement,), True)
                if not target or replacement == form_id or target['release_id'] != graph()['release'] or lifecycle(query, replacement)['status'] != 'active':
                    abort(409, 'Требуется действующая проверенная форма замены.')
                old = json.loads(form['body'])['thresholds']['objectives']
                new = json.loads(target['body'])['thresholds']['objectives']
                def revisions(row):
                    release = json.loads(query('SELECT body FROM skill_releases WHERE id=?', (row['release_id'],), True)['body'])
                    return {n['id']: n['revision'] for n in release['nodes']}
                old_rev, new_rev = revisions(form), revisions(target)
                if form['access'] != target['access'] or set(old) != set(new) or any(old_rev[o] != new_rev.get(o) for o in old):
                    abort(409, 'Замена должна сохранять цели, их смысл и доступ.')
            db().execute('INSERT INTO skill_form_withdrawals(form_id,replacement_id,reason,reviewer_id) VALUES(?,?,?,?)',
                         (form_id, replacement, reason.strip(), g.user['id']))
            return jsonify(lifecycle(query, form_id)), 201
