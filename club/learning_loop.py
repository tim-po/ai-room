"""The loop around lessons: how far the learner got inside a lesson, the plan they chose (with a
calendar file whose events lead back to the next lesson), and the briefing shown when they return.

Storage is additive (two new tables) and created on first use, so no migration step is needed.
Progress here records only what the learner did (steps reached, a plan chosen); it never claims
learning from page visits.
"""
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone

from flask import abort, g, jsonify, request

from .legacy_content import outline

SCHEMA = (
    '''CREATE TABLE IF NOT EXISTS lesson_steps (
     user_id TEXT NOT NULL REFERENCES users(id), lesson_id TEXT NOT NULL REFERENCES lessons(id),
     furthest INTEGER NOT NULL, last INTEGER NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
     PRIMARY KEY(user_id,lesson_id))''',
    '''CREATE TABLE IF NOT EXISTS learning_plans (
     user_id TEXT PRIMARY KEY REFERENCES users(id), days TEXT NOT NULL, time TEXT NOT NULL,
     updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''',
)
WEEKDAYS = ('MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU')   # ISO weekday 1..7
SESSION_MINUTES = 20
AWAY_DAYS = 3   # a break this long turns the resume strip into a briefing


def checkpoints(lesson):
    """Titles of the lesson's steps (its h2 sections) plus practice, in reading order."""
    blocks = 'body_format' in lesson.keys() and lesson['body_format'] == 'blocks'
    titles = outline(lesson['body']) if blocks else []
    return titles + (['Практика'] if lesson['task'] else [])


def anchor(lesson, index):
    """Where checkpoint `index` (1-based) starts on the lesson page."""
    steps = len(checkpoints(lesson)) - (1 if lesson['task'] else 0)
    return f'#step-{index}' if index <= steps else '#practice'


def register_learning_loop(app, db, query, require_user, get_lesson, event):
    ready = set()

    def ensure():
        # Once per process and database, on a connection of its own: inside a request the shared
        # connection may already be in a transaction that never commits, taking the tables with it.
        key = app.config['DATABASE']
        if key in ready:
            return
        connection = sqlite3.connect(key, timeout=10)
        try:
            with connection:
                for statement in SCHEMA:
                    connection.execute(statement)
        finally:
            connection.close()
        ready.add(key)

    def step_progress(lesson_id):
        if not g.user:
            return None
        ensure()
        row = query('SELECT furthest,last,updated_at FROM lesson_steps WHERE user_id=? AND lesson_id=?', (g.user['id'], lesson_id), True)
        return dict(row) if row else None

    def record_step(lesson, step):
        """Section `step` (1-based) reached in an accessible lesson; keeps the furthest one."""
        total = len(checkpoints(lesson))
        if type(step) is not int or not 1 <= step <= total:
            abort(400, f'Номер раздела — целое число от 1 до {total}.')
        ensure()
        with db():
            db().execute('''INSERT INTO lesson_steps(user_id,lesson_id,furthest,last) VALUES(?,?,?,?)
                ON CONFLICT(user_id,lesson_id) DO UPDATE SET furthest=MAX(furthest,excluded.furthest),
                last=excluded.last,updated_at=CURRENT_TIMESTAMP''', (g.user['id'], lesson['id'], step, step))
        return step_progress(lesson['id'])

    @app.post('/api/lessons/<lesson_id>/step')
    @require_user
    def lesson_step(lesson_id):
        data = request.get_json(silent=True)
        return jsonify(record_step(get_lesson(lesson_id), data.get('step') if isinstance(data, dict) else None))

    # ---- Plan ----
    def plan():
        if not g.user:
            return None
        ensure()
        row = query('SELECT days,time FROM learning_plans WHERE user_id=?', (g.user['id'],), True)
        days = [int(d) for d in row['days'].split(',') if d] if row else []
        return dict(days=days, time=row['time'] if row else '19:00', minutes=SESSION_MINUTES)

    @app.get('/api/app/plan')
    @require_user
    def plan_api():
        return jsonify(plan())

    @app.put('/api/app/plan')
    @require_user
    def save_plan():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            abort(400)
        days, time = data.get('days'), data.get('time')
        if (not isinstance(days, list) or any(type(d) is not int or not 1 <= d <= 7 for d in days) or len(set(days)) != len(days)
                or not isinstance(time, str) or not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', time)):
            abort(400, 'Выберите дни недели и время в формате ЧЧ:ММ.')
        ensure()
        with db():
            db().execute('''INSERT INTO learning_plans(user_id,days,time) VALUES(?,?,?) ON CONFLICT(user_id)
                DO UPDATE SET days=excluded.days,time=excluded.time,updated_at=CURRENT_TIMESTAMP''',
                (g.user['id'], ','.join(str(d) for d in sorted(days)), time))
            # The plan is the weekly goal with days attached: no days means "when it suits me".
            db().execute('UPDATE users SET weekly_goal=? WHERE id=?', (len(days), g.user['id']))
            event('plan_saved')
        return jsonify(plan())

    def fold(line):
        """RFC 5545: lines over 75 octets continue on the next line after a space."""
        out, chunk = [], ''
        for char in line:
            if len((chunk + char).encode()) > (75 if not out else 74):
                out.append(chunk)
                chunk = ''
            chunk += char
        out.append(chunk)
        return '\r\n '.join(out)

    def text(value):
        return value.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')

    @app.get('/plan.ics')
    @require_user
    def plan_calendar():
        current = plan()
        if not current['days']:
            abort(404, 'Сначала выберите дни занятий.')
        hour, minute = (int(x) for x in current['time'].split(':'))
        today = datetime.now(timezone.utc).date()
        first = next(today + timedelta(days=i) for i in range(7) if (today + timedelta(days=i)).isoweekday() in current['days'])
        start = datetime(first.year, first.month, first.day, hour, minute)
        end = start + timedelta(minutes=SESSION_MINUTES)
        link = (app.config.get('PUBLIC_URL') or request.host_url).rstrip('/') + '/continue'
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        # Floating local times (no time zone): "Tuesday 19:00" stays 19:00 wherever the learner is.
        lines = [
            'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//AI Room//Learning plan//RU', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
            'BEGIN:VEVENT', f'UID:plan-{g.user["id"]}@{request.host.split(":")[0]}', f'DTSTAMP:{stamp}',
            f'SEQUENCE:{int(datetime.now(timezone.utc).timestamp())}',
            f'DTSTART:{start:%Y%m%dT%H%M%S}', f'DTEND:{end:%Y%m%dT%H%M%S}',
            'RRULE:FREQ=WEEKLY;BYDAY=' + ','.join(WEEKDAYS[d - 1] for d in current['days']),
            'SUMMARY:' + text(f'AI Room: урок (~{SESSION_MINUTES} минут)'),
            'DESCRIPTION:' + text(f'Продолжить с того места, где вы остановились: {link}'),
            f'URL:{link}',
            'BEGIN:VALARM', 'ACTION:DISPLAY', 'TRIGGER:PT0M', 'DESCRIPTION:' + text('Время для урока AI Room'), 'END:VALARM',
            'END:VEVENT', 'END:VCALENDAR',
        ]
        with db():
            event('plan_calendar')
        response = app.response_class('\r\n'.join(fold(l) for l in lines) + '\r\n', mimetype='text/calendar')
        response.headers['Content-Disposition'] = 'attachment; filename="ai-room-plan.ics"'
        return response

    # ---- Return briefing ----
    def briefing(unfinished):
        """Where the learner stopped, for the resume strip; after a break of AWAY_DAYS or more it
        also carries a recap (the steps already done) and the saved work."""
        if not g.user or not unfinished:
            return None
        lesson = get_lesson(unfinished['lesson_id'], enforce=False)
        titles = checkpoints(lesson)
        progress = step_progress(lesson['id'])
        step = None
        url = unfinished['url'] + ('#practice' if unfinished['status'] == 'draft' else '')
        if titles and progress:
            index = min(progress['last'], len(titles))
            step = dict(index=index, total=len(titles), title=titles[index - 1])
            if unfinished['status'] != 'draft':
                url = unfinished['url'] + anchor(lesson, index)
        practice = query('SELECT body,status,updated_at FROM practice WHERE user_id=? AND lesson_id=?', (g.user['id'], lesson['id']), True)
        last_day = query('SELECT MAX(day) day FROM learning_days WHERE user_id=?', (g.user['id'],), True)['day']
        away = (datetime.now(timezone.utc).date() - date.fromisoformat(last_day)).days if last_day else None
        return dict(lesson_id=lesson['id'], title=lesson['title'], course=lesson['course_title'], status=unfinished['status'],
                    url=url, step=step, steps=titles, minutes=lesson['minutes'], away_days=away,
                    returning=away is not None and away >= AWAY_DAYS,
                    practice=dict(excerpt=practice['body'][:220], status=practice['status'], updated_at=practice['updated_at']) if practice else None)

    return dict(step_progress=step_progress, plan=plan, briefing=briefing, record_step=record_step)
