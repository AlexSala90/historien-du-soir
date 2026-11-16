"""Pas 7: miniatura 1280×720 JPG. Personatge a l'esquerra, fons fosc a la dreta,
text en majúscules amb serifa: línies en crema + una línia final en daurat."""
import json, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = Path(__file__).resolve().parent.parent / "fonts" / "Cinzel.ttf"
CREAM, GOLD = (243, 230, 200), (226, 178, 74)


def font(size, weight=800):
    f = ImageFont.truetype(str(FONT), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:  # noqa: BLE001
        pass
    return f


def fit(draw, text, maxw, size, weight=800):
    while size > 30:
        f = font(size, weight)
        if draw.textlength(text, font=f) <= maxw:
            return f
        size -= 4
    return font(size, weight)


def make(ep, work):
    from .images import pipe, fix_prompt
    import torch
    th = ep["thumbnail"]
    p = fix_prompt(th["prompt"] + ", single figure on the left side, dark empty background on the right side")
    img = pipe()(prompt=p, num_inference_steps=1, guidance_scale=0.0, width=768, height=432,
                 generator=torch.Generator().manual_seed(7)).images[0].resize((1280, 720), Image.LANCZOS)
    # Enfosquir la meitat dreta per al text
    grad = np.clip((np.linspace(0, 1, 1280) - 0.35) / 0.4, 0, 1) * 0.78
    arr = np.array(img).astype(np.float32) * (1 - grad[None, :, None])
    img = Image.fromarray(arr.astype(np.uint8))
    d = ImageDraw.Draw(img)
    x0, right, maxw = 560, 1240, 680
    lines = [(t, CREAM, 112) for t in th["lines"]] + [(th["gold"], GOLD, 64)]
    fonts = [fit(d, t.upper(), maxw, s) for t, _, s in lines]
    heights = [f.getbbox("ÀG")[3] for f in fonts]
    total = sum(heights) + 18 * (len(lines) - 1)
    y = (720 - total) // 2
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for (t, col, _), f, h in zip(lines, fonts, heights):
        w = d.textlength(t.upper(), font=f)
        x = right - w
        sd.text((x + 4, y + 5), t.upper(), font=f, fill=(0, 0, 0, 220))
        y += h + 18
    img = Image.alpha_composite(img.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(5)))
    d = ImageDraw.Draw(img)
    y = (720 - total) // 2
    for (t, col, _), f, h in zip(lines, fonts, heights):
        w = d.textlength(t.upper(), font=f)
        d.text((right - w, y), t.upper(), font=f, fill=col)
        y += h + 18
    out = work / "thumbnail.jpg"
    img.convert("RGB").save(out, quality=92)
    print(f"Miniatura: {out}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from hds.thumbnail import make as _m
    _m(json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]))
