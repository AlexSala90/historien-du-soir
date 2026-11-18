"""Pas 8: fitxa (títol, descripció amb capítols, etiquetes, paràmetres de publicació)."""
import json, re, sys
from pathlib import Path

CLOSING_CTA = ("Si ce voyage vous a aidé à trouver le repos, abonnez-vous pour nous retrouver "
               "d'autres nuits, en d'autres siècles. Dormez bien. 🌙")


EMOJI = re.compile("(?:[\U0001F1E6-\U0001F1FF]{2}|[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2300-\u23FF]"
                   "(?:[\uFE0F\U0001F3FB-\U0001F3FF]|\u200D[\U0001F000-\U0001FAFF\u2600-\u27BF]\uFE0F?)*)")


def clean_title(title):
    """Regles de títol: sense punt final abans de « | », com a màxim UN emoji (el primer)."""
    emojis = EMOJI.findall(title)
    t = EMOJI.sub("", title)
    t = re.sub(r"\s*\.+\s*\|", " |", t)          # «… pas. | Histoire» → «… pas | Histoire»
    t = re.sub(r"\s{2,}", " ", t).strip().rstrip(".").strip()
    return f"{t} {emojis[0]}" if emojis else t


def ts(sec):
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def make(ep, work):
    durations = json.loads((work / "sections.json").read_text())
    t, chapters = 0.0, []
    for sec, d in zip(ep["sections"], durations):
        chapters.append(f"{ts(t)} {sec['title']}")
        t += d
    title = clean_title(ep["title"])
    if title != ep["title"]:
        print(f"  Títol ajustat a les regles: {title}")
    assert "| Histoire pour dormir" in title, "El títol ha de contenir « | Histoire pour dormir »"
    assert len(title) <= 100, "Títol massa llarg per a YouTube (màx. 100)"
    desc = "\n".join([
        ep["description_intro"].strip(), "",
        "📖 Chapitres", *chapters, "",
        CLOSING_CTA, "",
        " ".join(ep["hashtags"][:3]),
    ])
    fitxa = {
        "title": title,
        "description": desc,
        "tags": ep["tags"],
        "categoryId": "27",  # Educació
        "language": "fr",
        "madeForKids": False,
        "containsSyntheticMedia": True,
        "publishAt": ep["publish_at"],
        "playlist": ep.get("playlist"),
        "duration_min": round(t / 60, 1),
    }
    (work / "fitxa.json").write_text(json.dumps(fitxa, ensure_ascii=False, indent=2))
    (work / "fitxa.txt").write_text(
        f"TÍTOL\n{title}\n\nDESCRIPCIÓ\n{desc}\n\nETIQUETES\n{', '.join(ep['tags'])}\n\n"
        f"Programat: {ep['publish_at']} · Educació · francès · no per a nens · contingut sintètic: Sí\n")
    print(f"Fitxa: {work/'fitxa.txt'}")
    return fitxa


if __name__ == "__main__":
    make(json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]))
