"""Skill tree: topics -> courses -> modules -> lessons on one canvas.

The structure comes from content/catalog.json. Lessons that exist in this
platform carry the learner's state; the rest are shown as coming.

The admin changes the map too (club/admin.py): a course's place (topic, rank name, or hidden) lives in
course_placements; courses made in the admin appear under a topic (by default the one matching their
goal); and in a catalogue course, module titles, lesson order and lessons added in the admin show up
on the map, while the catalogue's "coming" placeholders keep their slots.
"""
import json
from pathlib import Path

CATALOG = Path(__file__).with_name('content') / 'catalog.json'
PLACEMENTS = '''CREATE TABLE IF NOT EXISTS course_placements (
    course_id TEXT PRIMARY KEY REFERENCES courses(id), topic_id TEXT, rank TEXT, hidden INTEGER NOT NULL DEFAULT 0)'''
# Order within a topic: a sort key; NULL keeps the catalogue's order (admin courses after it).
PLACEMENT_COLUMNS = (('course_placements', 'position', 'REAL'),)
GOAL_TOPICS = {'essentials': 'basic-ai', 'work': 'basic-ai', 'agents': 'agents', 'build': 'coding'}
LEVELS = {'beginner': 'Начальный', 'intermediate': 'Средний', 'advanced': 'Продвинутый'}  # same words as library filters


def load_catalog():
    return json.loads(CATALOG.read_text(encoding='utf-8'))


def placements(query):
    if not query("SELECT 1 FROM sqlite_master WHERE type='table' AND name='course_placements'", one=True):
        return {}
    return {r['course_id']: r for r in query('SELECT * FROM course_placements')}


def default_topic(course):
    return GOAL_TOPICS.get(course['goal'], 'basic-ai')


def original_module_titles():
    """Imported modules ({course}-m{n}) by their title in the files, which matches catalog.json."""
    from .legacy_content import COURSES
    return {f'{course[0]}-m{i + 1}': title for course in COURSES for i, (title, _) in enumerate(course[-1])}


def order_key(place, default):
    return place['position'] if place and 'position' in place.keys() and place['position'] is not None else default


def arrange(query, published):
    """Courses per topic in map order: the catalogue's, then admin courses, moved and ordered by course_placements.
    published: course id -> row of the published courses (admin courses join the map only when published)."""
    placed = placements(query)
    catalog = load_catalog()
    home = {spec['id']: topic['id'] for topic in catalog['topics'] for spec in topic['courses']}
    by_topic = {topic['id']: [] for topic in catalog['topics']}
    for topic in catalog['topics']:
        for spec in topic['courses']:
            place = placed.get(spec['id'])
            if place and place['hidden']:
                continue
            target = place['topic_id'] if place and place['topic_id'] in by_topic else topic['id']
            by_topic[target].append(spec | ({'rank': place['rank']} if place and place['rank'] else {}))
    # Courses made in the admin (or placed there explicitly) join the map as database courses.
    for course_id, course in published.items():
        place = placed.get(course_id)
        if course_id in home or (place and place['hidden']) or not (place or course_id.startswith('course-')):
            continue
        target = place['topic_id'] if place and place['topic_id'] in by_topic else default_topic(course)
        by_topic.setdefault(target, []).append(dict(id=course_id, from_db=True, rank=place['rank'] if place else None))
    for entries in by_topic.values():
        for i, entry in enumerate(entries):
            entry['order'] = order_key(placed.get(entry['id']), float(i))
        entries.sort(key=lambda entry: entry['order'])
    return by_topic


def build_tree(query, user, can_access, current_lesson=None):
    uid = user['id'] if user else ''
    rows = query('''SELECT l.id,l.title,l.minutes,l.access,l.module_id,m.title AS module_title,m.position AS module_position,
        l.position AS lesson_position,m.course_id,COALESCE(p.completed,0) AS completed,p.user_id IS NOT NULL AS started,
        r.status AS practice FROM lessons l JOIN modules m ON m.id=l.module_id JOIN courses c ON c.id=m.course_id
        LEFT JOIN progress p ON p.lesson_id=l.id AND p.user_id=? LEFT JOIN practice r ON r.lesson_id=l.id AND r.user_id=?
        WHERE l.status='published' AND c.status='published' ''', (uid, uid))
    lessons = {r['id']: r for r in rows}
    courses_db = {r['id']: r for r in query("SELECT * FROM courses WHERE status='published'")}
    interests = set()
    if user and query("SELECT 1 FROM sqlite_master WHERE name='skill_interests'", one=True):
        interests = {r['node_id'] for r in query('SELECT node_id FROM skill_interests WHERE user_id=?', (uid,))}

    def lesson_node(row):
        if row['completed']:
            state = 'done'
        elif not can_access(row):
            state = 'locked'
        elif row['started'] or row['practice']:
            state = 'progress'
        else:
            state = 'open'
        return dict(id=row['id'], title=row['title'], minutes=row['minutes'], state=state,
                    url='/lessons/' + row['id'], current=row['id'] == current_lesson)

    def coming(title):
        return dict(id=None, title=title, state='coming')

    catalog = load_catalog()
    by_topic = arrange(query, courses_db)
    original = original_module_titles()

    def catalogue_modules(spec):
        """The catalogue's modules, with what the admin changed: titles, lesson order and added lessons."""
        rows_here = sorted((r for r in rows if r['course_id'] == spec['id']),
                           key=lambda r: (r['module_position'], r['lesson_position'], r['id']))
        in_module, titles = {}, {}
        for r in rows_here:
            in_module.setdefault(r['module_id'], []).append(r)
            titles[r['module_id']] = r['module_title']
        matched = {original[m]: m for m in in_module if m in original}
        shown, modules = set(), []
        for module in spec['modules']:
            module_id = matched.get(module['title'])
            queue = [r for r in in_module.get(module_id, [])]
            items = []
            for item in module['lessons']:
                if isinstance(item, str):
                    items.append(coming(item))
                elif module_id is not None:
                    if item['id'] in lessons and queue:   # the catalogue's slot, filled in the order set in the admin
                        items.append(lesson_node(queue.pop(0)))
                elif item['id'] in lessons:
                    items.append(lesson_node(lessons[item['id']]))
            items += [lesson_node(r) for r in queue]   # added in the admin
            shown.update(i['id'] for i in items if i['id'])
            modules.append(dict(title=titles.get(module_id, module['title']), lessons=items))
        for module_id, module_rows in in_module.items():   # modules added in the admin
            extra = [lesson_node(r) for r in module_rows if r['id'] not in shown]
            if extra:
                modules.append(dict(title=titles[module_id], lessons=extra))
        return modules

    topics = []
    for topic in catalog['topics']:
        courses = []
        for spec in by_topic[topic['id']]:
            db_course = courses_db.get(spec['id'])
            if spec.get('from_db'):
                if not db_course:
                    continue
                modules, by_id = [], {}
                for row in sorted((r for r in rows if r['course_id'] == spec['id']),
                                  key=lambda r: (r['module_position'], r['lesson_position'], r['id'])):
                    if row['module_id'] not in by_id:
                        by_id[row['module_id']] = dict(title=row['module_title'], lessons=[])
                        modules.append(by_id[row['module_id']])
                    by_id[row['module_id']]['lessons'].append(lesson_node(row))
                if not modules:
                    continue
                title, level = db_course['title'], 'beginner'
            else:
                modules = catalogue_modules(spec)
                title, level = (db_course['title'] if db_course else spec['title']), spec['level']
            flat = [l for m in modules for l in m['lessons']]
            for module in modules:
                states = {l['state'] for l in module['lessons']}
                module['state'] = 'coming' if states == {'coming'} else ('done' if states == {'done'} else 'active')
            next_lesson = next((l for l in flat if l['state'] in ('progress', 'open')), None)
            courses.append(dict(
                id=spec['id'], title=title, rank_name=spec.get('rank'), level=LEVELS.get(level, level), url='/courses/' + spec['id'] if db_course else None,
                modules=modules, total=len(flat), done=sum(l['state'] == 'done' for l in flat),
                available=sum(l['state'] != 'coming' for l in flat),
                next=dict(title=next_lesson['title'], url=next_lesson['url']) if next_lesson else None,
                current=any(l.get('current') for l in flat)))
        topics.append(dict(id=topic['id'], title=topic['title'], subtitle=topic['subtitle'],
                           interest=topic['id'] in interests, courses=courses))
    return dict(topics=topics)


def catalog_index():
    """course id -> topic and catalogue size, so lists elsewhere match the map."""
    index = {}
    for topic in load_catalog()['topics']:
        for spec in topic['courses']:
            modules = spec.get('modules', [])
            index[spec['id']] = dict(topic=topic['title'], topic_id=topic['id'], title=spec.get('title'),
                                     level=LEVELS.get(spec.get('level'), spec.get('level')), modules=len(modules),
                                     total=None if spec.get('from_db') else sum(len(m['lessons']) for m in modules))
    return index


def course_outline(query, user, can_access, course_id, current_lesson=None):
    """The map's view of one course (modules with every lesson and its state), or None."""
    for topic in build_tree(query, user, can_access, current_lesson)['topics']:
        for course in topic['courses']:
            if course['id'] == course_id:
                return course | dict(topic=topic['title'])
    return None
