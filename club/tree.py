"""Skill tree: topics -> courses -> modules -> lessons on one canvas.

The structure comes from content/catalog.json. Lessons that exist in this
platform carry the learner's state; the rest are shown as coming.
"""
import json
from pathlib import Path

CATALOG = Path(__file__).with_name('content') / 'catalog.json'
LEVELS = {'beginner': 'Начальный', 'intermediate': 'Средний', 'advanced': 'Продвинутый'}  # same words as library filters


def load_catalog():
    return json.loads(CATALOG.read_text(encoding='utf-8'))


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

    topics = []
    for topic in load_catalog()['topics']:
        courses = []
        for spec in topic['courses']:
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
                title, level = db_course['title'], 'beginner'
            else:
                modules = []
                for module in spec['modules']:
                    items = []
                    for item in module['lessons']:
                        if isinstance(item, str):
                            items.append(coming(item))
                        elif item['id'] in lessons:
                            items.append(lesson_node(lessons[item['id']]))
                    modules.append(dict(title=module['title'], lessons=items))
                title, level = spec['title'], spec['level']
            flat = [l for m in modules for l in m['lessons']]
            for module in modules:
                states = {l['state'] for l in module['lessons']}
                module['state'] = 'coming' if states == {'coming'} else ('done' if states == {'done'} else 'active')
            next_lesson = next((l for l in flat if l['state'] in ('progress', 'open')), None)
            courses.append(dict(
                id=spec['id'], title=title, level=LEVELS.get(level, level), url='/courses/' + spec['id'] if db_course else None,
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
