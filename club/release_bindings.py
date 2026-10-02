"""Explicit release compatibility; forms, rubrics and exposure identities stay pinned."""
import json


def available_forms(query, release_id):
    return query('''SELECT f.* FROM skill_forms f WHERE f.release_id=? OR EXISTS
                    (SELECT 1 FROM skill_form_bindings b WHERE b.form_id=f.id AND b.release_id=?)
                    ORDER BY f.id''', (release_id, release_id))


def form_available(query, form, release_id):
    return form['release_id'] == release_id or bool(query(
        'SELECT 1 FROM skill_form_bindings WHERE form_id=? AND release_id=?',
        (form['id'], release_id), True))


def compatible(query, form, target):
    source = json.loads(query('SELECT body FROM skill_releases WHERE id=?', (form['release_id'],), True)['body'])
    old = {n['id']: n for n in source['nodes']}
    new = {n['id']: n for n in target['nodes']}
    objectives = json.loads(form['body'])['thresholds']['objectives']
    # Structural category names/ancestry may change. Ability semantics and score
    # rules may not. Immutable form body retains source, rubric, access and lineage.
    return (source['score_rule'] == target['score_rule'] and form['node_id'] in new
            and all(old.get(o) == new.get(o) and o in new for o in objectives))


def carry_forms(db, query, source_id, target, reviewer):
    for form in available_forms(query, source_id):
        if form['release_id'] != target['release'] and compatible(query, form, target):
            db.execute('''INSERT OR IGNORE INTO skill_form_bindings
                          (release_id,form_id,from_release,reviewed_by) VALUES(?,?,?,?)''',
                       (target['release'], form['id'], source_id, reviewer))
    # Withdrawn bindings may be retained for audit, but every consumer still
    # enforces lifecycle (including inherited withdrawal) independently.


def availability_impact(query, source_id, target):
    from .form_lifecycle import lifecycle
    source = {f['id']: f for f in available_forms(query, source_id)}
    existing = {f['id']: f for f in available_forms(query, target['release'])}
    retained = {id: f for id, f in source.items() if compatible(query, f, target)}
    after = existing | retained
    active = lambda forms: {id for id in forms if lifecycle(query, id)['status'] == 'active'}
    before_ids, after_ids = active(source), active(after)
    tasks = query('SELECT id,form_id FROM skill_practical_tasks ORDER BY id')
    before_tasks = {t['id'] for t in tasks if t['form_id'] in before_ids}
    after_tasks = {t['id'] for t in tasks if t['form_id'] in after_ids}
    def diff(before, after):
        return dict(unchanged=sorted(before & after), added=sorted(after-before), removed=sorted(before-after))
    return dict(assessments=diff(before_ids, after_ids), practical_tasks=diff(before_tasks, after_tasks),
                withdrawn_assessments=sorted(set(source | after) - active(source | after)),
                policy='Original IDs, sources, access, rubrics, exposure and evidence are retained; withdrawal remains enforced.')
