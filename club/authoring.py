"""Protected content authoring; learner routes never query drafts."""
import hashlib
import json
import mimetypes
import re
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for

STATUSES = {'draft': 'Черновик', 'published': 'Опубликован', 'archived': 'Архив'}


def register_authoring(app, db, query, goals):
    bp = Blueprint('authoring', __name__, url_prefix='/admin/content')

    @bp.before_request
    def protect():
        if not g.user:
            abort(401)
        if g.user['role'] not in ('editor', 'admin'):
            abort(403)

    def row(table, identity):
        value = query(f'SELECT * FROM {table} WHERE id=?', (identity,), True)
        if not value:
            abort(404)
        return value

    def revision(value):
        return hashlib.sha256(json.dumps(dict(value), sort_keys=True).encode()).hexdigest()

    def check_revision(value):
        if request.form.get('revision') != revision(value):
            abort(409, 'Материал изменён в другой вкладке. Откройте актуальную версию перед сохранением. Ваши данные можно скопировать, вернувшись назад.')

    def text(name, maximum=500, required=True):
        value = request.form.get(name, '').strip()
        if len(value) > maximum or (required and not value):
            raise ValueError(f'Поле «{name}»: требуется от {1 if required else 0} до {maximum} символов.')
        return value

    def choice(name, values):
        value = text(name)
        if value not in values:
            raise ValueError(f'Недопустимое значение поля «{name}».')
        return value

    def media_names():
        directory = Path(app.instance_path) / 'media'
        return sorted(p.name for p in directory.glob('*') if p.is_file() and p.suffix.lower() in ('.webm', '.mp4') and re.fullmatch(r'[A-Za-z0-9_.-]+', p.name))

    def validate_lesson():
        data = {k: text(k, limit, required) for k, limit, required in [
            ('title', 200, True), ('objective', 1000, True), ('body', 24000, True),
            ('prompt', 6000, False), ('task', 4000, False), ('checklist', 4000, False)]}
        data['access'] = choice('access', ('free', 'member'))
        data['status'] = choice('status', STATUSES)
        try:
            data['minutes'] = int(request.form.get('minutes', ''))
        except ValueError:
            raise ValueError('Укажите длительность целым числом минут.')
        if not 1 <= data['minutes'] <= 600:
            raise ValueError('Длительность должна быть от 1 до 600 минут.')
        data['video'] = text('video', 200, False) or None
        if data['video'] and data['video'] not in media_names():
            raise ValueError('Выберите установленный медиафайл. Неизвестные пути запрещены.')
        if data['task'] and not data['checklist']:
            raise ValueError('Добавьте критерии успешной практики, каждый с новой строки.')
        return data

    @bp.get('/')
    def index():
        courses = query('SELECT * FROM courses ORDER BY updated_at DESC,id')
        return render_template('authoring/index.html', courses=courses, statuses=STATUSES)

    @bp.route('/courses/new', methods=['GET', 'POST'])
    @bp.route('/courses/<identity>', methods=['GET', 'POST'])
    def course_edit(identity=None):
        current = row('courses', identity) if identity else None
        error = None
        if request.method == 'POST':
            try:
                with db():
                    # Reserve the write transaction before checking the revision.
                    db().execute('BEGIN IMMEDIATE')
                    if identity:
                        current = row('courses', identity)
                        check_revision(current)
                    data = {k: text(k, limit) for k, limit in [('title',200),('description',2000),('outcome',2000),('tools',1000),('prerequisites',1000),('author',200)]}
                    data['goal'] = choice('goal', goals)
                    data['level'] = choice('level', ('Начальный', 'Продвинутый'))
                    data['status'] = choice('status', STATUSES)
                    if data['status'] == 'published' and (not identity or not query("SELECT 1 FROM lessons l JOIN modules m ON m.id=l.module_id WHERE m.course_id=? AND l.status='published'", (identity,), True)):
                        raise ValueError('Перед публикацией курса добавьте хотя бы один опубликованный урок. Курс пока можно сохранить как черновик.')
                    if current:
                        db().execute('UPDATE courses SET '+','.join(k+'=?' for k in data)+',updated_at=CURRENT_TIMESTAMP WHERE id=?', (*data.values(), identity))
                    else:
                        identity = 'course-' + uuid.uuid4().hex
                        db().execute('INSERT INTO courses(id,'+','.join(data)+',updated_at) VALUES('+','.join('?' for _ in range(len(data)+1))+',CURRENT_TIMESTAMP)', (identity,*data.values()))
                flash('Курс сохранён. Статус: '+STATUSES[data['status']]+'.', 'success')
                return redirect(url_for('authoring.course_edit', identity=identity))
            except ValueError as exc:
                error = str(exc)
        modules = query('SELECT * FROM modules WHERE course_id=? ORDER BY position,id', (identity,)) if identity else []
        lessons = query('SELECT l.* FROM lessons l JOIN modules m ON m.id=l.module_id WHERE m.course_id=? ORDER BY l.position,l.id', (identity,)) if identity else []
        return render_template('authoring/course.html', item=request.form if error else current, current=current, revision=revision(current) if current else '', modules=modules, lessons=lessons, statuses=STATUSES, error=error), 400 if error else 200

    @bp.post('/courses/<identity>/modules')
    def module_create(identity):
        row('courses', identity)
        try:
            title = text('title', 200)
        except ValueError as exc:
            abort(400, str(exc))
        module_id = 'module-'+uuid.uuid4().hex
        with db():
            db().execute('INSERT INTO modules(id,course_id,title,position) SELECT ?,?,?,COALESCE(MAX(position),0)+1 FROM modules WHERE course_id=?', (module_id,identity,title,identity))
        flash('Модуль добавлен. Теперь добавьте урок.', 'success')
        return redirect(url_for('authoring.course_edit', identity=identity, _anchor=module_id))

    @bp.post('/modules/<identity>/rename')
    def module_rename(identity):
        current = row('modules', identity)
        try:
            title = text('title', 200)
        except ValueError as exc:
            abort(400, str(exc))
        with db():
            db().execute('UPDATE modules SET title=? WHERE id=?', (title,identity))
        flash('Название модуля сохранено.', 'success')
        return redirect(url_for('authoring.course_edit', identity=current['course_id'], _anchor=identity))

    @bp.post('/<kind>/<identity>/move')
    def move(kind, identity):
        if kind not in ('modules', 'lessons'):
            abort(404)
        direction = request.form.get('direction')
        if direction not in ('up', 'down'):
            abort(400)
        parent = 'course_id' if kind == 'modules' else 'module_id'
        with db():
            db().execute('BEGIN IMMEDIATE')
            current = row(kind, identity)
            siblings = query(f'SELECT id FROM {kind} WHERE {parent}=? ORDER BY position,id', (current[parent],))
            ids = [r['id'] for r in siblings]
            index = ids.index(identity)
            target = index + (-1 if direction == 'up' else 1)
            if 0 <= target < len(ids):
                ids[index], ids[target] = ids[target], ids[index]
                db().executemany(f'UPDATE {kind} SET position=? WHERE id=?', enumerate(ids, 1))
        course_id = current['course_id'] if kind == 'modules' else row('modules', current['module_id'])['course_id']
        flash('Порядок сохранён. Прогресс учеников сохранён.', 'success')
        return redirect(url_for('authoring.course_edit', identity=course_id, _anchor=identity))

    @bp.route('/modules/<module_id>/lessons/new', methods=['GET', 'POST'])
    @bp.route('/lessons/<identity>', methods=['GET', 'POST'])
    def lesson_edit(module_id=None, identity=None):
        current = row('lessons', identity) if identity else None
        module = row('modules', current['module_id'] if current else module_id)
        error = None
        if request.method == 'POST':
            try:
                data = validate_lesson()
                with db():
                    db().execute('BEGIN IMMEDIATE')
                    if current:
                        current = row('lessons', identity)
                        check_revision(current)
                        db().execute('UPDATE lessons SET '+','.join(k+'=?' for k in data)+' WHERE id=?', (*data.values(),identity))
                    else:
                        identity = 'lesson-'+uuid.uuid4().hex
                        position = query('SELECT COALESCE(MAX(position),0)+1 n FROM lessons WHERE module_id=?', (module['id'],), True)['n']
                        fields = dict(id=identity, module_id=module['id'], position=position) | data
                        db().execute('INSERT INTO lessons('+','.join(fields)+') VALUES('+','.join('?' for _ in fields)+')', tuple(fields.values()))
                    db().execute('UPDATE courses SET updated_at=CURRENT_TIMESTAMP WHERE id=?', (module['course_id'],))
                flash('Урок сохранён. Статус: '+STATUSES[data['status']]+'.', 'success')
                return redirect(url_for('authoring.lesson_edit', identity=identity))
            except ValueError as exc:
                error = str(exc)
        resources = query('SELECT * FROM resources WHERE lesson_id=? ORDER BY id', (identity,)) if identity else []
        return render_template('authoring/lesson.html', item=request.form if error else current, current=current, module=module, revision=revision(current) if current else '', statuses=STATUSES, error=error, media_names=media_names(), resources=resources), 400 if error else 200

    @bp.post('/lessons/<identity>/resources')
    def resource_create(identity):
        row('lessons', identity)
        try:
            title = text('title', 200)
            kind = choice('kind', ('text', 'link'))
            content = text('content', 16000 if kind == 'text' else 2000)
            if kind == 'link':
                parsed = urlsplit(content)
                if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or any(ord(c) < 33 for c in content) or '\\' in content:
                    raise ValueError('Ссылка должна быть HTTPS, без пароля и пробелов.')
        except ValueError as exc:
            abort(400, str(exc))
        with db():
            db().execute('INSERT INTO resources(id,lesson_id,title,kind,content) VALUES(?,?,?,?,?)', ('resource-'+uuid.uuid4().hex,identity,title,kind,content))
        flash('Материал добавлен. Для учеников действует доступ урока.', 'success')
        return redirect(url_for('authoring.lesson_edit', identity=identity))

    @bp.post('/resources/<identity>/archive')
    def resource_archive(identity):
        current = row('resources', identity)
        with db():
            db().execute("UPDATE resources SET status='archived' WHERE id=?", (identity,))
        flash('Материал перенесён в архив.', 'success')
        return redirect(url_for('authoring.lesson_edit', identity=current['lesson_id']))

    @bp.get('/lessons/<identity>/preview')
    def preview(identity):
        lesson = dict(row('lessons', identity))
        module = row('modules', lesson['module_id'])
        course = row('courses', module['course_id'])
        lesson.update(course_id=course['id'], course_title=course['title'])
        lessons = query('SELECT l.*,m.title module_title,0 completed FROM lessons l JOIN modules m ON m.id=l.module_id WHERE m.course_id=? ORDER BY m.position,l.position,l.id', (course['id'],))
        return render_template('lesson.html', lesson=lesson, lessons=lessons, progress=None, practice=None, previous=None, following=None, preview=True, resources=query("SELECT * FROM resources WHERE lesson_id=? AND status='published'", (identity,)))

    @bp.get('/lessons/<identity>/media')
    def preview_media(identity):
        lesson = row('lessons', identity)
        if lesson['video'] not in media_names():
            abort(404)
        return send_file(Path(app.instance_path) / 'media' / lesson['video'], mimetype=mimetypes.guess_type(lesson['video'])[0], conditional=True)

    @bp.get('/resources/<identity>/preview')
    def resource_preview(identity):
        resource = row('resources', identity)
        if resource['kind'] == 'link':
            return redirect(resource['content'])
        response = app.response_class(resource['content'], mimetype='text/plain')
        response.headers['Content-Disposition'] = 'attachment; filename="lesson-resource.txt"'
        return response

    app.register_blueprint(bp)
