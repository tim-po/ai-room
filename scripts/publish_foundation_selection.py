"""Publish an explicitly selected, source-pinned foundation decision atomically.

Run on copied state first. The caller owns staging scheduling and backup location.
No schema initialization, source mutation, or application deployment is performed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys


def publish(db, decision, reviewer_email):
    from club.foundation_content import installed_candidates
    from club.skills import publish_reviewed_form
    from assessment_publication_inventory import digest
    db.row_factory = sqlite3.Row
    graph = json.loads(db.execute('SELECT r.body FROM skill_releases r JOIN skill_active a ON a.release_id=r.id').fetchone()[0])
    if graph['release'] != decision['active_release']:
        raise ValueError('Active release drift')
    reviewer = db.execute('SELECT id,role FROM users WHERE email=?', (reviewer_email,)).fetchone()
    if not reviewer or reviewer['role'] not in ('editor', 'admin'):
        raise ValueError('Named editor required')
    selected = decision['candidates']
    expected = {'skill-foundation-form-foundations-'+topic+'-a-v1' for topic in ('limitations', 'context', 'safety')}
    if len(selected) != 3 or {c['id'] for c in selected} != expected:
        raise ValueError('Only the three authorized A forms may be selected')
    candidates = {c['id']: c for c in installed_candidates(db)}
    # Validate the entire batch before inserting any form.
    for entry in selected:
        candidate = candidates[entry['id']]
        row = db.execute('''SELECT l.body,l.access,l.status,c.id,c.status FROM lessons l
            JOIN modules m ON m.id=l.module_id JOIN courses c ON c.id=m.course_id WHERE l.id=?''', (entry['lesson_id'],)).fetchone()
        if not row or tuple(row)[1:] != (entry['proposed_access'], 'published', entry['course_id'], 'published'):
            raise ValueError('Source access/publication drift')
        if hashlib.sha256(row[0].encode()).hexdigest() != entry['source_body_sha256']:
            raise ValueError('Source body drift')
        if digest(candidate['form']) != entry['form_sha256'] or candidate['node_id'] != entry['node_id'] or candidate['thresholds'] != entry['thresholds']:
            raise ValueError('Reviewed form drift')
        if db.execute('SELECT 1 FROM skill_forms WHERE id=?', (entry['id'],)).fetchone():
            raise ValueError('Selection already published; inspect ledger before retry')
    for entry in selected:
        publish_reviewed_form(db, id=entry['id'], graph=graph, node_id=entry['node_id'],
            form=candidates[entry['id']]['form'], access=entry['proposed_access'], reviewer=reviewer['id'])
    return dict(active_release=graph['release'], reviewer=reviewer_email,
                published=[dict(id=e['id'], form_sha256=e['form_sha256'], source_body_sha256=e['source_body_sha256']) for e in selected],
                applied_credit=False, retake_equivalence='not_approved')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'database', 'decision', 'backup', 'output', 'reviewer-email'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(args.source_root).resolve()))
    decision = json.loads(Path(args.decision).read_text())
    os.umask(0o077)
    backup = Path(args.backup)
    with backup.open('xb'):
        pass
    with sqlite3.connect(Path(args.database).resolve().as_uri()+'?mode=rw', uri=True, timeout=15) as db:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('BEGIN IMMEDIATE')
        # A separate reader copies the committed snapshot while this writer lock
        # prevents every other writer from changing it before publication.
        with sqlite3.connect(Path(args.database).resolve().as_uri()+'?mode=ro', uri=True) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        result = publish(db, decision, args.reviewer_email)
    result.update(staged_commit=decision['staged_commit'], backup=str(backup),
                  decision_sha256=hashlib.sha256(Path(args.decision).read_bytes()).hexdigest())
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(published=len(result['published']), active_release=result['active_release'])))


if __name__ == '__main__':
    main()
