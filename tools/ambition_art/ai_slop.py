"""Sprite generator for AI Slop: a heap of generated goo that wants a like.

The look (redrawn 2026-10-11): a glossy heap in the gradient every AI
product is sold in (violet over orchid over pink over peach), whose bands
flow and run while it stands. The heap is three lumps of unequal size on a
spill with drops beside it. It is not a smooth dome with one tip on a neat
rim: that shape was read as another thing (Jon, 2026-10-11). It has the marks of a generated picture: two eyes that
do not match and do not blink together, a third eye where no eye belongs, a
smile with too many teeth, a hand with seven fingers that waves from its
back, a stock picture sunk in its side, files that it made and that nobody
asked for afloat in it (a Python file, a Rust file, a Markdown file), and
sparkles. It faces right.

It walks by oozing: the front runs forward and the heap sinks, the rear
catches up and the heap rises. Its swipe is the hand, thrown over its head.
Struck, it squashes and tears in strips like a broken video frame. Dead, it
melts into a puddle and the hand goes under last, with both of its thumbs up.

The gameplay body is the heap where it is high (``_body_metrics``): the hand,
the picture and the sparkles do not make it larger, and the thin skirt of the
puddle at each side does not make it wider.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from PIL import Image, ImageChops, ImageFilter

from . import rigdoc, shape_rig
from .draw import blending_draw

RGBA = Tuple[int, int, int, int]
Point = Tuple[float, float]

TARGET_NAME = "ai_slop"
FRAME_SIZE = (192, 160)
SUPER = 4
CANVAS = (FRAME_SIZE[0] * SUPER, FRAME_SIZE[1] * SUPER)
#: Row names are the ones the game reads (`CharacterAnim::from_name`).
ROWS: List[Tuple[str, int, int]] = [
    ("idle", 6, 130),
    ("walk", 8, 95),
    ("slash", 6, 80),
    ("hurt", 4, 90),
    ("death", 8, 110),
]

#: The ground line and the middle of the heap (frame pixels).
GROUND = 148.0
CX = 92.0
#: The heap at rest: half its width at the ground, its height, and the height
#: of the curl on its top.
REST_W, REST_H, REST_TIP = 54.0, 84.0, 1.0

TRANSPARENT = (0, 0, 0, 0)
OUTLINE = (34, 22, 48, 255)
VIOLET = (140, 116, 244, 255)
ORCHID = (204, 118, 236, 255)
PINK = (255, 126, 188, 255)
PEACH = (255, 176, 132, 255)
SHADE = (88, 46, 150, 255)
WHITE = (255, 255, 255, 255)
EYE_WHITE = (252, 250, 255, 255)
IRIS = (104, 76, 206, 255)
PUPIL = (38, 24, 84, 255)
MOUTH = (92, 28, 74, 255)
TOOTH = (255, 252, 240, 255)
TOOTH_LINE = (196, 172, 196, 255)
TONGUE = (255, 112, 150, 255)
SKIN = (250, 222, 200, 255)
SKIN_SHADE = (226, 180, 160, 255)
SPARK = (255, 232, 132, 255)
SPARK_CORE = (255, 255, 236, 255)
CARD = (248, 248, 252, 255)
CARD_SKY = (126, 196, 255, 255)
CARD_SUN = (255, 222, 92, 255)
CARD_HILL = (94, 190, 132, 255)
CARD_HILL_DARK = (62, 150, 116, 255)

ACTOR_METADATA = {
    "actor": {"character_id": "npc_ai_slop", "display_name": "AI Slop"},
    "body": {
        "body_plan": "Crawler",
        "body_kind": "Wide",
        "mass_class": "Heavy",
        "traits": ["ai_era", "sludge", "enemy", "no_hands"],
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
            "use_lifts": None,
            "door_access": [],
        },
        "interactions": {"talk": None, "trade": None, "carry": None, "open_doors": []},
    },
    "brain": {"default_preset": "wanderer_puppy_slug"},
    "actions": {"default_preset": "zombie_bite"},
    "visual": {"default_pose": "idle", "portrait": {"animation": "idle", "frame": 0}},
    "tags": ["ai_era", "enemy", "crawler", "no_hands"],
    "sockets": {
        "mouth": {"source": "explicit.profile.ai_slop", "point": {"x": 107.0, "y": 116.0}},
        "center": {"source": "explicit.profile.ai_slop", "point": {"x": 92.0, "y": 104.0}},
    },
    "animation_bindings": {
        "default": {"animation": "idle", "events": []},
        "locomotion.walk": {"animation": "walk", "events": []},
        "action.melee.primary": {
            "animation": "slash",
            "events": [
                {"t": 0.35, "event": "hitbox_active_start", "source": "explicit.profile.ai_slop"},
                {"t": 0.6, "event": "hitbox_active_end", "source": "explicit.profile.ai_slop"},
            ],
        },
        "combat.hurt": {"animation": "hurt", "events": []},
        "combat.death": {"animation": "death", "events": []},
    },
    "authoring_description": (
        "AI Slop is a heap of generated goo in the gradient AI products are sold in. It carries "
        "the marks of a generated picture: eyes that do not match, a third eye, too many teeth, "
        "a hand with seven fingers, a stock picture sunk in its side, and sparkles."
    ),
    "gameplay_description": (
        "The plain walker: it oozes forward, turns at walls and hurts by touch. In Mary-O a "
        "stomp squashes it. Its one attack is a swipe of its hand."
    ),
}


def _s(v: float) -> int:
    return int(round(v * SUPER))


def _pt(p: Point) -> Tuple[int, int]:
    return (_s(p[0]), _s(p[1]))


def _box(cx: float, cy: float, rx: float, ry: float) -> Tuple[int, int, int, int]:
    return (_s(cx - rx), _s(cy - ry), _s(cx + rx), _s(cy + ry))


def _mix(a: RGBA, b: RGBA, t: float) -> RGBA:
    return tuple(int(round(a[i] * (1.0 - t) + b[i] * t)) for i in range(4))  # type: ignore[return-value]


def _line(d, pts: Sequence[Point], fill: RGBA, width: float) -> None:
    d.line([_pt(p) for p in pts], fill=fill, width=max(1, _s(width)), joint="curve")


def _poly(d, pts: Sequence[Point], fill: RGBA, outline: RGBA | None = OUTLINE, width: float = 1.0) -> None:
    ipts = [_pt(p) for p in pts]
    d.polygon(ipts, fill=fill)
    if outline is not None:
        d.line(ipts + [ipts[0]], fill=outline, width=max(1, _s(width)), joint="curve")


def _oval(d, c: Point, rx: float, ry: float, fill: RGBA, outline: RGBA | None = None, width: float = 1.0) -> None:
    d.ellipse(_box(c[0], c[1], rx, ry), fill=fill, outline=outline, width=max(1, _s(width)) if outline else 0)


def _capsule(d, a: Point, b: Point, width: float, fill: RGBA) -> None:
    _line(d, [a, b], fill, width)
    for p in (a, b):
        _oval(d, p, width / 2.0, width / 2.0, fill)


def _bezier(a: Point, b: Point, c: Point, e: Point, steps: int = 16) -> List[Point]:
    pts: List[Point] = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        w = (u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t)
        pts.append(tuple(w[0] * a[k] + w[1] * b[k] + w[2] * c[k] + w[3] * e[k] for k in (0, 1)))  # type: ignore[arg-type]
    return pts


def _star4(d, c: Point, r: float, fill: RGBA, outline: RGBA | None = OUTLINE, width: float = 0.9, waist: float = 0.26) -> None:
    """The four-pointed sparkle: long points up, down, left and right."""
    pts = []
    for i in range(8):
        a = math.radians(i * 45.0 - 90.0)
        rr = r if i % 2 == 0 else r * waist
        pts.append((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr))
    _poly(d, pts, fill, outline, width)


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 0.5 - 0.5 * math.cos(math.pi * t)


def _downsample(img: Image.Image) -> Image.Image:
    return rigdoc.downsampled_canvas(img, FRAME_SIZE, Image.Resampling.LANCZOS)


# ---- Pieces ------------------------------------------------------------------
#
# The heap is one piece for each shape it takes; everything on it (an eye, the
# mouth, the hand, the picture, a sparkle) is a piece painted once with its
# anchor at ``HOME`` and placed, and turned, where it sits. A part flipbook
# stores each once.

HOME = (float(FRAME_SIZE[0]), float(FRAME_SIZE[1]))
_PIECES: Dict[tuple, object] = {}


def _cut(canvas: Image.Image, anchor: Point):
    box = canvas.getchannel("A").getbbox()
    return None if box is None else (canvas.crop(box), (anchor[0] * SUPER - box[0], anchor[1] * SUPER - box[1]))


def _piece(key: tuple, paint):
    """``(raster, anchor)``: what ``paint(draw)`` paints with its anchor at
    ``HOME``, cut to its box; ``None`` when it paints nothing. ``key`` names
    everything ``paint`` reads."""
    if key not in _PIECES:
        canvas = Image.new("RGBA", (CANVAS[0] * 2, CANVAS[1] * 2), TRANSPARENT)
        paint(blending_draw(canvas))
        _PIECES[key] = _cut(canvas, HOME)
    return _PIECES[key]


def _put(img: Image.Image, key: tuple, paint, at: Point, name: str, degrees: float = 0.0) -> None:
    part = _piece(key, paint)
    if part is not None:
        shape_rig.place(img, part, (at[0] * SUPER, at[1] * SUPER), degrees, name)


# ---- The pose ----------------------------------------------------------------


def _pose(anim: str, i: int, n: int) -> Dict[str, object]:
    """Everything a frame is drawn from. Lengths are frame pixels; angles are
    degrees, clockwise, with 0 = the fingers up."""
    ph = math.tau * i / max(1, n)
    pose: Dict[str, object] = {
        "w": REST_W,
        "h": REST_H,
        "tip": REST_TIP,
        "lean": 5.0,
        "front": 0.0,
        "rear": 0.0,
        "flow": ph,
        "tear": (),
        "big_eye": "open",
        "small_eye": "open",
        "look": (1.2, 0.4),
        "mouth": ("grin", 0.0),
        "wrist": (-13.0, -30.0),
        "hand_turn": -12.0,
        "hand": "open",
        "arm_front": False,
        "card_turn": -22.0,
        "card_sink": 0.0,
        "sparkles": (1.0, 0.7, 0.8),
        "drops": (),
    }
    if anim == "idle":
        breath = math.sin(ph)
        pose.update(
            h=REST_H + 2.6 * breath,
            w=REST_W - 1.3 * breath,
            lean=5.0 + 0.9 * math.sin(ph + 1.0),
            # The eyes do not blink together.
            small_eye="closed" if i == 3 else "open",
            big_eye="closed" if i == 4 else "open",
            look=(1.2 + 0.8 * math.sin(ph), 0.4),
            wrist=(-13.0 + 2.0 * math.sin(ph), -30.0 - 1.5 * breath),
            hand_turn=-12.0 + 14.0 * math.sin(ph + 0.5),
            card_turn=-22.0 + 2.0 * math.sin(ph + 2.0),
            sparkles=tuple(0.72 + 0.28 * math.sin(ph * (1 if k != 1 else 2) + k * 2.1) for k in range(3)),
        )
    elif anim == "walk":
        reach = math.sin(ph)
        pose.update(
            w=REST_W + 5.0 * reach,
            h=REST_H - 7.5 * reach,
            lean=7.0 + 4.5 * math.sin(ph + 0.6),
            front=8.5 * max(0.0, reach),
            rear=7.0 * max(0.0, math.sin(ph - 1.1)),
            look=(1.8, 0.6 + 0.6 * reach),
            mouth=("grin", 0.15 + 0.15 * max(0.0, -reach)),
            wrist=(-13.0 - 4.0 * reach, -29.0 + 2.5 * math.cos(ph)),
            hand_turn=-10.0 + 24.0 * math.sin(ph + 1.2),
            card_turn=-22.0 + 5.0 * math.sin(ph + 2.0),
            sparkles=tuple(0.7 + 0.3 * math.sin(ph + k * 2.1) for k in range(3)),
            # A bead of it is left behind and sinks.
            drops=((-REST_W - 22.0 - 2.0 * (i - 4), 2.6 - 0.45 * (i - 4)),) if 4 <= i <= 7 else (),
        )
    elif anim == "slash":
        keys = [
            # w, h, lean, front, wrist, hand_turn, hand, front?, mouth
            (52.0, 88.0, -3.0, 0.0, (-26.0, -24.0), -44.0, "open", False, 0.25),
            (51.0, 91.0, -8.0, 0.0, (-36.0, -12.0), -76.0, "splay", False, 0.45),
            (57.0, 78.0, 13.0, 5.0, (40.0, -34.0), 44.0, "splay", True, 1.0),
            (59.0, 74.0, 17.0, 9.0, (67.0, 2.0), 104.0, "splay", True, 0.9),
            (56.0, 80.0, 11.0, 4.0, (40.0, -22.0), 50.0, "open", True, 0.5),
            (54.0, 85.0, 6.0, 0.0, (-4.0, -31.0), 2.0, "open", False, 0.2),
        ]
        w, h, lean, front, wrist, turn, hand, arm_front, opening = keys[i % len(keys)]
        pose.update(w=w, h=h, lean=lean, front=front, wrist=wrist, hand_turn=turn, hand=hand, arm_front=arm_front,
                    mouth=("grin", opening), look=(2.4, 0.2), card_turn=-22.0 - lean * 0.5,
                    # The hand goes through where the large sparkle was.
                    sparkles=(0.0 if 2 <= i <= 4 else 1.0, 0.5 + 0.1 * i, 0.9 - 0.1 * i))
        if i == 2:
            pose["drops"] = ((2.0, 112.0, 2.2), (-20.0, 106.0, 1.6))
        elif i == 3:
            pose["drops"] = ((46.0, 90.0, 2.0), (30.0, 102.0, 1.5))
    elif anim == "hurt":
        squash = (0.78, 0.70, 0.82, 0.93)[i % 4]
        pose.update(
            h=REST_H * squash,
            w=REST_W * (1.0 + (1.0 - squash) * 0.55),
            tip=squash,
            lean=(-6.0, -9.0, -5.0, 1.0)[i % 4],
            # Strips of it are out of place: (from, to, shift), heights as
            # parts of its height.
            tear=(((0.80, 0.93, 6.0), (0.10, 0.22, -7.0)), ((0.84, 0.98, -8.0), (0.06, 0.20, 6.0)),
                  ((0.82, 0.92, 4.0),), ())[i % 4],
            big_eye="squeeze" if i < 3 else "open",
            small_eye="wide",
            look=(0.0, 0.0),
            mouth=("wobble", (0.7, 0.9, 0.6, 0.3)[i % 4]),
            wrist=((-22.0, -24.0), (-4.0, -33.0), (-20.0, -27.0), (-12.0, -30.0))[i % 4],
            hand_turn=(-52.0, 26.0, -30.0, -6.0)[i % 4],
            hand="splay",
            card_turn=(-36.0, -44.0, -32.0, -24.0)[i % 4],
            sparkles=(0.0, 0.0, 0.0),
            drops=(((-70.0, 52.0, 2.4), (72.0, 44.0, 2.0), (10.0, 104.0, 1.8)), ((-80.0, 62.0, 2.0), (82.0, 56.0, 1.7), (14.0, 112.0, 1.5)),
                   ((-86.0, 58.0, 1.4), (88.0, 54.0, 1.2)), ())[i % 4],
        )
    elif anim == "death":
        melt = _ease(i / max(1, n - 1))
        pose.update(
            h=REST_H * (1.0 - 0.80 * melt),
            w=REST_W * (1.0 + 0.30 * melt),
            tip=max(0.0, 1.0 - 1.6 * melt),
            lean=5.0 * (1.0 - melt),
            flow=ph * 0.5,
            big_eye="open" if i == 0 else ("squeeze" if i < 3 else "dead"),
            small_eye="wide" if i < 2 else "dead",
            look=(0.0, 1.5),
            mouth=("wobble", 0.5 - 0.5 * melt) if i < 5 else ("flat", 0.0),
            wrist=(-12.0 + 4.0 * melt, -30.0 + 4.0 * melt),
            hand_turn=-12.0 + 12.0 * melt,
            hand="open" if i < 2 else "thumbs",
            card_turn=-22.0 - 62.0 * melt,
            card_sink=melt,
            sparkles=tuple(max(0.0, 1.0 - 2.2 * melt - 0.1 * k) for k in range(3)),
        )
    return pose


def _on_heap(pose: Dict[str, object], across: float, up: float) -> Point:
    """A point of the heap: ``across`` of its half width from its middle,
    ``up`` of its height above the ground. It leans as the heap does."""
    return (CX + across * float(pose["w"]) + float(pose["lean"]) * up**1.5, GROUND - up * float(pose["h"]))


# ---- The heap ----------------------------------------------------------------

#: Where one colour of the gradient gives way to the next, as parts of the
#: heap's height above the ground, from the top.
BANDS: Sequence[Tuple[float, RGBA]] = (
    (0.80, _mix(VIOLET, ORCHID, 0.5)),
    (0.68, ORCHID),
    (0.54, _mix(ORCHID, PINK, 0.5)),
    (0.42, PINK),
    (0.28, _mix(PINK, PEACH, 0.5)),
    (0.15, PEACH),
)


def _heap_outline(w: float, h: float, lean: float, lump: float) -> List[Point]:
    """The heap: a low round top that leans, with lumps along it."""
    pts: List[Point] = []
    steps = 56
    for j in range(steps + 1):
        u = -1.0 + 2.0 * j / steps
        k = (1.0 - abs(u) ** 2.2) ** 0.5
        pts.append((CX + u * w + lean * k**1.5, GROUND - 0.94 * h * k - 4.0 * k * math.sin(3.1 * u + 0.8 + lump) - 2.0 * k * math.sin(7.3 * u - lump)))
    return pts + [(CX + w, GROUND), (CX - w, GROUND)]


def _heap_piece(w: float, h: float, tip: float, lean: float, front: float, rear: float, flow: float, tear: tuple):
    key = ("heap", w, h, tip, lean, front, rear, flow, tear)
    if key in _PIECES:
        return _PIECES[key]

    def layer() -> Image.Image:
        return Image.new("RGBA", CANVAS, TRANSPARENT)

    # Its silhouette: the heap, the three lumps of its top, the spill where it
    # runs out over the ground, and the drops beside the spill.
    shape_img = layer()
    d = blending_draw(shape_img)
    d.polygon([_pt(p) for p in _heap_outline(w, h, lean, flow)], fill=WHITE)
    top = (CX + lean - 3.0, GROUND - h)
    if tip > 0.05:
        # Three lumps of unequal size, each a little out of the heap: the
        # tallest is not in the middle. `tip` is how far they stand out.
        for across, rise, r in ((-0.44, 0.03, 15.5), (0.10, 0.13, 18.5), (0.54, -0.02, 12.5)):
            k = (1.0 - abs(across) ** 2.2) ** 0.5
            c = (top[0] + 3.0 + across * w, GROUND - 0.94 * h * k + r * 0.55 - rise * h * tip)
            _oval(d, c, r, r * 0.84, WHITE)
    flat = min(1.0, h / REST_H + 0.25)
    # The spill: a long thin run behind it, a short one before it, and two
    # drops that are no part of it. A ring of equal lobes is a rim.
    for x, rx, ry in ((CX - w - 3.0 - rear, 19.0 + rear * 0.4, 4.6 * flat), (CX + w - 3.0 + front, 11.0 + front * 0.5, 7.4 * flat),
                      (CX - 0.30 * w, 15.0, 5.0 * flat), (CX + 0.52 * w, 13.0, 4.2 * flat)):
        _oval(d, (x, GROUND - ry), rx, ry, WHITE)
    for x, rx, ry in ((max(8.0, CX - w - 27.0 - rear), 4.6, 2.6), (min(FRAME_SIZE[0] - 8.0, CX + w + 15.0 + front), 3.4, 2.2)):
        _oval(d, (x, GROUND - ry), rx, ry, WHITE)
    # It sags: a bulge on its back, a smaller one on its front.
    _oval(d, (CX - 0.80 * w + lean * 0.2, GROUND - 0.30 * h), 10.0, 0.16 * h, WHITE)
    _oval(d, (CX + 0.90 * w + lean * 0.1, GROUND - 0.22 * h), 7.0, 0.11 * h, WHITE)
    d.rectangle((0, _s(GROUND), CANVAS[0], CANVAS[1]), fill=TRANSPARENT)
    shape = shape_img.getchannel("A")

    # The gradient, in bands whose edges wave and flow.
    body = Image.new("RGBA", CANVAS, VIOLET)
    d = blending_draw(body)
    for k, (level, colour) in enumerate(BANDS):
        edge = []
        for x in range(0, FRAME_SIZE[0] + 9, 4):
            edge.append((float(x), GROUND - level * h + 3.4 * math.sin(x / 11.0 + k * 1.7 + flow) + 1.4 * math.sin(x / 5.0 - flow)))
        d.polygon([_pt(p) for p in edge + [(FRAME_SIZE[0] + 8.0, GROUND + 8.0), (0.0, GROUND + 8.0)]], fill=colour)
    # The colours run: drips of each band go down into the band under it.
    above = VIOLET
    for k, (level, colour) in enumerate(BANDS):
        for j in range(5):
            x = CX + (-0.86 + 0.42 * j + 0.11 * k) * w
            y = GROUND - level * h
            long = (0.05 + 0.035 * ((j + 2 * k) % 3)) * h
            _capsule(d, (x, y - 3.0), (x, y + long), 3.4 + (j + k) % 2, above)
            _oval(d, (x, y + long + 1.2), 2.5 + 0.5 * ((j + k) % 2), 2.8, above)
        above = colour

    def edge_of(dx: float, dy: float) -> Image.Image:
        """The part of the heap that has nothing of the heap ``(dx, dy)`` away."""
        return ImageChops.multiply(shape, ImageChops.invert(ImageChops.offset(shape, -_s(dx), -_s(dy))))

    # The light is before and above it: a light rim there, a shade behind
    # and below.
    lit = Image.new("RGBA", CANVAS, WHITE)
    lit.putalpha(edge_of(3.0, -4.0).point(lambda a: a * 96 // 255))
    body.alpha_composite(lit)
    dark = Image.new("RGBA", CANVAS, SHADE)
    dark.putalpha(edge_of(-4.5, 6.0).point(lambda a: a * 92 // 255))
    body.alpha_composite(dark)
    # It is glossy, as a generated thing is.
    gloss = layer()
    d = blending_draw(gloss)
    g = (CX + 0.36 * w + lean * 0.8, GROUND - 0.86 * h)
    ring = []
    for j in range(24):
        a = math.tau * j / 24
        x, y = 9.5 * math.cos(a), 3.6 * math.sin(a)
        ring.append((g[0] + x * 0.87 - y * 0.5, g[1] + x * 0.5 + y * 0.87))
    d.polygon([_pt(p) for p in ring], fill=(255, 255, 255, 190))
    _oval(d, (g[0] + 13.5, g[1] + 9.5), 2.4, 2.0, (255, 255, 255, 190))
    for x, y, r in ((CX - 0.30 * w, GROUND - 0.20 * h, 2.8), (CX - 0.16 * w, GROUND - 0.10 * h, 1.7), (CX - 0.70 * w, GROUND - 0.16 * h, 1.4)):
        _oval(d, (x, y), r, r, (255, 255, 255, 96))
    for across, up, length in ((-0.44, 0.68, 0.16), (-0.25, 0.50, 0.11)):
        x, y = CX + across * w + lean * up**1.5, GROUND - up * h
        _capsule(d, (x, y), (x, y + length * h), 3.0, (255, 255, 255, 64))
        _oval(d, (x, y + length * h + 1.0), 2.7, 3.0, (255, 255, 255, 110))
    body.alpha_composite(gloss)
    body.putalpha(shape)

    # The outline is the silhouette, grown.
    grown = shape.filter(ImageFilter.MaxFilter(2 * _s(1.3) + 1))
    heap = Image.new("RGBA", CANVAS, OUTLINE)
    heap.putalpha(grown)
    heap.alpha_composite(body)

    # Struck: strips of it are out of place.
    for lo, hi, shift in tear:
        y0, y1 = _s(GROUND - hi * h), _s(GROUND - lo * h)
        strip = heap.crop((0, y0, CANVAS[0], y1))
        heap.paste(TRANSPARENT, (0, y0, CANVAS[0], y1))
        heap.paste(ImageChops.offset(strip, _s(shift), 0), (0, y0))

    _PIECES[key] = _cut(heap, (CX, GROUND))
    return _PIECES[key]


def _put_heap(img: Image.Image, pose: Dict[str, object]) -> None:
    part = _heap_piece(round(float(pose["w"]), 2), round(float(pose["h"]), 2), round(float(pose["tip"]), 2), round(float(pose["lean"]), 2),
                       round(float(pose["front"]), 2), round(float(pose["rear"]), 2), round(float(pose["flow"]), 3), tuple(pose["tear"]))  # type: ignore[arg-type]
    if part is not None:
        shape_rig.place(img, part, (CX * SUPER, GROUND * SUPER), 0.0, "heap")


# ---- The face ----------------------------------------------------------------


def _paint_eye(d, rx: float, ry: float, state: str, look: Point) -> None:
    hx, hy = HOME
    if state == "closed":
        _line(d, [(hx - rx, hy - 0.1 * ry), (hx - 0.4 * rx, hy + 0.3 * ry), (hx + 0.4 * rx, hy + 0.3 * ry), (hx + rx, hy - 0.1 * ry)], OUTLINE, 1.5)
        return
    if state == "squeeze":
        _line(d, [(hx - 0.8 * rx, hy - 0.55 * ry), (hx + 0.6 * rx, hy), (hx - 0.8 * rx, hy + 0.55 * ry)], OUTLINE, 1.7)
        return
    if state == "dead":
        for sign in (-1.0, 1.0):
            _line(d, [(hx - 0.6 * rx, hy - 0.45 * ry * sign), (hx + 0.6 * rx, hy + 0.45 * ry * sign)], OUTLINE, 1.6)
        return
    _oval(d, (hx, hy), rx, ry, EYE_WHITE, OUTLINE, 1.0)
    if state == "wide":
        _oval(d, (hx + look[0], hy + look[1]), 1.7, 1.7, PUPIL)
        return
    r = 0.64 * min(rx, ry)
    c = (hx + look[0], hy + look[1] + 0.06 * ry)
    _oval(d, c, r, r * 1.08, IRIS, OUTLINE, 0.7)
    _oval(d, (c[0] + 0.2, c[1] + 0.3), r * 0.5, r * 0.56, PUPIL)
    # The catchlight is a sparkle.
    _star4(d, (c[0] - 0.36 * r, c[1] - 0.42 * r), 0.58 * r, WHITE, None, 0.0, 0.3)
    _oval(d, (c[0] + 0.42 * r, c[1] + 0.48 * r), 0.16 * r, 0.16 * r, (255, 255, 255, 200))
    # A heavy lash line over it.
    arc = [(hx - rx + 0.4, hy - 0.42 * ry), (hx - 0.5 * rx, hy - 0.92 * ry), (hx + 0.5 * rx, hy - 0.92 * ry), (hx + rx - 0.4, hy - 0.42 * ry)]
    _line(d, arc, OUTLINE, 1.6)


def _put_eye(img: Image.Image, at: Point, rx: float, ry: float, state: str, look: Point, name: str, degrees: float = 0.0) -> None:
    look = (round(look[0], 1), round(look[1], 1)) if state in ("open", "wide") else (0.0, 0.0)
    rx, ry = round(rx, 1), round(ry, 1)
    _put(img, ("eye", rx, ry, state, look), lambda d: _paint_eye(d, rx, ry, state, look), at, name, degrees)


def _paint_mouth(d, half: float, mood: str, opening: float) -> None:
    hx, hy = HOME
    if mood == "flat":
        _line(d, [(hx - 0.7 * half, hy + 0.6), (hx - 0.2 * half, hy - 0.4), (hx + 0.3 * half, hy + 0.5), (hx + 0.7 * half, hy - 0.2)], OUTLINE, 1.5)
        return
    wobble = 1.5 if mood == "wobble" else 0.0
    steps = 26
    xs = [-half + 2.0 * half * j / steps for j in range(steps + 1)]

    def arch(x: float) -> float:
        return 1.0 - (x / half) ** 2

    def top(x: float) -> float:
        return hy + 2.4 * arch(x) + wobble * math.sin(x * 0.62)

    def bottom(x: float) -> float:
        return top(x) + (4.6 + 9.5 * opening) * max(0.0, arch(x)) ** 0.8

    lips = [(hx + x, top(x)) for x in xs] + [(hx + x, bottom(x)) for x in reversed(xs)]
    d.polygon([_pt(p) for p in lips], fill=MOUTH)
    if opening > 0.4:
        _oval(d, (hx + 1.0, bottom(0.0) - 1.6), 0.36 * half, 2.2 + 2.0 * opening, TONGUE)
    # Too many teeth: one row of them, from corner to corner.
    def gum(x: float) -> float:
        return top(x) + min(3.4 + 1.2 * opening, (bottom(x) - top(x)) * 0.78)

    d.polygon([_pt((hx + x, top(x))) for x in xs] + [_pt((hx + x, gum(x))) for x in reversed(xs)], fill=TOOTH)
    count = 13
    for j in range(1, count):
        x = -half + 2.0 * half * j / count
        _line(d, [(hx + x, top(x)), (hx + x, gum(x))], TOOTH_LINE, 0.45)
    _line(d, lips + [lips[0]], OUTLINE, 1.0)
    for sign in (-1.0, 1.0):
        _line(d, [(hx + sign * half, top(sign * half)), (hx + sign * (half + 2.2), top(sign * half) - 2.4)], OUTLINE, 1.0)


def _put_face(img: Image.Image, pose: Dict[str, object]) -> None:
    h = float(pose["h"])
    k = max(0.42, min(1.0, h / REST_H))
    face = _on_heap(pose, 0.27, 0.58)
    look = pose["look"]
    # A third eye, where no eye belongs.
    if h > 0.45 * REST_H:
        _put_eye(img, _on_heap(pose, -0.60, 0.36), 5.8 * k, 5.8 * k, "open" if pose["big_eye"] != "dead" else "dead", (-1.4, 1.0), "third_eye", -14.0)
    _put_eye(img, (face[0] - 13.5 * k, face[1] - 3.5 * k), 7.0 * k, 9.2 * k, str(pose["small_eye"]), look, "small_eye")  # type: ignore[arg-type]
    _put_eye(img, (face[0] + 8.5 * k, face[1]), 9.6 * k, 12.2 * k, str(pose["big_eye"]), (look[0] * 1.2, look[1] - 0.6), "big_eye")  # type: ignore[index]
    mood, opening = pose["mouth"]  # type: ignore[misc]
    half, opening = round(15.5 * k, 1), round(float(opening), 2)
    at = (face[0] + 0.5 * k, min(GROUND - 4.0 - (4.6 + 9.5 * opening) * 0.5, face[1] + 15.5 * k))
    _put(img, ("mouth", half, mood, opening), lambda d: _paint_mouth(d, half, mood, opening), at, "mouth")


# ---- The hand ----------------------------------------------------------------

#: How large the hand is drawn.
HAND_SIZE = 1.2
#: The seven fingers of the open hand: (degrees from straight up, length).
FINGERS = ((-70.0, 7.5), (-46.0, 10.0), (-23.0, 12.0), (0.0, 12.6), (22.0, 11.6), (45.0, 10.2), (69.0, 7.8))


def _paint_hand(d, kind: str) -> None:
    """The hand from its wrist at ``HOME``, its fingers up."""
    hx, hy = HOME
    k = HAND_SIZE

    def P(x: float, y: float) -> Point:
        return (hx + x * k, hy + y * k)

    palm = (0.0, -9.0)
    strokes: List[Tuple[List[Point], float]] = [([P(0.0, 2.0), P(0.0, -6.0)], 6.6)]
    if kind == "thumbs":
        # A fist, its fingers folded one under the other, and its thumb up.
        for y in (-13.6, -10.6, -7.6, -4.8):
            strokes.append(([P(-3.0, y), P(6.0, y)], 3.6))
        strokes.append(([P(-5.0, -12.0), P(-6.4, -25.5)], 5.4))
        radius = 6.4
    else:
        spread, longer = (1.22, 1.14) if kind == "splay" else (1.0, 1.0)
        for j, (angle, length) in enumerate(FINGERS):
            a = math.radians(angle * spread)
            root = (palm[0] + 6.0 * math.sin(a), palm[1] - 6.0 * math.cos(a))
            tip = (root[0] + length * longer * math.sin(a * 1.05), root[1] - length * longer * math.cos(a * 1.05))
            if j == 5:
                # One finger has a joint too many, and it bends the wrong way.
                knee = (root[0] + 0.55 * (tip[0] - root[0]) + 1.6, root[1] + 0.55 * (tip[1] - root[1]) + 2.2)
                strokes.append(([P(*root), P(*knee), P(tip[0] + 2.6, tip[1] - 1.8)], 3.3))
            else:
                strokes.append(([P(*root), P(*tip)], 3.3))
        radius = 7.6
    for colour, grow in ((OUTLINE, 2.3), (SKIN, 0.0)):
        _oval(d, P(*palm), radius * k + grow / 2.0, radius * k + grow / 2.0, colour)
        for pts, width in strokes:
            _line(d, pts, colour, width * k + grow)
            for p in (pts[0], pts[-1]):
                _oval(d, p, (width * k + grow) / 2.0, (width * k + grow) / 2.0, colour)
    if kind == "thumbs":
        for y in (-12.1, -9.1, -6.2):
            _line(d, [P(-1.0, y), P(6.6, y)], SKIN_SHADE, 0.8)
    else:
        _line(d, [P(-4.0, -7.4), P(0.5, -5.6), P(4.4, -8.0)], SKIN_SHADE, 0.8)
    # The heap it comes out of.
    _oval(d, P(0.0, 1.6), 6.0 * k, 3.4 * k, ORCHID, OUTLINE, 0.9)


def _put_arm(img: Image.Image, pose: Dict[str, object]) -> None:
    shoulder = _on_heap(pose, -0.38, 0.80)
    wx, wy = pose["wrist"]  # type: ignore[misc]
    wx, wy, turn = round(wx, 1), round(wy, 1), round(float(pose["hand_turn"]), 1)
    hx, hy = HOME
    a = math.radians(turn)
    aim = (math.sin(a), -math.cos(a))

    def arm(d) -> None:
        pts = _bezier((hx, hy + 6.0), (hx, hy - 12.0), (hx + wx - 13.0 * aim[0], hy + wy - 13.0 * aim[1]), (hx + wx, hy + wy), 18)
        for colour, grow in ((OUTLINE, 2.4), (ORCHID, 0.0)):
            for j in range(len(pts) - 1):
                width = 10.5 - 4.0 * j / (len(pts) - 1) + grow
                _capsule(d, pts[j], pts[j + 1], width, colour)
        _line(d, [(x + 1.4, y - 1.0) for x, y in pts[3:-3]], _mix(ORCHID, WHITE, 0.45), 1.3)

    _put(img, ("arm", wx, wy, turn), arm, shoulder, "arm")
    kind = str(pose["hand"])
    _put(img, ("hand", kind), lambda d: _paint_hand(d, kind), (shoulder[0] + wx, shoulder[1] + wy), "hand", turn)


# ---- What is in it, and round it ----------------------------------------------


def _paint_card(d) -> None:
    """A stock picture: a sky, a sun, two hills."""
    hx, hy = HOME
    d.rounded_rectangle((_s(hx - 14.0), _s(hy - 11.0), _s(hx + 14.0), _s(hy + 11.0)), radius=_s(2.4), fill=CARD, outline=OUTLINE, width=_s(1.0))
    d.rectangle((_s(hx - 11.2), _s(hy - 8.4), _s(hx + 11.2), _s(hy + 6.0)), fill=CARD_SKY)
    _oval(d, (hx + 6.4, hy - 3.8), 2.8, 2.8, CARD_SUN)
    _poly(d, [(hx - 11.2, hy + 6.0), (hx - 3.6, hy - 3.6), (hx + 3.6, hy + 6.0)], CARD_HILL_DARK, None)
    _poly(d, [(hx - 2.8, hy + 6.0), (hx + 4.4, hy - 0.4), (hx + 11.2, hy + 6.0)], CARD_HILL, None)


def _put_card(img: Image.Image, pose: Dict[str, object]) -> None:
    sink = float(pose["card_sink"])
    at = _on_heap(pose, -0.86, 0.62)
    _put(img, ("card",), _paint_card, (at[0] - 4.0 * sink, min(GROUND - 6.0, at[1] + 22.0 * sink)), "card", round(float(pose["card_turn"]), 1))


#: The files afloat in it: (kind, across, up, turn in degrees). They are where
#: its face is not.
DOCS = (("py", -0.66, 0.58, -13.0), ("md", 0.74, 0.38, 15.0), ("rs", -0.14, 0.90, 7.0))

PAGE = (250, 250, 252, 255)
PAGE_FOLD = (206, 208, 220, 255)
CODE_LINE = (150, 156, 176, 255)
PY_BLUE = (55, 118, 171, 255)
PY_YELLOW = (255, 212, 59, 255)
RUST = (206, 92, 52, 255)
MARK = (52, 46, 70, 255)


def _paint_doc(d, kind: str) -> None:
    """One file: a page with a folded corner, the mark of its language, two
    lines of what is in it, and the heap over its lower part."""
    hx, hy = HOME
    l, t, r, b = hx - 6.5, hy - 8.5, hx + 6.5, hy + 8.5
    fold = 4.0
    _poly(d, [(l, t), (r - fold, t), (r, t + fold), (r, b), (l, b)], PAGE, OUTLINE, 0.9)
    _poly(d, [(r - fold, t), (r - fold, t + fold), (r, t + fold)], PAGE_FOLD, OUTLINE, 0.6)
    if kind == "py":
        # Two snakes of one shape, one turned about: blue over yellow.
        d.rounded_rectangle((_s(hx - 4.4), _s(hy - 6.2), _s(hx + 1.2), _s(hy - 1.2)), radius=_s(1.4), fill=PY_BLUE)
        d.rounded_rectangle((_s(hx - 2.4), _s(hy - 3.4), _s(hx + 3.2), _s(hy + 1.6)), radius=_s(1.4), fill=PY_YELLOW)
        _oval(d, (hx - 3.0, hy - 4.9), 0.6, 0.6, PAGE)
        _oval(d, (hx + 1.8, hy + 0.3), 0.6, 0.6, PAGE)
    elif kind == "rs":
        # A cog: the mark of a thing made of iron that has rust on it.
        for k in range(8):
            a = math.tau * k / 8
            _oval(d, (hx - 0.6 + 4.1 * math.cos(a), hy - 2.6 + 4.1 * math.sin(a)), 1.0, 1.0, RUST)
        _oval(d, (hx - 0.6, hy - 2.6), 3.6, 3.6, RUST)
        _oval(d, (hx - 0.6, hy - 2.6), 1.5, 1.5, PAGE)
    else:
        # An M and an arrow that goes down, in a box.
        d.rounded_rectangle((_s(hx - 5.0), _s(hy - 6.0), _s(hx + 4.0), _s(hy + 0.4)), radius=_s(1.0), outline=MARK, width=_s(0.8))
        _line(d, [(hx - 3.8, hy - 1.0), (hx - 3.8, hy - 4.6), (hx - 2.2, hy - 2.6), (hx - 0.6, hy - 4.6), (hx - 0.6, hy - 1.0)], MARK, 0.9)
        _line(d, [(hx + 1.9, hy - 4.6), (hx + 1.9, hy - 1.4)], MARK, 0.9)
        _poly(d, [(hx + 0.5, hy - 2.6), (hx + 3.3, hy - 2.6), (hx + 1.9, hy - 0.8)], MARK, None)
    for k, long in enumerate((8.0, 5.5)):
        _capsule(d, (l + 2.2, hy + 3.6 + 2.4 * k), (l + 2.2 + long, hy + 3.6 + 2.4 * k), 0.9, CODE_LINE)
    # It is in the heap, not on it: the heap is over its lower part.
    d.rectangle((_s(l + 0.6), _s(hy + 2.4), _s(r - 0.6), _s(b - 0.6)), fill=(PINK[0], PINK[1], PINK[2], 120))


def _put_docs(img: Image.Image, pose: Dict[str, object]) -> None:
    sink = float(pose["card_sink"])
    flow = float(pose["flow"])
    for k, (kind, across, up, turn) in enumerate(DOCS):
        at = _on_heap(pose, across, up * 0.94)
        bob = round(1.2 * math.sin(flow * 2.0 + k * 2.1) * 2.0) / 2.0
        y = min(GROUND - 5.0, at[1] + bob + 16.0 * sink)
        _put(img, ("doc", kind), lambda d, kind=kind: _paint_doc(d, kind), (at[0], y), f"doc_{kind}", round(turn + 3.0 * math.sin(flow + k), 1))


#: The sparkles: (across, up, size) on the heap at rest.
SPARKLES = ((0.84, 1.14, 12.0), (1.14, 0.86, 7.0), (-1.04, 1.04, 5.5))


def _put_sparkles(img: Image.Image, pose: Dict[str, object]) -> None:
    hx, hy = HOME
    for k, ((across, up, size), scale) in enumerate(zip(SPARKLES, pose["sparkles"])):  # type: ignore[arg-type]
        r = round(size * float(scale) * 2.0) / 2.0
        if r < 1.5:
            continue

        def paint(d, r=r) -> None:
            _star4(d, (hx, hy), r, SPARK, OUTLINE, 0.9, 0.34)
            _star4(d, (hx, hy), r * 0.5, SPARK_CORE, None, 0.0, 0.4)

        _put(img, ("sparkle", r), paint, (CX + across * REST_W + 5.0, GROUND - up * REST_H), f"sparkle_{k}")


def _put_drops(img: Image.Image, pose: Dict[str, object]) -> None:
    """Beads of it in the air or on the ground: (x from its middle, height
    above the ground, radius); a bead of two numbers lies on the ground."""
    hx, hy = HOME
    for k, drop in enumerate(pose["drops"]):  # type: ignore[arg-type]
        if len(drop) == 2:
            x, r = drop
            y = r
        else:
            x, y, r = drop
        r = round(max(0.8, r) * 2.0) / 2.0

        def paint(d, r=r) -> None:
            _oval(d, (hx, hy), r + 1.1, r + 1.1, OUTLINE)
            _oval(d, (hx, hy), r, r, PINK)
            _oval(d, (hx + 0.3 * r, hy - 0.3 * r), 0.36 * r, 0.36 * r, (255, 255, 255, 200))

        _put(img, ("drop", r), paint, (CX + x, GROUND - y), f"drop_{k}")


# ---- Frames ------------------------------------------------------------------


def _render_frame(anim: str, frame_idx: int, nframes: int) -> Image.Image:
    pose = _pose(anim, frame_idx, nframes)
    img = Image.new("RGBA", CANVAS, TRANSPARENT)
    _put_card(img, pose)
    if not pose["arm_front"]:
        _put_arm(img, pose)
    _put_heap(img, pose)
    _put_docs(img, pose)
    _put_face(img, pose)
    if pose["arm_front"]:
        _put_arm(img, pose)
    _put_sparkles(img, pose)
    _put_drops(img, pose)
    return _downsample(img)


#: The heap is a part of the body where it is this part of its full height,
#: or more. Under it is the skirt of the puddle: paint on the ground, a third
#: of the width of the heap, that no player takes for a thing that hits.
BODY_HEIGHT_PART = 0.4


def _body_metrics(fw: int, fh: int) -> dict:
    """The gameplay body: the heap as it stands, where it is high, in frame pixels.

    The box was the box of all of the heap, with the skirt of its puddle: 161
    wide, where the heap that a player sees as a body is about 107. A touch of
    the air over the skirt was a hit (Jon, 2026-10-12: "a larger part of it
    ... extends past the visual sprite")."""
    rest = _pose("idle", 0, 6)
    raster, anchor = _heap_piece(round(float(rest["w"]), 2), round(float(rest["h"]), 2), round(float(rest["tip"]), 2),
                                 round(float(rest["lean"]), 2), 0.0, 0.0, round(float(rest["flow"]), 3), ())
    solid = np.asarray(raster.getchannel("A")) > 128
    heights = solid.sum(axis=0)
    high = np.flatnonzero(heights >= BODY_HEIGHT_PART * heights.max())
    left, right = int(high[0]), int(high[-1]) + 1
    x0 = (CX * SUPER - anchor[0] + left) / SUPER
    y0 = (GROUND * SUPER - anchor[1]) / SUPER
    x, y = int(math.floor(x0)), int(math.floor(y0))
    w = int(math.ceil(x0 + (right - left) / SUPER)) - x
    h = int(math.ceil(y0 + raster.size[1] / SUPER)) - y
    feet = (x + w / 2.0, float(y + h))
    return {
        "body_pixel_bbox": {"x": x, "y": y, "w": w, "h": h},
        "feet_pixel": {"x": feet[0], "y": feet[1]},
        "feet_anchor_norm": {"x": round((feet[0] - fw / 2.0) / fw, 6), "y": round((fh / 2.0 - feet[1]) / fh, 6)},
    }


def render(out_dir: str | Path, **opts) -> List[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frame_transform: dict = {}
    outputs = build_sheet(
        frame_transform_out=frame_transform,
        target=TARGET_NAME,
        rows=ROWS,
        render_fn=_render_frame,
        out_dir=out_dir,
        frame_size=opts.get("frame_size", FRAME_SIZE),
        auto_crop=False,
        actor_metadata=ACTOR_METADATA,
        body_metrics_fn=_body_metrics,
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
    parser = argparse.ArgumentParser(description="Render the AI Slop sprite target.")
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parents[2] / "generated" / TARGET_NAME)
    args = parser.parse_args(argv)
    for path in render(args.out_dir):
        print(path)
    return 0


TARGETS = {TARGET_NAME: {"render": render, "actor_metadata": ACTOR_METADATA}}


if __name__ == "__main__":
    raise SystemExit(main())
