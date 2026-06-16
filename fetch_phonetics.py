"""
One-shot script: fetches IPA from Wiktionary for each entry in language_words.json
and writes language_bank.json with IPA and English-approximate phonetics.

Run once:  python3 fetch_phonetics.py
Then open language_bank.json and correct any bad 'sounds' values before use.
Re-run to refresh IPA if Wiktionary entries change.
"""

import json
import re
import time
import unicodedata
import requests
from bs4 import BeautifulSoup
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (kobo-newspaper language bank builder)"}

def norm(s):
    return unicodedata.normalize("NFC", s)

# French IPA phoneme → English approximation.
# Sorted longest-first for greedy matching; digraphs must precede components.
FR_MAPPING = [(norm(p), r) for p, r in sorted([
    ("ɑ̃", "ahn"), ("ɛ̃", "an"), ("ɔ̃", "ohn"), ("œ̃", "un"),
    ("ɛj", "ay"), ("aj", "ay"), ("uj", "wee"), ("wa", "wah"), ("ɥi", "wee"),
    ("ɡ", "g"), ("ʁ", "r"), ("ʀ", "r"), ("ʃ", "sh"), ("ʒ", "zh"),
    ("ɲ", "ny"), ("ŋ", "ng"), ("ɥ", "wy"),
    ("y", "ew"), ("ø", "uh"), ("œ", "uh"), ("ɔ", "aw"), ("ɛ", "eh"),
    ("ə", "uh"), ("ɑ", "ah"), ("ɐ", "uh"),
    ("a", "ah"), ("e", "ay"), ("i", "ee"), ("o", "oh"), ("u", "oo"),
    ("j", "y"), ("w", "w"),
    ("p", "p"), ("b", "b"), ("t", "t"), ("d", "d"), ("k", "k"), ("g", "g"),
    ("f", "f"), ("v", "v"), ("s", "s"), ("z", "z"), ("m", "m"), ("n", "n"), ("l", "l"),
    ("ˈ", ""), ("ˌ", ""), ("ː", ""),
], key=lambda x: -len(x[0]))]

# Portuguese (Brazilian) IPA phoneme → English approximation.
PT_MAPPING = [(norm(p), r) for p, r in sorted([
    ("ɐ̃w̃", "own"), ("ɐ̃j̃", "ain"),
    ("ɐ̃", "ahn"), ("ã", "ahn"), ("ẽ", "en"), ("ĩ", "een"), ("õ", "ohn"), ("ũ", "oon"),
    ("ɡ", "g"), ("ʃ", "sh"), ("ʒ", "zh"), ("ɲ", "ny"), ("ŋ", "ng"), ("ʎ", "ly"),
    ("ɾ", "r"), ("ʁ", "r"), ("ʀ", "r"), ("x", "h"),
    ("ɐ", "uh"), ("ɔ", "aw"), ("ɛ", "eh"), ("ə", "uh"),
    ("a", "ah"), ("e", "eh"), ("i", "ee"), ("o", "oh"), ("u", "oo"),
    ("j", "y"), ("w", "w"),
    ("p", "p"), ("b", "b"), ("t", "t"), ("d", "d"), ("k", "k"), ("g", "g"),
    ("f", "f"), ("v", "v"), ("s", "s"), ("z", "z"), ("m", "m"), ("n", "n"), ("l", "l"),
    ("ˈ", ""), ("ˌ", ""), ("ː", ""),
], key=lambda x: -len(x[0]))]


def ipa_to_sounds(ipa_str, mapping):
    ipa = norm(re.sub(r"^[/\[]|[/\]]$", "", ipa_str.strip()))
    ipa = ipa.replace("ˈ", ".").replace("ˌ", ".")
    syllables = [s for s in ipa.split(".") if s]
    parts = []
    for syl in syllables:
        out, i = "", 0
        while i < len(syl):
            matched = False
            for pat, rep in mapping:
                if syl[i:i + len(pat)] == pat:
                    out += rep
                    i += len(pat)
                    matched = True
                    break
            if not matched:
                i += 1
        if out:
            parts.append(out)
    return re.sub(r"-+", "-", "-".join(parts)).strip("-") or None


def get_wiktionary_ipa(lookup_word, language_section, prefer_dialect=None):
    try:
        r = requests.get(
            f"https://en.wiktionary.org/wiki/{lookup_word}",
            headers=HEADERS, timeout=15
        )
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        content = soup.find("div", class_="mw-parser-output")
        if not content:
            return None

        in_section = False
        candidates = []  # list of (ipa, parent_li_text)
        for child in content.children:
            if not hasattr(child, "name") or not child.name:
                continue
            if "mw-heading2" in child.get("class", []):
                if language_section in child.get_text():
                    in_section = True
                elif in_section:
                    break
                continue
            if not in_section:
                continue
            for span in child.find_all("span", class_="IPA"):
                raw = span.get_text(strip=True)
                ipa = re.sub(r"\s*\(.*?\)\s*", "", raw).strip()
                if not (ipa.startswith("/") or ipa.startswith("[")):
                    continue
                # Capture the enclosing <li> text for dialect detection
                li = span.find_parent("li")
                context = li.get_text() if li else ""
                candidates.append((ipa, context))

        if not candidates:
            return None
        if prefer_dialect:
            for ipa, ctx in candidates:
                if prefer_dialect.lower() in ctx.lower():
                    return ipa
        return candidates[0][0]
    except Exception as e:
        print(f"    Wiktionary error for '{lookup_word}': {e}")
        return None


def main():
    words = json.loads(Path("language_words.json").read_text())
    bank = []
    total = len(words)

    for idx, entry in enumerate(words, 1):
        eng = entry["eng"]
        print(f"[{idx}/{total}] {eng}")

        fr_ipa = get_wiktionary_ipa(entry["fr_lookup"], "French")
        time.sleep(0.8)
        pt_ipa = get_wiktionary_ipa(entry["pt_lookup"], "Portuguese", prefer_dialect="Brazil")
        time.sleep(0.8)

        fr_sounds = ipa_to_sounds(fr_ipa, FR_MAPPING) if fr_ipa else None
        pt_sounds = ipa_to_sounds(pt_ipa, PT_MAPPING) if pt_ipa else None

        print(f"  FR: {entry['fr_word']:20} {str(fr_ipa):28} → {fr_sounds}")
        print(f"  PT: {entry['pt_word']:20} {str(pt_ipa):28} → {pt_sounds}")

        bank.append({
            "topic": entry["topic"],
            "eng": eng,
            "fr": {"word": entry["fr_word"], "ipa": fr_ipa, "sounds": fr_sounds},
            "pt": {"word": entry["pt_word"], "ipa": pt_ipa, "sounds": pt_sounds},
        })

    Path("language_bank.json").write_text(
        json.dumps(bank, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    missing = sum(1 for e in bank if not e["fr"]["ipa"] or not e["pt"]["ipa"])
    print(f"\nDone — {total} entries, {missing} missing IPA (review and fill manually)")


if __name__ == "__main__":
    main()
