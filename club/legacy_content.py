"""Real free lessons from the original AI Room platform, plus labelled demo
member lessons that exercise the paywall. No paid legacy content is imported.

Lesson bodies use a small Markdown subset (see ``parse_blocks``) and are
rendered through ``render_blocks``, which escapes everything and only emits
allowlisted links, images and video embeds.
"""
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import click
from markupsafe import Markup, escape

CONTENT_DIR = Path(__file__).with_name('content') / 'legacy'
IMAGE_HOSTS = ('https://airoom-storage.s3.twcstorage.ru/',)
VIDEO_EMBED = re.compile(r'https://kinescope\.io/embed/[A-Za-z0-9]+(\?[A-Za-z0-9_=&]*)?')
IMAGE_SOURCES = ' '.join(h.rstrip('/') for h in IMAGE_HOSTS)
FRAME_SOURCES = 'https://kinescope.io'
LEVELS = {'beginner': 'Начальный', 'intermediate': 'Средний', 'advanced': 'Продвинутый'}



def demo_body(outline):
    intro = ('!note **Демо-урок.** Он показывает, как работает закрытый доступ клуба. '
             'Настоящий урок появится здесь после переноса платных материалов.')
    return '\n\n'.join([intro] + [f'## {part}\n\nДемонстрационный текст раздела.' for part in outline])

# (course id, title, description, outcome, goal, branch, tools, modules)
# module: (title, [lesson spec]); lesson spec: legacy file id or ('demo', id, title, objective, minutes, outline)
COURSES = [
    ('claude-basics', 'Claude с 0 до PRO',
     'Практический курс: настроить Claude под себя, давать правильный контекст и получать рабочие результаты.',
     'Получите первый рабочий результат на своей задаче и сохраните запрос, который сработал.',
     'essentials', 'basic-ai', 'Claude, бесплатного тарифа достаточно.',
     [('Старт с Claude', ['claude-first-result']),
      ('Контекст и промты', [('demo', 'claude-basics-context', 'Контекст — фундамент хорошего ответа', 'Понять, какой контекст нужен модели для точного ответа.', 10,
                              ('Почему модель отвечает «средне»', 'Четыре слоя контекста', 'Что не нужно добавлять')),
                             ('demo', 'claude-basics-formula', 'Формула рабочего запроса', 'Собрать запрос из роли, задачи, формата и ограничений.', 10,
                              ('Роль и задача', 'Формат и объём', 'Запреты и критерии', 'Шаблон для своей библиотеки'))])]),
    ('ai-video', 'Видео с ИИ-агентом',
     'Монтаж словами: агент собирает ролик из исходников по вашим инструкциям.',
     'Смонтируете первый ролик с помощью Claude или Codex и готовых промптов.',
     'build', 'content', 'ChatCut и Claude Code или Codex.',
     [('Монтаж словами', ['chatcut-video-editing']),
      ('Свой формат', [('demo', 'ai-video-skill', 'Скилл монтажа под свой формат', 'Превратить удачный монтаж в повторяемый скилл агента.', 15,
                         ('Разбираем удачный монтаж', 'Пишем инструкцию скилла', 'Проверяем на новом ролике'))])]),
    ('ai-agents-start', 'Первый ИИ-агент',
     'Что такое агент, из чего он состоит и какие задачи отдать ему первыми.',
     'Поймёте устройство агента и составите список задач для делегирования.',
     'agents', 'agents', 'Для первого урока ничего устанавливать не нужно.',
     [('Что такое агент', ['what-is-ai-agent']),
      ('Запускаем агента', [('demo', 'ai-agents-server', 'Ставим агента на сервер', 'Подготовить сервер и запустить готовую архитектуру агента.', 20,
                            ('Выбираем и оплачиваем сервер', 'Автоустановка агента', 'Подключаем Telegram', 'Первая проверка')),
                            ('demo', 'ai-agents-soul', 'Душа и первые скиллы', 'Описать личность агента и дать ему первые инструкции.', 15,
                            ('Кто ваш агент', 'Цели и границы', 'Первые три скилла'))])]),
]

PRACTICE = {
    'claude-first-result': ('Сохраните свою задачу, запрос, который сработал, и одно уточнение, которое улучшило ответ.',
                            'Задача помещается в 20 минут\nВ запросе есть роль, аудитория, формат и запреты\nПервый ответ оценён: что хорошо и что плохо\nСделано хотя бы одно конкретное уточнение'),
    'chatcut-video-editing': ('Опишите ролик, который собрали, и промпт, который сработал лучше всего.',
                              'Агенту дана цель, порядок и запреты\nПлан монтажа проверен до сборки\nПравки названы таймкодами'),
    'what-is-ai-agent': ('Выпишите в столбик рутинные задачи, которые отдали бы первому агенту.',
                         'Задачи повторяются регулярно\nУ каждой понятен результат\nОтмечено, где нужно ваше подтверждение'),
}


def read_lesson(lesson_id):
    text = (CONTENT_DIR / (lesson_id + '.md')).read_text(encoding='utf-8')
    _, header, body = text.split('---\n', 2)
    meta = dict(line.split(': ', 1) for line in header.strip().splitlines())
    return meta, body.strip()


def parse_blocks(body):
    """Paragraph-separated Markdown subset: ##/### headings, -/1. lists, > quotes,
    !note callouts, ``` code, ![alt](url) images and @video embeds."""
    blocks = []
    for chunk in _chunks(body):
        lines = chunk.split('\n')
        first = lines[0]
        if first.startswith('```'):
            blocks.append(dict(type='code', text='\n'.join(lines[1:-1])))
        elif first.startswith('### '):
            blocks.append(dict(type='h3', text=first[4:]))
        elif first.startswith('## '):
            blocks.append(dict(type='h2', text=first[3:]))
        elif first.startswith('@video '):
            url = first[7:].strip()
            if VIDEO_EMBED.fullmatch(url):
                blocks.append(dict(type='video', url=url))
        elif image := re.fullmatch(r'!\[([^\]]*)\]\((\S+)\)', first):
            if image[2].startswith(IMAGE_HOSTS):
                blocks.append(dict(type='image', alt=image[1], url=image[2]))
        elif first.startswith('!note '):
            blocks.append(dict(type='note', text=chunk[6:]))
        elif all(l.startswith('> ') for l in lines):
            blocks.append(dict(type='quote', text='\n'.join(l[2:] for l in lines)))
        elif all(l.startswith('- ') for l in lines):
            blocks.append(dict(type='ul', items=[l[2:] for l in lines]))
        elif all(re.match(r'\d+\. ', l) for l in lines):
            blocks.append(dict(type='ol', items=[re.sub(r'^\d+\. ', '', l) for l in lines]))
        else:
            blocks.append(dict(type='p', text=chunk))
    return blocks


def _chunks(body):
    """Split on blank lines, keeping fenced code blocks intact."""
    chunks, current, fenced = [], [], False
    for line in body.split('\n'):
        if line.startswith('```'):
            fenced = not fenced
        if not line.strip() and not fenced:
            if current:
                chunks.append('\n'.join(current))
                current = []
            continue
        current.append(line)
    if current:
        chunks.append('\n'.join(current))
    return chunks


def inline(text):
    """Escape, then allow **bold** and [label](https://…) links only."""
    html = str(escape(text))
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\[([^\]]+)\]\((https?://[^\s)&]+(?:&amp;[^\s)&]+)*)\)',
                  r'<a href="\2" rel="noopener noreferrer" target="_blank">\1 ↗</a>', html)
    return Markup(html.replace('\n', '<br>'))


def render_blocks(body):
    out, step = [], 0
    for b in parse_blocks(body):
        t = b['type']
        if t == 'h2':
            step += 1  # anchors for the "В этом уроке" step list
            out.append(f'<h2 id="step-{step}">{escape(b["text"])}</h2>')
        elif t == 'h3':
            out.append(f'<h3>{escape(b["text"])}</h3>')
        elif t == 'p':
            out.append(f'<p>{inline(b["text"])}</p>')
        elif t in ('ul', 'ol'):
            out.append(f'<{t}>' + ''.join(f'<li>{inline(i)}</li>' for i in b['items']) + f'</{t}>')
        elif t == 'quote':
            out.append(f'<blockquote class="lesson-example"><p>{inline(b["text"])}</p></blockquote>')
        elif t == 'note':
            out.append(f'<aside class="lesson-note"><p>{inline(b["text"])}</p></aside>')
        elif t == 'code':
            out.append(f'<figure class="lesson-prompt"><pre>{escape(b["text"])}</pre>'
                       '<button type="button" class="button secondary" data-copy-block>Скопировать</button>'
                       '<span class="copy-status" role="status"></span></figure>')
        elif t == 'image':
            out.append(f'<figure class="lesson-figure"><img src="{escape(b["url"])}" alt="{escape(b["alt"])}" loading="lazy" decoding="async"></figure>')
        elif t == 'video':
            out.append(f'<div class="lesson-embed"><iframe src="{escape(b["url"])}" title="Видео к уроку" loading="lazy" '
                       'allow="autoplay; fullscreen; picture-in-picture; encrypted-media" allowfullscreen></iframe></div>')
    return Markup('\n'.join(out))


def outline(body):
    return [b['text'] for b in parse_blocks(body) if b['type'] == 'h2']


def ensure_schema(db):
    columns = {r[1] for r in db.execute('PRAGMA table_info(lessons)')}
    if 'body_format' not in columns:
        db.execute("ALTER TABLE lessons ADD COLUMN body_format TEXT NOT NULL DEFAULT 'text'")
    db.execute('''CREATE TABLE IF NOT EXISTS lesson_profiles (
        lesson_id TEXT PRIMARY KEY REFERENCES lessons(id), branch TEXT NOT NULL,
        level TEXT NOT NULL CHECK(level IN ('beginner','intermediate','advanced')),
        format TEXT NOT NULL, source_url TEXT, demo INTEGER NOT NULL DEFAULT 0)''')


def install(db, retire_synthetic=False):
    ensure_schema(db)
    for course_id, title, description, outcome, goal, branch, tools, modules in COURSES:
        level = 'beginner'
        db.execute('''INSERT INTO courses(id,title,description,outcome,goal,level,tools,prerequisites,author,updated_at,status)
            VALUES(?,?,?,?,?,?,?,?,?,?,'published') ON CONFLICT(id) DO UPDATE SET title=excluded.title,
            description=excluded.description,outcome=excluded.outcome,tools=excluded.tools,updated_at=excluded.updated_at''',
            (course_id, title, description, outcome, goal, LEVELS[level], tools, 'Не нужны', 'AI Room', datetime.now(timezone.utc).date().isoformat()))
        for m_index, (module_title, lessons) in enumerate(modules):
            module_id = f'{course_id}-m{m_index + 1}'
            db.execute('INSERT INTO modules VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,position=excluded.position',
                       (module_id, course_id, module_title, m_index))
            for position, spec in enumerate(lessons):
                if isinstance(spec, tuple):
                    _, lesson_id, lesson_title, objective, minutes, parts = spec
                    body, access, source, fmt, demo, task, checklist = demo_body(parts), 'member', None, 'lesson', 1, None, None
                else:
                    meta, body = read_lesson(spec)
                    lesson_id, lesson_title, objective, minutes = meta['id'], meta['title'], meta['summary'], int(meta['minutes'])
                    access, source, fmt, demo = meta['access'], meta['source'], meta['format'], 0
                    level = meta['level']
                    task, checklist = PRACTICE.get(lesson_id, (None, None))
                db.execute('''INSERT INTO lessons(id,module_id,title,objective,body,minutes,position,access,task,checklist,status,body_format)
                    VALUES(?,?,?,?,?,?,?,?,?,?,'published','blocks') ON CONFLICT(id) DO UPDATE SET module_id=excluded.module_id,
                    title=excluded.title,objective=excluded.objective,body=excluded.body,minutes=excluded.minutes,
                    position=excluded.position,access=excluded.access,task=excluded.task,checklist=excluded.checklist,body_format='blocks' ''',
                    (lesson_id, module_id, lesson_title, objective, body, minutes, position, access, task, checklist))
                db.execute('''INSERT INTO lesson_profiles VALUES(?,?,?,?,?,?) ON CONFLICT(lesson_id) DO UPDATE SET
                    branch=excluded.branch,level=excluded.level,format=excluded.format,source_url=excluded.source_url,demo=excluded.demo''',
                    (lesson_id, branch, level if not demo else 'beginner', fmt, source, demo))
    if retire_synthetic:
        legacy_ids = [c[0] for c in COURSES]
        db.execute(f"UPDATE courses SET status='archived' WHERE id NOT IN ({','.join('?' * len(legacy_ids))}) AND status='published'", legacy_ids)
        db.execute("UPDATE materials SET status='archived' WHERE status='published'")


def register_legacy_content(app, db):
    app.jinja_env.filters['lesson_blocks'] = render_blocks
    app.jinja_env.filters['lesson_outline'] = outline

    @app.cli.command('install-legacy-lessons')
    @click.option('--retire-synthetic', is_flag=True, help='Archive synthetic fixture courses (learner rows are kept).')
    def install_legacy_lessons(retire_synthetic):
        """Install selected free lessons from the original platform and demo member lessons."""
        database = Path(app.config['DATABASE'])
        backup = database.with_name(database.name + '.before-legacy-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f') + '.sqlite')
        with sqlite3.connect(backup) as dest:
            db().backup(dest)
        backup.chmod(0o600)
        with db():
            install(db(), retire_synthetic)
        click.echo('Legacy lessons installed. Backup: ' + str(backup))
