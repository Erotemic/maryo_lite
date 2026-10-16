"""Ambition FireOrb painter, adapted from targets/props/entities.py.

Mary-O uses this same artwork for all the balls of a rotating Fire Bar.
Their orbit paths are authored in LDtk and simulated separately in motion.py.
"""
from __future__ import annotations

import math
from PIL import Image, ImageDraw
from .common import rgba
from .draw import blending_draw

FRAME_SIZE = (128, 128)
ROWS = [('idle', 8, 75)]


def bbox(cx: float, cy: float, rx: float, ry: float):
    return (round(cx - rx), round(cy - ry), round(cx + rx), round(cy + ry))


def fire_orb(draw):
    """Round flame with three tongues, preserving the original geometry."""
    outline = rgba('#3A0A0C')
    draw.ellipse(bbox(64,64,52,52), fill=rgba('#FF4A24',52))
    for turn in (0.0,120.0,240.0):
        a = math.radians(turn-90.0)
        ca, sa = math.cos(a), math.sin(a)
        tongue = [(-9,-14),(0,-31),(9,-14)]
        placed = [(64 + x * -sa - y * ca, 64 + x * ca - y * sa) for x,y in tongue]
        draw.polygon(placed, fill=outline)
        inside = [(-6,-14),(0,-26),(6,-14)]
        placed = [(64 + x * -sa - y * ca, 64 + x * ca - y * sa) for x,y in inside]
        draw.polygon(placed, fill=rgba('#E02A1C'))
    for rx,ry,fill,center in (
        (40,40,outline,(64,64)),(35,35,rgba('#E02A1C'),(64,64)),
        (26,26,rgba('#FF6A22'),(63,62)),(16,16,rgba('#FFC24A'),(61.5,60)),
        (7,7,rgba('#FFF3C4'),(60,58))):
        draw.ellipse(bbox(*center,rx,ry), fill=fill)


def _render_frame(row: str, frame_idx: int, total: int) -> Image.Image:
    image = Image.new('RGBA', FRAME_SIZE, (0,0,0,0))
    fire_orb(blending_draw(image))
    # Rotate the source artwork, not the collision orb, to give fire a little
    # motion without bringing over the original shader.
    return image.rotate(-frame_idx * 5, resample=Image.Resampling.BICUBIC)


def render_void_orb(_row: str, _frame_idx: int, _total: int) -> Image.Image:
    """The Mary-O Void Lizard's projectile from Ambition's `void_orb`."""
    image = Image.new('RGBA', FRAME_SIZE, (0,0,0,0))
    d = blending_draw(image)
    for cx, cy, radius, fill in (
        (64, 64, 54, rgba('#FFFFFF', 44)),
        (64, 64, 42, rgba('#C9C9D2')),
        (64, 64, 39, rgba('#FFFFFF')),
        (64, 64, 35, rgba('#0D0D12')),
        (62, 62, 20, rgba('#030305')),
    ):
        d.ellipse(bbox(cx,cy,radius,radius),fill=fill)
    return image
