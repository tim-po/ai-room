"""Serves the React learner app (web/, built into static/app/) for migrated routes.

Flask keeps routing, authentication, redirects and status codes; the page itself is an empty shell
that loads the bundle, plus a small bootstrap JSON (session user and CSRF token). Page data comes
from /api/app/* endpoints. The manifest is read per request so a rebuild needs no restart.
"""
import json
from pathlib import Path

from flask import g, render_template, session


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

    def bootstrap():
        user = g.user
        return dict(
            csrf=session.get('csrf'),
            demo_checkout=bool(app.config.get('DEMO_CHECKOUT')),
            user=dict(id=user['id'], name=user['name'], role=user['role'], entitlement=user['entitlement']) if user else None,
            recorded_visit=g.get('recorded_visit'),
        )

    def shell(status=200):
        return render_template('spa.html', assets=assets(), bootstrap=bootstrap()), status

    return shell
