"""OAuth 2.1 for the MCP connector (claude.ai / ChatGPT): discovery, dynamic registration,
consent, authorization code + PKCE, refresh rotation and revocation."""
import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlsplit

from test_learning import app, login, post
from test_skills import skills
from test_onboarding import onboard
from test_legacy_content import legacy, learner

CALLBACK = 'https://claude.ai/api/mcp/auth_callback'
LESSON = 'claude-first-result'


def pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    return verifier, challenge


def register(machine, **extra):
    return machine.post('/oauth/register', json={'client_name': 'Claude', 'redirect_uris': [CALLBACK], **extra})


def authorize(browser, client_id, challenge, **extra):
    query = dict(response_type='code', client_id=client_id, redirect_uri=CALLBACK, code_challenge=challenge,
                 code_challenge_method='S256', state='xyz', scope='learning', resource='http://localhost/mcp') | extra
    return browser.get('/oauth/authorize', query_string=query)


def token(machine, **form):
    return machine.post('/oauth/token', data=form)


def test_discovery_points_clients_to_the_authorization_server(app):
    c = app.test_client()
    challenge = c.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'})
    assert challenge.status_code == 401
    assert 'resource_metadata="http://localhost/.well-known/oauth-protected-resource/mcp"' in challenge.headers['WWW-Authenticate']
    resource = c.get('/.well-known/oauth-protected-resource/mcp').json
    assert resource['resource'] == 'http://localhost/mcp' and resource['authorization_servers'] == ['http://localhost']
    server = c.get('/.well-known/oauth-authorization-server').json
    assert server['code_challenge_methods_supported'] == ['S256'] and server['registration_endpoint'] == 'http://localhost/oauth/register'
    assert c.get('/.well-known/oauth-authorization-server').headers['Access-Control-Allow-Origin'] == '*'


def test_registration_accepts_only_safe_public_clients(app):
    c = app.test_client()
    assert register(c).status_code == 201   # no CSRF: machine call without cookies
    for bad in [dict(redirect_uris=['http://evil.example/cb']), dict(redirect_uris=['javascript:alert(1)']),
                dict(redirect_uris=['https://user:pw@claude.ai/cb']), dict(redirect_uris=[]),
                dict(token_endpoint_auth_method='client_secret_basic')]:
        assert c.post('/oauth/register', json={'client_name': 'x', 'redirect_uris': [CALLBACK]} | bad).status_code == 400, bad
    assert c.post('/oauth/register', json={'redirect_uris': ['http://localhost:3334/callback']}).status_code == 201


def test_full_connection_flow(legacy):
    machine = legacy.test_client()
    client_id = register(machine).json['client_id']
    verifier, challenge = pkce()
    browser = legacy.test_client()
    assert authorize(browser, client_id, challenge).location == '/login?next=/oauth/consent'   # sign in first
    csrf = login(browser, learner(legacy, 'oauthed', onboarded=True))
    assert browser.get('/oauth/consent').status_code == 200                                   # the request survived login
    consent = browser.get('/api/app/oauth/consent').json
    assert consent['client'] == 'Claude' and consent['redirect_host'] == 'claude.ai'
    assert browser.post('/api/app/oauth/consent', json={'approve': True}).status_code == 400   # CSRF
    target = post(browser, '/api/app/oauth/consent', {'approve': True}, csrf).json['redirect']
    assert target.startswith(CALLBACK + '?')
    query = parse_qs(urlsplit(target).query)
    code = query['code'][0]
    assert query['state'] == ['xyz']
    assert browser.get('/api/app/oauth/consent').status_code == 404                            # the request is used up
    assert token(machine, grant_type='authorization_code', code=code, redirect_uri=CALLBACK, client_id=client_id,
                 code_verifier=secrets.token_urlsafe(48)).json['error'] == 'invalid_grant'     # wrong PKCE verifier
    issued = token(machine, grant_type='authorization_code', code=code, redirect_uri=CALLBACK, client_id=client_id, code_verifier=verifier)
    assert issued.status_code == 200 and 'no-store' in issued.headers['Cache-Control']
    tokens = issued.json
    assert tokens['token_type'] == 'Bearer' and tokens['access_token'].startswith('as_') and tokens['refresh_token'].startswith('or_')
    assert token(machine, grant_type='authorization_code', code=code, redirect_uri=CALLBACK, client_id=client_id,
                 code_verifier=verifier).json['error'] == 'invalid_grant'                      # codes work once
    bot = legacy.test_client()
    bot.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + tokens['access_token']
    assert bot.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}).json['result']['tools']
    saved = bot.post('/mcp', json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                                   'params': {'name': 'save_practice', 'arguments': {'lesson_id': LESSON, 'body': 'Из коннектора Claude'}}}).json
    assert not saved['result']['isError']
    assert browser.get('/api/app/lessons/' + LESSON).json['practice']['via'] == 'Claude'
    connection = browser.get('/api/app/connections').json['connections']
    assert len(connection) == 1 and connection[0]['label'] == 'Claude'
    # refresh rotates both tokens; the old refresh token stops working
    renewed = token(machine, grant_type='refresh_token', refresh_token=tokens['refresh_token'], client_id=client_id).json
    assert renewed['access_token'] != tokens['access_token'] and renewed['refresh_token'] != tokens['refresh_token']
    assert token(machine, grant_type='refresh_token', refresh_token=tokens['refresh_token'], client_id=client_id).json['error'] == 'invalid_grant'
    assert bot.post('/mcp', json={'jsonrpc': '2.0', 'id': 3, 'method': 'ping'}).status_code == 401   # old access token replaced
    bot.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + renewed['access_token']
    assert bot.post('/mcp', json={'jsonrpc': '2.0', 'id': 4, 'method': 'ping'}).status_code == 200
    # the learner switches it off: access and refresh both stop
    assert browser.delete('/api/app/connections/' + connection[0]['id'], headers={'X-CSRF-Token': csrf}).status_code == 200
    assert bot.post('/mcp', json={'jsonrpc': '2.0', 'id': 5, 'method': 'ping'}).status_code == 401
    assert token(machine, grant_type='refresh_token', refresh_token=renewed['refresh_token'], client_id=client_id).json['error'] == 'invalid_grant'


def test_authorization_requests_are_validated_before_anything_redirects(legacy):
    machine = legacy.test_client()
    client_id = register(machine).json['client_id']
    _, challenge = pkce()
    browser = legacy.test_client(); csrf = login(browser, learner(legacy, 'careful', onboarded=True))
    assert authorize(browser, 'oc_' + '0' * 24, challenge).status_code == 400                       # unknown client: no redirect
    assert authorize(browser, client_id, challenge, redirect_uri='https://evil.example/cb').status_code == 400
    missing_pkce = authorize(browser, client_id, '', code_challenge_method='plain')
    assert missing_pkce.location.startswith(CALLBACK) and 'error=invalid_request' in missing_pkce.location
    assert 'error=invalid_target' in authorize(browser, client_id, challenge, resource='https://other.example/mcp').location
    assert authorize(browser, client_id, challenge).location == '/oauth/consent'
    denied = post(browser, '/api/app/oauth/consent', {'approve': False}, csrf).json['redirect']
    assert 'error=access_denied' in denied and 'state=xyz' in denied and 'code=' not in denied
    other = register(machine).json['client_id']
    verifier, challenge = pkce()
    authorize(browser, client_id, challenge)
    code = parse_qs(urlsplit(post(browser, '/api/app/oauth/consent', {'approve': True}, csrf).json['redirect']).query)['code'][0]
    assert token(machine, grant_type='authorization_code', code=code, redirect_uri=CALLBACK, client_id=other,
                 code_verifier=verifier).json['error'] == 'invalid_grant'                              # bound to its client
    assert token(machine, grant_type='password', client_id=client_id).json['error'] == 'unsupported_grant_type'
