"""Attached sessions: a learner gives their own AI assistant (Claude, ChatGPT, Claude Code…) a
one-time link. The first real fetch of the link claims it and returns a document with the lesson and a
scoped access key; later calls use that key (HTTP under /api/agent/ or MCP at /mcp) and can read the
learner's lessons, save practice and mark sections reached. See docs/design/attached-sessions.md.

- Links and keys are stored as SHA-256 hashes only; a link lives 15 minutes and works once (the claim
  is a single conditional UPDATE, so two fetches can't both win).
- HEAD requests and link-preview bots don't use the link up. Everything else does, browsers included:
  assistants often open links in a real browser (the Claude app does), which looks just like a person.
  Browsers get an HTML page with a save form (a browsing assistant can't send headers, but can submit a
  form); other clients get Markdown.
- A key belongs to one learner, expires after 7 days, can be revoked, and sees exactly what that
  learner can see now (entitlements are re-read on every request). It never grants the web session.
"""
import hashlib
import hmac
import json
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from flask import abort, g, jsonify, request
from markupsafe import Markup, escape
from werkzeug.exceptions import HTTPException

from .legacy_content import render_blocks
from .learning_loop import checkpoints
from .storage import additive_tables

LINK_MINUTES = 15
SESSION_DAYS = 7
MAX_OPEN_LINKS = 5
RATE_LIMIT = (120, 60)   # requests per window (seconds), per key
PROTOCOL_VERSIONS = ('2025-06-18', '2025-03-26', '2024-11-05')
SCHEMA = (
    '''CREATE TABLE IF NOT EXISTS attach_links (
     id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), token_hash TEXT NOT NULL,
     lesson_id TEXT, draft TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, expires_at TEXT NOT NULL,
     consumed_at TEXT, session_id TEXT)''',
    '''CREATE TABLE IF NOT EXISTS connected_sessions (
     id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), token_hash TEXT NOT NULL,
     label TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, expires_at TEXT NOT NULL,
     last_used_at TEXT, revoked_at TEXT)''',
    '''CREATE TABLE IF NOT EXISTS practice_origins (
     user_id TEXT NOT NULL REFERENCES users(id), lesson_id TEXT NOT NULL REFERENCES lessons(id),
     session_id TEXT NOT NULL, saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,lesson_id))''',
)
LINK = re.compile(r'al_([0-9a-f]{12})_[A-Za-z0-9_-]{24,64}')
KEY = re.compile(r'Bearer (as_([0-9a-f]{12})_[A-Za-z0-9_-]{24,64})')
PREVIEW_BOTS = re.compile(r'Slackbot|TelegramBot|facebookexternalhit|Twitterbot|WhatsApp|Discordbot|LinkedInBot|SkypeUriPreview|'
                          r'vkShare|redditbot|Iframely|Embedly|Applebot|Googlebot|bingbot|YandexBot|Mastodon|Pinterest', re.I)


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def utc(delta=timedelta()):
    return (datetime.now(timezone.utc) + delta).strftime('%Y-%m-%d %H:%M:%S')


def client_label(name):
    """A human name for the connected client, from a User-Agent or MCP clientInfo."""
    value = (name or '').lower()
    if 'claude-code' in value or 'claude code' in value:
        return 'Claude Code'
    if 'claude' in value:
        return 'Claude'
    if 'chatgpt' in value or 'openai' in value:
        return 'ChatGPT'
    if 'codex' in value:
        return 'Codex'
    if 'cursor' in value:
        return 'Cursor'
    return 'ИИ-ассистент'


def lesson_text(lesson):
    """The lesson body as readable Markdown for an assistant (videos become a note)."""
    body = lesson['body'] or ''
    return re.sub(r'(?m)^@video (\S+)$', r'[Видео в уроке: \1]', body).strip()


def register_attach(app, db, query, require_user, get_lesson, event, loop, store_practice, continue_url, continuation):
    ensure = additive_tables(app, SCHEMA)

    def public_base():
        return (app.config.get('PUBLIC_URL') or request.host_url).rstrip('/')

    # ---- Keys on agent requests (called from load_user, before anything else) ----
    calls = defaultdict(deque)

    def is_agent_request():
        return request.path == '/mcp' or request.path.startswith('/api/agent/')

    def authenticate():
        """Sets g.user and g.agent_session from a valid key; agents never use the browser session."""
        g.user = g.agent_session = None
        header = request.headers.get('Authorization', '')
        if not header and request.method == 'POST' and request.mimetype == 'application/x-www-form-urlencoded':
            header = 'Bearer ' + request.form.get('key', '')   # the save form on the link page
        match = KEY.fullmatch(header)
        if not match:
            return
        ensure()
        row = query('SELECT * FROM connected_sessions WHERE id=?', (match[2],), True)
        if (not row or not hmac.compare_digest(row['token_hash'], digest(match[1]))
                or row['revoked_at'] or row['expires_at'] <= utc()):
            return
        limit, window = RATE_LIMIT
        recent, now = calls[row['id']], time.monotonic()
        while recent and now - recent[0] > window:
            recent.popleft()
        if len(recent) >= limit:
            abort(429, 'Слишком много запросов. Подождите минуту.')
        recent.append(now)
        g.user = query('SELECT * FROM users WHERE id=?', (row['user_id'],), True)
        g.agent_session = row
        if not row['last_used_at'] or row['last_used_at'] < utc(timedelta(minutes=-5)):
            with db():
                db().execute('UPDATE connected_sessions SET last_used_at=CURRENT_TIMESTAMP WHERE id=?', (row['id'],))

    def require_agent(fn):
        def wrapped(*args, **kwargs):
            if not g.get('agent_session'):
                response = jsonify(error='unauthorized', message='Нужен действующий ключ AI Room: заголовок Authorization: Bearer as_…')
                response.status_code = 401
                # Points OAuth clients (claude.ai, ChatGPT connectors) to discovery: club/oauth.py.
                response.headers['WWW-Authenticate'] = f'Bearer realm="ai-room", resource_metadata="{public_base()}/.well-known/oauth-protected-resource/mcp"'
                return response
            return fn(*args, **kwargs)
        wrapped.__name__ = fn.__name__
        return wrapped

    # ---- What an assistant sees ----
    def lesson_payload(lesson_id, draft=None):
        lesson = get_lesson(lesson_id)   # 403 for a club lesson the learner can't open
        titles = checkpoints(lesson)
        progress = loop['step_progress'](lesson_id) or {}
        furthest, last = progress.get('furthest', 0), progress.get('last', 0)
        practice = query('SELECT body,status,updated_at FROM practice WHERE user_id=? AND lesson_id=?', (g.user['id'], lesson_id), True)
        done = query('SELECT completed FROM progress WHERE user_id=? AND lesson_id=?', (g.user['id'], lesson_id), True)
        return dict(
            id=lesson['id'], title=lesson['title'], course=lesson['course_title'], objective=lesson['objective'],
            minutes=lesson['minutes'], url=f'{public_base()}/lessons/{lesson["id"]}', completed=bool(done and done['completed']),
            sections=[dict(number=i + 1, title=t, reached=i + 1 <= furthest) for i, t in enumerate(titles)],
            current_section=last or None, task=lesson['task'],
            checklist=lesson['checklist'].split('\n') if lesson['checklist'] else [],
            practice=dict(practice) if practice else None, unsaved_draft=draft or None, text=lesson_text(lesson))

    def status():
        unfinished = continuation()['unfinished']
        briefing = loop['briefing'](unfinished)
        plan = loop['plan']()
        return dict(learner=g.user['name'], current_lesson=dict(id=briefing['lesson_id'], title=briefing['title'], course=briefing['course'],
                                                                 status=briefing['status'], section=briefing['step']) if briefing else None,
                    plan=plan if plan and plan['days'] else None, next_url=public_base() + continue_url())

    def save(lesson_id, body, practice_status='draft'):
        store_practice(lesson_id, body, practice_status)
        with db():
            db().execute('''INSERT INTO practice_origins(user_id,lesson_id,session_id) VALUES(?,?,?) ON CONFLICT(user_id,lesson_id)
                DO UPDATE SET session_id=excluded.session_id,saved_at=CURRENT_TIMESTAMP''', (g.user['id'], lesson_id, g.agent_session['id']))
        row = query('SELECT body,status,updated_at FROM practice WHERE user_id=? AND lesson_id=?', (g.user['id'], lesson_id), True)
        return dict(saved=dict(row), where=f'{public_base()}/profile#practice')

    def mark(lesson_id, section):
        return loop['record_step'](get_lesson(lesson_id), section)

    def review(lesson_id):
        data = lesson_payload(lesson_id)
        return dict(lesson=data['title'], task=data['task'], checklist=data['checklist'], practice=data['practice'],
                    note='Сравните работу с каждым критерием и предложите улучшения. Это ваш отзыв как ассистента, не оценка AI Room.')

    # ---- The link ----
    def note_origin_cleared(lesson_id):
        """A save from the website replaces one made by an assistant."""
        ensure()
        db().execute('DELETE FROM practice_origins WHERE user_id=? AND lesson_id=?', (g.user['id'], lesson_id))

    def origin(lesson_id):
        if not g.user:
            return None
        ensure()
        row = query('''SELECT s.label FROM practice_origins o JOIN connected_sessions s ON s.id=o.session_id
            WHERE o.user_id=? AND o.lesson_id=?''', (g.user['id'], lesson_id), True)
        return row['label'] if row else None

    @app.post('/api/app/attach-links')
    @require_user
    def create_link():
        data = request.get_json(silent=True) or {}
        lesson_id, draft = data.get('lesson_id'), data.get('draft')
        if lesson_id is not None:
            if not isinstance(lesson_id, str):
                abort(400)
            get_lesson(lesson_id)
        if draft is not None and (not isinstance(draft, str) or len(draft) > 12000):
            abort(400)
        ensure()
        with db():   # drafts of links nobody used don't linger
            db().execute('UPDATE attach_links SET draft=NULL WHERE user_id=? AND draft IS NOT NULL AND expires_at<=?', (g.user['id'], utc()))
        open_links = query("SELECT COUNT(*) n FROM attach_links WHERE user_id=? AND consumed_at IS NULL AND expires_at>?",
                           (g.user['id'], utc()), True)['n']
        if open_links >= MAX_OPEN_LINKS:
            abort(429, 'Слишком много неиспользованных ссылок. Используйте одну из них или подождите 15 минут.')
        link_id = secrets.token_hex(6)
        token = f'al_{link_id}_{secrets.token_urlsafe(32)}'
        expires = utc(timedelta(minutes=LINK_MINUTES))
        with db():
            db().execute('INSERT INTO attach_links(id,user_id,token_hash,lesson_id,draft,expires_at) VALUES(?,?,?,?,?,?)',
                         (link_id, g.user['id'], digest(token), lesson_id, (draft or '').strip() or None, expires))
        return jsonify(url=f'{public_base()}/attach/{token}', expires_at=expires, minutes=LINK_MINUTES)

    def stub(text, status=200):
        return app.response_class(text, status=status, mimetype='text/plain', headers={'X-Robots-Tag': 'noindex'})

    @app.route('/attach/<token>', methods=['GET', 'HEAD'])
    def claim(token):
        match = LINK.fullmatch(token)
        ensure()
        link = query('SELECT * FROM attach_links WHERE id=?', (match[1],), True) if match else None
        if not link or not hmac.compare_digest(link['token_hash'], digest(token)):
            return stub('Ссылка не найдена.', 404)
        state = 409 if link['consumed_at'] else 410 if link['expires_at'] <= utc() else 200
        if request.method == 'HEAD':
            return stub('', state)
        if state == 409:
            return stub('Эта ссылка AI Room уже использована. Попросите ученика создать новую в уроке — кнопка «Скопировать ссылку для ассистента».', 409)
        if state == 410:
            return stub('Срок действия ссылки истёк (15 минут). Попросите ученика создать новую в уроке.', 410)
        # A chat app drawing a link preview must not use it up.
        if PREVIEW_BOTS.search(request.headers.get('User-Agent', '')):
            return stub('AI Room: учебная ссылка для ИИ-ассистента. Откройте её в чате с ассистентом.')
        session_id = secrets.token_hex(6)
        key = f'as_{session_id}_{secrets.token_urlsafe(32)}'
        expires = utc(timedelta(days=SESSION_DAYS))
        with db():
            claimed = db().execute('''UPDATE attach_links SET consumed_at=CURRENT_TIMESTAMP,session_id=?
                WHERE id=? AND consumed_at IS NULL AND expires_at>?''', (session_id, link['id'], utc())).rowcount
            if not claimed:   # lost the race to a concurrent fetch
                return stub('Эта ссылка AI Room уже использована.', 409)
            db().execute('INSERT INTO connected_sessions(id,user_id,token_hash,label,expires_at) VALUES(?,?,?,?,?)',
                         (session_id, link['user_id'], digest(key), client_label(request.headers.get('User-Agent')), expires))
            db().execute('UPDATE attach_links SET draft=NULL WHERE id=?', (link['id'],))
        g.user = query('SELECT * FROM users WHERE id=?', (link['user_id'],), True)
        g.agent_session = query('SELECT * FROM connected_sessions WHERE id=?', (session_id,), True)
        with db():
            event('session_connected', link['lesson_id'])
        lesson = context(link)
        if 'text/html' in request.headers.get('Accept', ''):
            return app.response_class(page(lesson, key, expires), mimetype='text/html', headers={'X-Robots-Tag': 'noindex'})
        return app.response_class(document(lesson, key, expires), mimetype='text/markdown', headers={'X-Robots-Tag': 'noindex'})

    def context(link):
        lesson_id = link['lesson_id'] or (continuation()['unfinished'] or {}).get('lesson_id')
        if not lesson_id:
            return None
        try:
            return lesson_payload(lesson_id, link['draft'])
        except HTTPException:   # e.g. the learner lost access to a club lesson meanwhile
            return None

    def document(lesson, key, expires):
        base = public_base()
        out = [f'# AI Room: учебная ссылка от ученика ({g.user["name"]})', '',
               'Ученик учебной платформы AI Room прислал вам эту ссылку, чтобы вы помогли ему с обучением. '
               'Ниже — его урок и ключ доступа, через который можно сохранить результат в его аккаунт.', '']
        if lesson:
            out += [f'## Урок: {lesson["title"]}', f'Курс «{lesson["course"]}» · около {lesson["minutes"]} минут · {lesson["url"]}',
                    f'Цель урока: {lesson["objective"]}', '']
            if lesson['sections']:
                out.append('Разделы урока:')
                for s in lesson['sections']:
                    mark_ = ' ✓' if s['reached'] else ''
                    here = ' ← ученик здесь' if s['number'] == lesson['current_section'] else ''
                    out.append(f'{s["number"]}. {s["title"]}{mark_}{here}')
                out.append('')
            if lesson['task']:
                out += ['### Задание', lesson['task'], '']
                if lesson['checklist']:
                    out += ['### Критерии хорошего результата', *[f'- {c}' for c in lesson['checklist']], '']
                draft = lesson['unsaved_draft'] or (lesson['practice'] or {}).get('body')
                if draft:
                    out += ['### Черновик ученика', '"""', draft, '"""', '']
                out += ['### Как помочь',
                        '1. Спросите, к какой своей задаче ученик применяет урок, — по одному вопросу за раз.',
                        '2. Помогайте шаг за шагом; не делайте работу целиком за него.',
                        '3. Проверьте результат по критериям выше и подскажите, что улучшить.',
                        '4. Когда ученик доволен итогом, предложите сохранить его в AI Room (как — ниже).', '']
            else:
                out += ['### Как помочь', 'Спросите, над чем ученик работает, и объясните главное из урока на его примере. Вопросы задавайте по одному.', '']
        else:
            out += ['Сейчас у ученика нет начатого урока. Спросите, чему он хочет научиться; статус и следующий шаг — ниже.', '']
        out += ['## Доступ к AI Room',
                f'Ключ действует до {expires} UTC. Ученик может отключить его в «Профиль → Подключения». '
                'Используйте ключ только для этой учебной работы и не публикуйте его.', '',
                '```', f'Authorization: Bearer {key}', '```', '',
                'HTTP (JSON):',
                f'- `GET {base}/api/agent/status` — где ученик сейчас и что дальше',
                f'- `GET {base}/api/agent/lessons/<id>` — урок: разделы, задание, критерии, текст']
        if lesson:
            out += [f'- `POST {base}/api/agent/lessons/{lesson["id"]}/practice` с телом `{{"body": "…", "status": "draft"}}` — сохранить работу '
                    '(`"submitted"` — итоговая версия). Она появится у ученика в «Моих работах» с пометкой, что сохранена ассистентом.',
                    f'- `POST {base}/api/agent/lessons/{lesson["id"]}/step` с телом `{{"section": 3}}` — отметить раздел, до которого дошли', '',
                    'Пример:', '```',
                    f'curl -X POST {base}/api/agent/lessons/{lesson["id"]}/practice \\',
                    f'  -H "Authorization: Bearer {key}" -H "Content-Type: application/json" \\',
                    '  -d \'{"body": "Итоговый текст работы", "status": "submitted"}\'', '```']
        out += ['', f'MCP (например, Claude Code): `claude mcp add --transport http airoom {base}/mcp --header "Authorization: Bearer {key}"` — '
                'инструменты learning_status, get_lesson, next_step, save_practice, mark_section, review_checklist.', '',
                'Если вы не можете отправлять HTTP-запросы (обычный чат), просто помогите ученику по уроку — итог он вставит в AI Room сам.', '',
                'Завершить урок ученик отмечает сам на сайте; ассистент этого не делает.']
        if lesson:
            out += ['', '## Текст урока', '', lesson['text']]
        return '\n'.join(out) + '\n'

    def page(lesson, key, expires):
        """The link as a web page, for assistants that open links in a browser: the same content as the
        Markdown document plus a form that saves the work (the key travels in the form)."""
        base = public_base()
        h = lambda value: escape(value)
        parts = ['<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
                 '<meta name="robots" content="noindex"><title>Урок для ИИ-ассистента · AI Room</title><link rel="stylesheet" href="/static/attach.css"></head>',
                 '<body><main>', '<p class="eyebrow">AI Room · страница для ИИ-ассистента</p>',
                 f'<h1>{h(lesson["title"]) if lesson else "Обучение в AI Room"}</h1>',
                 f'<p class="lead">Ученик ({h(g.user["name"])}) открыл эту страницу для своего ИИ-ассистента, чтобы тот помог с уроком: '
                 'ниже урок, задание и форма, которой можно сохранить работу ученика в AI Room.</p>',
                 '<p class="note">Если вы ученик и открыли страницу сами — ничего страшного: в уроке можно создать новую ссылку для ассистента, '
                 'а это подключение отключается в «Профиль → Подключения».</p>']
        if lesson:
            parts.append(f'<p class="meta">Курс «{h(lesson["course"])}» · около {lesson["minutes"]} минут · <a href="{h(lesson["url"])}">урок на сайте</a></p>')
            parts.append(f'<p><strong>Цель урока:</strong> {h(lesson["objective"])}</p>')
            if lesson['sections']:
                items = ''.join(f'<li>{h(s["title"])}{" ✓" if s["reached"] else ""}{" <em>← ученик здесь</em>" if s["number"] == lesson["current_section"] else ""}</li>'
                                for s in lesson['sections'])
                parts.append(f'<h2>Разделы урока</h2><ol>{items}</ol>')
            draft = lesson['unsaved_draft'] or (lesson['practice'] or {}).get('body') or ''
            if lesson['task']:
                parts.append(f'<h2>Задание</h2><p>{h(lesson["task"])}</p>')
                if lesson['checklist']:
                    parts.append('<h2>Критерии хорошего результата</h2><ul>' + ''.join(f'<li>{h(c)}</li>' for c in lesson['checklist']) + '</ul>')
                if draft:
                    parts.append(f'<h2>Черновик ученика</h2><pre>{h(draft)}</pre>')
                parts.append('<h2>Как помочь</h2><ol><li>Спросите, к какой своей задаче ученик применяет урок, — по одному вопросу за раз.</li>'
                             '<li>Помогайте шаг за шагом; не делайте работу целиком за него.</li>'
                             '<li>Проверьте результат по критериям и подскажите, что улучшить.</li>'
                             '<li>Когда ученик доволен итогом, сохраните его формой ниже (с согласия ученика).</li></ol>')
                parts.append(f'<section class="save" id="save"><h2>Сохранить работу в AI Room</h2>'
                             f'<p>Работа появится у ученика в «Моих работах» с пометкой, что её сохранил ассистент.</p>'
                             f'<form method="post" action="/api/agent/lessons/{h(lesson["id"])}/practice">'
                             f'<input type="hidden" name="key" value="{h(key)}">'
                             f'<label for="body">Текст работы</label><textarea id="body" name="body" rows="10" maxlength="12000" required>{h(draft)}</textarea>'
                             '<fieldset><legend>Это</legend><label><input type="radio" name="status" value="draft" checked> черновик</label>'
                             '<label><input type="radio" name="status" value="submitted"> итоговая версия</label></fieldset>'
                             '<button type="submit">Сохранить в AI Room</button></form></section>')
            else:
                parts.append('<h2>Как помочь</h2><p>Спросите, над чем ученик работает, и объясните главное из урока на его примере. Вопросы задавайте по одному.</p>')
        else:
            parts.append('<p>Сейчас у ученика нет начатого урока. Спросите, чему он хочет научиться.</p>')
        parts.append(f'<details><summary>Доступ через API и MCP</summary><p>Ключ действует до {h(expires)} UTC; используйте его только для этой учебной работы.</p>'
                     f'<pre>Authorization: Bearer {h(key)}</pre><ul>'
                     f'<li><code>GET {h(base)}/api/agent/status</code> — где ученик сейчас</li>'
                     f'<li><code>GET {h(base)}/api/agent/lessons/&lt;id&gt;</code> — урок</li>'
                     f'<li><code>POST {h(base)}/api/agent/lessons/&lt;id&gt;/practice</code> с JSON <code>{{"body": "…", "status": "draft"}}</code></li>'
                     f'<li>MCP: <code>{h(base)}/mcp</code> с тем же заголовком</li></ul></details>')
        parts.append('<p class="note">Завершить урок ученик отмечает сам на сайте; ассистент этого не делает.</p>')
        if lesson:
            lesson_row = get_lesson(lesson['id'])
            blocks = 'body_format' in lesson_row.keys() and lesson_row['body_format'] == 'blocks'
            body = render_blocks(lesson_row['body']) if blocks else Markup(''.join(f'<p>{h(p)}</p>' for p in lesson_row['body'].split('\n\n')))
            parts.append(f'<h2>Текст урока</h2><article class="lesson">{body}</article>')
        parts.append('</main></body></html>')
        return ''.join(str(x) for x in parts)

    def saved_page(result):
        saved = result['saved']
        return ('<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                '<meta name="robots" content="noindex"><title>Работа сохранена · AI Room</title><link rel="stylesheet" href="/static/attach.css"></head>'
                f'<body><main><p class="eyebrow">AI Room</p><h1>Работа сохранена ✓</h1>'
                f'<p>{"Итоговая версия" if saved["status"] == "submitted" else "Черновик"} теперь в «Моих работах» ученика. '
                'Чтобы обновить её, вернитесь на предыдущую страницу и сохраните ещё раз.</p>'
                f'<pre>{escape(saved["body"])}</pre></main></body></html>')

    # ---- Agent HTTP API ----
    def body_of():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            abort(400, 'Ожидается JSON-объект.')
        return data

    @app.get('/api/agent/status')
    @require_agent
    def agent_status():
        return jsonify(status())

    @app.get('/api/agent/lessons/<lesson_id>')
    @require_agent
    def agent_lesson(lesson_id):
        return jsonify(lesson_payload(lesson_id))

    @app.post('/api/agent/lessons/<lesson_id>/practice')
    @require_agent
    def agent_practice(lesson_id):
        if request.mimetype == 'application/x-www-form-urlencoded':   # the form on the link page
            result = save(lesson_id, request.form.get('body'), request.form.get('status', 'draft'))
            return app.response_class(saved_page(result), mimetype='text/html')
        data = body_of()
        return jsonify(save(lesson_id, data.get('body'), data.get('status', 'draft')))

    @app.post('/api/agent/lessons/<lesson_id>/step')
    @require_agent
    def agent_step(lesson_id):
        data = body_of()
        return jsonify(mark(lesson_id, data.get('section', data.get('step'))))

    @app.get('/api/agent/next')
    @require_agent
    def agent_next():
        return jsonify(url=public_base() + continue_url())

    # ---- MCP (Streamable HTTP, stateless JSON responses) ----
    def schema(properties=None, required=()):
        return dict(type='object', properties=properties or {}, required=list(required), additionalProperties=False)

    lesson_arg = dict(lesson_id=dict(type='string', description='ID урока (из learning_status или get_lesson)'))
    tools = [
        dict(name='learning_status', title='Где ученик сейчас',
             description='Текущий урок ученика в AI Room, раздел, его план занятий и ссылка на следующий шаг.', inputSchema=schema()),
        dict(name='get_lesson', title='Урок',
             description='Урок AI Room: цель, разделы (какие пройдены), задание, критерии, сохранённая работа и текст. Без lesson_id — текущий урок.',
             inputSchema=schema(dict(lesson_id=dict(type='string', description='ID урока; по умолчанию — текущий')))),
        dict(name='next_step', title='Что дальше', description='Ссылка, по которой ученик продолжит обучение.', inputSchema=schema()),
        dict(name='save_practice', title='Сохранить работу',
             description='Сохраняет работу ученика по уроку в «Мои работы» (draft — черновик, submitted — итог). Сохраняйте только с согласия ученика.',
             inputSchema=schema(dict(**lesson_arg, body=dict(type='string', description='Текст работы, до 12 000 символов'),
                                     status=dict(type='string', enum=['draft', 'submitted'])), ('lesson_id', 'body'))),
        dict(name='mark_section', title='Отметить раздел',
             description='Отмечает раздел урока, до которого дошёл ученик (номер с 1).',
             inputSchema=schema(dict(**lesson_arg, section=dict(type='integer', minimum=1)), ('lesson_id', 'section'))),
        dict(name='review_checklist', title='Критерии для проверки',
             description='Задание, критерии и сохранённая работа — чтобы вы проверили работу ученика. Это ваш отзыв, не оценка AI Room.',
             inputSchema=schema(lesson_arg, ('lesson_id',))),
    ]

    def current_lesson():
        unfinished = continuation()['unfinished']
        if not unfinished:
            abort(404, 'У ученика нет начатого урока. Посмотрите learning_status или спросите, какой урок открыть.')
        return unfinished['lesson_id']

    def call(name, args):
        if not isinstance(args, dict):
            abort(400, 'arguments должен быть объектом.')
        if name == 'learning_status':
            return status()
        if name == 'get_lesson':
            return lesson_payload(args.get('lesson_id') or current_lesson())
        if name == 'next_step':
            return dict(url=public_base() + continue_url())
        if name == 'save_practice':
            return save(str(args.get('lesson_id', '')), args.get('body'), args.get('status', 'draft'))
        if name == 'mark_section':
            return mark(str(args.get('lesson_id', '')), args.get('section'))
        if name == 'review_checklist':
            return review(str(args.get('lesson_id', '')))
        abort(404, f'Неизвестный инструмент: {name}')

    def handle(message):
        if not isinstance(message, dict) or message.get('jsonrpc') != '2.0':
            return dict(jsonrpc='2.0', id=None, error=dict(code=-32600, message='Invalid Request'))
        method, ident, params = message.get('method'), message.get('id'), message.get('params') or {}
        if ident is None:   # notification (e.g. notifications/initialized)
            return None
        reply = lambda result: dict(jsonrpc='2.0', id=ident, result=result)
        if method == 'initialize':
            client = (params.get('clientInfo') or {}).get('name') if isinstance(params, dict) else None
            if client:
                with db():
                    db().execute('UPDATE connected_sessions SET label=? WHERE id=?', (client_label(client), g.agent_session['id']))
            asked = params.get('protocolVersion') if isinstance(params, dict) else None
            return reply(dict(protocolVersion=asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                              capabilities=dict(tools=dict(listChanged=False)),
                              serverInfo=dict(name='ai-room', title='AI Room', version='1.0'),
                              instructions='AI Room — учебная платформа. Помогайте ученику с его уроком: начните с learning_status или get_lesson. '
                                           'Сохраняйте работу (save_practice) только с согласия ученика; урок завершает он сам на сайте.'))
        if method == 'ping':
            return reply({})
        if method == 'tools/list':
            return reply(dict(tools=tools))
        if method == 'tools/call':
            try:
                data = call(params.get('name'), params.get('arguments') or {})
                return reply(dict(content=[dict(type='text', text=json.dumps(data, ensure_ascii=False, indent=1))], isError=False))
            except HTTPException as error:
                return reply(dict(content=[dict(type='text', text=error.description or error.name)], isError=True))
        return dict(jsonrpc='2.0', id=ident, error=dict(code=-32601, message=f'Method not found: {method}'))

    @app.route('/mcp', methods=['GET', 'POST', 'DELETE'])
    @require_agent
    def mcp():
        if request.method != 'POST':
            return app.response_class(status=405, headers={'Allow': 'POST'})
        message = request.get_json(silent=True)
        if message is None:
            return jsonify(jsonrpc='2.0', id=None, error=dict(code=-32700, message='Parse error')), 400
        if isinstance(message, list):
            replies = [r for r in (handle(m) for m in message) if r]
            return jsonify(replies) if replies else app.response_class(status=202)
        result = handle(message)
        return jsonify(result) if result else app.response_class(status=202)

    # ---- Connections, for the learner ----
    def connections():
        if not g.user:
            return []
        ensure()
        return [dict(r) for r in query('''SELECT id,label,created_at,last_used_at,expires_at FROM connected_sessions
            WHERE user_id=? AND revoked_at IS NULL AND expires_at>? ORDER BY created_at DESC''', (g.user['id'], utc()))]

    @app.get('/api/app/connections')
    @require_user
    def list_connections():
        return jsonify(connections=connections())

    @app.delete('/api/app/connections/<session_id>')
    @require_user
    def revoke_connection(session_id):
        ensure()
        with db():
            changed = db().execute('UPDATE connected_sessions SET revoked_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=? AND revoked_at IS NULL',
                                   (session_id, g.user['id'])).rowcount
        if not changed:
            abort(404)
        return jsonify(connections=connections())

    return dict(is_agent_request=is_agent_request, authenticate=authenticate, connections=connections,
                origin=origin, clear_origin=note_origin_cleared)
