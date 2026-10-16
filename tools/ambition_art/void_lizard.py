"""The Void Lizard (a working title): the boss of Mary-O's castle.

A heavy lizard made of the void. Its body has no light in it and no colour: it
is near to black, and what shows its form is a thin white edge about its
outline, its white eyes with no pupil, its white teeth and claws, and a few
grey lines for its belly and its limbs. A few white points are in its body,
like stars it ate.

The frame is a fixed canvas. The lizard looks to the right and its feet are on
the bottom rows of the frame.

Rows: ``idle``, ``walk``, ``fire`` (the mouth open on an orb of the void) and
``death`` (it goes down and its eyes shut).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter


RGBA = Tuple[int, int, int, int]
Point = Tuple[float, float]

TARGET_NAME = "void_lizard"
FRAME_SIZE = (184, 152)
SUPER = 4
ROWS: List[Tuple[str, int, int]] = [("idle", 6, 140), ("walk", 8, 110), ("fire", 6, 100), ("death", 5, 130)]

TRANSPARENT = (0, 0, 0, 0)
VOID: RGBA = (10, 10, 14, 255)
MAW: RGBA = (44, 44, 54, 255)
SEAM: RGBA = (70, 70, 84, 255)
SEAM_LIGHT: RGBA = (118, 118, 134, 255)
WHITE: RGBA = (255, 255, 255, 255)
STAR: RGBA = (214, 214, 226, 255)

GROUND = 148.0

ACTOR_METADATA = {
    "actor": {"character_id": "void_lizard", "display_name": "Void Lizard"},
    "body": {
        "body_plan": "Biped",
        "body_kind": "Beast",
        "mass_class": "Heavy",
        "traits": ["boss", "void", "lizard"],
        "locomotion_hint": "Walk",
    },
    "visual": {"default_pose": "idle", "portrait": {"animation": "idle", "frame": 0}},
    "tags": ["boss", "void", "enemy"],
    "animation_bindings": {
        "default": {"animation": "idle", "events": []},
        "locomotion.walk": {"animation": "walk", "events": []},
        "combat.ranged": {"animation": "fire", "events": []},
        "combat.death": {"animation": "death", "events": []},
    },
}


def _pts(points: Sequence[Point]) -> List[Tuple[int, int]]:
    return [(int(round(x * SUPER)), int(round(y * SUPER))) for x, y in points]


def _leg(hip: Point, lift: float, reach: float) -> List[List[Point]]:
    foot = (hip[0] + reach, GROUND - lift)
    thigh = [(hip[0] - 12.0, hip[1] - 6.0), (hip[0] + 12.0, hip[1] - 6.0), (foot[0] + 9.0, foot[1] - 9.0), (foot[0] - 10.0, foot[1] - 9.0)]
    sole = [(foot[0] - 12.0, foot[1] - 10.0), (foot[0] + 15.0, foot[1] - 10.0), (foot[0] + 22.0, foot[1]), (foot[0] - 12.0, foot[1])]
    return [thigh, sole]


def _claws(draw: ImageDraw.ImageDraw, foot: Point) -> None:
    for index in range(3):
        x = foot[0] + 7.0 + index * 5.0
        draw.polygon(_pts([(x, foot[1] - 5.0), (x + 5.0, foot[1] - 0.5), (x - 1.0, foot[1] - 0.5)]), fill=WHITE)


def _render_frame(anim: str, frame_idx: int, nframes: int) -> Image.Image:
    size = (FRAME_SIZE[0] * SUPER, FRAME_SIZE[1] * SUPER)
    phase = frame_idx / float(max(nframes, 1))
    wave = math.sin(phase * math.tau)
    bob, stride, gape, orb, fall = wave * 1.6, 0.0, 0.1, 0.0, 0.0
    if anim == "walk":
        stride = wave
        bob = abs(math.cos(phase * math.tau)) * -2.4
    elif anim == "fire":
        ramp = min(1.0, frame_idx / 2.0)
        gape = 0.35 + 0.65 * ramp
        orb = ramp if 1 <= frame_idx < nframes - 1 else 0.0
        bob = -1.0 * ramp
    elif anim == "death":
        fall = min(1.0, (frame_idx + 1) / float(nframes))
        gape, bob = 0.45, 12.0 * fall

    body = (86.0, 104.0 + bob)
    head = (128.0, 64.0 + bob * 1.2 + 18.0 * fall)
    drop = 16.0 * gape
    sway = 3.0 * wave

    far_hip, near_hip = (72.0, body[1] + 20.0), (96.0, body[1] + 22.0)
    far_reach, near_reach = -stride * 9.0 - 4.0, stride * 9.0 + 2.0
    far_lift, near_lift = max(0.0, -stride) * 7.0, max(0.0, stride) * 7.0
    hand = (126.0, body[1] + 4.0 - 4.0 * orb)

    parts: List[List[Point]] = []
    # The tail: thick at the hip, along the floor, with its tip up.
    parts.append([
        (60.0, body[1] + 6.0), (38.0, body[1] + 22.0), (18.0, GROUND - 6.0 + fall * 4.0),
        (5.0, GROUND - 20.0 - sway + fall * 16.0), (10.0, GROUND - 30.0 - sway + fall * 22.0),
        (22.0, GROUND - 16.0), (42.0, GROUND - 2.0), (72.0, GROUND - 4.0), (76.0, body[1] + 24.0),
    ])
    # The spines of its back, from its neck to its tail.
    for index in range(5):
        t = index / 4.0
        base = (100.0 - 46.0 * t, body[1] - 34.0 + 30.0 * t * t + 6.0 * t)
        tall = 19.0 - 5.0 * abs(t - 0.35) * 2.0
        parts.append([(base[0] + 8.0, base[1] + 4.0), (base[0] - 9.0, base[1] - tall), (base[0] - 9.0, base[1] + 8.0)])
    parts += _leg(far_hip, far_lift, far_reach)
    # The body.
    parts.append([
        (56.0, body[1] - 24.0), (98.0, body[1] - 36.0), (120.0, body[1] - 16.0), (120.0, body[1] + 18.0),
        (104.0, body[1] + 30.0), (64.0, body[1] + 30.0), (50.0, body[1] + 10.0),
    ])
    parts += _leg(near_hip, near_lift, near_reach)
    # The horns, the neck, the jaw and the skull.
    for horn_x in (104.0, 116.0):
        parts.append([(horn_x + 4.0, head[1] - 14.0), (horn_x - 16.0, head[1] - 36.0), (horn_x + 14.0, head[1] - 19.0)])
    parts.append([(100.0, body[1] - 32.0), (112.0, head[1] - 14.0), (134.0, head[1] + 8.0), (120.0, body[1] - 6.0)])
    jaw = [(118.0, head[1] + 8.0), (170.0, head[1] + 9.0 + drop), (166.0, head[1] + 17.0 + drop), (124.0, head[1] + 20.0 + drop * 0.5)]
    parts.append(jaw)
    skull = [
        (106.0, head[1] - 18.0), (136.0, head[1] - 22.0), (160.0, head[1] - 10.0), (176.0, head[1] - 6.0),
        (178.0, head[1] + 4.0), (120.0, head[1] + 8.0), (106.0, head[1] + 2.0),
    ]
    parts.append(skull)
    # The near arm.
    parts.append([(104.0, body[1] - 16.0), (115.0, body[1] - 18.0), (hand[0] + 6.0, hand[1] - 4.0), (hand[0] + 4.0, hand[1] + 6.0), (hand[0] - 6.0, hand[1] + 5.0)])

    # The outline of the lizard is the one thing that is drawn in light: the
    # shape of all its parts, grown by the width of the edge.
    mask = Image.new("L", size, 0)
    pen = ImageDraw.Draw(mask)
    for part in parts:
        pen.polygon(_pts(part), fill=255)
    edge = mask.filter(ImageFilter.MaxFilter(2 * int(1.5 * SUPER) + 1))
    halo = mask.filter(ImageFilter.MaxFilter(2 * int(4.0 * SUPER) + 1)).filter(ImageFilter.GaussianBlur(3.0 * SUPER))
    image = Image.new("RGBA", size, TRANSPARENT)
    image.paste((255, 255, 255, 255), mask=halo.point(lambda value: int(value * 0.22)))
    image.paste(WHITE, mask=edge)
    image.paste(VOID, mask=mask)
    draw = ImageDraw.Draw(image)

    # The inside of the mouth, the grey seams, the points of light.
    if gape > 0.2:
        inside = [(122.0, head[1] + 5.0), (170.0, head[1] + 5.0), (167.0, head[1] + 11.0 + drop), (124.0, head[1] + 12.0)]
        draw.polygon(_pts(inside), fill=MAW)
    for row in range(4):
        ly = body[1] - 10.0 + row * 9.0
        draw.line(_pts([(92.0 + row * 0.5, ly), (117.0, ly + 2.0)]), fill=SEAM, width=int(1.3 * SUPER))
    draw.line(_pts([(104.0, body[1] - 16.0), (hand[0] - 6.0, hand[1] + 5.0)]), fill=SEAM_LIGHT, width=int(1.0 * SUPER))
    draw.line(_pts([(near_hip[0] - 12.0, near_hip[1] - 6.0), (near_hip[0] + near_reach - 10.0, GROUND - near_lift - 9.0)]), fill=SEAM_LIGHT, width=int(1.0 * SUPER))
    draw.line(_pts([(120.0, head[1] + 8.0), (176.0, head[1] + 5.0)]), fill=SEAM_LIGHT, width=int(1.0 * SUPER))
    for sx, sy, radius in ((70.0, body[1] - 6.0, 1.1), (84.0, body[1] + 14.0, 0.8), (62.0, body[1] + 12.0, 0.7), (100.0, body[1] - 24.0, 0.9), (44.0, body[1] + 16.0, 0.7), (112.0, head[1] - 6.0, 0.7)):
        draw.ellipse([(sx - radius) * SUPER, (sy - radius) * SUPER, (sx + radius) * SUPER, (sy + radius) * SUPER], fill=STAR)

    # The teeth, the claws and the eye are white.
    for index in range(4):
        x = 136.0 + index * 9.0
        draw.polygon(_pts([(x, head[1] + 5.0), (x + 3.0, head[1] + 12.0), (x + 6.0, head[1] + 5.0)]), fill=WHITE)
    _claws(draw, (far_hip[0] + far_reach, GROUND - far_lift))
    _claws(draw, (near_hip[0] + near_reach, GROUND - near_lift))
    for index in range(3):
        y = hand[1] - 3.0 + index * 4.0
        draw.polygon(_pts([(hand[0] + 4.0, y), (hand[0] + 11.0, y + 1.5), (hand[0] + 4.0, y + 3.5)]), fill=WHITE)
    if anim == "death" and frame_idx >= 1:
        draw.line(_pts([(134.0, head[1] - 8.0), (148.0, head[1] - 6.0)]), fill=WHITE, width=int(1.6 * SUPER))
    else:
        eye = [(133.0, head[1] - 13.0), (149.0, head[1] - 6.5), (146.0, head[1] - 3.5), (134.0, head[1] - 4.5)]
        draw.polygon(_pts(eye), fill=WHITE)

    if orb > 0.0:
        radius = 5.0 + 6.0 * orb
        at = (min(174.0, FRAME_SIZE[0] - radius - 2.0), head[1] + 8.0 + drop * 0.5)
        for grow, fill in ((1.0, WHITE), (0.74, VOID)):
            r = radius * grow
            draw.ellipse([(at[0] - r) * SUPER, (at[1] - r) * SUPER, (at[0] + r) * SUPER, (at[1] + r) * SUPER], fill=fill)
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
