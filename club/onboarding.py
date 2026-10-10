"""Onboarding v2: getting to know the learner and building their path (web/src/pages/Onboarding.tsx).

The answers and the path live in club/journey.py. This module only decides who goes there: a learner
who hasn't finished or skipped it lands on /onboarding from the entry pages and after logging in. A
direct link to a course or lesson always opens it — a shared link must never land on a questionnaire.
"""
import re

import click
from flask import g, jsonify, redirect, request


def register_onboarding(app, db, query, require_user, shell, journey):
    def permitted(target, user):
        # Explicit route allowlist, no decoding/normalization ambiguities or arbitrary query redirects.
        if not isinstance(target, str) or len(target) > 256:
            return '/'
        if target in ('/', '/map', '/catalogue', '/discover', '/profile', '/preferences', '/path', '/help', '/oauth/consent'):
            return target
        course = re.fullmatch(r'/courses/([A-Za-z0-9_.-]+)', target)
        if course and query("SELECT 1 FROM courses WHERE id=? AND status='published'", (course[1],), True):
            return target
        match = re.fullmatch(r'/lessons/([A-Za-z0-9_.-]+)', target)
        if match:
            row = query("""SELECT l.access FROM lessons l JOIN modules m ON m.id=l.module_id
                JOIN courses c ON c.id=m.course_id WHERE l.id=? AND l.status='published' AND c.status='published'""", (match[1],), True)
            if row and (row['access'] == 'free' or user['entitlement'] == 'member' or user['role'] != 'learner'):
                return target
        return '/'

    def login_destination(user, target):
        safe = permitted(target, user)
        if user['role'] != 'learner' or journey['finished'](user) or re.match(r'/(courses|lessons)/', safe):
            return safe
        return '/onboarding'

    pages = {'home', 'skill_map', 'catalogue', 'discover', 'profile', 'preferences', 'skill_tree'}
    page_data = {'home_api', 'catalogue_api', 'discover_api', 'search_api', 'profile_api', 'preferences_api'}

    @app.before_request
    def learner_entry():
        if (request.method == 'GET' and g.get('user') and g.user['role'] == 'learner'
                and request.endpoint in pages | page_data and not journey['finished'](g.user)):
            if request.endpoint in page_data:
                return jsonify(error='onboarding', message='Сначала завершите или пропустите знакомство.', redirect='/onboarding'), 409
            return redirect('/onboarding')
        return None

    @app.get('/onboarding')
    @require_user
    def onboarding():
        # Editors and admins may walk through it too (to see what learners see); only learners are sent here.
        return shell()

    @app.cli.command('init-onboarding')
    def migrate():
        """Kept for setup scripts: onboarding v2 stores its answers on first use (club/journey.py)."""
        click.echo('Onboarding v2 needs no migration: answers are stored on first use.')

    return login_destination
