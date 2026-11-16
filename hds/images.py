"""Pas 5: 60 imatges (6 per secció) amb SD-Turbo en local, estil pintura a l'oli."""
import json, re, sys, time
from pathlib import Path

import torch
from PIL import Image, ImageDraw, ImageFont

STYLE = ("oil painting, painterly, rich brushstrokes, warm golden candlelight, "
         "historical scene, cinematic composition, ")
NEG_FIX = [  # regles del document
    (r"\bParis\b", "a crowded medieval city"),
    (r"\bparisian\b", "medieval townsfolk"),
]
GEN_W, GEN_H = 768, 432
OUT_W, OUT_H = 2112, 1188
_pipe = None


def pipe():
    global _pipe
    if _pipe is None:
        from diffusers import AutoPipelineForText2Image
        torch.set_num_threads(max(1, torch.get_num_threads()))
        _pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sd-turbo", torch_dtype=torch.float32)
        _pipe.set_progress_bar_config(disable=True)
    return _pipe


def fix_prompt(p):
    for pat, rep in NEG_FIX:
        p = re.sub(pat, rep, p, flags=re.I)
    # «winter» en interiors hi posa neu
    if re.search(r"\b(interior|inside|room|hall|kitchen|bedroom|chamber)\b", p, re.I):
        p = re.sub(r"\bwinter\b", "cold season, fireplace, earthen floor", p, flags=re.I)
    return STYLE + p


def prompts(ep):
    out = []
    for sec in ep["sections"]:
        assert len(sec["images"]) == 6, f"Cal 6 imatges a «{sec['title']}»"
        out += sec["images"]
    return out


def render(ep, work, only=None, seed_offset=0):
    idir = work / "images"; idir.mkdir(parents=True, exist_ok=True)
    ps = prompts(ep)
    for i, p in enumerate(ps):
        f = idir / f"img_{i:02d}.png"
        if only is None and f.exists():
            continue
        if only is not None and i not in only:
            continue
        t = time.time()
        g = torch.Generator().manual_seed(1000 + i + seed_offset)
        img = pipe()(prompt=fix_prompt(p), num_inference_steps=1, guidance_scale=0.0,
                     width=GEN_W, height=GEN_H, generator=g).images[0]
        img.resize((OUT_W, OUT_H), Image.LANCZOS).save(f)
        print(f"  imatge {i+1}/{len(ps)} ({time.time()-t:.0f}s)")
    contact_sheet(idir, len(ps))


def contact_sheet(idir, n):
    """Làmina per revisar totes les imatges d'un cop."""
    tw, th, cols = 320, 180, 6
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), "black")
    d = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    for i in range(n):
        f = idir / f"img_{i:02d}.png"
        if not f.exists():
            continue
        im = Image.open(f).resize((tw, th))
        x, y = (i % cols) * tw, (i // cols) * th
        sheet.paste(im, (x, y))
        d.text((x + 6, y + 4), str(i), fill="yellow", font=font, stroke_width=2, stroke_fill="black")
    sheet.save(idir.parent / "contact_sheet.jpg", quality=85)


if __name__ == "__main__":
    ep = json.loads(Path(sys.argv[1]).read_text())
    only = {int(x) for x in sys.argv[3].split(",")} if len(sys.argv) > 3 else None
    render(ep, Path(sys.argv[2]), only, seed_offset=int(time.time()) % 1000 if only else 0)
