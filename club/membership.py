"""Club membership page and the staging-only demo checkout.

There is no billing. With CLUB_DEMO_CHECKOUT=1 a signed-in learner can switch
their own entitlement between free and member to test paid journeys. Revoked
access is never overridden here.
"""
import re

from flask import abort, flash, g, jsonify, redirect, request


def safe_return(target):
    if isinstance(target, str) and re.fullmatch(r'/(lessons|courses|materials)/[A-Za-z0-9_.-]{1,120}', target):
        return target
    return '/membership'


def register_membership(app, db, query, require_user, shell):
    def counts():
        return query('''SELECT SUM(l.access='member') AS member, SUM(l.access='free') AS free FROM lessons l
            JOIN modules m ON m.id=l.module_id JOIN courses c ON c.id=m.course_id
            WHERE l.status='published' AND c.status='published' ''', one=True)

    @app.get('/membership')
    def membership():
        return shell()

    @app.get('/api/app/membership')
    def membership_api():
        row = counts()
        return jsonify(member_lessons=row['member'] or 0, free_lessons=row['free'] or 0, demo=app.config['DEMO_CHECKOUT'],
                       return_to=safe_return(request.args.get('next')))

    def switch(entitlement, message):
        if not app.config['DEMO_CHECKOUT']:
            abort(404)
        if g.user['role'] != 'learner' or g.user['entitlement'] == 'revoked':
            abort(403, 'Доступ этого аккаунта меняется только через поддержку.')
        with db():
            db().execute('UPDATE users SET entitlement=? WHERE id=?', (entitlement, g.user['id']))
        data = request.get_json(silent=True) if request.is_json else request.form
        destination = safe_return(data.get('next') if hasattr(data, 'get') else None)
        if request.is_json:
            return jsonify(entitlement=entitlement, next=destination, message=message)
        flash(message, 'success')
        return redirect(destination)

    @app.post('/membership/demo')
    @require_user
    def membership_demo():
        return switch('member', 'Демо-доступ клуба включён. Оплата не списывалась.')

    @app.post('/membership/demo/cancel')
    @require_user
    def membership_demo_cancel():
        return switch('free', 'Демо-доступ выключен. Вы снова на бесплатном доступе.')
