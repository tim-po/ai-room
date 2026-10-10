"""Writes club/content/skills.json: the skills, the goals and how many skill points every lesson adds.

The numbers are a synthetic first draft for the demo: each module has a hand-written profile (which
skills it trains, how strongly), each lesson of it gets points from that profile, and every skill is
scaled so that the whole catalogue offers a bit more than 100 points of it. Lessons that are not on
the platform yet («скоро») get points too, so paths cover the whole map. Edit the profiles and rerun:

    python3 scripts/make_skill_model.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / 'club/content/catalog.json').read_text(encoding='utf-8'))

SKILLS = [
    ('dialog', 'Диалог с ИИ', 'Запросы, контекст и проверка ответов'),
    ('assistants', 'Ассистенты под себя', 'Projects, инструкции, память, свои GPT'),
    ('automation', 'Автоматизация задач', 'Skills, коннекторы, Cowork, режим агента'),
    ('agents', 'ИИ-агенты', 'Агенты с инструментами, команды агентов, сервер'),
    ('vibecoding', 'Вайбкодинг', 'Собрать сайт или сервис кодом с ИИ'),
    ('launch', 'Запуск продукта', 'Выкладка, данные, первые пользователи, аналитика'),
    ('visual', 'Визуальный контент', 'Изображения, товары, аватары, карусели'),
    ('video', 'Видео с ИИ', 'Сценарий, генерация, монтаж и аватары в видео'),
]

# Big goals: what a person wants their life or work to become. Targets are skill points (0–100).
GOALS = [
    ('everyday', 'Уверенно пользоваться ИИ каждый день', 'Понимать, что умеют нейросети, и решать с ними свои задачи без страха и лишних поисков.',
     {'dialog': 60, 'assistants': 40, 'automation': 20}),
    ('profession', 'Стать сильнее в своей профессии с ИИ', 'Делать ту же работу быстрее и лучше: ассистенты под твои задачи, проверенные запросы, автоматизация рутины.',
     {'dialog': 80, 'assistants': 70, 'automation': 50, 'visual': 20}),
    ('startup', 'Запустить свой продукт или стартап', 'От идеи до работающего сервиса и первых пользователей — без команды разработчиков.',
     {'dialog': 60, 'vibecoding': 70, 'launch': 80, 'agents': 30, 'visual': 30}),
    ('agentic', 'Стать агентным инженером', 'Проектировать и запускать ИИ-агентов и их команды, которые делают работу за людей.',
     {'agents': 90, 'automation': 80, 'vibecoding': 60, 'dialog': 70, 'launch': 40}),
    ('business', 'Автоматизировать свой бизнес', 'Отдать агентам заявки, продажи, отчёты и поддержку — и вернуть себе время на главное.',
     {'automation': 85, 'agents': 70, 'assistants': 60, 'dialog': 60}),
    ('creator', 'Стать ИИ-креатором', 'Делать визуал и видео для брендов, медиа и своих проектов на уровне студии.',
     {'visual': 85, 'video': 75, 'dialog': 50, 'assistants': 30}),
    ('it', 'Войти в IT без классического программирования', 'Собирать сайты, сервисы и приложения с ИИ и брать за это проекты.',
     {'vibecoding': 85, 'launch': 70, 'dialog': 60, 'agents': 30}),
    ('services', 'Зарабатывать на ИИ-услугах', 'Продавать то, что умеешь с ИИ: контент, ассистентов, автоматизации и сайты для клиентов.',
     {'dialog': 70, 'assistants': 60, 'automation': 60, 'visual': 50, 'vibecoding': 40}),
    ('lead', 'Возглавить внедрение ИИ в команде', 'Понимать, где ИИ даёт результат, учить команду и выстраивать процессы вокруг него.',
     {'dialog': 70, 'assistants': 70, 'automation': 70, 'agents': 50}),
    ('marketing', 'Маркетинг и продажи с ИИ', 'Контент, креативы, воронки и ответы клиентам — быстрее и в большем объёме.',
     {'dialog': 60, 'assistants': 50, 'automation': 50, 'visual': 60, 'video': 40}),
]

# What each module trains: {skill: weight}. Keyed by course id, in module order.
PROFILES = {
    'claude-basics': [
        {'dialog': .7, 'assistants': .3}, {'dialog': 1}, {'assistants': 1, 'dialog': .3},
        {'assistants': .5, 'automation': .4, 'dialog': .3}, {'automation': .7, 'assistants': .4},
        {'automation': .9, 'agents': .2}, {'automation': .7, 'agents': .5},
        {'vibecoding': .6, 'agents': .5, 'automation': .3}, {'automation': .5, 'assistants': .5, 'dialog': .3}],
    'chatgpt-basics': [
        {'dialog': .8, 'assistants': .2}, {'dialog': 1}, {'assistants': 1},
        {'assistants': .5, 'automation': .4, 'visual': .2}, {'assistants': .9, 'automation': .3},
        {'automation': .6, 'assistants': .3}, {'agents': .8, 'automation': .5},
        {'automation': .5, 'assistants': .4, 'dialog': .2}, {'vibecoding': .8, 'agents': .3}],
    'vibecoding-start': [
        {'vibecoding': .8, 'dialog': .2}, {'vibecoding': .6, 'dialog': .5}, {'vibecoding': 1, 'launch': .2},
        {'launch': 1, 'vibecoding': .3}, {'launch': .8}],
    'vibecoding-pro': [
        {'vibecoding': .8}, {'launch': .7, 'vibecoding': .3}, {'agents': .6, 'vibecoding': .7}, {'vibecoding': 1},
        {'vibecoding': 1, 'launch': .3}, {'vibecoding': .5, 'visual': .5}, {'vibecoding': .7, 'launch': .5},
        {'vibecoding': .9}, {'launch': 1}, {'launch': .6, 'vibecoding': .5}],
    'ai-content': [
        {'visual': .8, 'dialog': .3}, {'visual': 1}, {'visual': .9, 'video': .4}, {'visual': .9}, {'visual': .8}],
    'hermes-start': [
        {'agents': .5}, {'agents': .6, 'automation': .3}, {'agents': .8, 'launch': .2}, {'agents': .9},
        {'agents': 1, 'automation': .5}, {'agents': 1, 'automation': .6}],
}
# Guides and use cases (club/content/legacy/materials): side stops on a path. A profile per material, or its
# branch's when it has none; they add fewer points than a lesson and sit beside the module they fit best.
MATERIAL_PROFILES = {
    'ai-data-safety': {'dialog': .4, 'assistants': .5},
    'case-higgsfield': {'video': .8, 'visual': .4, 'launch': .3},
    'case-unusual': {'launch': .6, 'dialog': .3},
    'chatcut-video-editing': {'video': 1, 'agents': .3},
    'claude-chatgpt-gemini': {'dialog': .8},
    'claude-for-beginners': {'dialog': .7, 'assistants': .6},
    'prompts-that-work': {'dialog': 1, 'automation': .2},
    'what-is-ai-agent': {'agents': .8, 'automation': .4},
}
BRANCH_PROFILES = {'basic-ai': {'dialog': .6, 'assistants': .4}, 'coding': {'vibecoding': .8, 'launch': .3},
                   'content': {'visual': .6, 'video': .5}, 'agents': {'agents': .8, 'automation': .4}}
# Club materials (club/content/club_materials.json) have no text here: their profile comes from the topic,
# sharpened by words in the title and line.
KEYWORDS = [(('ролик', 'видео', 'монтаж', 'рилс', 'reels'), {'video': .8}), (('карусел', 'картин', 'фото', 'изображ', 'дизайн'), {'visual': .7}),
            (('агент', 'hermes', 'openclaw', 'джарвис'), {'agents': .7}), (('автопост', 'расписан', 'notion', 'telegram', 'телеграм'), {'automation': .5}),
            (('docker', 'github', 'деплой', 'сервер', 'сайт', 'codex', 'claude code'), {'vibecoding': .6}),
            (('запуск', 'стартап', 'заработ', 'нишу', 'маркетинг', 'продаж', 'клиент'), {'launch': .5}),
            (('промпт', 'промт', 'текст', 'нейрослоп'), {'dialog': .5}), (('скилл', 'проект', 'памят', 'второй мозг'), {'assistants': .5})]
MATERIAL_POINTS = 4   # a guide adds up to this many points to a skill (a lesson adds ~3–10)
LEVEL_BASE = {'beginner': 5.0, 'intermediate': 7.0, 'advanced': 8.0}
HEADROOM = 125   # what the whole catalogue offers of each skill, before the 100 cap


def lessons():
    """Every lesson of the map in course order: (course, module index, module title, lesson index, title, lesson id, profile, base)."""
    out = []
    for topic in CATALOG['topics']:
        for spec in topic['courses']:
            base = LEVEL_BASE.get(spec.get('level') or 'beginner', 5.0)
            if spec.get('from_db'):
                continue   # a course that lives only in the database has no catalogue outline to score
            profiles = PROFILES[spec['id']]
            assert len(profiles) == len(spec['modules']), spec['id']
            modules = [(m['title'], m['lessons'], prof) for m, prof in zip(spec['modules'], profiles)]
            for mi, (title, items, prof) in enumerate(modules):
                for li, item in enumerate(items):
                    lesson_id = item.get('id') if isinstance(item, dict) else None
                    name = item if isinstance(item, str) else (item or {}).get('title') if isinstance(item, dict) else None
                    minutes = (item.get('minutes') if isinstance(item, dict) else None) or 15
                    out.append((spec['id'], mi, title, li, name, lesson_id, prof, base * (1 + .25 * li / max(1, len(items) - 1)), minutes))
    return out


def main():
    rows = lessons()
    raw = {s: sum(base * prof.get(s, 0) for *_, prof, base, _ in rows) for s, *_ in SKILLS}
    scale = {s: HEADROOM / raw[s] if raw[s] else 0 for s in raw}
    out = []
    for course, mi, module, li, title, lesson_id, prof, base, minutes in rows:
        gains = {s: max(1, round(base * w * scale[s])) for s, w in prof.items() if w}
        out.append(dict(key=f'{course}:{mi}:{li}', course=course, module=mi, module_title=module, index=li,
                        title=title, lesson_id=lesson_id, minutes=minutes, gains=gains))
    totals = {s: sum(l['gains'].get(s, 0) for l in out) for s, *_ in SKILLS}
    modules = {}
    for course, mi, module, *_, prof, base, minutes in rows:
        modules.setdefault(f'{course}:{mi}', prof)
    materials = []
    for path in sorted((ROOT / 'club/content/legacy/materials').glob('*.md')):
        meta = dict(line.split(': ', 1) for line in path.read_text(encoding='utf-8').split('---\n', 2)[1].strip().splitlines())
        prof = MATERIAL_PROFILES.get(meta['id']) or BRANCH_PROFILES.get(meta.get('branch'), {'dialog': .5})
        near = max(modules, key=lambda key: sum(w * modules[key].get(skill, 0) for skill, w in prof.items()))   # the first best fit
        materials.append(dict(id=meta['id'], title=meta['title'], format=meta['format'], minutes=int(meta['minutes']), near=near,
                              gains={sk: max(1, round(MATERIAL_POINTS * w)) for sk, w in prof.items() if w}))
    club = json.loads((ROOT / 'club/content/club_materials.json').read_text(encoding='utf-8'))['items']
    for item in club:
        text = (item['title'] + ' ' + item['summary']).lower()
        prof = dict(BRANCH_PROFILES.get(item['branch'], {'dialog': .5}))
        for words, extra in KEYWORDS:
            if any(w in text for w in words):
                for skill, w in extra.items():
                    prof[skill] = max(prof.get(skill, 0), w)
        near = max(modules, key=lambda key: sum(w * modules[key].get(skill, 0) for skill, w in prof.items()))
        materials.append(dict(id=item['id'], title=item['title'], format=item['format'], minutes=item.get('minutes'), near=near, club=True,
                              gains={sk: max(1, round(MATERIAL_POINTS * w)) for sk, w in prof.items() if w}))
    model = dict(
        note='Synthetic demo numbers, generated by scripts/make_skill_model.py; edit the profiles there.',
        skills=[dict(id=i, title=t, text=x) for i, t, x in SKILLS],
        goals=[dict(id=i, title=t, text=x, targets=g) for i, t, x, g in GOALS],
        requires={'vibecoding-pro': {'vibecoding': 30}, 'hermes-start': {'automation': 15}},
        lessons=out, materials=materials, totals=totals)
    path = ROOT / 'club/content/skills.json'
    path.write_text(json.dumps(model, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(out), 'lessons,', len(materials), 'guides; points on offer per skill:', totals)


if __name__ == '__main__':
    main()
