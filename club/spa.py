"""Serves the React learner app (web/, built into static/app/) for migrated routes.

Flask keeps routing, authentication, redirects and status codes; the page itself is an empty shell
that loads the bundle, plus a small bootstrap JSON (session user, CSRF token, flashed notices and,
for error responses, the error). Page data comes from /api/app/* endpoints; the first page's data is
embedded in the bootstrap too, so a fresh load needs no second round trip before it can render. The
manifest is read per request so a rebuild needs no restart.
"""
import json
import re
from pathlib import Path

from flask import g, get_flashed_messages, render_template, request, session
from werkzeug.exceptions import HTTPException

SEARCH = ('q', 'class', 'topic', 'level', 'access')
FIXED = {'/': '/api/app/home', '/profile': '/api/app/profile', '/preferences': '/api/app/preferences',
         '/onboarding': '/api/onboarding', '/oauth/consent': '/api/app/oauth/consent'}


def page_data_url(path, args, query):
    """The API URL a page's loader asks for (web/src/prefetch.ts mirrors this)."""
    search = '?' + query if query else ''
    if path in FIXED:
        return FIXED[path]
    if path in ('/discover', '/catalogue'):
        return '/api/app/search' + search if any(args.get(k) for k in SEARCH) else '/api/app/discover'
    if path in ('/membership', '/help'):
        return '/api/app' + path + search
    match = re.fullmatch(r'/(lessons|courses|materials)/([A-Za-z0-9_.-]+)', path)
    return f'/api/app/{match[1]}/{match[2]}' if match else None


def register_spa(app):
    manifest_path = Path(app.static_folder) / 'app' / '.vite' / 'manifest.json'

    def assets():
        try:
            manifest = json.loads(manifest_path.read_text())
        except (OSError, ValueError):
            return None
        entry = manifest.get('src/main.tsx')
        if not entry:
            return None
        css = list(entry.get('css', []))
        for name in entry.get('imports', []):
            css += manifest.get(name, {}).get('css', [])
        return dict(js='/static/app/' + entry['file'], css=['/static/app/' + c for c in css])

    def page_data():
        """Runs the page's own API view in this request (same user, same query string)."""
        url = page_data_url(request.path, request.args, request.query_string.decode('latin-1'))
        if not url:
            return None
        try:
            endpoint, values = app.url_map.bind_to_environ(request.environ).match(url.split('?')[0], method='GET')
            response = app.make_response(app.ensure_sync(app.view_functions[endpoint])(**values))
        except HTTPException:
            return None
        except Exception:   # the page still loads; the app then asks for its data and shows that error
            app.logger.exception('Embedding page data for %s failed', request.path)
            return None
        if response.status_code != 200 or not response.is_json:
            return None
        return dict(url=url, data=response.get_json())

    def bootstrap(error):
        user = g.get('user')
        return dict(
            csrf=session.get('csrf'),
            demo_checkout=bool(app.config.get('DEMO_CHECKOUT')),
            user=dict(id=user['id'], name=user['name'], role=user['role'], entitlement=user['entitlement']) if user else None,
            recorded_visit=g.get('recorded_visit'),
            notices=[dict(kind=kind, text=text) for kind, text in get_flashed_messages(with_categories=True)],
            error=dict(code=error.code, description=error.description) if error else None,
            page=None if error else page_data(),
        )

    def shell(status=200, error=None):
        return render_template('spa.html', assets=assets(), bootstrap=bootstrap(error)), status

    return shell
