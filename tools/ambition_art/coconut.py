"""Standalone version of Ambition's small held/thrown coconut sprite.

Adapted from targets/props/coconut.py. The full supersampled sheet publisher
isn't needed in Lite: one source-generated, alpha-safe idle PNG suffices.
"""
from __future__ import annotations

from PIL import Image, ImageDraw

FRAME_SIZE = (56, 48)
ROWS = [('idle', 1, 200)]


def _render_frame(_row: str, _index: int, _total: int) -> Image.Image:
    scale = 3
    img = Image.new('RGBA', (FRAME_SIZE[0] * scale, FRAME_SIZE[1] * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    p = lambda n: round(n * scale)
    cx, cy, rx, ry = 28, 24, 21, 18
    d.ellipse((p(cx-rx),p(cy-ry),p(cx+rx),p(cy+ry)),
              fill=(122,78,42,255), outline=(24,20,16,255),width=4)
    d.ellipse((p(cx-rx*.72),p(cy-ry*.8),p(cx+rx*.42),p(cy-ry*.06)),fill=(160,110,62,255))
    d.ellipse((p(cx-rx*.78),p(cy-ry*.62),p(cx+rx*.5),p(cy+ry*.22)),fill=(122,78,42,255))
    for k in range(-3,4):
        y = cy+k*4.6
        bend=(1-(k/4)**2)*2
        d.line([(p(cx-rx*.82),p(y)),(p(cx-4),p(y-bend)),(p(cx+rx*.5),p(y))],
               fill=(78,46,20,255),width=max(1,round(.7*scale)),joint='curve')
    for ex,ey in ((cx+rx*.68,cy-5),(cx+rx*.78,cy+3),(cx+rx*.5,cy+6.5)):
        d.ellipse((p(ex-2.2),p(ey-2.6),p(ex+2.2),p(ey+2.6)),fill=(46,26,12,255))
    return img.resize(FRAME_SIZE,Image.Resampling.LANCZOS)
