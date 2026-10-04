"""Read-only continuation across branches; never derives competence from activity."""


def learning_continuation(query, user):
    result = {'version': 'learning-continuation-v1', 'unfinished': None, 'last_result': None}
    if not user:
        return result
    rows = query('''SELECT l.id AS lesson_id,l.title,m.course_id,p.completed,
        p.updated_at AS progress_updated_at,r.status AS practice_status,
        r.updated_at AS practice_updated_at,COALESCE(v.visit_order,0) AS visit_order
        FROM lessons l JOIN modules m ON m.id=l.module_id
        JOIN courses c ON c.id=m.course_id
        LEFT JOIN progress p ON p.lesson_id=l.id AND p.user_id=?
        LEFT JOIN practice r ON r.lesson_id=l.id AND r.user_id=?
        LEFT JOIN lesson_visits v ON v.lesson_id=l.id AND v.user_id=?
        WHERE l.status='published' AND c.status='published'
        AND (l.access='free' OR ?='member' OR ? IN ('editor','admin'))
        AND (p.user_id IS NOT NULL OR r.user_id IS NOT NULL)''',
        (user['id'], user['id'], user['id'], user['entitlement'], user['role']))
    unfinished, results = [], []
    for row in rows:
        base = {key: row[key] for key in ('lesson_id', 'title', 'course_id')}
        base['url'] = '/lessons/' + row['lesson_id']
        if row['practice_status'] == 'draft':
            unfinished.append((row['practice_updated_at'], row['visit_order'], row['lesson_id'],
                               base | {'status': 'draft', 'updated_at': row['practice_updated_at']}))
        elif row['completed'] == 0:
            unfinished.append((row['progress_updated_at'], row['visit_order'], row['lesson_id'],
                               base | {'status': 'in_progress', 'updated_at': row['progress_updated_at']}))
        if row['practice_status'] == 'submitted':
            results.append((row['practice_updated_at'], row['visit_order'], row['lesson_id'],
                            base | {'status': 'submitted', 'updated_at': row['practice_updated_at']}))
        elif row['completed'] == 1:
            results.append((row['progress_updated_at'], row['visit_order'], row['lesson_id'],
                            base | {'status': 'completed', 'updated_at': row['progress_updated_at']}))
    if unfinished:
        result['unfinished'] = max(unfinished, key=lambda item: item[:3])[3]
    if results:
        result['last_result'] = max(results, key=lambda item: item[:3])[3]
    return result
