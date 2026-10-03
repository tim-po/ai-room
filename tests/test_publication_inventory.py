"""Publication planning must hold mismatched reviews/sources and disclose no keys."""
import importlib.util
import json
from pathlib import Path
import sqlite3

from test_learning import app
from test_skills import skills
from test_skill_content import install
from test_foundation_content import foundations
from club.foundation_content import CASES
from club.skill_content import candidate_form

spec = importlib.util.spec_from_file_location('inventory', Path(__file__).parents[1]/'scripts/assessment_publication_inventory.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_inventory_holds_changed_review_or_source_without_writes(skills):
    install(skills)
    assert foundations(skills).exit_code == 0
    decisions = []
    for case in CASES:
        form = candidate_form(case)
        for item in form['items']:
            decisions.append(dict(form_id='skill-foundation-form-'+case['slug']+'-v1', item_id=item['id'],
                form_sha256=module.digest(form), source=item['source'], answer=item['answer'],
                objective_id=item['objective_id'], decision='acceptable_for_narrow_taught_case_understanding'))
    with sqlite3.connect(skills.config['DATABASE']) as db:
        clean = module.inventory(db, [], decisions)
        assert len([c for c in clean['candidates'] if not c['blockers']]) == 6
        assert db.total_changes == 0
        serialized = json.dumps(clean)
        for key in ['"answer"', '"choices"', '"rationale"', '"prompt"']:
            assert key not in serialized
        decisions[0]['form_sha256'] = 'changed'
        changed = module.inventory(db, [], decisions)
        assert len([c for c in changed['candidates'] if not c['blockers']]) == 5
        db.execute('UPDATE lessons SET body=? WHERE id=?', ('changed source', clean['candidates'][-1]['lesson_id']))
        drift = module.inventory(db, [], decisions)
        assert len([c for c in drift['candidates'] if not c['blockers']]) == 4
        assert drift['counts']['skill_forms'] == 0
