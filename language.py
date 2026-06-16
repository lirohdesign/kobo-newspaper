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

    def word_row(word, sounds):
        ph = f" <span class='lang-sounds'>({sounds})</span>" if sounds else ""
        return f"<span class='lang-word'>{word}</span>{ph}"

    rows = f"""
<table class='lang-table'>
  <tr>
    <td class='lang-flag'>🇺🇸</td>
    <td class='lang-eng'>{entry['eng']}</td>
  </tr>
  <tr>
    <td class='lang-flag'>🇫🇷</td>
    <td>{word_row(fr['word'], fr.get('sounds'))}</td>
  </tr>
  <tr>
    <td class='lang-flag'>🇧🇷</td>
    <td>{word_row(pt['word'], pt.get('sounds'))}</td>
  </tr>
</table>"""

    return f"<div class='lang-block'>{rows}</div>"
