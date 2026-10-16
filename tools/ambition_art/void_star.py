"""The Void Star: a small enemy of Mary-O that no stomp can hurt.

A hole in the world in the shape of a star. Its body is near to black, with no
light and no colour in it; its edge is a thin white line; its two eyes are the
only other white on it. It goes along the ground on its points, like a wheel.

The frame is a fixed canvas. The star looks to the right, and its lowest point
is on the bottom rows of the frame in each frame, so a turn of the wheel lifts
and lowers its middle.

Rows: ``idle`` (it breathes), ``walk`` (a fifth of a turn of the wheel, which
is a loop for a star of five points) and ``death`` (it closes).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFilter


RGBA = Tuple[int, int, int, int]
Point = Tuple[float, float]

TARGET_NAME = "void_star"
FRAME_SIZE = (96, 96)
SUPER = 4
ROWS: List[Tuple[str, int, int]] = [("idle", 6, 150), ("walk", 8, 90), ("death", 5, 100)]

TRANSPARENT = (0, 0, 0, 0)
VOID: RGBA = (10, 10, 14, 255)
VOID_DEEP: RGBA = (3, 3, 5, 255)
WHITE: RGBA = (255, 255, 255, 255)

GROUND = 93.0
POINTS = 5
OUTER = 40.0
INNER = 18.0

ACTOR_METADATA = {
    "actor": {"character_id": "void_star", "display_name": "Void Star"},
    "body": {
        "body_plan": "Amorphous",
        "body_kind": "Entity",
        "mass_class": "Light",
        "traits": ["void", "star", "spiked"],
        "locomotion_hint": "Roll",
    },
    "visual": {"default_pose": "idle", "portrait": {"animation": "idle", "frame": 0}},
    "tags": ["void", "enemy"],
    "animation_bindings": {
        "default": {"animation": "idle", "events": []},
        "locomotion.walk": {"animation": "walk", "events": []},
        "combat.death": {"animation": "death", "events": []},
    },
}


def _pts(points: Sequence[Point]) -> List[Tuple[int, int]]:
    return [(int(round(x * SUPER)), int(round(y * SUPER))) for x, y in points]


def _star(turn: float, scale: float) -> List[Point]:
    """The star about (0, 0), turned by `turn` radians, with its corners cut so it is soft."""
    shape = []
    for index in range(POINTS):
        tip = turn - math.pi / 2.0 + index * math.tau / POINTS
        shape.append((OUTER * scale * math.cos(tip), OUTER * scale * math.sin(tip)))
        notch = tip + math.pi / POINTS
        shape.append((INNER * scale * math.cos(notch), INNER * scale * math.sin(notch)))
    for _ in range(2):
        cut = []
        for index, (x, y) in enumerate(shape):
            bx, by = shape[(index + 1) % len(shape)]
            cut.append((x * 0.76 + bx * 0.24, y * 0.76 + by * 0.24))
            cut.append((x * 0.24 + bx * 0.76, y * 0.24 + by * 0.76))
        shape = cut
    return shape


def _render_frame(anim: str, frame_idx: int, nframes: int) -> Image.Image:
    size = (FRAME_SIZE[0] * SUPER, FRAME_SIZE[1] * SUPER)
    phase = frame_idx / float(max(nframes, 1))
    turn, scale, shut = 0.0, 1.0, False
    if anim == "idle":
        scale = 1.0 + 0.03 * math.sin(phase * math.tau)
        turn = 0.04 * math.sin(phase * math.tau)
        shut = frame_idx == nframes - 1
    elif anim == "walk":
        turn = phase * math.tau / POINTS
    elif anim == "death":
        scale = max(0.08, 1.0 - (frame_idx + 1) / float(nframes))
        turn = phase * math.tau * 0.6
        shut = True

    shape = _star(turn, scale)
    low = max(y for _x, y in shape)
    cx, cy = FRAME_SIZE[0] / 2.0, GROUND - low
    if anim == "death":
        cy = GROUND - OUTER * 0.85
    placed = [(cx + x, cy + y) for x, y in shape]

    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(_pts(placed), fill=255)
    edge = mask.filter(ImageFilter.MaxFilter(2 * int(1.3 * SUPER) + 1))
    halo = mask.filter(ImageFilter.MaxFilter(2 * int(3.0 * SUPER) + 1)).filter(ImageFilter.GaussianBlur(2.2 * SUPER))
    image = Image.new("RGBA", size, TRANSPARENT)
    image.paste(WHITE, mask=halo.point(lambda value: int(value * 0.22)))
    image.paste(WHITE, mask=edge)
    image.paste(VOID, mask=mask)
    draw = ImageDraw.Draw(image)
    # The dark is deeper at its middle.
    draw.polygon(_pts([(cx + x * 0.45, cy + y * 0.45) for x, y in shape]), fill=VOID_DEEP)

    # The eyes do not turn with the wheel: it looks where it goes.
    if scale > 0.3:
        ey = cy - 3.0 * scale
        for ex, wide in ((cx + 2.0 * scale, 4.6), (cx + 13.5 * scale, 3.9)):
            if shut:
                draw.line(_pts([(ex - wide * scale, ey + 1.0), (ex + wide * scale, ey + 1.0)]), fill=WHITE, width=int(1.3 * SUPER))
                continue
            eye = [
                (ex - wide * scale, ey - 3.2 * scale),
                (ex + wide * scale, ey - 0.4 * scale),
                (ex + wide * 0.8 * scale, ey + 3.4 * scale),
                (ex - wide * 0.7 * scale, ey + 3.4 * scale),
            ]
            draw.polygon(_pts(eye), fill=WHITE)
    return image.resize(FRAME_SIZE, Image.Resampling.LANCZOS)


def render(out_dir: str | Path, **opts) -> List[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = build_sheet(
        target=TARGET_NAME,
        rows=ROWS,
        render_fn=_render_frame,
        out_dir=out_dir,
        frame_size=opts.get("frame_size", FRAME_SIZE),
        auto_crop=False,
        actor_metadata=ACTOR_METADATA,
        animation_key_map={name: name for name, _frames, _duration in ROWS},
    )
    return [
        outputs[key]
        for key in ("spritesheet", "yaml", "ron", "actor", "preview", "canonical", "canonical_transparent")
    ]


TARGETS = {TARGET_NAME: {"render": render, "actor_metadata": ACTOR_METADATA}}
