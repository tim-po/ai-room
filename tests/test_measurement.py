import sqlite3
from datetime import date, timedelta
from flask import template_rendered
from test_learning import app, login, post, FREE, PAID


def test_activity_deduplication_privacy_and_role_boundaries(app):
    client = app.test_client()
    csrf = login(client)
    for _ in range(3):
        assert client.get('/lessons/' + FREE).status_code == 200
        assert post(client, '/api/lessons/'+FREE+'/practice', {'body':'PRIVATE DRAFT','status':'submitted'}, csrf).status_code == 200
        assert post(client, '/api/lessons/'+FREE+'/completion', {'completed':True}, csrf).status_code == 200
    db = sqlite3.connect(app.config['DATABASE'])
    counts = dict(db.execute('SELECT name,COUNT(*) FROM events GROUP BY name'))
    assert counts == {'course_started':1,'lesson_started':1,'practice_submitted':1,'lesson_completed':1}
    assert db.execute('SELECT COUNT(*) FROM learning_days').fetchone()[0] == 1
    assert 'PRIVATE DRAFT' not in str(db.execute('SELECT * FROM events').fetchall())
    # A prior learning day makes the next first daily activity a return, once only.
    db.execute("UPDATE learning_days SET day=date('now','-1 day')")
    db.commit()
    for _ in range(3):
        client.get('/lessons/' + FREE)
    assert db.execute("SELECT COUNT(*) FROM events WHERE name='meaningful_return'").fetchone()[0] == 1
    assert db.execute('SELECT COUNT(*) FROM course_starts').fetchone()[0] == 1
    assert client.get('/lessons/' + PAID).status_code == 403
    assert client.get('/admin/measurement').status_code == 403
    assert app.test_client().get('/admin/measurement').status_code == 401
    login(client, 'editor')
    assert client.get('/admin/measurement').status_code == 403
    client.get('/lessons/' + FREE)
    assert db.execute('SELECT COUNT(*) FROM learning_days').fetchone()[0] == 2
    assert db.execute("SELECT COUNT(*) FROM events WHERE user_id='user-editor'").fetchone()[0] == 0
    login(client, 'admin')
    assert client.get('/admin/measurement').status_code == 200
    db.close()


def test_report_denominators_time_and_calendar_retention(app):
    db = sqlite3.connect(app.config['DATABASE'])
    for user, seconds in [('user-learner',60),('user-member',180)]:
        db.execute("INSERT INTO events(user_id,name,lesson_id,created_at) VALUES(?,'lesson_started',?,'2026-01-01 10:00:00')", (user,FREE))
        db.execute("INSERT INTO events(user_id,name,lesson_id,created_at) VALUES(?,'practice_submitted',?,datetime('2026-01-01 10:00:00',?))", (user,FREE,f'+{seconds} seconds'))
    # One learner completes all current lessons in a module, another only starts.
    module = db.execute('SELECT module_id FROM lessons WHERE id=?',(FREE,)).fetchone()[0]
    for (lesson,) in db.execute('SELECT id FROM lessons WHERE module_id=?',(module,)).fetchall():
        db.execute('INSERT INTO progress(user_id,lesson_id,completed) VALUES(?,?,1)',('user-learner',lesson))
    db.execute('INSERT INTO progress(user_id,lesson_id) VALUES(?,?)',('user-member',FREE))
    monday = date.today() - timedelta(days=date.today().weekday())
    for user, weeks in [('user-learner',2),('user-member',2),('user-learner',1)]:
        db.execute('INSERT INTO learning_days VALUES(?,?)',(user,(monday-timedelta(weeks=weeks)).isoformat()))
    db.commit()
    client = app.test_client()
    login(client, 'admin')
    captured = []
    def receive(sender, template, context, **extra):
        captured.append(context)
    with template_rendered.connected_to(receive, app):
        assert client.get('/admin/measurement').status_code == 200
    context = captured[0]
    assert (context['activated'],context['learners'],context['median'],context['result_count']) == (2,3,120,2)
    last = context['weeks'][-1]
    assert (last['numerator'],last['denominator']) == (1,2)
    selected = next(m for m in context['modules'] if m['id'] == module)
    assert (selected['starters'],selected['finishers']) == (2,1)
    db.close()


def test_v2_upgrade_preserves_data_and_does_not_invent_history(app):
    db = sqlite3.connect(app.config['DATABASE'])
    db.executescript('DROP TABLE learning_days; DROP TABLE course_starts; PRAGMA user_version=2;')
    db.execute('INSERT INTO progress(user_id,lesson_id,completed) VALUES(?,?,1)',('user-learner',FREE))
    db.commit()
    for _ in range(2):
        assert app.test_cli_runner().invoke(args=['init-db']).exit_code == 0
    assert db.execute('PRAGMA user_version').fetchone()[0] == 3
    assert db.execute('SELECT completed FROM progress').fetchone()[0] == 1
    assert db.execute('SELECT COUNT(*) FROM learning_days').fetchone()[0] == 0
    assert db.execute('SELECT COUNT(*) FROM events').fetchone()[0] == 0
    db.close()
