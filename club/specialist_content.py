"""Additive, source-pinned specialist teaching edition; no automatic credit."""
import copy
import hashlib
import json

from .release_bindings import carry_forms
from .skill_content import LABEL
from .specialist_cases import CASES

COURSE = 'skill-specialists-v1'
PACK_HASH = hashlib.sha256(json.dumps(CASES, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def release_id(parent):
    return 'tree-specialists-v1-' + hashlib.sha256((parent + PACK_HASH).encode()).hexdigest()[:20]


def lesson_id(case):
    return 'skill-specialist-' + case['slug'] + '-v1'


def paragraphs(case):
    return case['paragraphs'] + ['Разобранный результат\n' + case['artifact']]


def lesson_body(case):
    return '\n\n'.join([f'Источник · абзац {i+1}\n{p}' for i, p in enumerate(paragraphs(case))]
                       + [LABEL, 'Практика сохраняет вашу работу. Чтение и выполнение задания сами по себе не присваивают подтверждённый навык.'])


def sources(case):
    return [dict(kind='original-fictional-example', lesson_id=lesson_id(case), edition=1,
                 paragraph=i+1, sha256=hashlib.sha256(p.encode()).hexdigest())
            for i, p in enumerate(paragraphs(case))]


def install_specialists(db, *, from_release, reviewer):
    """Caller provides locked transaction and backup, as for foundations."""
    def query(sql, params=(), one=False):
        cursor = db.execute(sql, params)
        return cursor.fetchone() if one else cursor.fetchall()

    user = query('SELECT role FROM users WHERE id=?', (reviewer,), True)
    if not user or user['role'] not in ('admin', 'editor'):
        raise ValueError('Editor identity required for explicit content rebase')
    active = query('SELECT release_id FROM skill_active WHERE singleton=1', one=True)
    if not active:
        raise ValueError('Run init-skills first')
    target = release_id(from_release)
    if active['release_id'] == target:
        return False
    if active['release_id'] != from_release:
        raise ValueError('Active release changed; explicitly rebase from the inspected current ID')
    current = json.loads(query('SELECT body FROM skill_releases WHERE id=?', (from_release,), True)['body'])
    nodes = {n['id']: n for n in current['nodes']}
    from .skill_seed import graph_fixture
    original = {n['id']: n for n in graph_fixture()['nodes']}
    for case in CASES:
        if nodes.get(case['objective']) != original[case['objective']]:
            raise ValueError('Specialist objective changed; fresh semantic review required')
    if query('SELECT id FROM courses WHERE id=?', (COURSE,), True):
        raise ValueError('Specialist pack exists on another release; explicit reconciliation required')
    db.execute('''INSERT INTO courses(id,title,description,outcome,goal,level,tools,prerequisites,author,updated_at,status)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
               (COURSE, 'Практикум: от интерфейса до безопасного агента', LABEL,
                'Разобрать конкретные решения в коде, команде, контенте, автоматизации и агентах; сохранить проверяемый результат.',
                'essentials', 'Начальный', 'Текст; для части практик локальный Python и SQLite. Внешние сервисы и оплата не нужны.',
                'Любая тема независимо. Для исполняемых практик нужны основы запуска локального кода.',
                'AI Room · оригинальные учебные примеры', '2026-10-03', 'published'))
    branches = [('coding', 'Код и интерфейсы'), ('teams', 'Командные решения'), ('content', 'Контент'),
                ('automation', 'Автоматизация'), ('agents', 'Агенты')]
    for position, (branch, title) in enumerate(branches):
        db.execute('INSERT INTO modules VALUES(?,?,?,?)', (COURSE+'-'+branch, COURSE, title, position))
    tree = copy.deepcopy(current)
    tree['release'] = target
    for position, case in enumerate(CASES):
        branch = case['objective'].split('.')[0]
        db.execute('''INSERT INTO lessons(id,module_id,title,objective,body,minutes,position,access,task,checklist,status)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                   (lesson_id(case), COURSE+'-'+branch, case['title'], nodes[case['objective']]['title'],
                    lesson_body(case), 12, position, 'free', case['task'], '\n'.join(case['checks']), 'published'))
        tree['mappings'].append(dict(objective_id=case['objective'], lesson_id=lesson_id(case),
                                     role='teaches', source=sources(case)[0]))
    db.execute('INSERT INTO skill_releases(id,body) VALUES(?,?)', (target, json.dumps(tree, ensure_ascii=False)))
    carry_forms(db, query, from_release, tree, reviewer)
    db.execute('UPDATE skill_active SET release_id=? WHERE singleton=1', (target,))
    return True


def inventory(db):
    """Exact persisted inventory for independent semantic review, not acceptance."""
    active = db.execute('SELECT r.body FROM skill_releases r JOIN skill_active a ON a.release_id=r.id').fetchone()
    if not active:
        raise ValueError('Install specialist sources first')
    tree = json.loads(active[0])
    rows = []
    for case in CASES:
        row = db.execute('SELECT body,task,checklist FROM lessons WHERE id=?', (lesson_id(case),)).fetchone()
        if not row or tuple(row) != (lesson_body(case), case['task'], '\n'.join(case['checks'])):
            raise ValueError('Specialist source or practice changed; new edition and review required')
        mapping = dict(objective_id=case['objective'], lesson_id=lesson_id(case), role='teaches', source=sources(case)[0])
        if mapping not in tree['mappings']:
            raise ValueError('Canonical specialist mapping missing or changed')
        rows.append(dict(lesson_id=lesson_id(case), objective_id=case['objective'], title=case['title'],
                         body_sha256=hashlib.sha256(row[0].encode()).hexdigest(), sources=sources(case),
                         paragraphs=paragraphs(case), task=case['task'], checks=case['checks'],
                         editorial_status='awaiting-independent-semantic-review', assessment_published=False))
    return dict(release=tree['release'], pack_sha256=PACK_HASH, lessons=rows,
                scope='Teaching mappings only. No understanding or applied evidence awarded.')
