"""Ordered learning routes reference stable lessons and their existing progress."""
import uuid
from flask import abort, flash, g, redirect, render_template, request, url_for

STATUSES = {'draft': 'Черновик', 'published': 'Опубликован', 'archived': 'Архив'}


def register_routes(app, db, query, can_access, require_user, goals):
    def steps(identity, preview=False):
        # Only public metadata is selected; bodies and resources use lesson authorization.
        return query('''SELECT s.*,l.title,l.minutes,l.access,l.video,m.course_id,m.id module_id,m.title module_title,c.title course_title,
            COALESCE(p.completed,0) completed
            FROM route_steps s JOIN lessons l ON l.id=s.lesson_id
            JOIN modules m ON m.id=l.module_id JOIN courses c ON c.id=m.course_id
            LEFT JOIN progress p ON p.lesson_id=l.id AND p.user_id=?
            WHERE s.route_id=? AND (? OR (l.status='published' AND c.status='published'))
            ORDER BY s.position,s.lesson_id''', (g.user['id'] if g.user and not preview else '', identity, preview))

    def state(route, preview=False):
        route = dict(route)
        all_steps = steps(route['id'], preview)
        experienced = g.user and g.user['experience'] == 'experienced'
        visible = [dict(s) | {'id': s['lesson_id']} for s in all_steps if preview or not experienced or not s['beginner_only']]
        missing = query('SELECT COUNT(*) n FROM route_steps WHERE route_id=? AND (? OR beginner_only=0)',
                        (route['id'], preview or not experienced), True)['n'] - len(visible)
        pending = [s for s in visible if not s['completed']]
        next_step = next((s for s in pending if can_access(s)), None)
        selection = query('SELECT route_id,visit_floor FROM route_selections WHERE user_id=?',
                          (g.user['id'],), True) if g.user and not preview else None
        selected_id = selection['route_id'] if selection else None
        if g.user and not preview and not selected_id:
            fallback = query("SELECT id FROM learning_routes WHERE goal=? AND status='published' ORDER BY id LIMIT 1",
                             (g.user['goal'],), True)
            selected_id = fallback['id'] if fallback else None
        is_selected = selected_id == route['id']
        resume_step = next_step
        if is_selected:
            eligible = {s['id']: s for s in pending if can_access(s)}
            visits = query('SELECT lesson_id FROM lesson_visits WHERE user_id=? AND visit_order>? ORDER BY visit_order DESC',
                           (g.user['id'], selection['visit_floor'] if selection else 0))
            resume_step = next((eligible[v['lesson_id']] for v in visits if v['lesson_id'] in eligible), next_step)
        groups = []
        for number, step in enumerate(visible, 1):
            if not groups or groups[-1]['id'] != step['module_id']:
                groups.append(dict(id=step['module_id'], title=step['module_title'], course=step['course_title'],
                                   steps=[], start=number, current=False))
            groups[-1]['steps'].append(step)
            if resume_step and step['id'] == resume_step['id']:
                groups[-1]['current'] = True
        route.update(selected=is_selected, resume_step=resume_step, groups=groups, steps=visible, total=len(visible)+missing, done=sum(s['completed'] for s in visible),
                     missing=missing, next_step=next_step,
                     complete=bool(visible) and not pending and not missing,
                     blocked=bool(pending) and not next_step,
                     bridge=bool(next_step and next_step['beginner_only']))
        return route

    def selected():
        chosen = query('''SELECT r.* FROM learning_routes r JOIN route_selections s ON s.route_id=r.id
            WHERE s.user_id=? AND r.status='published' ''', (g.user['id'],), True) if g.user else None
        if not chosen:
            chosen = query("SELECT * FROM learning_routes WHERE goal=? AND status='published' ORDER BY id LIMIT 1",
                           (g.user['goal'] if g.user else 'essentials',), True)
        return state(chosen) if chosen else None

    def choose(identity):
        with db():
            db().execute('''INSERT INTO route_selections(user_id,route_id,visit_floor) VALUES(?,?,
                (SELECT COALESCE(MAX(visit_order),0) FROM lesson_visits WHERE user_id=?))
                ON CONFLICT(user_id) DO UPDATE SET route_id=excluded.route_id,visit_floor=excluded.visit_floor''',
                (g.user['id'], identity, g.user['id']))

    def choose_goal(goal):
        route = query("SELECT id FROM learning_routes WHERE goal=? AND status='published' ORDER BY id LIMIT 1", (goal,), True)
        if route:
            choose(route['id'])

    @app.get('/routes')
    def route_index():
        routes = [state(r) for r in query("SELECT * FROM learning_routes WHERE status='published' ORDER BY id")]
        return render_template('routes/index.html', routes=routes, selected=selected())

    @app.get('/routes/<identity>')
    def route_detail(identity):
        route = query("SELECT * FROM learning_routes WHERE id=? AND status='published'", (identity,), True)
        if not route:
            abort(404)
        return render_template('routes/detail.html', route=state(route), preview=False)

    @app.post('/routes/<identity>/select')
    @require_user
    def route_select(identity):
        route = query("SELECT * FROM learning_routes WHERE id=? AND status='published'", (identity,), True)
        if not route:
            abort(404)
        choose(identity)
        with db():
            db().execute('UPDATE users SET goal=? WHERE id=?', (route['goal'], g.user['id']))
        flash('Маршрут выбран. Уже завершённые уроки и практика сохранены.', 'success')
        return redirect(url_for('home'))

    def protect():
        if not g.user:
            abort(401)
        if g.user['role'] not in ('editor', 'admin'):
            abort(403)

    @app.get('/admin/routes')
    def route_admin():
        protect()
        return render_template('routes/admin.html', routes=query('SELECT * FROM learning_routes ORDER BY id'), statuses=STATUSES)

    @app.route('/admin/routes/new', methods=['GET', 'POST'])
    @app.route('/admin/routes/<identity>', methods=['GET', 'POST'])
    def route_edit(identity=None):
        protect()
        current = query('SELECT * FROM learning_routes WHERE id=?', (identity,), True) if identity else None
        if identity and not current:
            abort(404)
        error = None
        if request.method == 'POST':
            try:
                with db():
                    db().execute('BEGIN IMMEDIATE')
                    current = query('SELECT * FROM learning_routes WHERE id=?', (identity,), True) if identity else None
                    if current and str(current['revision']) != request.form.get('revision'):
                        abort(409, 'Маршрут изменён в другой вкладке. Скопируйте свои изменения и обновите страницу.')
                    data = {}
                    for key, limit in [('title',200),('outcome',2000),('explanation',2000),('owner',200)]:
                        data[key] = request.form.get(key, '').strip()
                        if not data[key] or len(data[key]) > limit:
                            raise ValueError('Заполните название, результат, объяснение и ответственного в пределах указанной длины.')
                    data['goal'] = request.form.get('goal')
                    data['status'] = request.form.get('status')
                    if data['goal'] not in goals or data['status'] not in STATUSES:
                        raise ValueError('Проверьте цель и статус маршрута.')
                    ids = request.form.getlist('lesson_id')
                    bridge_ids = request.form.getlist('bridge_id')
                    # Select rows define ordering; empty slots are ignored.
                    chosen = [value for value in ids if value]
                    if len(chosen) > 100 or len(set(chosen)) != len(chosen):
                        raise ValueError('До 100 разных уроков: один урок нельзя добавить дважды.')
                    if not set(bridge_ids).issubset(set(chosen)):
                        raise ValueError('Вводный шаг должен входить в маршрут.')
                    for lesson_id in chosen:
                        lesson = query('''SELECT l.status,c.status course_status FROM lessons l JOIN modules m ON m.id=l.module_id
                            JOIN courses c ON c.id=m.course_id WHERE l.id=?''', (lesson_id,), True)
                        if not lesson:
                            raise ValueError('Выберите существующие уроки.')
                        if data['status'] == 'published' and (lesson['status'] != 'published' or lesson['course_status'] != 'published'):
                            raise ValueError('Для публикации все шаги и их курсы должны быть опубликованы.')
                    if data['status'] == 'published' and (not chosen or set(chosen) == set(bridge_ids)):
                        raise ValueError('Добавьте хотя бы один основной шаг для всех уровней опыта.')
                    if current:
                        db().execute('UPDATE learning_routes SET '+','.join(k+'=?' for k in data)+',revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?', (*data.values(),identity))
                    else:
                        identity = 'route-'+uuid.uuid4().hex
                        db().execute('INSERT INTO learning_routes(id,'+','.join(data)+') VALUES('+','.join('?' for _ in range(len(data)+1))+')', (identity,*data.values()))
                    db().execute('DELETE FROM route_steps WHERE route_id=?', (identity,))
                    db().executemany('INSERT INTO route_steps(route_id,lesson_id,position,beginner_only) VALUES(?,?,?,?)',
                                     [(identity,lesson_id,index,int(lesson_id in bridge_ids)) for index,lesson_id in enumerate(chosen)])
                flash('Маршрут сохранён. Прогресс общих уроков сохранён.', 'success')
                return redirect(url_for('route_edit', identity=identity))
            except ValueError as exc:
                error = str(exc)
        items = query('''SELECT l.id,l.title,l.status,c.title course_title FROM lessons l JOIN modules m ON m.id=l.module_id
            JOIN courses c ON c.id=m.course_id ORDER BY c.title,m.position,l.position,l.id''')
        saved = steps(identity, True) if identity else []
        selected_ids = request.form.getlist('lesson_id') if error else [s['lesson_id'] for s in saved]
        bridges = request.form.getlist('bridge_id') if error else [s['lesson_id'] for s in saved if s['beginner_only']]
        return render_template('routes/edit.html', current=current, item=request.form if error else current,
                               selected_ids=selected_ids, bridges=bridges, lessons=items, statuses=STATUSES, error=error), 400 if error else 200

    @app.get('/admin/routes/<identity>/preview')
    def route_preview(identity):
        protect()
        route = query('SELECT * FROM learning_routes WHERE id=?', (identity,), True)
        if not route:
            abort(404)
        return render_template('routes/detail.html', route=state(route, True), preview=True)

    return selected, choose_goal
