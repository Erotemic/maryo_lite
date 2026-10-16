"""Mary-O's fireball: the spark blossom.

The shot of the cinder beacon: a flower of fire that turns as it flies. Five
petals of flame about a hot middle, with a dark rim so it reads on the pink
sky and in the dark under the ground.

One row, ``idle``: the blossom turns a fifth of a turn in the row, so the loop
has no jump. The frame is a fixed canvas with the blossom on its middle.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Sequence, Tuple

from PIL import Image, ImageDraw


RGBA = Tuple[int, int, int, int]
Point = Tuple[float, float]

TARGET = "super_mary_o_spark"
FRAME = (64, 64)
SUPER = 4
FRAMES = 6
PETALS = 5

OUTLINE: RGBA = (74, 22, 12, 255)
PETAL: RGBA = (244, 96, 30, 255)
PETAL_HOT: RGBA = (255, 170, 44, 255)
PETAL_CORE: RGBA = (255, 228, 120, 255)
HEART: RGBA = (255, 250, 224, 255)
GLOW: RGBA = (255, 150, 60, 56)

_ACTOR = {
    "actor": {"character_id": f"prop_{TARGET}", "display_name": "Mary-O Spark Blossom"},
    "body": {
        "body_plan": "StaticProp",
        "body_kind": "Scenery",
        "mass_class": "Static",
        "locomotion_hint": "None",
        "traits": ["projectile", "fire", "animated"],
    },
    "tags": ["projectile", "fire", "animated"],
}


def _pts(points: Sequence[Point]) -> List[Tuple[int, int]]:
    return [(int(round(x * SUPER)), int(round(y * SUPER))) for x, y in points]


def _petal(center: Point, angle: float, length: float, width: float, curl: float) -> List[Point]:
    """A petal of flame from the middle out along `angle`, with its tip bent by `curl`."""
    ca, sa = math.cos(angle), math.sin(angle)
    shape = [(4.0, -width * 0.55), (length * 0.55, -width), (length, curl * width), (length * 0.6, width * 0.8), (4.0, width * 0.55)]
    return [(center[0] + x * ca - y * sa, center[1] + x * sa + y * ca) for x, y in shape]


def _spark_frame(animation: str, frame_idx: int, nframes: int) -> Image.Image:
    del animation
    image = Image.new("RGBA", (FRAME[0] * SUPER, FRAME[1] * SUPER), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    center = (FRAME[0] / 2.0, FRAME[1] / 2.0)
    turn = (frame_idx / float(max(nframes, 1))) * (math.tau / PETALS)
    beat = math.sin(frame_idx / float(max(nframes, 1)) * math.tau)
    glow = [_c * SUPER for _c in (center[0] - 29.0, center[1] - 29.0, center[0] + 29.0, center[1] + 29.0)]
    draw.ellipse(glow, fill=GLOW)
    for length, width, fill in ((27.0, 9.5, OUTLINE), (24.5, 7.6, PETAL), (18.0, 5.2, PETAL_HOT), (11.5, 3.0, PETAL_CORE)):
        for petal in range(PETALS):
            angle = turn + petal * math.tau / PETALS
            draw.polygon(_pts(_petal(center, angle, length + beat * 1.2, width, 0.9)), fill=fill)
    for radius, fill in ((9.5, OUTLINE), (8.0, PETAL_HOT), (6.0, PETAL_CORE), (3.4, HEART)):
        box = [(center[0] - radius) * SUPER, (center[1] - radius) * SUPER, (center[0] + radius) * SUPER, (center[1] + radius) * SUPER]
        draw.ellipse(box, fill=fill)
    return image.resize(FRAME, Image.Resampling.LANCZOS)
