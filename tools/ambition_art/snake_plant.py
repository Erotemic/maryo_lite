"""The Snake Plant: Mary-O's plant in a pipe.

It is a snake that wears leaves: the banded body of the Solid Snake, upright
like a stalk, with two leaves on it and a collar of petals under its head. The
head is the snake's (a gold eye under a heavy brow) and it bites the air.

The frame is a fixed canvas. The bottom of the stalk is at the bottom of the
frame, on its middle column: the game puts that point on the mouth of the pipe
the plant stands in, and the pipe's own art is drawn in front of the plant, so
the part that is under the mouth is not seen.

Rows: ``idle`` (the bite, in a loop) and ``death`` (it wilts).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageOps

from .solid_snake import (
    BELLY,
    EYE,
    EYE_GOLD,
    FANG,
    MOUTH,
    OUTLINE,
    SNAKE,
    SNAKE_DARK,
    SNAKE_DEEP,
    SNAKE_LIGHT,
    TONGUE,
)

RGBA = Tuple[int, int, int, int]
Point = Tuple[float, float]

TARGET_NAME = "snake_plant"
FRAME_SIZE = (96, 128)
SUPER = 4
ROWS: List[Tuple[str, int, int]] = [("idle", 8, 110), ("death", 5, 110)]

TRANSPARENT = (0, 0, 0, 0)
LEAF: RGBA = (62, 138, 84, 255)
LEAF_LIGHT: RGBA = (112, 184, 110, 255)
LEAF_DARK: RGBA = (38, 96, 66, 255)
PETAL: RGBA = (244, 122, 176, 255)
PETAL_LIGHT: RGBA = (255, 188, 216, 255)
PETAL_DARK: RGBA = (190, 70, 128, 255)

ROOT: Point = (48.0, 127.0)
NECK_Y = 62.0
HEAD_SCALE = 1.5
LEAF_SCALE = 1.5
PETAL_SCALE = 1.9

ACTOR_METADATA = {
    "actor": {"character_id": "snake_plant", "display_name": "Snake Plant"},
    "body": {
        "body_plan": "Serpentine",
        "body_kind": "Snake",
        "mass_class": "Light",
        "traits": ["serpent", "plant_parody", "pipe_dweller"],
        "locomotion_hint": "None",
    },
    "visual": {"default_pose": "idle", "portrait": {"animation": "idle", "frame": 2}},
    "tags": ["serpent", "plant_parody", "enemy"],
    "animation_bindings": {
        "default": {"animation": "idle", "events": []},
        "combat.death": {"animation": "death", "events": []},
    },
}


def _s(v: float) -> int:
    return int(round(v * SUPER))


def _pts(points: Sequence[Point]) -> List[Tuple[int, int]]:
    return [(_s(x), _s(y)) for x, y in points]


def _shape(draw: ImageDraw.ImageDraw, points: Sequence[Point], fill: RGBA, line: float = 1.1) -> None:
    """A filled shape with the dark outline of the family."""
    draw.polygon(_pts(points), fill=fill)
    draw.line(_pts(list(points) + [points[0]]), fill=OUTLINE, width=_s(line), joint="curve")


def _oval(draw: ImageDraw.ImageDraw, c: Point, rx: float, ry: float, fill: RGBA, line: float = 0.0) -> None:
    box = [_s(c[0] - rx), _s(c[1] - ry), _s(c[0] + rx), _s(c[1] + ry)]
    if line > 0.0:
        draw.ellipse(box, fill=fill, outline=OUTLINE, width=_s(line))
    else:
        draw.ellipse(box, fill=fill)


def _turned(points: Sequence[Point], about: Point, degrees: float) -> List[Point]:
    a = math.radians(degrees)
    ca, sa = math.cos(a), math.sin(a)
    return [
        (about[0] + (x - about[0]) * ca - (y - about[1]) * sa, about[1] + (x - about[0]) * sa + (y - about[1]) * ca)
        for x, y in points
    ]


def _stalk(sway: float, droop: float) -> List[Point]:
    """The middle line of the body, from the root to the neck."""
    line = []
    for step in range(13):
        t = step / 12.0
        y = ROOT[1] + (NECK_Y - ROOT[1]) * t * (1.0 - 0.35 * droop)
        x = ROOT[0] + math.sin(t * math.pi * 1.5 + sway) * 3.2 * t + droop * 9.0 * t * t
        line.append((x, y))
    return line


def _body(draw: ImageDraw.ImageDraw, line: Sequence[Point]) -> None:
    def side(width_at, sign: float) -> List[Point]:
        out = []
        for i, (x, y) in enumerate(line):
            j, k = max(i - 1, 0), min(i + 1, len(line) - 1)
            dx, dy = line[k][0] - line[j][0], line[k][1] - line[j][1]
            length = math.hypot(dx, dy) or 1.0
            half = width_at(i / (len(line) - 1))
            out.append((x + sign * -dy / length * half, y + sign * dx / length * half))
        return out

    full = lambda t: 9.5 - 2.4 * t  # noqa: E731
    left, right = side(full, -1.0), side(full, 1.0)
    _shape(draw, left + right[::-1], SNAKE, line=1.2)
    # The pale belly is the side of the body that faces where it looks.
    belly_edge = side(lambda t: (9.5 - 2.4 * t) * 0.45, -1.0)
    draw.polygon(_pts(left + belly_edge[::-1]), fill=BELLY)
    # The dark saddles of the Solid Snake, across the back.
    back_inner = side(lambda t: (9.5 - 2.4 * t) * 0.0, 1.0)
    for start in (1, 3, 5, 7, 9):
        band = right[start : start + 2] + back_inner[start : start + 2][::-1]
        draw.polygon(_pts(band), fill=SNAKE_DARK)
    light = side(lambda t: (9.5 - 2.4 * t) * 0.62, 1.0)
    draw.line(_pts(light[1:-1]), fill=SNAKE_LIGHT, width=_s(1.2))
    draw.line(_pts(left + right[::-1] + [left[0]]), fill=OUTLINE, width=_s(1.2), joint="curve")


def _leaf(draw: ImageDraw.ImageDraw, at: Point, side: float, degrees: float) -> None:
    """A leaf that grows from `at` to the left (`side` -1) or the right (+1)."""
    shape = [(0.0, 0.0), (7.0, -6.5), (17.0, -7.0), (24.0, -1.5), (16.0, 3.5), (6.0, 3.0)]
    vein = [(1.0, -0.4), (21.5, -2.0)]
    place = lambda pts: [  # noqa: E731
        (at[0] + side * x * LEAF_SCALE, at[1] + y * LEAF_SCALE) for x, y in _turned(pts, (0.0, 0.0), degrees)
    ]
    _shape(draw, place(shape), LEAF)
    lit = [(4.0, -3.4), (8.0, -5.4), (16.0, -5.8), (20.0, -3.0)]
    draw.line(_pts(place(lit)), fill=LEAF_LIGHT, width=_s(1.1), joint="curve")
    draw.line(_pts(place(vein)), fill=LEAF_DARK, width=_s(0.8))


def _collar(draw: ImageDraw.ImageDraw, neck: Point, flutter: float) -> None:
    """The petals under the head: what makes a snake a plant."""
    for index, degrees in enumerate((-104.0, -66.0, -30.0, 30.0, 66.0, 104.0)):
        turn = degrees + flutter * (1.0 if index % 2 == 0 else -1.0)
        petal = _turned([(0.0, 2.0), (-5.0, -7.0), (0.0, -16.5), (5.0, -7.0)], (0.0, 0.0), turn)
        at = [(neck[0] + x * PETAL_SCALE, neck[1] + 2.0 + y * PETAL_SCALE) for x, y in petal]
        _shape(draw, at, PETAL, line=1.0)
        mid = _turned([(0.0, -3.0), (0.0, -12.5)], (0.0, 0.0), turn)
        lit = [(neck[0] + x * PETAL_SCALE, neck[1] + 2.0 + y * PETAL_SCALE) for x, y in mid]
        draw.line(_pts(lit), fill=PETAL_LIGHT, width=_s(1.8))
    _oval(draw, (neck[0], neck[1] + 3.0), 9.5, 5.0, PETAL_DARK, line=1.0)


def _head(draw: ImageDraw.ImageDraw, neck: Point, gape: float, tilt: float, tongue: float, shut_eye: bool) -> None:
    """The head, drawn looking to the left. `gape` is how far the jaws are open, 0 to 1."""
    hinge = (neck[0] + 9.0 * HEAD_SCALE, neck[1] - 12.0 * HEAD_SCALE)
    place = lambda pts, deg: [  # noqa: E731
        (hinge[0] + x * HEAD_SCALE, hinge[1] + y * HEAD_SCALE)
        for x, y in _turned(_turned(pts, (0.0, 0.0), deg), (-9.0, 12.0), tilt)
    ]
    up, down = -20.0 * gape, 42.0 * gape
    # The inside of the mouth, between the jaws.
    if gape > 0.05:
        inside = place([(0.0, 0.0), (-25.0, -3.0)], up) + place([(-24.0, 5.0), (0.0, 3.0)], down)
        draw.polygon(_pts(inside), fill=MOUTH)
        if tongue > 0.0:
            fork = place([(-8.0, 2.0), (-22.0 - 9.0 * tongue, 2.5)], (up + down) * 0.5)
            draw.line(_pts(fork), fill=TONGUE, width=_s(2.0))
            tip = fork[1]
            draw.line(_pts([tip, (tip[0] - 4.0, tip[1] - 2.5)]), fill=TONGUE, width=_s(1.2))
            draw.line(_pts([tip, (tip[0] - 4.0, tip[1] + 2.5)]), fill=TONGUE, width=_s(1.2))
    # The lower jaw.
    jaw = [(4.0, 1.0), (-22.0, 3.0), (-26.0, 6.5), (-20.0, 10.0), (2.0, 11.0), (7.0, 6.0)]
    _shape(draw, place(jaw, down), BELLY, line=1.1)
    # The skull, with the brow of the Solid Snake.
    skull = [(8.0, 4.0), (9.0, -6.0), (2.0, -13.0), (-12.0, -13.5), (-24.0, -8.0), (-29.0, -3.0), (-24.0, 1.0), (-4.0, 3.0)]
    _shape(draw, place(skull, up), SNAKE, line=1.2)
    draw.line(_pts(place([(1.0, -11.0), (-11.0, -11.6), (-21.5, -7.0)], up)), fill=SNAKE_LIGHT, width=_s(1.3), joint="curve")
    draw.polygon(_pts(place([(8.0, 3.0), (8.6, -5.0), (3.0, -5.0), (0.0, 2.6)], up)), fill=SNAKE_DARK)
    if gape > 0.25:
        for x in (-22.0, -16.0):
            draw.polygon(_pts(place([(x, 0.6), (x + 1.6, 6.0), (x + 3.4, 0.9)], up)), fill=FANG)
    eye = place([(-10.5, -6.0)], up)[0]
    if shut_eye:
        draw.line(_pts([(eye[0] - 4.2, eye[1]), (eye[0] + 4.2, eye[1] + 0.8)]), fill=EYE, width=_s(1.4))
    else:
        _oval(draw, eye, 4.6, 4.2, EYE_GOLD, line=0.8)
        _oval(draw, (eye[0] - 1.1, eye[1] + 0.2), 1.3, 3.0, EYE)
    draw.line(_pts(place([(-15.5, -10.6), (-5.5, -8.8)], up)), fill=SNAKE_DEEP, width=_s(2.8))
    _oval(draw, place([(-26.0, -4.5)], up)[0], 1.1, 0.9, SNAKE_DEEP)


def _render_frame(anim: str, frame_idx: int, nframes: int) -> Image.Image:
    image = Image.new("RGBA", (FRAME_SIZE[0] * SUPER, FRAME_SIZE[1] * SUPER), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    phase = frame_idx / float(max(nframes, 1))
    if anim == "death":
        droop = min(1.0, (frame_idx + 1) / float(nframes))
        sway, gape, tongue, flutter = 0.0, 0.25 * (1.0 - droop), 0.0, 0.0
    else:
        droop = 0.0
        sway = math.sin(phase * math.tau) * 0.5
        # Two bites in one loop: open wide, shut fast.
        beat = (phase * 2.0) % 1.0
        gape = math.sin(min(beat / 0.75, 1.0) * math.pi) ** 0.6 if beat < 0.75 else 0.0
        tongue = 1.0 if frame_idx == nframes - 1 else 0.0
        flutter = math.sin(phase * math.tau * 2.0) * 5.0
    line = _stalk(sway, droop)
    neck = line[-1]
    _leaf(draw, line[3], 1.0, 8.0 + 30.0 * droop + flutter * 0.6)
    _leaf(draw, line[6], -1.0, -4.0 - 30.0 * droop + flutter * 0.6)
    _body(draw, line)
    _collar(draw, neck, flutter)
    tilt = 48.0 * droop + math.sin(phase * math.tau) * 3.0
    _head(draw, neck, max(gape, 0.08 if tongue else 0.0), tilt, tongue, shut_eye=anim == "death" and frame_idx >= 2)
    # The drawing above looks to the left. A sheet looks to the right, so the
    # frame is mirrored: the root is on the middle column and stays there.
    return ImageOps.mirror(image.resize(FRAME_SIZE, Image.Resampling.LANCZOS))


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
