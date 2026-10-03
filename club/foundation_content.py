"""Additive foundation teaching sources; assessment candidates stay private.

The six fictional cases originate in the learning review handoff. Installing
teaching material neither approves their assessment equivalence nor awards credit.
"""
import copy
import hashlib
import json
from pathlib import Path

from .release_bindings import carry_forms
from .skill_content import LABEL, candidate_form, lesson_id, source

CASES = json.loads(Path(__file__).with_name('foundation_candidates.json').read_text())
COURSE = 'skill-foundations-v1'
PACK_HASH = hashlib.sha256(json.dumps(CASES, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def release_id(from_release):
    return 'tree-foundations-v1-' + hashlib.sha256((from_release + PACK_HASH).encode()).hexdigest()[:20]


def lesson_body(case):
    return '\n\n'.join([f'Источник · абзац {i+1}\n{p}' for i, p in enumerate(case['paragraphs'])] + [LABEL])


def install_foundations(db, *, from_release, reviewer):
    """Caller owns transaction/backup. Explicit compare-and-set prevents stale rebase."""
    def query(sql, params=(), one=False):
        cursor = db.execute(sql, params)
        return cursor.fetchone() if one else cursor.fetchall()

    user = query('SELECT role FROM users WHERE id=?', (reviewer,), True)
    if not user or user['role'] not in ('admin', 'editor'):
        raise ValueError('Editor identity required for the explicit content rebase')
    active = query('SELECT release_id FROM skill_active WHERE singleton=1', one=True)
    target_id = release_id(from_release)
    if not active:
        raise ValueError('Run init-skills first')
    if active['release_id'] == target_id:
        return False
    if active['release_id'] != from_release:
        raise ValueError('Active release changed; inspect it and explicitly rebase from its current ID')
    current = json.loads(query('SELECT body FROM skill_releases WHERE id=?', (from_release,), True)['body'])
    nodes = {n['id']: n for n in current['nodes']}
    # These sources teach exactly the existing foundation semantics, not a new
    # revision invented to bypass historical evidence or exposure.
    from .skill_seed import graph_fixture
    original = {n['id']: n for n in graph_fixture()['nodes']}
    for case in CASES:
        if nodes.get(case['objective']) != original[case['objective']]:
            raise ValueError('Foundation objective changed; fresh semantic review required')
    if query('SELECT id FROM courses WHERE id=?', (COURSE,), True):
        raise ValueError('Foundation content already exists on another release; explicit editorial reconciliation required')
    db.execute('''INSERT INTO courses(id,title,description,outcome,goal,level,tools,prerequisites,author,updated_at,status)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
               (COURSE, 'Базовые решения: границы, контекст и данные', LABEL,
                'Отделить наблюдение от заявления, составить проверяемую инструкцию и подготовить безопасный учебный вход.',
                'essentials', 'Начальный', 'Текст урока; внешние сервисы и оплата не нужны.',
                'Начните с любой из трёх тем.', 'AI Room · оригинальные учебные примеры', '2026-10-03', 'published'))
    db.execute('INSERT INTO modules VALUES(?,?,?,?)', (COURSE+'-cases', COURSE, 'Три темы, по два независимых случая', 0))
    tree = copy.deepcopy(current)
    tree['release'] = target_id
    for position, case in enumerate(CASES):
        db.execute('''INSERT INTO lessons(id,module_id,title,objective,body,minutes,position,access,task,checklist,status)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                   (lesson_id(case), COURSE+'-cases', case['title'], nodes[case['objective']]['title'],
                    lesson_body(case), 7, position, 'free', case['task'], '\n'.join(case['checks']), 'published'))
        tree['mappings'].append(dict(objective_id=case['objective'], lesson_id=lesson_id(case), role='teaches',
                                    source={k:v for k,v in source(case, 1).items() if k != 'text'}))
    db.execute('INSERT INTO skill_releases(id,body) VALUES(?,?)', (target_id, json.dumps(tree, ensure_ascii=False)))
    carry_forms(db, query, from_release, tree, reviewer)
    db.execute('UPDATE skill_active SET release_id=? WHERE singleton=1', (target_id,))
    return True


def installed_candidates(db):
    """Private keyed preview only, with references verified against persisted lessons."""
    from .skills import validate_form
    active = db.execute('SELECT r.body FROM skill_releases r JOIN skill_active a ON a.release_id=r.id').fetchone()
    if not active:
        raise ValueError('Install foundation sources first')
    tree = json.loads(active[0])
    result = []
    for case in CASES:
        row = db.execute('SELECT body FROM lessons WHERE id=?', (lesson_id(case),)).fetchone()
        if not row or row[0] != lesson_body(case):
            raise ValueError('Canonical foundation source missing or changed; fresh source edition/review required')
        if not any(m['objective_id'] == case['objective'] and m['lesson_id'] == lesson_id(case) for m in tree['mappings']):
            raise ValueError('Foundation source not mapped in active release')
        form = candidate_form(case)
        result.append(dict(id='skill-foundation-form-'+case['slug']+'-v1', node_id=case['objective'],
                           release=tree['release'], status='private-candidate-not-approved', form=form,
                           thresholds=validate_form(form, tree),
                           sha256=hashlib.sha256(json.dumps(form, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                           practical_proposal=dict(task=case['task'], criteria=case['checks'])))
    return result
