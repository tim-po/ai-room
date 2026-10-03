"""Exact-hash reviewed revisions of existing teaching rows, preserving learner state."""
import argparse
import copy
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .curriculum_audit import digest
from .release_bindings import carry_forms

CASES = json.loads(Path(__file__).with_name('curriculum_revision_cases.json').read_text())
FIELDS = ('objective', 'body', 'prompt', 'task', 'checklist')


def prepare(db):
    active = db.execute('SELECT r.body FROM skill_active a JOIN skill_releases r ON r.id=a.release_id').fetchone()
    if not active:
        raise ValueError('Active skill graph required')
    graph = json.loads(active[0])
    revisions = []
    for case in CASES:
        cursor = db.execute('SELECT * FROM lessons WHERE id=?', (case['lesson_id'],))
        row = cursor.fetchone()
        if not row:
            raise ValueError('Existing lesson required: ' + case['lesson_id'])
        before = dict(zip([c[0] for c in cursor.description], row))
        parent = db.execute('''SELECT m.course_id,c.status FROM modules m
            JOIN courses c ON c.id=m.course_id WHERE m.id=?''', (before['module_id'],)).fetchone()
        if not parent:
            raise ValueError('Existing parent course required: ' + case['lesson_id'])
        # Learner visibility depends on the course as well as the lesson. Moving
        # a module or archiving its course must invalidate an uninstalled review.
        context = dict(module_id=before['module_id'], course_id=parent[0], course_status=parent[1])
        if any(m['lesson_id'] == before['id'] for m in graph['mappings']):
            raise ValueError('Existing mapping requires separate source reconciliation')
        if not any(n['id'] == case['objective_id'] for n in graph['nodes']):
            raise ValueError('Objective absent from current graph')
        after = dict(before, **{key: case[key] for key in FIELDS})
        # The old video is a fixture for a different teaching edition. Retain it
        # in the historical row, but present this new edition honestly as text.
        after['video'] = ''
        revisions.append(dict(lesson_id=before['id'], before=before, after=after,
                              before_sha256=digest(before), after_sha256=digest(after),
                              objective_id=case['objective_id'], mapping_scope=case['mapping_scope'],
                              publication_context=context))
    manifest = dict(version=2, base_release=graph['release'], graph_sha256=digest(graph),
                    revisions=revisions, scope='Teaching only; no assessments or proficiency credit')
    return dict(manifest=manifest, sha256=digest(manifest))


def install(db, *, reviewer, reviewed_sha256, confirm_reviewed=False):
    """Atomic exact-review application. Caller owns backup and outer transaction."""
    user = db.execute('SELECT role FROM users WHERE id=?', (reviewer,)).fetchone()
    if not user or user[0] not in ('admin', 'editor'):
        raise ValueError('Editor identity required')
    if confirm_reviewed is not True:
        raise ValueError('Explicit source and objective-mapping review required')
    existing = db.execute('SELECT body FROM skill_curriculum_revisions WHERE id=?', (reviewed_sha256,)).fetchone()
    if existing:
        # Replay never overwrites later editorial changes or restores a release.
        return False
    proposed = prepare(db)
    if proposed['sha256'] != reviewed_sha256:
        raise ValueError('Reviewed source or graph changed; fresh exact-hash review required')
    manifest = proposed['manifest']
    graph = json.loads(db.execute('SELECT body FROM skill_releases WHERE id=?', (manifest['base_release'],)).fetchone()[0])
    tree = copy.deepcopy(graph)
    tree['release'] = 'curriculum-' + reviewed_sha256
    for revision in manifest['revisions']:
        tree['mappings'].append(dict(lesson_id=revision['lesson_id'], objective_id=revision['objective_id'],
            role='teaches', source=dict(kind='retained-curriculum-edition', revision_id=reviewed_sha256,
                                      edition=2, sha256=revision['after_sha256'])))
    def query(sql, params=(), one=False):
        cursor = db.execute(sql, params)
        return cursor.fetchone() if one else cursor.fetchall()
    db.execute('SAVEPOINT curriculum_install')
    try:
        db.execute('INSERT INTO skill_curriculum_revisions(id,body,reviewed_by) VALUES(?,?,?)',
                   (reviewed_sha256, json.dumps(manifest, ensure_ascii=False, sort_keys=True), reviewer))
        for revision in manifest['revisions']:
            after = revision['after']
            db.execute('UPDATE lessons SET objective=?,body=?,prompt=?,task=?,checklist=?,video=? WHERE id=?',
                       tuple(after[key] for key in (*FIELDS, 'video')) + (after['id'],))
        db.execute('INSERT INTO skill_releases(id,body) VALUES(?,?)',
                   (tree['release'], json.dumps(tree, ensure_ascii=False)))
        carry_forms(db, query, graph['release'], tree, reviewer)
        db.execute('UPDATE skill_active SET release_id=? WHERE singleton=1', (tree['release'],))
        db.execute('RELEASE curriculum_install')
    except Exception:
        db.execute('ROLLBACK TO curriculum_install')
        db.execute('RELEASE curriculum_install')
        raise
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--reviewer')
    parser.add_argument('--reviewed-sha256')
    args = parser.parse_args()
    path = Path(args.database).resolve()
    apply = bool(args.reviewed_sha256)
    with sqlite3.connect(path.as_uri() + ('?mode=rw' if apply else '?mode=ro'), uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        if not apply:
            db.execute('BEGIN')
            print(json.dumps(prepare(db), ensure_ascii=False, indent=2))
            return
        if not args.reviewer:
            parser.error('--reviewer required for installation')
        backup = path.with_name(path.name + '.before-curriculum-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f'))
        # Restrict permissions before copying private learner state.
        backup.touch(mode=0o600, exist_ok=False)
        with sqlite3.connect(backup) as destination:
            db.backup(destination)
        db.execute('BEGIN IMMEDIATE')
        changed = install(db, reviewer=args.reviewer, reviewed_sha256=args.reviewed_sha256, confirm_reviewed=True)
        print(json.dumps(dict(installed=changed, backup=str(backup))))


if __name__ == '__main__':
    main()
