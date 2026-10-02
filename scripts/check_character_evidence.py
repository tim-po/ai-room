"""Character states against real isolated APIs; synthetic evidence is UI-only."""
import json, os, sqlite3, subprocess, sys, tempfile, threading
from pathlib import Path
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
from club import create_app
from club.seed import seed_database
sys.path.insert(0, str(Path('tests').resolve()))
from test_learning import PASSWORD, login, post
from test_practical import setup_task, draft, save

out = Path(os.environ.get('CHARACTER_EVIDENCE', '/tmp/character-evidence'))
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    os.environ['CLUB_SEED_PASSWORD'] = PASSWORD
    database = str(Path(tmp) / 'test.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text()); seed_database(db)
    app = create_app({'DATABASE': database, 'SECRET_KEY': 'character-disposable', 'TESTING': True})
    assert app.test_cli_runner().invoke(args=['init-skills']).exit_code == 0
    admin, at, task, _ = setup_task(app)
    learner = app.test_client(); lt = login(learner)
    member = app.test_client(); mt = login(member, 'member')
    server = make_server('127.0.0.1', 0, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    results = []; errors = []
    def challenge(client, token, key):
        attempt = post(client, '/api/skills/challenges', {'assessment_id':'test-form-v1', 'request_id':key}, token).json
        result = post(client, '/api/skills/challenges/'+attempt['id']+'/submit', {'answers':{'q1':'check','q2':'check'}}, token)
        assert result.json['credited'], result.json
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        def check(state, who, knowledge, applied):
            context = browser.new_context(); page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(origin+'/login'); page.locator('[name=email]').fill(who+'@example.test')
            page.locator('[name=password]').fill(PASSWORD); page.get_by_role('button',name='Войти',exact=True).click()
            for width in [390, 1440]:
                page.set_viewport_size({'width':width,'height':1000}); page.goto(origin+'/profile')
                page.locator('.character-branch').first.wait_for(); page.evaluate('document.fonts.ready')
                me = page.evaluate("fetch('/api/skills/me').then(r=>r.json())")
                assert len(me['evidence']) == knowledge and len(me['application_evidence']) == applied
                assert page.locator('#character-recent').is_visible() == bool(knowledge or applied)
                heading = page.locator('#character-next h2').inner_text()
                assert ('Продолжайте' in heading) == bool(knowledge or applied)
                foundation = page.locator('.character-branch').first
                assert ('Понимание: подтверждено 1' if knowledge else 'Понимание: ещё не проверено') in foundation.inner_text()
                assert ('Применение: подтверждено 1' if applied else 'Применение: ещё не подтверждено') in foundation.inner_text()
                if applied:
                    assert 'Проверено ' in page.locator('#character-application').inner_text()
                    result = page.locator('#character-recent a[href^="/practice?"]')
                    result.focus(); page.keyboard.press('Enter'); page.wait_for_url('**/practice?submission=*')
                    page.get_by_role('heading',name='Применение подтверждено',exact=True).wait_for()
                    page.go_back(); page.locator('.character-branch').first.wait_for()
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                page.screenshot(path=str(out/f'{state}-{width}.png'), full_page=True)
                results.append({'state':state,'width':width,'understanding':knowledge,'application':applied,'overflow':False})
            context.close()
        check('empty','learner',0,0)
        challenge(learner,lt,'character-understanding')
        check('understanding','learner',1,0)
        submission = draft(member,mt,task).json
        assert save(member,mt,submission['id'],1).status_code == 200
        decision = post(admin,'/api/skills/practical-submissions/'+submission['id']+'/review',dict(revision=2,ratings={'source':'met','reason':'met'},feedback='Synthetic UI fixture only; both criteria marked met.'),at)
        assert decision.json['decision']['credited']
        check('application','member',0,1)
        challenge(member,mt,'character-combined')
        check('combined','member',1,1)
        assert not errors, errors
        browser.close()
    server.shutdown()
    report = {'source':str(Path.cwd()),'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'origin':origin,'synthetic_UI_evidence_only':True,'states':results,'errors':errors}
    (out/'browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))
