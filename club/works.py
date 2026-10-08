"""Learners' practice results and the team's feedback on them.

A learner saves practice on a lesson (table practice: a draft or a «результат»). Editors and admins see
submitted results in the admin («Работы») next to the lesson's task and success criteria, and write one
note of feedback per work, which the learner reads on the lesson and in «Мои работы». A work changed
after its feedback shows up as waiting again; the feedback itself stays until it is rewritten.
"""
from flask import abort, g, jsonify, request

from .storage import additive_tables

SCHEMA = ('''CREATE TABLE IF NOT EXISTS practice_reviews (
    user_id TEXT NOT NULL REFERENCES users(id), lesson_id TEXT NOT NULL REFERENCES lessons(id), body TEXT NOT NULL,
    reviewer_id TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id, lesson_id))''',)


def register_works(app, db, query, staff):
    ensure = additive_tables(app, SCHEMA)

    def review(user_id, lesson_id):
        """The feedback a learner sees on their work, or None."""
        ensure()
        row = query('''SELECT r.body,r.updated_at,u.name reviewer FROM practice_reviews r JOIN users u ON u.id=r.reviewer_id
            WHERE r.user_id=? AND r.lesson_id=?''', (user_id, lesson_id), True)
        return dict(row) if row else None

    def works(show='waiting'):
        ensure()
        rows = query('''SELECT p.user_id,u.name user_name,u.entitlement,p.lesson_id,l.title lesson_title,c.id course_id,c.title course_title,
            l.task,l.checklist,p.body,p.status,p.updated_at,r.body review,r.updated_at reviewed_at,ru.name reviewer
            FROM practice p JOIN users u ON u.id=p.user_id JOIN lessons l ON l.id=p.lesson_id JOIN modules m ON m.id=l.module_id
            JOIN courses c ON c.id=m.course_id LEFT JOIN practice_reviews r ON r.user_id=p.user_id AND r.lesson_id=p.lesson_id
            LEFT JOIN users ru ON ru.id=r.reviewer_id
            WHERE p.status='submitted' AND u.role='learner' ORDER BY p.updated_at DESC''')
        out = []
        for r in rows:
            item = dict(r)
            item['checklist'] = r['checklist'].split('\n') if r['checklist'] else []
            item['waiting'] = not r['review'] or r['updated_at'] > r['reviewed_at']
            item['changed'] = bool(r['review']) and r['updated_at'] > r['reviewed_at']
            if show == 'all' or item['waiting']:
                out.append(item)
        return out

    def waiting_count():
        return len(works('waiting'))

    def save_review(user_id, lesson_id, body):
        if not isinstance(body, str) or not 1 <= len(body.strip()) <= 4000:
            abort(400, 'Отзыв — от 1 до 4000 символов.')
        ensure()
        if not query("SELECT 1 FROM practice WHERE user_id=? AND lesson_id=? AND status='submitted'", (user_id, lesson_id), True):
            abort(404, 'Такой сданной работы нет.')
        with db():
            db().execute('''INSERT INTO practice_reviews(user_id,lesson_id,body,reviewer_id) VALUES(?,?,?,?) ON CONFLICT(user_id,lesson_id)
                DO UPDATE SET body=excluded.body,reviewer_id=excluded.reviewer_id,updated_at=CURRENT_TIMESTAMP''',
                         (user_id, lesson_id, body.strip(), g.user['id']))
        return next(w for w in works('all') if w['user_id'] == user_id and w['lesson_id'] == lesson_id)

    @app.get('/api/admin/works')
    def admin_works():
        staff()
        show = 'all' if request.args.get('show') == 'all' else 'waiting'
        return jsonify(works=works('all'), waiting=waiting_count(), show=show)

    @app.post('/api/admin/works/<user_id>/<lesson_id>/review')
    def admin_work_review(user_id, lesson_id):
        staff()
        data = request.get_json(silent=True) or {}
        return jsonify(save_review(user_id, lesson_id, data.get('body')))

    return dict(review=review, works=works, waiting_count=waiting_count, save_review=save_review)
