"""Optional, bounded placement orchestration; grades remain in challenge service."""
import json
import uuid

from flask import abort, g, jsonify


def register_diagnostics(app, db, query, require_user, graph, data):
    def owned(id):
        row = query('SELECT * FROM skill_diagnostics WHERE id=? AND user_id=?', (id, g.user['id']), True)
        if not row:
            abort(404)
        return row

    def accessible(form):
        return form['access'] == 'free' or g.user['entitlement'] == 'member' or g.user['role'] in ('editor', 'admin')

    def dto(row):
        plan = json.loads(row['body'])
        release = json.loads(query('SELECT body FROM skill_releases WHERE id=?', (row['release_id'],), True)['body'])
        revisions = {n['id']: n['revision'] for n in release['nodes']}
        verified = {r['objective_id'] for r in query('SELECT objective_id,objective_revision FROM skill_evidence WHERE user_id=?', (g.user['id'],)) if revisions.get(r['objective_id']) == r['objective_revision']}
        observations, tested, recommendations = [], set(), []
        for attempt_id in plan['attempts']:
            attempt = query('''SELECT f.access,r.body FROM skill_attempts a JOIN skill_forms f ON f.id=a.form_id
                               JOIN skill_results r ON r.attempt_id=a.id WHERE a.id=?''', (attempt_id,), True)
            result = json.loads(attempt['body'])
            tested.update(result['objective_scores'])
            observations.append(dict(attempt_id=attempt_id, passed=result['passed'], credited=result['credited'], access_required=not accessible(attempt)))
            if accessible(attempt):
                recommendations.extend(dict(objective_id=f['objective_id'], source=f['source'], reason='gap') for f in result['feedback'] if not f['correct'])
        next_form = None
        if row['state'] == 'active' and row['release_id'] == graph()['release'] and len(plan['attempts']) < 8:
            for form_id in plan['forms']:
                form = query('SELECT * FROM skill_forms WHERE id=?', (form_id,), True)
                objectives = set(json.loads(form['body'])['thresholds']['objectives'])
                if objectives <= verified | tested or not accessible(form):
                    continue
                pending = query('''SELECT a.id FROM skill_attempts a LEFT JOIN skill_results r ON r.attempt_id=a.id
                                   WHERE a.user_id=? AND a.form_id=? AND r.attempt_id IS NULL''', (g.user['id'], form_id), True)
                next_form = dict(assessment_id=form_id, node_id=form['node_id'], objective_ids=sorted(objectives),
                                 pending_attempt_id=pending['id'] if pending else None,
                                 reason='foundation' if objectives & set(plan['foundations']) else 'selected_interest')
                break
        state = row['state'] if row['state'] != 'active' else ('active' if next_form else 'completed')
        return dict(id=row['id'], revision=row['revision'], release=row['release_id'], interests=plan['interests'],
                    state=state, next=next_form, observations=observations, recommendations=recommendations,
                    verified_objectives=sorted(set(plan['scope']) & verified),
                    unknown_objectives=sorted(set(plan['scope']) - verified - tested))

    @app.post('/api/skills/diagnostics')
    @require_user
    def create():
        value = data()
        key, interests = value.get('request_id'), value.get('interests', [])
        if not isinstance(key, str) or not 8 <= len(key) <= 128 or not isinstance(interests, list) or len(interests) > 100 or any(not isinstance(i, str) for i in interests):
            abort(400)
        interests = sorted(set(interests))
        with db():
            db().execute('BEGIN IMMEDIATE')
            prior = query('SELECT * FROM skill_diagnostics WHERE user_id=? AND request_id=?', (g.user['id'], key), True)
            if prior:
                if json.loads(prior['body'])['interests'] != interests:
                    abort(409)
                return jsonify(dto(prior))
            tree = graph()
            nodes = {n['id']: n for n in tree['nodes']}
            if any(i not in nodes for i in interests):
                abort(400)
            def descendants(start, foundation=False):
                seen, todo, result = set(), [start], set()
                while todo:
                    node = todo.pop()
                    if node in seen or (foundation and nodes[node]['kind'] == 'branch'):
                        continue
                    seen.add(node)
                    if nodes[node]['kind'] == 'ability':
                        result.add(node)
                    todo.extend(e['target'] for e in tree['edges'] if e['source'] == node and e['type'] == 'contains')
                return result
            foundations = descendants(tree['root'], True)
            groups = [foundations] + [descendants(i) for i in interests]
            forms = query('SELECT * FROM skill_forms WHERE release_id=? ORDER BY id', (tree['release'],))
            queues = [[f['id'] for f in forms if set(json.loads(f['body'])['thresholds']['objectives']) <= group and accessible(f)] for group in groups]
            ordered = list(queues[0])
            # Foundations first, then interleave branches instead of exhausting one interest.
            for index in range(max((len(q) for q in queues[1:]), default=0)):
                ordered.extend(q[index] for q in queues[1:] if index < len(q))
            plan = dict(interests=interests, scope=sorted(set().union(*groups)), foundations=sorted(foundations), forms=list(dict.fromkeys(ordered)), attempts=[])
            id = str(uuid.uuid4())
            db().execute('INSERT INTO skill_diagnostics(id,user_id,request_id,release_id,body) VALUES(?,?,?,?,?)', (id, g.user['id'], key, tree['release'], json.dumps(plan)))
            return jsonify(dto(owned(id))), 201

    @app.get('/api/skills/diagnostics')
    @require_user
    def listing():
        return jsonify(diagnostics=[dto(r) for r in query('SELECT * FROM skill_diagnostics WHERE user_id=? ORDER BY created_at DESC,id LIMIT 50', (g.user['id'],))])

    @app.get('/api/skills/diagnostics/<id>')
    @require_user
    def resume(id):
        return jsonify(dto(owned(id)))

    @app.post('/api/skills/diagnostics/<id>/advance')
    @require_user
    def advance(id):
        value = data()
        if value.get('skip') is not True and not isinstance(value.get('attempt_id'), str):
            abort(400)
        with db():
            db().execute('BEGIN IMMEDIATE')
            row = owned(id)
            plan = json.loads(row['body'])
            if value.get('attempt_id') in plan['attempts']:
                return jsonify(dto(row))
            if type(value.get('revision')) is not int or value['revision'] != row['revision']:
                abort(409)
            if row['state'] != 'active' or len(plan['attempts']) >= 8:
                abort(409)
            if value.get('skip') is True:
                state = 'skipped'
            else:
                attempt = query('''SELECT a.form_id,f.access FROM skill_attempts a JOIN skill_results r ON r.attempt_id=a.id
                                   JOIN skill_forms f ON f.id=a.form_id WHERE a.id=? AND a.user_id=?''', (value.get('attempt_id'), g.user['id']), True)
                # Current evidence may already have removed a just-passed form from next.
                if not attempt or attempt['form_id'] not in plan['forms'] or not accessible(attempt):
                    abort(400)
                plan['attempts'].append(value['attempt_id'])
                state = 'active'
            db().execute('UPDATE skill_diagnostics SET body=?,state=?,revision=revision+1 WHERE id=?', (json.dumps(plan), state, id))
            return jsonify(dto(owned(id)))
