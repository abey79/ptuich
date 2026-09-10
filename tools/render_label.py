#!/usr/bin/env python3
"""Compose a 29mm x 9mm label: icon left, text right, 1-bit output.

This is the render(spec) -> PIL.Image function to drop into the label tool.
Icon names resolve local-first (icons/NAME.svg), then fall back to the
Iconify API (prefix:name, e.g. "mdi:screw-lag"), caching the fetch locally.
"""
import io
import os
import re
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

DPI = 360
ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "src" / "ptuich" / "icons"
FONT = next((p for p in [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
] if os.path.exists(p)), None)


def mm(v):
    return int(round(v / 25.4 * DPI))


def load_icon(name, px):
    """local icons/ first, Iconify second (cached back into icons/)."""
    local = str(ICON_DIR / (name.replace(":", "_") + ".svg"))
    if not os.path.exists(local):
        if ":" not in name:
            raise FileNotFoundError(name)
        import urllib.request
        prefix, icon = name.split(":", 1)
        url = f"https://api.iconify.design/{prefix}/{icon}.svg?color=black"
        with urllib.request.urlopen(url, timeout=10) as r:
            svg = r.read()
        if b"<svg" not in svg:
            raise LookupError(name)
        ICON_DIR.mkdir(parents=True, exist_ok=True)
        open(local, "wb").write(svg)
    png = cairosvg.svg2png(url=local, output_width=px, output_height=px,
                           background_color="white")
    return Image.open(io.BytesIO(png)).convert("L")


def render(text, length_mm=29.0, tape_mm=9.0, printable_mm=6.8,
           icon=None, gap_mm=1.0, pad_mm=1.0, threshold=128):
    W, H = mm(length_mm), mm(printable_mm)
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)

    x = mm(pad_mm)
    if icon:
        s = H
        img.paste(load_icon(icon, s), (x, 0))
        x += s + mm(gap_mm)

    box_w = W - x - mm(pad_mm)
    # largest font size that fits the remaining box
    size = H
    while size > 6:
        f = ImageFont.truetype(FONT, size)
        l, t, r, b = d.textbbox((0, 0), text, font=f)
        if r - l <= box_w and b - t <= H:
            break
        size -= 1
    l, t, r, b = d.textbbox((0, 0), text, font=f)
    d.text((x + (box_w - (r - l)) / 2 - l, (H - (b - t)) / 2 - t),
           text, font=f, fill=0)

    # hard threshold - never dither line art or small type
    return img.point(lambda p: 255 if p > threshold else 0, mode="1")


if __name__ == "__main__":
    rows = [
        ("nut-hex", "M3 hex nut"),
        ("nut-square", "M6 square"),
        ("nut-wing", "M8 wing"),
        ("washer-flat", "M4 washer"),
        ("washer-split", "M5 split"),
        ("washer-tooth", "M4 tooth"),
        ("bearing-ball", "608ZZ"),
        ("screw-socket-cap", "M3x12 SHCS"),
        ("screw-countersunk", "M4x20 CSK"),
        ("screw-pan", "M3x8 pan"),
        ("bolt-hex", "M8x40 bolt"),
        ("screw-wood", "4x30 wood"),
        ("screw-set", "M4x6 grub"),
        ("standoff", "M3x10 F/F"),
        ("threaded-rod", "M6 rod"),
        ("drive-torx", "T20 bits"),
        ("drive-hex", "2.5mm hex"),
        ("mdi:screw-lag", "8x60 lag"),
    ]
    ZOOM = 3
    W, H = mm(29), mm(6.8)
    sheet = Image.new("L", ((W + 16) * ZOOM, (H + 12) * ZOOM * len(rows)), 210)
    for i, (ic, tx) in enumerate(rows):
        try:
            lab = render(tx, icon=ic).convert("L")
        except Exception as e:
            print("skip", ic, e)
            continue
        tape = Image.new("L", (W + 16, H + 12), 255)
        tape.paste(lab, (8, 6))
        sheet.paste(tape.resize(((W + 16) * ZOOM, (H + 12) * ZOOM), Image.NEAREST),
                    (0, i * (H + 12) * ZOOM))
    (ROOT / "docs").mkdir(exist_ok=True)
    out = ROOT / "docs" / "label-preview.png"
    sheet.save(out)
    print("wrote", out, sheet.size)
