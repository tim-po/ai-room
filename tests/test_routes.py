"""Route composition must reuse progress and respect all publication boundaries."""
import re
import sqlite3
from test_learning import app, login, post, FREE


def hero(client):
    """Where the map's "Продолжить" / "Следующий шаг" strip leads."""
    data = client.get('/api/app/home').json
    target = data['continuation']['unfinished'] or data['next']
    return target['url'] if target else ''


def form(revision='1', **overrides):
    data = dict(title='Проверяемый маршрут',outcome='Полезный результат',explanation='Сначала основа',
                owner='Редактор',goal='work',status='published',revision=revision,
                lesson_id=[FREE,'everyday-ai-intro-01'],bridge_id=[FREE])
    return data | overrides


def test_beginner_bridge_experienced_entry_and_explicit_switch(app):
    c=app.test_client();csrf=login(c)
    c.get('/lessons/foundations-start-04')
    c.post('/preferences',data=dict(csrf=csrf,goal='agents',experience='beginner',weekly_goal='0'))
    # Route preferences cannot discard unfinished work in another branch.
    assert '/lessons/foundations-start-04' in hero(c)
    post(c,'/api/lessons/foundations-start-04/completion',{'completed':True},csrf)
    assert '/lessons/'+FREE in hero(c)
    assert 'сначала основы' in c.get('/routes/path-agents').text
    assert 'agent-api-basics' in c.get('/routes/path-agents').text
    for lesson in [FREE,'foundations-start-02']:
        assert post(c,'/api/lessons/'+lesson+'/completion',{'completed':True},csrf).status_code==200
    assert '/lessons/agent-api-basics' in hero(c)
    c.post('/preferences',data=dict(csrf=csrf,goal='agents',experience='experienced',weekly_goal='2'))
    assert '/lessons/agent-lab-intro-01' in hero(c)
    c.get('/lessons/agent-lab-intro-01')
    c.post('/routes/path-work/select',data={'csrf':csrf})
    assert '/lessons/agent-lab-intro-01' in hero(c)
    second=app.test_client();login(second)
    assert '/lessons/agent-lab-intro-01' in hero(second)
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM progress WHERE completed=1').fetchone()[0]==3


def test_completion_access_exhaustion_and_unpublished_steps(app):
    c=app.test_client();csrf=login(c)
    for index in range(1,5):
        post(c,f'/api/lessons/foundations-start-{index:02}/completion',{'completed':True},csrf)
    assert 'маршрут ещё не пройден' in c.get('/routes/path-essentials').text
    assert 'Маршрут завершён' not in c.get('/routes/path-essentials').text
    c.post('/routes/path-work/select',data={'csrf':csrf})
    post(c,'/api/lessons/everyday-ai-intro-01/completion',{'completed':True},csrf)
    assert 'Маршрут завершён' in c.get('/routes/path-work').text
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE lessons SET status='draft',title='PRIVATE DRAFT TITLE' WHERE id='everyday-ai-intro-01'")
    page=c.get('/routes/path-work').text
    assert 'PRIVATE DRAFT TITLE' not in page
    assert 'временно снята с публикации' in page
    assert 'Маршрут завершён' not in c.get('/routes/path-work').text


def test_route_editor_lifecycle_shared_progress_conflicts_and_validation(app):
    learner=app.test_client();token=login(learner)
    post(learner,'/api/lessons/'+FREE+'/completion',{'completed':True},token)
    assert learner.get('/admin/routes').status_code==403
    assert learner.post('/admin/routes/new',data=form(csrf=token)).status_code==403
    editor=app.test_client();csrf=login(editor,'editor')
    created=editor.post('/admin/routes/new',data=form(csrf=csrf,status='draft'))
    assert created.status_code==302
    path=created.headers['Location'];identity=path.rsplit('/',1)[1]
    assert learner.get('/routes/'+identity).status_code==404
    assert editor.get(path+'/preview').status_code==200
    assert learner.get(path+'/preview').status_code==403
    assert editor.post(path,data=form(csrf=csrf)).status_code==302
    assert 'Завершено шагов: 1 из 2' in learner.get('/routes/'+identity).text
    assert editor.post(path,data=form(csrf=csrf)).status_code==409
    assert editor.post(path,data=form('2',csrf=csrf,lesson_id=[FREE,FREE])).status_code==400
    assert editor.post(path,data=form('2',csrf=csrf,lesson_id=['nonexistent'],bridge_id=[])).status_code==400
    assert editor.post(path,data=form('2',csrf=csrf,lesson_id=['everyday-ai-intro-01',FREE])).status_code==302
    assert 'Завершено шагов: 1 из 2' in learner.get('/routes/'+identity).text
    assert editor.post(path,data=form('3',csrf=csrf,lesson_id=[FREE,'everyday-ai-intro-01','foundations-start-03'])).status_code==302
    assert 'Завершено шагов: 1 из 3' in learner.get('/routes/'+identity).text
    assert editor.post(path,data=form('4',csrf=csrf,status='archived')).status_code==302
    assert learner.get('/routes/'+identity).status_code==404
    assert learner.post('/routes/'+identity+'/select',data={'csrf':token}).status_code==404
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT completed FROM progress WHERE lesson_id=?',(FREE,)).fetchone()[0]==1


def test_migration_and_route_seed_preserve_editorial_order(app):
    c=app.test_client();csrf=login(c,'editor')
    assert c.post('/admin/routes/path-work',data=form(csrf=csrf,lesson_id=['everyday-ai-intro-01',FREE])).status_code==302
    for _ in range(2):
        assert app.test_cli_runner().invoke(args=['init-db']).exit_code==0
        assert app.test_cli_runner().invoke(args=['seed']).exit_code==0
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute("SELECT lesson_id FROM route_steps WHERE route_id='path-work' ORDER BY position").fetchall()==[('everyday-ai-intro-01',),(FREE,)]
        assert db.execute('PRAGMA user_version').fetchone()[0]==6


def test_lesson_course_navigation(app):
    # The lesson page's previous/next links follow course order and mark club lessons.
    client = app.test_client(); login(client)
    data = client.get('/api/app/lessons/foundations-start-02').json
    assert data['previous']['id'] == FREE and data['following']['id'] == 'foundations-start-03'
    last = client.get('/api/app/lessons/foundations-start-04').json
    assert last['following']['id'] == 'foundations-context-01' and last['following']['locked']


def test_route_overview_resumes_intent_and_switch_resets_old_visits(app):
    c = app.test_client(); csrf = login(c, 'member')
    c.post('/routes/path-essentials/select', data={'csrf': csrf})
    with sqlite3.connect(app.config['DATABASE']) as db:
        lessons = [r[0] for r in db.execute("SELECT lesson_id FROM route_steps WHERE route_id='path-essentials' ORDER BY position")]
    for identity in lessons[:28]:
        post(c, '/api/lessons/'+identity+'/completion', {'completed': True}, csrf)
    c.get('/lessons/'+lessons[32])
    def primary():
        return re.search(r'<section class="panel" aria-label="Продолжить маршрут">(.*?)</section>', c.get('/routes/path-essentials').text, re.S).group(1)
    assert '/lessons/'+lessons[32] in primary()
    page = c.get('/routes/path-essentials').text
    assert page.count('class="module route-group"') == 9
    assert page.count('class="module route-group" open') == 1
    c.post('/routes/path-work/select', data={'csrf': csrf})
    assert 'Выбрать этот маршрут' in primary()
    assert '/lessons/' not in primary()
    c.post('/routes/path-essentials/select', data={'csrf': csrf})
    assert '/lessons/'+lessons[28] in primary()
    for identity in lessons[28:]:
        post(c, '/api/lessons/'+identity+'/completion', {'completed': True}, csrf)
    assert 'Маршрут завершён' in c.get('/routes/path-essentials').text
    assert '/lessons/' not in primary()
