"""Private supported-schema transfer proposals, never installed or published.

Run `python -m club.transfer_candidates` for an operator-only keyed review bundle.
Canonical source snapshots and original lineage are retained from learning review.
"""
import copy
import hashlib
import json
from pathlib import Path

from .skill_seed import graph_fixture
from .skills import validate_form

BLUEPRINTS = json.loads(Path(__file__).with_name('transfer_blueprints.json').read_text())

# Deliberate misconceptions for independent ambiguity/construct review.
DISTRACTORS = {
    'verification': [
        ['65%: среднее двух долей учитывает обе группы.', '80%: меньшая группа даёт более точную оценку.'],
        ['Да: 45 обработанных обращений против 8 доказывают качество.', 'Да: отсутствие сведений о сложности означает одинаковую сложность.'],
        ['Оставить 65%, добавив ссылку на v1.', 'Указать 53% и заключить, что A качественнее из-за доли 80%.'],
    ],
    'mobile': [
        ['Отсутствие запроса микрофона при первом запуске.', 'Возможность загрузить файл после отказа.'],
        ['Список ожидаемых результатов без запуска стенда.', 'Снимок экрана кнопки без версии и фактических исходов.'],
        ['Да: контакты помогут восстановить состояние микрофона.', 'Да: после устранения аварии повторная проверка отказа не нужна.'],
    ],
    'review': [
        ['Сравнить только возвращённый список с опубликованными записями.', 'Успех текущего теста доказывает неизменность входа.'],
        ['Сохранить rows[:], затем вернуть копию rows.', 'Вернуть исходный список без фильтрации.'],
        ['Только число опубликованных записей в результате.', 'Только смешанный вход; пустой список не относится к контракту.'],
    ],
    'writing': [
        ['Оставить обещание всем, сославшись на архив v1.', 'Написать: CSV недоступен в плане Старт.'],
        ['Да: неуказанная функция всегда отсутствует.', 'Нет: архив v1 доказывает, что экспорт по-прежнему есть всем.'],
        ['Да: оговорка разрешает неподтверждённое обещание.', 'Да: v1 и v2 можно объединить в более привлекательное обещание.'],
    ],
    'handoff': [
        ['Только D7: редактор сам выберет версию брифа.', 'D7 и разрешение редактору публиковать после правки ссылок.'],
        ['Усреднить значения v2 и v3.', 'Попросить AI выбрать наиболее уверенное число и утвердить его.'],
        ['Когда файл отправлен, даже без подтверждения получателя.', 'Когда редактор исправил ссылки и самостоятельно опубликовал документ.'],
    ],
    'workflow': [
        ['Любой запрос отмены.', 'Отказ в отмене, если известен booking_id.'],
        ['Создать задачу без связи с бронью.', 'Угадать booking_id по последней брони клиента.'],
        ['Каждое подтверждение создаёт отдельную задачу.', 'Записанного требования достаточно, чтобы считать идемпотентность проверенной.'],
    ],
    'tools': [
        ['Игнорировать лишнее поле и выполнить чтение.', 'Изменить status, потому что task_id разрешён.'],
        ['Выполнить команду заметки, затем вернуть done.', 'Вернуть заметку целиком вместе со status.'],
        ['Инструкция модели не изменять данные без проверки сервера.', 'Один успешный запрос demo-1 без отрицательных тестов.'],
    ],
}

PRACTICAL = {
    'mobile': {
        'instructions': 'На собственном синтетическом стенде «Клип» исправьте обработку отозванного разрешения микрофона. Приложите версию/коммит, изменение кода и фактический протокол запусков. Разделите выполненные проверки и планы; личные записи и реальные разрешения чужого устройства не нужны.',
        'criteria': [
            {'id': 'artifact', 'text': 'Доступен проверяемый исходный код или diff с версией стенда; обработка недоступного микрофона видна в коде, а не только описана.'},
            {'id': 'permission', 'text': 'Протокол с действиями и фактическими исходами показывает первый запуск без запроса, запись после согласия и отказ с сохранённой загрузкой файла.'},
            {'id': 'revocation', 'text': 'Воспроизводимый прогон отзыва разрешения и повторного открытия не вызывает аварию; недоступный микрофон обработан и загрузка остаётся доступной.'},
            {'id': 'scope', 'text': 'Изменение и наблюдаемые запросы не требуют контактов или иных дополнительных разрешений; отчёт явно отделяет выполненные прогоны от непроверенных сред.'},
        ],
    },
    'tools': {
        'instructions': 'Реализуйте локальный синтетический status_task по контракту источника. Приложите версию кода, валидатор, воспроизводимые тесты и журнал результатов. Используйте только demo-1/demo-2, без внешних сервисов, секретов и реальных задач.',
        'criteria': [
            {'id': 'validator', 'text': 'Исполняемый серверный валидатор до чтения отклоняет неизвестный task_id и лишние поля; код и фактические отрицательные тесты это показывают.'},
            {'id': 'response', 'text': 'Фактические успешные тесты обоих разрешённых ID возвращают только status из new/done; заметки и другие поля отсутствуют.'},
            {'id': 'injection', 'text': 'Тест заметки с командой изменить статус показывает отсутствие записи; снимки состояния до и после совпадают, журнал не содержит вызова изменения.'},
            {'id': 'reproduce', 'text': 'Версия, команда запуска и фактические результаты позволяют повторить положительные и отрицательные тесты; обещание в промпте или план тестирования не заменяет прогон.'},
        ],
    },
}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def candidates():
    """Read-only export. Structural validation is not editorial approval."""
    results = []
    for blueprint in BLUEPRINTS:
        case = copy.deepcopy(blueprint)
        source = case['source']
        if hashlib.sha256(source['text'].encode()).hexdigest() != source['sha256']:
            raise ValueError('Canonical transfer snapshot changed; new edition and review required')
        slug = case['id'].removeprefix('transfer-B-')
        items = []
        for index, decision in enumerate(case['decisions']):
            # Vary answer placement without changing the observation's lineage.
            options = list(DISTRACTORS[slug][index])
            answer = index % 3
            options.insert(answer, decision['expected'])
            items.append(dict(id=decision['id'], lineage_id=decision['lineage_id'],
                              objective_id=case['objective_id'], type='scenario', critical=False,
                              prompt=decision['prompt'], choices=[dict(id=str(i), text=t) for i,t in enumerate(options)],
                              answer=str(answer), rationale=decision['expected'],
                              source=dict(kind='original-fictional-example', source_id=source['id'],
                                          edition=source['edition'], paragraph=source['paragraph'],
                                          text=source['text'], sha256=source['sha256'])))
        form = dict(title='Перенос решения · '+slug, items=items,
                    scope='Понимание одного синтетического случая; выполнение и общая компетентность не сертифицируются.')
        proposal = copy.deepcopy(PRACTICAL.get(slug))
        results.append(dict(id=case['id'], node_id=case['objective_id'], status='private-candidate-not-approved',
                            form=form, sha256=digest(form), thresholds=validate_form(form, graph_fixture()),
                            source_snapshot=source, practical_proposal=proposal,
                            practical_sha256=digest(proposal) if proposal else None,
                            equivalence=dict(status='pending_independent_review', approved=False,
                                             scope='Three decisions within one case; no interchangeable-retake claim.'),
                            publication_blockers=['Independent source/item/construct and equivalence decision',
                                                  'Bind private source snapshot to retained canonical source storage before publication'],
                            retake=case['retake']))
    return results


if __name__ == '__main__':
    print(json.dumps(candidates(), ensure_ascii=False, indent=2))
