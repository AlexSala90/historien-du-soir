"""L'Historien du Soir: d'un guió (episode.json) a un vídeo programat a YouTube.

Ús:
  python3 run.py produce EPISODE.json WORKDIR      # veu, imatges, làmina de control
  python3 run.py redo-images EPISODE.json WORKDIR 3,17,42   # refer imatges dolentes
  python3 run.py finish EPISODE.json WORKDIR       # muntatge, miniatura, fitxa, castellà i anglès
  python3 run.py publish WORKDIR                   # pujada i programació a YouTube
  python3 run.py languages WORKDIR                 # tornar a pujar traduccions i subtítols d'un vídeo ja pujat
  python3 run.py titles                            # tots els vídeos del canal (també programats/privats)
"""
import asyncio, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hds import fitxa, images, langs, montage, thumbnail, voice  # noqa: E402


def check_episode(ep):
    secs = ep["sections"]
    assert len(secs) == 10, "Cal 10 seccions"
    n = sum(len(s["text"]) for s in secs)
    print(f"Guió: {n} caràcters (objectiu 35–45 mil)")
    assert n >= 30000, "Guió massa curt"
    assert "Dormez bien" in secs[-1]["text"], "Falta el tancament fix"
    for lang, loc in (ep.get("localizations") or {}).items():
        assert lang in langs.LANGS, f"Idioma no previst: {lang}"
        assert len(loc.get("title", "")) <= 100, f"Títol {lang} massa llarg (màx. 100)"
        assert len(loc.get("section_titles", secs)) == len(secs), f"Calen {len(secs)} títols de secció en {lang}"


def main():
    cmd = sys.argv[1]
    if cmd == "titles":
        from hds import upload
        for t, st in upload.list_all_titles():
            print(f"{st:9} {t}")
        return
    if cmd == "publish":
        from hds import upload
        upload.publish(Path(sys.argv[2]))
        return
    if cmd == "languages":
        from hds import upload
        work = Path(sys.argv[2])
        upload.add_languages(work, json.loads((work / "published.json").read_text())["videoId"])
        return
    ep = json.loads(Path(sys.argv[2]).read_text())
    work = Path(sys.argv[3]); work.mkdir(parents=True, exist_ok=True)
    t = time.time()
    if cmd == "produce":
        check_episode(ep)
        asyncio.run(voice.build(ep, work))
        images.render(ep, work)
    elif cmd == "redo-images":
        images.render(ep, work, {int(x) for x in sys.argv[4].split(",")}, seed_offset=int(t) % 1000)
    elif cmd == "finish":
        montage.build(work)
        thumbnail.make(ep, work)
        fitxa.make(ep, work)
        langs.make(ep, work)
    print(f"Fet en {(time.time()-t)/60:.1f} min")


if __name__ == "__main__":
    main()
