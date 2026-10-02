"""Standalone authoring and access boundaries, persistence and combined discovery."""
import re
import sqlite3
from pathlib import Path

from club import create_app
from test_learning import app, login, post
from test_authoring import form

GUIDE = 'guide-check-answer'
WORKSHOP = 'workshop-prompt-lab'


def fields(**changes):
    return dict(title='Проверяем самостоятельный материал', description='Описание в каталоге', outcome='Проверенный результат',
                format='workshop',goal='work',level='Начальный',tools='Текстовый AI',prerequisites='Без опыта',author='Редактор',
                minutes='10',body='Скрытый текст <script>alert(1)</script>',prompt='Скрытый запрос',video='',access='member',status='draft') | changes


def test_material_lifecycle_access_resources_and_conflicts(app):
    editor=app.test_client();csrf=login(editor,'editor')
    response=form(editor,'/admin/materials/new',csrf,**fields())
    assert response.status_code==302
    path=response.location;identity=path.rsplit('/',1)[1]
    public='/materials/'+identity
    anon=app.test_client();member=app.test_client();member_csrf=login(member,'member')
    for c in [anon,member]:
        for suffix in ['', '/media']:
            assert c.get(public+suffix).status_code==404
        assert c.get('/api/materials/'+identity).status_code==404
    assert member.get(path+'/preview').status_code==403
    preview=editor.get(path+'/preview')
    assert preview.status_code==200 and '&lt;script&gt;' in preview.text and '<script>alert' not in preview.text
    assert editor.post(path+'/resources',data={'csrf':csrf,'title':'Рабочий лист','kind':'text','content':'Секретный ресурс'}).status_code==302
    db=sqlite3.connect(app.config['DATABASE'])
    resource=db.execute('SELECT id FROM material_resources WHERE material_id=?',(identity,)).fetchone()[0]
    resource_path='/material-resources/'+resource
    assert member.get(resource_path).status_code==404
    assert editor.get('/admin/materials/resources/'+resource+'/preview').text=='Секретный ресурс'
    revision=re.search('name="revision" value="([^"]+)"',editor.get(path).text)[1]
    assert form(editor,path,csrf,**fields(status='published')).status_code==302
    assert editor.post(path,data={'csrf':csrf,'revision':revision,**fields()}).status_code==409
    for endpoint in [public,resource_path,'/api/materials/'+identity,public+'/media']:
        assert anon.get(endpoint).status_code==403
    assert member.get(public).status_code==200
    assert member.get(resource_path).text=='Секретный ресурс'
    assert member.post(public+'/favourite',data={'csrf':member_csrf,'saved':'1'}).status_code==302
    assert identity in member.get('/profile').text
    assert identity not in anon.get('/catalogue?format=guide').text
    for status in ['draft','archived']:
        assert form(editor,path,csrf,**fields(status=status)).status_code==302
        assert member.get(public).status_code==404
        assert member.get(resource_path).status_code==404
        assert identity not in member.get('/profile').text
        assert identity not in member.get('/catalogue').text
    assert form(editor,path,csrf,**fields(status='published')).status_code==302
    assert identity in member.get('/profile').text
    assert db.execute('SELECT count(*) FROM material_favourites WHERE material_id=?',(identity,)).fetchone()[0]==1
    # Entitlements are loaded every request, so an existing session cannot retain revoked access.
    for entitlement in ['free','expired','revoked']:
        db.execute("UPDATE users SET entitlement=? WHERE id='user-member'",(entitlement,));db.commit()
        for endpoint in [public,resource_path,'/api/materials/'+identity,public+'/media']:
            assert member.get(endpoint).status_code==403
        assert member.get('/materials/'+GUIDE).status_code==200
    assert editor.post('/admin/materials/resources/'+resource+'/archive',data={'csrf':csrf}).status_code==302
    assert editor.get(resource_path).status_code==404
    db.close()


def test_material_filter_metadata_validation_and_roles(app):
    c=app.test_client()
    page=c.get('/catalogue?format=workshop&goal=work&level=Начальный&tool=текстовый&q=мастерская')
    assert page.status_code==200 and WORKSHOP in page.text and GUIDE not in page.text
    assert 'Неизвестные данные оставьте пустыми' not in page.text
    assert 'Ничего не найдено' in c.get('/catalogue?format=guide&goal=agents').text
    assert GUIDE in c.get('/catalogue?format=guide&tool=AI').text
    assert GUIDE not in c.get('/catalogue?format=course').text
    assert c.get('/admin/materials').status_code==401
    assert c.get('/admin/materials/resources/worksheet-'+GUIDE+'/preview').status_code==401
    csrf=login(c)
    assert c.post('/admin/materials/new',data={'csrf':csrf,**fields()}).status_code==403
    csrf=login(c,'editor')
    assert c.post('/admin/materials/new',data=fields()).status_code==400
    for changes in [dict(format='bad'),dict(video='../session.key'),dict(minutes='0'),dict(body=''),dict(access='public')]:
        assert form(c,'/admin/materials/new',csrf,**fields(**changes)).status_code==400
    for url in ['javascript:alert(1)','https://user:password@example.test','https://example.test/ bad','//example.test']:
        assert c.post('/admin/materials/'+GUIDE+'/resources',data={'csrf':csrf,'title':'Источник','kind':'link','content':url}).status_code==400
    assert c.post('/admin/materials/'+GUIDE+'/resources',data={'csrf':csrf,'title':'Источник','kind':'link','content':'https://example.test/guide'}).status_code==302
    with sqlite3.connect(app.config['DATABASE']) as db:
        identity=db.execute("SELECT id FROM material_resources WHERE kind='link'").fetchone()[0]
    assert c.get('/material-resources/'+identity).location=='https://example.test/guide'


def test_material_media_resume_restart_isolation_and_seed(app,tmp_path):
    # Isolated media storage and a real HTTP byte-range response.
    app.instance_path=str(tmp_path)
    media=tmp_path/'media';media.mkdir();(media/'fixture.webm').write_bytes(b'test-media-bytes')
    c=app.test_client();csrf=login(c,'member')
    path='/materials/'+WORKSHOP
    assert c.get(path+'/media',headers={'Range':'bytes=0-3'}).status_code==206
    for seconds in [True,-1,float('inf'),'8',None]:
        assert post(c,'/api/materials/'+WORKSHOP+'/video',{'seconds':seconds},csrf).status_code==400
    assert post(c,'/api/materials/'+WORKSHOP+'/video',{'seconds':3.5},csrf).status_code==200
    assert c.post(path+'/favourite',data={'csrf':csrf,'saved':'1'}).status_code==302
    restart=create_app({'TESTING':True,'DATABASE':app.config['DATABASE'],'SECRET_KEY':'restart'})
    second=restart.test_client();login(second,'member')
    assert 'data-resume="3.5"' in second.get(path).text
    assert 'Убрать из избранного' in second.get(path).text
    other=app.test_client();login(other,'editor')
    assert 'data-resume="0"' in other.get(path).text
    assert 'Убрать из избранного' not in other.get(path).text
    (media/'fixture.webm').unlink()
    assert c.get(path).status_code==200 and c.get(path+'/media').status_code==404
    with sqlite3.connect(app.config['DATABASE']) as db:
        db.execute("UPDATE materials SET title='Редакционная версия' WHERE id=?",(WORKSHOP,))
    runner=app.test_cli_runner()
    for _ in range(2):
        assert runner.invoke(args=['init-db']).exit_code==0
        assert runner.invoke(args=['seed-materials']).exit_code==0
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('SELECT title FROM materials WHERE id=?',(WORKSHOP,)).fetchone()[0]=='Редакционная версия'
        assert db.execute('SELECT seconds FROM material_video_positions').fetchone()[0]==3.5
        assert db.execute('SELECT count(*) FROM material_favourites').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM progress').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM events').fetchone()[0]==0
