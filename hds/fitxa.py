"""Pas 8: fitxa (títol, descripció amb capítols, etiquetes, paràmetres de publicació)."""
import json, sys
from pathlib import Path

CLOSING_CTA = ("Si ce voyage vous a aidé à trouver le repos, abonnez-vous pour nous retrouver "
               "d'autres nuits, en d'autres siècles. Dormez bien. 🌙")


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
    title = ep["title"]
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
