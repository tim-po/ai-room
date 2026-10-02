"""Learner assessment workspace. Grading and access remain in skills.py."""
from flask import abort, g, render_template


def register_challenge_ui(app, require_user):
    @app.get('/challenges')
    @require_user
    def challenge_workspace():
        return render_template('challenge.html')

    @app.get('/diagnostic')
    @require_user
    def diagnostic_workspace():
        return render_template('diagnostic.html')

    @app.get('/practice')
    @require_user
    def practical_workspace():
        return render_template('practical.html', review=False)

    @app.get('/admin/practice')
    @require_user
    def practical_review_workspace():
        if g.user['role'] not in ('editor', 'admin'):
            abort(403)
        return render_template('practical.html', review=True)

    @app.get('/admin/tree')
    @require_user
    def graph_review_workspace():
        if g.user['role'] not in ('editor', 'admin'):
            abort(403)
        return render_template('graph_review.html')
