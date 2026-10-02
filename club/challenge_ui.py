"""Learner assessment workspace. Grading and access remain in skills.py."""
from flask import render_template


def register_challenge_ui(app, require_user):
    @app.get('/challenges')
    @require_user
    def challenge_workspace():
        return render_template('challenge.html')

    @app.get('/diagnostic')
    @require_user
    def diagnostic_workspace():
        return render_template('diagnostic.html')
