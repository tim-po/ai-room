"""Control points and course ranks: earned from completed modules, stored, celebrated once, never taken back."""
from club.ranks import standing
from test_learning import app, login, post
from test_skills import skills
from test_onboarding import onboard
from test_legacy_content import legacy, learner, demo_app

VIDEO_FREE, VIDEO_MEMBER = 'chatcut-video-editing', 'ai-video-skill'


def course(states, done=None, rank='Claude'):
    modules = [dict(title=f'Модуль {i + 1}', state=s, lessons=[dict(state='coming' if s == 'coming' else 'open')]) for i, s in enumerate(states)]
    return dict(id='c', title='Курс', rank_name=rank, modules=modules, done=done if done is not None else states.count('done'))


def test_rank_thresholds():
    assert standing(course(['active', 'coming'], done=0))['level'] == 0
    assert standing(course(['active', 'coming'], done=1))['title'] == 'Новичок Claude'
    assert standing(course(['done', 'active', 'active', 'coming']))['rank'] == 'Практик'
    assert standing(course(['done', 'done', 'active', 'coming']))['rank'] == 'Профи'
    assert standing(course(['done', 'done']))['title'] == 'Мастер Claude'
    assert standing(course(['done', 'active']))['rank'] == 'Практик'        # two points: Профи needs both, that's Мастер
    assert standing(course(['done', 'active', 'active', 'active']))['next'] == 'До звания «Профи Claude»: контрольная точка «Модуль 2»'
    assert standing(course(['done'] + ['active'] * 7))['next'] == 'До звания «Профи Claude»: ещё 3 контрольные точки'
    assert standing(course(['done', 'coming', 'coming']))['next'] == 'Следующие контрольные точки откроются с новыми уроками'


def test_completion_earns_and_the_map_celebrates_once(legacy):
    app = demo_app(legacy)
    c = app.test_client(); csrf = login(c, learner(app, 'climber', onboarded=True))
    earned = post(c, f'/api/lessons/{VIDEO_FREE}/completion', {'completed': True}, csrf).json['earned']
    assert {e['id'] for e in earned} == {'checkpoint:ai-video:0', 'rank:ai-video'}
    rank = next(e for e in earned if e['kind'] == 'rank')
    assert rank['title'] == 'Практик видео с ИИ' and 'Мастер видео с ИИ' in rank['next']
    home = c.get('/api/app/home').json
    assert {a['id'] for a in home['achievements']} == {'checkpoint:ai-video:0', 'rank:ai-video'}   # unseen until shown
    video = next(co for t in home['tree']['topics'] for co in t['courses'] if co['id'] == 'ai-video')
    assert video['standing']['rank'] == 'Практик' and [m['checkpoint'] for m in video['modules']] == [True, False]
    assert post(c, '/api/app/achievements/seen', {'ids': [a['id'] for a in home['achievements']]}, csrf).status_code == 200
    assert c.get('/api/app/home').json['achievements'] == []
    # Club lesson completes the course: Мастер. Taking a lesson back never lowers a rank.
    post(c, '/membership/demo', {'next': '/profile'}, csrf)
    master = post(c, f'/api/lessons/{VIDEO_MEMBER}/completion', {'completed': True}, csrf).json['earned']
    assert any(e['kind'] == 'rank' and e['title'] == 'Мастер видео с ИИ' for e in master)
    post(c, f'/api/lessons/{VIDEO_MEMBER}/completion', {'completed': False}, csrf)
    profile = c.get('/api/app/profile').json
    assert next(r for r in profile['ranks'] if r['course'] == 'ai-video')['title'] == 'Мастер видео с ИИ'
    assert post(c, f'/api/lessons/{VIDEO_MEMBER}/completion', {'completed': False}, csrf).json['earned'] == []
