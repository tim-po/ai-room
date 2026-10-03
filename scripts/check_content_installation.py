"""Disposable content rebase and rendered-source check; no assessment approval."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import threading
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
from club import create_app
from club.seed import seed_database

out = Path(os.environ.get('CONTENT_EVIDENCE', '/tmp/content-installation'))
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='club-content-') as tmp:
    database = str(Path(tmp)/'candidate.sqlite')
    os.environ['CLUB_SEED_PASSWORD'] = 'local-content-fixture-only'
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text()); seed_database(db)
    app = create_app(dict(TESTING=True, DATABASE=database, SECRET_KEY='disposable-content'))
    def cli(*args):
        result = app.test_cli_runner().invoke(args=list(args))
        assert result.exit_code == 0, result.output
        return result.output
    cli('init-skills'); cli('init-teaching'); cli('install-skill-examples')
    parents = []
    for command in ['install-skill-foundations', 'install-skill-specialists']:
        with sqlite3.connect(database) as db:
            parent = db.execute('SELECT release_id FROM skill_active').fetchone()[0]
        parents.append(parent)
        cli(command, '--from-release', parent, '--reviewer', 'user-admin')
    foundations = json.loads(cli('inspect-skill-foundations'))
    specialists = json.loads(cli('inspect-skill-specialists'))
    with sqlite3.connect(database) as db:
        release, raw = db.execute('SELECT r.id,r.body FROM skill_releases r JOIN skill_active a ON a.release_id=r.id').fetchone()
        graph = json.loads(raw)
        abilities = {n['id'] for n in graph['nodes'] if n['kind']=='ability'}
        assert abilities == {m['objective_id'] for m in graph['mappings']}
        total = db.execute('SELECT COUNT(*) FROM lessons').fetchone()[0]
        assert db.execute('SELECT COUNT(*) FROM skill_forms').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM skill_evidence').fetchone()[0] == 0
        mapped = len({m['lesson_id'] for m in graph['mappings']})
    server = make_server('127.0.0.1', 0, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        for width in [390,1440]:
            page.set_viewport_size({'width':width,'height':1000})
            for kind, objective in [('foundation','basic-ai.context'),('debug','coding.debug.demonstrate')]:
                # Locate the stable objective by installed inventory when its suffix changes.
                if kind == 'debug':
                    objective = next(n['id'] for n in graph['nodes'] if n['kind']=='ability' and 'debug' in n['id'])
                page.goto(origin+'/?node='+objective)
                link = page.locator('#node-detail a[href^="/lessons/"]').first
                link.wait_for();link.click()
                assert page.locator('h1').inner_text()
                if kind=='debug': assert 'Вход JSON:' in page.locator('body').inner_text()
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                page.screenshot(path=str(out/f'{kind}-{width}.png'),full_page=True)
        assert not errors, errors
        browser.close()
    server.shutdown()
    backups = list(Path(tmp).glob('*.before-*.sqlite'))
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in backups)
    report = dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source=str(Path.cwd()),origin=origin,parents=parents,active_release=release,abilities_with_teaching=len(abilities),mapped_lessons=mapped,total_lessons=total,unmapped_lessons=total-mapped,private_backups=len(backups),foundation_candidates=len(foundations),specialist_lessons=len(specialists['lessons']),assessment_publications=0,evidence_records=0,errors=errors,scope='Synthetic teaching only; no certification, equivalence, provider or most-content acceptance')
    (out/'installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report))
