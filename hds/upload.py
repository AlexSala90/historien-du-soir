"""Publicació automàtica amb l'API de YouTube: pujada, programació, miniatura i llista.
Credencials: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (variables secretes de l'entorn)."""
import json, os, sys, time
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]


def client(scopes=SCOPES):
    creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
                        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
                        token_uri="https://oauth2.googleapis.com/token", scopes=scopes)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def _norm(t):
    import re, unicodedata
    t = unicodedata.normalize("NFC", t).lower()
    return re.sub(r"[^\w\s]", "", t).split() and " ".join(re.sub(r"[^\w\s]", "", t).split())


def find_playlist(yt, name):
    """Troba la llista encara que el títol a YouTube porti cometes o emojis."""
    req = yt.playlists().list(part="snippet", mine=True, maxResults=50)
    while req:
        res = req.execute()
        for p in res.get("items", []):
            if _norm(name) in _norm(p["snippet"]["title"]):
                return p["id"]
        req = yt.playlists().list_next(req, res)
    return None


def publish(work):
    f = json.loads((work / "fitxa.json").read_text())
    yt = client()
    body = {
        "snippet": {"title": f["title"], "description": f["description"], "tags": f["tags"],
                    "categoryId": f["categoryId"], "defaultLanguage": f["language"],
                    "defaultAudioLanguage": f["language"]},
        "status": {"privacyStatus": "private", "publishAt": f["publishAt"],
                   "selfDeclaredMadeForKids": f["madeForKids"],
                   "containsSyntheticMedia": f["containsSyntheticMedia"], "embeddable": True},
    }
    media = MediaFileUpload(str(work / "video.mp4"), mimetype="video/mp4", chunksize=16 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media, notifySubscribers=True)
    resp, tries = None, 0
    while resp is None:
        try:
            status, resp = req.next_chunk()
            if status:
                print(f"  pujat {status.progress()*100:.0f}%")
        except Exception as e:  # noqa: BLE001
            tries += 1
            if tries > 6:
                raise
            print(f"  error de pujada ({e!r}), reintent {tries}")
            time.sleep(5 * tries)
    vid = resp["id"]
    print(f"Pujat: https://youtu.be/{vid} (programat {f['publishAt']})")
    yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(work / "thumbnail.jpg"), mimetype="image/jpeg")).execute()
    if f.get("playlist"):
        pid = find_playlist(yt, f["playlist"])
        if pid:
            yt.playlistItems().insert(part="snippet", body={"snippet": {
                "playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
        else:
            print(f"  Avís: no trobo la llista «{f['playlist']}»")
    (work / "published.json").write_text(json.dumps({"videoId": vid, **f}, ensure_ascii=False, indent=2))
    add_languages(work, vid)
    return vid


def add_languages(work, vid):
    """Títol i descripció en castellà i anglès + subtítols fr/es/en. Mai fa fallar la publicació."""
    from googleapiclient.errors import HttpError
    loc_path = work / "localizations.json"
    if loc_path.exists():
        try:
            client().videos().update(part="localizations", body={
                "id": vid, "localizations": json.loads(loc_path.read_text())}).execute()
            print("  Títol i descripció en castellà i anglès afegits")
        except HttpError as e:
            print(f"  Avís: no s'han pogut afegir les traduccions del títol ({e})")
    # Els subtítols demanen el permís youtube.force-ssl. Sense «scopes» el testimoni porta tots
    # els permisos concedits; si encara no hi és, cal tornar a passar per authorize.py.
    yt = client(scopes=None)
    names = {"fr": "Français", "es": "Español", "en": "English"}
    for lang, name in names.items():
        srt = work / f"subs_{lang}.srt"
        if not srt.exists():
            continue
        try:
            yt.captions().insert(part="snippet", body={"snippet": {
                "videoId": vid, "language": lang, "name": name, "isDraft": False}},
                media_body=MediaFileUpload(str(srt), mimetype="application/octet-stream")).execute()
            print(f"  Subtítols {lang} pujats")
        except HttpError as e:
            if e.resp.status in (401, 403):
                print("  Avís: el permís de YouTube no inclou els subtítols. Cal tornar a autoritzar amb "
                      "authorize.py i actualitzar YT_REFRESH_TOKEN. Els .srt queden als artefactes «control».")
                return
            print(f"  Avís: subtítols {lang} no pujats ({e})")


if __name__ == "__main__":
    publish(Path(sys.argv[1]))


def list_all_titles():
    """Tots els vídeos del canal, també programats i privats (la pàgina pública no els mostra)."""
    yt = client()
    up = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    out, req = [], yt.playlistItems().list(part="snippet,status", playlistId=up, maxResults=50)
    while req:
        res = req.execute()
        out += [(i["snippet"]["title"], i["status"]["privacyStatus"]) for i in res.get("items", [])]
        req = yt.playlistItems().list_next(req, res)
    return out
