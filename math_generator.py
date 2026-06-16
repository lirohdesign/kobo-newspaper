import random
from datetime import datetime


def _rng(today=None):
    if today is None:
        today = datetime.now()
    return random.Random(int(today.strftime("%Y%j")))


def _skip_counting(rng):
    step = rng.choice([2, 3, 5, 10, 11, 25, 50, 100])
    start = rng.randint(1, 10) * step
    seq = [start + i * step for i in range(5)]
    blank = rng.randint(1, 3)
    answer = seq[blank]
    display = [str(n) if i != blank else "___" for i, n in enumerate(seq)]
    return " → ".join(display), answer, step


def _nines_trick(rng):
    trick = rng.choice([9, 19, 29, 39, 49, 99])
    other = rng.randint(11, 89)
    hint = f"Think {trick + 1} + {other} − 1"
    return f"{trick} + {other}", trick + other, hint


def _basic_facts(rng):
    facts = []
    for _ in range(4):
        op = rng.choice(["add", "sub", "mul"])
        if op == "add":
            a, b = rng.randint(1, 50), rng.randint(1, 50)
            facts.append((f"{a} + {b}", a + b))
        elif op == "sub":
            a = rng.randint(10, 99)
            b = rng.randint(1, a)
            facts.append((f"{a} − {b}", a - b))
        else:
            a = rng.choice([2, 3, 4, 5, 10, 11])
            b = rng.randint(1, 12)
            facts.append((f"{a} × {b}", a * b))
    return facts


def collect_math_challenge(today=None):
    rng = _rng(today)
    seq_display, seq_ans, step = _skip_counting(rng)
    nines_prob, nines_ans, nines_hint = _nines_trick(rng)
    facts = _basic_facts(rng)

    facts_html = "".join(f"<li>{prob} = ____</li>" for prob, _ in facts)

    challenge = (
        f"<div class='math-challenge'>"
        f"<p><strong>1. fill in the missing number</strong><br>"
        f"count by {step}s: <span class='math-seq'>{seq_display}</span></p>"
        f"<p><strong>2. mental math</strong><br>"
        f"<span class='math-seq'>{nines_prob} = ____</span><br>"
        f"<span class='math-hint'>hint: {nines_hint}</span></p>"
        f"<p><strong>3. quick facts</strong></p>"
        f"<ul class='fact-list'>{facts_html}</ul>"
        f"</div>"
    )

    answer_lines = [
        f"missing number: {seq_ans}",
        f"mental math: {nines_ans}",
        "quick facts: " + " &nbsp;·&nbsp; ".join(str(a) for _, a in facts),
    ]
    answers = "".join(f"<p class='math-answers'>{line}</p>" for line in answer_lines)

    return challenge, answers
