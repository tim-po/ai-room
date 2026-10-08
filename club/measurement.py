"""First-party learning activity; never accepts client-authored analytics payloads."""
from datetime import datetime, timedelta, timezone
from flask import abort, g, render_template

from .storage import additive_tables

# Days a learner was present (opened a lesson), apart from days they actually learned.
SCHEMA = ('CREATE TABLE IF NOT EXISTS visit_days (user_id TEXT NOT NULL REFERENCES users(id), day TEXT NOT NULL, PRIMARY KEY(user_id,day))',)
MEANINGFUL = ('section_reached', 'practice_saved', 'practice_submitted', 'lesson_completed')


def register_measurement(app, db, query, event):
    from .skill_measurement import register_skill_measurement
    register_skill_measurement(app, query)
    ensure = additive_tables(app, SCHEMA)
    app.before_request(ensure)   # before any write in the request, so it never waits on it

    def activity(lesson_id, meaningful=True):
        """Called inside the same transaction as the learning action. Editors and admins are
        excluded so preview/maintenance cannot inflate learner rates. Opening a lesson
        (meaningful=False) records presence and course starts only: learning days and returns
        come from learning actions (a new section reached, practice saved, completion)."""
        if g.user['role'] != 'learner':
            return
        course_id = query('SELECT m.course_id FROM lessons l JOIN modules m ON m.id=l.module_id WHERE l.id=?', (lesson_id,), True)['course_id']
        inserted = db().execute('INSERT OR IGNORE INTO course_starts(user_id,course_id) VALUES(?,?)', (g.user['id'], course_id)).rowcount
        if inserted:
            event('course_started', lesson_id)
        db().execute("INSERT OR IGNORE INTO visit_days(user_id,day) VALUES(?,date('now'))", (g.user['id'],))
        if not meaningful:
            return
        prior = query('SELECT 1 FROM learning_days WHERE user_id=? AND day<date(\'now\') LIMIT 1', (g.user['id'],), True)
        new_day = db().execute('INSERT OR IGNORE INTO learning_days(user_id,day) VALUES(?,date(\'now\'))', (g.user['id'],)).rowcount
        if new_day and prior:
            event('meaningful_return', lesson_id)

    @app.get('/admin/measurement')
    def measurement():
        if not g.user:
            abort(401)
        if g.user['role'] != 'admin':
            abort(403)
        return render_template('measurement.html', **measurement_data())

    def measurement_data():
        learners = query("SELECT COUNT(*) n FROM users WHERE role='learner'", one=True)['n']
        activated = query("SELECT COUNT(DISTINCT e.user_id) n FROM events e JOIN users u ON u.id=e.user_id WHERE u.role='learner' AND e.name='practice_submitted'", one=True)['n']
        first_results = query('''WITH starts AS (
            SELECT e.user_id,MIN(e.created_at) started FROM events e JOIN users u ON u.id=e.user_id
            WHERE u.role='learner' AND e.name IN ('lesson_started','course_started') GROUP BY e.user_id
        ), results AS (
            SELECT user_id,MIN(created_at) submitted FROM events WHERE name='practice_submitted' GROUP BY user_id
        ) SELECT s.user_id,ROUND((julianday(r.submitted)-julianday(s.started))*86400) seconds
        FROM starts s JOIN results r USING(user_id) WHERE r.submitted>=s.started''')
        durations = sorted(int(r['seconds']) for r in first_results)
        n = len(durations)
        median = (durations[(n-1)//2] + durations[n//2]) / 2 if n else None
        modules = query('''SELECT m.id,m.title,c.title course_title,
            COUNT(DISTINCT p.user_id) starters,
            COUNT(DISTINCT CASE WHEN NOT EXISTS (
                SELECT 1 FROM lessons required WHERE required.module_id=m.id AND required.status='published'
                AND NOT EXISTS (SELECT 1 FROM progress done WHERE done.lesson_id=required.id AND done.user_id=p.user_id AND done.completed=1)
            ) THEN p.user_id END) finishers
            FROM modules m JOIN courses c ON c.id=m.course_id
            JOIN lessons l ON l.module_id=m.id AND l.status='published'
            LEFT JOIN progress p ON p.lesson_id=l.id AND p.user_id IN (SELECT id FROM users WHERE role='learner')
            WHERE c.status='published' GROUP BY m.id ORDER BY c.id,m.position''')
        today = datetime.now(timezone.utc).date()
        monday = today - timedelta(days=today.weekday())
        weeks = []
        # Only fully observed pairs of UTC calendar weeks; no incomplete-week rate.
        for offset in range(4, 0, -1):
            start = monday - timedelta(weeks=offset+1)
            following = start + timedelta(weeks=1)
            end = following + timedelta(weeks=1)
            counts = query('''SELECT COUNT(DISTINCT a.user_id) denominator,
                COUNT(DISTINCT CASE WHEN EXISTS (SELECT 1 FROM learning_days b
                    WHERE b.user_id=a.user_id AND b.day>=? AND b.day<?) THEN a.user_id END) numerator
                FROM learning_days a JOIN users u ON u.id=a.user_id
                WHERE u.role='learner' AND a.day>=? AND a.day<?''',
                (following.isoformat(), end.isoformat(), start.isoformat(), following.isoformat()), True)
            weeks.append(dict(start=start, following=following, **dict(counts)))
        events = query('''SELECT e.name,COUNT(*) n FROM events e JOIN users u ON u.id=e.user_id
            WHERE u.role='learner' GROUP BY e.name ORDER BY e.name''')
        return dict(learners=learners, activated=activated, median=median, result_count=n, modules=modules,
                    weeks=weeks, events=events, loop=learning_loop(today, monday))

    app.extensions['measurement_data'] = measurement_data

    def table(name):
        return bool(query("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,), True))

    def learning_loop(today, monday):
        """Activation, meaningful return and weekly active learners, plus use of the loop features
        (plan, calendar, /continue, assistant links). Learners only; meaningful = MEANINGFUL events."""
        marks = ','.join('?' * len(MEANINGFUL))
        started = query(f'''WITH first_start AS (
              SELECT e.user_id,MIN(e.created_at) at FROM events e JOIN users u ON u.id=e.user_id
              WHERE u.role='learner' AND e.name='lesson_started' GROUP BY e.user_id),
            first_learning AS (SELECT user_id,MIN(created_at) at FROM events WHERE name IN ({marks}) GROUP BY user_id)
            SELECT COUNT(*) starters,
              SUM(CASE WHEN l.at IS NOT NULL AND julianday(l.at)-julianday(s.at) BETWEEN 0 AND 1 THEN 1 ELSE 0 END) activated
            FROM first_start s LEFT JOIN first_learning l USING(user_id)''', MEANINGFUL, True)
        returns = []
        for days in (1, 7, 30):
            row = query('''WITH first AS (
                  SELECT d.user_id,MIN(d.day) day FROM learning_days d JOIN users u ON u.id=d.user_id
                  WHERE u.role='learner' GROUP BY d.user_id)
                SELECT COUNT(*) cohort, SUM(EXISTS(SELECT 1 FROM learning_days b WHERE b.user_id=f.user_id
                  AND b.day>f.day AND b.day<=date(f.day,?))) returned
                FROM first f WHERE f.day<=date(?,?)''', (f'+{days} days', today.isoformat(), f'-{days} days'), True)
            returns.append(dict(days=days, cohort=row['cohort'], returned=row['returned'] or 0))
        weekly = []
        for offset in range(4, -1, -1):
            start = monday - timedelta(weeks=offset)
            n = query('''SELECT COUNT(DISTINCT d.user_id) n FROM learning_days d JOIN users u ON u.id=d.user_id
                WHERE u.role='learner' AND d.day>=? AND d.day<?''', (start.isoformat(), (start + timedelta(weeks=1)).isoformat()), True)['n']
            weekly.append(dict(start=start, learners=n, partial=offset == 0))
        def learners_with(name):
            return query('''SELECT COUNT(DISTINCT e.user_id) n FROM events e JOIN users u ON u.id=e.user_id
                WHERE u.role='learner' AND e.name=?''', (name,), True)['n']
        features = [
            ('Дошли хотя бы до одного нового раздела урока', learners_with('section_reached')),
            ('Выбрали план занятий', query("""SELECT COUNT(*) n FROM learning_plans p JOIN users u ON u.id=p.user_id
                WHERE u.role='learner' AND p.days!=''""", one=True)['n'] if table('learning_plans') else 0),
            ('Добавили план в календарь (.ics)', learners_with('plan_calendar')),
            ('Пришли по ссылке «продолжить» (календарь, ассистент)', learners_with('continue_opened')),
            ('Подключили ИИ-ассистента ссылкой', learners_with('session_connected')),
            ('Получили работу, сохранённую ассистентом', query("""SELECT COUNT(DISTINCT o.user_id) n FROM practice_origins o
                JOIN users u ON u.id=o.user_id WHERE u.role='learner'""", one=True)['n'] if table('practice_origins') else 0),
        ]
        return dict(starters=started['starters'] or 0, activated=started['activated'] or 0, returns=returns, weekly=weekly, features=features)

    return activity
