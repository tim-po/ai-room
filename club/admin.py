"""The admin area: one React app under /admin (web/src/admin), fed by the JSON API below.

Editors and admins see content, the material library and learner questions; learners' accounts and
analytics are for admins only. Content that ships in the repository (the imported courses, lessons
and guides) is reinstalled on every deploy, but anything edited here is recorded in content_edits
and the installer leaves it alone from then on; «Вернуть версию из файлов» drops that record and
reinstalls the file version. Saves use the same optimistic revision check as the older server
editors: a change made in another tab is refused, never overwritten.
"""
import hashlib
import json
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from flask import abort, g, jsonify, redirect, request
from markupsafe import escape

from .authoring import STATUSES
from .legacy_content import CONTENT_EDITS, install
from .storage import additive_tables
from .tree import PLACEMENT_COLUMNS, PLACEMENTS, arrange, default_topic, load_catalog
from .materials import FORMATS

LEVELS = ('Начальный', 'Продвинутый')
ENTITLEMENTS = {'free': 'Бесплатный', 'member': 'Участник клуба', 'revoked': 'Доступ закрыт', 'expired': 'Истёк'}
ROLES = {'learner': 'Ученик', 'editor': 'Редактор', 'admin': 'Администратор'}
EVENTS = {'lesson_started': 'начал урок', 'lesson_completed': 'завершил урок', 'practice_submitted': 'сдал практику',
          'course_started': 'начал курс', 'help_requested': 'задал вопрос', 'meaningful_return': 'вернулся к учёбе',
          'onboarding_completed': 'прошёл знакомство'}
SPA_PAGES = ('', '/courses', '/courses/<identity>', '/lessons/<identity>', '/library', '/library/<identity>',
             '/learners', '/learners/<identity>', '/questions', '/works', '/analytics')
ADMIN_ONLY = ('learners', 'analytics')


RETIRED = (   # old server page -> its place in the admin app (admin_only: editors still get the old 403)
    (r'/admin/content/?', '/admin/courses', False), (r'/admin/content/courses/new', '/admin/courses/new', False),
    (r'/admin/content/courses/([A-Za-z0-9_.-]+)', '/admin/courses/{0}', False),
    (r'/admin/content/lessons/([A-Za-z0-9_.-]+)', '/admin/lessons/{0}', False),
    (r'/admin/content/modules/([A-Za-z0-9_.-]+)/lessons/new', '/admin/lessons/new?module={0}', False),
    (r'/admin/materials/?', '/admin/library', False), (r'/admin/materials/new', '/admin/library/new', False),
    (r'/admin/materials/([A-Za-z0-9_.-]+)', '/admin/library/{0}', False),
    (r'/admin/measurement', '/admin/analytics', True),
    (r'/admin/(?:workshop|assistant)', '/admin', False),   # drafting from materials: the admin's own assistant, on the overview
    (r'/admin/(?:tree|assessments|practice)', '/admin/works', False),   # the old skills engine; learners' results are in «Работы»
    (r'/admin/routes(?:/[A-Za-z0-9_.-]+)?', '/admin/courses', False),
)


class Invalid(ValueError):
    pass


def estimate(body, task=''):
    """Minutes for a lesson or material when the editor gives none: ~180 words a minute, plus practice."""
    words = len(re.findall(r'\w+', re.sub(r'!?\[[^\]]*\]\([^)]*\)|@video \S+', ' ', body or '')))
    return max(1, min(600, int(words / 180 + .5) + (5 if task else 0)))


def revision(row):
    return hashlib.sha256(json.dumps(dict(row), sort_keys=True, default=str).encode()).hexdigest()


def register_admin(app, db, query, shell, goals, managed):
    """managed() -> dict(courses=set, lessons=set, materials=set): ids installed from the repository."""
    ensure_edits = additive_tables(app, [CONTENT_EDITS])
    ensure_placements = additive_tables(app, [PLACEMENTS], PLACEMENT_COLUMNS)
    files = managed

    def managed():
        # Reading the content files once per request is enough.
        if 'admin_managed' not in g:
            g.admin_managed = files()
        return g.admin_managed
    MARKS = {'courses': ('course', 'structure'), 'lessons': ('lesson',), 'materials': ('material',)}

    def source(kind, identity):
        """None: made in the admin; 'files': installed and untouched; 'edited': installed, then changed here."""
        if identity not in managed()[kind]:
            return None
        ensure_edits()
        marks = MARKS[kind]
        edited = query(f"SELECT 1 FROM content_edits WHERE ref=? AND kind IN ({','.join('?' * len(marks))})", (identity, *marks), True)
        return 'edited' if edited else 'files'

    def mark(kind, identity):
        """Inside a save: from now on the deploy installer keeps this as edited here."""
        group = 'courses' if kind in ('course', 'structure') else kind + 's'
        if identity in managed()[group]:
            db().execute('''INSERT INTO content_edits(kind,ref,editor_id) VALUES(?,?,?) ON CONFLICT(kind,ref)
                DO UPDATE SET edited_at=CURRENT_TIMESTAMP,editor_id=excluded.editor_id''', (kind, identity, g.user['id']))

    def staff(admin_only=False):
        if not g.user:
            abort(401)
        if g.user['role'] not in ('editor', 'admin') or (admin_only and g.user['role'] != 'admin'):
            abort(403)

    def table(name):
        return bool(query("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,), True))

    def row(name, identity):
        value = query(f'SELECT * FROM {name} WHERE id=?', (identity,), True)
        if not value:
            abort(404)
        return value

    # ---- pages -------------------------------------------------------------------------------
    def page(identity=None):
        section = request.path.split('/')[2] if request.path.count('/') > 1 else ''
        staff(section in ADMIN_ONLY)
        return shell()

    for suffix in SPA_PAGES:
        app.add_url_rule('/admin' + suffix, 'admin_page' + suffix.replace('/', '_').replace('<identity>', 'item'), page)

    @app.before_request
    def retired_admin_pages():
        """The older server editors and tools now live in this app: an editor or admin opening an old
        address (a bookmark, a link in an old note) lands on its new place. Everyone else still gets the
        old page's own 401/403, and form posts, previews and media keep working as they were."""
        if request.method != 'GET' or not request.path.startswith('/admin/') or not g.get('user') or g.user['role'] not in ('editor', 'admin'):
            return None
        for pattern, target, admin_only in RETIRED:
            match = re.fullmatch(pattern, request.path)
            if match and (not admin_only or g.user['role'] == 'admin'):
                return redirect(target.format(*match.groups()))
        return None

    # ---- validation (same limits as the server editors) ---------------------------------------
    def payload():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            abort(400)
        return data

    def text(data, name, maximum, required=True, label=None):
        value = data.get(name)
        value = '' if value is None else value
        if not isinstance(value, str):
            raise Invalid(f'Поле «{label or name}» должно быть текстом.')
        value = value.strip()
        if len(value) > maximum or (required and not value):
            raise Invalid(f'«{label or name}»: ' + (f'от 1 до {maximum} символов.' if required else f'не больше {maximum} символов.'))
        return value

    def choice(data, name, values, label=None):
        value = data.get(name)
        if value not in values:
            raise Invalid(f'Выберите значение поля «{label or name}».')
        return value

    def minutes(data, body='', task=''):
        """An explicit duration, or (null/empty) an estimate: reading time plus five minutes for a practice task."""
        value = data.get('minutes')
        if value in (None, ''):
            return estimate(body, task)
        if type(value) is str and value.strip().isdigit():
            value = int(value)
        if type(value) is not int or not 1 <= value <= 600:
            raise Invalid('Длительность — целое число минут от 1 до 600.')
        return value

    def choice_or(data, name, values, default, label=None):
        return choice(data, name, values, label) if data.get(name) not in (None, '') else default

    def ready_to_publish(fields, required):
        """Drafts may be unfinished; publishing needs every field a learner will see."""
        if fields.get('status') != 'published':
            return
        missing = [label for name, label in required if not fields.get(name)]
        if missing:
            raise Invalid('Чтобы опубликовать, заполните: ' + ', '.join(missing) + '. Пока можно сохранить черновиком.')

    def media_names():
        directory = Path(app.instance_path) / 'media'
        return sorted(p.name for p in directory.glob('*') if p.is_file() and re.fullmatch(r'[A-Za-z0-9_.-]+\.(mp4|webm)', p.name))

    def video(data):
        value = text(data, 'video', 200, False) or None
        if value and value not in media_names():
            raise Invalid('Выберите установленный видеофайл.')
        return value

    def https_link(value):
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or any(ord(c) < 33 for c in value) or '\\' in value:
            raise Invalid('Ссылка должна быть HTTPS, без пароля и пробелов.')

    def check_revision(current, data):
        if data.get('revision') != revision(current):
            abort(409, 'Это изменили в другой вкладке или другой человек. Скопируйте свой текст и обновите страницу.')

    def saving(fn):
        """Runs fn() in one write transaction; validation problems become a 400 with the message.
        The additive tables a save may write are made first, on their own connection, never inside it."""
        ensure_edits()
        ensure_placements()
        try:
            with db():
                db().execute('BEGIN IMMEDIATE')
                return fn()
        except Invalid as exc:
            abort(400, str(exc))

    # ---- overview -----------------------------------------------------------------------------
    @app.get('/api/admin/overview')
    def admin_overview():
        staff()
        # The admin's own assistant lives on the overview (club/assist.py), for the person in the browser.
        assistant = app.extensions.get('assist_summary')
        return jsonify(overview() | (dict(assistant=assistant()) if assistant and not g.get('agent_session') else {}))

    def overview():
        one = lambda sql, *args: query(sql, args, True)[0]
        learners = "SELECT id FROM users WHERE role='learner'"
        counts = dict(
            learners=one(f"SELECT COUNT(*) FROM ({learners})"),
            members=one("SELECT COUNT(*) FROM users WHERE role='learner' AND entitlement='member'"),
            active_week=one(f"SELECT COUNT(DISTINCT user_id) FROM learning_days WHERE day>=date('now','-6 days') AND user_id IN ({learners})"),
            completions_week=one(f"SELECT COUNT(*) FROM events WHERE name='lesson_completed' AND created_at>=datetime('now','-7 days') AND user_id IN ({learners})"),
            open_questions=one("SELECT COUNT(*) FROM help_requests WHERE status='open'"),
            works_waiting=one(f"""SELECT COUNT(*) FROM practice p {'LEFT JOIN practice_reviews r ON r.user_id=p.user_id AND r.lesson_id=p.lesson_id' if table('practice_reviews') else ''}
                WHERE p.status='submitted' AND p.user_id IN ({learners}) {'AND (r.user_id IS NULL OR p.updated_at>r.updated_at)' if table('practice_reviews') else ''}"""),
            drafts=one("SELECT (SELECT COUNT(*) FROM courses WHERE status='draft')+(SELECT COUNT(*) FROM lessons WHERE status='draft')+(SELECT COUNT(*) FROM materials WHERE status='draft')"),
        )
        days = {r['day']: r['n'] for r in query(f"""SELECT day,COUNT(DISTINCT user_id) n FROM learning_days
            WHERE day>=date('now','-13 days') AND user_id IN ({learners}) GROUP BY day""")}
        today = date.fromisoformat(one("SELECT date('now')"))
        activity = [dict(day=d, learners=days.get(d, 0)) for d in
                    (date.fromordinal(today.toordinal() - i).isoformat() for i in range(13, -1, -1))]
        feed = [dict(r) | dict(action=EVENTS[r['name']]) for r in query(f"""SELECT e.id,e.name,e.created_at,u.id user_id,u.name user_name,
            l.id lesson_id,l.title lesson_title FROM events e JOIN users u ON u.id=e.user_id LEFT JOIN lessons l ON l.id=e.lesson_id
            WHERE u.role='learner' AND e.name IN ({','.join('?' * len(EVENTS))}) ORDER BY e.id DESC LIMIT 12""", tuple(EVENTS))]
        popular = [dict(r) for r in query(f"""SELECT l.id,l.title,c.title course_title,COUNT(*) completions FROM events e
            JOIN lessons l ON l.id=e.lesson_id JOIN modules m ON m.id=l.module_id JOIN courses c ON c.id=m.course_id
            WHERE e.name='lesson_completed' AND e.created_at>=datetime('now','-30 days') AND e.user_id IN ({learners})
            GROUP BY l.id ORDER BY completions DESC,l.title LIMIT 5""")]
        return dict(counts=counts, activity=activity, feed=feed, popular=popular, questions=questions(limit=4, open_only=True),
                    role=g.user['role'])

    # ---- courses, modules, lessons ------------------------------------------------------------
    def course_fields(data):
        fields = {k: text(data, k, limit, required, label) for k, limit, required, label in [
            ('title', 200, True, 'Название'), ('description', 2000, False, 'Описание'), ('outcome', 2000, False, 'Что получится'),
            ('tools', 1000, False, 'Инструменты'), ('prerequisites', 1000, False, 'Что нужно заранее'), ('author', 200, False, 'Автор')]}
        fields['author'] = fields['author'] or g.user['name']
        fields.update(goal=choice_or(data, 'goal', goals, next(iter(goals)), 'Цель'), level=choice_or(data, 'level', LEVELS, LEVELS[0], 'Уровень'),
                      status=choice_or(data, 'status', STATUSES, 'draft', 'Статус'))
        ready_to_publish(fields, [('description', 'описание'), ('outcome', 'что получится')])
        return fields

    def course_detail(identity):
        ensure_placements()
        course = row('courses', identity)
        modules = []
        for m in query('SELECT * FROM modules WHERE course_id=? ORDER BY position,id', (identity,)):
            lessons = [dict(id=l['id'], title=l['title'], status=l['status'], access=l['access'], minutes=l['minutes'],
                            completions=l['completions']) for l in query('''SELECT l.*,(SELECT COUNT(*) FROM progress p JOIN users u ON u.id=p.user_id
                            WHERE p.lesson_id=l.id AND p.completed=1 AND u.role='learner') completions FROM lessons l
                            WHERE module_id=? ORDER BY position,id''', (m['id'],))]
            modules.append(dict(id=m['id'], title=m['title'], lessons=lessons))
        return dict(course=dict(course), revision=revision(course), modules=modules, source=source('courses', identity), map=map_place(course),
                    learners=query("SELECT COUNT(*) n FROM course_starts s JOIN users u ON u.id=s.user_id WHERE s.course_id=? AND u.role='learner'", (identity,), True)['n'])

    def map_order():
        """Each topic's courses in map order (published ones and this admin's drafts aside): [(id, title, key)]."""
        published = {r['id']: r for r in query("SELECT * FROM courses WHERE status='published'")}
        titles = {r['id']: r['title'] for r in query('SELECT id,title FROM courses')}
        return {topic: [(e['id'], titles.get(e['id']) or e.get('title') or e['id'], e['order']) for e in entries]
                for topic, entries in arrange(query, published).items()}

    def map_place(course):
        """Where the course sits on the skill map (club/tree.py): topic or hidden, its place among the topic's
        courses (after: the course before it, '' for first), and the rank's name."""
        ensure_placements()
        catalog = load_catalog()
        home = next((t['id'] for t in catalog['topics'] for spec in t['courses'] if spec['id'] == course['id']), None)
        spec = next((spec for t in catalog['topics'] for spec in t['courses'] if spec['id'] == course['id']), {})
        place = query('SELECT * FROM course_placements WHERE course_id=?', (course['id'],), True)
        topic = 'hidden' if place and place['hidden'] else (place and place['topic_id']) or home or default_topic(course)
        order = map_order()
        here = [c[0] for c in order.get(topic, [])]
        after = here[here.index(course['id']) - 1] if course['id'] in here[1:] else '' if here[:1] == [course['id']] else (here[-1] if here else '')
        return dict(topic=topic, after=after, rank=(place and place['rank']) or spec.get('rank') or '',
                    topics=[dict(id=t['id'], title=t['title']) for t in catalog['topics']],
                    order={t: [dict(id=i, title=title) for i, title, _ in courses if i != course['id']] for t, courses in order.items()},
                    url=f"/map#course-{course['id']}")

    def place_on_map(identity, data):
        """Inside a save: map_topic ('hidden' to leave it off the map), map_after (the course it follows in its
        topic, '' for first) and rank, when the request names them."""
        if 'map_topic' not in data and 'rank' not in data and 'map_after' not in data:
            return
        topics = {t['id'] for t in load_catalog()['topics']}
        current = map_place(row('courses', identity))
        topic = data.get('map_topic', current['topic'])
        if topic not in topics | {'hidden'}:
            raise Invalid('Выберите раздел карты навыков.')
        rank = text(data, 'rank', 80, False, 'Звание') if 'rank' in data else current['rank']
        position = None
        if 'map_after' in data and topic != 'hidden':
            after = data['map_after'] or ''
            others = [c for c in map_order().get(topic, []) if c[0] != identity]
            keys = [c[2] for c in others]
            if after == '':
                position = (keys[0] - 1) if keys else 0.0
            else:
                at = next((i for i, c in enumerate(others) if c[0] == after), None)
                if at is None:
                    raise Invalid('Выберите курс, после которого стоять на карте.')
                position = (keys[at] + keys[at + 1]) / 2 if at + 1 < len(keys) else keys[at] + 1
        else:
            existing = query('SELECT position FROM course_placements WHERE course_id=?', (identity,), True)
            position = existing['position'] if existing and topic == current['topic'] else None
        db().execute("""INSERT INTO course_placements(course_id,topic_id,rank,hidden,position) VALUES(?,?,?,?,?) ON CONFLICT(course_id)
            DO UPDATE SET topic_id=excluded.topic_id,rank=excluded.rank,hidden=excluded.hidden,position=excluded.position""",
                     (identity, None if topic == 'hidden' else topic, rank or None, int(topic == 'hidden'), position))

    def options():
        return dict(goals=[dict(id=k, label=v) for k, v in goals.items()], levels=list(LEVELS),
                    statuses=[dict(id=k, label=v) for k, v in STATUSES.items()], formats=[dict(id=k, label=v) for k, v in FORMATS.items()],
                    media=media_names())

    def courses_list():
        return [dict(r) | dict(source=source('courses', r['id'])) for r in query("""SELECT c.id,c.title,c.status,c.goal,c.updated_at,
            (SELECT COUNT(*) FROM modules WHERE course_id=c.id) modules,
            (SELECT COUNT(*) FROM lessons l JOIN modules m ON m.id=l.module_id WHERE m.course_id=c.id) lessons,
            (SELECT COUNT(*) FROM lessons l JOIN modules m ON m.id=l.module_id WHERE m.course_id=c.id AND l.status='published') published,
            (SELECT COUNT(*) FROM course_starts s JOIN users u ON u.id=s.user_id WHERE s.course_id=c.id AND u.role='learner') learners
            FROM courses c ORDER BY CASE c.status WHEN 'published' THEN 0 WHEN 'draft' THEN 1 ELSE 2 END,c.updated_at DESC,c.id""")]

    def publishable_course(identity, fields):
        if fields['status'] == 'published' and (not identity or not query("""SELECT 1 FROM lessons l JOIN modules m ON m.id=l.module_id
                WHERE m.course_id=? AND l.status='published'""", (identity,), True)):
            raise Invalid('Чтобы опубликовать курс, нужен хотя бы один опубликованный урок. Пока сохраните его черновиком.')

    def with_current(current, data):
        """An update may name only the fields it changes (assistants do); the rest stay as they are.
        A revision, when given, must still match: someone else's save is never overwritten."""
        if 'revision' in data:
            check_revision(current, data)
        return {k: current[k] for k in current.keys()} | data

    def columns(name):
        if f'columns_{name}' not in g:
            g.setdefault(f'columns_{name}', {r[1] for r in query(f'PRAGMA table_info({name})')})
        return g.get(f'columns_{name}')

    def rich(values, name):
        """New lessons and materials use the Markdown subset the imported content uses (headings, lists,
        images, @video embeds), so the editor, the learner page and assistants all speak one format."""
        return values | dict(body_format='blocks') if 'body_format' in columns(name) else values

    def lesson_fields(data):
        fields = {k: text(data, k, limit, required, label) for k, limit, required, label in [
            ('title', 200, True, 'Название'), ('objective', 1000, False, 'Цель урока'), ('body', 24000, False, 'Текст урока'),
            ('prompt', 6000, False, 'Промпт'), ('task', 4000, False, 'Практика'), ('checklist', 4000, False, 'Критерии')]}
        fields.update(access=choice_or(data, 'access', ('free', 'member'), 'free', 'Доступ'),
                      status=choice_or(data, 'status', STATUSES, 'draft', 'Статус'),
                      minutes=minutes(data, fields['body'], fields['task']), video=video(data))
        if fields['task'] and not fields['checklist']:
            raise Invalid('У практики должны быть критерии успеха — каждый с новой строки.')
        ready_to_publish(fields, [('objective', 'цель урока'), ('body', 'текст урока')])
        return fields

    def lesson_detail(identity):
        lesson = row('lessons', identity)
        module = row('modules', lesson['module_id'])
        course = row('courses', module['course_id'])
        stats = query("""SELECT COUNT(*) started,SUM(p.completed) completed FROM progress p JOIN users u ON u.id=p.user_id
            WHERE p.lesson_id=? AND u.role='learner' """, (identity,), True)
        resources = [dict(r) for r in query('SELECT id,title,kind,content,status FROM resources WHERE lesson_id=? ORDER BY id', (identity,))]
        fields = {k: lesson[k] for k in ('id', 'title', 'objective', 'body', 'prompt', 'task', 'checklist', 'access', 'status', 'minutes', 'video')}
        fields['body_format'] = lesson['body_format'] if 'body_format' in lesson.keys() else 'text'
        return dict(lesson=fields, revision=revision(lesson), module=dict(id=module['id'], title=module['title']),
                    course=dict(id=course['id'], title=course['title']), source=source('lessons', identity),
                    resources=resources, stats=dict(started=stats['started'] or 0, completed=stats['completed'] or 0))

    def material_fields(data):
        fields = {k: text(data, k, limit, required, label) for k, limit, required, label in [
            ('title', 200, True, 'Название'), ('description', 2000, False, 'Описание'), ('outcome', 2000, False, 'Что получится'),
            ('tools', 1000, False, 'Инструменты'), ('prerequisites', 1000, False, 'Что нужно заранее'), ('author', 200, False, 'Автор'),
            ('body', 24000, False, 'Текст'), ('prompt', 6000, False, 'Промпт')]}
        fields['author'] = fields['author'] or g.user['name']
        fields.update(format=choice_or(data, 'format', FORMATS, 'guide', 'Формат'), goal=choice_or(data, 'goal', goals, next(iter(goals)), 'Цель'),
                      level=choice_or(data, 'level', LEVELS, LEVELS[0], 'Уровень'), access=choice_or(data, 'access', ('free', 'member'), 'free', 'Доступ'),
                      status=choice_or(data, 'status', STATUSES, 'draft', 'Статус'), minutes=minutes(data, fields['body']), video=video(data))
        ready_to_publish(fields, [('description', 'описание'), ('outcome', 'что получится'), ('body', 'текст')])
        return fields

    def material_detail(identity):
        item = row('materials', identity)
        fields = {k: item[k] for k in ('id', 'title', 'description', 'outcome', 'tools', 'prerequisites', 'author', 'body', 'prompt',
                                       'format', 'goal', 'level', 'access', 'status', 'minutes', 'video', 'updated_at')}
        fields['body_format'] = item['body_format'] if 'body_format' in item.keys() else 'text'
        saved = query('SELECT COUNT(*) n FROM material_favourites WHERE material_id=?', (identity,), True)['n']
        resources = [dict(r) for r in query('SELECT id,title,kind,content,status FROM material_resources WHERE material_id=? ORDER BY id', (identity,))]
        return dict(material=fields, revision=revision(item), source=source('materials', identity), saved=saved, resources=resources)

    # Operations: the JSON routes below and the assistant connection (club/assist.py) both call these.
    def create_course(data):
        def create():
            fields = course_fields(data)
            publishable_course(None, fields)
            identity = 'course-' + uuid.uuid4().hex
            db().execute('INSERT INTO courses(id,' + ','.join(fields) + ',updated_at) VALUES(?,' + ','.join('?' * len(fields)) + ',CURRENT_TIMESTAMP)',
                         (identity, *fields.values()))
            place_on_map(identity, data)
            return identity
        return course_detail(saving(create))

    def update_course(identity, data):
        def update():
            fields = course_fields(with_current(row('courses', identity), data))
            publishable_course(identity, fields)
            db().execute('UPDATE courses SET ' + ','.join(k + '=?' for k in fields) + ',updated_at=CURRENT_TIMESTAMP WHERE id=?', (*fields.values(), identity))
            mark('course', identity)
            place_on_map(identity, data)
        saving(update)
        return course_detail(identity)

    def add_module(course_id, title):
        def create():
            row('courses', course_id)
            db().execute('INSERT INTO modules(id,course_id,title,position) SELECT ?,?,?,COALESCE(MAX(position),0)+1 FROM modules WHERE course_id=?',
                         ('module-' + uuid.uuid4().hex, course_id, text(dict(title=title), 'title', 200, label='Название модуля'), course_id))
            db().execute('UPDATE courses SET updated_at=CURRENT_TIMESTAMP WHERE id=?', (course_id,))
            mark('structure', course_id)
        saving(create)
        return course_detail(course_id)

    def rename_module(module_id, title):
        module = row('modules', module_id)

        def rename():
            db().execute('UPDATE modules SET title=? WHERE id=?', (text(dict(title=title), 'title', 200, label='Название модуля'), module_id))
            mark('structure', module['course_id'])
        saving(rename)
        return course_detail(module['course_id'])

    def move(kind, identity, direction):
        if kind not in ('modules', 'lessons') or direction not in ('up', 'down'):
            abort(400, 'Укажите, что двигать (module или lesson) и куда (up или down).')
        parent = 'course_id' if kind == 'modules' else 'module_id'
        current = row(kind, identity)
        course_id = current['course_id'] if kind == 'modules' else row('modules', current['module_id'])['course_id']

        def swap():
            ids = [r['id'] for r in query(f'SELECT id FROM {kind} WHERE {parent}=? ORDER BY position,id', (current[parent],))]
            index = ids.index(identity)
            target = index + (-1 if direction == 'up' else 1)
            if 0 <= target < len(ids):
                ids[index], ids[target] = ids[target], ids[index]
                db().executemany(f'UPDATE {kind} SET position=? WHERE id=?', [(n, i) for n, i in enumerate(ids, 1)])
                mark('structure', course_id)
        saving(swap)
        return course_detail(course_id)

    def create_lesson(module_id, data):
        module = row('modules', module_id)

        def create():
            fields = lesson_fields(data)
            lesson_id = 'lesson-' + uuid.uuid4().hex
            position = query('SELECT COALESCE(MAX(position),0)+1 n FROM lessons WHERE module_id=?', (module_id,), True)['n']
            values = rich(dict(id=lesson_id, module_id=module_id, position=position) | fields, 'lessons')
            db().execute('INSERT INTO lessons(' + ','.join(values) + ') VALUES(' + ','.join('?' * len(values)) + ')', tuple(values.values()))
            db().execute('UPDATE courses SET updated_at=CURRENT_TIMESTAMP WHERE id=?', (module['course_id'],))
            return lesson_id
        return lesson_detail(saving(create))

    def update_lesson(identity, data):
        def update():
            current = row('lessons', identity)
            fields = lesson_fields(with_current(current, data))
            db().execute('UPDATE lessons SET ' + ','.join(k + '=?' for k in fields) + ' WHERE id=?', (*fields.values(), identity))
            mark('lesson', identity)
            db().execute('UPDATE courses SET updated_at=CURRENT_TIMESTAMP WHERE id=(SELECT course_id FROM modules WHERE id=?)', (current['module_id'],))
        saving(update)
        return lesson_detail(identity)

    def materials_list():
        return [dict(r) | dict(source=source('materials', r['id'])) for r in query("""SELECT m.id,m.title,m.format,m.status,m.access,
            m.minutes,m.updated_at,(SELECT COUNT(*) FROM material_favourites f WHERE f.material_id=m.id) saved FROM materials m
            ORDER BY CASE m.status WHEN 'published' THEN 0 WHEN 'draft' THEN 1 ELSE 2 END,m.updated_at DESC,m.id""")]

    def create_material(data):
        def create():
            fields = rich({'id': 'material-' + uuid.uuid4().hex} | material_fields(data), 'materials')
            db().execute('INSERT INTO materials(' + ','.join(fields) + ') VALUES(' + ','.join('?' * len(fields)) + ')', tuple(fields.values()))
            return fields['id']
        return material_detail(saving(create))

    def update_material(identity, data):
        def update():
            fields = material_fields(with_current(row('materials', identity), data))
            db().execute('UPDATE materials SET ' + ','.join(k + '=?' for k in fields) + ',updated_at=CURRENT_TIMESTAMP WHERE id=?', (*fields.values(), identity))
            mark('material', identity)
        saving(update)
        return material_detail(identity)

    RESTORE = {'courses': 'courses', 'lessons': 'lessons', 'library': 'materials', 'materials': 'materials'}

    def restore(section, identity):
        """Drops the edit record and reinstalls the repository version (published, as it ships)."""
        kind = RESTORE[section]
        if identity not in managed()[kind]:
            abort(404, 'Это сделано в админке: версии из файлов у него нет.')
        ensure_edits()

        def back():
            marks = MARKS[kind]
            db().execute(f"DELETE FROM content_edits WHERE ref=? AND kind IN ({','.join('?' * len(marks))})", (identity, *marks))
            install(db())
            db().execute(f"UPDATE {kind} SET status='published' WHERE id=?", (identity,))
        saving(back)
        return {'courses': course_detail, 'lessons': lesson_detail, 'materials': material_detail}[kind](identity)

    @app.post('/api/admin/preview')
    def admin_preview():
        """The text as the learner page renders it (club/legacy_content.py), unsaved edits included."""
        staff()
        data = payload()
        body = data.get('body')
        if not isinstance(body, str) or len(body) > 24000:
            abort(400)
        from .legacy_content import outline, render_blocks
        if data.get('body_format') == 'blocks':
            return jsonify(html=str(render_blocks(body)), steps=outline(body))
        return jsonify(html=''.join(f'<p>{escape(p)}</p>' for p in body.split('\n\n') if p.strip()), steps=[])

    # ---- JSON routes for the admin app ----------------------------------------------------------
    @app.get('/api/admin/courses')
    def admin_courses():
        staff()
        return jsonify(courses=courses_list(), options=options())

    @app.get('/api/admin/courses/<identity>')
    def admin_course(identity):
        staff()
        if identity == 'new':
            blank = dict(id=None, title='', description='', outcome='', tools='', prerequisites='', author=g.user['name'],
                         goal=next(iter(goals)), level=LEVELS[0], status='draft')
            ensure_placements()
            return jsonify(course=blank, revision='', modules=[], source=None, learners=0, options=options(),
                           map=map_place(dict(blank, id='')) | dict(url=None))
        return jsonify(course_detail(identity) | dict(options=options()))

    @app.post('/api/admin/courses')
    def admin_course_create():
        staff()
        return jsonify(create_course(payload()) | dict(options=options())), 201

    @app.put('/api/admin/courses/<identity>')
    def admin_course_update(identity):
        staff()
        return jsonify(update_course(identity, payload()) | dict(options=options()))

    @app.post('/api/admin/courses/<identity>/modules')
    def admin_module_create(identity):
        staff()
        return jsonify(add_module(identity, payload().get('title')))

    @app.put('/api/admin/modules/<identity>')
    def admin_module_rename(identity):
        staff()
        return jsonify(rename_module(identity, payload().get('title')))

    @app.post('/api/admin/<any(modules,lessons):kind>/<identity>/move')
    def admin_move(kind, identity):
        staff()
        return jsonify(move(kind, identity, payload().get('direction')))

    @app.get('/api/admin/lessons/<identity>')
    def admin_lesson(identity):
        staff()
        if identity == 'new':
            module = row('modules', request.args.get('module', ''))
            course = row('courses', module['course_id'])
            blank = dict(id=None, title='', objective='', body='', prompt='', task='', checklist='', access='free',
                         status='draft', minutes=10, video=None, body_format='blocks' if 'body_format' in columns('lessons') else 'text')
            return jsonify(lesson=blank, revision='', module=dict(id=module['id'], title=module['title']),
                           course=dict(id=course['id'], title=course['title']), source=None, resources=[],
                           stats=dict(started=0, completed=0), options=options())
        return jsonify(lesson_detail(identity) | dict(options=options()))

    @app.post('/api/admin/modules/<identity>/lessons')
    def admin_lesson_create(identity):
        staff()
        return jsonify(create_lesson(identity, payload()) | dict(options=options())), 201

    @app.put('/api/admin/lessons/<identity>')
    def admin_lesson_update(identity):
        staff()
        return jsonify(update_lesson(identity, payload()) | dict(options=options()))

    def resource_fields(data):
        title = text(data, 'title', 200, label='Название')
        kind = choice(data, 'kind', ('text', 'link'), 'Тип')
        content = text(data, 'content', 16000 if kind == 'text' else 2000, label='Содержимое')
        if kind == 'link':
            https_link(content)
        return title, kind, content

    RESOURCES = {'lessons': ('resources', 'lesson_id', 'resource-'), 'materials': ('material_resources', 'material_id', 'material-resource-')}

    def add_resource(kind, identity, data):
        """A link or a text file for a lesson or a material (kind 'lessons' or 'materials')."""
        name, parent, prefix = RESOURCES[kind]
        saving(lambda: db().execute(f'INSERT INTO {name}(id,{parent},title,kind,content) VALUES(?,?,?,?,?)',
                                    (prefix + uuid.uuid4().hex, row(kind, identity)['id'], *resource_fields(data))))
        return (lesson_detail if kind == 'lessons' else material_detail)(identity)

    def archive_resource(kind, identity):
        name, parent, _ = RESOURCES[kind]
        resource = row(name, identity)
        saving(lambda: db().execute(f"UPDATE {name} SET status='archived' WHERE id=?", (identity,)))
        return (lesson_detail if kind == 'lessons' else material_detail)(resource[parent])

    @app.post('/api/admin/lessons/<identity>/resources')
    def admin_lesson_resource(identity):
        staff()
        return jsonify(add_resource('lessons', identity, payload()) | dict(options=options()))

    @app.post('/api/admin/resources/<identity>/archive')
    def admin_resource_archive(identity):
        staff()
        return jsonify(archive_resource('lessons', identity) | dict(options=options()))

    @app.get('/api/admin/library')
    def admin_library():
        staff()
        return jsonify(items=materials_list(), options=options())

    @app.get('/api/admin/library/<identity>')
    def admin_material(identity):
        staff()
        if identity == 'new':
            blank = dict(id=None, title='', description='', outcome='', tools='', prerequisites='', author=g.user['name'], body='',
                         prompt='', format=request.args.get('format') if request.args.get('format') in FORMATS else 'guide',
                         goal=next(iter(goals)), level=LEVELS[0], access='free', status='draft', minutes=15, video=None,
                         updated_at=None, body_format='blocks' if 'body_format' in columns('materials') else 'text')
            return jsonify(material=blank, revision='', source=None, saved=0, resources=[], options=options())
        return jsonify(material_detail(identity) | dict(options=options()))

    @app.post('/api/admin/library')
    def admin_material_create():
        staff()
        return jsonify(create_material(payload()) | dict(options=options())), 201

    @app.put('/api/admin/library/<identity>')
    def admin_material_update(identity):
        staff()
        return jsonify(update_material(identity, payload()) | dict(options=options()))

    @app.post('/api/admin/library/<identity>/resources')
    def admin_material_resource(identity):
        staff()
        return jsonify(add_resource('materials', identity, payload()) | dict(options=options()))

    @app.post('/api/admin/library/resources/<identity>/archive')
    def admin_material_resource_archive(identity):
        staff()
        return jsonify(archive_resource('materials', identity) | dict(options=options()))

    @app.post('/api/admin/<any(courses,lessons,library):section>/<identity>/restore')
    def admin_restore(section, identity):
        staff()
        return jsonify(restore(section, identity) | dict(options=options()))

    # ---- learners (admins) ----------------------------------------------------------------------
    def learner_rows(where='', args=()):
        return [dict(r) for r in query(f'''SELECT u.id,u.name,u.email,u.role,u.entitlement,u.onboarding_done,
            (SELECT MAX(day) FROM learning_days d WHERE d.user_id=u.id) last_active,
            (SELECT COUNT(*) FROM progress p WHERE p.user_id=u.id AND p.completed=1) completed,
            (SELECT COUNT(*) FROM practice p WHERE p.user_id=u.id AND p.status='submitted') practice,
            (SELECT COUNT(*) FROM help_requests h WHERE h.user_id=u.id AND h.status='open') open_questions
            FROM users u {where} ORDER BY last_active IS NULL,last_active DESC,u.name''', args)]

    def learners(q=''):
        q = (q or '').strip()[:100]
        if not q:
            return learner_rows()
        like = '%' + q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        return learner_rows("WHERE u.name LIKE ? ESCAPE '\\' OR u.email LIKE ? ESCAPE '\\'", (like, like))

    @app.get('/api/admin/learners')
    def admin_learners():
        staff(True)
        q = request.args.get('q', '').strip()[:100]
        people = learners(q)
        return jsonify(learners=people, query=q, entitlements=ENTITLEMENTS, roles=ROLES,
                       totals=dict(query('SELECT COUNT(*) total,SUM(entitlement=\'member\') members FROM users WHERE role=\'learner\'', one=True)))

    def learner_detail(identity):
        person = learner_rows('WHERE u.id=?', (identity,))
        if not person:
            abort(404)
        courses = [dict(r) for r in query('''SELECT c.id,c.title,s.created_at started,
            (SELECT COUNT(*) FROM lessons l JOIN modules m ON m.id=l.module_id WHERE m.course_id=c.id AND l.status='published') total,
            (SELECT COUNT(*) FROM progress p JOIN lessons l ON l.id=p.lesson_id JOIN modules m ON m.id=l.module_id
              WHERE m.course_id=c.id AND p.user_id=s.user_id AND p.completed=1) done
            FROM course_starts s JOIN courses c ON c.id=s.course_id WHERE s.user_id=? ORDER BY s.created_at DESC''', (identity,))]
        ranks = [dict(r) for r in query("""SELECT ref course_id,level,earned_at FROM achievements WHERE user_id=? AND kind='rank'
            ORDER BY earned_at DESC""", (identity,))] if table('achievements') else []
        feed = [dict(r) | dict(action=EVENTS[r['name']]) for r in query(f'''SELECT e.id,e.name,e.created_at,l.id lesson_id,l.title lesson_title
            FROM events e LEFT JOIN lessons l ON l.id=e.lesson_id WHERE e.user_id=? AND e.name IN ({','.join('?' * len(EVENTS))})
            ORDER BY e.id DESC LIMIT 20''', (identity, *EVENTS))]
        days = query("SELECT COUNT(*) n FROM learning_days WHERE user_id=? AND day>=date('now','-29 days')", (identity,), True)['n']
        return dict(learner=person[0], courses=courses, ranks=ranks, feed=feed, days_month=days,
                    questions=[q for q in questions() if q['user_id'] == identity], entitlements=ENTITLEMENTS, roles=ROLES,
                    self=identity == g.user['id'])

    @app.get('/api/admin/learners/<identity>')
    def admin_learner(identity):
        staff(True)
        return jsonify(learner_detail(identity))

    @app.put('/api/admin/learners/<identity>')
    def admin_learner_update(identity):
        staff(True)
        data = payload()
        person = row('users', identity)
        entitlement = data.get('entitlement', person['entitlement'])
        role = data.get('role', person['role'])
        if entitlement not in ENTITLEMENTS or role not in ROLES:
            abort(400)
        if identity == g.user['id'] and role != person['role']:
            abort(409, 'Свою роль менять нельзя: так легко случайно потерять доступ к админке.')

        def update():
            db().execute('UPDATE users SET entitlement=?,role=? WHERE id=?', (entitlement, role, identity))
            if role != person['role']:
                # A changed role takes effect on the next request; nothing else about the account moves.
                app.logger.info('admin %s changed role of %s: %s -> %s', g.user['id'], identity, person['role'], role)
        saving(update)
        return jsonify(learner_detail(identity))

    # ---- questions ------------------------------------------------------------------------------
    def questions(limit=None, open_only=False):
        answered = table('support_responses')
        reply = '''(SELECT response FROM support_responses r WHERE r.ticket_id=h.id ORDER BY revision DESC LIMIT 1) response,
            (SELECT handled_at FROM support_responses r WHERE r.ticket_id=h.id ORDER BY revision DESC LIMIT 1) handled_at,
            (SELECT COALESCE(MAX(revision),0) FROM support_responses r WHERE r.ticket_id=h.id) revision''' if answered else \
            'NULL response,NULL handled_at,0 revision'
        rows = query(f'''SELECT h.id,h.body,h.created_at,h.status,u.id user_id,u.name user_name,u.entitlement,
            l.id lesson_id,l.title lesson_title,{reply} FROM help_requests h JOIN users u ON u.id=h.user_id
            LEFT JOIN lessons l ON l.id=h.lesson_id {"WHERE h.status='open'" if open_only else ''}
            ORDER BY h.status='open' DESC,h.id DESC {f'LIMIT {int(limit)}' if limit else ''}''')
        return [dict(r) for r in rows]

    @app.get('/api/admin/questions')
    def admin_questions():
        staff()
        return jsonify(questions=questions(), ready=table('support_responses'))

    # ---- analytics (admins) ---------------------------------------------------------------------
    def plain(value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: plain(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [plain(v) for v in value]
        if hasattr(value, 'keys'):
            return {k: plain(value[k]) for k in value.keys()}
        return value

    def analytics():
        data = plain(app.extensions['measurement_data']())
        data['loop']['features'] = [dict(label=label, learners=n) for label, n in data['loop']['features']]
        return data | dict(generated_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))

    @app.get('/api/admin/analytics')
    def admin_analytics():
        staff(True)
        return jsonify(analytics())

    # ---- search (the assistant's way to any course, lesson or material) -----------------------------
    def search(words, limit=30):
        """Courses, modules, lessons and materials whose title or text has every word (any case, any status)."""
        terms = [t for t in re.findall(r'\w+', (words or '').casefold())][:8]
        if not terms:
            abort(400, 'Что искать? Передайте слова из названия или текста.')
        found = []

        def hit(kind, item, title, *texts):
            haystack = ' '.join(t or '' for t in (title, *texts)).casefold()
            if all(t in haystack for t in terms):
                where = next((t for t in texts if t and terms[0] in t.casefold()), '')
                at = where.casefold().find(terms[0])
                snippet = ' '.join(where[max(0, at - 80):at + 120].split()) if where else ''
                found.append(dict(kind=kind, title=title, snippet=snippet, **item))
        for c in query('SELECT id,title,description,outcome,status FROM courses'):
            hit('course', dict(id=c['id'], status=c['status']), c['title'], c['description'], c['outcome'])
        for m in query('SELECT m.id,m.title,c.id course_id,c.title course_title FROM modules m JOIN courses c ON c.id=m.course_id'):
            hit('module', dict(id=m['id'], course_id=m['course_id'], course=m['course_title']), m['title'])
        for l in query('''SELECT l.id,l.title,l.objective,l.body,l.prompt,l.task,l.status,m.id module_id,m.title module_title,c.id course_id,
                c.title course_title FROM lessons l JOIN modules m ON m.id=l.module_id JOIN courses c ON c.id=m.course_id'''):
            hit('lesson', dict(id=l['id'], status=l['status'], module_id=l['module_id'], module=l['module_title'], course_id=l['course_id'],
                               course=l['course_title']), l['title'], l['objective'], l['body'], l['prompt'], l['task'])
        for m in query('SELECT id,title,description,outcome,body,format,status FROM materials'):
            hit('material', dict(id=m['id'], status=m['status'], format=m['format']), m['title'], m['description'], m['outcome'], m['body'])
        # Title matches first, then the rest in the order above.
        found.sort(key=lambda f: not all(t in f['title'].casefold() for t in terms))
        return found[:limit]

    def answer_question(ticket_id, response):
        """The same append-only answer the web inbox saves (support_responses); the learner sees it in Помощь."""
        if not table('support_responses'):
            abort(503, 'Хранилище ответов не подготовлено: flask --app club init-support.')
        if not isinstance(response, str) or not 1 <= len(response.strip()) <= 4000:
            abort(400, 'Ответ — от 1 до 4000 символов.')

        def save():
            if not query('SELECT 1 FROM help_requests WHERE id=?', (ticket_id,), True):
                abort(404, 'Вопрос не найден.')
            latest = query('SELECT COALESCE(MAX(revision),0) n FROM support_responses WHERE ticket_id=?', (ticket_id,), True)['n']
            db().execute('INSERT INTO support_responses(ticket_id,revision,response,handler_id) VALUES(?,?,?,?)',
                         (ticket_id, latest + 1, response.strip(), g.user['id']))
            db().execute("UPDATE help_requests SET status='handled' WHERE id=?", (ticket_id,))
        saving(save)
        return next(q for q in questions() if q['id'] == ticket_id)

    return dict(staff=staff, overview=overview, options=options, courses=courses_list, course=course_detail,
                create_course=create_course, update_course=update_course, add_module=add_module, rename_module=rename_module,
                move=move, lesson=lesson_detail, create_lesson=create_lesson, update_lesson=update_lesson,
                materials=materials_list, material=material_detail, create_material=create_material, update_material=update_material,
                restore=restore, questions=questions, answer_question=answer_question, add_resource=add_resource,
                archive_resource=archive_resource, search=search, learners=learners, learner=learner_detail, analytics=analytics)
