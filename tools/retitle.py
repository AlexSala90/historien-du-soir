"""Canvia el títol (fr i, si hi són, es/en) de vídeos ja pujats. Llegeix tools/retitle.json."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hds import upload

yt = upload.client()
up = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
ids, req = [], yt.playlistItems().list(part="snippet", playlistId=up, maxResults=50)
while req:
    res = req.execute()
    ids += [i["snippet"]["resourceId"]["videoId"] for i in res.get("items", [])]
    req = yt.playlistItems().list_next(req, res)
videos = []
for k in range(0, len(ids), 50):
    videos += yt.videos().list(part="snippet,localizations", id=",".join(ids[k:k+50])).execute().get("items", [])
for r in json.loads((Path(__file__).parent / "retitle.json").read_text()):
    hits = [v for v in videos if r["match"].lower() in v["snippet"]["title"].lower()]
    if len(hits) != 1:
        print(f"!! {r['match']}: {len(hits)} vídeos coincideixen, no faig res"); continue
    v = hits[0]; sn = v["snippet"]
    print(f"{v['id']}: «{sn['title']}» -> «{r['fr']}»")
    body = {"id": v["id"], "snippet": {k: sn[k] for k in ("title", "description", "categoryId", "tags", "defaultLanguage", "defaultAudioLanguage") if k in sn}}
    body["snippet"]["title"] = r["fr"]
    parts = "snippet"
    loc = v.get("localizations") or {}
    for lang in ("es", "en"):
        if lang in loc and r.get(lang):
            loc[lang]["title"] = r[lang]
    if loc:
        body["localizations"] = loc; parts += ",localizations"
    yt.videos().update(part=parts, body=body).execute()
    print("   fet")
