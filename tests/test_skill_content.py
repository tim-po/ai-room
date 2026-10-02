"""Local test-only review, not independent learning acceptance."""
import json
import sqlite3
from html import unescape

from club.skill_content import CASES, RELEASE, candidate_form, lesson_id
from test_learning import app, login, post
from test_skills import skills, install_form


def install(app):
    result = app.test_cli_runner().invoke(args=['install-skill-examples'])
    assert result.exit_code == 0, result.output


def review(app):
    result = app.test_cli_runner().invoke(args=['review-skill-examples', '--reviewer', 'user-admin', '--confirm-reviewed'])
    assert result.exit_code == 0, result.output


def test_content_is_mapped_readable_and_idempotent_without_automatic_review(skills):
    install(skills)
    c = skills.test_client()
    assert c.get('/api/skills/graph').json['release'] == RELEASE
    for case in CASES:
        node = c.get('/api/skills/nodes/' + case['objective']).json
        assert node['assessments'] == []
        assert node['content'][0]['id'] == lesson_id(case)
        assert node['content'][0]['source']['paragraph'] == 1
        assert 'text' not in node['content'][0]['source']
        lesson = c.get('/lessons/' + lesson_id(case))
        assert lesson.status_code == 200
        assert case['paragraphs'][0] in unescape(lesson.get_data(as_text=True))
        assert 'Все организации, числа и ситуации вымышлены' in lesson.get_data(as_text=True)
    install(skills)
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute("SELECT COUNT(*) FROM lessons WHERE id LIKE 'skill-example-%'").fetchone()[0] == 7
        assert db.execute('SELECT COUNT(*) FROM skill_releases').fetchone()[0] == 2
        assert db.execute('SELECT COUNT(*) FROM skill_forms').fetchone()[0] == 0
    refused = skills.test_cli_runner().invoke(args=['review-skill-examples', '--reviewer', 'user-admin'])
    assert refused.exit_code != 0
    refused = skills.test_cli_runner().invoke(args=['review-skill-examples', '--reviewer', 'user-learner', '--confirm-reviewed'])
    assert refused.exit_code != 0


def test_reviewed_cases_grade_distinct_source_decisions_without_watched_credit(skills):
    install(skills); review(skills); review(skills)
    c = skills.test_client(); csrf = login(c)
    for case in CASES:
        public = c.get('/api/skills/nodes/' + case['objective']).json['assessments'][0]
        assert public['item_count'] == 3
        assert 'items' not in public
        attempt = post(c, '/api/skills/challenges', {'assessment_id':public['id'], 'request_id':'case-'+case['slug']}, csrf).json
        assert attempt['mode'] == 'certification'
        assert 'rationale' not in json.dumps(attempt)
        answers = {i['id']:i['answer'] for i in candidate_form(case)['items']}
        result = post(c, '/api/skills/challenges/'+attempt['id']+'/submit', {'answers':answers}, csrf).json
        assert result['passed'] and result['credited']
        assert all(i['source']['lesson_id'] == lesson_id(case) for i in result['feedback'])
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM skill_evidence').fetchone()[0] == 7
        assert db.execute('SELECT COUNT(*) FROM progress').fetchone()[0] == 0
    me = c.get('/api/skills/me').json
    root = me['coverage'][0]
    assert root['verified'] == 7 and root['unknown'] == 19 and root['application_verified'] == 0


def test_partial_case_recommends_exact_source_and_hides_archived_content(skills):
    install(skills); review(skills)
    case = CASES[1]
    c = skills.test_client(); csrf = login(c)
    attempt = post(c, '/api/skills/challenges', {'assessment_id':'skill-example-form-mobile-v1','request_id':'partial-mobile'}, csrf).json
    answers = {i['id']: i['answer'] for i in candidate_form(case)['items']}
    answers['q2'] = '0'
    result = post(c, '/api/skills/challenges/'+attempt['id']+'/submit', {'answers':answers}, csrf).json
    assert not result['passed'] and not result['credited']
    assert result['feedback'][1]['source']['paragraph'] == 3
    assert result['feedback'][1]['source']['lesson_id'] == lesson_id(case)
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute('UPDATE lessons SET status=? WHERE id=?', ('archived', lesson_id(case)))
    assert c.get('/api/skills/nodes/'+case['objective']).json['content'] == []


def test_install_preserves_existing_progress_and_pinned_attempts_and_refuses_newer_release(skills):
    install_form(skills)
    c = skills.test_client(); csrf = login(c)
    attempt = post(c, '/api/skills/challenges', {'assessment_id':'test-form-v1','request_id':'pinned-example'}, csrf).json
    install(skills)
    case = CASES[0]
    post(c, '/api/lessons/'+lesson_id(case)+'/completion', {'completed':True}, csrf)
    post(c, '/api/lessons/'+lesson_id(case)+'/practice', {'body':'saved original work','status':'draft'}, csrf)
    install(skills)
    result = post(c, '/api/skills/challenges/'+attempt['id']+'/submit', {'answers':{'q1':'check','q2':'check'}}, csrf).json
    assert result['credited']
    assert c.get('/api/skills/me').json['coverage'][0]['verified'] == 1
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT completed FROM progress').fetchone()[0] == 1
        assert db.execute('SELECT body FROM practice').fetchone()[0] == 'saved original work'
        tree = json.loads(db.execute('SELECT body FROM skill_releases WHERE id=?',(RELEASE,)).fetchone()[0])
        tree['release'] = 'future-release'
        db.execute('INSERT INTO skill_releases(id,body) VALUES(?,?)', ('future-release',json.dumps(tree)))
        db.execute("UPDATE skill_active SET release_id='future-release'")
    refused = skills.test_cli_runner().invoke(args=['install-skill-examples'])
    assert refused.exit_code != 0 and 'refusing' in refused.output
    assert c.get('/api/skills/graph').json['release'] == 'future-release'


def test_install_collision_rolls_back_partial_content_and_graph(skills):
    # A conflicting stable ID must not result in half a curriculum being installed.
    with sqlite3.connect(skills.config['DATABASE']) as db:
        db.execute('''INSERT INTO lessons(id,module_id,title,objective,body,minutes,position,access)
            SELECT ?,module_id,title,objective,body,minutes,position,access FROM lessons LIMIT 1''',
            (lesson_id(CASES[1]),))
        before = db.execute('SELECT COUNT(*) FROM lessons').fetchone()[0]
    result = skills.test_cli_runner().invoke(args=['install-skill-examples'])
    assert result.exit_code != 0
    with sqlite3.connect(skills.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM lessons').fetchone()[0] == before
        assert db.execute("SELECT COUNT(*) FROM courses WHERE id='skill-workshop-v1'").fetchone()[0] == 0
        assert db.execute('SELECT release_id FROM skill_active').fetchone()[0] == 'tree-2026-10-v1'
        assert db.execute('SELECT COUNT(*) FROM skill_releases').fetchone()[0] == 1
