import json
import random
from datetime import datetime
from pathlib import Path


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
        f"{word_row('fr', fr['word'], fr.get('sounds'))}"
        f"{word_row('pt', pt['word'], pt.get('sounds'))}"
        f"</div>"
    )
