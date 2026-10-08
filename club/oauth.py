"""OAuth 2.1 for the MCP connector (phase 3 of attached sessions; docs/design/attached-sessions.md).

claude.ai and ChatGPT connect to remote MCP servers only through OAuth: dynamic client registration
(RFC 7591), authorization code + PKCE S256, protected-resource and authorization-server metadata
(RFC 9728, RFC 8414). The learner approves on AI Room's own consent page while logged in.

It is the attach-link scheme in standard form: the authorization code is the one-time code (hashed,
10 minutes, single use, bound to client, redirect URI and PKCE challenge), and the access token is the
same scoped key as an attach link's (connected_sessions, listed and revocable in Подключения). Access
tokens last a day; refresh tokens rotate on use and last 30 days. Tokens are stored as hashes only.
"""
import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import timedelta
from urllib.parse import urlencode, urlsplit

from flask import abort, g, jsonify, redirect, request, session

from .attach import SCHEMA as SESSION_SCHEMA, SCOPE_COLUMNS, client_label, digest, utc
from .storage import additive_tables

SCOPE = 'learning'
SCOPES = ('learning', 'content')   # content: editors' assistants at /mcp/admin (club/assist.py)
CODE_MINUTES = 10
ACCESS_HOURS = 24
REFRESH_DAYS = 30
SCHEMA = (
    '''CREATE TABLE IF NOT EXISTS oauth_clients (
     id TEXT PRIMARY KEY, name TEXT NOT NULL, redirect_uris TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''',
    '''CREATE TABLE IF NOT EXISTS oauth_codes (
     id TEXT PRIMARY KEY, code_hash TEXT NOT NULL, client_id TEXT NOT NULL REFERENCES oauth_clients(id),
     user_id TEXT NOT NULL REFERENCES users(id), redirect_uri TEXT NOT NULL, challenge TEXT NOT NULL,
     expires_at TEXT NOT NULL, used_at TEXT)''',
    '''CREATE TABLE IF NOT EXISTS oauth_refresh (
     session_id TEXT PRIMARY KEY REFERENCES connected_sessions(id), client_id TEXT NOT NULL REFERENCES oauth_clients(id),
     refresh_hash TEXT NOT NULL, expires_at TEXT NOT NULL)''',
)
CLIENT_ID = re.compile(r'oc_[0-9a-f]{24}')
CODE = re.compile(r'oa_([0-9a-f]{12})_[A-Za-z0-9_-]{24,64}')
REFRESH = re.compile(r'or_([0-9a-f]{12})_[A-Za-z0-9_-]{24,64}')
CHALLENGE = re.compile(r'[A-Za-z0-9_-]{43,128}')
VERIFIER = re.compile(r'[A-Za-z0-9._~-]{43,128}')


def allowed_redirect(uri):
    """https anywhere, or http on localhost (desktop clients and local testing); no fragments."""
    if not isinstance(uri, str) or len(uri) > 500 or '#' in uri:
        return False
    parts = urlsplit(uri)
    if parts.username or parts.password:
        return False
    return (parts.scheme == 'https' and bool(parts.hostname)) or (parts.scheme == 'http' and parts.hostname in ('localhost', '127.0.0.1', '::1'))


def register_oauth(app, db, query, require_user, spa_shell, event):
    ensure = additive_tables(app, SESSION_SCHEMA + SCHEMA, SCOPE_COLUMNS + (('oauth_codes', 'scope', "TEXT NOT NULL DEFAULT 'learning'"),))   # tokens live in connected_sessions
    registrations = defaultdict(deque)

    def base():
        return (app.config.get('PUBLIC_URL') or request.host_url).rstrip('/')

    def oauth_error(error, description, status=400):
        response = jsonify(error=error, error_description=description)
        response.status_code = status
        response.headers['Cache-Control'] = 'no-store'
        return response

    # ---- Discovery ----
    def resource_metadata():
        return jsonify(resource=f'{base()}/mcp', authorization_servers=[base()], scopes_supported=[SCOPE],
                       bearer_methods_supported=['header'], resource_name='AI Room')

    def content_resource_metadata():
        return jsonify(resource=f'{base()}/mcp/admin', authorization_servers=[base()], scopes_supported=['content'],
                       bearer_methods_supported=['header'], resource_name='AI Room · админка')

    app.add_url_rule('/.well-known/oauth-protected-resource', 'oauth_resource', resource_metadata)
    app.add_url_rule('/.well-known/oauth-protected-resource/mcp', 'oauth_resource_mcp', resource_metadata)
    app.add_url_rule('/.well-known/oauth-protected-resource/mcp/admin', 'oauth_resource_mcp_admin', content_resource_metadata)

    def server_metadata():
        return jsonify(issuer=base(), authorization_endpoint=f'{base()}/oauth/authorize', token_endpoint=f'{base()}/oauth/token',
                       registration_endpoint=f'{base()}/oauth/register', scopes_supported=list(SCOPES),
                       response_types_supported=['code'], grant_types_supported=['authorization_code', 'refresh_token'],
                       code_challenge_methods_supported=['S256'], token_endpoint_auth_methods_supported=['none'],
                       service_documentation=f'{base()}/help')

    app.add_url_rule('/.well-known/oauth-authorization-server', 'oauth_server', server_metadata)
    app.add_url_rule('/.well-known/openid-configuration', 'oauth_server_oidc', server_metadata)

    # ---- Dynamic client registration (public clients) ----
    @app.post('/oauth/register')
    def oauth_register():
        ensure()
        recent, now = registrations[request.remote_addr], time.monotonic()
        while recent and now - recent[0] > 3600:
            recent.popleft()
        if len(recent) >= 30:
            return oauth_error('slow_down', 'Too many client registrations from this address.', 429)
        recent.append(now)
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return oauth_error('invalid_client_metadata', 'Expected a JSON object.')
        uris = data.get('redirect_uris')
        if not isinstance(uris, list) or not 1 <= len(uris) <= 5 or not all(allowed_redirect(u) for u in uris):
            return oauth_error('invalid_redirect_uri', 'redirect_uris must be 1-5 https URLs (or http on localhost).')
        if data.get('token_endpoint_auth_method', 'none') != 'none':
            return oauth_error('invalid_client_metadata', 'Only public clients (token_endpoint_auth_method "none") are supported.')
        name = str(data.get('client_name') or 'ИИ-ассистент')[:80]
        client_id = 'oc_' + secrets.token_hex(12)
        with db():
            db().execute('INSERT INTO oauth_clients(id,name,redirect_uris) VALUES(?,?,?)', (client_id, name, json.dumps(uris)))
        response = jsonify(client_id=client_id, client_name=name, redirect_uris=uris, token_endpoint_auth_method='none',
                           grant_types=['authorization_code', 'refresh_token'], response_types=['code'], scope=SCOPE)
        response.status_code = 201
        return response

    # ---- Authorization: validate, remember the request, ask the learner ----
    def client(client_id):
        if not isinstance(client_id, str) or not CLIENT_ID.fullmatch(client_id):
            return None
        ensure()
        row = query('SELECT * FROM oauth_clients WHERE id=?', (client_id,), True)
        return dict(row) | dict(redirect_uris=json.loads(row['redirect_uris'])) if row else None

    @app.get('/oauth/authorize')
    def oauth_authorize():
        args = request.args
        found = client(args.get('client_id'))
        redirect_uri = args.get('redirect_uri')
        # Without a known client and one of its registered redirect URIs we must not redirect anywhere.
        if not found or redirect_uri not in found['redirect_uris']:
            abort(400, 'Приложение не зарегистрировано или адрес возврата не совпадает. Подключите AI Room в ассистенте заново.')

        def back(**params):
            if args.get('state'):
                params['state'] = args['state']
            return redirect(redirect_uri + ('&' if '?' in redirect_uri else '?') + urlencode(params))

        if args.get('response_type') != 'code':
            return back(error='unsupported_response_type')
        if args.get('code_challenge_method') != 'S256' or not CHALLENGE.fullmatch(args.get('code_challenge', '')):
            return back(error='invalid_request', error_description='PKCE S256 is required')
        resource = (args.get('resource') or '').rstrip('/')
        if resource and resource not in (f'{base()}/mcp', f'{base()}/mcp/admin', base()):
            return back(error='invalid_target')
        asked = set(args.get('scope', '').split())
        if asked - set(SCOPES):
            return back(error='invalid_scope')
        # The connector's address decides what it may do: /mcp/admin edits content, /mcp helps a learner.
        scope = 'content' if resource == f'{base()}/mcp/admin' or 'content' in asked else 'learning'
        session['oauth_request'] = dict(client_id=found['id'], redirect_uri=redirect_uri, challenge=args['code_challenge'],
                                        state=args.get('state'), scope=scope)
        return redirect('/oauth/consent' if g.user else '/login?next=/oauth/consent')

    @app.get('/oauth/consent')
    @require_user
    def oauth_consent_page():
        return spa_shell()

    def pending():
        data = session.get('oauth_request')
        found = client(data.get('client_id')) if isinstance(data, dict) else None
        if not found or data.get('redirect_uri') not in found['redirect_uris']:
            abort(404, 'Запрос на подключение не найден или устарел. Начните подключение в ассистенте заново.')
        return data, found

    @app.get('/api/app/oauth/consent')
    @require_user
    def oauth_consent_data():
        data, found = pending()
        scope = data.get('scope', 'learning')
        return jsonify(client=found['name'], label=client_label(found['name']), redirect_host=urlsplit(data['redirect_uri']).hostname,
                       learner=g.user['name'], access_days=REFRESH_DAYS, scope=scope,
                       allowed=scope == 'learning' or g.user['role'] in ('editor', 'admin'))

    @app.post('/api/app/oauth/consent')
    @require_user
    def oauth_consent_decision():
        data, found = pending()
        session.pop('oauth_request', None)
        answer = request.get_json(silent=True) or {}
        target = data['redirect_uri'] + ('&' if '?' in data['redirect_uri'] else '?')
        extra = dict(state=data['state']) if data.get('state') else {}
        scope = data.get('scope', 'learning')
        if answer.get('approve') is not True or (scope == 'content' and g.user['role'] not in ('editor', 'admin')):
            return jsonify(redirect=target + urlencode(dict(error='access_denied', **extra)))
        code_id = secrets.token_hex(6)
        code = f'oa_{code_id}_{secrets.token_urlsafe(32)}'
        with db():
            db().execute('INSERT INTO oauth_codes(id,code_hash,client_id,user_id,redirect_uri,challenge,expires_at,scope) VALUES(?,?,?,?,?,?,?,?)',
                         (code_id, digest(code), found['id'], g.user['id'], data['redirect_uri'], data['challenge'],
                          utc(timedelta(minutes=CODE_MINUTES)), scope))
        return jsonify(redirect=target + urlencode(dict(code=code, **extra)))

    # ---- Token endpoint ----
    def issue(user_id, client_row, session_id=None, scope='learning'):
        """New access + refresh pair; reuses the connection (session_id, and so its scope) on refresh."""
        access_secret = secrets.token_urlsafe(32)
        if session_id is None:
            session_id = secrets.token_hex(6)
            db().execute('INSERT INTO connected_sessions(id,user_id,token_hash,label,expires_at,scope) VALUES(?,?,?,?,?,?)',
                         (session_id, user_id, digest(f'as_{session_id}_{access_secret}'), client_label(client_row['name']),
                          utc(timedelta(hours=ACCESS_HOURS)), scope))
        else:
            scope = query('SELECT scope FROM connected_sessions WHERE id=?', (session_id,), True)['scope']
            db().execute('UPDATE connected_sessions SET token_hash=?,expires_at=? WHERE id=?',
                         (digest(f'as_{session_id}_{access_secret}'), utc(timedelta(hours=ACCESS_HOURS)), session_id))
        refresh = f'or_{session_id}_{secrets.token_urlsafe(32)}'
        db().execute('''INSERT INTO oauth_refresh(session_id,client_id,refresh_hash,expires_at) VALUES(?,?,?,?)
            ON CONFLICT(session_id) DO UPDATE SET refresh_hash=excluded.refresh_hash,expires_at=excluded.expires_at''',
                     (session_id, client_row['id'], digest(refresh), utc(timedelta(days=REFRESH_DAYS))))
        response = jsonify(access_token=f'as_{session_id}_{access_secret}', token_type='Bearer', expires_in=ACCESS_HOURS * 3600,
                           refresh_token=refresh, scope=scope)
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.post('/oauth/token')
    def oauth_token():
        ensure()
        form = request.form
        grant, found = form.get('grant_type'), client(form.get('client_id'))
        if not found:
            return oauth_error('invalid_client', 'Unknown client_id.', 401)
        if grant == 'authorization_code':
            code, verifier = form.get('code', ''), form.get('code_verifier', '')
            match = CODE.fullmatch(code)
            row = query('SELECT * FROM oauth_codes WHERE id=?', (match[1],), True) if match else None
            if (not row or not hmac.compare_digest(row['code_hash'], digest(code)) or row['client_id'] != found['id']
                    or row['used_at'] or row['expires_at'] <= utc() or row['redirect_uri'] != form.get('redirect_uri')):
                return oauth_error('invalid_grant', 'The authorization code is invalid, expired or already used.')
            expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            if not VERIFIER.fullmatch(verifier) or not hmac.compare_digest(expected, row['challenge']):
                return oauth_error('invalid_grant', 'PKCE verification failed.')
            with db():
                if not db().execute('UPDATE oauth_codes SET used_at=CURRENT_TIMESTAMP WHERE id=? AND used_at IS NULL', (row['id'],)).rowcount:
                    return oauth_error('invalid_grant', 'The authorization code was already used.')
                g.user = query('SELECT * FROM users WHERE id=?', (row['user_id'],), True)
                if row['scope'] == 'learning':
                    event('session_connected')
                return issue(row['user_id'], found, scope=row['scope'])
        if grant == 'refresh_token':
            token = form.get('refresh_token', '')
            match = REFRESH.fullmatch(token)
            row = query('''SELECT r.*,s.user_id,s.revoked_at FROM oauth_refresh r JOIN connected_sessions s ON s.id=r.session_id
                WHERE r.session_id=?''', (match[1],), True) if match else None
            if (not row or not hmac.compare_digest(row['refresh_hash'], digest(token)) or row['client_id'] != found['id']
                    or row['revoked_at'] or row['expires_at'] <= utc()):
                return oauth_error('invalid_grant', 'The refresh token is invalid, expired or revoked.')
            with db():
                return issue(row['user_id'], found, row['session_id'])   # rotates the refresh token
        return oauth_error('unsupported_grant_type', 'Use authorization_code or refresh_token.')

    def is_oauth_machine_request():
        """Token and registration calls come from the assistant's servers: no cookies, no CSRF."""
        return request.path in ('/oauth/token', '/oauth/register')

    # Public metadata, registration, token and MCP calls carry no cookies, so browser-based MCP clients may call them.
    @app.after_request
    def cors(response):
        if request.path.startswith('/.well-known/') or request.path in ('/oauth/token', '/oauth/register', '/mcp', '/mcp/admin'):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type, MCP-Protocol-Version, Mcp-Session-Id'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Expose-Headers'] = 'WWW-Authenticate'
        return response

    return dict(is_machine_request=is_oauth_machine_request)
