"""Idempotent initial route fixtures; never overwrite editorial compositions."""

def seed_routes(db):
    goals = [('essentials','Основы AI','Составите запрос, проверите ответ и сохраните результат.'),
             ('work','AI для работы','Превратите заметки встречи в проверяемый план действий.'),
             ('agents','Агенты и автоматизация','Опишете разрешения агента и условия остановки.'),
             ('build','Создание с AI','Подготовите спецификацию прототипа и критерии проверки.')]
    db.execute('''INSERT OR IGNORE INTO lessons(id,module_id,title,objective,body,minutes,position,access,task,checklist)
        VALUES('agent-api-basics','agent-lab-intro','API: запрос, разрешение и проверка','Понять границу между предложением AI и действием сервиса.',
        'API — договорённый способ обращения одной программы к другой. Запрос содержит действие и данные; ответ сообщает результат или ошибку. Например, помощник может предложить создать задачу, но выполнять запрос должен только после проверки человеком.\n\nРазделяйте чтение и изменение данных. Используйте минимальные разрешения, не передавайте секреты в запрос модели и останавливайте процесс при ошибке. Повтор запроса может повторить действие: предусмотрите проверку уже выполненной операции.\n\nСинтетическая вводная практика: опишите запрос к вымышленному списку задач без подключения реального сервиса.',
        8,1,'free','Опишите входные данные, допустимое действие, разрешение человека и остановку при ошибке.','Нет секретов в данных\nРазрешения ограничены\nПовтор действия проверяется\nУказана остановка при ошибке')''')
    for goal,title,outcome in goals:
        identity='path-'+goal
        inserted=db.execute('''INSERT OR IGNORE INTO learning_routes(id,title,goal,outcome,explanation,owner,status)
            VALUES(?,?,?,?,?,?,'published')''',(identity,title,goal,outcome,
            'Маршрут выбран по вашей цели. Для начинающих сначала добавлены общие основы: безопасный запрос и проверка результата. Для агентов также нужен вводный шаг об API. Опыт можно изменить в настройках; знакомые уроки доступны для повторения.',
            'Учебная команда AI Room')).rowcount
        if not inserted:
            continue
        if goal=='essentials':
            ids=[(r[0],0) for r in db.execute("SELECT l.id FROM lessons l JOIN modules m ON m.id=l.module_id WHERE m.course_id='ai-foundations' ORDER BY m.position,l.position,l.id")]
        else:
            ids=[('foundations-start-01',1),('foundations-start-02',1)]
            if goal=='agents':
                ids.append(('agent-api-basics',1))
            ids.append(({'work':'everyday-ai-intro-01','agents':'agent-lab-intro-01','build':'build-lab-intro-01'}[goal],0))
        db.executemany('INSERT INTO route_steps VALUES(?,?,?,?)', [(identity,lesson,index,bridge) for index,(lesson,bridge) in enumerate(ids)])
