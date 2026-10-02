"""Provider-neutral source-grounded drafts and immutable editorial editions."""
import copy
import hashlib
import json
import math
import sqlite3
import time
from pathlib import Path

from flask import abort, g, jsonify, request, send_file
from .skills import validate_form, publish_reviewed_form
from .release_bindings import carry_forms
from .teaching_provider import OpenAIProvider, ProviderError

DRAFT_CONTRACT = '''Object fields: schema_version=1, title:string, summary:string, body:string,
minutes:integer 1..180, outcomes:[{objective_id,objective_revision,explanation,refs}],
prerequisites:[string], skill_proposals:[{kind:"reuse"|"new",objective_id:string,explanation:string}],
practice:{instructions:string,checklist:[string],refs:[reference]}, warnings:[string],
assessments:[{node_id,scope:string,items:[{id,objective_id,objective_revision,lineage_id,
 type:"knowledge"|"scenario",difficulty:"introductory_uncalibrated"|"intermediate_uncalibrated",
 critical:boolean,evidence_kind:"understanding",prompt,choices:[{id,text}],answer,rationale,refs:[reference]}]}].
A reference is {source_id,edition:1,sha256,paragraph:integer}. Media paragraphs also have start/end seconds in source.
No fields for access policy, publication or credentials. Limit 8 outcomes, 8 assessments, 24 items total.
'''


def active_graph(db):
    row = db.execute('SELECT r.body FROM skill_active a JOIN skill_releases r ON r.id=a.release_id WHERE singleton=1').fetchone()
    if not row:
        raise ValueError('Active skill graph required')
    return json.loads(row[0])


def text(value, limit=12000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError('Nonempty bounded text required')
    return value


def validate_draft(value, sources, graph):
    """Validate anchors and sufficient mechanical coverage; semantic review stays human."""
    if not isinstance(value, dict) or value.get('schema_version') != 1:
        raise ValueError('Draft schema_version 1 required')
    allowed = {'schema_version','title','summary','body','minutes','outcomes','prerequisites','skill_proposals','practice','warnings','assessments'}
    if set(value) != allowed or len(json.dumps(value).encode()) > 60000:
        raise ValueError('Unexpected draft fields or oversized draft')
    text(value['title'], 200); text(value['summary'], 2000); text(value['body'], 16000)
    if type(value['minutes']) is not int or not 1 <= value['minutes'] <= 180:
        raise ValueError('Invalid duration')
    abilities = {n['id']: n for n in graph['nodes'] if n['kind'] == 'ability'}
    source_map = {s['source_id']: s for s in sources}

    def references(refs):
        if not isinstance(refs, list) or not 1 <= len(refs) <= 12:
            raise ValueError('Source references required')
        for index, ref in enumerate(refs):
            if not isinstance(ref, dict):
                raise ValueError('Invalid source reference')
            src = source_map.get(ref.get('source_id'))
            if not src or type(ref.get('edition')) is not int or ref.get('edition') != src['edition'] or ref.get('sha256') != src['sha256']:
                raise ValueError('Unknown source edition/hash')
            if type(ref.get('paragraph')) is not int or ref['paragraph'] not in {p['paragraph'] for p in src['paragraphs']}:
                raise ValueError('Invalid source paragraph')
            # Provider/editor fields are untrusted, including plausible timestamps,
            # URLs and quoted text. Rebuild EVERY anchor from the pinned snapshot.
            span = next(p for p in src['paragraphs'] if p['paragraph'] == ref['paragraph'])
            canonical = {k: src[k] for k in ('source_id', 'edition', 'sha256')}
            canonical['paragraph'] = span['paragraph']
            if src['kind'] == 'media':
                canonical.update(start=span['start'], end=span['end'],
                                 transcript_edition=src['transcript_edition'],
                                 transcript_sha256=src['transcript_sha256'])
            refs[index] = canonical

    def objective(item):
        node = abilities.get(item.get('objective_id'))
        if not node or item.get('objective_revision') != node['revision']:
            raise ValueError('Unknown objective edition')

    if not isinstance(value['outcomes'], list) or not 0 <= len(value['outcomes']) <= 8:
        raise ValueError('At most eight mapped outcomes required')
    for outcome in value['outcomes']:
        objective(outcome); text(outcome['explanation'], 1500); references(outcome['refs'])
    mapped = {o['objective_id'] for o in value['outcomes']}
    if len(mapped) != len(value['outcomes']):
        raise ValueError('Duplicate mapped outcome')
    for key in ('prerequisites', 'warnings'):
        if not isinstance(value[key], list) or len(value[key]) > 12:
            raise ValueError('Invalid list')
        for item in value[key]:
            text(item, 1500)
    proposals = value['skill_proposals']
    if not isinstance(proposals, list) or len(proposals) > 12:
        raise ValueError('Invalid skill proposals')
    for proposal in proposals:
        if proposal['kind'] not in ('new', 'reuse'):
            raise ValueError('Invalid proposal kind')
        text(proposal['objective_id'], 128); text(proposal['explanation'], 1500)
        if (proposal['kind'] == 'reuse') != (proposal['objective_id'] in abilities):
            raise ValueError('Reuse existing objectives; new nodes await separate review')
    practice = value['practice']
    text(practice['instructions'], 4000); references(practice['refs'])
    if not isinstance(practice['checklist'], list) or not 1 <= len(practice['checklist']) <= 12:
        raise ValueError('Practice checklist required')
    for check in practice['checklist']:
        text(check, 1000)
    forms = value['assessments']
    if not isinstance(forms, list) or len(forms) > 8 or sum(len(f['items']) for f in forms) > 24:
        raise ValueError('Assessment limit exceeded')
    seen_nodes = set()
    for form in forms:
        if form['node_id'] not in mapped or form['node_id'] in seen_nodes:
            raise ValueError('Assessment must cover a distinct mapped ability')
        seen_nodes.add(form['node_id'])
        text(form['scope'], 1500)
        for item in form['items']:
            objective(item)
            if item['objective_id'] != form['node_id'] or item['evidence_kind'] != 'understanding':
                raise ValueError('Assessment scope mismatch')
            text(item['id'], 128); text(item['lineage_id'], 128)
            text(item['prompt'], 3000); text(item['rationale'], 3000)
            if item['difficulty'] not in ('introductory_uncalibrated','intermediate_uncalibrated'):
                raise ValueError('Difficulty must be labelled uncalibrated')
            if type(item['critical']) is not bool:
                raise ValueError('Critical must be boolean')
            for choice in item['choices']:
                text(choice['id'], 128); text(choice['text'], 1500)
            references(item['refs'])
        prepared = copy.deepcopy(form)
        for item in prepared['items']:
            item['source'] = item['refs'][0]
        validate_form(prepared, graph)
    return value


def coverage(draft):
    assessed = {f['node_id'] for f in draft['assessments']}
    return dict(challenge_available=bool(assessed), assessed_objectives=sorted(assessed),
                unassessed_objectives=sorted({o['objective_id'] for o in draft['outcomes']} - assessed),
                mapped=bool(draft['outcomes']))


def review_action(draft, action, graph):
    """Never silently retarget questions when their teaching objective changes."""
    kind, objective_id = action.get('kind'), action.get('objective_id')
    removed = []
    if kind in ('remap_outcome', 'reject_outcome'):
        outcome = next((o for o in draft['outcomes'] if o['objective_id'] == objective_id), None)
        if outcome is None:
            raise ValueError('Unknown outcome')
        if kind == 'remap_outcome':
            target = next((n for n in graph['nodes'] if n['id'] == action.get('target_id') and n['kind'] == 'ability'), None)
            if not target or any(o['objective_id'] == target['id'] for o in draft['outcomes']):
                raise ValueError('Choose a distinct existing ability')
            outcome.update(objective_id=target['id'], objective_revision=target['revision'])
        else:
            draft['outcomes'].remove(outcome)
        removed = [f['node_id'] for f in draft['assessments'] if f['node_id'] == objective_id]
        draft['assessments'] = [f for f in draft['assessments'] if f['node_id'] != objective_id]
        draft['skill_proposals'] = [p for p in draft['skill_proposals'] if p['objective_id'] != objective_id]
    elif kind in ('remove_question', 'remove_assessment'):
        form = next((f for f in draft['assessments'] if f['node_id'] == objective_id), None)
        if form is None:
            raise ValueError('Unknown assessment')
        if kind == 'remove_question':
            item = next((i for i in form['items'] if i['id'] == action.get('item_id')), None)
            if item is None:
                raise ValueError('Unknown question')
            form['items'].remove(item)
            prepared = copy.deepcopy(form)
            for i in prepared['items']:
                i['source'] = i['refs'][0]
            try:
                validate_form(prepared, graph)
            except ValueError:
                removed.append(objective_id)
        else:
            removed.append(objective_id)
        if removed:
            draft['assessments'].remove(form)
    else:
        raise ValueError('Unknown review action')
    return dict(removed_assessments=removed, **coverage(draft))


def source_snapshots(db, job_id, provider, root, alive):
    row = db.execute('SELECT upload_id FROM teaching_jobs WHERE id=?', (job_id,)).fetchone()
    ids = [r[0] for r in db.execute('SELECT upload_id FROM teaching_package_sources WHERE job_id=? ORDER BY position', (job_id,))] or [row[0]]
    sources = []
    for identity in ids:
        upload = db.execute('SELECT filename,sha256 FROM teaching_uploads WHERE id=?', (identity,)).fetchone()
        original = json.loads(db.execute('SELECT body FROM teaching_sources WHERE upload_id=?', (identity,)).fetchone()[0])
        source = dict(source_id=identity, edition=1, sha256=upload[1], filename=upload[0], kind=original['kind'])
        if original['kind'] == 'document':
            source['paragraphs'] = original['paragraphs']
        else:
            cached = db.execute('SELECT body FROM teaching_transcripts WHERE upload_id=?', (identity,)).fetchone()
            if cached:
                transcript = json.loads(cached[0])
            else:
                if not alive():
                    raise ProviderError('lease_lost')
                transcript = provider.transcribe(root / identity, upload[0])
                duration = transcript.get('duration')
                if type(duration) not in (int,float) or not math.isfinite(duration) or not 0 < duration <= 1800:
                    raise ValueError('Invalid transcript duration; maximum 30 minutes')
                if not isinstance(transcript.get('segments'), list) or not transcript['segments']:
                    raise ValueError('Timestamped segments required')
                for s in transcript['segments']:
                    text(s['text'], 16000)
                    if not all(type(s[k]) in (int,float) and math.isfinite(s[k]) for k in ('start','end')) or not 0 <= s['start'] < s['end'] <= duration:
                        raise ValueError('Invalid transcript segment')
                with db:
                    if not alive():
                        raise ProviderError('lease_lost')
                    db.execute('INSERT OR IGNORE INTO teaching_transcripts(upload_id,body,provider,model) VALUES(?,?,?,?)',
                               (identity,json.dumps(transcript),provider.name,provider.transcription_model))
            source.update(duration=transcript['duration'], transcript_edition=1,
                          transcript_sha256=hashlib.sha256(json.dumps(transcript,sort_keys=True).encode()).hexdigest(),
                          paragraphs=[dict(paragraph=i+1,text=s['text'],start=s['start'],end=s['end']) for i,s in enumerate(transcript['segments'])])
        sources.append(source)
    if len(json.dumps(sources).encode()) > 80000:
        raise ValueError('Source package exceeds 80 KB analysis context')
    return sources


def process_claim(app, db, claim):
    from .teaching import finish_job, record_event
    def alive():
        return db.execute("SELECT 1 FROM teaching_jobs WHERE id=? AND state='running' AND lease_token=? AND lease_until>?",
                          (claim['id'],claim['lease_token'],int(time.time()))).fetchone() is not None
    try:
        factory = app.config.get('TEACHING_PROVIDER_FACTORY', OpenAIProvider)
        if factory is not OpenAIProvider and not app.testing:
            raise ProviderError('provider_test_adapter_refused')
        provider = factory()
        graph = active_graph(db)
        sources = source_snapshots(db, claim['id'], provider, Path(app.config['TEACHING_UPLOAD_DIR']), alive)
        if not alive():
            return 'lease_lost'
        draft = provider.generate(sources, graph)
        validate_draft(draft, sources, graph)
        with db:
            db.execute('BEGIN IMMEDIATE')
            if not alive():
                return 'lease_lost'
            db.execute('''INSERT INTO teaching_drafts(job_id,revision,body,sources,release_id,provider,model)
                          VALUES(?,1,?,?,?,?,?)''', (claim['id'],json.dumps(draft,ensure_ascii=False),json.dumps(sources,ensure_ascii=False),graph['release'],provider.name,provider.model))
            db.execute("UPDATE teaching_jobs SET state='ready',lease_token=NULL,lease_until=NULL,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?", (claim['id'],))
            record_event(db, claim['id'])
        return 'ready'
    except sqlite3.OperationalError:
        finish_job(db, claim, state='blocked', error_code='database_migration_required')
        return 'database_migration_required'
    except ProviderError as exc:
        code = str(exc)
        finish_job(db, claim, state='blocked' if code == 'provider_approved_configuration_required' else 'failed', error_code=code)
        return code
    except (ValueError, KeyError, TypeError, IndexError, AttributeError):
        finish_job(db, claim, state='failed', error_code='invalid_generated_draft_or_source')
        return 'invalid_generated_draft_or_source'


def register_drafts(app, db, query, editor, owned_job, dto):
    def current(id):
        owned_job(id)
        row = query('SELECT * FROM teaching_drafts WHERE job_id=? ORDER BY revision DESC LIMIT 1', (id,), True)
        if not row:
            abort(409, 'Черновик ещё не готов.')
        return row

    def payload():
        value = request.get_json(silent=True)
        if not isinstance(value, dict) or type(value.get('revision')) is not int:
            abort(400, 'Укажите revision.')
        return value

    def checked(value, sources, graph):
        try:
            return validate_draft(value, sources, graph)
        except (ValueError, KeyError, TypeError, IndexError, AttributeError):
            abort(400, 'Проверьте поля, источники и покрытие вопросов.')

    def draft_dto(row):
        published = query('SELECT lesson_id,release_id,draft_revision FROM teaching_publications WHERE job_id=?', (row['job_id'],), True)
        return dict(job_id=row['job_id'],revision=row['revision'],draft=json.loads(row['body']),
                    sources=json.loads(row['sources']),release_id=row['release_id'],provider=row['provider'],model=row['model'],
                    publication=dict(published) if published else None,coverage=coverage(json.loads(row['body'])))

    @app.post('/api/teaching/jobs/<id>/package')
    @editor
    def teaching_package(id):
        value = payload()
        ids = value.get('upload_ids')
        if not isinstance(ids, list) or not 1 <= len(ids) <= 5 or not all(isinstance(i,str) for i in ids) or len(set(ids)) != len(ids):
            abort(400, 'Укажите до пяти уникальных источников.')
        with db():
            db().execute('BEGIN IMMEDIATE')
            job = owned_job(id)
            if job['revision'] != value['revision'] or job['attempt'] or (job['state'] != 'queued' and job['error_code'] != 'awaiting_package') or job['upload_id'] not in ids:
                abort(409, 'Пакет можно собрать только до начала обработки.')
            if query('SELECT 1 FROM teaching_package_sources WHERE job_id=?',(id,),True):
                abort(409, 'Пакет уже собран.')
            for identity in ids:
                source_job = owned_job(identity)
                if source_job['owner_id'] != job['owner_id'] or source_job['attempt'] or (source_job['state'] != 'queued' and source_job['error_code'] != 'awaiting_package'):
                    abort(409, 'Источник уже обрабатывается.')
                if query('SELECT 1 FROM teaching_package_sources WHERE upload_id=?', (identity,), True):
                    abort(409, 'Источник уже включён в пакет.')
            from .teaching import record_event
            for position, identity in enumerate(ids):
                db().execute('INSERT INTO teaching_package_sources VALUES(?,?,?)',(id,identity,position))
                if identity != job['upload_id']:
                    db().execute("UPDATE teaching_jobs SET state='cancelled',error_code='included_in_package',revision=revision+1 WHERE id=?",(identity,))
                    record_event(db(),identity)
            db().execute("UPDATE teaching_jobs SET state='queued',error_code=NULL,revision=revision+1 WHERE id=?",(id,))
            record_event(db(),id)
        return jsonify(dto(owned_job(id)))

    @app.get('/api/teaching/jobs/<id>/draft')
    @editor
    def teaching_draft(id):
        return jsonify(draft_dto(current(id)))

    @app.put('/api/teaching/jobs/<id>/draft')
    @editor
    def teaching_edit(id):
        value = payload()
        with db():
            db().execute('BEGIN IMMEDIATE')
            row = current(id)
            if row['revision'] != value['revision'] or query('SELECT 1 FROM teaching_publications WHERE job_id=?',(id,),True):
                abort(409, 'Черновик изменился или уже опубликован.')
            graph = json.loads(query('SELECT body FROM skill_releases WHERE id=?',(row['release_id'],),True)['body'])
            checked(value.get('draft'),json.loads(row['sources']),graph)
            db().execute('''INSERT INTO teaching_drafts(job_id,revision,body,sources,release_id,provider,model,editor_id)
                          VALUES(?,?,?,?,?,?,?,?)''',(id,row['revision']+1,json.dumps(value['draft'],ensure_ascii=False),row['sources'],row['release_id'],row['provider'],row['model'],g.user['id']))
        return jsonify(draft_dto(current(id)))

    @app.post('/api/teaching/jobs/<id>/review')
    @editor
    def teaching_review(id):
        value = payload()
        with db():
            db().execute('BEGIN IMMEDIATE')
            row = current(id)
            if row['revision'] != value['revision'] or query('SELECT 1 FROM teaching_publications WHERE job_id=?', (id,), True):
                abort(409, 'Черновик изменился или уже опубликован.')
            graph = json.loads(query('SELECT body FROM skill_releases WHERE id=?', (row['release_id'],), True)['body'])
            draft = json.loads(row['body'])
            try:
                changes = review_action(draft, value.get('action', {}), graph)
            except (ValueError, KeyError, TypeError, AttributeError):
                abort(400, 'Проверьте выбранное действие и цель.')
            checked(draft, json.loads(row['sources']), graph)
            db().execute('''INSERT INTO teaching_drafts(job_id,revision,body,sources,release_id,provider,model,editor_id)
                          VALUES(?,?,?,?,?,?,?,?)''', (id,row['revision']+1,json.dumps(draft,ensure_ascii=False),row['sources'],row['release_id'],row['provider'],row['model'],g.user['id']))
        return jsonify(**draft_dto(current(id)), review_changes=changes)

    @app.get('/api/teaching/jobs/<id>/preview')
    @editor
    def teaching_preview(id):
        row = current(id); draft = json.loads(row['body'])
        return jsonify(revision=row['revision'],title=draft['title'],body=draft['body'],outcomes=draft['outcomes'],
                       practice=draft['practice'],assessments=[dict(node_id=f['node_id'],scope=f['scope'],items=[
                           {k:i[k] for k in ('id','prompt','choices','refs')} for i in f['items']]) for f in draft['assessments']],
                       coverage=coverage(draft),new_skills_publish=False,access_requires_editor_choice=True)

    @app.post('/api/teaching/jobs/<id>/publish')
    @editor
    def teaching_publish(id):
        value = payload()
        if value.get('confirm_reviewed') is not True or value.get('access') not in ('free','member'):
            abort(400, 'Подтвердите проверку источников, вопросов и условия доступа.')
        try:
            text(value.get('review_note'), 2000)
        except ValueError:
            abort(400, 'Добавьте краткий итог редакторской проверки.')
        with db():
            db().execute('BEGIN IMMEDIATE')
            row = current(id)
            if row['revision'] != value['revision']:
                abort(409, 'Черновик изменился.')
            old = query('SELECT lesson_id,release_id FROM teaching_publications WHERE job_id=?',(id,),True)
            if old:
                return jsonify(dict(old))
            graph = active_graph(db())
            draft = checked(json.loads(row['body']), json.loads(row['sources']),graph)
            identity = 'teaching-' + id
            release = 'teaching-map-' + id
            previous_release = graph['release']
            graph = copy.deepcopy(graph); graph['release'] = release
            db().execute('''INSERT INTO courses(id,title,description,outcome,goal,level,tools,prerequisites,author,updated_at,status)
                          VALUES(?,?,?,?,?,?,?,?,?,CURRENT_DATE,'published')''',
                         (identity,draft['title'],draft['summary'],draft['summary'],'essentials','По материалу автора','Указаны в уроке',
                          '\n'.join(draft['prerequisites']),g.user['name']))
            db().execute('INSERT INTO modules VALUES(?,?,?,0)',(identity,identity,draft['title']))
            media = next((s for s in json.loads(row['sources']) if s['kind']=='media'),None)
            video = 'teaching-' + media['source_id'] + Path(media['filename']).suffix if media and media['filename'].endswith(('.mp4','.webm')) else None
            db().execute('''INSERT INTO lessons(id,module_id,title,objective,body,minutes,position,access,video,task,checklist,status)
                          VALUES(?,?,?,?,?,?,0,?,?,?,?,'published')''',
                         (identity,identity,draft['title'],draft['summary'],draft['body'],draft['minutes'],value['access'],video,
                          draft['practice']['instructions'],'\n'.join(draft['practice']['checklist'])))
            for src in json.loads(row['sources']):
                db().execute("INSERT INTO resources(id,lesson_id,title,kind,content,status) VALUES(?,?,?,'link',?,'published')",
                             (identity+'-'+src['source_id'],identity,src['filename'],
                              '/api/teaching/published/'+identity+'/sources/'+src['source_id']+'/file'))
            for outcome in draft['outcomes']:
                graph['mappings'].append(dict(objective_id=outcome['objective_id'],lesson_id=identity,role='teaches',source=outcome['refs'][0]))
            db().execute('INSERT INTO skill_releases(id,body) VALUES(?,?)',(release,json.dumps(graph,ensure_ascii=False)))
            # Keep identities and attached practical rubrics across mapping edits.
            carry_forms(db(), query, previous_release, graph, g.user['id'])
            for index, form in enumerate(draft['assessments']):
                form = copy.deepcopy(form)
                for item in form['items']:
                    anchored = []
                    for ref in item['refs']:
                        src = next(s for s in json.loads(row['sources']) if s['source_id']==ref['source_id'])
                        span = next(p for p in src['paragraphs'] if p['paragraph']==ref['paragraph'])
                        anchored.append(dict(ref,lesson_id=identity,text=span['text'],
                            snapshot_url='/api/teaching/published/'+identity+'/sources/'+ref['source_id']))
                    item['refs'] = anchored
                    item['source'] = anchored[0]
                publish_reviewed_form(db(),id=identity+'-form-'+str(index),graph=graph,node_id=form['node_id'],form=form,access=value['access'],reviewer=g.user['id'])
            db().execute('INSERT INTO teaching_publications(job_id,draft_revision,lesson_id,release_id,reviewed_by,review_note) VALUES(?,?,?,?,?,?)',
                         (id,row['revision'],identity,release,g.user['id'],value['review_note']))
            db().execute('UPDATE skill_active SET release_id=? WHERE singleton=1',(release,))
        return jsonify(lesson_id=identity,release_id=release),201

    def published_source(lesson, source):
        row = query('''SELECT d.sources,l.access,l.status,c.status course_status FROM teaching_publications p
                       JOIN teaching_drafts d ON d.job_id=p.job_id AND d.revision=p.draft_revision
                       JOIN lessons l ON l.id=p.lesson_id JOIN modules m ON m.id=l.module_id JOIN courses c ON c.id=m.course_id
                       WHERE p.lesson_id=?''',(lesson,),True)
        if not row:
            abort(404)
        staff = g.user and g.user['role'] in ('editor','admin')
        if not staff and (row['status'] != 'published' or row['course_status'] != 'published'):
            abort(404)
        if row['access'] != 'free' and not staff and (not g.user or g.user['entitlement'] != 'member'):
            abort(403)
        result = next((s for s in json.loads(row['sources']) if s['source_id']==source),None)
        if not result:
            abort(404)
        return result

    @app.get('/api/teaching/published/<lesson>/sources/<source>')
    def teaching_historical_source(lesson, source):
        return jsonify(published_source(lesson,source))

    @app.get('/api/teaching/published/<lesson>/sources/<source>/file')
    def teaching_published_file(lesson, source):
        meta = published_source(lesson,source)
        upload = query('SELECT media_type FROM teaching_uploads WHERE id=?',(source,),True)
        return send_file(Path(app.config['TEACHING_UPLOAD_DIR'])/source, mimetype=upload['media_type'],
                         as_attachment=meta['kind']!='media',download_name=meta['filename'],conditional=True)
