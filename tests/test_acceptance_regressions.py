"""Independent tester regressions plus persistence and background-write coverage."""
import re
import sqlite3
from pathlib import Path
import pytest
from club import create_app
from club.seed import seed_database

@pytest.fixture
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv('CLUB_SEED_PASSWORD', 'isolated-regression-password')
    database = str(tmp_path / 'regression.sqlite')
    with sqlite3.connect(database) as db:
        db.executescript(Path('club/schema.sql').read_text())
        seed_database(db)
    app = create_app({'TESTING':True,'DATABASE':database,'SECRET_KEY':'isolated-regression-key'})
    client = app.test_client()
    client.get('/login')
    with client.session_transaction() as state:
        csrf = state['csrf']
    response = client.post('/login',data={'email':'member@example.test','password':'isolated-regression-password','csrf':csrf})
    assert response.status_code == 302
    with client.session_transaction() as state:
        csrf = state['csrf']
    return client, database, csrf

def test_home_resumes_most_recently_reopened_text_lesson(fresh):
    client, database, _ = fresh
    first = 'foundations-start-03'
    second = 'foundations-start-04'
    assert client.get('/lessons/'+first).status_code == 200
    assert client.get('/lessons/'+second).status_code == 200
    # Deterministic fixture chronology, independent of machine clock resolution.
    with sqlite3.connect(database) as db:
        db.execute("UPDATE progress SET updated_at='2000-01-01 00:00:00' WHERE lesson_id=?",(first,))
        db.execute("UPDATE progress SET updated_at='2000-01-02 00:00:00' WHERE lesson_id=?",(second,))
    assert client.get('/lessons/'+first).status_code == 200
    home = client.get('/').text
    hero = re.search(r'<section class="hero">(.*?)</section>',home,re.S).group(1)
    actual = re.search(r'href="(/lessons/[^"]+)"',hero).group(1)
    assert actual == '/lessons/'+first

def test_first_completed_preferences_after_skip_emits_completion_event(fresh):
    client, database, csrf = fresh
    assert client.post('/preferences/skip',data={'csrf':csrf}).status_code == 302
    assert client.post('/preferences',data={'csrf':csrf,'goal':'build','experience':'experienced','weekly_goal':'2'}).status_code == 302
    with sqlite3.connect(database) as db:
        count = db.execute("SELECT COUNT(*) FROM events WHERE name='onboarding_completed'").fetchone()[0]
    assert count == 1


def hero_target(client):
    hero = re.search(r'<section class="hero">(.*?)</section>', client.get('/').text, re.S).group(1)
    return re.search(r'href="(/lessons/[^"]+)"', hero).group(1)


def test_navigation_survives_background_writes_and_second_device(fresh):
    client, database, csrf = fresh
    first, second = 'foundations-start-03', 'foundations-start-04'
    for lesson in (first, second, first):
        assert client.get('/lessons/' + lesson).status_code == 200
    # A background tab saves video or changes completion after navigation elsewhere.
    for suffix, payload in [('video', {'seconds': 12}), ('completion', {'completed': True}),
                            ('completion', {'completed': False})]:
        assert client.post('/api/lessons/' + second + '/' + suffix, json=payload,
                           headers={'X-CSRF-Token': csrf}).status_code == 200
    assert hero_target(client) == '/lessons/' + first
    assert client.post('/logout', data={'csrf': csrf}).status_code == 302
    # Recreate the application and cookie jar, keeping only the database.
    restarted = create_app({'TESTING': True, 'DATABASE': database, 'SECRET_KEY': 'second-process'})
    device = restarted.test_client()
    device.get('/login')
    with device.session_transaction() as state:
        token = state['csrf']
    assert device.post('/login', data={'email': 'member@example.test',
        'password': 'isolated-regression-password', 'csrf': token}).status_code == 302
    assert hero_target(device) == '/lessons/' + first
    with sqlite3.connect(database) as db:
        db.execute("UPDATE lessons SET status='draft' WHERE id=?", (first,))
    assert hero_target(device) == '/lessons/' + second
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT COUNT(*) FROM lesson_visits').fetchone()[0] == 2


def test_onboarding_skips_edits_and_retries_are_distinct(fresh):
    client, database, csrf = fresh
    for _ in range(2):
        assert client.post('/preferences/skip', data={'csrf': csrf}).status_code == 302
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE name='onboarding_completed'").fetchone()[0] == 0
    for goal in ('work', 'work', 'build'):
        assert client.post('/preferences', data={'csrf': csrf, 'goal': goal,
            'experience': 'beginner', 'weekly_goal': '0'}).status_code == 302
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE name='onboarding_completed'").fetchone()[0] == 1


def test_v3_upgrade_preserves_work_without_inventing_visits(fresh):
    client, database, csrf = fresh
    lesson = 'foundations-start-03'
    assert client.post('/api/lessons/' + lesson + '/completion', json={'completed': True},
                       headers={'X-CSRF-Token': csrf}).status_code == 200
    with sqlite3.connect(database) as db:
        db.executescript('DROP TABLE lesson_visits; DROP INDEX unique_onboarding_completion; PRAGMA user_version=3;')
        for _ in range(2):
            db.execute("INSERT INTO events(user_id,name) VALUES('user-member','onboarding_completed')")
    for _ in range(2):
        assert client.application.test_cli_runner().invoke(args=['init-db']).exit_code == 0
    with sqlite3.connect(database) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 6
        assert db.execute('SELECT completed FROM progress WHERE lesson_id=?', (lesson,)).fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM lesson_visits').fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM events WHERE name='onboarding_completed'").fetchone()[0] == 1
    assert client.get('/').status_code == 200
