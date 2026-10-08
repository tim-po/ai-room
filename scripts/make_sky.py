"""Generate the abstract sky used by the Сумерки (dusk) and Рассвет (dawn) themes.

Shapes are white alpha masks (club/static/sky/*.svg); sky.css fills them with theme colour tokens,
so one scene serves both themes and its colours can animate. Also writes the scene markup
(club/templates/_sky.html). Deterministic: re-running gives the same art.
    python scripts/make_sky.py
"""
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'club' / 'static' / 'sky'
OUT.mkdir(parents=True, exist_ok=True)
for old in ['land-dusk.svg', 'land-dawn.svg', 'clouds-dusk-far.svg', 'clouds-dusk-near.svg', 'clouds-dawn-far.svg',
            'clouds-dawn-near.svg', 'rays-dusk.svg', 'rays-dawn.svg', 'motes.css']:
    (OUT / old).unlink(missing_ok=True)


def write(name, body, w, h, aspect='none', defs=''):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="{aspect}">'
           f'<defs>{defs}</defs>{body}</svg>')
    (OUT / name).write_text(svg)
    return len(svg)


def f(v):
    return f'{v:.1f}'.rstrip('0').rstrip('.')


def stars():
    """A sparse field: mostly faint points, a handful slightly brighter. No halos or sparkles."""
    rnd = random.Random(11)
    dim, bright = [], []
    for _ in range(70):
        x, y = rnd.uniform(0, 1600), 1000 * 0.6 * rnd.random() ** 1.4
        dim.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{rnd.choice([.6, .7, .8, .9])}" fill="#fff6ec" opacity="{rnd.uniform(.2, .55) * (1 - y / 800):.2f}"/>')
    for _ in range(7):
        x, y = rnd.uniform(60, 1540), 1000 * 0.45 * rnd.random() ** 1.2
        bright.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{rnd.uniform(1.1, 1.5):.1f}" fill="#fffaf3" opacity=".8"/>')
    return (write('stars.svg', ''.join(dim), 1600, 1000, 'xMidYMin slice')
            + write('stars-bright.svg', ''.join(bright), 1600, 1000, 'xMidYMin slice'))


def rays():
    """Soft fan of light shafts, centred on the sun (middle of the square)."""
    rnd = random.Random(4)
    defs = ('<radialGradient id="g" cx="500" cy="500" r="500" gradientUnits="userSpaceOnUse">'
            '<stop offset="0" stop-color="#fff"/><stop offset=".45" stop-color="#fff" stop-opacity=".45"/>'
            '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
            '<filter id="b" x="-.2" y="-.2" width="1.4" height="1.4"><feGaussianBlur stdDeviation="9"/></filter>')
    parts = []
    for i in range(12):
        angle = -78 + 156 * (i + rnd.uniform(.25, .75)) / 12
        half = rnd.uniform(1.2, 4.8)
        pts = [(500, 500)] + [(500 + 500 * math.sin(math.radians(a)), 500 - 500 * math.cos(math.radians(a))) for a in (angle - half, angle + half)]
        parts.append('<path d="M' + ' L'.join(f'{f(x)},{f(y)}' for x, y in pts) + f'Z" opacity="{rnd.uniform(.4, 1):.2f}"/>')
    return write('rays.svg', f'<g fill="url(#g)" filter="url(#b)">{"".join(parts)}</g>', 1000, 1000, 'xMidYMid meet', defs)


def wrap(body):
    """Tile-safe: shapes crossing an edge reappear on the other side, so drifting strips loop."""
    return f'<g id="t">{body}</g><use href="#t" x="-1600"/><use href="#t" x="1600"/>'


def clouds(name, seed, count, rx, ry, blur):
    """Abstract cloud forms: a few long, very soft blobs."""
    rnd = random.Random(seed)
    parts = []
    for _ in range(count):
        cx, cy = rnd.uniform(0, 1600), rnd.uniform(110, 300)
        for _ in range(rnd.randint(1, 2)):
            parts.append(f'<ellipse cx="{f(cx + rnd.uniform(-90, 90))}" cy="{f(cy + rnd.uniform(-8, 8))}" '
                         f'rx="{f(rnd.uniform(*rx))}" ry="{f(rnd.uniform(*ry))}" opacity="{rnd.uniform(.4, .8):.2f}"/>')
    defs = f'<filter id="s" x="-.2" y="-2" width="1.4" height="5"><feGaussianBlur stdDeviation="{blur}"/></filter>'
    return write(name, wrap(f'<g fill="#fff" filter="url(#s)">{"".join(parts)}</g>'), 1600, 400, 'none', defs)


def curve(seed, base, amp):
    rnd = random.Random(seed)
    waves = [(rnd.uniform(.0018, .0032), rnd.uniform(0, 6), amp), (rnd.uniform(.005, .008), rnd.uniform(0, 6), amp * .35)]
    return [(x, base - sum(a * math.sin(x * k + p) for k, p, a in waves)) for x in range(0, 1610, 10)]


def path(points, close=True):
    d = ' L'.join(f'{x},{f(y)}' for x, y in points)
    return f'M0,420 L{d} L1600,420Z' if close else f'M{d}'


def horizon():
    """Three smooth abstract bands and a thin light edge along the farthest one. Edges are crisp
    (anti-aliased, no blur): softness lives in the sky and clouds, not in the shapes."""
    far, mid, near = curve(3, 110, 26), curve(7, 205, 22), curve(12, 300, 16)
    size = write('band-far.svg', f'<path d="{path(far)}" fill="#fff"/>', 1600, 420)
    size += write('band-mid.svg', f'<path d="{path(mid)}" fill="#fff"/>', 1600, 420)
    size += write('band-near.svg', f'<path d="{path(near)}" fill="#fff"/>', 1600, 420)
    size += write('band-rim.svg', f'<path d="{path(far, False)}" fill="none" stroke="#fff" stroke-width="1.6" vector-effect="non-scaling-stroke"/>', 1600, 420)
    return size


if __name__ == '__main__':
    size = stars() + rays() + horizon()
    size += clouds('clouds-far.svg', 31, 3, (240, 420), (8, 14), '16 7')
    size += clouds('clouds-near.svg', 37, 3, (300, 520), (14, 24), '24 11')
    (OUT / 'orbs.css').unlink(missing_ok=True)
    (ROOT / 'club' / 'templates' / '_sky.html').write_text(
        '{# Generated by scripts/make_sky.py. Decorative sky for the Сумерки/Рассвет themes. #}\n'
        '<div class="sky" aria-hidden="true"><div class="sky-night"><div class="sky-stars"></div><div class="sky-stars sky-stars-bright"></div></div>'
        '<div class="sky-sun"><div class="sky-sun-rays"></div><div class="sky-sun-halo"></div><div class="sky-sun-disc"></div></div>'
        '<div class="sky-clouds sky-clouds-far"></div><div class="sky-clouds sky-clouds-near"></div><div class="sky-haze"></div>'
        '<div class="sky-band sky-band-far"></div><div class="sky-band sky-band-rim"></div><div class="sky-band sky-band-mid"></div><div class="sky-band sky-band-near"></div></div>\n')
    print(f'sky art: {size // 1024} KB')
