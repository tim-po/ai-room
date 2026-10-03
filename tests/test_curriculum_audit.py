import sqlite3

from club.curriculum_audit import inventory
from test_learning import app
from test_skills import skills


def test_audit_counts_real_inventory_without_mutations(skills):
    with sqlite3.connect(skills.config['DATABASE']) as db:
        before = db.total_changes
        result = inventory(db)
        count = db.execute("SELECT count(*) FROM lessons l JOIN modules m ON m.id=l.module_id "
                           "JOIN courses c ON c.id=m.course_id WHERE l.status='published' "
                           "AND c.status='published'").fetchone()[0]
        assert result['coverage']['published'] == count
        assert result['coverage']['unmapped'] > 0
        assert result['duplicate_bodies']
        assert db.total_changes == before
        assert all('user_id' not in lesson for lesson in result['lessons'])
        db.execute("UPDATE courses SET status='draft'")
        assert inventory(db)['coverage'] == dict(published=0, mapped=0, unmapped=0, ratio=None)


def test_source_pin_changes_for_substance_not_title(skills):
    with sqlite3.connect(skills.config['DATABASE']) as db:
        original = inventory(db)['lessons'][0]
        identity = original['lesson_id']
        db.execute('UPDATE lessons SET title=? WHERE id=?', ('New title', identity))
        assert inventory(db)['lessons'][0]['source_sha256'] == original['source_sha256']
        db.execute('UPDATE lessons SET task=? WHERE id=?', ('Different observed result', identity))
        assert inventory(db)['lessons'][0]['source_sha256'] != original['source_sha256']
        assert inventory(db)['lessons'][0]['body_sha256'] == original['body_sha256']
