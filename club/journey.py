"""The learner's own path (onboarding v2 and «Мой путь»): goals, starting level, deadlines and pace, and
the path club/paths.py builds from them.

Answers live in personal_paths (one JSON row per learner, created on first use). A goal written in the
learner's own words is kept as text only: analysing it into a personal path needs a subscription, and
the API says so (402) instead of pretending.
"""
import json
import math

from flask import abort, g, jsonify, request

from . import paths
from .storage import additive_tables

SCHEMA = ('''CREATE TABLE IF NOT EXISTS personal_paths (
    user_id TEXT PRIMARY KEY REFERENCES users(id), body TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''',)
MAX_GOALS = 3
DEADLINES = (4, 13, 26, 52)       # weeks: a month, three months, half a year, a year
# Self-assessment on the third step: three plain questions, 0–5, spread over the eight skills.
SLIDERS = {
    'chat': ('Работа с ChatGPT и Claude', {'dialog': 1, 'assistants': .8}),
    'code': ('Создание сайтов и сервисов с ИИ', {'vibecoding': 1, 'launch': .6}),
    'agents': ('Автоматизации и ИИ-агенты', {'automation': 1, 'agents': .8}),
    'media': ('Картинки и видео с ИИ', {'visual': 1, 'video': .7}),
}
# One per chosen goal, on the map and in the plan: CSS variables, so each theme has its own shades
# (web/src/journey.css: the club's lime, steel and sand; deeper, cleaner ones on light themes).
COLORS = ('var(--goal-1)', 'var(--goal-2)', 'var(--goal-3)')


def levels_from(answers):
    """Skill points from the sliders (each step of 0–5 is 20 points); a beginner starts at zero."""
    if answers.get('beginner', True):
        return {}
    points = {}
    for key, value in (answers.get('sliders') or {}).items():
        if key in SLIDERS and isinstance(value, (int, float)):
            for skill, weight in SLIDERS[key][1].items():
                points[skill] = max(points.get(skill, 0), round(max(0, min(5, value)) * 20 * weight))
    return points


def alignment(query, user):
    """What serves the learner's goals, for marking it across the platform («для цели …»): their goals with
    colours, and per course, lesson and guide the goals it serves. None without goals."""
    if not user or not query("SELECT 1 FROM sqlite_master WHERE type='table' AND name='personal_paths'", one=True):
        return None
    row = query('SELECT body FROM personal_paths WHERE user_id=?', (user['id'],), True)
    answers = json.loads(row['body']) if row else {}
    chosen = answers.get('goals') or []
    if not chosen:
        return None
    model = paths.model()
    path = paths.build_path(chosen, levels_from(answers), answers.get('deadlines') or {})
    courses, lessons = {}, {}
    for lesson in path['lessons']:
        for goal_id in lesson['goals']:
            courses.setdefault(lesson['course'], set()).add(goal_id)
            if lesson['lesson_id']:
                lessons.setdefault(lesson['lesson_id'], set()).add(goal_id)
    materials = {m['id']: [x for x in chosen if set(m['gains']) & set(model['goal_by_id'][x]['targets'])] for m in model.get('materials', [])}
    goals = [dict(id=x, title=model['goal_by_id'][x]['title'], color=COLORS[i % len(COLORS)]) for i, x in enumerate(chosen) if x in model['goal_by_id']]
    order = {x: i for i, x in enumerate(chosen)}
    tidy = lambda found: {k: sorted(v, key=order.get) for k, v in found.items() if v}
    return dict(goals=goals, course=tidy(courses), lesson=tidy(lessons), material=tidy(materials))


def register_journey(app, db, query, require_user, tree_for, shell):
    """tree_for(user) -> the map (club/tree.py build_tree) for real lesson titles, minutes and states."""
    ensure = additive_tables(app, SCHEMA)

    def saved(user_id):
        ensure()
        row = query('SELECT body,status FROM personal_paths WHERE user_id=?', (user_id,), True)
        return (json.loads(row['body']), row['status']) if row else ({}, 'new')

    def clean(data):
        """Validated answers: a request may send only some of them; the rest stay as saved."""
        model = paths.model()
        out = {}
        if 'goals' in data:
            goals = data['goals']
            if not isinstance(goals, list) or len(goals) > MAX_GOALS or len(set(goals)) != len(goals) or any(x not in model['goal_by_id'] for x in goals):
                abort(400, f'Выберите до {MAX_GOALS} целей из списка.')
            out['goals'] = goals
        if 'custom' in data:
            custom = data['custom'] if isinstance(data['custom'], str) else ''
            if len(custom) > 600:
                abort(400, 'Своя цель — до 600 символов.')
            out['custom'] = custom.strip()
        if 'beginner' in data:
            out['beginner'] = bool(data['beginner'])
        if 'sliders' in data:
            sliders = data['sliders'] if isinstance(data['sliders'], dict) else {}
            out['sliders'] = {k: max(0, min(5, int(v))) for k, v in sliders.items() if k in SLIDERS and isinstance(v, (int, float))}
        if 'deadlines' in data:
            deadlines = data['deadlines'] if isinstance(data['deadlines'], dict) else {}
            out['deadlines'] = {k: int(v) for k, v in deadlines.items() if k in model['goal_by_id'] and v in DEADLINES}
        if 'pace' in data:
            pace = data['pace'] if isinstance(data['pace'], dict) else {}
            sessions, minutes = pace.get('sessions'), pace.get('session_minutes')
            if not (isinstance(sessions, int) and 1 <= sessions <= 7 and isinstance(minutes, int) and 10 <= minutes <= 120):
                abort(400, 'Темп — от 1 до 7 занятий в неделю по 10–120 минут.')
            out['pace'] = dict(sessions=sessions, session_minutes=minutes)
        if 'step' in data:
            out['step'] = data['step'] if data['step'] in ('hello', 'goals', 'level', 'plan', 'done') else 'hello'
        return out

    def lesson_index(user, outline=None):
        """Real titles, minutes, links and states for the model's lessons, from the map."""
        index = {}
        tree = tree_for(user)
        if outline is not None:
            outline.extend(dict(id=t['id'], title=t['title'], courses=[dict(id=c['id'], title=c['title'], modules=len(c['modules'])) for c in t['courses']])
                           for t in tree['topics'])
        for topic in tree['topics']:
            for course in topic['courses']:
                for mi, module in enumerate(course['modules']):
                    for li, lesson in enumerate(module['lessons']):
                        index[f"{course['id']}:{mi}:{li}"] = dict(lesson, topic=topic['id'], course_title=course['title'], module_title=module['title'])
        return index

    def summary(answers, user):
        """Everything the onboarding and «Мой путь» draw: goals with colours, the lessons, modules per goal, plans."""
        model = paths.model()
        goals = answers.get('goals') or []
        outline = []
        index = lesson_index(user, outline)
        minutes = {k: v['minutes'] for k, v in index.items() if v.get('minutes')}
        # What the learner has already done counts as known: start from their levels plus their finished lessons.
        start = dict(paths.clamp_levels(levels_from(answers)))
        for lesson in model['lessons']:
            if index.get(lesson['key'], {}).get('state') == 'done':
                for skill, points in lesson['gains'].items():
                    start[skill] = min(paths.MAX, start[skill] + points)
        deadlines = answers.get('deadlines') or {}
        path = paths.build_path(goals, start, deadlines, minutes)
        colours = {goal_id: COLORS[i % len(COLORS)] for i, goal_id in enumerate(goals)}
        course_titles = {c['id']: c['title'] for t in outline for c in t['courses']}   # planned modules aren't on the map yet
        lessons = []
        for lesson in path['lessons']:
            real = index.get(lesson['key'], {})
            lessons.append(lesson | dict(lesson_id=real.get('id') or lesson['lesson_id'], title=real.get('title') or lesson['title'] or lesson['module_title'], url=real.get('url'),
                                         state=real.get('state', 'coming'), course_title=real.get('course_title') or course_titles.get(lesson['course']), topic=real.get('topic')))
        modules = {}
        for lesson in lessons:
            for goal_id in lesson['goals']:
                key = f"{lesson['course']}:{lesson['module']}"
                if key not in modules.setdefault(goal_id, []):
                    modules[goal_id].append(key)
        # What the path takes as known, by module («ты, вероятно, уже знаешь»).
        assumed = {}
        by_key = {l['key']: l for l in model['lessons']}
        for key in path['assumed']:
            lesson = by_key[key]
            module_key = f"{lesson['course']}:{lesson['module']}"
            real = index.get(key, {})
            entry = assumed.setdefault(module_key, dict(key=module_key, course=lesson['course'], module=lesson['module'],
                                                        title=real.get('module_title') or lesson['module_title'], course_title=real.get('course_title') or course_titles.get(lesson['course']),
                                                        lessons=0))
            entry['lessons'] += 1
        # Guides and use cases as side stops: those that train a skill a goal needs, beside the module they fit
        # (or the first module of that course on the path). Optional: they don't move a goal's progress.
        published = {r['id'] for r in query("SELECT id FROM materials WHERE status='published'")}
        on_path = [f"{l['course']}:{l['module']}" for l in lessons]
        guides = []
        for material in model.get('materials', []):
            if material['format'] not in ('guide', 'use_case'):
                continue   # workshops live in Обзор, not on the path or the map
            serves = [x for x in path['goals'] if set(material['gains']) & set(model['goal_by_id'][x]['targets'])]
            course = material['near'].split(':')[0]
            at = material['near'] if material['near'] in on_path else next((k for k in on_path if k.split(':')[0] == course), None)
            if material['id'] in published and serves and at:
                guides.append(dict(id=material['id'], title=material['title'], format=material['format'], minutes=material['minutes'],
                                   url=f"/materials/{material['id']}", module=at, goals=serves, club=bool(material.get('club'))))
        # At most three beside a module: free ones first, then those serving more goals.
        guides.sort(key=lambda x: (x['club'], -len(x['goals'])))
        per_module = {}
        guides = [x for x in guides if per_module.setdefault(x['module'], []).append(x) or len(per_module[x['module']]) <= 3]
        pace = answers.get('pace')
        line = paths.timeline(path, pace['sessions'] * pace['session_minutes']) if pace else None
        return dict(map=outline,
            goals=[dict(id=x, title=model['goal_by_id'][x]['title'], color=colours[x], reach=round(path['reach'][x], 3),
                        deadline=deadlines.get(x), lessons=sum(x in l['goals'] for l in lessons), modules=modules.get(x, []),
                        targets=model['goal_by_id'][x]['targets']) for x in path['goals']],
            lessons=lessons, guides=guides, assumed=list(assumed.values()), start=path['start'], end=path['end'], minutes=path['minutes'],
            coming=sum(l['state'] == 'coming' for l in lessons),
            plans=paths.plans(path, deadlines),
            timeline=line['done'] if line else None,
            pace=dict(pace, minutes_per_week=pace['sessions'] * pace['session_minutes'], weeks=math.ceil(line['weeks']),
                      reached={k: math.ceil(v) for k, v in line['reached'].items()}) if line else None)

    def options():
        model = paths.model()
        return dict(skills=model['skills'], goals=[dict(id=x['id'], title=x['title'], text=x['text'], targets=x['targets']) for x in model['goals']],
                    sliders=[dict(id=k, title=v[0]) for k, v in SLIDERS.items()], deadlines=list(DEADLINES), max_goals=MAX_GOALS)

    @app.get('/path')
    @require_user
    def path_page():
        return shell()

    @app.get('/api/app/journey')
    @require_user
    def journey_api():
        answers, status = saved(g.user['id'])
        return jsonify(options=options(), answers=answers, status=status,
                       path=summary(answers, g.user) if answers.get('goals') else None)

    @app.post('/api/app/journey/preview')
    @require_user
    def journey_preview():
        """The path for answers not saved yet (the «Строим твой путь» screen and every change after it)."""
        answers, _ = saved(g.user['id'])
        answers = answers | clean(request.get_json(silent=True) or {})
        if not answers.get('goals'):
            abort(400, 'Выберите хотя бы одну цель.')
        return jsonify(path=summary(answers, g.user))

    @app.put('/api/app/journey')
    @require_user
    def journey_save():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            abort(400)
        answers, status = saved(g.user['id'])
        answers = answers | clean(data)
        finished = data.get('status') in ('done', 'skipped')
        if data.get('status') == 'done' and not answers.get('goals'):
            abort(400, 'Выберите хотя бы одну цель.')
        new_status = data['status'] if finished else (status if status in ('done', 'skipped') else 'draft')
        with db():
            db().execute('''INSERT INTO personal_paths(user_id,body,status) VALUES(?,?,?) ON CONFLICT(user_id)
                DO UPDATE SET body=excluded.body,status=excluded.status,updated_at=CURRENT_TIMESTAMP''',
                         (g.user['id'], json.dumps(answers, ensure_ascii=False), new_status))
            if finished:
                db().execute('UPDATE users SET onboarding_done=1 WHERE id=?', (g.user['id'],))
        return jsonify(answers=answers, status=new_status, path=summary(answers, g.user) if answers.get('goals') else None)

    @app.get('/api/app/journey/custom')
    @require_user
    def journey_custom():
        """The learner's own goal: kept as written; turning it into a path is a subscription feature."""
        answers, _ = saved(g.user['id'])
        response = jsonify(error='subscription', message='Нужна подписка для анализа', custom=answers.get('custom') or '')
        response.status_code = 402
        return response

    def finished(user):
        if user['onboarding_done']:
            return True
        _, status = saved(user['id'])
        return status in ('done', 'skipped')

    return dict(finished=finished, summary=summary, saved=saved)

