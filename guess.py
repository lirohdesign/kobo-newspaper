import os
import random
from datetime import datetime
from itertools import permutations

from PIL import Image, ImageDraw, ImageFont

SHAPES = ['circle', 'square', 'triangle', 'diamond']
N = 3
SS = 2          # supersample factor — render big, downscale for crisp edges
OUT_DIR = "puzzles"


def _rng(today):
    return random.Random(int(today.strftime("%Y%j")) * 100 + 22)


def _font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default(size=size)


def _score(secret, guess):
    black = sum(s == g for s, g in zip(secret, guess))
    white = sum(min(secret.count(s), guess.count(s)) for s in SHAPES) - black
    return black, white


def _shape(d, sh, cx, cy, r, s, fill="black", outline=None, ow=0):
    def P(pts):
        return [(x * s, y * s) for x, y in pts]
    if sh == 'circle':
        d.ellipse(P([(cx-r, cy-r), (cx+r, cy+r)]), fill=fill, outline=outline, width=ow*s)
    elif sh == 'square':
        d.rectangle(P([(cx-r, cy-r), (cx+r, cy+r)]), fill=fill, outline=outline, width=ow*s)
    elif sh == 'triangle':
        h = r * 1.5
        d.polygon(P([(cx, cy-h), (cx-r, cy+r*0.7), (cx+r, cy+r*0.7)]), fill=fill, outline=outline)
    elif sh == 'diamond':
        d.polygon(P([(cx, cy-r-3), (cx+r, cy), (cx, cy+r+3), (cx-r, cy)]), fill=fill, outline=outline)


def _dots(d, black, white, cx, cy, s):
    r, gap = 9, 26
    start = cx - (N - 1) * gap / 2
    for i in range(N):
        x = start + i * gap
        box = [(x-r)*s, (cy-r)*s, (x+r)*s, (cy+r)*s]
        if i < black:
            d.ellipse(box, fill="black")
        elif i < black + white:
            d.ellipse(box, outline="black", width=2*s)
        else:
            d.ellipse(box, outline=(200, 200, 200), width=max(1, s))


def _render_png(guesses_scores, secret, show_answer, path):
    cell, pad, score_w = 100, 30, 120
    row_h, legend_h = 100, 116
    s = SS
    W = pad + N * cell + pad + score_w + pad
    n_rows = len(guesses_scores) + (1 if show_answer else 0)
    H = legend_h + n_rows * row_h + pad

    img = Image.new("RGB", (W * s, H * s), "white")
    d = ImageDraw.Draw(img)
    label_f = _font(20 * s)
    head_f = _font(22 * s)

    # Legend — the four shapes so the reader knows the alphabet
    d.text((pad * s, 8 * s), "shapes:", fill=(90, 90, 90), font=head_f)
    sp = (W - pad * 2) / len(SHAPES)
    for i, sh in enumerate(SHAPES):
        cx = pad + i * sp + sp / 2
        _shape(d, sh, cx, 56, 18, s, fill=(90, 90, 90))
        d.text((cx * s, 92 * s), sh, fill=(90, 90, 90), font=label_f, anchor="mm")
    d.line([(pad*s, (legend_h-6)*s), ((W-pad)*s, (legend_h-6)*s)],
           fill=(200, 200, 200), width=max(1, s))

    # Guess rows
    for i, (guess, (black, white)) in enumerate(guesses_scores):
        ry = legend_h + i * row_h
        if i % 2 == 0:
            d.rectangle([(pad/2)*s, ry*s, (W-pad/2)*s, (ry+row_h)*s], fill=(245, 245, 245))
        for ci, sh in enumerate(guess):
            _shape(d, sh, pad + ci*cell + cell/2, ry + row_h/2, 28, s)
        _dots(d, black, white, pad + N*cell + pad + score_w/2, ry + row_h/2, s)

    # Answer row
    if show_answer:
        ry = legend_h + len(guesses_scores) * row_h
        d.rectangle([(pad/2)*s, ry*s, (W-pad/2)*s, (ry+row_h)*s], fill=(17, 17, 17))
        for ci, sh in enumerate(secret):
            _shape(d, sh, pad + ci*cell + cell/2, ry + row_h/2, 28, s, fill="white")
        ck = pad + N*cell + pad + score_w/2
        cy = ry + row_h/2
        d.line([((ck-16)*s, cy*s), ((ck-5)*s, (cy+12)*s), ((ck+18)*s, (cy-15)*s)],
               fill="white", width=4*s, joint="curve")

    img.resize((W, H), Image.LANCZOS).save(path, "JPEG", quality=92)


def _make_guesses(rng, secret, all_codes):
    remaining = list(all_codes)
    used, result = set(), []
    for _ in range(5):
        if len(remaining) <= 1 and len(result) >= 2:
            break
        candidates = [c for c in all_codes if list(c) != secret and c not in used]
        if not candidates:
            break
        sample = rng.sample(candidates, min(40, len(candidates)))
        best, best_gap = sample[0], float('inf')
        for g in sample:
            sc = _score(secret, list(g))
            after = sum(1 for c in remaining if _score(list(c), list(g)) == sc)
            gap = abs(after - len(remaining) / 2)
            if gap < best_gap:
                best_gap, best = gap, g
        sc = _score(secret, list(best))
        result.append((list(best), sc))
        used.add(best)
        remaining = [c for c in remaining if _score(list(c), list(best)) == sc]
    return result


def collect_guess(today=None, base_url=""):
    if today is None:
        today = datetime.now()
    rng = _rng(today)
    all_codes = list(permutations(SHAPES, N))
    secret = list(rng.choice(all_codes))
    guesses = _make_guesses(rng, secret, all_codes)

    os.makedirs(OUT_DIR, exist_ok=True)
    date = today.strftime("%Y-%m-%d")
    q_name = f"guess-{date}.jpg"
    a_name = f"guess-{date}-answer.jpg"
    _render_png(guesses, secret, False, os.path.join(OUT_DIR, q_name))
    _render_png(guesses, secret, True,  os.path.join(OUT_DIR, a_name))

    q_src = f"{base_url}/{OUT_DIR}/{q_name}"
    a_src = f"{base_url}/{OUT_DIR}/{a_name}"

    puzzle = (
        f"<div class='puzzle-block'>"
        f"<p class='math-hint'>A secret code of {N} shapes (no repeats) was chosen from the {len(SHAPES)} above. "
        f"Each row shows a guess and its score: "
        f"&#9679; = right shape, right spot &nbsp; &#9675; = right shape, wrong spot. "
        f"What is the code?</p>"
        f"<img src='{q_src}' alt='code breaker puzzle' class='apod-img'>"
        f"</div>"
    )
    answer = f"<div class='puzzle-block'><img src='{a_src}' alt='code breaker answer' class='apod-img'></div>"
    return puzzle, answer
