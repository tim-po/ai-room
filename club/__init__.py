import hmac
import mimetypes
import re
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

import click
from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, send_file, session, url_for
from markupsafe import Markup
from werkzeug.security import check_password_hash

from .legacy_content import FRAME_SOURCES, IMAGE_SOURCES

GOALS = {'essentials': 'Основы ИИ', 'work': 'ИИ для работы', 'agents': 'Агенты и автоматизация', 'build': 'Создание с ИИ'}


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config.from_mapping(
        DATABASE=os.environ.get('CLUB_DATABASE', str(Path(app.instance_path) / 'club.sqlite')),
        SECRET_KEY=os.environ.get('CLUB_SECRET_KEY'),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('CLUB_SECURE_COOKIE') == '1',
        PERMANENT_SESSION_LIFETIME=timedelta(days=7), MAX_CONTENT_LENGTH=64 * 1024,
        # Staging/demo only: lets a learner switch membership on and off without billing.
        DEMO_CHECKOUT=os.environ.get('CLUB_DEMO_CHECKOUT') == '1',
        # Public address for links that leave the site (assistant links, calendar events); the request's host otherwise.
        PUBLIC_URL=os.environ.get('CLUB_PUBLIC_URL'),
    )
    if config:
        app.config.update(config)
    app.json.ensure_ascii = False   # readable Russian in JSON (assistants read /api/agent/* raw)
    if not app.config['SECRET_KEY']:
        key_file = Path(app.instance_path) / 'session.key'
        if not key_file.exists():
            try:
                fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'w') as f:
                    f.write(secrets.token_hex(32))
            except FileExistsError:
                pass
        app.config['SECRET_KEY'] = key_file.read_text()

    from .spa import register_spa
    spa_shell = register_spa(app)

    def db():
        if 'db' not in g:
            g.db = sqlite3.connect(app.config['DATABASE'], timeout=10)
            g.db.row_factory = sqlite3.Row
            g.db.execute('PRAGMA foreign_keys=ON')
        return g.db

    @app.teardown_appcontext
    def close_db(_):
        if 'db' in g:
            g.db.close()

    def query(sql, args=(), one=False):
        rows = db().execute(sql, args).fetchall()
        return (rows[0] if rows else None) if one else rows

    def event(name, lesson_id=None):
        allowed = {'lesson_started', 'lesson_completed', 'practice_saved', 'practice_submitted', 'help_requested', 'onboarding_completed', 'course_started', 'meaningful_return',
                   'plan_saved', 'plan_calendar', 'session_connected', 'section_reached', 'continue_opened'}
        if name not in allowed:
            raise ValueError('Unsupported event')
        if g.user['role'] != 'learner':
            return
        db().execute('INSERT OR IGNORE INTO events(user_id,name,lesson_id) VALUES(?,?,?)', (g.user['id'], name, lesson_id))

    from .measurement import register_measurement
    learning_activity = register_measurement(app, db, query, event)

    def require_user(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not g.user:
                if request.path.startswith('/api/'):
                    abort(401)
                return redirect(url_for('login', next=request.path))
            return fn(*args, **kwargs)
        return wrapped

    # Learner pages from earlier iterations that now dead-end; their APIs stay available.
    retired_pages = {'/practice': '/profile#practice', '/challenges': '/', '/diagnostic': '/', '/routes': '/'}

    @app.before_request
    def retire_pages():
        if request.method == 'GET' and request.path in retired_pages:
            return redirect(retired_pages[request.path])

    @app.before_request
    def load_user():
        # Increase the limit only for teaching uploads, before form parsing.
        if request.endpoint == 'upload':
            request.max_content_length = app.config['TEACHING_UPLOAD_LIMIT'] + 64 * 1024
        # Connected assistants authenticate with their own key only: no cookies, so no CSRF to check.
        if attach['is_agent_request']() or oauth['is_machine_request']():
            attach['authenticate']()
            return
        g.user = query('SELECT * FROM users WHERE id=?', (session['user_id'],), True) if session.get('user_id') else None
        session.setdefault('csrf', secrets.token_hex(32))
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf', '')
            if not hmac.compare_digest(session['csrf'], token):
                abort(400, 'Сессия формы устарела. Обновите страницу и повторите действие.')

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data: " + IMAGE_SOURCES + "; media-src 'self'; frame-src " + FRAME_SOURCES + "; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        if request.endpoint == 'prototypes':
            response.headers['Content-Security-Policy'] = response.headers['Content-Security-Policy'].replace("style-src 'self'", "style-src 'self' 'unsafe-inline'")
        if not request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'private, no-store'
        return response

    @app.template_filter('plural_ru')
    def plural_ru(value, one, few, many):
        number = abs(int(value))
        return many if 11 <= number % 100 <= 14 else one if number % 10 == 1 else few if 2 <= number % 10 <= 4 else many

    @app.template_filter('human_time')
    def human_time(value):
        # Stored times are UTC; app.js rewrites the text into the viewer's local "сегодня в 14:05".
        try:
            moment = datetime.strptime(str(value)[:19], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        except ValueError:
            return value
        month = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'][moment.month - 1]
        return Markup('<time datetime="{}" data-local-time>{} {} {}</time>').format(moment.isoformat(), moment.day, month, moment.year)

    def weekly_completed():
        # First-completion history is immutable: retries and re-completion never add credit.
        return query("SELECT COUNT(*) n FROM events WHERE user_id=? AND name='lesson_completed' AND created_at>=datetime('now','-7 days') AND created_at<=datetime('now')", (g.user['id'],), True)['n'] if g.user else 0

    @app.context_processor
    def shared():
        return dict(user=g.user, csrf=session.get('csrf'), goals=GOALS, can_access=can_access)

    def can_access(lesson):
        return lesson['access'] == 'free' or bool(g.user and (g.user['entitlement'] == 'member' or g.user['role'] in ('editor', 'admin')))

    def get_course(course_id):
        course = query("SELECT * FROM courses WHERE id=? AND status='published'", (course_id,), True)
        if not course:
            abort(404)
        return course

    def lesson_list(course_id):
        return query('''SELECT l.id,l.title,l.minutes,l.access,l.video,l.module_id,m.title AS module_title,
            COALESCE(p.completed,0) AS completed FROM lessons l JOIN modules m ON l.module_id=m.id
            LEFT JOIN progress p ON p.lesson_id=l.id AND p.user_id=?
            WHERE m.course_id=? AND l.status='published' ORDER BY m.position,l.position,l.id''',
            (g.user['id'] if g.user else '', course_id))

    def get_lesson(lesson_id, enforce=True):
        row = query('''SELECT l.*,m.course_id,c.title AS course_title FROM lessons l
            JOIN modules m ON l.module_id=m.id JOIN courses c ON m.course_id=c.id
            WHERE l.id=? AND l.status='published' AND c.status='published' ''', (lesson_id,), True)
        if not row:
            abort(404)
        if enforce and not can_access(row):
            abort(403, 'Этот урок доступен участникам клуба. Можно вернуться к бесплатным урокам или обратиться за помощью по доступу.')
        return row

    from .learning_loop import register_learning_loop
    loop = register_learning_loop(app, db, query, require_user, get_lesson, event, learning_activity)

    def cards():
        from .tree import catalog_index
        index = catalog_index()
        results = []
        for c in query("SELECT * FROM courses WHERE status='published' ORDER BY id"):
            lessons = lesson_list(c['id'])
            known = index.get(c['id'], {})
            # topic/catalog_total keep library cards consistent with the map (same names, honest size).
            results.append(dict(c) | dict(total=len(lessons), done=sum(l['completed'] for l in lessons),
                minutes=sum(l['minutes'] for l in lessons), free=sum(l['access'] == 'free' for l in lessons),
                topic=known.get('topic') or GOALS.get(c['goal']), catalog_total=known.get('total') or len(lessons)))
        return results

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            # The app signs in with JSON (and then reloads, since the session and CSRF token change);
            # a plain form post still works.
            data = payload()
            email = str(data.get('email', '')).strip().lower()[:254]
            attempt = query('SELECT * FROM login_attempts WHERE identity=?', (email,), True)
            now = int(time.time())
            if attempt and attempt['failures'] >= 10 and now - attempt['window_start'] < 900:
                abort(429, 'Слишком много попыток. Попробуйте через 15 минут.')
            user = query('SELECT * FROM users WHERE email=?', (email,), True)
            if not user or not check_password_hash(user['password_hash'], str(data.get('password', ''))[:1024]):
                with db():
                    if not attempt or now - attempt['window_start'] >= 900:
                        db().execute('INSERT OR REPLACE INTO login_attempts VALUES(?,1,?)', (email, now))
                    else:
                        db().execute('UPDATE login_attempts SET failures=failures+1 WHERE identity=?', (email,))
                message = 'Не удалось войти. Проверьте почту и пароль.'
                if request.is_json:
                    return jsonify(error='Unauthorized', message=message), 401
                flash(message, 'error')
                return spa_shell(401)
            with db():
                db().execute('DELETE FROM login_attempts WHERE identity=?', (email,))
            pending_connection = session.get('oauth_request')   # an assistant waiting for consent (club/oauth.py)
            session.clear()
            session.update(user_id=user['id'], csrf=secrets.token_hex(32))
            if pending_connection:
                session['oauth_request'] = pending_connection
            session.permanent = True
            destination = request.args.get('next', '/')
            if not destination.startswith('/') or destination.startswith('//') or '\\' in destination:
                destination = '/'
            destination = onboarding_destination(user, destination)
            return jsonify(next=destination) if request.is_json else redirect(destination)
        return spa_shell()

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect(url_for('home'))

    def continuation_context():
        from .continuation import learning_continuation
        return learning_continuation(query, g.user)

    def home_data():
        courses = cards()
        goal = g.user['goal'] if g.user else 'essentials'
        course = next((c for c in courses if c['goal'] == goal), courses[0] if courses else None)
        continuation = continuation_context()
        unfinished = continuation['unfinished']
        next_lesson = get_lesson(unfinished['lesson_id']) if unfinished else None
        route = selected_route()
        if not next_lesson and route:
            candidate = route['next_step']
            if candidate and can_access(candidate):
                next_lesson = candidate
        elif not next_lesson and course:
            next_lesson = next((l for l in lesson_list(course['id']) if not l['completed'] and can_access(l)), None)
        from .tree import build_tree
        tree = build_tree(query, g.user, can_access, unfinished['lesson_id'] if unfinished else None)
        free_lessons = [dict(l, course=c['title'], topic=t['title']) for t in tree['topics'] for c in t['courses']
                        for m in c['modules'] for l in m['lessons'] if l['state'] == 'open'][:3] if not g.user else []
        return dict(tree=tree, continuation=continuation, free_lessons=free_lessons, briefing=loop['briefing'](unfinished),
                    next=dict(id=next_lesson['id'], title=next_lesson['title'], url='/lessons/' + next_lesson['id']) if next_lesson else None)

    def continue_url():
        data = home_data()
        return data['briefing']['url'] if data['briefing'] else data['next']['url'] if data['next'] else '/'

    @app.get('/continue')
    @require_user
    def continue_learning():
        # Calendar events and assistants link here: the next thing to do, resolved when the learner arrives.
        with db():
            event('continue_opened')
        return redirect(continue_url())

    @app.get('/')
    def home():
        return spa_shell()

    @app.get('/api/app/home')
    def home_api():
        return jsonify(home_data())

    def catalogue_data():
        from .materials import FORMATS
        q = request.args.get('q', '').strip()[:150].lower()
        goal = request.args.get('goal', '')
        level = request.args.get('level', '')
        tool = request.args.get('tool', '').strip()[:150].casefold()
        content_format = request.args.get('format', '')
        def matches(c):
            return ((not q or q in (c['title'] + c['description'] + c['tools']).lower())
                    and (not goal or c['goal'] == goal) and (not level or c['level'] == level)
                    and (not tool or tool in c['tools'].casefold()))
        courses = [c for c in cards() if matches(c)] if content_format in ('', 'course') else []
        # Discovery exposes metadata only, never member-only body, prompt or video references.
        materials = [m for m in query("""SELECT id,title,description,outcome,format,goal,level,tools,minutes,access
            FROM materials WHERE status='published' ORDER BY updated_at DESC,id""")
            if matches(m) and (not content_format or m['format'] == content_format)]
        from .tree import catalog_index
        published = {c['id'] for c in query("SELECT id FROM courses WHERE status='published'")}
        coming = [dict(id=i, **c) for i, c in catalog_index().items() if i not in published and c['title']
                  and (not q or q in c['title'].lower()) and not (goal or level or tool) and content_format in ('', 'course')]
        card = ('id', 'title', 'description', 'goal', 'level', 'topic', 'total', 'catalog_total', 'minutes', 'free', 'done')
        return dict(courses=[{k: c[k] for k in card} for c in courses], materials=[dict(m) for m in materials], coming=coming,
                    filters=dict(goals=list(GOALS.items()), levels=['Начальный', 'Продвинутый'],
                                 formats=[('course', 'Курс'), *FORMATS.items()]))

    @app.get('/catalogue')
    def catalogue():
        return spa_shell()

    @app.get('/api/app/catalogue')
    def catalogue_api():
        return jsonify(catalogue_data())

    def course_data(course_id):
        c = get_course(course_id)
        lessons = lesson_list(course_id)
        first = next((l for l in lessons if not l['completed'] and can_access(l)), None)
        favourite = g.user and query('SELECT 1 FROM favourites WHERE user_id=? AND course_id=?', (g.user['id'], course_id), True)
        started = bool(g.user and query('''SELECT 1 FROM progress p JOIN lessons l ON l.id=p.lesson_id JOIN modules m ON m.id=l.module_id
            WHERE p.user_id=? AND m.course_id=? UNION SELECT 1 FROM practice r JOIN lessons l ON l.id=r.lesson_id
            JOIN modules m ON m.id=l.module_id WHERE r.user_id=? AND m.course_id=?''', (g.user['id'], course_id) * 2, True))
        from .tree import course_outline
        outline = course_outline(query, g.user, can_access, course_id)
        info = {k: c[k] for k in ('id', 'title', 'outcome', 'level', 'goal', 'prerequisites', 'tools', 'author', 'updated_at')}
        return dict(course=info | dict(topic=outline['topic'] if outline else GOALS.get(c['goal'])),
                    # Courses outside the catalogue (synthetic fixtures) have no outline: the page lists lessons instead.
                    lessons=[dict(id=l['id'], title=l['title'], minutes=l['minutes'], access=l['access'], video=bool(l['video']),
                                  module_id=l['module_id'], module_title=l['module_title'], completed=bool(l['completed']),
                                  locked=not can_access(l)) for l in lessons],
                    first=dict(id=first['id'], title=first['title']) if first else None, started=started,
                    favourite=bool(favourite), outline=outline,
                    done=outline['done'] if outline else sum(l['completed'] for l in lessons),
                    minutes=sum(l['minutes'] for l in lessons))

    @app.get('/courses/<course_id>')
    def course(course_id):
        get_course(course_id)
        return spa_shell()

    @app.get('/api/app/courses/<course_id>')
    def course_api(course_id):
        return jsonify(course_data(course_id))

    def record_visit(lesson_id):
        with db():
            learning_activity(lesson_id, meaningful=False)
            inserted = db().execute('INSERT OR IGNORE INTO progress(user_id,lesson_id) VALUES(?,?)', (g.user['id'], lesson_id)).rowcount
            # Navigation is independent of video polling, practice and completion writes.
            # A per-user sequence preserves ordering even for visits in the same second.
            db().execute('''INSERT INTO lesson_visits(user_id,lesson_id,visit_order)
                VALUES(?,?,(SELECT COALESCE(MAX(visit_order),0)+1 FROM lesson_visits WHERE user_id=?))
                ON CONFLICT(user_id,lesson_id) DO UPDATE SET visit_order=excluded.visit_order''',
                (g.user['id'], lesson_id, g.user['id']))
            if inserted:
                event('lesson_started', lesson_id)

    def lesson_data(lesson_id):
        """Everything the lesson page shows. Locked lessons expose only their outline, never content."""
        from .legacy_content import outline as body_outline, render_blocks
        from .tree import course_outline
        lesson = get_lesson(lesson_id, enforce=False)
        blocks = lesson['body_format'] == 'blocks' if 'body_format' in lesson.keys() else False
        info = dict(id=lesson['id'], title=lesson['title'], objective=lesson['objective'], minutes=lesson['minutes'],
                    access=lesson['access'], steps=body_outline(lesson['body']) if blocks else [])
        course = dict(id=lesson['course_id'], title=lesson['course_title'])
        outline = course_outline(query, g.user, can_access, lesson['course_id'], lesson_id)
        lessons = lesson_list(lesson['course_id'])
        if not can_access(lesson):
            free = next((l for l in lessons if l['access'] == 'free'), None)
            return dict(locked=True, lesson=info, course=course, outline=outline,
                        entitlement=g.user['entitlement'] if g.user else None,
                        free_lesson=dict(id=free['id'], title=free['title']) if free else None)
        progress = practice = None
        if g.user:
            progress = query('SELECT completed,video_seconds FROM progress WHERE user_id=? AND lesson_id=?', (g.user['id'], lesson_id), True)
            practice = query('SELECT body,status,updated_at FROM practice WHERE user_id=? AND lesson_id=?', (g.user['id'], lesson_id), True)
        index = next(i for i, l in enumerate(lessons) if l['id'] == lesson_id)
        def neighbour(l):
            if not l:
                return None
            row = query('SELECT objective FROM lessons WHERE id=?', (l['id'],), True)
            return dict(id=l['id'], title=l['title'], locked=not can_access(l), minutes=l['minutes'], objective=row['objective'])
        video = None
        if lesson['video']:
            video = dict(url=url_for('media', lesson_id=lesson_id), type='video/mp4' if lesson['video'].endswith('.mp4') else 'video/webm',
                         fixture=lesson['video'] == 'fixture.webm')
        resources = [dict(id=r['id'], title=r['title'], kind=r['kind'], url=url_for('lesson_resource', resource_id=r['id']))
                     for r in query("SELECT id,title,kind FROM resources WHERE lesson_id=? AND status='published'", (lesson_id,))]
        if lesson['checklist'] and not blocks:
            resources.insert(0, dict(id='checklist', title='Чек-лист проверки результата', kind='text', url=f'/lessons/{lesson_id}/resources/checklist.txt'))
        info |= dict(body_html=str(render_blocks(lesson['body'])) if blocks else None,
                     paragraphs=None if blocks else lesson['body'].split('\n\n'),
                     prompt=lesson['prompt'], task=lesson['task'],
                     checklist=lesson['checklist'].split('\n') if lesson['checklist'] else [], video=video)
        from .learning_loop import checkpoints
        return dict(locked=False, lesson=info, course=course, outline=outline, resources=resources,
                    progress=dict(progress) if progress else None,
                    practice=dict(practice) | dict(via=attach['origin'](lesson_id)) if practice else None,
                    checkpoints=checkpoints(lesson), step_progress=loop['step_progress'](lesson_id), plan=loop['plan'](),
                    previous=neighbour(lessons[index - 1] if index else None),
                    following=neighbour(lessons[index + 1] if index + 1 < len(lessons) else None))

    @app.get('/lessons/<lesson_id>')
    def lesson(lesson_id):
        lesson = get_lesson(lesson_id, enforce=False)
        if not can_access(lesson):
            return spa_shell(403)
        if g.user:
            record_visit(lesson_id)
            g.recorded_visit = lesson_id   # the app skips its own visit call for this first load
        return spa_shell()

    @app.get('/api/app/lessons/<lesson_id>')
    def lesson_page_api(lesson_id):
        return jsonify(lesson_data(lesson_id))

    @app.post('/api/app/lessons/<lesson_id>/visit')
    @require_user
    def lesson_visit_api(lesson_id):
        if not can_access(get_lesson(lesson_id, enforce=False)):
            abort(403)
        record_visit(lesson_id)
        return jsonify(ok=True)

    @app.get('/api/lessons/<lesson_id>')
    def lesson_api(lesson_id):
        return jsonify(dict(get_lesson(lesson_id)))

    def payload():
        if request.is_json:
            value = request.get_json()
            if not isinstance(value, dict):
                abort(400)
            return value
        return request.form

    def saved_response(lesson_id, message):
        if request.is_json:
            return jsonify(ok=True)
        flash(message, 'success')
        return redirect(url_for('lesson', lesson_id=lesson_id))

    @app.post('/api/lessons/<lesson_id>/completion')
    @require_user
    def completion(lesson_id):
        get_lesson(lesson_id)
        value = payload().get('completed')
        if value not in ('0', '1', False, True):
            abort(400)
        completed = int(value)
        with db():
            learning_activity(lesson_id)
            old = query('SELECT completed FROM progress WHERE user_id=? AND lesson_id=?', (g.user['id'], lesson_id), True)
            db().execute('''INSERT INTO progress(user_id,lesson_id,completed) VALUES(?,?,?)
                ON CONFLICT(user_id,lesson_id) DO UPDATE SET completed=excluded.completed,updated_at=CURRENT_TIMESTAMP''', (g.user['id'], lesson_id, completed))
            if completed and (not old or not old['completed']):
                if not query("SELECT 1 FROM events WHERE user_id=? AND lesson_id=? AND name='lesson_completed'", (g.user['id'], lesson_id), True):
                    event('lesson_completed', lesson_id)
        return saved_response(lesson_id, 'Урок завершён. Прогресс сохранён.' if completed else 'Урок снова в работе.')

    @app.route('/api/lessons/<lesson_id>/practice', methods=['GET', 'POST'])
    @require_user
    def practice_api(lesson_id):
        lesson = get_lesson(lesson_id)
        if not lesson['task']:
            abort(404)
        if request.method == 'GET':
            row = query('SELECT body,status,updated_at FROM practice WHERE user_id=? AND lesson_id=?', (g.user['id'], lesson_id), True)
            return jsonify(dict(row) if row else None)
        data = payload()
        status = data.get('status', 'draft')
        store_practice(lesson_id, data.get('body'), status)
        with db():
            attach['clear_origin'](lesson_id)
        return saved_response(lesson_id, 'Результат сохранён.' if status == 'submitted' else 'Черновик сохранён.')

    def store_practice(lesson_id, body, status):
        """Validated practice save for the website and connected assistants."""
        lesson = get_lesson(lesson_id)
        if not lesson['task']:
            abort(404, 'В этом уроке нет практики.')
        if not isinstance(body, str) or not body.strip() or len(body) > 12000 or status not in ('draft', 'submitted'):
            abort(400, 'Введите результат до 12 000 символов и выберите допустимый статус.')
        with db():
            learning_activity(lesson_id)
            old = query('SELECT body,status FROM practice WHERE user_id=? AND lesson_id=?', (g.user['id'], lesson_id), True)
            db().execute('''INSERT INTO practice(user_id,lesson_id,body,status) VALUES(?,?,?,?)
                ON CONFLICT(user_id,lesson_id) DO UPDATE SET body=excluded.body,status=excluded.status,updated_at=CURRENT_TIMESTAMP''', (g.user['id'], lesson_id, body.strip(), status))
            if not old or old['body'] != body.strip() or old['status'] != status:
                event('practice_submitted' if status == 'submitted' else 'practice_saved', lesson_id)

    @app.post('/api/lessons/<lesson_id>/video')
    @require_user
    def video_progress(lesson_id):
        get_lesson(lesson_id)
        value = payload().get('seconds')
        if not isinstance(value, (int, float)) or not 0 <= value <= 86400:
            abort(400)
        with db():
            db().execute('''INSERT INTO progress(user_id,lesson_id,video_seconds) VALUES(?,?,?)
                ON CONFLICT(user_id,lesson_id) DO UPDATE SET video_seconds=excluded.video_seconds,updated_at=CURRENT_TIMESTAMP''', (g.user['id'], lesson_id, value))
        return jsonify(ok=True)

    @app.get('/lessons/<lesson_id>/resources/checklist.txt')
    def resource(lesson_id):
        lesson = get_lesson(lesson_id)
        response = app.response_class(lesson['title'] + '\n\n' + (lesson['checklist'] or 'Проверьте ответ AI по независимому источнику.'), mimetype='text/plain')
        response.headers['Content-Disposition'] = 'attachment; filename="practice-checklist.txt"'
        return response

    @app.get('/lessons/<lesson_id>/media')
    def media(lesson_id):
        lesson = get_lesson(lesson_id)
        if not lesson['video'] or not re.fullmatch(r'[A-Za-z0-9_.-]+\.(webm|mp4)', lesson['video']):
            abort(404, 'Видео пока недоступно. Используйте текст урока ниже.')
        if lesson_id.startswith('teaching-') and lesson['video'].startswith('teaching-'):
            source_id = lesson['video'][len('teaching-'):].rsplit('.', 1)[0]
            return app.view_functions['teaching_published_file'](lesson_id, source_id)
        path = Path(app.instance_path) / 'media' / lesson['video']
        if not path.exists():
            abort(404)
        return send_file(path, mimetype=mimetypes.guess_type(lesson['video'])[0], conditional=True)

    @app.get('/resources/<resource_id>')
    def lesson_resource(resource_id):
        resource = query("SELECT * FROM resources WHERE id=? AND status='published'", (resource_id,), True)
        if not resource:
            abort(404)
        get_lesson(resource['lesson_id'])
        if resource['kind'] == 'link':
            return redirect(resource['content'])
        response = app.response_class(resource['content'], mimetype='text/plain')
        response.headers['Content-Disposition'] = 'attachment; filename="lesson-resource.txt"'
        return response

    @app.post('/courses/<course_id>/favourite')
    @require_user
    def favourite(course_id):
        get_course(course_id)
        saved = payload().get('saved') in ('1', True)
        with db():
            if saved:
                db().execute('INSERT OR IGNORE INTO favourites VALUES(?,?)', (g.user['id'], course_id))
            else:
                db().execute('DELETE FROM favourites WHERE user_id=? AND course_id=?', (g.user['id'], course_id))
        return jsonify(favourite=saved) if request.is_json else redirect(url_for('course', course_id=course_id))

    @app.route('/preferences', methods=['GET', 'POST'])
    @require_user
    def preferences():
        if request.method == 'POST':
            data = {k: str(v) for k, v in payload().items()}
            if data.get('goal') not in GOALS or data.get('experience') not in ('beginner', 'experienced') or data.get('weekly_goal') not in ('0', '1', '2', '3', '4', '5', '6', '7'):
                abort(400)
            with db():
                db().execute('UPDATE users SET goal=?,experience=?,weekly_goal=?,onboarding_done=1 WHERE id=?', (data['goal'], data['experience'], int(data['weekly_goal']), g.user['id']))
                # Dismissing the prompt is not completing the questionnaire.
                # The partial unique index makes retries and later preference edits idempotent.
                event('onboarding_completed')
            if data['goal'] != g.user['goal'] or data['experience'] != g.user['experience']:
                choose_route_goal(data['goal'])
            if request.is_json:
                return jsonify(ok=True)
            flash('Настройки сохранены.', 'success')
            return redirect(url_for('profile'))
        return spa_shell()

    @app.get('/api/app/preferences')
    @require_user
    def preferences_api():
        return jsonify(goal=g.user['goal'], experience=g.user['experience'], weekly_goal=g.user['weekly_goal'], plan=loop['plan']())

    @app.post('/preferences/skip')
    @require_user
    def skip_preferences():
        with db():
            db().execute('UPDATE users SET onboarding_done=1 WHERE id=?', (g.user['id'],))
        return redirect(url_for('home'))

    def profile_data():
        practices = query('''SELECT p.lesson_id,p.body,p.status,p.updated_at,l.title,m.course_id FROM practice p JOIN lessons l ON l.id=p.lesson_id
            JOIN modules m ON m.id=l.module_id WHERE p.user_id=? ORDER BY p.updated_at DESC''', (g.user['id'],))
        favourites = query('''SELECT c.id,c.title FROM favourites f JOIN courses c ON c.id=f.course_id
            WHERE f.user_id=? AND c.status='published' ''', (g.user['id'],))
        started_ids = {row['course_id'] for row in query('''SELECT course_id FROM course_starts WHERE user_id=?
            UNION SELECT m.course_id FROM progress p JOIN lessons l ON l.id=p.lesson_id
                JOIN modules m ON m.id=l.module_id WHERE p.user_id=?
            UNION SELECT m.course_id FROM practice p JOIN lessons l ON l.id=p.lesson_id
                JOIN modules m ON m.id=l.module_id WHERE p.user_id=?''', (g.user['id'],) * 3)}
        brief = lambda l: dict(id=l['id'], title=l['title']) if l else None
        learning = []
        for c in cards():
            if c['id'] in started_ids:
                remaining = [l for l in lesson_list(c['id']) if not l['completed']]
                # next_locked explains a course whose next step is a club lesson instead of showing a bare button.
                learning.append(dict(id=c['id'], title=c['title'], done=c['done'], total=c['total'],
                                     next=brief(next((l for l in remaining if can_access(l)), None)),
                                     next_locked=brief(next((l for l in remaining if not can_access(l)), None))))
        completed = [c for c in learning if c['total'] and c['done'] == c['total']]
        material_favourites = query('''SELECT m.id,m.title FROM material_favourites f JOIN materials m ON m.id=f.material_id WHERE f.user_id=? AND m.status='published' ''', (g.user['id'],))
        user = g.user
        continuation = continuation_context()
        return dict(user=dict(name=user['name'], email=user['email'], entitlement=user['entitlement'], weekly_goal=user['weekly_goal']),
                    continuation=continuation, briefing=loop['briefing'](continuation['unfinished']), plan=loop['plan'](),
                    weekly=weekly_completed(),
                    practices=[dict(p) | dict(via=attach['origin'](p['lesson_id'])) for p in practices],
                    connections=attach['connections'](), active_courses=[c for c in learning if c not in completed],
                    completed_courses=completed, favourites=[dict(f) for f in favourites],
                    material_favourites=[dict(m) for m in material_favourites])

    @app.get('/profile')
    @require_user
    def profile():
        return spa_shell()

    @app.get('/api/app/profile')
    @require_user
    def profile_api():
        return jsonify(profile_data())

    def help_lesson():
        lesson_id = request.args.get('lesson') or None
        # Access recovery needs public context, never the protected lesson payload.
        lesson = query('''SELECT l.id,l.title FROM lessons l
            JOIN modules m ON m.id=l.module_id JOIN courses c ON c.id=m.course_id
            WHERE l.id=? AND l.status='published' AND c.status='published' ''',
            (lesson_id,), True) if lesson_id else None
        if lesson_id and not lesson:
            abort(404)
        return lesson

    @app.route('/help', methods=['GET', 'POST'])
    def help_page():
        lesson = help_lesson()
        if request.method == 'POST':
            if not g.user:
                abort(401)
            body = payload().get('body', '')
            body = body.strip() if isinstance(body, str) else ''
            if not body or len(body) > 4000:
                abort(400)
            with db():
                db().execute('INSERT INTO help_requests(user_id,lesson_id,body) VALUES(?,?,?)', (g.user['id'], lesson['id'] if lesson else None, body))
                event('help_requested', lesson['id'] if lesson else None)
            if request.is_json:
                return jsonify(ok=True)
            flash('Вопрос сохранён для администратора. Срок ответа пока не установлен.', 'success')
            return redirect(url_for('help_page'))
        return spa_shell()

    @app.get('/api/app/help')
    def help_api():
        lesson = help_lesson()
        tickets = []
        if g.user:
            # Answers live in support_responses once `flask init-support` has run.
            answered = query("SELECT 1 FROM sqlite_master WHERE type='table' AND name='support_responses'", one=True)
            for t in query('SELECT id,body,created_at,status FROM help_requests WHERE user_id=? ORDER BY id DESC', (g.user['id'],)):
                reply = answered and query('SELECT response,handled_at FROM support_responses WHERE ticket_id=? ORDER BY revision DESC LIMIT 1', (t['id'],), True)
                tickets.append(dict(t) | dict(response=reply['response'] if reply else None, handled_at=reply['handled_at'] if reply else None))
        return jsonify(lesson=dict(lesson) if lesson else None, tickets=tickets)

    @app.get('/admin')
    @require_user
    def admin():
        if g.user['role'] not in ('editor', 'admin'):
            abort(403)
        tickets = query('SELECT h.*,u.name,l.title FROM help_requests h JOIN users u ON u.id=h.user_id LEFT JOIN lessons l ON l.id=h.lesson_id ORDER BY h.id DESC')
        return render_template('admin.html', tickets=tickets)

    @app.get('/prototypes/')
    @app.get('/prototypes/<filename>')
    def prototypes(filename='index.html'):
        directory = os.environ.get('CLUB_PROTOTYPES_DIR')
        if not directory or filename not in ('index.html', 'app.js', 'style.css'):
            abort(404)
        path = Path(directory) / filename
        if not path.is_file():
            abort(404)
        if filename == 'index.html':
            return path.read_text().replace('href="/style.css"', 'href="/prototypes/style.css"').replace('src="/app.js"', 'src="/prototypes/app.js"')
        return send_file(path)

    @app.get('/health')
    def health():
        db().execute('SELECT 1 FROM users LIMIT 1')
        return jsonify(build=os.environ.get('CLUB_BUILD_ID', 'development'), status='ok', schema=query('PRAGMA user_version', one=True)[0])

    @app.errorhandler(400)
    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def error(err):
        if request.path.startswith('/api/') or request.path == '/mcp' or request.is_json:
            return jsonify(error=err.name, message=err.description), err.code
        return spa_shell(err.code, err)

    @app.cli.command('init-db')
    def init_db():
        db().executescript(Path(__file__).with_name('schema.sql').read_text())
        click.echo('Schema ready (version 6).')

    @app.cli.command('seed-routes')
    def seed_route_fixtures():
        from .route_seed import seed_routes
        with db():
            seed_routes(db())
        click.echo('Initial synthetic routes added; existing compositions preserved.')

    @app.cli.command('seed-materials')
    def seed_material_fixtures():
        from .material_seed import seed_materials
        with db():
            seed_materials(db())
        click.echo('Synthetic standalone materials added; existing content preserved.')

    @app.cli.command('seed')
    def seed():
        from .seed import seed_database
        seed_database(db())
        click.echo('Synthetic content and isolated accounts seeded. Existing learner data preserved.')

    from .legacy_content import register_legacy_content
    register_legacy_content(app, db)

    from .membership import register_membership
    register_membership(app, db, query, require_user, spa_shell)

    from .routes import register_routes
    selected_route, choose_route_goal = register_routes(app, db, query, can_access, require_user, GOALS)

    from .authoring import register_authoring
    register_authoring(app, db, query, GOALS)

    from .materials import register_materials
    register_materials(app, db, query, can_access, require_user, GOALS, spa_shell)

    from .skills import register_skills
    register_skills(app, db, query, require_user)

    from .challenge_ui import register_challenge_ui
    register_challenge_ui(app, require_user)

    from .teaching import register_teaching
    register_teaching(app, db, query)

    from .onboarding import register_onboarding
    onboarding_destination = register_onboarding(app, db, query, require_user, spa_shell)

    from .support_admin import register_support
    register_support(app, db, query, require_user)

    from .attach import register_attach
    attach = register_attach(app, db, query, require_user, get_lesson, event, loop, store_practice, continue_url, continuation_context)

    from .oauth import register_oauth
    oauth = register_oauth(app, db, query, require_user, spa_shell, event)

    return app
