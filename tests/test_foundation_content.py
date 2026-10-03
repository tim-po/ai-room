"""Installation/provenance checks, not editorial equivalence acceptance."""
import hashlib
import json
import sqlite3

from club.foundation_content import CASES, release_id
from club.skill_content import RELEASE, lesson_id, candidate_form
from club.skills import form_exposure_keys
from test_learning import app, login, post
from test_skills import skills
from test_skill_content import install, review


def foundations(app, parent=RELEASE, reviewer='user-admin'):
    return app.test_cli_runner().invoke(args=['install-skill-foundations', '--from-release', parent, '--reviewer', reviewer])


def test_additive_sources_carry_existing_inventory_and_preserve_history(skills):
    install(skills); review(skills)
    c = skills.test_client(); token = login(c)
    attempt = post(c, '/api/skills/challenges', dict(assessment_id='skill-example-form-verification-v1', request_id='foundation-before'), token).json
    from club.skill_content import CASES as originals
    answers = {i['id']:i['answer'] for i in candidate_form(originals[0])['items']}
    result = post(c, '/api/skills/challenges/'+attempt['id']+'/submit', dict(answers=answers), token).json
    assert result['credited']
    post(c, '/api/lessons/'+lesson_id(originals[0])+'/completion', dict(completed=True), token)
    post(c, '/api/lessons/'+lesson_id(originals[0])+'/practice', dict(body='Retain my work',status='draft'), token)
    assert foundations(skills, reviewer='user-learner').exit_code != 0
    assert foundations(skills).exit_code == 0
    assert foundations(skills).exit_code == 0
    assert c.get('/api/skills/graph').json['release'] == release_id(RELEASE)
    assert c.get('/api/skills/challenges/'+attempt['id']).json['result'] == result
    repeat = post(c, '/api/skills/challenges', dict(assessment_id='skill-example-form-verification-v1',request_id='foundation-after'), token).json
    assert repeat['mode'] == 'practice'
    for case in CASES:
        node = c.get('/api/skills/nodes/'+case['objective']).json
        assert len(node['content']) == 2
        assert node['assessments'] == []
        assert c.get('/lessons/'+lesson_id(case)).status_code == 200
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM skill_forms').fetchone()[0] == 7
        assert db.execute('SELECT COUNT(*) FROM skill_form_bindings').fetchone()[0] == 7
        assert db.execute('SELECT COUNT(*) FROM skill_evidence').fetchone()[0] == 1
        assert db.execute('SELECT completed FROM progress').fetchone()[0] == 1
        assert db.execute('SELECT body FROM practice').fetchone()[0] == 'Retain my work'
    assert c.get('/api/skills/me').json['coverage'][0]['unknown'] == 25


def test_private_candidates_pin_persisted_sources_and_distinct_lineage(skills):
    install(skills)
    assert foundations(skills).exit_code == 0
    preview = skills.test_cli_runner().invoke(args=['inspect-skill-foundations'])
    assert preview.exit_code == 0, preview.output
    candidates = json.loads(preview.output)
    assert len(candidates) == 6
    seen = set()
    for case, candidate in zip(CASES, candidates):
        assert candidate['status'] == 'private-candidate-not-approved'
        assert candidate['thresholds']['overall'] == 3
        assert candidate['thresholds']['objectives'] == {case['objective']:3}
        keys = form_exposure_keys(candidate['form'])
        assert not seen & keys
        seen |= keys
        for item in candidate['form']['items']:
            ref = item['source']
            paragraph = case['paragraphs'][ref['paragraph']-1]
            assert ref['lesson_id'] == lesson_id(case) and ref['edition'] == 1
            assert ref['text'] == paragraph
            assert ref['sha256'] == hashlib.sha256(paragraph.encode()).hexdigest()
            with sqlite3.connect(skills.config['DATABASE']) as db:
                assert paragraph in db.execute('SELECT body FROM lessons WHERE id=?',(ref['lesson_id'],)).fetchone()[0]
    c = skills.test_client()
    assert c.get('/static/foundation_candidates.json').status_code == 404
    public_graph = json.dumps(c.get('/api/skills/graph').json, ensure_ascii=False)
    for candidate in candidates:
        for item in candidate['form']['items']:
            assert item['rationale'] not in public_graph
            assert item['prompt'] not in public_graph
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute('UPDATE lessons SET body=? WHERE id=?', ('changed source',lesson_id(CASES[0])))
    assert skills.test_cli_runner().invoke(args=['inspect-skill-foundations']).exit_code != 0


def test_stale_rebase_and_colliding_content_fail_without_partial_install(skills):
    install(skills)
    assert foundations(skills, parent='tree-2026-10-v1').exit_code != 0
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute('''INSERT INTO lessons(id,module_id,title,objective,body,minutes,position,access)
                      SELECT ?,module_id,title,objective,body,minutes,position,access FROM lessons LIMIT 1''', (lesson_id(CASES[2]),))
        count = db.execute('SELECT COUNT(*) FROM lessons').fetchone()[0]
    assert foundations(skills).exit_code != 0
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM lessons').fetchone()[0] == count
        assert db.execute('SELECT release_id FROM skill_active').fetchone()[0] == RELEASE
        assert db.execute("SELECT COUNT(*) FROM courses WHERE id='skill-foundations-v1'").fetchone()[0] == 0
