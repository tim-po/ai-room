"""Personal paths: from a learner's goals to an ordered list of lessons, and from a weekly pace to dates.

The model (club/content/skills.json, made by scripts/make_skill_model.py): 8 skills scored 0–100; every
lesson of the map adds points to one or two skills; a goal is a set of target points per skill.

The path: goals are served in order of their deadlines. For a goal, courses are tried in order of how
much they offer of what it still lacks; inside a course, lessons go in course order, and a lesson is
taken when it adds points to a skill the goal still lacks and the learner doesn't already know that part
(the lesson's place in its course lies below the learner's own level). A course that builds on another
(«requires») first pulls in what it needs. Lessons shared by several goals are taken once and remember
every goal they serve.

A goal's progress at any moment is how much of the gap between where the learner started and its
targets is covered: Σ min(points, target) − start, over Σ target − start.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

MODEL = Path(__file__).with_name('content') / 'skills.json'
MAX = 100
# Schedules offered on the last onboarding step: sessions a week × minutes a session.
PACES = (('light', 'Лёгкий', 2, 20), ('steady', 'Ровный', 4, 30), ('intense', 'Интенсив', 6, 45))


@lru_cache(maxsize=1)
def model():
    data = json.loads(MODEL.read_text(encoding='utf-8'))
    # Where each lesson sits in its course, per skill: the course's points up to and including it.
    running = {}
    for lesson in data['lessons']:
        totals = running.setdefault(lesson['course'], {})
        for skill, points in lesson['gains'].items():
            totals[skill] = totals.get(skill, 0) + points
        lesson['band'] = {s: totals[s] for s in lesson['gains']}
    data['goal_by_id'] = {g['id']: g for g in data['goals']}
    data['skill_ids'] = [s['id'] for s in data['skills']]
    return data


def clamp_levels(levels):
    m = model()
    return {s: max(0, min(MAX, int((levels or {}).get(s) or 0))) for s in m['skill_ids']}


def progress(goal, start, points):
    """0..1: how much of the gap from the start to the goal's targets the points cover."""
    need = sum(max(0, t - min(start.get(s, 0), t)) for s, t in goal['targets'].items())
    if not need:
        return 1.0
    got = sum(max(0, min(points.get(s, 0), t) - min(start.get(s, 0), t)) for s, t in goal['targets'].items())
    return min(1.0, got / need)


def build_path(goal_ids, levels=None, deadlines=None, minutes=None):
    """The ordered lessons for these goals. levels: the learner's points per skill (0–100);
    deadlines: weeks per goal (sooner goals go first); minutes: lesson key -> real minutes, when known.

    Also returns `assumed`: lessons skipped because the learner's level says they know them, lying before
    a lesson the path takes in the same course — «ты, вероятно, уже знаешь», so the path doesn't seem to
    start in the middle of a course."""
    m = model()
    goals = [m['goal_by_id'][g] for g in goal_ids if g in m['goal_by_id']]
    start = clamp_levels(levels)
    deadlines = deadlines or {}
    goals.sort(key=lambda g: (deadlines.get(g['id']) or 10 ** 6, goal_ids.index(g['id'])))
    state = dict(start)
    chosen, serves = [], {}
    by_course = {}
    for lesson in m['lessons']:
        by_course.setdefault(lesson['course'], []).append(lesson)

    def lacking(goal):
        return {s: t - state.get(s, 0) for s, t in goal['targets'].items() if state.get(s, 0) < t}

    def useful(lesson, skills):
        return any(skill in skills and points and lesson['band'][skill] > start.get(skill, 0) for skill, points in lesson['gains'].items())

    def take(lesson, goal_id):
        if lesson['key'] not in serves:
            chosen.append(lesson)
            serves[lesson['key']] = []
            for skill, points in lesson['gains'].items():
                state[skill] = min(MAX, state.get(skill, 0) + points)
        if goal_id not in serves[lesson['key']]:
            serves[lesson['key']].append(goal_id)

    def satisfy(requirement, goal_id, depth=0):
        """Pull in lessons until a course's prerequisite skills are met (any course that teaches them)."""
        for skill, level in requirement.items():
            # from the course that teaches this skill most (a foundation course, not one that itself builds on another)
            teaching = sorted(by_course.items(), key=lambda item: -sum(l['gains'].get(skill, 0) for l in item[1]))
            for course, lessons in teaching:
                if state.get(skill, 0) >= level or depth > 2:
                    break
                for lesson in lessons:
                    if state.get(skill, 0) >= level:
                        break
                    if lesson['gains'].get(skill) and useful(lesson, {skill}) and course not in m['requires']:
                        take(lesson, goal_id)

    for goal in goals:
        def offer(course):
            need = lacking(goal)
            return sum(min(p, need.get(s, 0)) for lesson in by_course[course] for s, p in lesson['gains'].items())
        for course in sorted(by_course, key=offer, reverse=True):
            if not lacking(goal) or not offer(course):
                continue
            pulled = False
            for lesson in by_course[course]:
                need = lacking(goal)
                if not need:
                    break
                if useful(lesson, need):
                    if not pulled and course in m['requires']:
                        satisfy(m['requires'][course], goal['id'])
                        pulled = True
                    take(lesson, goal['id'])
    # Every goal a lesson moves forward, not only the one it was taken for: replay the path and credit a
    # lesson to each goal whose target it raises while that goal still lacks the skill.
    replay = dict(start)
    for lesson in chosen:
        for goal in goals:
            if goal['id'] not in serves[lesson['key']] and any(
                    points and skill in goal['targets'] and replay.get(skill, 0) < goal['targets'][skill] for skill, points in lesson['gains'].items()):
                serves[lesson['key']].append(goal['id'])
        for skill, points in lesson['gains'].items():
            replay[skill] = min(MAX, replay.get(skill, 0) + points)
    minutes = minutes or {}
    lessons = [dict(key=l['key'], course=l['course'], module=l['module'], module_title=l['module_title'], title=l['title'],
                    lesson_id=l['lesson_id'], minutes=minutes.get(l['key'], l['minutes']), gains=l['gains'], goals=serves[l['key']])
               for l in chosen]
    reach = {g['id']: progress(g, start, state) for g in goals}
    last = {}
    for lesson in chosen:
        last[lesson['course']] = max(last.get(lesson['course'], -1), by_course[lesson['course']].index(lesson))
    assumed = [l['key'] for course, end in last.items() for l in by_course[course][:end]
               if l['key'] not in serves and any(points and l['band'][skill] <= start.get(skill, 0) for skill, points in l['gains'].items())]
    return dict(lessons=lessons, start=start, end=state, goals=[g['id'] for g in goals], reach=reach,
                minutes=sum(l['minutes'] for l in lessons), assumed=assumed)


def timeline(path, minutes_per_week):
    """When each lesson is done at this pace (in weeks), and when each goal is reached."""
    m = model()
    pace = max(1, minutes_per_week)
    points = dict(path['start'])
    elapsed = 0
    done, reached = [], {}
    for lesson in path['lessons']:
        elapsed += lesson['minutes']
        for skill, gain in lesson['gains'].items():
            points[skill] = min(MAX, points.get(skill, 0) + gain)
        week = elapsed / pace
        done.append(week)
        for goal_id in path['goals']:
            if goal_id not in reached and progress(m['goal_by_id'][goal_id], path['start'], points) >= .999:
                reached[goal_id] = week
    return dict(done=done, reached=reached, weeks=elapsed / pace)


def at_week(path, minutes_per_week, week):
    """The picture at a moment: lessons done, points per skill and each goal's progress."""
    m = model()
    budget = max(0, week) * max(1, minutes_per_week)
    points, spent, keys = dict(path['start']), 0, []
    for lesson in path['lessons']:
        if spent + lesson['minutes'] > budget:
            break
        spent += lesson['minutes']
        keys.append(lesson['key'])
        for skill, gain in lesson['gains'].items():
            points[skill] = min(MAX, points.get(skill, 0) + gain)
    return dict(done=keys, points=points, goals={g: progress(m['goal_by_id'][g], path['start'], points) for g in path['goals']})


def plans(path, deadlines=None):
    """The three schedules, each with when every goal is reached and whether that meets its deadline;
    plus the pace that meets every deadline (minutes a week), when there are deadlines."""
    deadlines = deadlines or {}
    out = []
    for pace_id, title, sessions, length in PACES:
        per_week = sessions * length
        line = timeline(path, per_week)
        out.append(dict(id=pace_id, title=title, sessions=sessions, session_minutes=length, minutes_per_week=per_week,
                        weeks=math.ceil(line['weeks']),
                        goals={g: dict(weeks=math.ceil(w) if w is not None else None, on_time=w is not None and (not deadlines.get(g) or w <= deadlines[g]))
                               for g in path['goals'] for w in [line['reached'].get(g)]}))
    needed = None
    if deadlines:
        line = timeline(path, 1)   # minutes of study before each goal is reached
        needed = max((line['reached'][g] / deadlines[g] for g in path['goals'] if deadlines.get(g) and g in line['reached']), default=None)
        needed = math.ceil(needed) if needed else None
    return dict(options=out, needed_minutes_per_week=needed)
