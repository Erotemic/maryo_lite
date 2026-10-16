"""The moving platform of the Super Mary-O demo: a clockwork lift.

One target, ``super_mary_o_lift``: a gilt deck on a plum hull, with a cog under
its middle that turns. A lift that goes up or down and a ferry that goes across
are the same machine, so one drawing serves both.

The frame is a fixed canvas, because the game places it by frame pixels:

* the deck is the full width of the frame (``DECK_SPAN_PX``);
* the top of the deck is at ``DECK_TOP_PX``. A body stands at that row.

The game states the same numbers in its ``PlatformLook``
(``game/ambition_demo_mary_o/src/scenery.rs``). The frame metadata publishes
them as the anchors ``deck_left``, ``deck_right`` and ``deck_top``.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

from PIL import Image

from .common import (
    COIN_GOLD,
    COIN_GOLD_LIGHT,
    OUTLINE,
    PixelCanvas,
    rasterize_logical,
)

RGBA = Tuple[int, int, int, int]

TARGET = "super_mary_o_lift"
SCALE = 4
LOGICAL = (48, 18)
FRAME = (LOGICAL[0] * SCALE, LOGICAL[1] * SCALE)
FRAMES = 4

# Logical rows of the drawing.
DECK_TOP = 1.0
DECK_BOTTOM = 5.0
HULL_BOTTOM = 8.0
COG_CENTER = (24.0, 11.5)
COG_RADIUS = 5.5
COG_TEETH = 6

DECK_TOP_PX = DECK_TOP * SCALE
DECK_SPAN_PX = (0.0, float(FRAME[0]))

GOLD_DARK: RGBA = (168, 112, 28, 255)
PLUM: RGBA = (104, 62, 150, 255)
PLUM_DARK: RGBA = (62, 36, 98, 255)
PLUM_LIGHT: RGBA = (150, 104, 196, 255)
MINT: RGBA = (150, 236, 208, 255)
MINT_DARK: RGBA = (72, 160, 140, 255)
ROSE: RGBA = (255, 128, 190, 255)
ROSE_LIGHT: RGBA = (255, 206, 230, 255)


def _cog(px: PixelCanvas, turn: float) -> None:
    """The cog, turned by `turn` of the angle between two teeth."""
    cx, cy = COG_CENTER
    step = 2.0 * math.pi / COG_TEETH
    outer, root = COG_RADIUS, COG_RADIUS - 1.6
    rim = []
    for tooth in range(COG_TEETH):
        base = (tooth + turn) * step
        # Each tooth is a flat top between two flanks.
        for part, radius in ((-0.30, root), (-0.19, outer), (0.19, outer), (0.30, root)):
            angle = base + part * step
            rim.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    px.polygon(rim, fill=MINT_DARK, outline=OUTLINE, width=0.5)
    px.ellipse(cx - root + 0.5, cy - root + 0.5, cx + root - 0.5, cy + root - 0.5, fill=MINT)
    # Three holes turn with the teeth, so the turn shows inside the rim too.
    for hole in range(3):
        a = turn * step + hole * 2.0 * math.pi / 3.0
        hx, hy = cx + 2.1 * math.cos(a), cy + 2.1 * math.sin(a)
        px.ellipse(hx - 0.75, hy - 0.75, hx + 0.75, hy + 0.75, fill=MINT_DARK)
    px.ellipse(cx - 1.0, cy - 1.0, cx + 1.0, cy + 1.0, fill=COIN_GOLD, outline=OUTLINE, width=0.25)


def _lift_frame(animation: str, frame_idx: int, nframes: int) -> Image.Image:
    del animation
    turn = frame_idx / float(max(nframes, 1))

    def painter(px: PixelCanvas) -> None:
        width = float(LOGICAL[0])
        # The bracket that holds the cog's axle, behind the cog.
        px.polygon(
            [
                (COG_CENTER[0] - 10.0, HULL_BOTTOM - 0.5),
                (COG_CENTER[0] + 10.0, HULL_BOTTOM - 0.5),
                (COG_CENTER[0] + 3.0, COG_CENTER[1] + 1.0),
                (COG_CENTER[0] - 3.0, COG_CENTER[1] + 1.0),
            ],
            fill=PLUM_DARK,
            outline=OUTLINE,
            width=0.5,
        )
        _cog(px, turn)

        # The hull: plum, narrower than the deck, with a row of round lamps.
        px.rounded_rect(2.0, DECK_BOTTOM - 1.0, width - 2.0, HULL_BOTTOM, radius=1.5, fill=OUTLINE)
        px.rounded_rect(2.5, DECK_BOTTOM - 1.0, width - 2.5, HULL_BOTTOM - 0.5, radius=1.2, fill=PLUM)
        px.rect(3.5, DECK_BOTTOM, width - 3.5, DECK_BOTTOM + 0.75, fill=PLUM_DARK)
        px.rect(4.0, HULL_BOTTOM - 1.25, width - 4.0, HULL_BOTTOM - 0.75, fill=PLUM_LIGHT)
        lamps = 5
        for lamp in range(lamps):
            # One lamp is bright in each frame, and the bright one goes along the hull.
            x = 8.0 + lamp * (width - 16.0) / (lamps - 1)
            lit = (lamp + frame_idx) % lamps == 0
            px.ellipse(x - 0.9, 5.9, x + 0.9, 7.2, fill=ROSE_LIGHT if lit else ROSE, outline=PLUM_DARK, width=0.25)

        # The deck: a gilt plank over the full width. Its top row is the floor.
        px.rounded_rect(0.0, DECK_TOP, width, DECK_BOTTOM, radius=1.25, fill=OUTLINE)
        px.rounded_rect(0.5, DECK_TOP + 0.5, width - 0.5, DECK_BOTTOM - 0.5, radius=0.9, fill=COIN_GOLD)
        px.rect(1.5, DECK_TOP + 0.5, width - 1.5, DECK_TOP + 1.25, fill=COIN_GOLD_LIGHT)
        px.rect(1.5, DECK_BOTTOM - 1.25, width - 1.5, DECK_BOTTOM - 0.5, fill=GOLD_DARK)
        for x in (3.0, width - 3.0):
            px.ellipse(x - 0.8, 2.3, x + 0.8, 3.9, fill=MINT, outline=GOLD_DARK, width=0.25)
        # A star at the middle of the deck's face.
        cx, cy = width / 2.0, (DECK_TOP + DECK_BOTTOM) / 2.0 + 0.1
        star = []
        for point in range(10):
            radius = 1.5 if point % 2 == 0 else 0.65
            angle = -math.pi / 2.0 + point * math.pi / 5.0
            star.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
        px.polygon(star, fill=ROSE_LIGHT, outline=GOLD_DARK, width=0.25)

    return rasterize_logical(LOGICAL, SCALE, painter)


def _lift_meta(animation: str, frame_idx: int, nframes: int) -> dict:
    del animation, frame_idx, nframes
    return {
        "anchors": {
            "deck_left": {"x": DECK_SPAN_PX[0], "y": DECK_TOP_PX},
            "deck_right": {"x": DECK_SPAN_PX[1], "y": DECK_TOP_PX},
            "deck_top": {"x": FRAME[0] / 2, "y": DECK_TOP_PX},
        },
        "construction": {"kind": "moving_platform"},
    }


_ACTOR = {
    "actor": {"character_id": f"prop_{TARGET}", "display_name": "Mary-O Clockwork Lift"},
    "body": {
        "body_plan": "StaticProp",
        "body_kind": "Scenery",
        "mass_class": "Static",
        "locomotion_hint": "None",
        "traits": ["scenery", "platform", "animated"],
    },
    "tags": ["scenery", "platform", "animated"],
}
