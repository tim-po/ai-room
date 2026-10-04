"""Real HTTP regressions for retained source authorization; synthetic content only."""
import json
import re
import sqlite3
from threading import Thread
from urllib.request import build_opener, HTTPCookieProcessor, Request
from urllib.error import HTTPError
from urllib.parse import urlencode

import pytest
from werkzeug.serving import make_server
from club.skills import publish_reviewed_form
from club.skill_seed import graph_fixture
from test_learning import app, FREE, PASSWORD
from test_skills import skills, fixture_form

MARKER = 'PROTECTED-SYNTHETIC-SOURCE'


class Client:
    def __init__(self, base, who):
        self.base = base
        self.http = build_opener(HTTPCookieProcessor())
        page = self.http.open(base + '/login').read().decode()
        self.csrf = re.search(r'name="csrf" value="([^"]+)"', page)[1]
        with self.http.open(base + '/login', urlencode(dict(email=who+'@example.test', password=PASSWORD, csrf=self.csrf)).encode()) as response:
            page = response.read().decode()
        self.csrf = re.search(r'name="csrf-token" content="([^"]+)"', page)[1]

    def call(self, path, value=None, method=None):
        req = Request(self.base + path, data=json.dumps(value).encode() if value is not None else None,
                      headers={'Content-Type': 'application/json', 'X-CSRF-Token': self.csrf}, method=method)
        try:
            response = self.http.open(req)
        except HTTPError as exc:
            response = exc
        with response:
            body = response.read().decode()
            return response.status, json.loads(body) if response.headers.get_content_type() == 'application/json' else body


@pytest.mark.parametrize('change', ['paid', 'revoked', 'lesson_withdrawn', 'course_withdrawn'])
def test_current_binding_fences_history_tasks_and_work_over_http(skills, change):
    with sqlite3.connect(skills.config['DATABASE']) as db:
        reviewer = db.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
        form = fixture_form()
        form['transfer_publication'] = dict(lesson_id=FREE, form_id='bound-test')
        for item in form['items']:
            item['source']['text'] = MARKER
        publish_reviewed_form(db, id='bound-test', graph=graph_fixture(), node_id='basic-ai.verification', form=form, access='free', reviewer=reviewer)
        if change == 'revoked':
            db.execute("UPDATE lessons SET access='member' WHERE id=?", (FREE,))
    server = make_server('127.0.0.1', 0, skills)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        base = 'http://127.0.0.1:' + str(server.server_port)
        learner = Client(base, 'member' if change == 'revoked' else 'learner')
        admin = Client(base, 'admin')
        other = Client(base, 'revoked')
        code, task = admin.call('/api/skills/practical-tasks', dict(assessment_id='bound-test', objective_id='basic-ai.verification', instructions='Synthetic task: compare the claim against the provided source.', criteria=[dict(id='a', text='Record the source used.'), dict(id='b', text='Explain the comparison.')], confirm_reviewed=True))
        assert code == 201
        task_path = '/api/skills/practical-tasks/' + task['id']
        create = dict(task_id=task['id'], request_id='bound-submission')
        code, submission = learner.call('/api/skills/practical-submissions', create)
        assert code == 201
        sub_path = '/api/skills/practical-submissions/' + submission['id']
        work = dict(revision=1, body=MARKER + '-work', status='draft')
        assert learner.call(sub_path, work, 'PUT')[0] == 200
        _, diagnostic = learner.call('/api/skills/diagnostics', dict(request_id='bound-diagnostic', interests=[]))
        diag_path = '/api/skills/diagnostics/' + diagnostic['id']
        _, pending = learner.call('/api/skills/diagnostics', dict(request_id='pending-diagnostic', interests=[]))
        pending_path = '/api/skills/diagnostics/' + pending['id']
        _, attempt = learner.call('/api/skills/challenges', dict(assessment_id='bound-test', request_id='bound-attempt'))
        assert learner.call('/api/skills/challenges/'+attempt['id']+'/submit', dict(answers={'q1':'trust','q2':'trust'}))[0] == 200
        advance = dict(revision=1, attempt_id=attempt['id'])
        assert learner.call(diag_path+'/advance', advance)[0] == 200
        assert MARKER in json.dumps(learner.call(diag_path)[1])
        with sqlite3.connect(skills.config['DATABASE']) as db:
            if change == 'paid':
                db.execute("UPDATE lessons SET access='member' WHERE id=?", (FREE,))
            elif change == 'revoked':
                db.execute("UPDATE users SET entitlement='revoked' WHERE email='member@example.test'")
            elif change == 'lesson_withdrawn':
                db.execute("UPDATE lessons SET status='draft' WHERE id=?", (FREE,))
            else:
                db.execute("UPDATE courses SET status='draft' WHERE id=(SELECT m.course_id FROM modules m JOIN lessons l ON l.module_id=m.id WHERE l.id=?)", (FREE,))
        for path in [task_path, sub_path]:
            assert learner.call(path)[0] == 403
        assert learner.call('/api/skills/practical-tasks')[1] == {'tasks': []}
        assert learner.call('/api/skills/practical-submissions')[1]['submissions'] == [dict(id=submission['id'], task_id=task['id'], access_required=True)]
        assert learner.call('/api/skills/practical-submissions', create)[0] == 403
        assert learner.call(sub_path, dict(work, revision=2), 'PUT')[0] == 403
        assert other.call(sub_path)[0] == 404
        for path in [diag_path, '/api/skills/diagnostics']:
            code, result = learner.call(path)
            assert code == 200 and MARKER not in json.dumps(result)
        detail = learner.call(diag_path)[1]
        assert detail['observations'][0]['access_required'] is True
        assert detail['observations'][0]['passed'] is False
        assert learner.call(pending_path)[1]['next'] is None
        assert learner.call(pending_path+'/advance', advance)[0] == 400
        # Replay remains metadata-only; new planning cannot offer inaccessible forms.
        assert MARKER not in json.dumps(learner.call(diag_path+'/advance', advance)[1])
        assert learner.call('/api/skills/diagnostics', dict(request_id='blocked-diagnostic', interests=[]))[1]['next'] is None
        assert admin.call(task_path)[0] == 200
        with sqlite3.connect(skills.config['DATABASE']) as db:
            db.execute("UPDATE lessons SET access='free',status='published' WHERE id=?", (FREE,))
            db.execute("UPDATE courses SET status='published'")
        assert learner.call(task_path)[0] == 200
        assert learner.call(sub_path)[1]['body'] == work['body']
        assert learner.call(pending_path)[1]['next']['assessment_id'] == 'bound-test'
        assert MARKER in json.dumps(learner.call(diag_path)[1])
        assert learner.call(pending_path+'/advance', advance)[0] == 200
        assert learner.call(sub_path, dict(work, revision=2, status='submitted'), 'PUT')[0] == 200
        with sqlite3.connect(skills.config['DATABASE']) as db:
            assert db.execute('SELECT COUNT(*) FROM skill_attempts').fetchone()[0] == 1
            assert db.execute('SELECT COUNT(*) FROM skill_results').fetchone()[0] == 1
            assert db.execute('SELECT COUNT(*) FROM skill_practical_submissions').fetchone()[0] == 1
    finally:
        server.shutdown(); thread.join(); server.server_close()
