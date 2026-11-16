"""Pas 6: muntatge. Desplaçament lateral lent alternat, fosa d'1,2 s,
efecte de profunditat 3D a la imatge de cada múltiple de 150 s. 1080p, 24 fps, H.264 + AAC."""
import json, subprocess, sys, time
from pathlib import Path

import cv2
import numpy as np

W, H, FPS = 1920, 1080, 24
FADE = 1.2
DEPTH_EVERY = 150.0
PAN_X = 2112 - W  # 192 px
PAN_Y = (1188 - H) / 2


def slots(durations):
    """60 franges: cada secció es reparteix a parts iguals entre les seves 6 imatges."""
    out, t = [], 0.0
    for si, d in enumerate(durations):
        for k in range(6):
            out.append((si * 6 + k, t + k * d / 6, d / 6))
        t += d
    return out


def depth_maps(work, idxs):
    from transformers import pipeline
    from PIL import Image
    est = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf")
    maps = {}
    for i in idxs:
        img = Image.open(work / "images" / f"img_{i:02d}.png")
        d = np.array(est(img.resize((1056, 594)))["depth"], dtype=np.float32)
        d = cv2.resize(d, (2112, 1188), interpolation=cv2.INTER_CUBIC)
        d = (d - d.min()) / max(1e-6, d.max() - d.min())  # 1 = a prop
        maps[i] = cv2.GaussianBlur(d, (0, 0), 6)
    return maps


class Renderer:
    def __init__(self, work, sl, depth_idx):
        self.work, self.sl = work, sl
        self.cache = {}
        self.depth = depth_maps(work, depth_idx) if depth_idx else {}
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xx, self.yy = xx, yy

    def img(self, i):
        if i not in self.cache:
            if len(self.cache) > 4:
                self.cache.pop(next(iter(self.cache)))
            self.cache[i] = cv2.imread(str(self.work / "images" / f"img_{i:02d}.png"))
        return self.cache[i]

    def frame_of(self, k, t):
        i, start, dur = self.sl[k]
        p = np.clip((t - start + FADE / 2) / (dur + FADE), 0, 1)
        p = p * p * (3 - 2 * p) * 0.15 + p * 0.85  # suavitzat lleuger als extrems
        src = self.img(i)
        x0 = PAN_X * (p if k % 2 == 0 else 1 - p)
        if i in self.depth:
            z = 1.0 + 0.06 * p
            par = 46.0 * (p - 0.5) * (1 if k % 2 == 0 else -1)
            cx, cy = W / 2, H / 2
            mx = cx + (self.xx - cx) / z + x0
            my = cy + (self.yy - cy) / z + PAN_Y
            mx, my = mx.astype(np.float32), my.astype(np.float32)
            dmap = cv2.remap(self.depth[i], mx, my, cv2.INTER_LINEAR)
            mx = (mx - par * dmap).astype(np.float32)
            my = (my - 0.25 * par * dmap).astype(np.float32)
            return cv2.remap(src, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        M = np.float32([[1, 0, -float(x0)], [0, 1, -PAN_Y]])
        return cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR)

    def frame(self, t):
        sl = self.sl
        k = max(0, min(len(sl) - 1, next((j for j, s in enumerate(sl) if s[1] + s[2] > t), len(sl) - 1)))
        _, start, dur = sl[k]
        end = start + dur
        if k + 1 < len(sl) and t > end - FADE / 2:
            a = (t - (end - FADE / 2)) / FADE
            return cv2.addWeighted(self.frame_of(k, t), 1 - a, self.frame_of(k + 1, t), a, 0)
        if k > 0 and t < start + FADE / 2:
            a = (t - (start - FADE / 2)) / FADE
            return cv2.addWeighted(self.frame_of(k - 1, t), 1 - a, self.frame_of(k, t), a, 0)
        return self.frame_of(k, t)


def build(work):
    durations = json.loads((work / "sections.json").read_text())
    total = sum(durations)
    sl = slots(durations)
    depth_idx = sorted({i for i, s, d in sl for m in np.arange(DEPTH_EVERY, total, DEPTH_EVERY) if s <= m < s + d})
    print(f"Muntatge: {total/60:.1f} min, efecte 3D a {len(depth_idx)} imatges")
    r = Renderer(work, sl, depth_idx)
    video = work / "video_noaudio.mp4"
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-tune", "film",
                            "-pix_fmt", "yuv420p", "-g", "96", str(video)], stdin=subprocess.PIPE)
    n = int(round(total * FPS))
    t0 = time.time()
    for f in range(n):
        enc.stdin.write(r.frame(f / FPS).tobytes())
        if f % (FPS * 300) == 0 and f:
            print(f"  {f/FPS/60:.0f} min fets ({time.time()-t0:.0f}s)")
    enc.stdin.close(); enc.wait()
    out = work / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-i", str(work / "narration.wav"),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
                    str(out)], check=True)
    video.unlink()
    # Control: fotogrames de mostra
    for m in (0.1, 0.5, 0.9):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(total * m), "-i", str(out),
                        "-frames:v", "1", "-vf", "scale=640:-1", str(work / f"sample_{int(m*100)}.jpg")])
    print(f"Vídeo: {out} ({out.stat().st_size/1e6:.0f} MB)")


if __name__ == "__main__":
    build(Path(sys.argv[1]))
