import hmac
import mimetypes
import re
import os
import secrets
import sqlite3
import time
from datetime import timedelta
from functools import wraps
from pathlib import Path

import click
from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash

GOALS = {'essentials': 'Основы AI', 'work': 'AI для работы', 'agents': 'Агенты и автоматизация', 'build': 'Создание с AI'}


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config.from_mapping(
        DATABASE=os.environ.get('CLUB_DATABASE', str(Path(app.instance_path) / 'club.sqlite')),
        SECRET_KEY=os.environ.get('CLUB_SECRET_KEY'),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('CLUB_SECURE_COOKIE') == '1',
        PERMANENT_SESSION_LIFETIME=timedelta(days=7), MAX_CONTENT_LENGTH=64 * 1024,
    )
    if config:
        app.config.update(config)
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
        allowed = {'lesson_started', 'lesson_completed', 'practice_saved', 'practice_submitted', 'help_requested', 'onboarding_completed', 'course_started', 'meaningful_return'}
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

    @app.before_request
    def load_user():
        # Increase the limit only for teaching uploads, before form parsing.
        if request.endpoint == 'upload':
            request.max_content_length = app.config['TEACHING_UPLOAD_LIMIT'] + 64 * 1024
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
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; media-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        if request.endpoint == 'prototypes':
            response.headers['Content-Security-Policy'] = response.headers['Content-Security-Policy'].replace("style-src 'self'", "style-src 'self' 'unsafe-inline'")
        if not request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'private, no-store'
        return response

    @app.template_filter('plural_ru')
    def plural_ru(value, one, few, many):
        number = abs(int(value))
        return many if 11 <= number % 100 <= 14 else one if number % 10 == 1 else few if 2 <= number % 10 <= 4 else many

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

    def cards():
        results = []
        for c in query("SELECT * FROM courses WHERE status='published' ORDER BY id"):
            lessons = lesson_list(c['id'])
            results.append(dict(c) | dict(total=len(lessons), done=sum(l['completed'] for l in lessons),
                minutes=sum(l['minutes'] for l in lessons), free=sum(l['access'] == 'free' for l in lessons)))
        return results

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()[:254]
            attempt = query('SELECT * FROM login_attempts WHERE identity=?', (email,), True)
            now = int(time.time())
            if attempt and attempt['failures'] >= 10 and now - attempt['window_start'] < 900:
                abort(429, 'Слишком много попыток. Попробуйте через 15 минут.')
            user = query('SELECT * FROM users WHERE email=?', (email,), True)
            if not user or not check_password_hash(user['password_hash'], request.form.get('password', '')[:1024]):
                with db():
                    if not attempt or now - attempt['window_start'] >= 900:
                        db().execute('INSERT OR REPLACE INTO login_attempts VALUES(?,1,?)', (email, now))
                    else:
                        db().execute('UPDATE login_attempts SET failures=failures+1 WHERE identity=?', (email,))
                flash('Не удалось войти. Проверьте почту и пароль.', 'error')
                return render_template('login.html'), 401
            with db():
                db().execute('DELETE FROM login_attempts WHERE identity=?', (email,))
            session.clear()
            session.update(user_id=user['id'], csrf=secrets.token_hex(32))
            session.permanent = True
            destination = request.args.get('next', '/')
            if not destination.startswith('/') or destination.startswith('//') or '\\' in destination:
                destination = '/'
            return redirect(destination)
        return render_template('login.html')

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect(url_for('home'))

    @app.get('/')
    def home():
        courses = cards()
        goal = g.user['goal'] if g.user else 'essentials'
        course = next((c for c in courses if c['goal'] == goal), courses[0] if courses else None)
        next_lesson = None
        if g.user:
            recent = query('''SELECT v.lesson_id FROM lesson_visits v JOIN lessons l ON l.id=v.lesson_id
                JOIN progress p ON p.lesson_id=v.lesson_id AND p.user_id=v.user_id
                JOIN modules m ON l.module_id=m.id JOIN courses c ON c.id=m.course_id
                WHERE v.user_id=? AND p.completed=0 AND l.status='published' AND c.status='published'
                AND (l.access='free' OR ?='member' OR ? IN ('editor','admin'))
                ORDER BY v.visit_order DESC LIMIT 1''', (g.user['id'], g.user['entitlement'], g.user['role']), True)
            if recent:
                next_lesson = get_lesson(recent['lesson_id'])
                course = next(c for c in courses if c['id'] == next_lesson['course_id'])
        route = selected_route()
        if route:
            floor = query('SELECT visit_floor FROM route_selections WHERE user_id=?', (g.user['id'],), True) if g.user else None
            recent_order = query('SELECT visit_order FROM lesson_visits WHERE user_id=? AND lesson_id=?',
                                 (g.user['id'], next_lesson['id']), True) if g.user and next_lesson else None
            if next_lesson and (next_lesson['id'] not in {step['id'] for step in route['steps']} or
                                (floor and recent_order and recent_order['visit_order'] <= floor['visit_floor'])):
                next_lesson = None
            if not next_lesson:
                next_lesson = route['next_step']
            if next_lesson:
                course = next(c for c in courses if c['id'] == next_lesson['course_id'])
        elif not next_lesson and course:
            next_lesson = next((l for l in lesson_list(course['id']) if not l['completed'] and can_access(l)), None)
        started = bool(g.user and next_lesson and query('SELECT 1 FROM lesson_visits WHERE user_id=? AND lesson_id=?', (g.user['id'],next_lesson['id']), True))
        saved = query('SELECT COUNT(*) n FROM practice WHERE user_id=?', (g.user['id'],), True)['n'] if g.user else 0
        return render_template('home.html', courses=courses, course=course, next_lesson=next_lesson, saved=saved, route=route, started=started, weekly=weekly_completed())

    @app.get('/catalogue')
    def catalogue():
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
        return render_template('catalogue.html', courses=courses, materials=materials)

    @app.get('/courses/<course_id>')
    def course(course_id):
        c = get_course(course_id)
        lessons = lesson_list(course_id)
        first = next((l for l in lessons if not l['completed'] and can_access(l)), None)
        favourite = g.user and query('SELECT 1 FROM favourites WHERE user_id=? AND course_id=?', (g.user['id'], course_id), True)
        return render_template('course.html', course=c, lessons=lessons, first=first, favourite=favourite)

    @app.get('/lessons/<lesson_id>')
    def lesson(lesson_id):
        lesson = get_lesson(lesson_id)
        progress = practice = None
        if g.user:
            with db():
                learning_activity(lesson_id)
                inserted = db().execute('INSERT OR IGNORE INTO progress(user_id,lesson_id) VALUES(?,?)', (g.user['id'], lesson_id)).rowcount
                # Navigation is independent of video polling, practice and completion writes.
                # A per-user sequence preserves ordering even for visits in the same second.
                db().execute('''INSERT INTO lesson_visits(user_id,lesson_id,visit_order)
                    VALUES(?,?,(SELECT COALESCE(MAX(visit_order),0)+1 FROM lesson_visits WHERE user_id=?))
                    ON CONFLICT(user_id,lesson_id) DO UPDATE SET visit_order=excluded.visit_order''',
                    (g.user['id'], lesson_id, g.user['id']))
                if inserted:
                    event('lesson_started', lesson_id)
            progress = query('SELECT * FROM progress WHERE user_id=? AND lesson_id=?', (g.user['id'], lesson_id), True)
            practice = query('SELECT * FROM practice WHERE user_id=? AND lesson_id=?', (g.user['id'], lesson_id), True)
        lessons = lesson_list(lesson['course_id'])
        index = next(i for i, l in enumerate(lessons) if l['id'] == lesson_id)
        route = selected_route() if g.user else None
        route_index = next((i for i, step in enumerate(route['steps']) if step['id'] == lesson_id), None) if route else None
        if route_index is None:
            route = None
        route_following = route['steps'][route_index+1] if route and route_index+1 < len(route['steps']) else None
        return render_template('lesson.html', lesson=lesson, lessons=lessons, progress=progress, practice=practice,
            route=route, route_index=route_index, route_following=route_following,
            previous=lessons[index-1] if index else None, following=lessons[index+1] if index+1 < len(lessons) else None,
            resources=query("SELECT id,title,kind FROM resources WHERE lesson_id=? AND status='published'", (lesson_id,)))

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
        body, status = data.get('body'), data.get('status', 'draft')
        if not isinstance(body, str) or not body.strip() or len(body) > 12000 or status not in ('draft', 'submitted'):
            abort(400, 'Введите результат до 12 000 символов и выберите допустимый статус.')
        with db():
            learning_activity(lesson_id)
            old = query('SELECT body,status FROM practice WHERE user_id=? AND lesson_id=?', (g.user['id'], lesson_id), True)
            db().execute('''INSERT INTO practice(user_id,lesson_id,body,status) VALUES(?,?,?,?)
                ON CONFLICT(user_id,lesson_id) DO UPDATE SET body=excluded.body,status=excluded.status,updated_at=CURRENT_TIMESTAMP''', (g.user['id'], lesson_id, body.strip(), status))
            if not old or old['body'] != body.strip() or old['status'] != status:
                event('practice_submitted' if status == 'submitted' else 'practice_saved', lesson_id)
        return saved_response(lesson_id, 'Результат сохранён.' if status == 'submitted' else 'Черновик сохранён.')

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
        with db():
            if request.form.get('saved') == '1':
                db().execute('INSERT OR IGNORE INTO favourites VALUES(?,?)', (g.user['id'], course_id))
            else:
                db().execute('DELETE FROM favourites WHERE user_id=? AND course_id=?', (g.user['id'], course_id))
        return redirect(url_for('course', course_id=course_id))

    @app.route('/preferences', methods=['GET', 'POST'])
    @require_user
    def preferences():
        if request.method == 'POST':
            data = request.form
            if data.get('goal') not in GOALS or data.get('experience') not in ('beginner', 'experienced') or data.get('weekly_goal') not in ('0', '1', '2', '3', '5'):
                abort(400)
            with db():
                db().execute('UPDATE users SET goal=?,experience=?,weekly_goal=?,onboarding_done=1 WHERE id=?', (data['goal'], data['experience'], int(data['weekly_goal']), g.user['id']))
                # Dismissing the prompt is not completing the questionnaire.
                # The partial unique index makes retries and later preference edits idempotent.
                event('onboarding_completed')
            if data['goal'] != g.user['goal'] or data['experience'] != g.user['experience']:
                choose_route_goal(data['goal'])
            flash('Настройки сохранены. Можно менять маршрут в любое время.', 'success')
            return redirect(url_for('home'))
        return render_template('preferences.html')

    @app.post('/preferences/skip')
    @require_user
    def skip_preferences():
        with db():
            db().execute('UPDATE users SET onboarding_done=1 WHERE id=?', (g.user['id'],))
        return redirect(url_for('home'))

    @app.get('/profile')
    @require_user
    def profile():
        practices = query('''SELECT p.*,l.title,m.course_id FROM practice p JOIN lessons l ON l.id=p.lesson_id
            JOIN modules m ON m.id=l.module_id WHERE p.user_id=? ORDER BY p.updated_at DESC''', (g.user['id'],))
        favourites = query('''SELECT c.* FROM favourites f JOIN courses c ON c.id=f.course_id
            WHERE f.user_id=? AND c.status='published' ''', (g.user['id'],))
        started_ids = {row['course_id'] for row in query('''SELECT course_id FROM course_starts WHERE user_id=?
            UNION SELECT m.course_id FROM progress p JOIN lessons l ON l.id=p.lesson_id
                JOIN modules m ON m.id=l.module_id WHERE p.user_id=?
            UNION SELECT m.course_id FROM practice p JOIN lessons l ON l.id=p.lesson_id
                JOIN modules m ON m.id=l.module_id WHERE p.user_id=?''', (g.user['id'],) * 3)}
        learning = [c for c in cards() if c['id'] in started_ids]
        completed_courses = [c for c in learning if c['total'] and c['done'] == c['total']]
        active_courses = [c for c in learning if c not in completed_courses]
        material_favourites = query('''SELECT m.id,m.title,m.format,m.access FROM material_favourites f JOIN materials m ON m.id=f.material_id WHERE f.user_id=? AND m.status='published' ''', (g.user['id'],))
        return render_template('profile.html', material_favourites=material_favourites, active_courses=active_courses, completed_courses=completed_courses, practices=practices, favourites=favourites, weekly=weekly_completed(), route=selected_route())

    @app.route('/help', methods=['GET', 'POST'])
    def help_page():
        lesson_id = request.args.get('lesson') or None
        # Access recovery needs public context, never the protected lesson payload.
        lesson = query('''SELECT l.id,l.title FROM lessons l
            JOIN modules m ON m.id=l.module_id JOIN courses c ON c.id=m.course_id
            WHERE l.id=? AND l.status='published' AND c.status='published' ''',
            (lesson_id,), True) if lesson_id else None
        if lesson_id and not lesson:
            abort(404)
        if request.method == 'POST':
            if not g.user:
                abort(401)
            body = request.form.get('body', '').strip()
            if not body or len(body) > 4000:
                abort(400)
            with db():
                db().execute('INSERT INTO help_requests(user_id,lesson_id,body) VALUES(?,?,?)', (g.user['id'], lesson_id, body))
                event('help_requested', lesson_id)
            flash('Вопрос сохранён для администратора. Срок ответа пока не установлен.', 'success')
            return redirect(url_for('help_page'))
        tickets = query('SELECT * FROM help_requests WHERE user_id=? ORDER BY id DESC', (g.user['id'],)) if g.user else []
        return render_template('help.html', lesson=lesson, tickets=tickets)

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
        if request.path.startswith('/api/'):
            return jsonify(error=err.name, message=err.description), err.code
        return render_template('error.html', error=err), err.code

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

    from .routes import register_routes
    selected_route, choose_route_goal = register_routes(app, db, query, can_access, require_user, GOALS)

    from .authoring import register_authoring
    register_authoring(app, db, query, GOALS)

    from .materials import register_materials
    register_materials(app, db, query, can_access, require_user, GOALS)

    from .skills import register_skills
    register_skills(app, db, query, require_user)

    from .teaching import register_teaching
    register_teaching(app, db, query)

    return app
