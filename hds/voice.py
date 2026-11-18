"""Pas 4: veu. Edge TTS Rémy (-18 %, -10 Hz) + tractament «Rémy càlid mig»."""
import asyncio, html, json, os, re, subprocess, sys
from pathlib import Path

import edge_tts

VOICE = "fr-FR-RemyMultilingualNeural"
RATE, PITCH = "-18%", "-10Hz"
MAX_CHARS = 1400
GAP_CHUNK, GAP_SECTION = 0.8, 2.5
SR = 24000
# To una mica més greu, més greus, menys aguts, compressió suau i una mica de sala.
WARM = ("asetrate={sr}*0.97,aresample={sr},atempo=1.0309,"
        "equalizer=f=140:t=q:w=1:g=3,equalizer=f=5500:t=q:w=1.2:g=-3.5,"
        "acompressor=threshold=-20dB:ratio=2.2:attack=15:release=250:makeup=2,"
        "aecho=0.85:0.7:28:0.10").format(sr=SR)


def chunks(text):
    """Talla per paràgrafs en fragments de màx. MAX_CHARS caràcters."""
    out, cur = [], ""
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    for p in paras:
        pieces = [p] if len(p) <= MAX_CHARS else re.split(r"(?<=[.!?…])\s+", p)
        for piece in pieces:
            if cur and len(cur) + 1 + len(piece) > MAX_CHARS:
                out.append(cur); cur = piece
            else:
                cur = f"{cur}\n{piece}" if cur else piece
    if cur:
        out.append(cur)
    return out


def dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


async def tts_one(text, mp3, sem):
    proxy = os.environ.get("HTTPS_PROXY")
    async with sem:
        for attempt in range(1, 4):
            try:
                c = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH, proxy=proxy)
                await c.save(str(mp3), str(mp3.with_suffix(".json")))  # temps de cada frase (subtítols)
                d = dur(mp3)
                cps = len(text) / d if d else 0
                if 11 <= cps <= 17.5:
                    return d, cps
                print(f"  {mp3.name}: velocitat estranya {cps:.1f} c/s, regenero ({attempt})")
            except Exception as e:  # noqa: BLE001
                print(f"  {mp3.name}: error {e!r}, reintent {attempt}")
            await asyncio.sleep(2 * attempt)
        raise RuntimeError(f"No s'ha pogut generar {mp3.name}")


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?…»])\s+|\n+", text) if s.strip()]


def chunk_timeline(mp3, text, length):
    """Frases d'un fragment amb el seu inici i final (s). Usa els temps que dona Edge TTS;
    si no hi són (àudio de caché antic), reparteix la durada segons els caràcters."""
    meta = mp3.with_suffix(".json")
    out = []
    if meta.exists():
        for line in meta.read_text().splitlines():
            if not line.strip():
                continue
            m = json.loads(line)
            if m.get("type") in ("SentenceBoundary", "WordBoundary") and m.get("text", "").strip():
                a = m["offset"] / 1e7
                out.append({"start": a, "end": a + m["duration"] / 1e7, "text": html.unescape(m["text"]).strip()})
    if not out:
        sents = sentences(text)
        total = sum(len(x) for x in sents) or 1
        t = 0.0
        for x in sents:
            d = length * len(x) / total
            out.append({"start": t, "end": t + d, "text": x.strip()})
            t += d
    for x in out:
        x["start"], x["end"] = min(x["start"], length), min(x["end"], length)
    return out


def section_timeline(vdir, si, n, offset, actual):
    """Frases d'una secció amb temps absoluts dins del vídeo, ajustades a la durada real de la secció."""
    items, t = [], 0.0
    for ci in range(n):
        mp3 = vdir / f"s{si:02d}_c{ci:02d}.mp3"
        length = dur(mp3.with_suffix(".wav"))
        for x in chunk_timeline(mp3, mp3.with_suffix(".txt").read_text(), length):
            items.append({"start": t + x["start"], "end": t + x["end"], "text": x["text"]})
        t += length + (GAP_CHUNK if ci < n - 1 else GAP_SECTION)
    k = actual / t if t else 1.0  # el tractament de veu pot allargar uns mil·lisegons
    return [{"start": round(offset + x["start"] * k, 3), "end": round(offset + x["end"] * k, 3),
             "text": x["text"]} for x in items]


def silence(path, secs):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    f"anullsrc=r={SR}:cl=mono", "-t", str(secs), str(path)], check=True)


async def build(ep, work):
    vdir = work / "voice"; vdir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(3)
    jobs, layout = [], []
    for si, sec in enumerate(ep["sections"]):
        parts = chunks(sec["text"])
        layout.append(len(parts))
        for ci, txt in enumerate(parts):
            mp3 = vdir / f"s{si:02d}_c{ci:02d}.mp3"
            mp3.with_suffix(".txt").write_text(txt)
            if mp3.exists() and dur(mp3) > 1:
                continue
            jobs.append(tts_one(txt, mp3, sem))
    await asyncio.gather(*jobs)
    silence(vdir / "gap_chunk.wav", GAP_CHUNK)
    silence(vdir / "gap_section.wav", GAP_SECTION)
    durations, timeline = [], []
    for si, n in enumerate(layout):
        lst = vdir / f"s{si:02d}.txt"
        lines = []
        for ci in range(n):
            mp3 = vdir / f"s{si:02d}_c{ci:02d}.mp3"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-ar", str(SR), "-ac", "1",
                            str(mp3.with_suffix(".wav"))], check=True)
            lines.append(f"file 's{si:02d}_c{ci:02d}.wav'")
            lines.append("file 'gap_chunk.wav'" if ci < n - 1 else "file 'gap_section.wav'")
        lst.write_text("\n".join(lines) + "\n")
        wav = vdir / f"section_{si:02d}.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-ar", str(SR), "-ac", "1", "-af", WARM, str(wav)], check=True)
        durations.append(dur(wav))
        timeline += section_timeline(vdir, si, n, sum(durations[:-1]), durations[-1])
    full = work / "narration.wav"
    lst = vdir / "all.txt"
    lst.write_text("".join(f"file 'section_{i:02d}.wav'\n" for i in range(len(layout))))
    # Volum normalitzat a -18 LUFS (sense això queda a uns -24, massa fluix per a YouTube)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-af", "loudnorm=I=-18:TP=-2:LRA=11", "-ar", str(SR), str(full)], check=True)
    (work / "sections.json").write_text(json.dumps(durations))
    (work / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False))
    total = sum(durations)
    print(f"Veu: {len(layout)} seccions, {total/60:.1f} min")
    return durations


if __name__ == "__main__":
    ep = json.loads(Path(sys.argv[1]).read_text())
    asyncio.run(build(ep, Path(sys.argv[2])))
