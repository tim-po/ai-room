import sqlite3
from pathlib import Path
from club import create_app
from test_learning import app, login, post, FREE


def test_support_preserves_history_and_rejects_conflicts(app):
    learner = app.test_client(); csrf = login(learner)
    assert learner.post('/help?lesson='+FREE, data={'csrf':csrf, 'body':'Synthetic source question', 'lesson_id':FREE}).status_code == 302
    result = app.test_cli_runner().invoke(args=['init-support'])
    assert result.exit_code == 0, result.output
    backups = list(Path(app.config['DATABASE']).parent.glob('before-support-*/database.sqlite'))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as db:
        assert db.execute('SELECT body FROM help_requests').fetchone()[0] == 'Synthetic source question'
    ticket = learner.get('/api/support/tickets').json['tickets'][0]
    url = '/api/support/tickets/' + str(ticket['id'])
    other = app.test_client(); login(other, 'member')
    assert other.get(url).status_code == 404
    assert other.get('/api/support/tickets').json['tickets'] == []
    payload = {'revision':0,'response':'Synthetic answer <script>literal</script>'}
    assert post(learner,url+'/handle',payload,csrf).status_code == 403
    editor = app.test_client(); csrf = login(editor,'admin')
    assert editor.post(url+'/handle',json=payload).status_code == 400
    first = post(editor,url+'/handle',payload,csrf)
    assert first.status_code == 200
    assert first.json['ticket']['status'] == 'handled'
    assert post(editor,url+'/handle',payload,csrf).json == first.json
    assert post(editor,url+'/handle',dict(revision=0,response='Conflicting answer'),csrf).status_code == 409
    for payload in ({'revision':True,'response':'bad'}, {'revision':1,'response':' '}, {'revision':1,'response':'x'*4001}):
        assert post(editor,url+'/handle',payload,csrf).status_code == 400
    assert learner.get(url).json == first.json
    assert 'handler_id' not in first.json['ticket']
    restarted = create_app({'TESTING':True,'DATABASE':app.config['DATABASE'],'SECRET_KEY':'test-only-key'})
    client = restarted.test_client(); login(client)
    assert client.get(url).json == first.json
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM support_responses').fetchone()[0] == 1
        assert db.execute('SELECT body,lesson_id FROM help_requests').fetchone() == ('Synthetic source question',FREE)
