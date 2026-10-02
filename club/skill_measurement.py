"""Read-only aggregate metrics. Never serialize source, answer or learner work bodies."""
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from flask import abort, g, jsonify, request


def register_skill_measurement(app, query):
    @app.get('/api/admin/measurement/skills')
    def report():
        if not g.user:
            abort(401)
        if g.user['role'] != 'admin':
            abort(403)
        today = datetime.now(timezone.utc).date()
        try:
            start = date.fromisoformat(request.args.get('start', (today - timedelta(days=29)).isoformat()))
            end = date.fromisoformat(request.args.get('end', (today + timedelta(days=1)).isoformat()))
        except ValueError:
            abort(400, 'Use UTC dates YYYY-MM-DD.')
        if not start < end or (end - start).days > 366:
            abort(400, 'Window must contain 1–366 days.')
        bounds = (start.isoformat(), end.isoformat())
        tables = {r['name'] for r in query("SELECT name FROM sqlite_master WHERE type='table'")}
        required = {'skill_diagnostics', 'skill_application_evidence', 'teaching_jobs', 'teaching_publications'}
        if not required <= tables:
            return jsonify(error='measurement_not_initialized', required_commands=['init-skills', 'init-teaching']), 503

        def rows(table, timestamp='created_at'):
            return query(f'''SELECT t.* FROM {table} t JOIN users u ON u.id=t.user_id
                             WHERE u.role='learner' AND t.{timestamp}>=? AND t.{timestamp}<?''', bounds)

        def ratio(numerator, denominator):
            return dict(numerator=numerator, denominator=denominator,
                        rate=numerator / denominator if denominator else None)

        forms = {r['id']: dict(r) for r in query('SELECT id,release_id,node_id,body FROM skill_forms')}
        results = {r['attempt_id']: json.loads(r['body']) for r in query('SELECT attempt_id,body FROM skill_results')}
        # Completion is evidence-based against the original plan, not today's inventory:
        # withdrawal or lost entitlement must not turn an unfinished placement into success.
        placement = Counter(started=0, completed=0, stopped=0, unfinished=0, unavailable=0)
        all_evidence = query('SELECT user_id,objective_id,objective_revision FROM skill_evidence')
        releases = {r['id']: json.loads(r['body']) for r in query('SELECT id,body FROM skill_releases')}
        for row in rows('skill_diagnostics'):
            placement['started'] += 1
            plan = json.loads(row['body'])
            revisions = {n['id']: n['revision'] for n in releases[row['release_id']]['nodes']}
            observed = {objective for attempt in plan['attempts'] for objective in results.get(attempt, {}).get('objective_scores', {})}
            observed.update(r['objective_id'] for r in all_evidence if r['user_id'] == row['user_id'] and revisions.get(r['objective_id']) == r['objective_revision'])
            planned = {objective for form in plan['forms'] for objective in json.loads(forms[form]['body'])['thresholds']['objectives']}
            state = ('stopped' if row['state'] == 'skipped' else 'unavailable' if not planned else
                     'completed' if planned <= observed or len(plan['attempts']) >= 8 else 'unfinished')
            placement[state] += 1
        placement = dict(placement)
        placement['completion'] = ratio(placement['completed'], placement['started'])

        attempts = rows('skill_attempts')
        challenges = {}
        for mode in ('certification', 'practice'):
            cohort = [r for r in attempts if r['mode'] == mode]
            completed = [results[r['id']] for r in cohort if r['id'] in results]
            challenges[mode] = dict(started=len(cohort), completed=len(completed), unfinished=len(cohort)-len(completed),
                                    passed=sum(bool(r['passed']) for r in completed))
        evidence = {}
        for kind, table in [('understanding', 'skill_evidence'), ('application', 'skill_application_evidence')]:
            credits = rows(table)
            evidence[kind] = dict(unique_objective_revision_credits=len(credits), learners=len({r['user_id'] for r in credits}))

        # Form provenance supplies historical branch attribution. Lesson activity has
        # no historical graph ID, so its current-release projection is explicit.
        branch_cache = {}
        def branches(release_id, node_id):
            key = (release_id, node_id)
            if key not in branch_cache:
                tree = releases[release_id]
                nodes = {n['id']: n for n in tree['nodes']}
                seen, todo, found = set(), [node_id], set()
                while todo:
                    node = todo.pop()
                    if node in seen:
                        continue
                    seen.add(node)
                    if nodes.get(node, {}).get('kind') == 'branch':
                        found.add(node)
                    todo.extend(e['source'] for e in tree['edges'] if e['type'] == 'contains' and e['target'] == node)
                branch_cache[key] = found
            return branch_cache[key]

        engagement = defaultdict(set)
        def add_form(user_id, form_id):
            form = forms[form_id]
            engagement[user_id].update(branches(form['release_id'], form['node_id']))
        for row in attempts:
            add_form(row['user_id'], row['form_id'])
        tasks = {r['id']: r['form_id'] for r in query('SELECT id,form_id FROM skill_practical_tasks')}
        for row in rows('skill_practical_submissions'):
            add_form(row['user_id'], tasks[row['task_id']])
        active = query('SELECT release_id FROM skill_active WHERE singleton=1', one=True)
        release_id = active['release_id'] if active else None
        mappings = defaultdict(set)
        if release_id:
            for mapping in releases[release_id]['mappings']:
                mappings[mapping['lesson_id']].update(branches(release_id, mapping['objective_id']))
        unmapped = 0
        for row in rows('events'):
            if row['name'] not in ('lesson_started', 'lesson_completed', 'practice_saved', 'practice_submitted'):
                continue
            engagement[row['user_id']].update(mappings[row['lesson_id']])
            unmapped += not bool(mappings[row['lesson_id']])
        multi = ratio(sum(len(b) >= 2 for b in engagement.values()), len(engagement))
        multi.update(lesson_mapping_release=release_id, lesson_mapping_mode='current_release_projection',
                     activities_without_major_branch=unmapped,
                     exploration_learners=len({r['user_id'] for r in rows('skill_explorations', 'updated_at')}))

        jobs = query('SELECT id,state,attempt FROM teaching_jobs WHERE created_at>=? AND created_at<?', bounds)
        attempted = [r for r in jobs if r['attempt'] > 0]
        states = {state: sum(r['state'] == state for r in jobs) for state in ('queued', 'running', 'blocked', 'failed', 'cancelled', 'ready')}
        processing = dict(jobs=len(jobs), attempted_jobs=len(attempted), states=states,
                          retries=sum(max(0, r['attempt']-1) for r in jobs),
                          jobs_retried=sum(r['attempt'] > 1 for r in jobs),
                          readiness=ratio(sum(r['state'] == 'ready' for r in attempted), len(attempted)))
        publication = query('''WITH ready AS (
            SELECT job_id,MIN(created_at) ready_at FROM teaching_drafts GROUP BY job_id
        ) SELECT COUNT(*) denominator, COUNT(p.job_id) numerator FROM ready r
          LEFT JOIN teaching_publications p ON p.job_id=r.job_id
          WHERE r.ready_at>=? AND r.ready_at<?''', bounds, True)
        return jsonify(version='skill-measurement-v1', window=dict(start=bounds[0], end=bounds[1], timezone='UTC', end_exclusive=True),
                       observed_at=datetime.now(timezone.utc).isoformat(), semantics='created_in_window_current_outcome',
                       placement=placement, challenges=challenges, evidence=evidence, cross_branch=multi,
                       processing=processing, publication=ratio(publication['numerator'], publication['denominator']))
