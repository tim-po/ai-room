"""Additive graph and deterministic reviewed knowledge challenges.

Forms and releases are immutable. Source review is an explicit editorial operation;
there is intentionally no automatic certification from generated or saved text.
"""
import json
import hashlib
import unicodedata
import math
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import click
from .reviewer_identity import reviewer_identity
from .form_lifecycle import lifecycle, register_form_lifecycle
from .release_bindings import available_forms, form_available, carry_forms
from flask import abort, g, jsonify, request


def item_exposure_keys(item):
    """Ignore packaging and choice ordering; retain editorial variant lineage."""
    def normalize(value):
        return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())
    payload = [normalize(item['prompt']), sorted(normalize(c['text']) for c in item['choices'])]
    keys = {'content:' + hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()}
    if item.get('lineage_id'):
        keys.add('lineage:' + item['lineage_id'])
    return keys


def form_exposure_keys(body):
    return set().union(*(item_exposure_keys(item) for item in body['items']))


def validate_form(form, graph):
    objectives = {n['id']: n for n in graph['nodes'] if n['kind'] == 'ability'}
    items = form.get('items', [])
    if not isinstance(items, list) or not 2 <= len(items) <= 40:
        raise ValueError('A reviewed form needs 2–40 items')
    ids, coverage, observations = set(), {}, set()
    for item in items:
        if item['id'] in ids or item['objective_id'] not in objectives:
            raise ValueError('Invalid item identity or objective')
        ids.add(item['id'])
        if 'lineage_id' in item and (not isinstance(item['lineage_id'], str) or not 1 <= len(item['lineage_id']) <= 128):
            raise ValueError('Invalid item lineage')
        choices = item['choices']
        if len(choices) < 2 or item['answer'] not in {c['id'] for c in choices} or len({c['id'] for c in choices}) != len(choices):
            raise ValueError('Invalid answer choices')
        if not item.get('source') or not item.get('rationale') or not item.get('prompt'):
            raise ValueError('Source and rationale required')
        if item['type'] not in ('knowledge', 'scenario') or not isinstance(item.get('critical', False), bool):
            raise ValueError('Invalid item type')
        keys = item_exposure_keys(item)
        if keys & observations:
            raise ValueError('Repeated observation cannot satisfy independent coverage')
        observations.update(keys)
        coverage.setdefault(item['objective_id'], []).append(item)
    for group in coverage.values():
        if len(group) < 2 or not any(i['type'] == 'scenario' for i in group):
            raise ValueError('Each objective needs two observations including a scenario')
    # Independence and semantic source support additionally require human review.
    return {'overall': math.ceil(len(items) * .8), 'total': len(items),
            'objectives': {id: math.ceil(len(group) * .75) for id, group in coverage.items()},
            'critical_required': [i['id'] for i in items if i.get('critical')]}


def publish_reviewed_form(db, *, id, graph, node_id, form, access, reviewer):
    """Internal editorial boundary; callers must supply an authenticated reviewer."""
    user = db.execute('SELECT role FROM users WHERE id=?', (reviewer,)).fetchone()
    if not user or user[0] not in ('admin', 'editor'):
        raise ValueError('Editor review required')
    if node_id not in {n['id'] for n in graph['nodes']}:
        raise ValueError('Unknown node')
    form = dict(form, thresholds=validate_form(form, graph), score_rule=graph['score_rule'])
    db.execute('INSERT INTO skill_forms(id,release_id,node_id,body,access,reviewed_by) VALUES(?,?,?,?,?,?)',
               (id, graph['release'], node_id, json.dumps(form, ensure_ascii=False), access, reviewer))


def register_skills(app, db, query, require_user):
    from .transfer_sources import register_transfer_sources, transfer_access
    register_transfer_sources(app, db)
    def graph():
        try:
            row = query('SELECT r.body FROM skill_active a JOIN skill_releases r ON r.id=a.release_id WHERE singleton=1', one=True)
        except sqlite3.OperationalError:
            abort(409, 'Дерево ещё не установлено. Требуется init-skills.')
        if not row:
            abort(409, 'Дерево ещё не опубликовано.')
        return json.loads(row['body'])

    def data():
        value = request.get_json(silent=True)
        if not isinstance(value, dict):
            abort(400)
        return value

    def valid_node(id, tree):
        node = next((n for n in tree['nodes'] if n['id'] == id), None)
        if not node:
            abort(404)
        return node

    def form_access(form):
        if not transfer_access(db(), form, g.user):
            abort(403)
        if form['access'] != 'free' and g.user['entitlement'] != 'member' and g.user['role'] not in ('editor', 'admin'):
            abort(403)

    def learner_attempts():
        if not g.user:
            return []
        return query('''SELECT a.id,a.form_id,a.mode,a.created_at,f.node_id,f.release_id,f.access,f.body,
                        r.attempt_id AS finished,r.created_at AS completed_at
                        FROM skill_attempts a JOIN skill_forms f ON f.id=a.form_id
                        LEFT JOIN skill_results r ON r.attempt_id=a.id
                        WHERE a.user_id=? ORDER BY a.created_at,a.id''', (g.user['id'],))

    def pending_attempts():
        return [row for row in learner_attempts() if not row['finished']]

    def exposure(body, attempts):
        keys = form_exposure_keys(body)
        overlaps = [row for row in attempts if keys & form_exposure_keys(json.loads(row['body']))]
        return ([row for row in overlaps if not row['finished']],
                any(row['finished'] for row in overlaps))

    def pending_metadata(row):
        accessible = transfer_access(db(), row, g.user) and (row['access'] == 'free' or g.user['entitlement'] == 'member' or g.user['role'] in ('editor', 'admin'))
        return dict(id=row['id'], assessment_id=row['form_id'], node_id=row['node_id'],
                    mode=row['mode'], release=row['release_id'], created_at=row['created_at'],
                    resume_url='/api/skills/challenges/' + row['id'], access_required=not accessible,
                    lifecycle=lifecycle(query, row['form_id']))

    register_form_lifecycle(app, db, query, require_user, graph, data)

    from .graph_review import register_graph_review
    register_graph_review(app, db, query, require_user, graph, data)

    from .practical import register_practical
    register_practical(app, db, query, require_user, graph, data)

    from .diagnostics import register_diagnostics
    register_diagnostics(app, db, query, require_user, graph, data)

    @app.cli.command('init-skills')
    def init_skills():
        database = Path(app.config['DATABASE'])
        backup = database.with_name(database.name + '.before-skills-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f') + '.sqlite')
        with sqlite3.connect(backup) as dest:
            db().backup(dest)
        backup.chmod(0o600)
        db().executescript(Path(__file__).with_name('skills_schema.sql').read_text())
        from .skill_seed import seed_graph
        with db():
            seed_graph(db())
            # Backfill only previously approved structural transitions. The
            # immutable event records supply reviewer and transition authority.
            for event in query("SELECT * FROM skill_graph_events WHERE action IN ('activate','rollback') ORDER BY id"):
                target = json.loads(query('SELECT body FROM skill_releases WHERE id=?', (event['to_release'],), True)['body'])
                carry_forms(db(), query, event['from_release'], target, event['actor_id'])
        click.echo('Competency tables and graph ready; baseline backup: ' + str(backup))

    @app.cli.command('install-skill-examples')
    def install_skill_examples():
        """Install original text lessons/mappings, without publishing assessment keys."""
        from .skill_content import install_examples
        database = Path(app.config['DATABASE'])
        backup = database.with_name(database.name + '.before-skill-examples-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f') + '.sqlite')
        with sqlite3.connect(backup) as dest:
            db().backup(dest)
        backup.chmod(0o600)
        try:
            with db():
                db().execute('BEGIN IMMEDIATE')
                changed = install_examples(db())
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(('Examples installed; assessments await review.' if changed else 'Examples already installed; no changes.') + ' Backup: ' + str(backup))

    @app.cli.command('install-skill-foundations')
    @click.option('--from-release', required=True, help='Exact current release inspected for additive rebase.')
    @click.option('--reviewer', required=True, help='Existing editor/admin ID recording content installation.')
    def install_skill_foundations(from_release, reviewer):
        """Add six original teaching cases; do not publish assessment candidates."""
        from .foundation_content import install_foundations
        database = Path(app.config['DATABASE'])
        backup = database.with_name(database.name + '.before-foundations-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f') + '.sqlite')
        with sqlite3.connect(backup) as dest:
            db().backup(dest)
        backup.chmod(0o600)
        try:
            with db():
                db().execute('BEGIN IMMEDIATE')
                changed = install_foundations(db(), from_release=from_release, reviewer=reviewer)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(('Foundation sources installed; assessments remain private.' if changed else 'Already installed; no changes.') + ' Backup: ' + str(backup))

    @app.cli.command('install-skill-specialists')
    @click.option('--from-release', required=True, help='Exact inspected current release for additive rebase.')
    @click.option('--reviewer', required=True, help='Existing editor/admin ID.')
    def install_skill_specialists(from_release, reviewer):
        """Add worked teaching sources; preserve forms and learner history."""
        from .specialist_content import install_specialists
        database = Path(app.config['DATABASE'])
        backup = database.with_name(database.name + '.before-specialists-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f') + '.sqlite')
        with sqlite3.connect(backup) as dest:
            db().backup(dest)
        backup.chmod(0o600)
        try:
            with db():
                db().execute('BEGIN IMMEDIATE')
                changed = install_specialists(db(), from_release=from_release, reviewer=reviewer)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(('Specialist teaching installed; no assessments published.' if changed else 'Already installed; no changes.') + ' Backup: ' + str(backup))

    @app.cli.command('inspect-skill-specialists')
    def inspect_skill_specialists():
        """Export persisted source/mapping inventory for independent review."""
        from .specialist_content import inventory
        try:
            click.echo(json.dumps(inventory(db()), ensure_ascii=False, indent=2))
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

    @app.cli.command('inspect-skill-foundations')
    def inspect_skill_foundations():
        """Private operator preview: includes keys, never serve publicly."""
        from .foundation_content import installed_candidates
        try:
            click.echo(json.dumps(installed_candidates(db()), ensure_ascii=False, indent=2))
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

    @app.cli.command('inspect-skill-examples')
    def inspect_skill_examples():
        """Private operator preview, including answer keys. Never serve publicly."""
        from .skill_content import CASES, candidate_form
        click.echo(json.dumps([candidate_form(case) for case in CASES], ensure_ascii=False, indent=2))

    @app.cli.command('review-skill-examples')
    @click.option('--reviewer', required=True, help='Existing editor/admin user ID.')
    @click.option('--confirm-reviewed', is_flag=True, help='Confirm source support, independent coverage and unambiguous answers were reviewed.')
    def review_skill_examples(reviewer, confirm_reviewed):
        """Publish only after an operator has inspected each candidate and source."""
        from .skill_content import review_examples
        if not confirm_reviewed:
            raise click.ClickException('Inspect candidates and sources first; explicit --confirm-reviewed is required.')
        try:
            with db():
                db().execute('BEGIN IMMEDIATE')
                review_examples(db(), reviewer)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo('Reviewed example forms published. Credit is understanding only.')

    @app.get('/api/skills/graph')
    def skill_graph():
        tree = graph()
        return jsonify({k: v for k, v in tree.items() if k != 'mappings'})

    @app.put('/api/skills/interests')
    @require_user
    def interests():
        tree, values = graph(), data().get('node_ids')
        if not isinstance(values, list) or len(values) > 100 or any(not isinstance(v, str) for v in values):
            abort(400)
        for value in values:
            valid_node(value, tree)
        with db():
            db().execute('DELETE FROM skill_interests WHERE user_id=?', (g.user['id'],))
            db().executemany('INSERT INTO skill_interests VALUES(?,?)', [(g.user['id'], v) for v in set(values)])
        return jsonify(interests=sorted(set(values)))

    @app.post('/api/skills/explore')
    @require_user
    def explore():
        node = valid_node(data().get('node_id'), graph())
        with db():
            db().execute('''INSERT INTO skill_explorations(user_id,node_id) VALUES(?,?)
                ON CONFLICT(user_id,node_id) DO UPDATE SET updated_at=CURRENT_TIMESTAMP''', (g.user['id'], node['id']))
        return jsonify(ok=True)

    @app.get('/api/skills/me')
    @require_user
    def skill_me():
        tree = graph()
        evidence = [dict(r) for r in query('SELECT * FROM skill_evidence WHERE user_id=?', (g.user['id'],))]
        for entry in evidence:
            row = query('''SELECT f.id,f.body,f.access,f.created_at AS reviewed_at,r.created_at AS assessed_at
                           FROM skill_attempts a JOIN skill_forms f ON f.id=a.form_id
                           JOIN skill_results r ON r.attempt_id=a.id WHERE a.id=?''', (entry['attempt_id'],), True)
            body = json.loads(row['body'])
            accessible = transfer_access(db(), row, g.user) and (row['access'] == 'free' or g.user['entitlement'] == 'member' or g.user['role'] in ('editor', 'admin'))
            entry.update(assessment_id=row['id'], score_rule=body['score_rule'], assessed_at=row['assessed_at'],
                         review=dict(status='editor_reviewed', reviewed_at=row['reviewed_at']),
                         source_access_required=not accessible,
                         sources=[i['source'] for i in body['items'] if i['objective_id'] == entry['objective_id']] if accessible else [])
        application_evidence = [dict(r) for r in query('''SELECT e.*,t.form_id AS assessment_id,f.release_id,
                                  t.id AS task_id,d.created_at AS reviewed_at,d.reviewer_id FROM skill_application_evidence e
                                  JOIN skill_practical_submissions s ON s.id=e.submission_id
                                  JOIN skill_practical_tasks t ON t.id=s.task_id
                                  JOIN skill_forms f ON f.id=t.form_id
                                  JOIN skill_practical_decisions d ON d.submission_id=s.id WHERE e.user_id=?''', (g.user['id'],))]
        for entry in application_evidence:
            entry['reviewer'] = reviewer_identity(entry.pop('reviewer_id'))
        applied = {(r['objective_id'], r['objective_revision']) for r in application_evidence}
        verified = {(r['objective_id'], r['objective_revision']) for r in evidence}
        assessed = set(verified)
        for row in query('''SELECT f.body, sr.body AS release_body FROM skill_results r
                           JOIN skill_attempts a ON a.id=r.attempt_id
                           JOIN skill_forms f ON f.id=a.form_id
                           JOIN skill_releases sr ON sr.id=f.release_id WHERE a.user_id=?''', (g.user['id'],)):
            revisions = {n['id']: n['revision'] for n in json.loads(row['release_body'])['nodes']}
            assessed.update((i['objective_id'], revisions[i['objective_id']]) for i in json.loads(row['body'])['items'])
        children = {}
        for e in tree['edges']:
            if e['type'] == 'contains':
                children.setdefault(e['source'], []).append(e['target'])
        nodes = {n['id']: n for n in tree['nodes']}
        def abilities(id, foundation_only=False):
            # Deduplicate shared descendants; tolerate cycles in historical imports.
            result, seen, todo = set(), set(), [id]
            while todo:
                current = todo.pop()
                if current in seen or current not in nodes:
                    continue
                seen.add(current)
                if foundation_only and nodes[current]['kind'] == 'branch':
                    continue
                if nodes[current]['kind'] == 'ability':
                    result.add(current)
                todo.extend(children.get(current, []))
            return result

        def summarize(node_id, eligible):
            count = sum((id, nodes[id]['revision']) in verified for id in eligible)
            tested = sum((id, nodes[id]['revision']) in assessed for id in eligible)
            return dict(node_id=node_id, eligible=len(eligible), assessed=tested, verified=count,
                        unknown=len(eligible) - tested,
                        verified_coverage=count / len(eligible) if eligible else None, application_verified=sum((id, nodes[id]['revision']) in applied for id in eligible))

        coverage = [summarize(n['id'], abilities(n['id'])) for n in tree['nodes']]
        foundation = dict(summarize(tree['root'], abilities(tree['root'], foundation_only=True)), scope='foundation_only')
        return jsonify(release=tree['release'], score_rule=tree['score_rule'], coverage=coverage, evidence=evidence, application_evidence=application_evidence,
                       foundation_coverage=foundation, pending_attempts=[pending_metadata(r) for r in pending_attempts()],
                       interests=[r['node_id'] for r in query('SELECT node_id FROM skill_interests WHERE user_id=? ORDER BY node_id', (g.user['id'],))],
                       explorations=[dict(r) for r in query('SELECT node_id,updated_at FROM skill_explorations WHERE user_id=? ORDER BY updated_at DESC,node_id', (g.user['id'],))])

    @app.get('/api/skills/nodes/<node_id>')
    def node_detail(node_id):
        tree = graph()
        node = valid_node(node_id, tree)
        content = []
        for mapping in tree['mappings']:
            if mapping['objective_id'] != node_id:
                continue
            lesson = query('''SELECT l.id,l.title,l.access FROM lessons l JOIN modules m ON m.id=l.module_id
                              JOIN courses c ON c.id=m.course_id WHERE l.id=? AND l.status='published' AND c.status='published' ''', (mapping['lesson_id'],), True)
            if lesson:
                content.append(dict(lesson, source=mapping['source'], role=mapping['role']))
        forms = []
        attempts = learner_attempts()
        pending = [row for row in attempts if not row['finished']]
        completed = [row for row in attempts if row['finished'] and
                     (row['node_id'] == node_id or node_id in json.loads(row['body'])['thresholds']['objectives'])]
        latest = max(completed, key=lambda row: (row['completed_at'], row['created_at'], row['id'])) if completed else None
        latest_metadata = dict(pending_metadata(latest), completed_at=latest['completed_at']) if latest else None
        relevant = {r['id']: r for r in pending if r['node_id'] == node_id}
        for row in available_forms(query, tree['release']):
            if row['node_id'] != node_id:
                continue
            if lifecycle(query, row['id'])['status'] != 'active':
                continue
            body = json.loads(row['body'])
            overlaps, exposed = exposure(body, attempts)
            accessible = transfer_access(db(), row, g.user) and bool(g.user and (row['access'] == 'free' or g.user['entitlement'] == 'member' or g.user['role'] in ('editor', 'admin')))
            relevant.update({r['id']: r for r in overlaps})
            forms.append(dict(id=row['id'], access=row['access'], item_count=len(body['items']),
                              objective_ids=sorted(body['thresholds']['objectives']),
                              availability='active', credit_kind='understanding',
                              start_mode=('practice' if exposed else 'certification') if g.user else None,
                              exposed=exposed if g.user else None,
                              can_start=accessible and not overlaps,
                              credit_eligible=accessible and not overlaps and not exposed,
                              start_blocker='sign_in' if not g.user else 'access_required' if not accessible else 'pending_attempt' if overlaps else None,
                              pending_attempt=pending_metadata(overlaps[0]) if overlaps else None))
        return jsonify(node=node, content=content, assessments=forms, latest_completed_attempt=latest_metadata,
                       pending_attempts=[pending_metadata(r) for r in relevant.values()],
                       readiness=[e for e in tree['edges'] if e['type'] == 'prerequisite' and e['target'] == node_id])

    def attempt_dto(attempt):
        form = query('SELECT * FROM skill_forms WHERE id=?', (attempt['form_id'],), True)
        form_access(form)
        body = json.loads(form['body'])
        # Explicit allow-list: answer, rationale and future private fields cannot leak.
        items = []
        for item in body['items']:
            public = {k: item[k] for k in ('id', 'prompt', 'type', 'objective_id')}
            public['choices'] = [{k: choice[k] for k in ('id', 'text')} for choice in item['choices']]
            # The versioned random attempt ID persists the presentation seed. Old
            # UUID attempts retain their original order; no history migration.
            if attempt['id'].startswith('p1-'):
                def presentation_key(choice):
                    seed = json.dumps([attempt['id'], item['id'], choice['id']], separators=(',', ':'))
                    return hashlib.sha256(seed.encode()).digest()
                public['choices'].sort(key=presentation_key)
            if body.get('transfer_publication') and item['source'].get('source_id'):
                ref = item['source']
                retained = query('SELECT body FROM skill_transfer_sources WHERE source_id=? AND edition=?',
                                 (ref['source_id'], ref['edition']), True)
                if not retained:
                    abort(409, 'Источник проверки недоступен.')
                source = json.loads(retained['body'])
                if (source['sha256'] != ref['sha256'] or
                        hashlib.sha256(source['text'].encode()).hexdigest() != ref['sha256']):
                    abort(409, 'Версия источника проверки изменилась.')
                # Only the reviewed case, never the keyed form or arbitrary
                # source metadata. Current content access was checked above.
                public['case'] = dict(source_id=ref['source_id'], edition=ref['edition'],
                                      paragraph=ref.get('paragraph'), text=source['text'],
                                      sha256=source['sha256'])
            items.append(public)
        return dict(id=attempt['id'], mode=attempt['mode'], items=items, thresholds=body['thresholds'], release=form['release_id'], lifecycle=lifecycle(query, form['id']))

    @app.post('/api/skills/challenges')
    @require_user
    def challenge():
        tree = graph()
        value = data()
        key = value.get('request_id')
        if not isinstance(key, str) or not 8 <= len(key) <= 128:
            abort(400, 'Требуется request_id длиной 8–128 символов.')
        with db():
            db().execute('BEGIN IMMEDIATE')
            existing = query('SELECT * FROM skill_attempts WHERE user_id=? AND request_id=?', (g.user['id'], key), True)
            if existing:
                if existing['form_id'] != value.get('assessment_id'):
                    abort(409)
                return jsonify(attempt_dto(existing))
            form = query('SELECT * FROM skill_forms WHERE id=?', (value.get('assessment_id'),), True)
            if not form:
                abort(404)
            form_access(form)
            if lifecycle(query, form['id'])['status'] != 'active':
                return jsonify(error='Проверка снята с публикации.', lifecycle=lifecycle(query, form['id'])), 409
            # New attempts require an active release binding; pinned attempts can finish.
            if not form_available(query, form, tree['release']):
                abort(409, 'Эта версия проверки снята. Откройте актуальную проверку темы.')
            overlaps, exposed = exposure(json.loads(form['body']), learner_attempts())
            if overlaps:
                return jsonify(error='Сначала завершите начатую попытку с этими вопросами.',
                               code='pending_attempt', pending_attempt=pending_metadata(overlaps[0])), 409
            # Any overlap conservatively makes the whole form practice-only.
            id, mode = 'p1-' + str(uuid.uuid4()), 'practice' if exposed else 'certification'
            db().execute('INSERT INTO skill_attempts(id,user_id,form_id,request_id,mode) VALUES(?,?,?,?,?)', (id,g.user['id'],form['id'],key,mode))
            return jsonify(attempt_dto(dict(id=id, form_id=form['id'], mode=mode))), 201

    @app.get('/api/skills/challenges/<attempt_id>')
    @require_user
    def resume_attempt(attempt_id):
        attempt = query('SELECT * FROM skill_attempts WHERE id=? AND user_id=?', (attempt_id, g.user['id']), True)
        if not attempt:
            abort(404)
        dto = attempt_dto(attempt)
        result = query('SELECT body FROM skill_results WHERE attempt_id=?', (attempt_id,), True)
        dto['result'] = json.loads(result['body']) if result else None
        return jsonify(dto)

    @app.post('/api/skills/challenges/<attempt_id>/submit')
    @require_user
    def submit(attempt_id):
        value = data()
        with db():
            db().execute('BEGIN IMMEDIATE')
            attempt = query('SELECT * FROM skill_attempts WHERE id=? AND user_id=?', (attempt_id, g.user['id']), True)
            if not attempt:
                abort(404)
            form = query('SELECT * FROM skill_forms WHERE id=?', (attempt['form_id'],), True)
            form_access(form)
            existing = query('SELECT body FROM skill_results WHERE attempt_id=?', (attempt_id,), True)
            if existing:
                return jsonify(json.loads(existing['body']))
            body = json.loads(form['body'])
            answers = value.get('answers')
            if not isinstance(answers, dict) or set(answers) != {i['id'] for i in body['items']}:
                abort(400, 'Ответьте на все вопросы формы.')
            for item in body['items']:
                if answers[item['id']] not in [c['id'] for c in item['choices']]:
                    abort(400)
            correct = {i['id']: answers[i['id']] == i['answer'] for i in body['items']}
            scores = {obj: sum(correct[i['id']] for i in body['items'] if i['objective_id'] == obj) for obj in body['thresholds']['objectives']}
            passed = sum(correct.values()) >= body['thresholds']['overall'] and all(scores[o] >= t for o,t in body['thresholds']['objectives'].items()) and all(correct[i] for i in body['thresholds']['critical_required'])
            result = dict(id=attempt_id, passed=passed, mode=attempt['mode'], points=sum(correct.values()), thresholds=body['thresholds'],
                          objective_scores=scores, credited=passed and attempt['mode']=='certification' and lifecycle(query, form['id'])['status']=='active',
                          lifecycle=lifecycle(query, form['id']),
                          feedback=[dict(item_id=i['id'], correct=correct[i['id']], objective_id=i['objective_id'], rationale=i['rationale'], source=i['source']) for i in body['items']])
            db().execute('INSERT INTO skill_results(attempt_id,answers,body) VALUES(?,?,?)', (attempt_id,json.dumps(answers),json.dumps(result)))
            if result['credited']:
                release = json.loads(query('SELECT body FROM skill_releases WHERE id=?', (form['release_id'],), True)['body'])
                for node in release['nodes']:
                    if node['id'] in scores:
                        db().execute('''INSERT OR IGNORE INTO skill_evidence(user_id,release_id,objective_id,objective_revision,attempt_id,kind)
                                      VALUES(?,?,?,?,?,'understanding')''', (g.user['id'],form['release_id'],node['id'],node['revision'],attempt_id))
            return jsonify(result)
