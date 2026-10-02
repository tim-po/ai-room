"""Versioned curriculum fixture; no fabricated learner proficiency or assessments."""
import json


def graph_fixture():
    nodes, edges = [], []

    def add(id, title, kind, parent=None):
        nodes.append(dict(id=id, title=title, kind=kind, revision=1))
        if parent:
            edges.append(dict(source=parent, target=id, type='contains', advisory=True))

    add('basic-ai', 'Базовые знания об AI', 'root')
    for id, title in [('limitations','Объяснить ограничения модели'), ('context','Составить инструкцию с контекстом'),
                      ('verification','Проверить утверждение по источнику'), ('safety','Защитить конфиденциальные данные')]:
        add('basic-ai.'+id, title, 'ability', 'basic-ai')
    branches = {
        'coding': ('Кодинг с AI', [('design','AI-дизайн','Оценить интерфейс по требованиям'), ('mobile','Мобильные приложения','Проверить разрешения устройства'), ('review','AI-ревью кода','Обосновать дефект в изменении'), ('web','Веб-разработка','Проверить валидацию формы'), ('debug','Тестирование и отладка','Воспроизвести сбой'), ('codebase','Существующий код','Проследить зависимости')]),
        'teams': ('AI-команды', [('handoff','Роли и передача задач','Передать задачу с критериями приёмки'), ('context','Общий контекст','Подготовить бриф с источниками'), ('review','Совместное ревью','Разрешить противоречия в ответах'), ('evaluation','Оценка','Применить общую рубрику')]),
        'content': ('Создание контента', [('writing','Тексты','Проверить утверждения в тексте'), ('visual','Визуальный контент','Оценить соответствие брифу'), ('video','Аудио и видео','Исправить сценарий по источникам'), ('publishing','Публикация','Проверить атрибуцию')]),
        'automation': ('Автоматизация', [('workflow','Анализ процессов','Описать триггер и результат'), ('integrations','Интеграции','Проверить передаваемые данные'), ('reliability','Надёжность','Реализовать идемпотентный повтор'), ('monitoring','Мониторинг','Восстановить неудачный запуск')]),
        'agents': ('Агенты', [('tools','Инструменты','Ограничить контракт инструмента'), ('planning','Планирование','Ограничить выполнение задачи'), ('memory','Память и поиск','Проверить найденное свидетельство'), ('safety','Оценка и безопасность','Проверить защиту от инъекции')]),
    }
    for branch, (title, children) in branches.items():
        add(branch, title, 'branch', 'basic-ai')
        for slug, label, ability in children:
            add(f'{branch}.{slug}', label, 'category', branch)
            add(f'{branch}.{slug}.demonstrate', ability, 'ability', f'{branch}.{slug}')
    for target in ['coding.review.demonstrate', 'content.writing.demonstrate']:
        edges.append(dict(source='basic-ai.verification', target=target, type='prerequisite', advisory=True,
                          rationale='Проверка источников помогает обосновать вывод.'))
    edges.append(dict(source='automation.reliability.demonstrate', target='agents.tools.demonstrate', type='related', advisory=True))
    return dict(release='tree-2026-10-v1', root='basic-ai', nodes=nodes, edges=edges,
                mappings=[], score_rule='verified-coverage-v1')


def seed_graph(db):
    graph = graph_fixture()
    db.execute('INSERT OR IGNORE INTO skill_releases(id,body) VALUES(?,?)', (graph['release'], json.dumps(graph, ensure_ascii=False)))
    db.execute('INSERT OR IGNORE INTO skill_active VALUES(1,?)', (graph['release'],))
