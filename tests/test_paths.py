"""The path engine (club/paths.py) on the skill model (club/content/skills.json)."""
from club import paths


def test_every_goal_can_be_reached_from_zero():
    for goal in paths.model()['goals']:
        path = paths.build_path([goal['id']])
        assert path['reach'][goal['id']] == 1, goal['id']
        assert path['lessons'] and all(goal['id'] in l['goals'] for l in path['lessons'])


def test_known_skills_shorten_the_path_and_shared_lessons_count_once():
    fresh = paths.build_path(['profession'])
    skilled = paths.build_path(['profession'], {'dialog': 60, 'assistants': 40})
    assert len(skilled['lessons']) < len(fresh['lessons'])
    both = paths.build_path(['profession', 'lead'])
    keys = [l['key'] for l in both['lessons']]
    assert len(keys) == len(set(keys))
    assert any(set(l['goals']) == {'profession', 'lead'} for l in both['lessons'])
    assert len(both['lessons']) < len(fresh['lessons']) + len(paths.build_path(['lead'])['lessons'])


def test_a_course_that_builds_on_another_brings_its_foundation_first():
    path = paths.build_path(['it'])
    order = [l['course'] for l in path['lessons']]
    assert order.index('vibecoding-start') < order.index('vibecoding-pro')


def test_pace_turns_the_path_into_weeks_and_progress():
    path = paths.build_path(['startup'], deadlines={'startup': 13})
    slow, fast = paths.timeline(path, 40), paths.timeline(path, 270)
    assert slow['reached']['startup'] > fast['reached']['startup'] > 0
    assert paths.at_week(path, 120, 0)['goals']['startup'] == 0
    half = paths.at_week(path, 120, paths.timeline(path, 120)['weeks'] / 2)['goals']['startup']
    assert 0 < half < 1 and paths.at_week(path, 120, 1000)['goals']['startup'] == 1
    plans = paths.plans(path, {'startup': 13})
    assert [o['id'] for o in plans['options']] == ['light', 'steady', 'intense']
    needed = plans['needed_minutes_per_week']
    assert paths.timeline(path, needed)['reached']['startup'] <= 13 + 1e-9


def test_what_the_level_skips_before_the_path_in_a_course_is_listed_as_known():
    levels = {'dialog': 60, 'assistants': 48}
    path = paths.build_path(['startup', 'creator'], levels)
    taken = {l['key'] for l in path['lessons']}
    assert path['assumed'] and not set(path['assumed']) & taken
    assert not paths.build_path(['startup', 'creator'])['assumed']   # from zero nothing is assumed
