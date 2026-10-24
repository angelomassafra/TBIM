"""Compose the TBIM workflow videos (MP4 and GIF) from the frames captured in Revit.

    python tools/video/video.py tools/video/six_buildings.json
    python tools/video/video.py tools/video/residential_1960s.json

A configuration lists the buildings (folders of frames written by capture_frames.cs, each with its
phases.txt), the captions of the phases and the output. One building gives a full-screen video, several
buildings a grid whose phases are synchronised. Frames are looked for in ``frames_root`` of the
configuration, else in the TBIM_FRAMES environment variable, else in %TEMP%/tbim_frames.

Requires Pillow and imageio-ffmpeg (``pip install pillow imageio-ffmpeg``).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))
W, H, FPS = 1920, 1080, 24
FONTS = {"regular": "C:/Windows/Fonts/segoeui.ttf", "bold": "C:/Windows/Fonts/segoeuib.ttf"}
ACCENT = (31, 163, 163)
PHASES = ["faces", "controllers", "cells", "types", "apertures", "graph", "data", "orbit"]
REPEAT = {"orbit": 2}  # output frames per captured frame (default 4: 6 frames per second for the build-up)
CAPTION_BAND = 150


def font(weight, size):
    try:
        return ImageFont.truetype(FONTS[weight], size)
    except OSError:
        return ImageFont.load_default()


def frames_root(config):
    return config.get("frames_root") or os.environ.get("TBIM_FRAMES") or os.path.join(tempfile.gettempdir(),
                                                                                      "tbim_frames")


def phases_of(folder):
    """{phase: [frame paths]} of a capture folder (frames sorted by name, spans in phases.txt)."""
    files = sorted(f for f in os.listdir(folder) if f.startswith("f") and f.endswith(".png"))
    phases = {}
    for line in open(os.path.join(folder, "phases.txt")):
        name, span = line.split()
        a, b = (int(x) for x in span.split("-"))
        phases[name] = [os.path.join(folder, files[i]) for i in range(a, b + 1)]
    return phases


def card(title, subtitle, note):
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    d.rectangle([0, H - 14, W, H], fill=ACCENT)
    d.text((W // 2, H // 2 - 90), title, font=font("bold", 96), fill=(30, 30, 30), anchor="mm")
    d.text((W // 2, H // 2 + 20), subtitle, font=font("regular", 44), fill=(70, 70, 70), anchor="mm")
    d.text((W // 2, H // 2 + 110), note, font=font("regular", 30), fill=(120, 120, 120), anchor="mm")
    return im


def caption(im, title, text, header=None):
    d = ImageDraw.Draw(im)
    d.rectangle([0, H - CAPTION_BAND, W, H], fill=(255, 255, 255))
    d.rectangle([0, H - CAPTION_BAND, 12, H], fill=ACCENT)
    d.text((48, H - 128), title, font=font("bold", 46), fill=ACCENT)
    d.text((48, H - 66), text, font=font("regular", 34), fill=(50, 50, 50))
    if header:
        d.text((48, 22), "TBIM for pyRevit", font=font("bold", 34), fill=(40, 40, 40))
        d.text((W - 40, 30), header, font=font("regular", 26), fill=(150, 150, 150), anchor="ra")
    else:
        d.text((W - 40, 36), "TBIM for pyRevit", font=font("regular", 28), fill=(150, 150, 150), anchor="ra")
    return im


def single(path, title, text):
    frame = Image.open(path).convert("RGB")
    im = Image.new("RGB", (W, H), "white")
    scale = min(W / float(frame.width), (H - CAPTION_BAND - 10) / float(frame.height))
    fw, fh = int(frame.width * scale), int(frame.height * scale)
    im.paste(frame.resize((fw, fh), Image.LANCZOS), ((W - fw) // 2, 10))
    return caption(im, title, text)


def grid(paths, labels, title, text, header, cols=3):
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    rows = (len(paths) + cols - 1) // cols
    label_h, top, gap_y = 34, 74, 12
    panel_h = (H - CAPTION_BAND - top - rows * (label_h + gap_y)) // rows
    panel_w = min(panel_h * 16 // 9, (W - (cols + 1) * 24) // cols)
    panel_h = panel_w * 9 // 16
    gap_x = (W - cols * panel_w) // (cols + 1)
    for k, (path, label) in enumerate(zip(paths, labels)):
        x = gap_x + (k % cols) * (panel_w + gap_x)
        y = top + (k // cols) * (panel_h + label_h + gap_y)
        d.text((x + 4, y + 2), label, font=font("bold", 24), fill=ACCENT)
        im.paste(Image.open(path).convert("RGB").resize((panel_w, panel_h), Image.LANCZOS), (x, y + label_h))
        d.rectangle([x, y + label_h, x + panel_w - 1, y + label_h + panel_h - 1], outline=(225, 225, 225))
    return caption(im, title, text, header)


def compose(config):
    root = frames_root(config)
    buildings = config["buildings"]
    sets = [phases_of(os.path.join(root, b["frames"])) for b in buildings]
    work = tempfile.mkdtemp(prefix="tbim_video_")
    count = [0]

    def frame(i):
        return os.path.join(work, "o%05d.png" % i)

    def emit(im, times):
        im.save(frame(count[0]))
        for _ in range(times - 1):
            shutil.copyfile(frame(count[0]), frame(count[0] + 1))
            count[0] += 1
        count[0] += 1

    emit(card(*config["opening"]), FPS * 3)
    for phase in PHASES:
        title, text = config["captions"][phase]
        length = max(len(s[phase]) for s in sets)
        for i in range(length):
            paths = [s[phase][min(len(s[phase]) - 1, i * len(s[phase]) // length)] for s in sets]
            if len(paths) == 1:
                im = single(paths[0], title, text)
            else:
                im = grid(paths, [b["label"] for b in buildings], title, text, config.get("header", ""),
                          config.get("columns", 3))
            emit(im, REPEAT.get(phase, 4))
    emit(card(*config["closing"]), FPS * 3)

    out = os.path.join(ROOT, config["output"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(work, "o%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(config.get("crf", 22)),
                    "-movflags", "+faststart", out + ".mp4"], check=True)
    gif = config.get("gif", {"fps": 6, "width": 960})
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", out + ".mp4", "-vf",
                    "fps=%d,scale=%d:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];"
                    "[b][p]paletteuse=dither=bayer" % (gif["fps"], gif["width"]), out + ".gif"], check=True)
    shutil.rmtree(work, ignore_errors=True)
    print("%d frames (%.1f s) -> %s.mp4 (%.1f MB), .gif (%.1f MB)" % (
        count[0], count[0] / float(FPS), out, os.path.getsize(out + ".mp4") / 1e6, os.path.getsize(out + ".gif") / 1e6))


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        compose(json.load(f))
