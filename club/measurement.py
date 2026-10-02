"""First-party learning activity; never accepts client-authored analytics payloads."""
from datetime import datetime, timedelta, timezone
from flask import abort, g, render_template


def register_measurement(app, db, query, event):
    def activity(lesson_id):
        # Called inside the same transaction as the learning action. Editors and
        # admins are excluded so preview/maintenance cannot inflate learner rates.
        if g.user['role'] != 'learner':
            return
        course_id = query('SELECT m.course_id FROM lessons l JOIN modules m ON m.id=l.module_id WHERE l.id=?', (lesson_id,), True)['course_id']
        inserted = db().execute('INSERT OR IGNORE INTO course_starts(user_id,course_id) VALUES(?,?)', (g.user['id'], course_id)).rowcount
        if inserted:
            event('course_started', lesson_id)
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
        return render_template('measurement.html', learners=learners, activated=activated,
            median=median, result_count=n, modules=modules, weeks=weeks, events=events)

    return activity
