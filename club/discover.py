"""Обзор (Discover) and search: one index of everything a learner can open or look forward to.

Lessons, courses, materials (guides, use cases, workshops) and what is coming from the old
platform's outline become uniform items. Discover arranges them into shelves (continue, free to
start, top per topic, classes, quick lessons, coming); search ranks them for a query. Both expose
metadata only: never a member-only body, prompt, task text or video reference.
"""
import re
from datetime import datetime, timedelta, timezone

from flask import g, jsonify, request

from .tree import build_tree

CLASSES = {'lesson': 'Уроки', 'course': 'Курсы', 'guide': 'Гайды', 'use_case': 'Кейсы', 'workshop': 'Воркшопы', 'coming': 'Скоро'}
# Materials are tagged with a goal; the map and Discover group by topic.
GOAL_TOPIC = {'essentials': 'basic-ai', 'work': 'basic-ai', 'agents': 'agents', 'build': 'coding'}
NEW_DAYS = 21
SUGGESTIONS = ['Claude', 'ChatGPT', 'ИИ-агент', 'видео', 'промпты', 'сайт без кода']


def normalise(text):
    return re.sub(r'\s+', ' ', (text or '').lower().replace('ё', 'е')).strip()


def stems(query):
    """Query words cut to a stem, so «агенты» finds «агентом» and «промпты» finds «промптов»."""
    words = re.findall(r'[\w+#]+', normalise(query))[:8]
    return [w[:max(4, len(w) - 2)] if len(w) > 5 else w for w in words]


def score(item, query, parts):
    """0 when a word is missing; otherwise higher for matches in the title, and at word starts."""
    title, context, text = normalise(item['title']), normalise(item.get('context')), normalise(item.get('haystack'))
    total = 0
    for stem in parts:
        if re.search(r'(?:^|[^\w])' + re.escape(stem), title):
            total += 10
        elif stem in title:
            total += 6
        elif stem in context:
            total += 3
        elif stem in text:
            total += 1
        else:
            return 0
    if normalise(query) in title:
        total += 8
    return total - (3 if item['kind'] == 'coming' else 0)


def register_discover(app, query, can_access, cards, continuation_context, shell):

    def recent(value):
        try:
            moment = datetime.strptime(str(value)[:19], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        except ValueError:
            return False
        return datetime.now(timezone.utc) - moment < timedelta(days=NEW_DAYS)

    def index():
        """Every item, in catalogue order, with the learner's state."""
        user = g.get('user')
        tree = build_tree(query, user, can_access)
        learners = {r['lesson_id']: r['n'] for r in query('SELECT lesson_id,COUNT(DISTINCT user_id) n FROM progress GROUP BY lesson_id')}
        course_learners = {r['course_id']: r['n'] for r in query('''SELECT m.course_id,COUNT(DISTINCT p.user_id) n FROM progress p
            JOIN lessons l ON l.id=p.lesson_id JOIN modules m ON m.id=l.module_id GROUP BY m.course_id''')}
        details = {r['id']: r for r in query('''SELECT l.id,l.objective,l.access,l.task IS NOT NULL AS practice,m.title AS module
            FROM lessons l JOIN modules m ON m.id=l.module_id WHERE l.status='published' ''')}
        courses = {c['id']: c for c in cards()}
        items, topics = [], []
        for topic in tree['topics']:
            topic_items = 0
            for course in topic['courses']:
                card = courses.get(course['id'])
                base = dict(topic=topic['title'], topic_id=topic['id'], level=course['level'])
                if not card:
                    # Not on this platform yet: the course and its lessons are shown as coming.
                    lessons = [l for m in course['modules'] for l in m['lessons']]
                    items.append(base | dict(kind='coming', id=course['id'], title=course['title'], url=f'/?view=map#course-{course["id"]}',
                                             text=f'{len(course["modules"])} модулей · {len(lessons)} уроков', lessons=len(lessons),
                                             context=topic['title'], haystack=' '.join(m['title'] for m in course['modules']),
                                             state='coming', access=None, learners=0, new=False))
                    for module in course['modules']:
                        for lesson in module['lessons']:
                            items.append(base | dict(kind='coming', sub='lesson', id=None, title=lesson['title'], url=f'/?view=map#course-{course["id"]}',
                                                     text=f'Урок курса «{course["title"]}»', course=dict(id=course['id'], title=course['title']),
                                                     context=course['title'], haystack=module['title'], state='coming', access=None,
                                                     learners=0, new=False, hidden=True))
                    continue
                topic_items += 1
                fresh = recent(card['updated_at'])
                items.append(base | dict(kind='course', id=card['id'], title=card['title'], url=f'/courses/{card["id"]}', text=card['description'],
                                         lessons=card['total'], catalog_total=card['catalog_total'], done=card['done'], minutes=card['minutes'],
                                         free=card['free'], state='done' if card['total'] and card['done'] == card['total'] else 'progress' if card['done'] else 'open',
                                         access='free' if card['free'] == card['total'] else 'mixed', context=topic['title'],
                                         haystack=' '.join((card['outcome'], card['tools'])), learners=course_learners.get(card['id'], 0), new=fresh,
                                         next=course['next']))
                for module in course['modules']:
                    for lesson in module['lessons']:
                        if lesson['state'] == 'coming':
                            items.append(base | dict(kind='coming', sub='lesson', id=None, title=lesson['title'], url=f'/?view=map#course-{course["id"]}',
                                                     text=f'Урок курса «{course["title"]}»', course=dict(id=course['id'], title=course['title']),
                                                     context=course['title'], haystack=module['title'], state='coming', access=None,
                                                     learners=0, new=False, hidden=True))
                            continue
                        detail = details.get(lesson['id'])
                        if not detail:
                            continue
                        topic_items += 1
                        items.append(base | dict(kind='lesson', id=lesson['id'], title=lesson['title'], url=lesson['url'], text=detail['objective'],
                                                 minutes=lesson['minutes'], state=lesson['state'], access=detail['access'], practice=bool(detail['practice']),
                                                 course=dict(id=card['id'], title=card['title']), context=f'{card["title"]} {topic["title"]}',
                                                 haystack=detail['module'] + ' ' + detail['objective'], learners=learners.get(lesson['id'], 0), new=fresh))
            topics.append(dict(id=topic['id'], title=topic['title'], subtitle=topic['subtitle'], interest=topic['interest'], available=topic_items,
                               coming=sum(1 for c in topic['courses'] if c['id'] not in courses)))
        names = {t['id']: t['title'] for t in topics}
        branches = {}
        if query("SELECT 1 FROM sqlite_master WHERE name='material_profiles'", one=True):
            branches = {r['material_id']: r['branch'] for r in query('SELECT material_id,branch FROM material_profiles')}
        for m in query('''SELECT id,title,description,outcome,format,goal,level,tools,minutes,access,updated_at
                FROM materials WHERE status='published' ORDER BY updated_at DESC,id'''):
            topic_id = branches.get(m['id']) or GOAL_TOPIC.get(m['goal'], 'basic-ai')
            items.append(dict(kind=m['format'], id=m['id'], title=m['title'], url=f'/materials/{m["id"]}', text=m['description'],
                              minutes=m['minutes'], level=m['level'], topic=names.get(topic_id), topic_id=topic_id,
                              access=m['access'], state='open' if m['access'] == 'free' or can_access(dict(access=m['access'])) else 'locked',
                              context=names.get(topic_id, ''), haystack=' '.join((m['outcome'], m['tools'])), learners=0, new=recent(m['updated_at'])))
        return items, topics

    PUBLIC = ('kind', 'sub', 'id', 'title', 'url', 'text', 'topic', 'topic_id', 'level', 'minutes', 'state', 'access', 'course',
              'lessons', 'catalog_total', 'done', 'free', 'practice', 'learners', 'new', 'next', 'resume', 'course_done', 'course_total')

    def public(item):
        return {k: item[k] for k in PUBLIC if k in item}

    def classes(visible):
        """The classes that have something to show, with counts."""
        counts = {}
        for i in visible:
            counts[i['kind']] = counts.get(i['kind'], 0) + 1
        return [dict(id=k, title=v, count=counts[k]) for k, v in CLASSES.items() if counts.get(k)]

    def discover_data():
        items, topics = index()
        user = g.get('user')
        visible = [i for i in items if not i.get('hidden')]
        lessons = [i for i in visible if i['kind'] == 'lesson']
        by_popularity = lambda i: -i['learners']
        shelves = []

        def shelf(key, title, entries, style='row', subtitle=None, link=None):
            if entries:
                shelves.append(dict(id=key, title=title, subtitle=subtitle, style=style, link=link, items=[public(e) for e in entries]))

        # Continue: the unfinished lesson first, then the next lesson of every course in progress.
        continuing = []
        unfinished = continuation_context()['unfinished'] if user else None
        if unfinished:
            lesson = next((i for i in lessons if i['id'] == unfinished['lesson_id']), None)
            if lesson:
                continuing.append(lesson | dict(resume='draft' if unfinished['status'] == 'draft' else 'started'))
        if user:
            for course in (i for i in visible if i['kind'] == 'course' and i['state'] == 'progress' and i.get('next')):
                lesson = next((i for i in lessons if i['url'] == course['next']['url']), None)
                if lesson and all(c['id'] != lesson['id'] for c in continuing):
                    continuing.append(lesson | dict(resume='next', course_done=course['done'], course_total=course['lessons']))
        shelf('continue', 'Продолжить', continuing, style='wide')

        started = {c['id'] for c in continuing}
        free = [i for i in lessons if i['access'] == 'free' and i['state'] == 'open' and i['id'] not in started]
        shelf('free', 'Начните бесплатно', free, subtitle='Короткие уроки с практикой на вашей задаче')
        for topic in topics:
            ranked = sorted((i for i in visible if i['topic_id'] == topic['id'] and i['kind'] != 'coming'), key=by_popularity)[:10]
            if len(ranked) >= 3:
                shelf(f'top-{topic["id"]}', f'Топ в «{topic["title"]}»', ranked, style='top', link=f'/discover?topic={topic["id"]}')
        shelf('courses', 'Курсы', [i for i in visible if i['kind'] == 'course'], subtitle='Программы от первого запуска до результата', link='/discover?class=course')
        for kind in ('guide', 'use_case', 'workshop'):
            shelf(kind, CLASSES[kind], [i for i in visible if i['kind'] == kind], link=f'/discover?class={kind}')
        shelf('quick', 'Быстро: до 15 минут', [i for i in lessons if i.get('minutes', 99) <= 15 and i['state'] in ('open', 'progress')])
        if not (user and (user['entitlement'] == 'member' or user['role'] != 'learner')):
            shelf('club', 'В клубе', [i for i in lessons if i['state'] == 'locked'], subtitle='Полные курсы и практика — для участников клуба', link='/membership')
        shelf('coming', 'Скоро в AI Room', [i for i in visible if i['kind'] == 'coming'], style='coming',
              subtitle='Уже на карте навыков — уроки появятся по мере переноса')
        if user:
            listed = {r['course_id'] for r in query('SELECT course_id FROM favourites WHERE user_id=?', (user['id'],))}
            listed |= {r['material_id'] for r in query('SELECT material_id FROM material_favourites WHERE user_id=?', (user['id'],))}
            shelf('list', 'Мой список', [i for i in visible if i['id'] in listed and i['kind'] != 'lesson'])

        # Hero: what to start next (the Продолжить shelf already holds what's begun): the strongest
        # free lesson, the most followed course, and something new.
        featured = sorted(free, key=lambda i: (-i['learners'], -bool(i.get('practice'))))[:1]
        featured = [i | dict(cta='Начать урок') for i in featured]
        course = sorted((i for i in visible if i['kind'] == 'course' and i['state'] == 'open'), key=by_popularity)
        course = course or sorted((i for i in visible if i['kind'] == 'course' and i['state'] == 'progress'), key=by_popularity)
        featured += [i | dict(cta='Открыть курс') for i in course[:1]]
        fresh = [i for i in visible if i['new'] and i['kind'] in ('guide', 'use_case', 'workshop', 'course') and i['state'] != 'done']
        featured += [i | dict(cta='Открыть') for i in fresh if all(f['id'] != i['id'] for f in featured)][:1]
        if not featured and continuing:
            featured = [continuing[0] | dict(cta='Продолжить')]
        hero = [public(i) | {k: i[k] for k in ('cta', 'resume') if k in i} for i in featured[:3]]

        return dict(hero=hero, shelves=shelves, topics=topics, suggestions=SUGGESTIONS, classes=classes(visible))

    def search_data():
        q = request.args.get('q', '').strip()[:120]
        kind, topic, level = request.args.get('class', ''), request.args.get('topic', ''), request.args.get('level', '')
        free_only = request.args.get('access') == 'free'
        limit = min(max(request.args.get('limit', 60, type=int), 1), 200)
        items, topics = index()
        parts = stems(q)
        hits = []
        for item in items:
            if (kind and item['kind'] != kind) or (topic and item['topic_id'] != topic) or (level and item.get('level') != level):
                continue
            if free_only and item.get('access') != 'free':
                continue
            if item.get('hidden') and not parts:
                continue
            value = score(item, q, parts) if parts else 1
            if value:
                hits.append((value, item))
        # Stable sort keeps catalogue order among equal scores.
        hits.sort(key=lambda pair: (-pair[0], pair[1]['kind'] == 'coming', -pair[1]['learners']))
        ranked = [public(item) for _, item in hits[:limit]]
        return dict(query=q, stems=parts, total=len(hits), items=ranked, topics=topics,
                    classes=classes([i for i in items if not i.get('hidden')]), suggestions=SUGGESTIONS)

    @app.get('/discover')
    def discover():
        return shell()

    @app.get('/api/app/discover')
    def discover_api():
        return jsonify(discover_data())

    @app.get('/api/app/search')
    def search_api():
        return jsonify(search_data())

    return dict(index=index)
