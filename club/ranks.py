"""Control points and ranks on the skill map.

Every module of a course is a control point: it is reached when all its lessons are completed (a
module with lessons still coming can't be reached yet, so ranks stay honest about what exists).
A course rank follows from them:
    1 Новичок  - the first lesson of the course completed
    2 Практик  - the first control point reached
    3 Профи    - half the course's control points
    4 Мастер   - all of them
Titles read «Практик Claude», «Мастер вайбкодинга» (the catalogue's "rank" word per course).
Earned ranks and control points are stored, never taken back, and each is celebrated once: new ones
are "unseen" until the map, the finish dialog or the profile has shown them.
"""
from math import ceil

from flask import g, jsonify, request

from .storage import additive_tables

RANKS = {1: 'Новичок', 2: 'Практик', 3: 'Профи', 4: 'Мастер'}
SCHEMA = ['''CREATE TABLE IF NOT EXISTS achievements (
    user_id TEXT NOT NULL REFERENCES users(id), kind TEXT NOT NULL CHECK(kind IN ('rank','checkpoint')),
    ref TEXT NOT NULL, level INTEGER NOT NULL DEFAULT 1, earned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    seen INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(user_id, kind, ref))''']


def points(n):
    return 'контрольные точки' if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else 'контрольных точек'


def title(level, course):
    return f'{RANKS[level]} {course.get("rank_name") or "курса «" + course["title"] + "»"}'


def standing(course):
    """Where the learner stands on one course of the tree: rank level, control points, what's next."""
    modules = course['modules']
    total = len(modules)
    reached = [i for i, m in enumerate(modules) if m['state'] == 'done']
    level = 0
    if course['done']:
        level = 1
    if reached:
        level = 2
    if total and len(reached) >= ceil(total / 2) and len(reached) >= 2:
        level = 3
    if total and len(reached) == total:
        level = 4
    # The next control point: the first unreached module that has lessons on the platform.
    upcoming = next((m for m in modules if m['state'] != 'done' and any(l['state'] != 'coming' for l in m['lessons'])), None)
    if level == 0:
        hint = 'Пройдите первый урок курса — станете новичком'
    elif level < 4 and upcoming:
        # The rank the next threshold actually gives (with two control points, Профи is Мастер).
        if level < 2:
            target, missing = 2, 1
        elif level < 3:
            need = max(ceil(total / 2), 2)
            target, missing = (4 if need >= total else 3), need - len(reached)
        else:
            target, missing = 4, total - len(reached)
        hint = (f'До звания «{title(target, course)}»: '
                + (f'контрольная точка «{upcoming["title"]}»' if missing == 1 else f'ещё {missing} {points(missing)}'))
    elif level < 4:
        hint = 'Следующие контрольные точки откроются с новыми уроками'
    else:
        hint = 'Высшее звание курса'
    return dict(level=level, title=title(level, course) if level else None, rank=RANKS.get(level),
                checkpoints=total, reached=len(reached), next=hint)


def register_ranks(app, db, query, require_user):
    ensure = additive_tables(app, SCHEMA)

    def stored(user_id):
        ensure()
        return {(r['kind'], r['ref']): r for r in query('SELECT * FROM achievements WHERE user_id=?', (user_id,))}

    def sync(tree):
        """Decorates the tree (course ranks, reached control points) and records anything newly earned.
        Returns the unseen achievements, oldest first."""
        user = g.get('user')
        have = stored(user['id']) if user else {}
        new = []
        for topic in tree['topics']:
            for course in topic['courses']:
                state = standing(course)
                best = max(state['level'], have.get(('rank', course['id']), {'level': 0})['level'])
                if best != state['level']:      # earned before, never taken back
                    state |= dict(level=best, title=title(best, course), rank=RANKS[best])
                course['standing'] = state
                for index, module in enumerate(course['modules']):
                    module['checkpoint'] = module['state'] == 'done' or ('checkpoint', f'{course["id"]}:{index}') in have
                    if user and module['state'] == 'done' and ('checkpoint', f'{course["id"]}:{index}') not in have:
                        new.append(('checkpoint', f'{course["id"]}:{index}', 1))
                if user and state['level'] > have.get(('rank', course['id']), {'level': 0})['level']:
                    new.append(('rank', course['id'], state['level']))
        if new:
            with db():
                for kind, ref, level in new:
                    db().execute('''INSERT INTO achievements(user_id,kind,ref,level) VALUES(?,?,?,?)
                        ON CONFLICT(user_id,kind,ref) DO UPDATE SET level=excluded.level,seen=0,earned_at=CURRENT_TIMESTAMP''',
                        (user['id'], kind, ref, level))
        return unseen(tree) if user else []

    def unseen(tree):
        courses = {c['id']: (c, t) for t in tree['topics'] for c in t['courses']}
        out = []
        for row in query('SELECT * FROM achievements WHERE user_id=? AND seen=0 ORDER BY earned_at,kind DESC', (g.user['id'],)):
            if row['kind'] == 'rank' and row['ref'] in courses:
                course, topic = courses[row['ref']]
                out.append(dict(kind='rank', id=f'rank:{row["ref"]}', course=course['id'], course_title=course['title'], topic=topic['title'],
                                level=row['level'], rank=RANKS[row['level']], title=title(row['level'], course), next=course['standing']['next']))
            elif row['kind'] == 'checkpoint':
                course_id, _, index = row['ref'].rpartition(':')
                if course_id in courses and index.isdigit() and int(index) < len(courses[course_id][0]['modules']):
                    course = courses[course_id][0]
                    out.append(dict(kind='checkpoint', id=f'checkpoint:{row["ref"]}', course=course_id, course_title=course['title'],
                                    module=course['modules'][int(index)]['title'], number=int(index) + 1, of=len(course['modules'])))
        return out

    def mark_seen(ids):
        refs = [(i.split(':', 1)[0], i.split(':', 1)[1]) for i in ids if isinstance(i, str) and ':' in i][:50]
        with db():
            for kind, ref in refs:
                db().execute('UPDATE achievements SET seen=1 WHERE user_id=? AND kind=? AND ref=?', (g.user['id'], kind, ref))

    @app.post('/api/app/achievements/seen')
    @require_user
    def achievements_seen():
        body = request.get_json(silent=True) or {}
        mark_seen(body.get('ids') if isinstance(body.get('ids'), list) else [])
        return jsonify(ok=True)

    return dict(sync=sync, mark_seen=mark_seen)
