"""Generate the app icon (icon.png / icon.ico / icon.icns) from code.

No design assets needed — draws a simple, recognizable "convert" glyph (two
arrows cycling around a document) on a rounded gradient tile. Run with:

    python packaging/make_icon.py

Produces, next to this script:
* icon.png   (1024x1024 master)
* icon.ico   (Windows, multi-size)
* icon.icns  (macOS, if Pillow supports writing ICNS on this platform)
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SIZE = 1024
BG_TOP = (88, 101, 242)     # indigo
BG_BOTTOM = (37, 99, 235)   # blue
ACCENT = (255, 255, 255)


def _rounded_gradient(size: int, radius: int) -> Image.Image:
    grad = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / (size - 1)
        grad.putpixel(
            (0, y),
            tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3)),
        )
    grad = grad.resize((size, size))
    img = grad.convert("RGBA")

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=radius, fill=255
    )
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def _draw_glyph(img: Image.Image) -> None:
    d = ImageDraw.Draw(img)
    cx = cy = SIZE // 2
    r = SIZE * 0.30
    w = int(SIZE * 0.055)

    # Two opposing circular arcs => a "recycle / convert" loop.
    box = [cx - r, cy - r, cx + r, cy + r]
    d.arc(box, start=40, end=210, fill=ACCENT, width=w)
    d.arc(box, start=220, end=390, fill=ACCENT, width=w)

    # Arrowheads at the open ends of each arc.
    for ang in (210, 390 - 360):
        a = math.radians(ang)
        px, py = cx + r * math.cos(a), cy + r * math.sin(a)
        s = SIZE * 0.07
        perp = a + math.pi / 2
        tip = (px + s * math.cos(a), py + s * math.sin(a))
        left = (px + s * math.cos(perp), py + s * math.sin(perp))
        right = (px - s * math.cos(perp), py - s * math.sin(perp))
        d.polygon([tip, left, right], fill=ACCENT)


def main() -> None:
    img = _rounded_gradient(SIZE, radius=int(SIZE * 0.22))
    _draw_glyph(img)

    png = HERE / "icon.png"
    img.save(png)
    print("wrote", png)

    ico = HERE / "icon.ico"
    img.save(ico, sizes=[(s, s) for s in (16, 32, 48, 64, 128, 256)])
    print("wrote", ico)

    try:
        icns = HERE / "icon.icns"
        # ICNS requires a square image; Pillow picks supported sizes itself.
        img.save(icns)
        print("wrote", icns)
    except Exception as exc:  # noqa: BLE001
        print(f"(skipped icon.icns: {exc} — CI builds it with iconutil on macOS)")


if __name__ == "__main__":
    main()
