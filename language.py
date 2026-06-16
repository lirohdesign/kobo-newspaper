import json
import random
from datetime import datetime
from pathlib import Path

# Article sounds, so the phonetics match the displayed word (which carries the
# article). Elided articles (l') attach directly to the noun's sounds with no
# space — "l" + "ah-mee" → "lah-mee"; spaced articles get a space —
# "oo" + "ah-mee-goo" → "oo ah-mee-goo". Words without an article (colours)
# pass through unchanged.
FR_ARTICLES = {"l'": ("l", True), "le": ("luh", False),
               "la": ("lah", False), "les": ("lay", False)}
PT_ARTICLES = {"o": ("oo", False), "a": ("ah", False),
               "os": ("oos", False), "as": ("ahs", False)}


def _with_article(word, sounds, articles):
    if not sounds:
        return sounds
    w = word.lower()
    # elided article, e.g. l'ami
    if "'" in w:
        art = w.split("'", 1)[0] + "'"
        if art in articles and articles[art][1]:
            return articles[art][0] + sounds
    # spaced article, e.g. le chat / o gato
    if " " in w:
        head = w.split(" ", 1)[0]
        if head in articles:
            return f"{articles[head][0]} {sounds}"
    return sounds


def collect_language(today=None):
    if today is None:
        today = datetime.now()

    try:
        bank = json.loads(Path("language_bank.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("DEBUG: language_bank.json not found — run fetch_phonetics.py first")
        return ""
    except Exception as e:
        print(f"DEBUG: Language error: {e}")
        return ""

    rng = random.Random(int(today.strftime("%Y%j")))
    entry = rng.choice(bank)

    fr = entry["fr"]
    pt = entry["pt"]

    def word_row(label, word, sounds):
        ph = f" <span class='lang-sounds'>({sounds})</span>" if sounds else ""
        return f"<p class='lang-row'><span class='lang-label'>{label}</span> <span class='lang-word'>{word}</span>{ph}</p>"

    return (
        f"<div class='lang-block'>"
        f"<p class='lang-eng'><span class='lang-label'>en</span> {entry['eng']}</p>"
        f"{word_row('fr', fr['word'], _with_article(fr['word'], fr.get('sounds'), FR_ARTICLES))}"
        f"{word_row('pt', pt['word'], _with_article(pt['word'], pt.get('sounds'), PT_ARTICLES))}"
        f"</div>"
    )
