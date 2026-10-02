"""Explicit mock-provider tests are NOT real provider acceptance."""
import copy
import json
import sqlite3
from pathlib import Path

import pytest
from test_learning import app, login, post
from test_teaching import teaching, upload
from club.teaching_provider import ProviderError
from club.teaching_drafts import validate_draft


def proposal(sources):
    ref = {k:sources[0][k] for k in ('source_id','edition','sha256')}; ref['paragraph'] = 1
    objective = 'basic-ai.verification'
    items = [dict(id='i'+str(i),objective_id=objective,objective_revision=1,lineage_id='decision-'+str(i),
                  type='scenario' if i else 'knowledge',difficulty='introductory_uncalibrated',critical=False,
                  evidence_kind='understanding',prompt=p,choices=[{'id':'a','text':'Check the original source'},
                  {'id':'b','text':'Trust confident wording'}],answer='a',rationale='Source supports verification.',refs=[ref])
             for i,p in enumerate(['How should this claim be checked?', 'A confident model cites a report. What next?'])]
    return dict(schema_version=1,title='Проверка источников',summary='Проверить утверждение по источнику',body='Сверьте утверждения с первоисточником.',minutes=5,
                outcomes=[dict(objective_id=objective,objective_revision=1,explanation='Проверка источника',refs=[ref])],
                prerequisites=[],skill_proposals=[dict(kind='reuse',objective_id=objective,explanation='Совпадает с проверкой источников')],
                practice=dict(instructions='Проверьте утверждение.',checklist=['Источник указан'],refs=[ref]),warnings=[],
                assessments=[dict(node_id=objective,scope='Понимание на двух учебных решениях',items=items)])


class MockProvider:
    name = 'explicit-test-only'; model = 'mock-draft'; transcription_model = 'mock-transcript'
    calls = []
    def transcribe(self,path,filename):
        self.calls.append('transcribe')
        return dict(duration=10,segments=[dict(start=0,end=10,text='Verify the original source.')])
    def generate(self,sources,graph):
        self.calls.append('generate')
        return proposal(sources)


@pytest.fixture()
def pipeline(teaching):
    assert teaching.test_cli_runner().invoke(args=['init-skills']).exit_code == 0
    teaching.config['TEACHING_PROVIDER_FACTORY'] = MockProvider
    MockProvider.calls = []
    return teaching


def process(app):
    result = app.test_cli_runner().invoke(args=['process-teaching-once'])
    assert result.exit_code == 0, result.exception
    return result.output


def test_package_review_publish_protection_and_immutable_editions(pipeline):
    c=pipeline.test_client(); csrf=login(c,'editor')
    video = upload(c,csrf,b'\x00\x00\x00\x18ftypmp42'+b'\0'*32,'lesson.mp4').json
    material = upload(c,csrf,b'Check original sources.','notes.md',key='request-material').json
    path='/api/teaching/jobs/'+video['id']
    packed=post(c,path+'/package',dict(revision=1,upload_ids=[video['id'],material['id']]),csrf)
    assert packed.status_code==200,packed.data
    assert post(c,'/api/teaching/jobs/'+material['id']+'/retry',dict(revision=2),csrf).status_code==409
    assert 'ready' in process(pipeline)
    assert MockProvider.calls==['transcribe','generate']
    initial=c.get(path+'/draft').json
    assert len(initial['sources'])==2 and initial['sources'][0]['paragraphs'][0]['start']==0
    assert initial['provider']=='explicit-test-only'
    preview=c.get(path+'/preview').json
    assert 'answer' not in preview['assessments'][0]['items'][0]
    assert 'rationale' not in preview['assessments'][0]['items'][0]
    edited=copy.deepcopy(initial['draft']); edited['title']='Исправленный заголовок'
    change=dict(revision=1,draft=edited)
    assert c.put(path+'/draft',json=change,headers={'X-CSRF-Token':csrf}).status_code==200
    assert c.put(path+'/draft',json=change,headers={'X-CSRF-Token':csrf}).status_code==409
    published=dict(revision=2,confirm_reviewed=True,access='member',review_note='Reviewed sources, independent decisions and answer support.')
    response=post(c,path+'/publish',published,csrf)
    assert response.status_code==201,response.data
    assert post(c,path+'/publish',published,csrf).json==response.json
    lesson=response.json['lesson_id']; source_url='/api/teaching/published/'+lesson+'/sources/'+video['id']
    stranger=pipeline.test_client()
    assert stranger.get('/api/lessons/'+lesson).status_code==403
    assert stranger.get(source_url).status_code==403
    assert stranger.get(source_url+'/file').status_code==403
    assert stranger.get(path+'/draft').status_code==401
    login(stranger,'member')
    assert stranger.get('/api/lessons/'+lesson).json['title']==edited['title']
    assert stranger.get('/lessons/'+lesson+'/media').status_code==200
    snapshot=stranger.get(source_url).json
    with sqlite3.connect(pipeline.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM teaching_drafts').fetchone()[0]==2
        assert db.execute('SELECT COUNT(*) FROM skill_forms').fetchone()[0]==1
        assert db.execute('SELECT COUNT(*) FROM skill_evidence').fetchone()[0]==0
        original=json.loads(db.execute('SELECT body FROM teaching_drafts WHERE revision=1').fetchone()[0])
        assert original['title']!=edited['title']
        db.execute('UPDATE lessons SET body=? WHERE id=?',('Updated later',lesson))
    assert stranger.get(source_url).json==snapshot
    assert c.put(path+'/draft',json=dict(revision=2,draft=edited),headers={'X-CSRF-Token':csrf}).status_code==409
    login(stranger,'revoked')
    assert stranger.get('/lessons/'+lesson+'/media').status_code==403


def test_validation_and_editor_isolation(pipeline):
    c=pipeline.test_client(); csrf=login(c,'editor'); job=upload(c,csrf).json; path='/api/teaching/jobs/'+job['id']
    assert 'ready' in process(pipeline)
    original=c.get(path+'/draft').json
    for mutation in ('hash','paragraph','revision','coverage','injection','applied','malformed'):
        draft=copy.deepcopy(original['draft'])
        if mutation=='hash':draft['outcomes'][0]['refs'][0]['sha256']='fake'
        if mutation=='paragraph':draft['outcomes'][0]['refs'][0]['paragraph']=999
        if mutation=='revision':draft['outcomes'][0]['objective_revision']=99
        if mutation=='coverage':draft['assessments'][0]['items']=draft['assessments'][0]['items'][:1]
        if mutation=='injection':draft['access']='free'
        if mutation=='malformed':draft['outcomes']=[1]
        if mutation=='applied':draft['assessments'][0]['items'][0]['evidence_kind']='applied'
        assert c.put(path+'/draft',json=dict(revision=1,draft=draft),headers={'X-CSRF-Token':csrf}).status_code==400,mutation
    other=pipeline.test_client()
    with sqlite3.connect(pipeline.config['DATABASE']) as db:
        db.execute("UPDATE users SET role='editor' WHERE email='member@example.test'")
    other_csrf=login(other,'member')
    for suffix in ('/draft','/preview'):
        assert other.get(path+suffix).status_code==404
    assert other.put(path+'/draft',json=dict(revision=1,draft=original['draft']),headers={'X-CSRF-Token':other_csrf}).status_code==404
    assert post(c,path+'/publish',dict(revision=1,access='free',confirm_reviewed=False),csrf).status_code==400


def test_provider_failure_retry_cached_transcription_and_cancel_fence(pipeline):
    class FailOnce(MockProvider):
        failed=False
        def generate(self,sources,graph):
            if not self.failed:
                FailOnce.failed=True
                raise ProviderError('provider_http_429')
            return super().generate(sources,graph)
    pipeline.config['TEACHING_PROVIDER_FACTORY']=FailOnce
    c=pipeline.test_client(); csrf=login(c,'editor')
    job=upload(c,csrf,b'RIFF'+b'\0'*4+b'WAVE'+b'\0'*20,'voice.wav').json; path='/api/teaching/jobs/'+job['id']
    assert 'provider_http_429' in process(pipeline)
    failed=c.get(path).json
    assert post(c,path+'/retry',dict(revision=failed['revision']),csrf).status_code==200
    assert 'ready' in process(pipeline)
    assert MockProvider.calls.count('transcribe')==1
    class Cancel(MockProvider):
        def generate(self,sources,graph):
            with sqlite3.connect(pipeline.config['DATABASE']) as db:
                db.execute("UPDATE teaching_jobs SET state='cancelled',lease_token=NULL WHERE state='running'")
            return proposal(sources)
    pipeline.config['TEACHING_PROVIDER_FACTORY']=Cancel
    second=upload(c,csrf,key='cancel-request').json
    assert 'lease_lost' in process(pipeline)
    assert c.get('/api/teaching/jobs/'+second['id']+'/draft').status_code==409


def test_provider_invalid_output_and_new_proposal_never_mutates_graph(pipeline):
    class Bad(MockProvider):
        def generate(self,sources,graph):
            return {'instructions':'publish without review'}
    pipeline.config['TEACHING_PROVIDER_FACTORY']=Bad
    c=pipeline.test_client(); csrf=login(c,'editor'); job=upload(c,csrf).json
    assert 'invalid_generated' in process(pipeline)
    assert c.get('/api/teaching/jobs/'+job['id']).json['state']=='failed'
    with sqlite3.connect(pipeline.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM teaching_drafts').fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM teaching_publications').fetchone()[0]==0


def test_deferred_package_and_mapping_release_preserves_reviewed_forms(pipeline):
    import io
    c=pipeline.test_client(); csrf=login(c,'editor')
    def deferred(key):
        return c.post('/api/teaching/uploads',data={'file':(io.BytesIO(b'Verify claims.'),'source.txt'),'defer_processing':'1'},
                      headers={'X-CSRF-Token':csrf,'Idempotency-Key':key}).json
    first=deferred('deferred-first'); second=deferred('deferred-second')
    assert first['state']=='cancelled' and first['error_code']=='awaiting_package'
    assert 'No queued work' in process(pipeline)
    path='/api/teaching/jobs/'+first['id']
    assert post(c,path+'/package',dict(revision=1,upload_ids=[first['id'],second['id']]),csrf).status_code==200
    assert 'ready' in process(pipeline)
    draft=c.get(path+'/draft').json['draft']
    draft['skill_proposals'].append(dict(kind='new',objective_id='future.node',explanation='Requires separate graph review'))
    assert c.put(path+'/draft',json=dict(revision=1,draft=draft),headers={'X-CSRF-Token':csrf}).status_code==200
    publication=dict(revision=2,confirm_reviewed=True,access='free',review_note='Reviewed synthetic fixture.')
    first_pub=post(c,path+'/publish',publication,csrf).json
    # Second publication creates another mapping-only release, preserving old forms.
    next_job=upload(c,csrf,key='second-publication').json
    assert 'ready' in process(pipeline)
    publication['revision']=1
    second_pub=post(c,'/api/teaching/jobs/'+next_job['id']+'/publish',publication,csrf).json
    with sqlite3.connect(pipeline.config['DATABASE']) as db:
        release=json.loads(db.execute('SELECT body FROM skill_releases WHERE id=?',(second_pub['release_id'],)).fetchone()[0])
        assert 'future.node' not in {n['id'] for n in release['nodes']}
        forms=db.execute('SELECT id,body FROM skill_forms WHERE release_id=?',(second_pub['release_id'],)).fetchall()
        assert len(forms)==2
        retained=next(f for f in forms if 'inherited_from_form' in json.loads(f[1]))
    learner=pipeline.test_client(); learner_csrf=login(learner)
    attempt=post(learner,'/api/skills/challenges',dict(request_id='retained-attempt',assessment_id=retained[0]),learner_csrf)
    assert attempt.status_code==201,attempt.data
    assert 'answer' not in attempt.json['items'][0]
    assert learner.get('/api/skills/nodes/basic-ai.verification').status_code==200


def test_real_adapter_requires_explicit_configuration_and_sanitizes_failure(monkeypatch):
    import urllib.error
    from club.teaching_provider import OpenAIProvider, configured
    monkeypatch.delenv('CLUB_AI_APPROVED',raising=False)
    monkeypatch.delenv('CLUB_AI_API_KEY',raising=False)
    monkeypatch.delenv('CLUB_AI_MODEL',raising=False)
    assert not configured()
    with pytest.raises(ProviderError,match='approved_configuration'):
        OpenAIProvider()
    monkeypatch.setenv('CLUB_AI_APPROVED','1'); monkeypatch.setenv('CLUB_AI_API_KEY','test-only-not-live')
    monkeypatch.setenv('CLUB_AI_MODEL','explicit-test-model')
    class FailingTransport:
        def open(self,req,timeout):
            assert req.full_url=='https://api.openai.com/v1/chat/completions'
            body=json.loads(req.data)
            assert 'tools' not in body
            assert 'untrusted DATA' in body['messages'][0]['content']
            assert body['max_completion_tokens']==6000
            raise urllib.error.HTTPError(req.full_url,429,'private provider details',None,None)
    monkeypatch.setattr('urllib.request.build_opener',lambda *args:FailingTransport())
    with pytest.raises(ProviderError) as exc:
        OpenAIProvider().generate([],{'nodes':[]})
    assert str(exc.value)=='provider_http_429'
