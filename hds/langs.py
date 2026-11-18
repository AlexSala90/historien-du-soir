"""Pas 9: castellà i anglès. Títol i descripció traduïts (localitzacions de YouTube) i
subtítols fr/es/en amb els temps reals de la veu (timeline.json del pas de veu).

Si episode.json porta `localizations` (escrites per Claude), s'usen per al títol, la introducció
de la descripció i els títols dels capítols. El que falti, i tots els subtítols, es tradueix aquí
amb models lliures i locals (Helsinki-NLP opus-mt): fr→en, i fr→en→es, que en castellà
dona millor resultat que el model directe fr→es."""
import json, math, re, sys
from pathlib import Path

LANGS = {
    "es": {"suffix": "| Historia para dormir", "chapters": "📖 Capítulos", "name": "Español",
           "cta": ("Si este viaje te ha ayudado a encontrar el descanso, suscríbete para reencontrarnos "
                   "otras noches, en otros siglos. Que duermas bien. 🌙"),
           "hashtags": "#historiaparadormir #edadmedia #historia"},
    "en": {"suffix": "| History for Sleep", "chapters": "📖 Chapters", "name": "English",
           "cta": ("If this journey helped you find rest, subscribe to join us on other nights, "
                   "in other centuries. Sleep well. 🌙"),
           "hashtags": "#historyforsleep #middleages #sleepstory"},
}
MODELS = {"en": "Helsinki-NLP/opus-mt-fr-en", "es": "Helsinki-NLP/opus-mt-en-es"}  # es: via anglès
CUE_MAX, LINE_MAX = 84, 42
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿⌀-⏿]️?")


class Translator:
    def __init__(self):
        self.models, self.cache = {}, {}

    def _model(self, key):
        if key not in self.models:
            from transformers import MarianMTModel, MarianTokenizer
            name = MODELS[key]
            self.models[key] = (MarianTokenizer.from_pretrained(name), MarianMTModel.from_pretrained(name).eval())
        return self.models[key]

    def _run(self, key, texts, batch=16):
        import torch
        tok, model = self._model(key)
        out = [""] * len(texts)
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        for b in range(0, len(order), batch):
            idx = [i for i in order[b:b + batch] if texts[i].strip()]
            if not idx:
                continue
            enc = tok([texts[i] for i in idx], return_tensors="pt", padding=True, truncation=True, max_length=400)
            with torch.no_grad():
                gen = model.generate(**enc, num_beams=4, max_length=512)
            for i, t in zip(idx, tok.batch_decode(gen, skip_special_tokens=True)):
                out[i] = t.strip()
        return out

    def __call__(self, texts, lang):
        """Tradueix una llista de frases franceses a `lang` ('en' o 'es')."""
        texts = list(texts)
        todo = [t for t in dict.fromkeys(texts) if (t, lang) not in self.cache]
        if todo:
            en = [self.cache.get((t, "en")) for t in todo]
            miss = [t for t, e in zip(todo, en) if e is None]
            for t, e in zip(miss, self._run("en", miss)):
                self.cache[(t, "en")] = e
            if lang == "es":
                src = [self.cache[(t, "en")] for t in todo]
                for t, e in zip(todo, self._run("es", src)):
                    self.cache[(t, "es")] = e
        return [self.cache[(t, lang)] for t in texts]


# ---------- subtítols ----------

def srt_time(s):
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def split_words(text, n):
    """Parteix un text en n trossos de llargada semblant, sense tallar paraules."""
    words = text.split()
    if n <= 1 or len(words) <= 1:
        return [text]
    target, parts, cur = len(text) / n, [], []
    for w in words:
        if cur and len(" ".join(cur + [w])) > target * 1.15 and len(parts) < n - 1:
            parts.append(" ".join(cur)); cur = []
        cur.append(w)
    parts.append(" ".join(cur))
    return parts


def two_lines(text):
    if len(text) <= LINE_MAX:
        return text
    a, b = split_words(text, 2) if len(text.split()) > 1 else (text, "")
    return f"{a}\n{b}".strip()


def to_srt(timeline, texts):
    """Un bloc per frase; les frases llargues es parteixen en blocs de ≤ 84 caràcters (2 línies),
    amb el temps repartit segons els caràcters."""
    out, k = [], 1
    for seg, text in zip(timeline, texts):
        text = re.sub(r"\s+", " ", text or "").strip()
        if not text:
            continue
        pieces = split_words(text, math.ceil(len(text) / CUE_MAX))
        total = sum(len(p) for p in pieces) or 1
        t, span = seg["start"], max(0.5, seg["end"] - seg["start"])
        for p in pieces:
            d = span * len(p) / total
            out.append(f"{k}\n{srt_time(t)} --> {srt_time(t + d)}\n{two_lines(p)}\n")
            k += 1; t += d
    return "\n".join(out)


# ---------- títol i descripció ----------

def ts(sec):
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def clean(text):
    return text.replace("<", "‹").replace(">", "›")  # YouTube rebutja < i > al títol i la descripció


def localize(ep, durations, lang, tr):
    given = (ep.get("localizations") or {}).get(lang, {})
    conf = LANGS[lang]
    fr_title = ep["title"]
    emoji = (EMOJI.findall(fr_title) or [""])[0]
    if given.get("title"):
        title = given["title"]
    else:
        hook = EMOJI.sub("", fr_title.split("|")[0]).strip().rstrip(".")
        title = f"{tr([hook], lang)[0].rstrip('.')} {conf['suffix']} {emoji}".strip()
    if len(title) > 100:  # màxim de YouTube: es retalla el ganxo, mai el sufix
        tail = f" {conf['suffix']} {emoji}".rstrip()
        title = title.split("|")[0][: 100 - len(tail) - 1].rstrip() + "…" + tail
    intro = given.get("description_intro") or " ".join(tr(sentences_of(ep["description_intro"]), lang))
    heads = given.get("section_titles") or tr([s["title"] for s in ep["sections"]], lang)
    t, chapters = 0.0, []
    for h, d in zip(heads, durations):
        chapters.append(f"{ts(t)} {h}")
        t += d
    desc = "\n".join([intro.strip(), "", conf["chapters"], *chapters, "", conf["cta"], "", conf["hashtags"]])
    return {"title": clean(title), "description": clean(desc)[:5000]}


def sentences_of(text):
    return [s for s in re.split(r"(?<=[.!?…])\s+", text.strip()) if s]


def make(ep, work, tr=None):
    tr = tr or Translator()
    durations = json.loads((work / "sections.json").read_text())
    tl_path = work / "timeline.json"
    loc = {lang: localize(ep, durations, lang, tr) for lang in LANGS}
    (work / "localizations.json").write_text(json.dumps(loc, ensure_ascii=False, indent=2))
    for lang, l in loc.items():
        print(f"Títol {lang}: {l['title']}")
    if not tl_path.exists():
        print("Avís: no hi ha timeline.json (veu antiga); sense subtítols")
        return loc
    timeline = json.loads(tl_path.read_text())
    fr = [s["text"] for s in timeline]
    (work / "subs_fr.srt").write_text(to_srt(timeline, fr))
    for lang in LANGS:
        (work / f"subs_{lang}.srt").write_text(to_srt(timeline, tr(fr, lang)))
    print(f"Subtítols fr/es/en: {len(timeline)} frases")
    return loc


if __name__ == "__main__":
    make(json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]))
