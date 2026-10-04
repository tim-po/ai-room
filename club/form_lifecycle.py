"""Permanent per-form withdrawal, independent of active graph edition."""
import json
from flask import abort, g, jsonify
from .release_bindings import form_available, available_forms


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


def compatible_replacement(query, form, target):
    old = json.loads(form['body'])['thresholds']['objectives']
    new = json.loads(target['body'])['thresholds']['objectives']
    def revisions(row):
        release = json.loads(query('SELECT body FROM skill_releases WHERE id=?', (row['release_id'],), True)['body'])
        return {n['id']: n['revision'] for n in release['nodes']}
    old_rev, new_rev = revisions(form), revisions(target)
    if form['access'] != target['access'] or set(old) != set(new) or any(old_rev[o] != new_rev.get(o) for o in old):
        return False
    # A mapping-only descendant would immediately inherit this withdrawal.
    seen, ancestor = set(), target['id']
    while ancestor and ancestor not in seen:
        if ancestor == form['id']:
            return False
        seen.add(ancestor)
        row = query('SELECT body FROM skill_forms WHERE id=?', (ancestor,), True)
        ancestor = json.loads(row['body']).get('inherited_from_form') if row else None
    return True


def withdrawal_impact(query, form_id):
    """Count retained records across the same ancestry fenced by lifecycle()."""
    counts = query('''WITH RECURSIVE affected(id) AS (
        SELECT id FROM skill_forms WHERE id=?
        UNION
        SELECT f.id FROM skill_forms f JOIN affected a
          ON json_extract(f.body, '$.inherited_from_form')=a.id
    ), attempts AS (
        SELECT id,user_id FROM skill_attempts WHERE form_id IN (SELECT id FROM affected)
    ), tasks AS (
        SELECT id FROM skill_practical_tasks WHERE form_id IN (SELECT id FROM affected)
    ), submissions AS (
        SELECT id,user_id FROM skill_practical_submissions WHERE task_id IN (SELECT id FROM tasks)
    ) SELECT
        (SELECT COUNT(*) FROM affected) AS forms,
        (SELECT COUNT(*) FROM (SELECT user_id FROM attempts UNION SELECT user_id FROM submissions)) AS learners,
        (SELECT COUNT(*) FROM attempts) AS attempts,
        (SELECT COUNT(*) FROM attempts a WHERE NOT EXISTS
          (SELECT 1 FROM skill_results r WHERE r.attempt_id=a.id)) AS pending_attempts,
        (SELECT COUNT(*) FROM tasks) AS practical_tasks,
        (SELECT COUNT(*) FROM submissions) AS submissions,
        (SELECT COUNT(*) FROM submissions s WHERE NOT EXISTS
          (SELECT 1 FROM skill_practical_decisions d WHERE d.submission_id=s.id)) AS pending_submissions,
        (SELECT COUNT(*) FROM skill_evidence WHERE attempt_id IN (SELECT id FROM attempts)) AS understanding_evidence,
        (SELECT COUNT(*) FROM skill_application_evidence WHERE submission_id IN (SELECT id FROM submissions)) AS application_evidence
    ''', (form_id,), True)
    return dict(version=1, status='available', scope='form_and_inherited_descendants', counts=dict(counts))


def register_form_lifecycle(app, db, query, require_user, graph, data):
    @app.get('/api/skills/forms')
    @require_user
    def editorial_forms():
        if g.user['role'] not in ('editor', 'admin'):
            abort(403)
        tree = graph()
        names = {n['id']: n['title'] for n in tree['nodes']}
        current = available_forms(query, tree['release'])
        active = [f for f in current if lifecycle(query, f['id'])['status'] == 'active']
        rows = query('SELECT * FROM skill_forms ORDER BY id')
        result = []
        for row in rows:
            body = json.loads(row['body'])
            state = lifecycle(query, row['id'])
            result.append(dict(id=row['id'], title=names.get(row['node_id'], row['node_id']),
                node_id=row['node_id'], release_id=row['release_id'], access=row['access'],
                item_count=len(body['items']), lifecycle=state,
                impact=withdrawal_impact(query, row['id']),
                available=form_available(query, row, tree['release']),
                eligible_replacements=[f['id'] for f in active if compatible_replacement(query, row, f)] if state['status']=='active' else []))
        return jsonify(forms=result)

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
                if not target or replacement == form_id or not form_available(query, target, graph()['release']) or lifecycle(query, replacement)['status'] != 'active':
                    abort(409, 'Требуется действующая проверенная форма замены.')
                if not compatible_replacement(query, form, target):
                    abort(409, 'Замена должна сохранять цели, их смысл и доступ и не наследовать отозванную форму.')
            db().execute('INSERT INTO skill_form_withdrawals(form_id,replacement_id,reason,reviewer_id) VALUES(?,?,?,?)',
                         (form_id, replacement, reason.strip(), g.user['id']))
            return jsonify(lifecycle(query, form_id)), 201
