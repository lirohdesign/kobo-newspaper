import os
import random
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

SS = 2          # supersample factor — render big, downscale for crisp edges
OUT_DIR = "puzzles"


def _rng(today):
    return random.Random(int(today.strftime("%Y%j")) * 100 + 11)


def _font(size):
    # CI has DejaVu on disk; elsewhere Pillow's embedded default is scalable.
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default(size=size)


def _fill_grid(rng, n):
    grid = [[0] * n for _ in range(n)]

    def ok(r, c, v):
        return v not in grid[r] and all(grid[rr][c] != v for rr in range(n))

    def solve(pos):
        if pos == n * n:
            return True
        r, c = divmod(pos, n)
        nums = list(range(1, n + 1))
        rng.shuffle(nums)
        for v in nums:
            if ok(r, c, v):
                grid[r][c] = v
                if solve(pos + 1):
                    return True
                grid[r][c] = 0
        return False

    solve(0)
    return grid


def _visible(seq):
    count, peak = 0, 0
    for h in seq:
        if h > peak:
            count += 1
            peak = h
    return count


def _clues(grid, n):
    top    = [_visible(grid[r][c] for r in range(n))         for c in range(n)]
    bottom = [_visible(grid[r][c] for r in range(n-1,-1,-1)) for c in range(n)]
    left   = [_visible(grid[r])                              for r in range(n)]
    right  = [_visible(reversed(grid[r]))                    for r in range(n)]
    return top, right, bottom, left


def _render_png(grid, clues, n, filled, path):
    cs, mg = 120, 80                 # logical px: cell size, clue margin
    W = mg + n * cs + mg
    s = SS
    top, right, bottom, left = clues

    img = Image.new("RGB", (W * s, W * s), "white")
    d = ImageDraw.Draw(img)
    clue_f = _font(46 * s)
    num_f = _font(56 * s)

    def tc(x, y, val, font):
        d.text((x * s, y * s), str(val), fill="black", font=font, anchor="mm",
               stroke_width=max(1, s // 2), stroke_fill="black")

    gx = gy = mg
    for c, v in enumerate(top):    tc(gx + c*cs + cs/2, mg/2, v, clue_f)
    for c, v in enumerate(bottom): tc(gx + c*cs + cs/2, gy + n*cs + mg/2, v, clue_f)
    for r, v in enumerate(left):   tc(mg/2, gy + r*cs + cs/2, v, clue_f)
    for r, v in enumerate(right):  tc(gx + n*cs + mg/2, gy + r*cs + cs/2, v, clue_f)

    for r in range(n):
        for c in range(n):
            x, y = (gx + c*cs) * s, (gy + r*cs) * s
            d.rectangle([x, y, x + cs*s, y + cs*s],
                        fill=((240, 240, 240) if filled else "white"),
                        outline="black", width=2 * s)
            if filled:
                tc(gx + c*cs + cs/2, gy + r*cs + cs/2, grid[r][c], num_f)

    d.rectangle([gx*s, gy*s, (gx + n*cs)*s, (gy + n*cs)*s],
                outline="black", width=4 * s)

    img.resize((W, W), Image.LANCZOS).save(path)


def collect_towers(today=None, base_url=""):
    if today is None:
        today = datetime.now()
    rng = _rng(today)
    n = 3
    grid = _fill_grid(rng, n)
    clues = _clues(grid, n)

    os.makedirs(OUT_DIR, exist_ok=True)
    date = today.strftime("%Y-%m-%d")
    q_name = f"towers-{date}.png"
    a_name = f"towers-{date}-answer.png"
    _render_png(grid, clues, n, False, os.path.join(OUT_DIR, q_name))
    _render_png(grid, clues, n, True,  os.path.join(OUT_DIR, a_name))

    q_src = f"{base_url}/{OUT_DIR}/{q_name}"
    a_src = f"{base_url}/{OUT_DIR}/{a_name}"

    puzzle = (
        f"<div class='puzzle-block'>"
        f"<p class='math-hint'>Fill each row and column with 1–{n}. "
        f"The number on each edge shows how many towers you can see from that side "
        f"— taller towers hide shorter ones behind them.</p>"
        f"<img src='{q_src}' alt='towers puzzle' class='apod-img'>"
        f"</div>"
    )
    answer = f"<div class='puzzle-block'><img src='{a_src}' alt='towers answer' class='apod-img'></div>"
    return puzzle, answer
