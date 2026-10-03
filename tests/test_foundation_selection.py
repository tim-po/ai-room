"""Hash drift must roll back the entire selected batch, including under -O."""
import copy
import importlib.util
from pathlib import Path
import sqlite3
import sys
import pytest
from test_learning import app
from test_skills import skills
from test_skill_content import install
from test_foundation_content import foundations
from test_publication_inventory import module as inventory
from club.foundation_content import CASES
from club.skill_content import candidate_form

sys.path.insert(0, str(Path(__file__).parents[1]/'scripts'))
from publish_foundation_selection import publish


def test_atomic_selection_and_drift(skills):
    install(skills)
    assert foundations(skills).exit_code == 0
    reviews=[]
    for case in CASES:
        form=candidate_form(case)
        for item in form['items']:
            reviews.append(dict(form_id='skill-foundation-form-'+case['slug']+'-v1', item_id=item['id'],
                form_sha256=inventory.digest(form), source=item['source'], answer=item['answer'],
                objective_id=item['objective_id'], decision='acceptable_for_narrow_taught_case_understanding'))
    with sqlite3.connect(skills.config['DATABASE']) as db:
        report=inventory.inventory(db, [], reviews)
    decision=dict(active_release=report['active_release'], candidates=[c for c in report['candidates'] if c['suggested_initial_selection']])
    for mutation in ('hash', 'source', 'release', 'selection', 'reviewer'):
        altered=copy.deepcopy(decision)
        if mutation=='hash': altered['candidates'][-1]['form_sha256']='drift'
        if mutation=='source': altered['candidates'][-1]['source_body_sha256']='drift'
        if mutation=='release': altered['active_release']='drift'
        if mutation=='selection': altered['candidates'].pop()
        with pytest.raises(ValueError), sqlite3.connect(skills.config['DATABASE']) as db:
            db.execute('BEGIN IMMEDIATE')
            publish(db, altered, 'learner@example.test' if mutation=='reviewer' else 'editor@example.test')
        with sqlite3.connect(skills.config['DATABASE']) as db:
            assert db.execute('SELECT COUNT(*) FROM skill_forms').fetchone()[0]==0
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute('BEGIN IMMEDIATE')
        assert len(publish(db,decision,'editor@example.test')['published'])==3
    with pytest.raises(ValueError), sqlite3.connect(skills.config['DATABASE']) as db:
        publish(db,decision,'editor@example.test')
