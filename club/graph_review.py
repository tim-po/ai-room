"""Explicit editorial activation of immutable graph editions; never rewrites evidence."""
import json
import re
import uuid
from flask import abort, g, jsonify
from .release_bindings import carry_forms, availability_impact


def validate_graph(candidate, baseline):
    if not isinstance(candidate, dict) or set(candidate) != set(baseline):
        raise ValueError('Graph fields must match the base edition')
    if candidate['root'] != baseline['root'] or candidate['score_rule'] != baseline['score_rule']:
        raise ValueError('Root and score rules cannot change in structural review')
    if candidate['mappings'] != baseline['mappings']:
        raise ValueError('Content mappings belong to the source publication workflow')
    nodes = candidate['nodes']
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 1000:
        raise ValueError('Expected 1–1000 nodes')
    indexed = {}
    for node in nodes:
        if not isinstance(node, dict) or set(node) != {'id', 'title', 'kind', 'revision'}:
            raise ValueError('Invalid node fields')
        if not isinstance(node['id'], str) or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,127}', node['id']) or node['id'] in indexed:
            raise ValueError('Invalid or duplicate node identity')
        if not isinstance(node['title'], str) or not 1 <= len(node['title'].strip()) <= 200:
            raise ValueError('A bounded node title is required')
        if node['kind'] not in ('root', 'branch', 'category', 'ability') or type(node['revision']) is not int or node['revision'] != 1:
            raise ValueError('Invalid kind or revision; changed abilities require new IDs')
        indexed[node['id']] = node
    if [n['id'] for n in nodes if n['kind'] == 'root'] != [baseline['root']]:
        raise ValueError('Exactly one shared root is required')
    for old in baseline['nodes']:
        new = indexed.get(old['id'])
        if not new or new['kind'] != old['kind'] or new['revision'] != old['revision']:
            raise ValueError('Existing node identities and revisions must be retained')
        if old['kind'] == 'ability' and new != old:
            raise ValueError('Existing ability semantics are immutable; use a new ID')
    edges = candidate['edges']
    if not isinstance(edges, list) or len(edges) > 4000:
        raise ValueError('Too many edges')
    seen, parents = set(), {}
    adjacency = {kind: {id: [] for id in indexed} for kind in ('contains', 'prerequisite')}
    for edge in edges:
        if not isinstance(edge, dict) or not {'source','target','type','advisory'} <= set(edge) or set(edge) - {'source','target','type','advisory','rationale'}:
            raise ValueError('Invalid edge fields')
        source, target, kind = edge['source'], edge['target'], edge['type']
        if not all(isinstance(v, str) for v in (source, target, kind)) or source not in indexed or target not in indexed or source == target or kind not in ('contains','prerequisite','related'):
            raise ValueError('Invalid edge endpoints or type')
        if edge['advisory'] is not True:
            raise ValueError('Structural review cannot introduce access gates')
        if 'rationale' in edge and (not isinstance(edge['rationale'], str) or len(edge['rationale']) > 1500):
            raise ValueError('Invalid rationale')
        key = (source, target, kind)
        if key in seen:
            raise ValueError('Duplicate edge')
        seen.add(key)
        if kind in adjacency:
            adjacency[kind][source].append(target)
        if kind == 'contains':
            if target in parents or target == baseline['root'] or indexed[source]['kind'] == 'ability':
                raise ValueError('Containment requires one parent and no ability containers')
            parents[target] = source
    if set(parents) != set(indexed) - {baseline['root']}:
        raise ValueError('Every node must belong to the shared tree')
    for links in adjacency.values():
        indegree = {id: 0 for id in indexed}
        for targets in links.values():
            for target in targets:
                indegree[target] += 1
        pending = [id for id, degree in indegree.items() if degree == 0]
        count = 0
        while pending:
            node = pending.pop(); count += 1
            for target in links[node]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    pending.append(target)
        if count != len(indexed):
            raise ValueError('Containment and prerequisites must be acyclic')
    for node in nodes:
        if node['kind'] == 'branch' and parents[node['id']] != baseline['root']:
            raise ValueError('Major branches must stay under the shared root')
    return candidate


def graph_diff(before, after):
    old = {n['id']: n for n in before['nodes']}; new = {n['id']: n for n in after['nodes']}
    added = [n for id, n in new.items() if id not in old]
    changed = [dict(id=id, before=old[id], after=n) for id, n in new.items() if id in old and old[id] != n]
    removed_edges = [e for e in before['edges'] if e not in after['edges']]
    added_edges = [e for e in after['edges'] if e not in before['edges']]
    affected = {n['id'] for n in added} | {n['id'] for n in changed}
    affected.update(e[k] for e in removed_edges + added_edges for k in ('source','target'))
    # Include descendants whose displayed ancestry/readiness can change.
    while True:
        expanded = affected | {e['target'] for e in before['edges'] + after['edges'] if e['source'] in affected and e['type'] in ('contains','prerequisite')}
        if expanded == affected:
            break
        affected = expanded
    return dict(added_nodes=added, changed_nodes=changed, added_edges=added_edges, removed_edges=removed_edges,
                affected_nodes=sorted(affected), affected_lessons=sorted({m['lesson_id'] for m in before['mappings'] if m['objective_id'] in affected}),
                evidence_policy='Historical attempts and evidence remain unchanged; new abilities start unknown.')


def register_graph_review(app, db, query, require_user, graph, data):
    def editor():
        if g.user['role'] not in ('editor', 'admin'):
            abort(403)

    def release(id):
        row = query('SELECT body FROM skill_releases WHERE id=?', (id,), one=True)
        if not row:
            abort(404)
        return json.loads(row['body'])

    def proposal(id):
        row = query('SELECT * FROM skill_graph_proposals WHERE id=?', (id,), one=True)
        if not row or (g.user['role'] != 'admin' and row['created_by'] != g.user['id']):
            abort(404)
        return row

    def dto(row):
        value = dict(row)
        edition = query('SELECT body,note FROM skill_graph_editions WHERE proposal_id=? AND revision=?', (row['id'],row['revision']), one=True)
        value.update(graph=json.loads(edition['body']), note=edition['note'], source=json.loads(row['source']))
        value['diff'] = graph_diff(release(row['base_release']), value['graph'])
        value['diff']['availability'] = availability_impact(query, row['base_release'], value['graph'])
        value['rollback_availability'] = availability_impact(query, row['id'], release(row['base_release'])) if row['state'] == 'active' else None
        value['stale'] = graph()['release'] != row['base_release']
        value['editions'] = [dict(e) for e in query('SELECT revision,note,editor_id FROM skill_graph_editions WHERE proposal_id=? ORDER BY revision', (row['id'],))]
        return value

    def note(value):
        result = value.get('note')
        if not isinstance(result, str) or not 5 <= len(result.strip()) <= 2000:
            abort(400, 'Editorial explanation required (5–2000 characters)')
        return result

    def check(candidate, base):
        try:
            validate_graph(candidate, base)
            # IDs cannot be repurposed after rollback either.
            known = {n['id']: n for n in candidate['nodes']}
            for row in query('SELECT body FROM skill_releases'):
                for node in json.loads(row['body'])['nodes']:
                    if node['id'] in known:
                        current = known[node['id']]
                        if current['kind'] != node['kind'] or current['revision'] != node['revision'] or (node['kind'] == 'ability' and current != node):
                            raise ValueError('Historical node identity cannot be repurposed')
        except (ValueError, TypeError, KeyError) as exc:
            abort(400, str(exc))

    @app.get('/api/skills/graph-proposals')
    @require_user
    def list_proposals():
        editor()
        return jsonify(proposals=[dto(row) for row in query('SELECT * FROM skill_graph_proposals ORDER BY created_at DESC,id') if g.user['role'] == 'admin' or row['created_by'] == g.user['id']])

    @app.post('/api/skills/graph-proposals')
    @require_user
    def create_proposal():
        editor(); value = data(); explanation = note(value)
        with db():
            db().execute('BEGIN IMMEDIATE')
            base = graph()
            if value.get('base_release') != base['release']:
                abort(409, 'Active graph changed; review against the current edition')
            source = {}
            if value.get('job_id'):
                if not isinstance(value['job_id'], str) or type(value.get('draft_revision')) is not int:
                    abort(400)
                owner = query('SELECT u.owner_id FROM teaching_jobs j JOIN teaching_uploads u ON u.id=j.upload_id WHERE j.id=?', (value['job_id'],), one=True)
                if not owner or (g.user['role'] != 'admin' and owner['owner_id'] != g.user['id']):
                    abort(404)
                row = query('SELECT * FROM teaching_drafts WHERE job_id=? AND revision=?', (value['job_id'],value.get('draft_revision')), one=True)
                if not row:
                    abort(404)
                source = dict(job_id=row['job_id'], draft_revision=row['revision'], release_id=row['release_id'],
                              proposals=json.loads(row['body'])['skill_proposals'], sources=json.loads(row['sources']))
            id = 'graph-proposal-' + uuid.uuid4().hex
            candidate = value.get('graph', base.copy())
            if not isinstance(candidate, dict):
                abort(400)
            candidate['release'] = id
            check(candidate, base)
            db().execute('INSERT INTO skill_graph_proposals(id,base_release,source,created_by) VALUES(?,?,?,?)', (id,base['release'],json.dumps(source),g.user['id']))
            db().execute('INSERT INTO skill_graph_editions VALUES(?,?,?,?,?)', (id,1,json.dumps(candidate,ensure_ascii=False),explanation,g.user['id']))
        return jsonify(dto(proposal(id))), 201

    @app.get('/api/skills/graph-proposals/<id>')
    @require_user
    def get_proposal(id):
        editor()
        return jsonify(dto(proposal(id)))

    @app.put('/api/skills/graph-proposals/<id>')
    @require_user
    def edit_proposal(id):
        editor(); value = data(); explanation = note(value)
        with db():
            db().execute('BEGIN IMMEDIATE')
            row = proposal(id)
            if row['state'] != 'draft' or type(value.get('revision')) is not int or value['revision'] != row['revision']:
                abort(409)
            candidate = value.get('graph')
            if not isinstance(candidate, dict):
                abort(400)
            candidate['release'] = id
            check(candidate, release(row['base_release']))
            db().execute('INSERT INTO skill_graph_editions VALUES(?,?,?,?,?)', (id,row['revision']+1,json.dumps(candidate,ensure_ascii=False),explanation,g.user['id']))
            db().execute('UPDATE skill_graph_proposals SET revision=revision+1 WHERE id=?', (id,))
        return jsonify(dto(proposal(id)))

    @app.post('/api/skills/graph-proposals/<id>/<action>')
    @require_user
    def decide(id, action):
        editor(); value = data(); explanation = note(value)
        if action not in ('activate','reject','rollback'):
            abort(404)
        with db():
            db().execute('BEGIN IMMEDIATE')
            row = proposal(id)
            if type(value.get('revision')) is not int or value['revision'] != row['revision']:
                abort(409)
            active = graph()['release']
            expected_state = 'active' if action == 'rollback' else 'draft'
            if row['state'] != expected_state:
                abort(409)
            candidate = dto(row)['graph']
            if action == 'activate':
                if active != row['base_release']:
                    abort(409, 'Active graph changed; create a fresh proposal')
                if value.get('confirm_reviewed') is not True:
                    abort(400, 'Explicit structural and semantic review required')
                check(candidate, release(active))
                if candidate['nodes'] == release(active)['nodes'] and candidate['edges'] == release(active)['edges']:
                    abort(400, 'No structural changes to activate')
                db().execute('INSERT INTO skill_releases(id,body) VALUES(?,?)', (id,json.dumps(candidate,ensure_ascii=False)))
                carry_forms(db(), query, active, candidate, g.user['id'])
                db().execute('UPDATE skill_active SET release_id=? WHERE singleton=1', (id,))
            elif action == 'rollback':
                if active != id:
                    abort(409, 'A later edition is active; review its changes first')
                carry_forms(db(), query, active, release(row['base_release']), g.user['id'])
                db().execute('UPDATE skill_active SET release_id=? WHERE singleton=1', (row['base_release'],))
            state = {'activate':'active','reject':'rejected','rollback':'rolled_back'}[action]
            db().execute('UPDATE skill_graph_proposals SET state=? WHERE id=?', (state,id))
            db().execute('INSERT INTO skill_graph_events(proposal_id,revision,action,actor_id,note,from_release,to_release) VALUES(?,?,?,?,?,?,?)',
                         (id,row['revision'],action,g.user['id'],explanation,active,graph()['release']))
        return jsonify(dto(proposal(id)))

    @app.get('/api/skills/graph-history')
    @require_user
    def history():
        editor()
        return jsonify(active_release=graph()['release'], events=[dict(row) for row in query('SELECT e.* FROM skill_graph_events e JOIN skill_graph_proposals p ON p.id=e.proposal_id WHERE ? OR p.created_by=? ORDER BY e.id', (g.user['role'] == 'admin',g.user['id']))])
