"""Add the "charts" phase to the video frames of a building: the heating and cooling need of its three TBEM levels.

    python tools/video/charts_frame.py <frames folder> <project folder>

The frame is drawn from the results of the TBEM tab (bem/tbem_<level>_Results.json) with fonts large enough for
the panels of the grid video, appended to the frames written by capture_frames.cs and to their phases.txt.
"""
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from video import font  # noqa: E402

W, H = 1280, 720
LEVELS = [("SpatialBEM", "Spatial BEM", (52, 140, 210)), ("TopologicalBEM", "Topological BEM", (120, 84, 190)),
          ("FullTBEM", "Full TBEM", (214, 120, 40))]
KEYS = [("heating_per_m2", "Heating"), ("cooling_per_m2", "Cooling")]


def draw(results):
    """Grouped bars (kWh/m2 y) of ``results`` {level: results JSON}."""
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    d.text((W // 2, 44), "Energy need (kWh/m² y) - EnergyPlus, Bologna", font=font("bold", 44),
           fill=(40, 40, 40), anchor="mm")
    levels = [lv for lv in LEVELS if lv[0] in results]
    top = max([results[lv]["building"][k] for lv, _, _ in levels for k, _ in KEYS] or [1]) * 1.15 or 1
    x0, x1, y0, y1 = 90, W - 40, 150, H - 90
    d.line([(x0, y1), (x1, y1)], fill=(60, 60, 60), width=3)
    group = (x1 - x0) / float(len(KEYS))
    bar = group * 0.8 / max(len(levels), 1)
    for g, (key, label) in enumerate(KEYS):
        gx = x0 + g * group + group * 0.1
        for i, (lv, _, rgb) in enumerate(levels):
            value = results[lv]["building"][key]
            bx, by = gx + i * bar, y1 - (y1 - y0) * value / top
            d.rectangle([bx + 6, by, bx + bar - 6, y1], fill=rgb)
            d.text((bx + bar / 2, by - 8), "%.0f" % value, font=font("bold", 40), fill=(40, 40, 40), anchor="mb")
        d.text((x0 + g * group + group / 2, y1 + 14), label, font=font("bold", 42), fill=(40, 40, 40), anchor="mt")
    x = x0
    for _, label, rgb in levels:
        d.rectangle([x, 92, x + 30, 122], fill=rgb)
        d.text((x + 40, 107), label, font=font("regular", 32), fill=(60, 60, 60), anchor="lm")
        x += 70 + int(d.textlength(label, font=font("regular", 32)))
    return im


def main(frames, project):
    results = {}
    for level, _, _ in LEVELS:
        path = os.path.join(project, "bem", "tbem_%s_Results.json" % level)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                results[level] = json.load(f)
    if not results:
        raise SystemExit("No TBEM results in %s" % project)
    phases = os.path.join(frames, "phases.txt")
    lines = [line for line in open(phases).read().splitlines() if line and not line.startswith("charts ")]
    index = len([f for f in os.listdir(frames) if f.startswith("f") and f.endswith(".png") and "Charts" not in f])
    for name in os.listdir(frames):
        if name.startswith("f") and "Charts" in name:
            os.remove(os.path.join(frames, name))
    draw(results).save(os.path.join(frames, "f%04d - Charts.png" % index))
    with open(phases, "w") as f:
        f.write("\n".join(lines + ["charts %d-%d" % (index, index)]) + "\n")
    print("%s: charts frame %d (%s)" % (os.path.basename(frames), index, ", ".join(results)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
