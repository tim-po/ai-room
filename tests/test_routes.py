"""Route composition must reuse progress and respect all publication boundaries."""
import re
import sqlite3
from test_learning import app, login, post, FREE


def hero(client):
    return re.search(r'<section class="hero">(.*?)</section>',client.get('/').text,re.S).group(1)


def form(revision='1', **overrides):
    data = dict(title='Проверяемый маршрут',outcome='Полезный результат',explanation='Сначала основа',
                owner='Редактор',goal='work',status='published',revision=revision,
                lesson_id=[FREE,'everyday-ai-intro-01'],bridge_id=[FREE])
    return data | overrides


def test_beginner_bridge_experienced_entry_and_explicit_switch(app):
    c=app.test_client();csrf=login(c)
    c.get('/lessons/foundations-start-04')
    c.post('/preferences',data=dict(csrf=csrf,goal='agents',experience='beginner',weekly_goal='0'))
    assert '/lessons/'+FREE in hero(c)
    assert 'Сначала основы' in hero(c)
    assert 'agent-api-basics' in c.get('/routes/path-agents').text
    for lesson in [FREE,'foundations-start-02']:
        assert post(c,'/api/lessons/'+lesson+'/completion',{'completed':True},csrf).status_code==200
    assert '/lessons/agent-api-basics' in hero(c)
    c.post('/preferences',data=dict(csrf=csrf,goal='agents',experience='experienced',weekly_goal='2'))
    assert '/lessons/agent-lab-intro-01' in hero(c)
    c.get('/lessons/agent-lab-intro-01')
    c.post('/routes/path-work/select',data={'csrf':csrf})
    assert '/lessons/everyday-ai-intro-01' in hero(c)
    second=app.test_client();login(second)
    assert '/lessons/everyday-ai-intro-01' in hero(second)
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM progress WHERE completed=1').fetchone()[0]==2


def test_completion_access_exhaustion_and_unpublished_steps(app):
    c=app.test_client();csrf=login(c)
    for index in range(1,5):
        post(c,f'/api/lessons/foundations-start-{index:02}/completion',{'completed':True},csrf)
    assert 'маршрут ещё не пройден' in c.get('/').text
    assert 'Маршрут завершён' not in hero(c)
    c.post('/routes/path-work/select',data={'csrf':csrf})
    post(c,'/api/lessons/everyday-ai-intro-01/completion',{'completed':True},csrf)
    assert 'Маршрут завершён' in hero(c)
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE lessons SET status='draft',title='PRIVATE DRAFT TITLE' WHERE id='everyday-ai-intro-01'")
    page=c.get('/routes/path-work').text
    assert 'PRIVATE DRAFT TITLE' not in page
    assert 'временно снята с публикации' in page
    assert 'Маршрут завершён' not in hero(c)


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
        assert db.execute('PRAGMA user_version').fetchone()[0]==5
