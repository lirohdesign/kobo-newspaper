import random
from datetime import datetime
from itertools import permutations


SHAPES = ['circle', 'square', 'triangle', 'diamond']
N = 3


def _rng(today):
    return random.Random(int(today.strftime("%Y%j")) * 100 + 22)


def _score(secret, guess):
    black = sum(s == g for s, g in zip(secret, guess))
    white = sum(min(secret.count(s), guess.count(s)) for s in SHAPES) - black
    return black, white


def _shape(sh, cx, cy, r=13, fill="#1a1a1a"):
    if sh == 'circle':
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>'
    if sh == 'square':
        return f'<rect x="{cx-r}" y="{cy-r}" width="{r*2}" height="{r*2}" fill="{fill}"/>'
    if sh == 'triangle':
        h = int(r * 1.65)
        pts = f"{cx},{cy-h} {cx-r},{cy+r//2} {cx+r},{cy+r//2}"
        return f'<polygon points="{pts}" fill="{fill}"/>'
    if sh == 'diamond':
        pts = f"{cx},{cy-r-4} {cx+r},{cy} {cx},{cy+r+4} {cx-r},{cy}"
        return f'<polygon points="{pts}" fill="{fill}"/>'
    if sh == 'cross':
        t = max(4, r // 3)
        return (f'<rect x="{cx-t}" y="{cy-r}" width="{t*2}" height="{r*2}" fill="{fill}"/>'
                f'<rect x="{cx-r}" y="{cy-t}" width="{r*2}" height="{t*2}" fill="{fill}"/>')
    return ''


def _dots(black, white, cx, cy):
    r, gap = 5, 13
    start = cx - (N - 1) * gap / 2
    out = []
    for i in range(N):
        x = start + i * gap
        if i < black:
            out.append(f'<circle cx="{x}" cy="{cy}" r="{r}" fill="#000"/>')
        elif i < black + white:
            out.append(f'<circle cx="{x}" cy="{cy}" r="{r}" fill="none" stroke="#000" stroke-width="1.5"/>')
        else:
            out.append(f'<circle cx="{x}" cy="{cy}" r="{r}" fill="none" stroke="#ccc" stroke-width="1"/>')
    return ''.join(out)


def _svg(guesses_scores, secret, show_answer):
    cell, pad, score_w, row_h, legend_h = 50, 14, 38, 56, 62
    W = pad + N * cell + pad + score_w + pad
    n_rows = len(guesses_scores) + (1 if show_answer else 0)
    H = legend_h + n_rows * row_h + pad

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'style="width:100%;max-width:360px;display:block">']

    # Legend
    out.append(f'<text x="{pad}" y="13" font-size="11" fill="#555" font-weight="bold">shapes:</text>')
    sp = (W - pad * 2) // len(SHAPES)
    for i, sh in enumerate(SHAPES):
        cx = pad + i * sp + sp // 2
        out.append(_shape(sh, cx, 34, r=10, fill="#555"))
        out.append(f'<text x="{cx}" y="54" text-anchor="middle" font-size="10" fill="#555">'
                   f'{"crs" if sh == "cross" else sh[:3]}</text>')

    out.append(f'<line x1="{pad}" y1="{legend_h-3}" x2="{W-pad}" y2="{legend_h-3}" '
               f'stroke="#ccc" stroke-width="1"/>')

    # Guess rows
    for i, (guess, (black, white)) in enumerate(guesses_scores):
        ry = legend_h + i * row_h
        out.append(f'<rect x="{pad//2}" y="{ry}" width="{W-pad}" height="{row_h}" '
                   f'fill="{"#f5f5f5" if i % 2 == 0 else "#fff"}"/>')
        for ci, sh in enumerate(guess):
            out.append(_shape(sh, pad + ci * cell + cell // 2, ry + row_h // 2))
        out.append(_dots(black, white, pad + N * cell + pad + score_w // 2, ry + row_h // 2))

    # Answer row
    if show_answer:
        ry = legend_h + len(guesses_scores) * row_h
        out.append(f'<rect x="{pad//2}" y="{ry}" width="{W-pad}" height="{row_h}" fill="#111"/>')
        for ci, sh in enumerate(secret):
            out.append(_shape(sh, pad + ci * cell + cell // 2, ry + row_h // 2, fill="#fff"))
        out.append(f'<text x="{pad + N*cell + pad + score_w//2}" y="{ry + row_h//2}" '
                   f'text-anchor="middle" dominant-baseline="middle" '
                   f'font-size="16" fill="#fff" font-weight="bold">&#10003;</text>')

    out.append('</svg>')
    return ''.join(out)


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


def collect_guess(today=None):
    if today is None:
        today = datetime.now()
    rng = _rng(today)
    all_codes = list(permutations(SHAPES, N))
    secret = list(rng.choice(all_codes))
    guesses = _make_guesses(rng, secret, all_codes)
    puzzle = (
        f"<div class='puzzle-block'>"
        f"<p class='math-hint'>A secret code of {N} shapes (no repeats) was chosen from the {len(SHAPES)} above. "
        f"Each row shows a guess and its score: "
        f"&#9679; = right shape, right spot &nbsp; &#9675; = right shape, wrong spot. "
        f"What is the code?</p>"
        f"{_svg(guesses, secret, show_answer=False)}"
        f"</div>"
    )
    answer = f"<div class='puzzle-block'>{_svg(guesses, secret, show_answer=True)}</div>"
    return puzzle, answer
