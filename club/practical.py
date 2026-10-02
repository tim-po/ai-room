"""Pinned human-reviewed practical rubrics; uncertain decisions never certify."""
import json
import re
import uuid
from .form_lifecycle import lifecycle
from .release_bindings import available_forms, form_available

from flask import abort, g, jsonify, request


def register_practical(app, db, query, require_user, graph, data):
    def editor():
        if g.user['role'] not in ('editor', 'admin'):
            abort(403)

    def text(value, minimum, maximum):
        return isinstance(value, str) and minimum <= len(value.strip()) <= maximum

    def task(id):
        row = query('''SELECT t.*,f.release_id,f.access FROM skill_practical_tasks t
                       JOIN skill_forms f ON f.id=t.form_id WHERE t.id=?''', (id,), True)
        if not row:
            abort(404)
        if row['access'] != 'free' and g.user['entitlement'] != 'member' and g.user['role'] not in ('editor', 'admin'):
            abort(403)
        return row

    def task_dto(row):
        return dict(id=row['id'], assessment_id=row['form_id'], objective_id=row['objective_id'],
                    objective_revision=row['objective_revision'], release=row['release_id'], access=row['access'],
                    reviewed_at=row['created_at'], lifecycle=lifecycle(query, row['form_id']), **json.loads(row['body']))

    def submission(id, owner_only=False):
        row = query('SELECT * FROM skill_practical_submissions WHERE id=?', (id,), True)
        if not row or (row['user_id'] != g.user['id'] and (owner_only or g.user['role'] not in ('editor', 'admin'))):
            abort(404)
        if row['user_id'] != g.user['id'] and row['state'] == 'draft':
            abort(404)
        task(row['task_id'])
        return row

    def submission_dto(row):
        decision = query('SELECT * FROM skill_practical_decisions WHERE submission_id=?', (row['id'],), True)
        return dict(id=row['id'], task_id=row['task_id'], body=row['body'], revision=row['revision'],
                    state='reviewed' if decision else row['state'],
                    decision=dict(**json.loads(decision['body']), reviewed_at=decision['created_at']) if decision else None)

    @app.post('/api/skills/practical-tasks')
    @require_user
    def publish_task():
        editor()
        value = data()
        criteria = value.get('criteria')
        if value.get('confirm_reviewed') is not True or not text(value.get('instructions'), 30, 12000):
            abort(400)
        if not isinstance(criteria, list) or not 2 <= len(criteria) <= 12:
            abort(400)
        if any(not isinstance(c, dict) or not isinstance(c.get('id'), str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', c['id']) or not text(c.get('text'), 10, 2000) for c in criteria):
            abort(400)
        if len({c['id'] for c in criteria}) != len(criteria):
            abort(400)
        if not isinstance(value.get('assessment_id'), str) or not isinstance(value.get('objective_id'), str):
            abort(400)
        with db():
            db().execute('BEGIN IMMEDIATE')
            tree = graph()
            form = query('SELECT * FROM skill_forms WHERE id=?', (value['assessment_id'],), True)
            if not form or not form_available(query, form, tree['release']) or lifecycle(query, form['id'])['status'] != 'active':
                abort(409)
            objective = next((n for n in tree['nodes'] if n['id'] == value['objective_id'] and n['kind'] == 'ability'), None)
            sources = [i['source'] for i in json.loads(form['body'])['items'] if i['objective_id'] == value['objective_id']]
            if not objective or not sources:
                abort(400)
            body = dict(instructions=value['instructions'].strip(), criteria=[dict(id=c['id'], text=c['text'].strip()) for c in criteria],
                        sources=sources, credit_kind='application', scoring='all_criteria_met_by_human_reviewer')
            id = str(uuid.uuid4())
            db().execute('INSERT INTO skill_practical_tasks(id,form_id,objective_id,objective_revision,body,reviewed_by) VALUES(?,?,?,?,?,?)',
                         (id, form['id'], objective['id'], objective['revision'], json.dumps(body), g.user['id']))
            return jsonify(task_dto(task(id))), 201

    @app.get('/api/skills/practical-tasks')
    @require_user
    def list_tasks():
        rows = query('''SELECT t.*,f.release_id,f.access FROM skill_practical_tasks t JOIN skill_forms f ON f.id=t.form_id
                        ORDER BY t.created_at,t.id''')
        available = {f['id'] for f in available_forms(query, graph()['release'])}
        return jsonify(tasks=[task_dto(r) for r in rows if r['form_id'] in available and (not request.args.get('node_id') or r['objective_id'] == request.args['node_id'])
                              and lifecycle(query, r['form_id'])['status'] == 'active'
                              and (r['access'] == 'free' or g.user['entitlement'] == 'member' or g.user['role'] in ('editor', 'admin'))])

    @app.get('/api/skills/practical-tasks/<id>')
    @require_user
    def get_task(id):
        return jsonify(task_dto(task(id)))

    @app.post('/api/skills/practical-submissions')
    @require_user
    def create_submission():
        value = data()
        if not text(value.get('request_id'), 8, 128) or not isinstance(value.get('task_id'), str):
            abort(400)
        with db():
            db().execute('BEGIN IMMEDIATE')
            rubric = task(value['task_id'])
            prior = query('SELECT * FROM skill_practical_submissions WHERE user_id=? AND request_id=?', (g.user['id'], value['request_id']), True)
            if prior:
                if prior['task_id'] != rubric['id']:
                    abort(409)
                return jsonify(submission_dto(prior))
            if not form_available(query, dict(id=rubric['form_id'], release_id=rubric['release_id']), graph()['release']) or lifecycle(query, rubric['form_id'])['status'] != 'active':
                abort(409)
            pending = query('''SELECT s.id FROM skill_practical_submissions s LEFT JOIN skill_practical_decisions d ON d.submission_id=s.id
                               WHERE s.user_id=? AND s.task_id=? AND d.submission_id IS NULL''', (g.user['id'], rubric['id']), True)
            if pending:
                abort(409)
            id = str(uuid.uuid4())
            db().execute('INSERT INTO skill_practical_submissions(id,user_id,task_id,request_id) VALUES(?,?,?,?)',
                         (id, g.user['id'], rubric['id'], value['request_id']))
            return jsonify(submission_dto(submission(id))), 201

    @app.get('/api/skills/practical-submissions')
    @require_user
    def list_submissions():
        rows = query('''SELECT s.*,f.access FROM skill_practical_submissions s JOIN skill_practical_tasks t ON t.id=s.task_id
                        JOIN skill_forms f ON f.id=t.form_id WHERE s.user_id=? ORDER BY s.created_at DESC,s.id LIMIT 100''', (g.user['id'],))
        # A revoked entitlement exposes only recovery metadata, never protected source/work.
        return jsonify(submissions=[submission_dto(r) if r['access'] == 'free' or g.user['entitlement'] == 'member' or g.user['role'] in ('editor', 'admin')
                                    else dict(id=r['id'], task_id=r['task_id'], access_required=True) for r in rows])

    @app.get('/api/skills/practical-submissions/<id>')
    @require_user
    def get_submission(id):
        return jsonify(submission_dto(submission(id)))

    @app.put('/api/skills/practical-submissions/<id>')
    @require_user
    def save_submission(id):
        value = data()
        if not isinstance(value.get('body'), str) or len(value['body']) > 20000 or value.get('status') not in ('draft', 'submitted'):
            abort(400)
        if value['status'] == 'submitted' and not value['body'].strip():
            abort(400)
        with db():
            db().execute('BEGIN IMMEDIATE')
            row = submission(id, owner_only=True)
            if row['state'] == 'submitted' and value['status'] == 'submitted' and value['body'] == row['body']:
                return jsonify(submission_dto(row))
            if type(value.get('revision')) is not int or value['revision'] != row['revision'] or row['state'] != 'draft':
                abort(409)
            db().execute('UPDATE skill_practical_submissions SET body=?,state=?,revision=revision+1 WHERE id=?', (value['body'], value['status'], id))
            return jsonify(submission_dto(submission(id)))

    @app.get('/api/skills/practical-review')
    @require_user
    def review_queue():
        editor()
        rows = query('''SELECT s.* FROM skill_practical_submissions s LEFT JOIN skill_practical_decisions d ON d.submission_id=s.id
                        WHERE s.state='submitted' AND d.submission_id IS NULL AND s.user_id<>? ORDER BY s.created_at,s.id LIMIT 100''', (g.user['id'],))
        return jsonify(submissions=[submission_dto(r) for r in rows])

    @app.post('/api/skills/practical-submissions/<id>/review')
    @require_user
    def review_submission(id):
        editor()
        value = data()
        if not isinstance(value.get('ratings'), dict) or not text(value.get('feedback'), 10, 8000):
            abort(400)
        with db():
            db().execute('BEGIN IMMEDIATE')
            row = submission(id)
            if row['user_id'] == g.user['id']:
                abort(403)
            rubric = task(row['task_id'])
            expected = {c['id'] for c in json.loads(rubric['body'])['criteria']}
            ratings = value['ratings']
            if set(ratings) != expected or any(not isinstance(r, str) or r not in ('met', 'not_met', 'uncertain') for r in ratings.values()):
                abort(400)
            prior = query('SELECT body FROM skill_practical_decisions WHERE submission_id=?', (id,), True)
            if prior:
                saved = json.loads(prior['body'])
                if saved['ratings'] != ratings or saved['feedback'] != value['feedback'].strip():
                    abort(409)
                return jsonify(submission_dto(row))
            if row['state'] != 'submitted' or type(value.get('revision')) is not int or value['revision'] != row['revision']:
                abort(409)
            passed = all(r == 'met' for r in ratings.values())
            existing = query('SELECT 1 FROM skill_application_evidence WHERE user_id=? AND objective_id=? AND objective_revision=?',
                             (row['user_id'], rubric['objective_id'], rubric['objective_revision']), True)
            decision = dict(ratings=ratings, feedback=value['feedback'].strip(), passed=passed,
                            credited=passed and not bool(existing) and lifecycle(query, rubric['form_id'])['status']=='active', lifecycle=lifecycle(query, rubric['form_id']), kind='application', grading='human_reviewed')
            db().execute('INSERT INTO skill_practical_decisions(submission_id,reviewer_id,body) VALUES(?,?,?)', (id, g.user['id'], json.dumps(decision)))
            if decision['credited']:
                db().execute('INSERT INTO skill_application_evidence(user_id,objective_id,objective_revision,submission_id) VALUES(?,?,?,?)',
                             (row['user_id'], rubric['objective_id'], rubric['objective_revision'], id))
            return jsonify(submission_dto(row))
