import random
from datetime import datetime


def _rng(today):
    return random.Random(int(today.strftime("%Y%j")) * 100 + 11)


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


def _svg(grid, clues, n, filled):
    cs, mg = 60, 50
    W = mg + n * cs + mg
    top, right, bottom, left = clues

    def T(x, y, v, sz=20):
        return (f'<text x="{x}" y="{y}" text-anchor="middle" '
                f'dominant-baseline="middle" font-size="{sz}" '
                f'font-weight="bold" fill="#000">{v}</text>')

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {W}" '
           f'style="width:100%;max-width:320px;display:block">']

    gx, gy = mg, mg

    for c, v in enumerate(top):
        out.append(T(gx + c*cs + cs//2, mg//2, v))
    for c, v in enumerate(bottom):
        out.append(T(gx + c*cs + cs//2, gy + n*cs + mg//2, v))
    for r, v in enumerate(left):
        out.append(T(mg//2, gy + r*cs + cs//2, v))
    for r, v in enumerate(right):
        out.append(T(gx + n*cs + mg//2, gy + r*cs + cs//2, v))

    for r in range(n):
        for c in range(n):
            x, y = gx + c*cs, gy + r*cs
            out.append(f'<rect x="{x}" y="{y}" width="{cs}" height="{cs}" '
                       f'fill="{"#f0f0f0" if filled else "#fff"}" '
                       f'stroke="#000" stroke-width="1.5"/>')
            if filled:
                out.append(T(x + cs//2, y + cs//2, grid[r][c], sz=22))

    out.append(f'<rect x="{gx}" y="{gy}" width="{n*cs}" height="{n*cs}" '
               f'fill="none" stroke="#000" stroke-width="3"/>')
    out.append('</svg>')
    return ''.join(out)


def collect_towers(today=None):
    if today is None:
        today = datetime.now()
    rng = _rng(today)
    n = 3
    grid = _fill_grid(rng, n)
    clues = _clues(grid, n)
    return (
        f"<div class='puzzle-block'>"
        f"<p class='math-hint'>Fill each row and column with 1–{n}. "
        f"The number on each edge shows how many towers you can see from that side "
        f"— taller towers hide shorter ones behind them.</p>"
        f"{_svg(grid, clues, n, filled=False)}"
        f"<p>&nbsp;</p><p>&nbsp;</p><p>&nbsp;</p>"
        f"<p class='math-hint'>&#8645; flip for answer</p>"
        f"{_svg(grid, clues, n, filled=True)}"
        f"</div>"
    )
