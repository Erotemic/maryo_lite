"""Sprite generator for a literal snake with a cardboard-box shell.

This is the intended Koopa-replacement joke: a sneaky green snake that crawls
around carrying a taped-up box on its back, retreats fully into it when
stomped, idles while boxed, peeks to telegraph emergence, and then emerges.
The target name stays ``solid_snake`` for the pun, but the art is an actual
snake, not the stealth-game protagonist.

The look (redrawn 2026-10-11, in place: the rows, the frame and the places
of the body and the box are the ones the sheet always had): a banded body
that tapers to its tail, with a light back, dark saddles and a pale belly; a
wedge of a head with a gold eye under a heavy brow, and a slate bandana tied
at the back with two tails that flutter; a corrugated box in three faces with
tape over its seam, a hand hole and a "this side up" mark. Boxed, its eyes
show in the hand hole for a moment. To peek, the box lifts on one side and
the head looks out from under it. Its hiss opens the mouth on two fangs.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw

from . import rigdoc, shape_rig
from .draw import blending_draw

RGBA = Tuple[int, int, int, int]
Point = Tuple[float, float]

TARGET_NAME = "solid_snake"
FRAME_SIZE = (128, 128)
SUPER = 4
CANVAS_W = FRAME_SIZE[0] * SUPER
CANVAS_H = FRAME_SIZE[1] * SUPER
ROWS: List[Tuple[str, int, int]] = [
    ("idle", 6, 140),
    ("walk", 8, 96),
    ("retreat", 6, 120),
    ("boxed_idle", 6, 140),
    ("peek", 6, 135),
    ("emerge", 6, 120),
    ("hiss", 6, 110),
    ("death", 6, 120),
]

TRANSPARENT = (0, 0, 0, 0)
OUTLINE = (24, 20, 16, 255)
SNAKE = (98, 152, 86, 255)
SNAKE_LIGHT = (150, 198, 118, 255)
SNAKE_DARK = (66, 112, 68, 255)
SNAKE_DEEP = (42, 78, 54, 255)
BELLY = (226, 216, 156, 255)
BELLY_DARK = (184, 168, 110, 255)
EYE = (24, 20, 18, 255)
EYE_GOLD = (246, 204, 70, 255)
TONGUE = (214, 70, 96, 255)
MOUTH = (176, 56, 80, 255)
FANG = (250, 246, 232, 255)
HISS = (244, 240, 218, 255)
BANDANA = (72, 96, 132, 255)
BANDANA_LIGHT = (118, 146, 184, 255)
BANDANA_DARK = (46, 62, 92, 255)
BOX = (198, 154, 98, 255)
BOX_LIGHT = (228, 192, 136, 255)
BOX_DARK = (152, 112, 68, 255)
BOX_DEEP = (124, 90, 54, 255)
TAPE = (236, 220, 178, 255)
TAPE_DARK = (198, 178, 132, 255)
BOX_MARK = (116, 78, 46, 255)
HOLE = (50, 34, 24, 255)

ACTOR_METADATA = {
    "actor": {"character_id": "npc_solid_snake", "display_name": "Solid Snake"},
    "body": {
        "body_plan": "Serpentine",
        "body_kind": "Snake",
        "mass_class": "Light",
        "traits": [
            "story",
            "serpent",
            "box_shell",
            "memey",
            "stealth_parody",
        ],
        "locomotion_hint": "Slither",
    },
    "capabilities": {
        "traversal": {
            "walk": True,
            "jump": None,
            "climb": None,
            "fly": None,
            "swim": None,
            "crawl": True,
            "use_lifts": False,
            "door_access": None,
        },
        "interactions": {
            "talk": False,
            "trade": None,
            "carry": None,
            "open_doors": None,
        },
    },
    "brain": {"default_preset": "patrol_peaceful"},
    "actions": {"default_preset": "peaceful"},
    "visual": {
        "default_pose": "idle",
        "portrait": {"animation": "idle", "frame": 2},
    },
    "tags": ["story", "serpent", "box_shell", "stealth_parody"],
    "animation_bindings": {
        "default": {"animation": "idle", "events": []},
        "locomotion.walk": {"animation": "walk", "events": []},
        "ability.hide": {"animation": "retreat", "events": []},
        "ability.hidden_idle": {"animation": "boxed_idle", "events": []},
        "ability.peek": {"animation": "peek", "events": []},
        "ability.emerge": {"animation": "emerge", "events": []},
        "combat.hurt": {"animation": "retreat", "events": []},
        "combat.death": {"animation": "death", "events": []},
    },
    "dialogue_hints": {
        "barks": [
            "Hiss.",
            "The box is the shell.",
            "Sneaking is easier when nobody respects the disguise.",
        ]
    },
}


ACTOR_METADATA.update(
    {
        "authoring_description": (
            "Solid Snake is a literal snake carrying a cardboard box, parodying the stealth-game hero "
            "Solid Snake while also filling the gameplay role of a shell-bearing platform enemy. It "
            "should evoke the famous box disguise without becoming a human imitation of the "
            "copyrighted character."
        ),
        "gameplay_description": (
            "Use as a sneaky crawling enemy that retreats into its box when threatened, waits, peeks, "
            "and re-emerges. The box is simultaneously disguise, shell, defense state, and the entire "
            "visual punchline."
        ),
    }
)
ACTOR_METADATA.setdefault("dialogue_hints", {}).setdefault(
    "barks",
    [
        'Hiss.',
        'The box is the shell.',
        'Sneaking is easier when nobody respects the disguise.',
    ],
)


def _s(v: float) -> int:
    return int(round(v * SUPER))


def _pt(x: float, y: float) -> Tuple[int, int]:
    return (_s(x), _s(y))


def _bbox(cx: float, cy: float, rx: float, ry: float) -> Tuple[int, int, int, int]:
    return (_s(cx - rx), _s(cy - ry), _s(cx + rx), _s(cy + ry))


def _draw_line(draw: ImageDraw.ImageDraw, pts: Iterable[Point], fill: RGBA, width: float) -> None:
    draw.line([_pt(x, y) for x, y in pts], fill=fill, width=max(1, _s(width)), joint="curve")


def _poly(
    draw: ImageDraw.ImageDraw,
    pts: Sequence[Point],
    fill: RGBA,
    outline: RGBA | None = OUTLINE,
    width: float = 1.0,
) -> None:
    ipts = [_pt(x, y) for x, y in pts]
    draw.polygon(ipts, fill=fill)
    if outline is not None:
        draw.line(ipts + [ipts[0]], fill=outline, width=max(1, _s(width)), joint="curve")


def _circle(
    draw: ImageDraw.ImageDraw,
    p: Point,
    r: float,
    fill: RGBA,
    outline: RGBA | None = OUTLINE,
    width: float = 1.0,
) -> None:
    draw.ellipse(_bbox(p[0], p[1], r, r), fill=fill, outline=outline, width=max(1, _s(width)) if outline else 0)


def _ellipse(draw: ImageDraw.ImageDraw, p: Point, rx: float, ry: float, fill: RGBA) -> None:
    draw.ellipse(_bbox(p[0], p[1], rx, ry), fill=fill)


def _downsample(img: Image.Image) -> Image.Image:
    return rigdoc.downsampled_canvas(img, FRAME_SIZE, Image.Resampling.LANCZOS)


def _mix(a: RGBA, b: RGBA, t: float) -> RGBA:
    return tuple(int(round(a[i] * (1.0 - t) + b[i] * t)) for i in range(4))  # type: ignore[return-value]


def _phase(frame_idx: int, nframes: int) -> float:
    return math.tau * (frame_idx / max(1, nframes))


def _smooth(a: float, b: float, t: float) -> float:
    u = min(1.0, max(0.0, (t - a) / (b - a)))
    return u * u * (3.0 - 2.0 * u)


def _snake_curve(anim: str, frame_idx: int, nframes: int) -> tuple[list[Point], Point, Point, float]:
    ph = _phase(frame_idx, nframes)
    pts: list[Point] = []
    if anim == "death":
        for i in range(16):
            x = 28.0 + i * 5.3
            y = 84.0 + 1.4 * math.sin(i * 0.8) + i * 0.55
            pts.append((x, y))
        neck = (104.0, 88.0)
        head = (113.0, 91.0)
        angle = 0.42
        return pts, neck, head, angle

    if anim == "walk":
        amp = 8.0
        lift = 0.0
        slither = ph
    elif anim == "hiss":
        amp = 5.5
        lift = -1.5
        slither = ph * 0.35
    elif anim == "emerge":
        amp = 4.0
        lift = -1.0
        slither = ph * 0.30
    else:
        amp = 4.0
        lift = 0.0
        slither = ph * 0.45

    for i in range(16):
        t = i / 15.0
        x = 22.0 + t * 78.0
        sway = math.sin(t * 2.5 * math.pi + slither) * amp
        taper = 1.0 - 0.25 * t
        y = 81.0 + sway * taper + lift - t * 2.0
        pts.append((x, y))

    neck_base = pts[-1]
    if anim == "hiss":
        neck = (neck_base[0] + 7.0, neck_base[1] - 17.0)
        head = (neck[0] + 8.5, neck[1] - 4.0)
        angle = -0.35
    else:
        neck = (neck_base[0] + 7.0, neck_base[1] - 10.0)
        head = (neck[0] + 8.0, neck[1] - 1.5)
        angle = -0.10 if anim in {"walk", "emerge"} else -0.05
    return pts, neck, head, angle


def _body_width(t: float) -> float:
    """The body's width ``t`` of the way from the tip of the tail to the
    head: a thin tail, a thick middle, a narrower neck."""
    return round(3.2 + 11.6 * _smooth(0.0, 0.3, t) - 5.2 * _smooth(0.68, 1.0, t), 2)


# ---- Pieces ------------------------------------------------------------------
#
# The snake is drawn as a rig: each body segment is one piece per (segment,
# quarter pixel of length), turned to the segment; the box, the head, the
# bandana's tails, the tongue are pieces placed where they sit. A part
# flipbook stores each once.
#
# A body segment is a tapered capsule along +x with the body's bands across
# it: a highlight near the back, the scales, a shade, the belly. The ends are
# round and each segment covers the end of the one before it, so the bands run
# on round a bend. All the outlines are placed first, then all the segments,
# then the dark saddles of the pattern.

#: Where a piece's anchor is painted on the scratch canvas (frame pixels);
#: the canvas is twice it.
HOME = (64.0, 64.0)
_PIECES: Dict[tuple, object] = {}


def _cut(canvas: Image.Image):
    box = canvas.getchannel("A").getbbox()
    return None if box is None else (canvas.crop(box), (HOME[0] * SUPER - box[0], HOME[1] * SUPER - box[1]))


def _scratch() -> Image.Image:
    return Image.new("RGBA", (int(2 * HOME[0] * SUPER), int(2 * HOME[1] * SUPER)), TRANSPARENT)


def _piece(key: tuple, paint):
    """``(raster, anchor)``: what ``paint(draw)`` paints with its anchor at
    ``HOME``, cut to its box; ``None`` when it paints nothing."""
    if key not in _PIECES:
        canvas = _scratch()
        paint(blending_draw(canvas))
        _PIECES[key] = _cut(canvas)
    return _PIECES[key]


def _put(img: Image.Image, key: tuple, paint, at: Point, name: str, degrees: float = 0.0) -> None:
    part = _piece(key, paint)
    if part is not None:
        shape_rig.place(img, part, (at[0] * SUPER, at[1] * SUPER), degrees, name)


def _capsule_points(length: float, ra: float, rb: float, grow: float = 0.0) -> List[Point]:
    """The outline of a tapered capsule from ``HOME`` along +x: a half circle
    of radius ``ra`` at the start, one of ``rb`` at the end."""
    hx, hy = HOME
    ra, rb = ra + grow, rb + grow
    pts: List[Point] = []
    for k in range(13):
        a = math.pi * 0.5 + math.pi * k / 12.0
        pts.append((hx + ra * math.cos(a), hy + ra * math.sin(a)))
    for k in range(13):
        a = -math.pi * 0.5 + math.pi * k / 12.0
        pts.append((hx + length + rb * math.cos(a), hy + rb * math.sin(a)))
    return pts


#: The bands across the body, as (from, to, colour) in parts of the half
#: width: -1 is the back, +1 the belly side.
BANDS: Sequence[Tuple[float, float, RGBA]] = (
    (-0.74, -0.42, SNAKE_LIGHT),
    (0.18, 0.46, SNAKE_DARK),
    (0.46, 1.2, BELLY),
    (0.80, 1.2, BELLY_DARK),
)


def _segment_piece(length: float, ra: float, rb: float):
    key = ("segment", length, ra, rb)
    if key not in _PIECES:
        hx, hy = HOME
        shape = _scratch()
        blending_draw(shape).polygon([_pt(x, y) for x, y in _capsule_points(length, ra, rb)], fill=SNAKE)
        bands = _scratch()
        d = blending_draw(bands)
        x0, x1 = hx - ra - 1.0, hx + length + rb + 1.0

        def half(x: float) -> float:
            return ra + (rb - ra) * (x - hx) / max(length, 0.25)

        for lo, hi, colour in BANDS:
            d.polygon([_pt(x0, hy + lo * half(x0)), _pt(x1, hy + lo * half(x1)), _pt(x1, hy + hi * half(x1)),
                       _pt(x0, hy + hi * half(x0))], fill=colour)
        # The bands only where the capsule is.
        alpha = ImageChops.multiply(bands.getchannel("A"), shape.getchannel("A"))
        shape.paste(bands, (0, 0), alpha)
        _PIECES[key] = _cut(shape)
    return _PIECES[key]


def _turn(a: Point, b: Point) -> float:
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def _length(a: Point, b: Point) -> float:
    return round(math.hypot(b[0] - a[0], b[1] - a[1]) * 4) / 4


def _put_outline(img: Image.Image, a: Point, b: Point, wa: float, wb: float, name: str) -> None:
    length = _length(a, b)
    _put(img, ("outline", length, wa, wb),
         lambda d: d.polygon([_pt(x, y) for x, y in _capsule_points(length, wa * 0.5, wb * 0.5, 1.15)], fill=OUTLINE),
         a, name, _turn(a, b))


def _put_segment(img: Image.Image, a: Point, b: Point, wa: float, wb: float, name: str) -> None:
    part = _segment_piece(_length(a, b), wa * 0.5, wb * 0.5)
    if part is not None:
        shape_rig.place(img, part, (a[0] * SUPER, a[1] * SUPER), _turn(a, b), name)


def _put_saddle(img: Image.Image, a: Point, b: Point, wa: float, wb: float, name: str) -> None:
    """A dark saddle of the pattern: a wedge down from the back, over one segment."""
    length = _length(a, b)
    hx, hy = HOME

    def paint(d) -> None:
        ra, rb = wa * 0.5, wb * 0.5
        mid = 0.5 * (ra + rb)
        d.polygon([_pt(hx - 0.6, hy - ra), _pt(hx + length + 0.6, hy - rb), _pt(hx + length * 0.5 + 1.2, hy + 0.12 * mid),
                   _pt(hx + length * 0.5 - 1.2, hy + 0.12 * mid)], fill=SNAKE_DEEP)
        d.polygon([_pt(hx + length * 0.5 - 1.1, hy - 0.62 * mid), _pt(hx + length * 0.5 + 1.1, hy - 0.62 * mid),
                   _pt(hx + length * 0.5, hy - 0.2 * mid)], fill=SNAKE_DARK)

    _put(img, ("saddle", length, wa, wb), paint, a, name, _turn(a, b))


def _put_chain(img: Image.Image, chain: Sequence[Point], widths: Sequence[float], saddles: Iterable[int] = ()) -> None:
    """A run of body through ``chain``, ``widths[i]`` wide at ``chain[i]``."""
    spans = range(len(chain) - 1)
    for i in spans:
        _put_outline(img, chain[i], chain[i + 1], widths[i], widths[i + 1], f"outline_{i}")
    for i in spans:
        _put_segment(img, chain[i], chain[i + 1], widths[i], widths[i + 1], f"segment_{i}")
    for i in saddles:
        _put_saddle(img, chain[i], chain[i + 1], widths[i], widths[i + 1], f"saddle_{i}")


# ---- The box -----------------------------------------------------------------

#: The box's front face (frame pixels), and how far its top and side go back.
BOX_W, BOX_H, BOX_BACK = 34.0, 26.0, (7.0, -6.0)


def _draw_box(img: Image.Image, cx: float, cy: float, wobble: float = 0.0, eyes: bool = False, tilt: float = 0.0) -> None:
    """The box, as one piece, placed by the low left corner of its front
    face. ``tilt`` (degrees) lifts its right side about that corner; ``eyes``
    puts two eyes in its hand hole."""
    _put(img, ("box", eyes), lambda d: _paint_box(d, eyes), (cx - 20.0 + wobble, cy + 15.0), "box", -tilt)


def _paint_box(draw: ImageDraw.ImageDraw, eyes: bool) -> None:
    hx, hy = HOME
    bx, by = BOX_BACK
    left, right, top, bottom = hx, hx + BOX_W, hy - BOX_H, hy
    # The side and the top, then the front.
    _poly(draw, [(right, top), (right + bx, top + by), (right + bx, bottom + by), (right, bottom)], BOX_DARK, OUTLINE, 1.0)
    _poly(draw, [(right + 0.6, bottom - 9.0), (right + bx - 0.6, bottom + by - 9.0), (right + bx - 0.6, bottom + by - 0.8),
                 (right + 0.6, bottom - 0.8)], BOX_DEEP, None)
    _poly(draw, [(left, top), (left + bx, top + by), (right + bx, top + by), (right, top)], BOX_LIGHT, OUTLINE, 1.0)
    _poly(draw, [(left, top), (right, top), (right, bottom), (left, bottom)], BOX, OUTLINE, 1.0)
    # Corrugated board: faint flutes down the front, a worn low edge.
    flute = _mix(BOX, BOX_DARK, 0.28)
    for k in range(1, 11):
        x = left + k * BOX_W / 11.0
        _draw_line(draw, [(x, top + 1.4), (x, bottom - 1.2)], flute, 0.35)
    _poly(draw, [(left + 0.6, bottom - 3.0), (right - 0.6, bottom - 3.0), (right - 0.6, bottom - 0.6), (left + 0.6, bottom - 0.6)],
          _mix(BOX, BOX_DARK, 0.5), None)
    _draw_line(draw, [(left + 1.0, top + 1.1), (right - 1.0, top + 1.1)], BOX_LIGHT, 0.6)
    # The flaps of the top meet in the middle; the tape goes along the seam
    # and down over the front edge.
    _draw_line(draw, [(left + bx * 0.5 + 0.8, top + by * 0.5), (right + bx * 0.5 - 0.8, top + by * 0.5)], BOX_DARK, 0.6)
    tape_x = left + 14.0
    _poly(draw, [(tape_x + bx * 0.9, top + by * 0.9), (tape_x + 6.0 + bx * 0.9, top + by * 0.9), (tape_x + 6.0, top),
                 (tape_x, top)], TAPE, None)
    _poly(draw, [(tape_x, top), (tape_x + 6.0, top), (tape_x + 6.0, top + 6.4), (tape_x + 4.4, top + 7.4), (tape_x + 2.6, top + 6.2),
                 (tape_x + 1.2, top + 7.2), (tape_x, top + 6.0)], TAPE, None)
    _draw_line(draw, [(tape_x + 4.4, top + 0.6), (tape_x + 4.4, top + 6.2)], TAPE_DARK, 0.5)
    _draw_line(draw, [(left, top), (right, top)], OUTLINE, 0.8)
    # The hand hole.
    hole = (left + 4.0, top + 12.0, left + 13.0, top + 16.0)
    draw.rounded_rectangle((_s(hole[0]), _s(hole[1]), _s(hole[2]), _s(hole[3])), radius=_s(1.8), fill=HOLE, outline=OUTLINE,
                           width=max(1, _s(0.6)))
    if eyes:
        for ex in (hole[0] + 2.6, hole[0] + 6.2):
            _ellipse(draw, (ex, top + 14.0), 1.15, 1.25, EYE_GOLD)
            _ellipse(draw, (ex + 0.2, top + 14.0), 0.35, 1.0, EYE)
    # "This side up": two arrows over a bar.
    for ax in (left + 22.0, left + 28.0):
        _draw_line(draw, [(ax, top + 18.6), (ax, top + 13.2)], BOX_MARK, 0.9)
        _poly(draw, [(ax - 2.2, top + 13.6), (ax, top + 10.6), (ax + 2.2, top + 13.6)], BOX_MARK, None)
    _draw_line(draw, [(left + 19.4, top + 20.4), (left + 30.6, top + 20.4)], BOX_MARK, 0.9)


# ---- The head ----------------------------------------------------------------


def _paint_head(draw: ImageDraw.ImageDraw, k: float = 1.0, look: str = "open") -> None:
    """The head, its centre at ``HOME``, ``k`` its size. ``look`` is ``open``,
    ``hiss`` (the mouth wide, the fangs out) or ``dead``."""
    hx, hy = HOME

    def P(x: float, y: float) -> Point:
        return (hx + x * k, hy + y * k)

    if look == "hiss":
        # The low jaw and the inside of the mouth, under the skull.
        _poly(draw, [P(-8.0, 2.0), P(2.0, 1.4), P(11.6, 5.6), P(10.6, 8.2), P(4.0, 9.2), P(-3.0, 7.6), P(-8.4, 4.8)], BELLY, OUTLINE,
              0.9 * k)
        _poly(draw, [P(1.0, 0.6), P(13.0, -1.6), P(11.0, 5.4), P(2.4, 2.2)], MOUTH, OUTLINE, 0.6 * k)
        skull = [P(-9.0, -5.5), P(-3.0, -8.2), P(4.0, -8.0), P(10.4, -6.2), P(14.2, -3.6), P(13.2, -1.4), P(2.0, 0.8), P(-8.0, 2.4),
                 P(-10.2, 0.0)]
        _poly(draw, skull, SNAKE, OUTLINE, 1.0 * k)
        for fx in (11.6, 8.6):
            _poly(draw, [P(fx - 0.9, -1.2), P(fx + 0.7, -1.5), P(fx + 0.2, 2.4)], FANG, OUTLINE, 0.35 * k)
        eye_y = -3.4
    else:
        skull = [P(-9.0, -5.5), P(-3.0, -8.0), P(4.0, -7.6), P(10.0, -4.6), P(13.6, -0.6), P(12.6, 3.0), P(6.0, 6.0), P(-2.0, 6.6),
                 P(-8.0, 4.2), P(-10.2, 0.0)]
        _poly(draw, skull, SNAKE, OUTLINE, 1.0 * k)
        _poly(draw, [P(-8.0, 2.6), P(4.0, 2.2), P(12.8, 1.4), P(12.2, 3.0), P(6.0, 5.6), P(-2.0, 6.2), P(-7.6, 4.0)], BELLY, None)
        # The mouth, with the corner turned up.
        _draw_line(draw, [P(13.2, 1.3), P(6.0, 2.3), P(1.6, 2.0), P(0.2, 0.8)], OUTLINE, 0.7 * k)
        eye_y = -2.6
    _draw_line(draw, [P(-6.0, -5.0), P(3.0, -6.2), P(9.0, -3.9)], SNAKE_LIGHT, 0.9 * k)
    _ellipse(draw, P(11.4, -1.9 if look != "hiss" else -3.6), 0.5 * k, 0.45 * k, SNAKE_DEEP)
    # The bandana: a band round the head behind the eye, tied at the back.
    band = [P(-6.4, -7.0), P(-2.4, -8.4), P(-1.0, 2.4 if look == "hiss" else 6.6), P(-5.4, 3.0 if look == "hiss" else 6.0)]
    _poly(draw, band, BANDANA, OUTLINE, 0.7 * k)
    _draw_line(draw, [P(-4.6, -6.6), P(-3.6, 1.6 if look == "hiss" else 5.2)], BANDANA_LIGHT, 0.7 * k)
    # The eye, under a heavy brow.
    ex, ey = 5.0, eye_y
    if look == "dead":
        for dx in (-1.0, 1.0):
            _draw_line(draw, [P(ex - 1.8, ey - 1.8 * dx), P(ex + 1.8, ey + 1.8 * dx)], OUTLINE, 0.8 * k)
    else:
        draw.ellipse(_bbox(hx + ex * k, hy + ey * k, 2.5 * k, 2.3 * k), fill=EYE_GOLD, outline=OUTLINE, width=max(1, _s(0.55 * k)))
        _ellipse(draw, P(ex + 0.5, ey + 0.1), 0.7 * k, 1.9 * k, EYE)
        _ellipse(draw, P(ex - 0.8, ey - 0.9), 0.5 * k, 0.5 * k, (255, 255, 255, 255))
        _poly(draw, [P(ex - 3.6, ey - 3.4), P(ex + 3.6, ey - 1.5), P(ex + 3.4, ey - 0.4), P(ex - 3.4, ey - 2.0)], SNAKE_DEEP, OUTLINE,
              0.45 * k)


def _put_head(img: Image.Image, head: Point, flutter: float, k: float = 1.0, look: str = "open", degrees: float = 0.0) -> None:
    """The head, with the two tails of the bandana behind it."""
    hx, hy = HOME
    flutter = round(flutter, 2)

    def tails(d) -> None:
        root = (hx - 4.4 * k, hy - 7.2 * k)
        for dy, reach, sway in ((-2.6, 13.0, 1.0), (2.4, 11.0, -1.0)):
            mid = (root[0] - 0.5 * reach * k, root[1] + (0.5 * dy - 1.6 * flutter * sway) * k)
            tip = (root[0] - reach * k, root[1] + (dy + 2.6 * flutter * sway) * k)
            _draw_line(d, [root, mid, tip], OUTLINE, 3.6 * k)
            _draw_line(d, [root, mid, tip], BANDANA, 2.2 * k)
            _draw_line(d, [mid, tip], BANDANA_DARK, 0.8 * k)
        _circle(d, root, 1.7 * k, BANDANA_DARK, OUTLINE, 0.6 * k)

    _put(img, ("tails", k, flutter), tails, head, "bandana", degrees)
    _put(img, ("head", k, look), lambda d: _paint_head(d, k, look), head, "head", degrees)


def _draw_body(img: Image.Image, pts: list[Point], neck: Point, head: Point, flutter: float, look: str = "open") -> None:
    chain = pts + [neck]
    n = len(chain)
    widths = [_body_width(i / (n - 1)) for i in range(n)]
    _put_chain(img, chain, widths, saddles=range(3, n - 2, 2))
    _put_head(img, head, flutter, 1.0, look, degrees=18.0 if look == "dead" else 0.0)


def _draw_tongue(img: Image.Image, head: Point, length: float = 7.5, drop: float = 1.0, degrees: float = 0.0) -> None:
    length = round(length, 2)
    hx, hy = HOME

    def paint(d) -> None:
        mid = (hx + 12.6, hy + drop)
        tip = (hx + 12.6 + length, hy + drop - 0.7)
        _draw_line(d, [mid, tip], TONGUE, 0.9)
        _draw_line(d, [tip, (tip[0] + 1.8, tip[1] - 1.7)], TONGUE, 0.5)
        _draw_line(d, [tip, (tip[0] + 1.8, tip[1] + 1.7)], TONGUE, 0.5)

    _put(img, ("tongue", length, drop), paint, head, "tongue", degrees)


def _draw_back_box_snake(img: Image.Image, anim: str, frame_idx: int, nframes: int) -> tuple[list[Point], Point, Point, Point]:
    pts, neck, head, _ = _snake_curve(anim, frame_idx, nframes)
    ph = _phase(frame_idx, nframes)
    look = {"hiss": "hiss", "death": "dead"}.get(anim, "open")
    # The head is longer than the one the curve was made for: it sits back
    # on its neck, so that its snout stays in the frame.
    head = (head[0] - {"hiss": 6.5, "death": 5.5}.get(anim, 4.5), head[1] - (2.0 if anim == "death" else 0.0))
    if anim == "hiss":
        # The tongue is under the head: it comes out of the open mouth.
        _draw_tongue(img, head, 2.6 + 0.8 * math.sin(ph), drop=1.6, degrees=24.0)
    _draw_body(img, pts, neck, head, 0.0 if anim == "death" else math.sin(ph + 0.6), look)
    box_anchor = pts[7]
    wobble = math.sin(ph) * (1.2 if anim == "walk" else 0.4)
    _draw_box(img, box_anchor[0] + 5.0, box_anchor[1] - 13.5, wobble=wobble)
    hx, hy = HOME

    def straps(d) -> None:
        for colour, width in ((OUTLINE, 1.9), (TAPE, 1.1)):
            _draw_line(d, [(hx - 9.0, hy - 5.0), (hx - 10.0, hy + 4.4)], colour, width)
            _draw_line(d, [(hx + 15.0, hy - 5.0), (hx + 16.0, hy + 4.4)], colour, width)

    _put(img, ("straps",), straps, box_anchor, "straps")
    return pts, neck, head, box_anchor


def _draw_short_snake(img: Image.Image, tail: Point, mid: Point, head: Point, visible: float, flutter: float) -> None:
    """The snake half out of the box (retreat / emerge): two segments and its head."""
    widths = [round(w * (0.85 + 0.15 * visible), 2) for w in (8.4, 7.4, 6.4)]
    _put_chain(img, [tail, mid, head], widths)
    _put_head(img, (head[0] - 1.5, head[1] - 0.6), flutter, 0.74)


def _box_and_snake(img: Image.Image, frame_idx: int, nframes: int, visible: float, wobble: float) -> None:
    """The snake part of the way out of the right side of its box; the box is over its tail."""
    ph = _phase(frame_idx, nframes)
    if visible > 0.0:
        entry = (84.0 + wobble, 83.5)
        tail = (entry[0] - 3.0, 84.6)
        mid = (entry[0] + 8.0 + 10.0 * visible, 84.0 + math.sin(ph) * 1.2)
        head = (entry[0] + 13.0 + 19.0 * visible, 81.5 - 4.5 * visible)
        _draw_short_snake(img, tail, mid, head, visible, math.sin(ph + 0.6))
    _draw_box(img, 67.0, 74.0, wobble=wobble)


def _draw_retreat_frame(img: Image.Image, frame_idx: int, nframes: int) -> None:
    progress = frame_idx / max(1, nframes - 1)
    retreat_end = 0.82
    visible = 0.0 if progress >= retreat_end else 1.0 - (progress / retreat_end)
    _box_and_snake(img, frame_idx, nframes, visible, math.sin(_phase(frame_idx, nframes)) * 0.45)


def _draw_boxed_idle(img: Image.Image, frame_idx: int, nframes: int) -> None:
    ph = _phase(frame_idx, nframes)
    # Its eyes are in the hand hole for two frames of the six: it looks, and it is a box again.
    _draw_box(img, 67.0, 74.0, wobble=math.sin(ph) * 0.45, eyes=frame_idx % max(1, nframes) in (2, 3))


def _draw_peek(img: Image.Image, frame_idx: int, nframes: int) -> None:
    """The box lifts on its right side and the head looks out from under it."""
    ph = _phase(frame_idx, nframes)
    t = frame_idx / max(1, nframes - 1)
    peek = 0.22 + 0.72 * (0.5 - 0.5 * math.cos(math.pi * t))
    head = (84.0 + 7.0 * peek, 84.6 - 1.4 * peek)
    if peek > 0.55:
        _draw_tongue(img, (head[0] - 3.0, head[1]), 4.0 + 2.0 * math.sin(ph), drop=1.4)
    _put_head(img, head, 0.0, 0.74)
    _draw_box(img, 67.0, 74.0, wobble=math.sin(ph) * 0.35, tilt=round(7.0 * peek, 1))


def _draw_emerge(img: Image.Image, frame_idx: int, nframes: int) -> None:
    visible = frame_idx / max(1, nframes - 1)
    _box_and_snake(img, frame_idx, nframes, max(visible, 0.02), math.sin(_phase(frame_idx, nframes)) * 0.30)


def _render_frame(anim: str, frame_idx: int, nframes: int) -> Image.Image:
    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), TRANSPARENT)

    if anim == "retreat":
        _draw_retreat_frame(img, frame_idx, nframes)
        return _downsample(img)
    if anim == "boxed_idle":
        _draw_boxed_idle(img, frame_idx, nframes)
        return _downsample(img)
    if anim == "peek":
        _draw_peek(img, frame_idx, nframes)
        return _downsample(img)
    if anim == "emerge":
        _draw_emerge(img, frame_idx, nframes)
        return _downsample(img)

    pts, neck, head, box_anchor = _draw_back_box_snake(img, anim, frame_idx, nframes)
    hx, hy = HOME

    if anim == "hiss":
        wave = round(math.sin(_phase(frame_idx, nframes)) * 1.2, 3)

        def rings(d) -> None:
            for i in range(2):
                r = 4.0 + i * 3.0 + 0.4 * wave
                d.arc(_bbox(hx + 10.0, hy + 1.0, r, r * 0.9), start=300, end=40, fill=HISS, width=max(1, _s(0.8)))

        _put(img, ("hiss", wave), rings, head, "hiss")
    elif anim == "idle" and frame_idx % max(1, nframes // 3) == 1:
        _draw_tongue(img, head, 1.4)
    elif anim == "death":
        _draw_tongue(img, (head[0] - 3.0, head[1] + 3.0), 2.0, drop=2.0)

    return _downsample(img)


def render(out_dir: str | Path, **opts) -> List[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frame_transform: dict = {}
    outputs = build_sheet(
        frame_transform_out=frame_transform,
        target=TARGET_NAME,
        rows=ROWS,
        render_fn=lambda anim, frame_idx, nframes: _render_frame(anim, frame_idx, nframes),
        out_dir=out_dir,
        frame_size=opts.get("frame_size", FRAME_SIZE),
        auto_crop=False,
        actor_metadata=ACTOR_METADATA,
        # The snake's silhouette CHANGES SHAPE between poses more than almost
        # any other body in the tree: sprawled it is a long low serpent, boxed
        # it is a small cardboard cube. Publishing per-row hurtboxes is what
        # lets the runtime take its collision + hurt box FROM THE ART for the
        # pose it is actually showing, instead of one idle-frame box that is
        # wrong for half the withdraw cycle. Row names are the gameplay keys
        # here (the runtime maps them through `CharacterAnim::from_name`), so
        # the identity map is the honest mapping.
        animation_key_map={name: name for name, _frames, _duration in ROWS},
    )
    parts = publish_rig_flipbook(TARGET_NAME, ROWS, _render_frame, outputs, frame_transform, out_dir)
    return [
        outputs["spritesheet"],
        outputs["yaml"],
        outputs["ron"],
        outputs["actor"],
        outputs["preview"],
        outputs["canonical"],
        outputs["canonical_transparent"],
    ] + list(parts.values())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the Solid Snake sprite target.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "generated" / TARGET_NAME,
    )
    args = parser.parse_args(argv)
    for path in render(args.out_dir):
        print(path)
    return 0


TARGETS = {TARGET_NAME: {"render": render, "actor_metadata": ACTOR_METADATA}}


if __name__ == "__main__":
    raise SystemExit(main())
