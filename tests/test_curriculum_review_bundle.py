import json
import sqlite3

import pytest

from club.curriculum_audit import digest
from club.curriculum_review_bundle import bundle
from club.skill_content import install_examples
from club.transfer_sources import install_sources
from club.transfer_candidates import digest as form_digest
from test_learning import app
from test_skills import skills


def test_cumulative_export_is_read_only_bound_and_role_protected(skills):
    with sqlite3.connect(skills.config['DATABASE']) as db:
        install_examples(db)
        install_sources(db, 'user-editor')
    with sqlite3.connect(skills.config['DATABASE']) as db:
        before = list(db.iterdump())
        with pytest.raises(ValueError, match='Editor'):
            bundle(db, 'user-member')
        export = bundle(db, 'user-editor')
        assert list(db.iterdump()) == before
        assert export['sha256'] == digest(export['manifest'])
        manifest = export['manifest']
        assert len(manifest['curriculum']['manifest']['revisions']) == 10
        assert len(manifest['transfer_publication_candidates']) == 7
        for candidate in manifest['transfer_publication_candidates']:
            assert candidate['sha256'] == form_digest(candidate['form'])
            assert candidate['form']['transfer_publication']['access'] == candidate['access']
            for item in candidate['form']['items']:
                assert item['source']['snapshot_url'].startswith('/api/skills/forms/skill-transfer-form-')
        # Entitlement changes must invalidate the review digest and bound form.
        target = manifest['transfer_publication_candidates'][0]['form']['transfer_publication']['lesson_id']
        db.execute("UPDATE lessons SET access='member' WHERE id=?", (target,))
        changed = bundle(db, 'user-editor')
        assert changed['sha256'] != export['sha256']
        assert changed['manifest']['transfer_publication_candidates'][0]['sha256'] != manifest['transfer_publication_candidates'][0]['sha256']
        # Original current source edits affect bundle even if retained transfer source is stable.
        previous = changed['sha256']
        db.execute("UPDATE lessons SET body='A changed current lesson' WHERE id=?", (target,))
        assert bundle(db, 'user-editor')['sha256'] != previous


def test_review_cli_cannot_mutate_database(skills):
    import subprocess
    import sys
    with sqlite3.connect(skills.config['DATABASE']) as db:
        install_examples(db)
        install_sources(db, 'user-admin')
    command = [sys.executable, '-m', 'club.curriculum_review_bundle', '--database', skills.config['DATABASE'], '--reviewer', 'user-admin']
    with sqlite3.connect(skills.config['DATABASE']) as db:
        before = list(db.iterdump())
    export = json.loads(subprocess.check_output(command, text=True))
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert export == bundle(db, 'user-admin')
        assert list(db.iterdump()) == before
