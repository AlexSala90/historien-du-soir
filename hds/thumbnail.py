"""Pas 7: miniatura 1280×720 JPG, pensada per al CTR (objectiu ≥ 4 %).

Regles (CLAUDE.md):
- Una cara en primer pla il·luminada per una espelma (càlid) contra un fons fred (blau de nit/neu).
- Text de 2–3 paraules, molt gran, que COMPLETA el títol (no el repeteix).
- Marca fixa: una espelma petita a baix a l'esquerra. Etiqueta opcional («PARTIE 2»).
- Cantonada de baix a la dreta buida (hi va la durada del vídeo).

Es generen diverses cares candidates i es tria automàticament la més neta
(una sola cara detectada, ulls visibles, nítida). També surten dues variants
(thumbnail_b: 2a cara, mateix text; thumbnail_c: mateixa cara, text alternatiu)
per si es vol fer «Tester et comparer» a mà a YouTube Studio.
"""
import json, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = Path(__file__).resolve().parent.parent / "fonts" / "Cinzel.ttf"
CREAM, GOLD, INK = (246, 236, 212), (236, 184, 72), (12, 10, 14)
W, H = 1280, 720
N_FACES = 8

FACE_STYLE = ("oil painting, painterly, close-up portrait, whole head and shoulders visible, "
              "space above the head, face lit only by a single candle flame, warm orange candlelight "
              "on the skin, deep dark background, soft gaze towards the viewer, calm gentle expression, "
              "detailed eyes, sharp focus, ")
BG_STYLE = ("oil painting, painterly, night scene, cold blue moonlight, deep blue and teal tones, "
            "snow, mist, no people, ")


# ---------------------------------------------------------------- dades
def spec(ep):
    """Llegeix el bloc «thumbnail» (format nou; tolera el format antic)."""
    th = ep["thumbnail"]
    text = th.get("text") or th.get("gold") or " ".join(th.get("lines", []))
    face = th.get("face") or th.get("prompt", "a tired medieval peasant")
    bg = th.get("background") or th.get("prompt", "medieval village")
    return {"text": text.upper(), "alt_text": (th.get("alt_text") or "").upper(),
            "face": face, "background": bg, "label": (th.get("label") or "").upper()}


# ---------------------------------------------------------------- tipografia
def font(size, weight=900):
    f = ImageFont.truetype(str(FONT), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:  # noqa: BLE001
        pass
    return f


def split_lines(text):
    """2–3 paraules: 1 línia si és curt, si no 2 línies equilibrades."""
    if "\n" in text:
        return [t.strip() for t in text.split("\n") if t.strip()]
    words = text.split()
    if len(text) <= 9 or len(words) == 1:
        return [text]
    best = min(range(1, len(words)),
               key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
    return [" ".join(words[:best]), " ".join(words[best:])]


def fit(draw, lines, maxw, maxh, size=210):
    while size > 60:
        f = font(size)
        ws = [draw.textlength(t, font=f) for t in lines]
        lh = f.getbbox("ÀGQ")[3]
        if max(ws) <= maxw and lh * len(lines) + 10 * (len(lines) - 1) <= maxh:
            return f
        size -= 6
    return font(size)


# ---------------------------------------------------------------- color
def grade(img, shadows, highlights, amount):
    """Tonalitat dividida: ombres cap a un color, llums cap a un altre."""
    a = np.asarray(img).astype(np.float32) / 255
    lum = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])[..., None]
    tint = (1 - lum) * np.array(shadows) / 255 + lum * np.array(highlights) / 255
    out = a * (1 - amount) + (lum * 0.35 + tint * 0.65) * amount
    return Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8))


def warm_face(img):
    img = grade(img, (40, 14, 6), (255, 196, 120), 0.45)
    a = np.asarray(img).astype(np.float32)
    a = (a - 128) * 1.12 + 132  # una mica més de contrast
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def cold_bg(img):
    img = grade(img, (4, 16, 48), (90, 150, 235), 0.9)
    a = np.asarray(img).astype(np.float32) * 0.7  # fosc perquè el text es llegeixi
    a[..., 2] = np.clip(a[..., 2] * 1.15 + 10, 0, 255)  # blau de nit
    return Image.fromarray(a.astype(np.uint8))


# ---------------------------------------------------------------- marca
def candle_mark(img, x=38, y=30, s=1.0):
    """Espelma petita (marca del canal) amb halo càlid."""
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    cx, fy = x + int(14 * s), y + int(18 * s)
    g.ellipse([cx - 34 * s, fy - 34 * s, cx + 34 * s, fy + 34 * s], fill=(255, 170, 60, 110))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(14 * s)))
    d = ImageDraw.Draw(img)
    d.ellipse([cx - 7 * s, fy - 16 * s, cx + 7 * s, fy + 10 * s], fill=(255, 200, 90, 255))
    d.ellipse([cx - 3.5 * s, fy - 6 * s, cx + 3.5 * s, fy + 8 * s], fill=(255, 245, 210, 255))
    d.line([cx, fy + 8 * s, cx, fy + 14 * s], fill=(40, 30, 20, 255), width=max(1, int(2 * s)))
    d.rounded_rectangle([cx - 10 * s, fy + 14 * s, cx + 10 * s, fy + 62 * s], radius=3 * s,
                        fill=(244, 232, 205, 255))
    d.rectangle([cx - 10 * s, fy + 14 * s, cx - 4 * s, fy + 62 * s], fill=(214, 198, 168, 255))


def label_badge(img, text):
    d = ImageDraw.Draw(img)
    f = font(40, 800)
    w = d.textlength(text, font=f)
    x1, y0 = W - 36, 30
    d.rounded_rectangle([x1 - w - 36, y0, x1, y0 + 62], radius=10, fill=(*GOLD, 255))
    d.text((x1 - w - 18, y0 + 9), text, font=f, fill=INK)


# ---------------------------------------------------------------- composició
def compose(face, bg, text, label=""):
    """face: imatge quadrada (cara càlida). bg: escena (es torna freda)."""
    canvas = cold_bg(bg.convert("RGB").resize((W, H), Image.LANCZOS)).convert("RGBA")
    fs = 740
    fimg = warm_face(face.convert("RGB").resize((fs, fs), Image.LANCZOS)).convert("RGBA")
    # màscara: fosa cap a la dreta i cap avall, perquè la cara surti del fons fred
    xs = np.linspace(0, 1, fs)[None, :]
    ys = np.linspace(0, 1, fs)[:, None]
    m = np.clip((0.95 - xs) / 0.32, 0, 1) * np.clip((1.02 - ys) / 0.25, 0, 1)
    fimg.putalpha(Image.fromarray((m * 255).astype(np.uint8)))
    canvas.alpha_composite(fimg, (-30, -10))

    d = ImageDraw.Draw(canvas)
    lines = split_lines(text)
    # zona del text: meitat dreta, part alta; la cantonada de baix a la dreta queda lliure
    zx0, zx1, zy0, zy1 = 640, 1244, 110, 520
    f = fit(d, lines, zx1 - zx0, zy1 - zy0)
    lh = f.getbbox("ÀGQ")[3]
    total = lh * len(lines) + 10 * (len(lines) - 1)
    y = zy0 + (zy1 - zy0 - total) // 2
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    pos = []
    for i, t in enumerate(lines):
        w = d.textlength(t, font=f)
        x = (zx0 + zx1 - w) / 2
        pos.append((x, y, t, GOLD if i == len(lines) - 1 and len(lines) > 1 else CREAM))
        sd.text((x + 6, y + 8), t, font=f, fill=(0, 0, 0, 230))
        y += lh + 10
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(9)))
    d = ImageDraw.Draw(canvas)
    sw = max(4, f.size // 22)
    for x, y, t, col in pos:
        d.text((x, y), t, font=f, fill=col, stroke_width=sw, stroke_fill=INK)

    candle_mark(canvas, x=40, y=H - 130, s=1.25)  # baix a l'esquerra: lliure a YouTube
    if label:
        label_badge(canvas, label)
    return canvas.convert("RGB")


# ---------------------------------------------------------------- generació i tria
YUNET = Path(__file__).resolve().parent.parent / "models" / "face_detection_yunet_2023mar.onnx"


def score_face(img):
    """Puntua una cara candidata amb YuNet (OpenCV): una sola cara clara, gran i centrada,
    ulls i nas ben posats (sense deformacions), nítida. Retorna -1 si no serveix."""
    import cv2
    a = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    h0, w0 = a.shape[:2]
    det = cv2.FaceDetectorYN.create(str(YUNET), "", (w0, h0), 0.6, 0.3, 5000)
    _, faces = det.detect(a)
    faces = [] if faces is None else [f for f in faces if f[14] >= 0.6]
    if len(faces) != 1:
        return -1.0
    f = faces[0]
    x, y, w, h = f[:4]
    (rx, ry), (lx, ly), (nx, ny), (mrx, mry), (mlx, mly) = f[4:14].reshape(5, 2)
    eye_d = np.hypot(lx - rx, ly - ry)
    if eye_d < 0.2 * w:  # ulls massa junts: cara de perfil o deformada
        return -1.0
    tilt = abs(ly - ry) / eye_d                     # ulls a la mateixa alçada
    nose_off = abs(nx - (lx + rx) / 2) / eye_d      # nas entre els ulls
    order_ok = ry < ny < (mry + mly) / 2            # ulls > nas > boca
    g = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
    x0, y0 = max(0, int(x)), max(0, int(y))
    sharp = cv2.Laplacian(g[y0:y0 + int(h), x0:x0 + int(w)], cv2.CV_64F).var()
    size = w / w0
    centre = 1 - abs((x + w / 2) / w0 - 0.5) * 2
    s = float(f[14]) * 2 + min(size, 0.6) * 2 + centre * 0.5 + min(sharp, 400) / 400
    s -= tilt * 2 + max(0, nose_off - 0.15) * 3 + (0 if order_ok else 2)
    return float(s)


def candidates(sp, n=N_FACES):
    from .images import pipe
    import torch
    out = []
    for i in range(n):
        img = pipe()(prompt=FACE_STYLE + sp["face"], num_inference_steps=1, guidance_scale=0.0,
                     width=512, height=512, generator=torch.Generator().manual_seed(100 + i)).images[0]
        out.append((score_face(img), i, img))
        print(f"  cara {i+1}/{n}: puntuació {out[-1][0]:.2f}")
    out.sort(key=lambda t: -t[0])
    return out


def background(sp):
    from .images import pipe
    import torch
    return pipe()(prompt=BG_STYLE + sp["background"], num_inference_steps=1, guidance_scale=0.0,
                  width=768, height=432, generator=torch.Generator().manual_seed(7)).images[0]


def faces_sheet(cands, path):
    tw = 256
    sheet = Image.new("RGB", (tw * len(cands), tw + 40), "black")
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    for k, (s, i, img) in enumerate(cands):
        sheet.paste(img.resize((tw, tw)), (k * tw, 40))
        d.text((k * tw + 8, 8), f"#{i} {s:.2f}" + (" ✓" if k == 0 else ""), fill="yellow", font=f)
    sheet.save(path, quality=85)


def make(ep, work):
    sp = spec(ep)
    cands = candidates(sp)
    faces_sheet(cands, work / "thumbnail_faces.jpg")
    if cands[0][0] < 0:
        print("  Avís: cap cara neta detectada; faig servir la millor que hi ha")
    bg = background(sp)
    compose(cands[0][2], bg, sp["text"], sp["label"]).save(work / "thumbnail.jpg", quality=92)
    compose(cands[1][2], bg, sp["text"], sp["label"]).save(work / "thumbnail_b.jpg", quality=92)
    if sp["alt_text"]:
        compose(cands[0][2], bg, sp["alt_text"], sp["label"]).save(work / "thumbnail_c.jpg", quality=92)
    print(f"Miniatura: {work/'thumbnail.jpg'} (cara #{cands[0][1]}, text «{sp['text']}»)")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from hds.thumbnail import make as _m
    _m(json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]))
