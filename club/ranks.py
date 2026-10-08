"""Milestones and ranks on the skill map.

Each course row carries 2–3 milestones: goals on the way, placed between modules (not on lessons) and
spread by lesson count, the last one at the end of the course. A milestone is reached when every
lesson before it is completed (lessons still coming keep it out of reach, so ranks stay honest about
what exists), and each one awards a rank:
    1 Новичок  - the first lesson of the course completed (no milestone)
    2 Практик  - the first milestone (courses with three)  \
    3 Профи    - the second milestone                       > two milestones: Практик, Мастер
    4 Мастер   - the last milestone, at the end of the course /
Titles read «Практик Claude», «Мастер вайбкодинга» (the catalogue's "rank" word per course).
Earned ranks are stored, never taken back (a reached milestone stays reached), and each is celebrated
once: new ones are "unseen" until the map, the finish dialog or the profile has shown them.
"""
from math import ceil

from flask import g, jsonify, request

from .storage import additive_tables

RANKS = {1: 'Новичок', 2: 'Практик', 3: 'Профи', 4: 'Мастер'}
MILESTONE_RANKS = {1: (4,), 2: (2, 4), 3: (2, 3, 4)}
SCHEMA = ['''CREATE TABLE IF NOT EXISTS achievements (
    user_id TEXT NOT NULL REFERENCES users(id), kind TEXT NOT NULL CHECK(kind IN ('rank','checkpoint')),
    ref TEXT NOT NULL, level INTEGER NOT NULL DEFAULT 1, earned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    seen INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(user_id, kind, ref))''']


def lessons_word(n):
    return 'урок' if n % 10 == 1 and n % 100 != 11 else 'урока' if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else 'уроков'


def title(level, course):
    return f'{RANKS[level]} {course.get("rank_name") or "курса «" + course["title"] + "»"}'


def placements(modules):
    """After which modules the milestones stand: 3 on longer courses, 2 on shorter, spread by lessons."""
    sizes = [len(m['lessons']) for m in modules]
    total, n = sum(sizes), len(modules)
    if not total:
        return []
    count = 3 if total >= 9 and n >= 3 else 2 if n >= 2 else 1
    ends, running = [], 0
    for size in sizes:
        running += size
        ends.append(running)
    chosen = []
    for k in range(1, count):
        target = total * k / count
        index = next(i for i, end in enumerate(ends) if end >= target)
        index = max(index, chosen[-1] + 1 if chosen else 0)
        if index < n - 1:
            chosen.append(index)
    return chosen + [n - 1]


def milestones(course, best=0):
    """The course's milestones with their state for this learner: reached, next, ahead or coming."""
    modules = course['modules']
    after = placements(modules)
    ranks = MILESTONE_RANKS[len(after)] if after else ()
    out, found_next = [], False
    for number, (index, rank) in enumerate(zip(after, ranks), 1):
        before = [l for m in modules[:index + 1] for l in m['lessons']]
        done = sum(l['state'] == 'done' for l in before)
        available = sum(l['state'] != 'coming' for l in before)
        reached = done == len(before) or best >= rank   # earned once, kept
        if reached:
            state = 'reached'
        elif done == available:
            state = 'coming'   # only lessons not yet on the platform stand in the way
        elif not found_next:
            state, found_next = 'next', True
        else:
            state = 'ahead'
        # left: every lesson still between the learner and this milestone, those not yet published included
        out.append(dict(number=number, after=index, rank=rank, name=RANKS[rank], title=title(rank, course), state=state,
                        lessons=len(before), done=done, left=len(before) - done))
    return out


def standing(course, best=0):
    """Where the learner stands on one course: rank level, milestones reached, what's next."""
    stones = milestones(course, best)
    level = 1 if course['done'] else 0
    for stone in stones:
        if stone['state'] == 'reached':
            level = max(level, stone['rank'])
    level = max(level, best)
    upcoming = next((m for m in stones if m['state'] == 'next'), None)
    if level == 0:
        hint = 'Пройдите первый урок курса — станете новичком'
    elif upcoming:
        hint = f'До вехи «{upcoming["title"]}»: ещё {upcoming["left"]} {lessons_word(upcoming["left"])}'
    elif level < 4:
        hint = 'Следующая веха откроется с новыми уроками'
    else:
        hint = 'Высшее звание курса'
    return dict(level=level, title=title(level, course) if level else None, rank=RANKS.get(level),
                milestones=len(stones), reached=sum(m['state'] == 'reached' for m in stones), next=hint), stones


def register_ranks(app, db, query, require_user):
    ensure = additive_tables(app, SCHEMA)

    def stored(user_id):
        ensure()
        return {(r['kind'], r['ref']): r for r in query('SELECT * FROM achievements WHERE user_id=?', (user_id,))}

    def sync(tree):
        """Decorates the tree (course ranks, milestones) and records any rank newly earned.
        Returns the unseen achievements, oldest first."""
        user = g.get('user')
        have = stored(user['id']) if user else {}
        new = []
        for topic in tree['topics']:
            for course in topic['courses']:
                best = have.get(('rank', course['id']), {'level': 0})['level']
                state, stones = standing(course, best)
                course['standing'], course['milestones'] = state, stones
                for module in course['modules']:
                    module.pop('checkpoint', None)
                if user and state['level'] > best:
                    new.append(('rank', course['id'], state['level']))
        if new:
            with db():
                for kind, ref, level in new:
                    db().execute('''INSERT INTO achievements(user_id,kind,ref,level) VALUES(?,?,?,?)
                        ON CONFLICT(user_id,kind,ref) DO UPDATE SET level=excluded.level,seen=0,earned_at=CURRENT_TIMESTAMP''',
                        (user['id'], kind, ref, level))
        return unseen(tree) if user else []

    def unseen(tree):
        """New ranks to celebrate. Reaching a milestone is celebrated as the rank it gives, once."""
        courses = {c['id']: (c, t) for t in tree['topics'] for c in t['courses']}
        out = []
        for row in query("SELECT * FROM achievements WHERE user_id=? AND seen=0 AND kind='rank' ORDER BY earned_at", (g.user['id'],)):
            if row['ref'] in courses:
                course, topic = courses[row['ref']]
                stone = next((m for m in course['milestones'] if m['rank'] == row['level']), None)
                out.append(dict(kind='rank', id=f'rank:{row["ref"]}', course=course['id'], course_title=course['title'], topic=topic['title'],
                                level=row['level'], rank=RANKS[row['level']], title=title(row['level'], course), next=course['standing']['next'],
                                milestone=dict(number=stone['number'], of=len(course['milestones'])) if stone else None))
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
