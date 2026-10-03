"""Private, read-only curriculum inventory. Coverage is not semantic approval."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(',', ':')).encode()).hexdigest()


def inventory(db):
    active = db.execute('SELECT r.body FROM skill_active a JOIN skill_releases r '
                        'ON r.id=a.release_id WHERE singleton=1').fetchone()
    if not active:
        raise ValueError('Active graph required')
    graph = json.loads(active[0])
    cursor = db.execute('''SELECT l.*, m.course_id, c.status AS course_status
        FROM lessons l JOIN modules m ON m.id=l.module_id
        JOIN courses c ON c.id=m.course_id ORDER BY l.id''')
    columns = [column[0] for column in cursor.description]
    lessons = []
    groups = {}
    for values in cursor:
        row = dict(zip(columns, values))
        source = {key: row[key] for key in
                  ('objective', 'body', 'prompt', 'task', 'checklist', 'video')}
        mappings = [m for m in graph['mappings'] if m['lesson_id'] == row['id']]
        visible = row['status'] == row['course_status'] == 'published'
        body_hash = hashlib.sha256(row['body'].encode()).hexdigest()
        groups.setdefault(body_hash, []).append(row['id'])
        lessons.append(dict(lesson_id=row['id'], course_id=row['course_id'],
            title=row['title'], status=row['status'], course_status=row['course_status'],
            access=row['access'], published=visible, source=source,
            source_sha256=digest(source), body_sha256=body_hash, mappings=mappings,
            review_status='mapping_requires_semantic_review' if mappings else 'unmapped'))
    published = [lesson for lesson in lessons if lesson['published']]
    mapped = sum(bool(lesson['mappings']) for lesson in published)
    return dict(schema_version=1, graph_release=graph['release'], graph_sha256=digest(graph),
        definitions={'denominator': 'Lessons and parent courses both published; includes unmapped fixtures.',
                     'mapped': 'At least one active graph mapping; not a verdict on teaching sufficiency.',
                     'source_sha256': 'Exact objective/body/prompt/task/checklist/video; title excluded.',
                     'duplicate_body': 'Exact same body bytes; not proof of equivalent outcomes.'},
        coverage=dict(published=len(published), mapped=mapped, unmapped=len(published)-mapped,
                      ratio=mapped/len(published) if published else None),
        duplicate_bodies=[dict(body_sha256=key, lesson_ids=ids)
                          for key, ids in sorted(groups.items()) if len(ids) > 1], lessons=lessons)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    args = parser.parse_args()
    # URI encoding protects paths containing '?' or '#'; mode=ro cannot create a DB.
    with sqlite3.connect(Path(args.database).resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')  # One consistent graph/content snapshot during concurrent edits.
        result = inventory(db)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
