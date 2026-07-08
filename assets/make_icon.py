"""One-off generator for the app icon (run manually, not at app runtime).
Generic two-arrow "sync" glyph, matching the app's blue accent color."""

import math
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent
ICONSET = OUT / "icon.iconset"
ICONSET.mkdir(exist_ok=True)

BLUE_TOP = (61, 124, 240)
BLUE_BOTTOM = (37, 90, 196)
WHITE = (255, 255, 255, 255)


def draw_arc_arrow(draw, size, start_deg, end_deg, stroke_w):
    """Draw an arc from start_deg to end_deg with an arrowhead at end_deg,
    pointing along the direction of travel (tangent to the circle)."""
    cx, cy = size / 2, size / 2
    r = size * 0.27
    bbox = [cx - r, cy - r, cx + r, cy + r]
    draw.arc(bbox, start_deg, end_deg, fill=WHITE, width=stroke_w)

    angle = math.radians(end_deg)
    tip_x = cx + r * math.cos(angle)
    tip_y = cy + r * math.sin(angle)
    travel = angle + math.pi / 2
    head_len = size * 0.11
    p_tip = (tip_x + head_len * 0.6 * math.cos(travel), tip_y + head_len * 0.6 * math.sin(travel))
    perp = travel + math.pi / 2
    base1 = (tip_x - head_len * 0.55 * math.cos(perp) - head_len * 0.35 * math.cos(travel),
             tip_y - head_len * 0.55 * math.sin(perp) - head_len * 0.35 * math.sin(travel))
    base2 = (tip_x + head_len * 0.55 * math.cos(perp) - head_len * 0.35 * math.cos(travel),
             tip_y + head_len * 0.55 * math.sin(perp) - head_len * 0.35 * math.sin(travel))
    draw.polygon([p_tip, base1, base2], fill=WHITE)


def draw_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for y in range(size):
        t = y / size
        r = int(BLUE_TOP[0] + (BLUE_BOTTOM[0] - BLUE_TOP[0]) * t)
        g = int(BLUE_TOP[1] + (BLUE_BOTTOM[1] - BLUE_TOP[1]) * t)
        b = int(BLUE_TOP[2] + (BLUE_BOTTOM[2] - BLUE_TOP[2]) * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))

    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    radius = int(size * 0.22)
    mdraw.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=radius, fill=255)
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg.paste(img, (0, 0), mask)
    img = bg
    draw = ImageDraw.Draw(img)

    stroke_w = max(2, int(size * 0.075))
    # two opposing arcs forming the classic "sync" double-arrow loop
    draw_arc_arrow(draw, size, -150, 60, stroke_w)
    draw_arc_arrow(draw, size, 30, 240, stroke_w)

    return img


SIZES = {
    "icon_16x16.png": 16,
    "icon_16x16@2x.png": 32,
    "icon_32x32.png": 32,
    "icon_32x32@2x.png": 64,
    "icon_128x128.png": 128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png": 256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png": 512,
    "icon_512x512@2x.png": 1024,
}

for name, px in SIZES.items():
    draw_icon(px).save(ICONSET / name)

print(f"Wrote iconset to {ICONSET}")
