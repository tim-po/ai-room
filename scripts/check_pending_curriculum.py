"""Rehearse pending changes on a private SQLite backup; never write the source DB."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import threading
from club import create_app
from club.curriculum_audit import inventory
from club.curriculum_review_bundle import bundle
from club.curriculum_revisions import install
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--private-output', type=Path, required=True)
parser.add_argument('--evidence', type=Path, required=True)
args = parser.parse_args()
os.umask(0o077)
args.private_output.mkdir(parents=True, exist_ok=False, mode=0o700)
args.evidence.mkdir(parents=True, exist_ok=True)
copy = args.private_output / 'rehearsal.sqlite'
with sqlite3.connect(args.source.resolve().as_uri()+'?mode=ro', uri=True) as source:
    with sqlite3.connect(copy) as target:
        source.backup(target)
app = create_app(dict(TESTING=True, DATABASE=str(copy), SECRET_KEY='local-rehearsal-only'))

def snapshot():
    with sqlite3.connect(copy) as db:
        names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {name: sorted([list(r) for r in db.execute('SELECT * FROM "'+name+'"')], key=repr) for name in names}

before = snapshot()
with sqlite3.connect(copy) as db:
    reviewer = db.execute("SELECT id FROM users WHERE role='editor' ORDER BY id LIMIT 1").fetchone()[0]
for command in [('init-skills',), ('init-teaching',), ('install-transfer-sources', '--reviewer', reviewer)]:
    result = app.test_cli_runner().invoke(args=list(command))
    if result.exit_code:
        raise RuntimeError(result.output)
with sqlite3.connect(copy) as db:
    db.row_factory = sqlite3.Row
    export = bundle(db, reviewer)
    private = args.private_output/'CUMULATIVE-REVIEW.json'
    private.write_text(json.dumps(export, ensure_ascii=False, indent=2)+'\n')
    curriculum = export['manifest']['curriculum']
    pre_coverage = inventory(db)['coverage']
    # This is an installation rehearsal, not a semantic approval or publication.
    install(db, reviewer=reviewer, reviewed_sha256=curriculum['sha256'], confirm_reviewed=True)
    post_coverage = inventory(db)['coverage']
    assert install(db, reviewer=reviewer, reviewed_sha256=curriculum['sha256'], confirm_reviewed=True) is False
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
after = snapshot()
allowed = {'lessons', 'skill_active', 'skill_releases', 'skill_form_bindings'}
for table, rows in before.items():
    if table not in allowed:
        assert rows == after[table], table
assert len(before['lessons']) == len(after['lessons'])
assert len(before['skill_forms']) == len(after['skill_forms']) == 3
# Existing stored attempts, results and source feedback are returned unchanged.
with sqlite3.connect(copy) as db:
    attempts = db.execute('SELECT a.id,a.user_id,r.body,a.form_id FROM skill_attempts a JOIN skill_results r ON r.attempt_id=a.id ORDER BY a.id').fetchall()
    forms = {r[0]: json.loads(r[1]) for r in db.execute('SELECT id,body FROM skill_forms')}
checks = []
for attempt_id, user_id, body, form_id in attempts:
    client = app.test_client()
    with client.session_transaction() as session:
        session.update(user_id=user_id, csrf='private-rehearsal-token')
    response = client.get('/api/skills/challenges/'+attempt_id)
    assert response.status_code == 200
    assert response.json['result'] == json.loads(body)
    for feedback in response.json['result']['feedback']:
        source = feedback['source']
        assert client.get('/lessons/'+source['lesson_id']).status_code == 200
    retry = client.post('/api/skills/challenges', json={'assessment_id':form_id,'request_id':'rehearsal-repeat-'+attempt_id}, headers={'X-CSRF-Token':'private-rehearsal-token'})
    if retry.status_code == 409 and retry.json.get('code') == 'pending_attempt':
        retry = client.get(retry.json['pending_attempt']['resume_url'])
        assert retry.status_code == 200
    else:
        assert retry.status_code == 201
    assert retry.json['mode'] == 'practice'
    checks.append(dict(form_id=form_id, historical_feedback_unchanged=True, lesson_access=200, repeat_mode='practice'))
# Browser uses the retained learner session on the local copy, no credential changes.
server = make_server('127.0.0.1', 0, app)
threading.Thread(target=server.serve_forever, daemon=True).start()
origin = f'http://127.0.0.1:{server.server_port}'
errors = []
browser_sources = []
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in [360, 390, 768, 1440]:
            context = browser.new_context(viewport={'width':width,'height':1000})
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            for attempt_id, user_id, body, form_id in attempts:
                token = app.session_interface.get_signing_serializer(app).dumps({'user_id':user_id,'csrf':'private-rehearsal-token'})
                context.add_cookies([dict(name='session',value=token,url=origin)])
                page.goto(origin+'/challenges?attempt='+attempt_id)
                page.get_by_text('Результат сохранён', exact=True).wait_for()
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                # Follow the actual feedback link with a keyboard, not just an API GET.
                source_id = json.loads(body)['feedback'][0]['source']['lesson_id']
                with sqlite3.connect(copy) as db:
                    title = db.execute('SELECT title FROM lessons WHERE id=?', (source_id,)).fetchone()[0]
                link = page.locator('a[href="/lessons/'+source_id+'"]').first
                link.focus()
                page.keyboard.press('Enter')
                page.wait_for_url(origin+'/lessons/'+source_id)
                page.get_by_role('heading', name=title, exact=True).wait_for()
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                browser_sources.append(dict(width=width, form_id=form_id, lesson_id=source_id, keyboard_open=True))
                if attempt_id == attempts[0][0]:
                    page.screenshot(path=str(args.evidence/f'copied-source-{width}.png'),full_page=True)
                page.go_back()
                page.get_by_text('Результат сохранён', exact=True).wait_for()
                if attempt_id == attempts[0][0]:
                    page.screenshot(path=str(args.evidence/f'copied-feedback-{width}.png'),full_page=True)
            context.close()
        browser.close()
finally:
    server.shutdown()
assert not errors
final = snapshot()
for name in ['skill_evidence','skill_application_evidence','progress','practice','skill_results']:
    assert before.get(name) == final.get(name), name
manifest = export['manifest']
report = dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    scope='Builder rehearsal on fresh private copy of current staging; no staging mutation or independent approval',
    package_path=str(private), package_mode=oct(private.stat().st_mode & 0o777), package_sha256=export['sha256'],
    curriculum_sha256=curriculum['sha256'], curriculum_version=curriculum['manifest']['version'],
    graph_sha256=curriculum['manifest']['graph_sha256'], parent_release=curriculum['manifest']['base_release'],
    coverage_before=pre_coverage, coverage_after=post_coverage, revisions=len(curriculum['manifest']['revisions']),
    retained_form_ids=[f['id'] for f in manifest['retained_forms']], original_proposals=len(manifest['original_form_proposals']),
    transfer_proposals=[dict(id=c['id'],sha256=c['sha256'],source_sha256=c['source_snapshot']['sha256'],practical_sha256=c['practical_sha256']) for c in manifest['transfer_publication_candidates']],
    preserved_tables=sorted(set(before)-allowed), historical_checks=checks, browser_widths=[360,390,768,1440], browser_source_checks=browser_sources, browser_errors=errors,
    semantic_approval=False, staged_mutation=False, provider_called=False)
(args.evidence/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
