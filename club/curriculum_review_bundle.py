"""PRIVATE cumulative source/form review export; read-only and never approval."""
import argparse
import json
import sqlite3
from pathlib import Path

from .curriculum_audit import digest, inventory
from .curriculum_revisions import prepare
from .skill_content import CASES, lesson_id
from .transfer_sources import publication_candidate


def bundle(db, reviewer):
    user = db.execute('SELECT role FROM users WHERE id=?', (reviewer,)).fetchone()
    if not user or user[0] not in ('admin', 'editor'):
        raise ValueError('Editor identity required for private keyed review export')
    curriculum = prepare(db)
    transfers = []
    for case in CASES:
        slug = case['slug']
        transfers.append(publication_candidate(db, 'transfer-B-' + slug,
            'skill-transfer-form-' + slug + '-v1', lesson_id(case)))
    existing = []
    for form_id, raw in db.execute('SELECT id,body FROM skill_forms ORDER BY id'):
        body = json.loads(raw)
        existing.append(dict(id=form_id, body=body, sha256=digest(body)))
    manifest = dict(version=1, status='pending-independent-review',
        scope='Private keyed proposals only; no publication, equivalence approval or proficiency credit.',
        curriculum=curriculum, transfer_publication_candidates=transfers,
        retained_forms=existing, before_inventory=inventory(db),
        hash_definitions=dict(package_curriculum_inventory='SHA256 UTF-8 JSON: ensure_ascii=False, sort_keys=True, separators=(comma,colon)',
            transfer_forms='SHA256 UTF-8 JSON: ensure_ascii=False, sort_keys=True, default separators including spaces',
            retained_form_export='Compact JSON digest of the retained body; not a replacement for its publication hash'),
        blockers=['Independent teaching/mapping and source/item/rubric review on exact hashes',
                  'Explicit equivalence decision separate from narrow taught-case understanding',
                  'Manager scheduled integration and new preview if source, access or graph differs'])
    return dict(manifest=manifest, sha256=digest(manifest))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--reviewer', required=True)
    args = parser.parse_args()
    with sqlite3.connect(Path(args.database).resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        print(json.dumps(bundle(db, args.reviewer), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
