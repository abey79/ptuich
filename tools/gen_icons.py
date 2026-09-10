#!/usr/bin/env python3
"""
Generate a fastener icon set tuned for small thermal label printing.

Design constraints (9mm TZe tape, ~100px of printable height at 360dpi):
  - icons get rendered into roughly a 90x90px box, then hard-thresholded to 1-bit
  - so: solid silhouettes, holes cut with fill-rule=evenodd, no hairlines
  - MIN_FEATURE below is the smallest gap/limb allowed anywhere, in viewBox units
  - 512 viewBox units -> 90px means 1px ~= 5.7 units, so MIN_FEATURE=26 is ~4.5px

Screw-like icons are drawn vertically then rotated -45 deg, which lets a long
thin shape fill a square box (head upper-left, tip lower-right).
"""

import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "ptuich" / "icons"
VB = 512
C = VB / 2  # 256, centre

MIN_FEATURE = 26  # smallest gap or limb, in viewBox units


# ---------------------------------------------------------------- path helpers

def poly(pts, close=True):
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return d + (" Z" if close else "")


def circ(cx, cy, r):
    """Circle as a path subpath, so it can be combined under fill-rule=evenodd."""
    return (f"M{cx - r:.1f},{cy:.1f} "
            f"a{r:.1f},{r:.1f} 0 1,0 {2 * r:.1f},0 "
            f"a{r:.1f},{r:.1f} 0 1,0 {-2 * r:.1f},0 Z")


def ngon(cx, cy, r, n, rot=0.0):
    return [(cx + r * math.cos(rot + i * 2 * math.pi / n),
             cy + r * math.sin(rot + i * 2 * math.pi / n)) for i in range(n)]


def star(cx, cy, r_out, r_in, lobes, rot=0.0):
    pts = []
    for i in range(lobes * 2):
        r = r_out if i % 2 == 0 else r_in
        a = rot + i * math.pi / lobes
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def plus_poly(cx, cy, arm, half):
    """Plus sign as ONE polygon (never two overlapping rects - evenodd would
    punch the intersection back out)."""
    return [
        (cx - half, cy - arm), (cx + half, cy - arm), (cx + half, cy - half),
        (cx + arm, cy - half), (cx + arm, cy + half), (cx + half, cy + half),
        (cx + half, cy + arm), (cx - half, cy + arm), (cx - half, cy + half),
        (cx - arm, cy + half), (cx - arm, cy - half), (cx - half, cy - half),
    ]


def threaded_shank(y0, y1, hw_out, hw_in, period, tip="flat", cx=C):
    """Vertical threaded shank silhouette: zigzag on both edges, half a period
    out of phase so it reads as a helix rather than a fir tree.
    tip: 'flat' | 'point'
    """
    half = period / 2.0
    n = max(2, int(round((y1 - y0) / half)))
    half = (y1 - y0) / n

    def hw_at(i, phase):
        # taper the last third for pointed tips
        base = hw_out if (i + phase) % 2 == 0 else hw_in
        return base

    right, left = [], []
    for i in range(n + 1):
        y = y0 + i * half
        t = 1.0
        if tip == "point":
            frac = (y - y0) / (y1 - y0)
            t = 1.0 if frac < 0.55 else max(0.0, (1.0 - frac) / 0.45)
        right.append((cx + hw_at(i, 0) * t, y))
        left.append((cx - hw_at(i, 1) * t, y))

    if tip == "point":
        pts = right + [(cx, y1 + 26)] + left[::-1]
    else:
        pts = right + left[::-1]
    return pts


def svg(body, rotate=False):
    g_open = (f'<g transform="translate({C},{C}) rotate(-45) scale(1.12) '
              f'translate({-C},{-C})">') if rotate else ""
    g_close = "</g>" if rotate else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VB} {VB}" '
            f'width="{VB}" height="{VB}" color="#000" fill="currentColor">'
            f'{g_open}{body}{g_close}</svg>\n')


def path(d, evenodd=True):
    fr = ' fill-rule="evenodd"' if evenodd else ""
    return f'<path{fr} d="{d}"/>'


# ---------------------------------------------------------------------- pieces

def head_on_head(recess_d):
    """A solid screw head seen end-on with the drive recess punched out."""
    return path(circ(C, C, 232) + " " + recess_d)


ICONS = {}


def add(name, body, rotate=False, tags=()):
    ICONS[name] = (svg(body, rotate), list(tags))


# ------------------------------------------------------------------- 1. nuts

add("nut-hex",
    path(poly(ngon(C, C, 232, 6)) + " " + circ(C, C, 100)),
    tags=("nut", "hex", "hexagon"))

add("nut-square",
    path(poly([(46, 46), (466, 46), (466, 466), (46, 466)]) + " " + circ(C, C, 100)),
    tags=("nut", "square"))

add("nut-nyloc",
    path(poly(ngon(C, C, 232, 6)) + " " + circ(C, C, 152)
         + " " + circ(C, C, 120) + " " + circ(C, C, 74)),
    tags=("nut", "nyloc", "lock", "insert"))

add("nut-wing",
    path(poly([(150, 206), (36, 62), (36, 450), (150, 306)])
         + " " + poly([(362, 206), (476, 62), (476, 450), (362, 306)]),
         evenodd=False)
    + path(circ(C, C, 142) + " " + circ(C, C, 60)),
    tags=("nut", "wing", "thumb"))

# ---------------------------------------------------------------- 2. washers

add("washer-flat",
    path(circ(C, C, 232) + " " + circ(C, C, 122)),
    tags=("washer", "flat"))

add("washer-split",
    path(circ(C, C, 232) + " " + circ(C, C, 128)
         + " " + poly([(C + 118, C - 33), (500, C - 33),
                        (500, C + 33), (C + 118, C + 33)])),
    tags=("washer", "split", "spring", "lock"))

add("washer-tooth",
    path(poly(star(C, C, 250, 192, 8, rot=math.pi / 8)) + " " + circ(C, C, 112)),
    tags=("washer", "tooth", "serrated", "star"))

# ----------------------------------------------------------- 3. bearings etc.

_balls = " ".join(circ(C + 130 * math.cos(i * math.pi / 4),
                       C + 130 * math.sin(i * math.pi / 4), 44) for i in range(8))
add("bearing-ball",
    path(circ(C, C, 240) + " " + circ(C, C, 192) + " " + _balls),
    tags=("bearing", "ball"))

add("dowel-pin",
    path(f"M60,{C - 56} h392 a56,56 0 0 1 0,112 h-392 a56,56 0 0 1 0,-112 Z"),
    rotate=True, tags=("dowel", "pin", "shaft"))

add("standoff",
    path(poly([(150, 168), (362, 168), (362, 344), (150, 344)])
         + " " + poly([(150, 168), (110, 200), (110, 312), (150, 344)])
         + " " + poly([(362, 168), (402, 200), (402, 312), (362, 344)])
         + " " + poly(threaded_shank(112, 40, 26, 14, 36, cx=0)[0:0] or
                      [(24, C - 26), (110, C - 26), (110, C + 26), (24, C + 26)])
         + " " + poly([(402, C - 26), (488, C - 26), (488, C + 26), (402, C + 26)]),
         evenodd=False),
    tags=("standoff", "spacer", "pillar"))

add("rivet",
    path(f"M{C - 108},176 a108,108 0 0 1 216,0 "
         f"L{C + 56},176 L{C + 56},452 L{C - 56},452 L{C - 56},176 Z",
         evenodd=False),
    rotate=True, tags=("rivet", "pop"))

# ------------------------------------------------- 4. screws & bolts, profile

SHANK = dict(hw_out=48, hw_in=28, period=64)


def screw(head_pts, shank_y0, tip="flat", notch=None, taper=False):
    body = poly(head_pts) + " " + poly(
        threaded_shank(shank_y0, 486, tip=tip, **SHANK))
    if notch:
        body += " " + poly(notch)
    return path(body)


# pan head: rounded crown, slot notch in the top
add("screw-pan",
    path("M171,134 L171,118 a85,85 0 0 1 170,0 L341,134 Z"
         + " " + poly([(C - 16, 34), (C + 16, 34), (C + 16, 102), (C - 16, 102)])
         + " " + poly(threaded_shank(132, 486, **SHANK))),
    rotate=True, tags=("screw", "machine", "pan", "round"))

# countersunk / flat head: trapezoid
add("screw-countersunk",
    path(poly([(163, 34), (349, 34), (300, 134), (212, 134)])
         + " " + poly([(C - 17, 34), (C + 17, 34), (C + 17, 100), (C - 17, 100)])
         + " " + poly(threaded_shank(134, 486, **SHANK))),
    rotate=True, tags=("screw", "countersunk", "flat", "flathead"))

# socket cap: straight cylinder head with a hex socket sunk into it
add("screw-socket-cap",
    path(poly([(180, 30), (332, 30), (332, 150), (180, 150)])
         + " " + poly([(C - 40, 30), (C + 40, 30), (C + 26, 96), (C - 26, 96)])
         + " " + poly(threaded_shank(150, 486, **SHANK))),
    rotate=True, tags=("screw", "socket", "cap", "allen", "shcs"))

# hex bolt: wide, short, chamfered corners, part-threaded shank
add("bolt-hex",
    path(poly([(178, 52), (200, 26), (312, 26), (334, 52),
               (334, 128), (178, 128)])
         + " " + poly([(C - 48, 128), (C + 48, 128), (C + 48, 196), (C - 48, 196)])
         + " " + poly(threaded_shank(196, 486, **SHANK))),
    rotate=True, tags=("bolt", "hex", "machine"))

# wood screw: countersunk head, coarse tapered thread, point
add("screw-wood",
    path(poly([(157, 30), (355, 30), (300, 138), (212, 138)])
         + " " + poly([(C - 17, 30), (C + 17, 30), (C + 17, 100), (C - 17, 100)])
         + " " + poly(threaded_shank(138, 452, hw_out=52, hw_in=24,
                                     period=76, tip="point"))),
    rotate=True, tags=("screw", "wood", "self-tapping", "pointed"))

# set screw / grub: headless, socket at one end
add("screw-set",
    path(poly(threaded_shank(110, 402, hw_out=62, hw_in=42, period=68))
         + " " + poly([(C - 30, 114), (C + 30, 114), (C + 19, 176), (C - 19, 176)])),
    rotate=True, tags=("screw", "set", "grub", "headless"))

add("threaded-rod",
    path(poly(threaded_shank(30, 482, hw_out=54, hw_in=32, period=68))),
    rotate=True, tags=("rod", "threaded", "stud"))

# ------------------------------------------------------ 5. drive types, head-on

add("drive-slot",
    head_on_head(poly([(78, C - 33), (434, C - 33), (434, C + 33), (78, C + 33)])),
    tags=("drive", "slot", "slotted", "flat"))

add("drive-phillips",
    head_on_head(poly(plus_poly(C, C, 178, 33))),
    tags=("drive", "phillips", "cross", "ph"))

_pozi_ticks = " ".join(
    poly(star(C + 118 * math.cos(a), C + 118 * math.sin(a), 46, 46, 2,
              rot=a)) for a in
    [math.pi / 4, 3 * math.pi / 4, 5 * math.pi / 4, 7 * math.pi / 4])
add("drive-pozidriv",
    head_on_head(poly(plus_poly(C, C, 178, 31)) + " " + " ".join(
        poly([(C + (95 + 4 * s) * math.cos(a) - 22 * math.sin(a),
               C + (95 + 4 * s) * math.sin(a) + 22 * math.cos(a)),
              (C + (95 + 4 * s) * math.cos(a) + 22 * math.sin(a),
               C + (95 + 4 * s) * math.sin(a) - 22 * math.cos(a)),
              (C + 178 * math.cos(a) + 22 * math.sin(a),
               C + 178 * math.sin(a) - 22 * math.cos(a)),
              (C + 178 * math.cos(a) - 22 * math.sin(a),
               C + 178 * math.sin(a) + 22 * math.cos(a))])
        for s, a in enumerate([math.pi / 4, 3 * math.pi / 4,
                               5 * math.pi / 4, 7 * math.pi / 4]))),
    tags=("drive", "pozidriv", "pozi", "pz"))

add("drive-hex",
    head_on_head(poly(ngon(C, C, 148, 6))),
    tags=("drive", "hex", "allen", "socket"))

add("drive-torx",
    head_on_head(poly(star(C, C, 162, 96, 6, rot=math.pi / 6))),
    tags=("drive", "torx", "star", "tx"))

add("drive-square",
    head_on_head(poly([(C - 104, C - 104), (C + 104, C - 104),
                       (C + 104, C + 104), (C - 104, C + 104)])),
    tags=("drive", "square", "robertson"))

# ------------------------------------------------------------------ write out

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    index = {}
    for name, (data, tags) in ICONS.items():
        with open(OUT / (name + ".svg"), "w") as f:
            f.write(data)
        index[name] = tags
    with open(OUT / "index.json", "w") as f:
        json.dump(index, f, indent=2, sort_keys=True)
    print(f"wrote {len(ICONS)} icons to {OUT}")
