#!/usr/bin/env python3
"""Render every icon the way the printer will actually see it: ~90px tall,
hard threshold to 1-bit. Shown at 1x and at 4x nearest-neighbour so the
damage is visible."""
import glob, io, os
from pathlib import Path
import cairosvg
from PIL import Image, ImageDraw, ImageFont

SIZE = 90          # px an icon gets on 9mm tape at 360dpi
ZOOM = 4
COLS = 6

ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "src" / "ptuich" / "icons"
DOCS = ROOT / "docs"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def render(path, size=SIZE):
    png = cairosvg.svg2png(url=path, output_width=size, output_height=size,
                           background_color="white")
    im = Image.open(io.BytesIO(png)).convert("L")
    return im.point(lambda p: 255 if p > 128 else 0, mode="1").convert("L")


def sheet(files, out):
    cell_w = SIZE * ZOOM + 20
    cell_h = SIZE * ZOOM + SIZE + 46
    rows = (len(files) + COLS - 1) // COLS
    img = Image.new("L", (COLS * cell_w, rows * cell_h), 255)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 20)
    for i, p in enumerate(files):
        cx = (i % COLS) * cell_w
        cy = (i // COLS) * cell_h
        big = render(p).resize((SIZE * ZOOM, SIZE * ZOOM), Image.NEAREST)
        img.paste(big, (cx + 10, cy + 8))
        img.paste(render(p), (cx + 10, cy + SIZE * ZOOM + 14))
        d.text((cx + SIZE + 26, cy + SIZE * ZOOM + 14 + SIZE // 2 - 12),
               os.path.basename(p)[:-4], font=f, fill=0)
        d.rectangle([cx + 9, cy + 7, cx + 11 + SIZE * ZOOM, cy + 9 + SIZE * ZOOM],
                    outline=200)
    img.save(out)
    print("wrote", out, img.size)


if __name__ == "__main__":
    DOCS.mkdir(exist_ok=True)
    sheet(sorted(glob.glob(str(ICON_DIR / "*.svg"))),
          str(DOCS / "icon-contact-sheet.png"))
