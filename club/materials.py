"""Standalone guides, use cases and workshops with protected storage boundaries."""
import hashlib
import json
import mimetypes
import re
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, send_file, url_for

from .authoring import STATUSES

FORMATS = {'guide': 'Гайд', 'use_case': 'Кейс', 'workshop': 'Воркшоп'}


def register_materials(app, db, query, can_access, require_user, goals):
    bp = Blueprint('materials', __name__)

    def get(identity, preview=False):
        item = query('SELECT * FROM materials WHERE id=?' + ('' if preview else " AND status='published'"), (identity,), True)
        if not item:
            abort(404)
        if not preview and not can_access(item):
            abort(403, 'Материал доступен участникам клуба. Откройте бесплатные материалы в каталоге или обратитесь за помощью по доступу.')
        return item

    @bp.before_request
    def protect_editor():
        if request.path.startswith('/admin/materials'):
            if not g.user:
                abort(401)
            if g.user['role'] not in ('editor', 'admin'):
                abort(403)

    @app.context_processor
    def formats():
        return {'material_formats': FORMATS}

    def show(identity, preview=False):
        item = get(identity, preview)
        saved = position = None
        if g.user and not preview:
            saved = query('SELECT 1 FROM material_favourites WHERE user_id=? AND material_id=?', (g.user['id'], identity), True)
            position = query('SELECT seconds FROM material_video_positions WHERE user_id=? AND material_id=?', (g.user['id'], identity), True)
        resources = query("SELECT id,title,kind FROM material_resources WHERE material_id=? AND status='published' ORDER BY id", (identity,))
        return render_template('materials/detail.html', item=item, resources=resources, preview=preview, favourite=saved, seconds=position['seconds'] if position else 0)

    @bp.get('/materials/<identity>')
    def detail(identity):
        return show(identity)

    @bp.get('/api/materials/<identity>')
    def api(identity):
        return jsonify(dict(get(identity)))

    @bp.get('/admin/materials/<identity>/preview')
    def preview(identity):
        return show(identity, True)

    def media_names():
        return sorted(p.name for p in (Path(app.instance_path) / 'media').glob('*') if p.is_file() and re.fullmatch(r'[A-Za-z0-9_.-]+\.(mp4|webm)', p.name))

    @bp.get('/materials/<identity>/media')
    @bp.get('/admin/materials/<identity>/media')
    def media(identity):
        item = get(identity, request.path.startswith('/admin/'))
        if item['video'] not in media_names():
            abort(404, 'Видео недоступно. Прочитайте текст материала и попробуйте позже.')
        return send_file(Path(app.instance_path) / 'media' / item['video'], mimetype=mimetypes.guess_type(item['video'])[0], conditional=True)

    @bp.post('/api/materials/<identity>/video')
    @require_user
    def video_position(identity):
        item = get(identity)
        if not item['video']:
            abort(404)
        data = request.get_json(silent=True)
        value = data.get('seconds') if isinstance(data, dict) else None
        if type(value) not in (float, int) or not 0 <= value <= 86400:
            abort(400)
        with db():
            db().execute('''INSERT INTO material_video_positions(user_id,material_id,seconds) VALUES(?,?,?)
                ON CONFLICT(user_id,material_id) DO UPDATE SET seconds=excluded.seconds''', (g.user['id'], identity, value))
        return jsonify(ok=True)

    @bp.post('/materials/<identity>/favourite')
    @require_user
    def favourite(identity):
        get(identity)
        value = request.form.get('saved')
        if value not in ('0', '1'):
            abort(400)
        with db():
            if value == '1':
                db().execute('INSERT OR IGNORE INTO material_favourites VALUES(?,?)', (g.user['id'], identity))
            else:
                db().execute('DELETE FROM material_favourites WHERE user_id=? AND material_id=?', (g.user['id'], identity))
        return redirect(url_for('materials.detail', identity=identity))

    @bp.get('/material-resources/<identity>')
    @bp.get('/admin/materials/resources/<identity>/preview')
    def resource(identity):
        row = query("SELECT * FROM material_resources WHERE id=? AND status='published'", (identity,), True)
        if not row:
            abort(404)
        get(row['material_id'], request.path.startswith('/admin/'))
        if row['kind'] == 'link':
            return redirect(row['content'])
        response = app.response_class(row['content'], mimetype='text/plain')
        response.headers['Content-Disposition'] = 'attachment; filename="material-resource.txt"'
        return response

    def text(name, maximum=200, required=True):
        value = request.form.get(name, '').strip()
        if len(value) > maximum or (required and not value):
            raise ValueError(f'Поле «{name}»: требуется от {1 if required else 0} до {maximum} символов.')
        return value

    def choice(name, values):
        value = text(name)
        if value not in values:
            raise ValueError(f'Недопустимое значение поля «{name}».')
        return value

    def revision(row):
        return hashlib.sha256(json.dumps(dict(row), sort_keys=True).encode()).hexdigest()

    @bp.get('/admin/materials')
    def index():
        return render_template('materials/index.html', items=query('SELECT * FROM materials ORDER BY updated_at DESC,id'), statuses=STATUSES)

    @bp.route('/admin/materials/new', methods=['GET', 'POST'])
    @bp.route('/admin/materials/<identity>', methods=['GET', 'POST'])
    def edit(identity=None):
        current = get(identity, True) if identity else None
        error = None
        if request.method == 'POST':
            try:
                data = {key: text(key, limit, required) for key, limit, required in [
                    ('title',200,True), ('description',2000,True), ('outcome',2000,True),
                    ('tools',1000,True), ('prerequisites',1000,True), ('author',200,True),
                    ('body',24000,True), ('prompt',6000,False)]}
                data.update(format=choice('format',FORMATS), goal=choice('goal',goals),
                            level=choice('level',('Начальный','Продвинутый')), access=choice('access',('free','member')),
                            status=choice('status',STATUSES))
                try:
                    data['minutes'] = int(request.form.get('minutes',''))
                except ValueError:
                    raise ValueError('Укажите длительность целым числом минут.')
                if not 1 <= data['minutes'] <= 600:
                    raise ValueError('Длительность должна быть от 1 до 600 минут.')
                data['video'] = text('video',200,False) or None
                if data['video'] and data['video'] not in media_names():
                    raise ValueError('Выберите установленный медиафайл. Неизвестные пути запрещены.')
                with db():
                    db().execute('BEGIN IMMEDIATE')
                    if identity:
                        current = get(identity, True)
                        if request.form.get('revision') != revision(current):
                            abort(409, 'Материал изменён в другой вкладке. Скопируйте свой текст и откройте актуальную версию.')
                        db().execute('UPDATE materials SET '+','.join(k+'=?' for k in data)+',updated_at=CURRENT_TIMESTAMP WHERE id=?', (*data.values(),identity))
                    else:
                        identity = 'material-'+uuid.uuid4().hex
                        fields = {'id':identity} | data
                        db().execute('INSERT INTO materials('+','.join(fields)+') VALUES('+','.join('?' for _ in fields)+')', tuple(fields.values()))
                flash('Материал сохранён. Статус: '+STATUSES[data['status']]+'.', 'success')
                return redirect(url_for('materials.edit', identity=identity))
            except ValueError as exc:
                error = str(exc)
        resources = query('SELECT * FROM material_resources WHERE material_id=? ORDER BY id', (identity,)) if identity else []
        return render_template('materials/edit.html', item=request.form if error else current, current=current,
            revision=revision(current) if current else '', statuses=STATUSES, error=error, resources=resources, media_names=media_names()), 400 if error else 200

    @bp.post('/admin/materials/<identity>/resources')
    def add_resource(identity):
        get(identity, True)
        try:
            title = text('title')
            kind = choice('kind', ('text','link'))
            content = text('content',16000 if kind == 'text' else 2000)
            if kind == 'link':
                parsed = urlsplit(content)
                if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or any(ord(c)<33 for c in content) or '\\' in content:
                    raise ValueError('Ссылка должна быть HTTPS, без пароля и пробелов.')
        except ValueError as exc:
            abort(400, str(exc))
        with db():
            db().execute('INSERT INTO material_resources(id,material_id,title,kind,content) VALUES(?,?,?,?,?)', ('material-resource-'+uuid.uuid4().hex,identity,title,kind,content))
        flash('Ресурс добавлен. Доступ соответствует материалу.', 'success')
        return redirect(url_for('materials.edit', identity=identity))

    @bp.post('/admin/materials/resources/<identity>/archive')
    def archive_resource(identity):
        row = query('SELECT * FROM material_resources WHERE id=?',(identity,),True)
        if not row:
            abort(404)
        with db():
            db().execute("UPDATE material_resources SET status='archived' WHERE id=?",(identity,))
        flash('Ресурс перенесён в архив.', 'success')
        return redirect(url_for('materials.edit',identity=row['material_id']))

    app.register_blueprint(bp)
