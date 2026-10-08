"""Milestones and course ranks: 2-3 goals between modules, stored, celebrated once, never taken back."""
from club.ranks import placements, standing
from test_learning import app, login, post
from test_skills import skills
from test_onboarding import onboard
from test_legacy_content import legacy, learner, demo_app

VIDEO_FREE, VIDEO_MEMBER = 'chatcut-video-editing', 'ai-video-skill'
STATE = {'d': 'done', 'o': 'open', 'c': 'coming', 'l': 'locked'}


def course(*modules, rank='Claude'):
    """course('dd', 'oo', 'cc'): one string per module, one letter per lesson."""
    built = [dict(title=f'Модуль {i + 1}', lessons=[dict(state=STATE[ch]) for ch in m]) for i, m in enumerate(modules)]
    return dict(id='c', title='Курс', rank_name=rank, modules=built, done=sum(m.count('d') for m in modules))


def test_milestones_stand_between_modules():
    assert placements(course('ooo', 'ooo', 'ooo')['modules']) == [0, 1, 2]            # 9 lessons: three
    assert placements(course('oo', 'oo', 'oo', 'oo')['modules']) == [1, 3]            # 8 lessons: two, halfway and the end
    assert placements(course('o' * 10)['modules']) == [0]                             # one module: the end only
    assert placements(course('o' * 8, 'o', 'o')['modules']) == [0, 1, 2]              # never two at one place


def test_ranks_follow_milestones():
    level = lambda *m, best=0: standing(course(*m), best)[0]
    assert level('ooo', 'ooo', 'ooo')['level'] == 0
    assert level('doo', 'ooo', 'ooo')['title'] == 'Новичок Claude'
    first = level('ddd', 'ooo', 'ooo')
    assert first['rank'] == 'Практик' and first['next'] == 'До вехи «Профи Claude»: ещё 3 урока'
    assert level('ddd', 'ddd', 'ooo')['rank'] == 'Профи'
    assert level('ddd', 'ddd', 'ddd')['title'] == 'Мастер Claude' and level('ddd', 'ddd', 'ddd')['next'] == 'Высшее звание курса'
    assert level('dd', 'oo')['rank'] == 'Практик'                                       # two milestones: Практик, then Мастер
    assert level('ddd', 'ccc', 'ccc')['next'] == 'Следующая веха откроется с новыми уроками'
    _, stones = standing(course('ddd', 'doo', 'ccc'))
    assert [m['state'] for m in stones] == ['reached', 'next', 'ahead'] and stones[1]['left'] == 2
    _, stones = standing(course('ddd', 'dcc', 'ooo'))
    assert [m['state'] for m in stones] == ['reached', 'coming', 'next']
    # Earned once, kept: a reached milestone stays reached when a lesson is taken back.
    kept, stones = standing(course('doo', 'ooo', 'ooo'), best=2)
    assert kept['rank'] == 'Практик' and stones[0]['state'] == 'reached'


def test_completion_earns_and_the_map_celebrates_once(legacy):
    app = demo_app(legacy)
    c = app.test_client(); csrf = login(c, learner(app, 'climber', onboarded=True))
    earned = post(c, f'/api/lessons/{VIDEO_FREE}/completion', {'completed': True}, csrf).json['earned']
    assert [e['id'] for e in earned] == ['rank:ai-video']                    # the milestone is celebrated as its rank
    rank = earned[0]
    assert rank['title'] == 'Практик видео с ИИ' and 'Мастер видео с ИИ' in rank['next'] and rank['milestone'] == {'number': 1, 'of': 2}
    home = c.get('/api/app/home').json
    assert [a['id'] for a in home['achievements']] == ['rank:ai-video']    # unseen until shown
    video = next(co for t in home['tree']['topics'] for co in t['courses'] if co['id'] == 'ai-video')
    assert video['standing']['rank'] == 'Практик' and [m['state'] for m in video['milestones']] == ['reached', 'next']
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
