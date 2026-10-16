"""World-object sheets for the Super Mary-O push.

These targets intentionally stay lightweight and data-driven so the repo can
swap in SMB1-like pickups / scenery without touching runtime code first.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, sin
from pathlib import Path
from typing import Callable, Dict, List, Tuple

from PIL import Image

from .common import (
    BRICK,
    GAS_RED,
    GAS_RED_DARK,
    MILK_BLUE,
    MILK_WHITE,
    OUTLINE,
    PIPE_COPPER,
    PIPE_COPPER_DARK,
    PIPE_COPPER_LIGHT,
    STEEL,
    STEEL_DARK,
    WHITE,
    COIN_GOLD,
    COIN_GOLD_LIGHT,
    bottom_center_canvas,
    rasterize_logical,
)

FRAME = (96, 96)
LOGICAL = (28, 28)
SCALE = 3
LABEL_WIDTH = 120

WAND_PINK = (224, 72, 148, 255)
WAND_PINK_DARK = (139, 42, 96, 255)
WAND_VIOLET = (119, 83, 196, 255)
BRASS = (187, 119, 47, 255)
BRASS_LIGHT = (242, 190, 83, 255)
BRASS_DARK = (102, 62, 34, 255)
EMBER_ORANGE = (239, 91, 38, 255)
EMBER_YELLOW = (255, 218, 92, 255)
LANTERN_GLASS = (255, 174, 61, 145)
QUASAR_VIOLET = (109, 70, 203, 255)
QUASAR_INDIGO = (57, 44, 124, 255)
QUASAR_PINK = (236, 103, 182, 255)
QUASAR_CYAN = (117, 232, 249, 255)
QUASAR_CORE = (255, 240, 183, 255)


@dataclass(frozen=True)
class PropSpec:
    target_name: str
    display_name: str
    rows: List[Tuple[str, int, int]]
    renderer: Callable[[str, int, int], Image.Image]
    traits: Tuple[str, ...]



def _outlined_rect(px, x1, y1, x2, y2, *, fill, inset: float = 0.4) -> None:
    px.rect(x1, y1, x2, y2, fill=OUTLINE)
    ix1, iy1 = x1 + inset, y1 + inset
    ix2, iy2 = x2 - inset, y2 - inset
    if ix2 <= ix1 or iy2 <= iy1:
        px.rect(x1, y1, x2, y2, fill=fill)
        return
    px.rect(ix1, iy1, ix2, iy2, fill=fill)


def _star_points(
    cx: float,
    cy: float,
    outer_radius: float,
    inner_radius: float,
    *,
    rotation: float = -pi / 2.0,
) -> List[Tuple[float, float]]:
    points: List[Tuple[float, float]] = []
    for index in range(10):
        radius = outer_radius if index % 2 == 0 else inner_radius
        angle = rotation + index * pi / 5.0
        points.append((cx + cos(angle) * radius, cy + sin(angle) * radius))
    return points



def _pipe_frame(animation: str, frame_idx: int, nframes: int) -> Image.Image:
    bob = [0.0, -0.2, 0.0, 0.2][frame_idx % 4] if nframes > 1 else 0.0

    def painter(px) -> None:
        _outlined_rect(px, 7, 20 + bob, 21, 27 + bob, fill=PIPE_COPPER)
        _outlined_rect(px, 5, 11 + bob, 23, 17 + bob, fill=PIPE_COPPER)
        px.rect(5.8, 12.0 + bob, 9.0, 16.2 + bob, fill=PIPE_COPPER_LIGHT)
        px.rect(10.0, 12.0 + bob, 13.8, 16.2 + bob, fill=PIPE_COPPER)
        px.rect(14.5, 12.0 + bob, 22.0, 16.2 + bob, fill=PIPE_COPPER_DARK)
        px.rect(19.2, 11.6 + bob, 22.0, 27.0 + bob, fill=PIPE_COPPER_DARK)
        px.rect(6.0, 18.0 + bob, 20.0, 19.0 + bob, fill=PIPE_COPPER_LIGHT)
        px.rect(8.2, 13.8 + bob, 20.0, 15.0 + bob, fill=(0, 0, 0, 110))

    sprite = rasterize_logical(LOGICAL, SCALE, painter)
    frame = bottom_center_canvas(sprite, FRAME)
    return frame



def _milk_frame(animation: str, frame_idx: int, nframes: int) -> Image.Image:
    bob = [0.0, -0.5, -1.0, -0.4][frame_idx % 4]
    tilt = [-0.3, 0.0, 0.3, 0.0][frame_idx % 4]

    def painter(px) -> None:
        left = 9.0 + tilt
        right = 19.0 + tilt
        _outlined_rect(px, left, 9.0 + bob, right, 23.0 + bob, fill=MILK_WHITE)
        px.polygon(
            [(left, 9.0 + bob), (left + 2.4, 6.0 + bob), (right - 2.4, 6.0 + bob), (right, 9.0 + bob)],
            fill=MILK_WHITE,
            outline=OUTLINE,
        )
        px.rect(left + 1.0, 12.0 + bob, right - 1.0, 17.0 + bob, fill=MILK_BLUE)
        px.line([(left + 2.6, 10.6 + bob), (left + 2.6, 21.0 + bob)], fill=(216, 230, 255, 255), width=0.6)
        _outlined_rect(px, left + 2.1, 13.0 + bob, left + 3.4, 16.5 + bob, fill=WHITE, inset=0.15)
        _outlined_rect(px, left + 5.0, 13.2 + bob, left + 8.2, 14.4 + bob, fill=WHITE, inset=0.15)
        _outlined_rect(px, left + 5.0, 15.1 + bob, left + 8.6, 16.3 + bob, fill=WHITE, inset=0.15)
        px.rect(left + 2.0, 18.1 + bob, right - 2.0, 20.0 + bob, fill=(209, 230, 255, 255))

    sprite = rasterize_logical(LOGICAL, SCALE, painter)
    frame = bottom_center_canvas(sprite, FRAME)
    return frame



def _gas_tank_frame(animation: str, frame_idx: int, nframes: int) -> Image.Image:
    bob = [0.0, -0.5, -0.8, -0.2][frame_idx % 4]
    glow = [0.0, 0.6, 1.0, 0.4][frame_idx % 4]

    def painter(px) -> None:
        _outlined_rect(px, 8.0, 10.5 + bob, 19.8, 23.0 + bob, fill=GAS_RED)
        _outlined_rect(px, 10.4, 8.8 + bob, 17.2, 12.0 + bob, fill=GAS_RED)
        _outlined_rect(px, 16.6, 8.0 + bob, 18.6, 10.8 + bob, fill=STEEL)
        _outlined_rect(px, 18.4, 8.5 + bob, 21.5, 10.0 + bob, fill=STEEL)
        px.rect(18.2, 10.2 + bob, 19.8, 12.6 + bob, fill=STEEL_DARK)
        px.rect(9.4, 13.0 + bob, 12.4, 21.0 + bob, fill=(255, 189, 171, 255))
        px.rect(13.2, 13.0 + bob, 18.4, 14.4 + bob, fill=GAS_RED_DARK)
        px.rect(13.2, 16.2 + bob, 18.4, 17.6 + bob, fill=GAS_RED_DARK)
        px.rect(13.2, 19.4 + bob, 18.4, 20.8 + bob, fill=GAS_RED_DARK)
        if glow > 0.0:
            px.ellipse(11.2, 12.2 + bob, 19.0, 20.0 + bob, fill=(255, 236, 192, int(70 * glow)), outline=None)

    sprite = rasterize_logical(LOGICAL, SCALE, painter)
    frame = bottom_center_canvas(sprite, FRAME)
    return frame



def _spark_blossom_frame(animation: str, frame_idx: int, nframes: int) -> Image.Image:
    """The spark-blossom (fire-flower) pickup.

    The runtime has referenced ``super_mary_o_spark_blossom`` through
    ``WorldItemArt`` since the spark form landed, but no generator target ever
    produced it — so the item was collectible and completely invisible. This is
    that missing target.

    Four petals around a bright core on a two-leaf stem, cycling the core
    between gold and red so a dropped blossom reads as "live" at a glance the
    way the milk carton's bob does.
    """
    bob = [0.0, -0.6, -1.0, -0.4][frame_idx % 4]
    pulse = [0.0, 0.55, 1.0, 0.45][frame_idx % 4]
    core = (
        int(COIN_GOLD[0] + (GAS_RED[0] - COIN_GOLD[0]) * pulse),
        int(COIN_GOLD[1] + (GAS_RED[1] - COIN_GOLD[1]) * pulse),
        int(COIN_GOLD[2] + (GAS_RED[2] - COIN_GOLD[2]) * pulse),
        255,
    )

    def painter(px) -> None:
        cx = 14.0
        cy = 12.0 + bob
        # Stem + the two leaves, so the blossom sits on the ground rather than
        # floating like the coin does.
        px.rect(cx - 0.7, cy + 3.0, cx + 0.7, 22.5, fill=PIPE_COPPER_DARK)
        px.ellipse(cx - 6.0, 17.0, cx - 0.8, 20.4, fill=PIPE_COPPER, outline=OUTLINE, width=0.6)
        px.ellipse(cx + 0.8, 18.6, cx + 6.0, 22.0, fill=PIPE_COPPER, outline=OUTLINE, width=0.6)
        # Four petals, drawn before the core so the core caps their seams.
        petal = 4.4
        for dx, dy in ((0.0, -1.0), (0.0, 1.0), (-1.0, 0.0), (1.0, 0.0)):
            px.ellipse(
                cx + dx * 3.1 - petal / 2.0,
                cy + dy * 3.1 - petal / 2.0,
                cx + dx * 3.1 + petal / 2.0,
                cy + dy * 3.1 + petal / 2.0,
                fill=MILK_WHITE,
                outline=OUTLINE,
                width=0.6,
            )
        px.ellipse(cx - 3.0, cy - 3.0, cx + 3.0, cy + 3.0, fill=core, outline=OUTLINE, width=0.7)
        px.ellipse(cx - 1.3, cy - 1.6, cx + 0.9, cy + 0.4, fill=COIN_GOLD_LIGHT, outline=None)
        # Deliberately NO glow halo. A translucent ellipse over the transparent
        # canvas composites as a visible disc rather than a glow (the same class
        # of trap as alpha-0 blending acting as an eraser), and the classic
        # flower has no aura anyway — the pulsing core is the whole tell.

    sprite = rasterize_logical(LOGICAL, SCALE, painter)
    frame = bottom_center_canvas(sprite, FRAME)
    return frame


def _star_wand_frame(animation: str, frame_idx: int, nframes: int) -> Image.Image:
    """Magical-girl wand pickup: Mary-O's invincibility-grade star item."""
    bob = [0.0, -0.5, -0.9, -0.5, 0.0, -0.3][frame_idx % 6]
    pulse = [0.15, 0.45, 1.0, 0.55, 0.25, 0.7][frame_idx % 6]
    sparkle_slot = frame_idx % 3

    def painter(px) -> None:
        # A diagonal silhouette reads as a held wand rather than a generic
        # collectible star. The ribbon wings below the crown supply the
        # magical-girl read at the tiny 28 px authoring scale.
        px.line([(8.0, 23.0 + bob), (16.4, 11.3 + bob)], fill=OUTLINE, width=3.0)
        px.line([(8.0, 23.0 + bob), (16.4, 11.3 + bob)], fill=WAND_PINK, width=1.55)
        px.line([(9.1, 21.7 + bob), (15.8, 12.2 + bob)], fill=(255, 174, 216, 255), width=0.45)

        # Pommel and grip collar.
        px.ellipse(5.8, 21.0 + bob, 9.8, 25.0 + bob, fill=WAND_VIOLET, outline=OUTLINE, width=0.7)
        px.ellipse(6.8, 21.8 + bob, 8.8, 23.8 + bob, fill=(199, 162, 255, 255), outline=None)
        px.polygon(
            [(13.1, 14.4 + bob), (15.0, 11.8 + bob), (17.1, 13.5 + bob), (15.2, 15.5 + bob)],
            fill=WAND_PINK_DARK,
            outline=OUTLINE,
            width=0.55,
        )

        # Ribbon / wing flourishes make the head more ornate without turning
        # the entire pickup into an unreadable halo.
        px.polygon(
            [(14.6, 12.2 + bob), (10.5, 11.3 + bob), (12.8, 14.2 + bob)],
            fill=WAND_PINK,
            outline=OUTLINE,
            width=0.55,
        )
        px.polygon(
            [(17.1, 11.9 + bob), (20.9, 10.5 + bob), (18.9, 13.9 + bob)],
            fill=WAND_PINK,
            outline=OUTLINE,
            width=0.55,
        )

        # Star crown: outlined first, then a smaller gold inset so the shape
        # survives nearest-neighbor scaling and still reads against bright sky.
        crown_x = 17.1
        crown_y = 8.0 + bob
        px.polygon(
            _star_points(crown_x, crown_y, 5.5, 2.5),
            fill=OUTLINE,
        )
        px.polygon(
            _star_points(crown_x, crown_y, 4.55, 2.0),
            fill=COIN_GOLD,
        )
        gem = (
            int(WAND_PINK[0] + (255 - WAND_PINK[0]) * pulse * 0.35),
            int(WAND_PINK[1] + (205 - WAND_PINK[1]) * pulse * 0.35),
            int(WAND_PINK[2] + (236 - WAND_PINK[2]) * pulse * 0.35),
            255,
        )
        px.ellipse(crown_x - 1.65, crown_y - 1.65, crown_x + 1.65, crown_y + 1.65, fill=gem, outline=OUTLINE, width=0.45)
        px.ellipse(crown_x - 0.75, crown_y - 1.0, crown_x + 0.25, crown_y, fill=WHITE, outline=None)

        # Tiny hard-edged glints animate around the crown. These are deliberately
        # sparse pixels, not translucent discs, so the pickup remains crisp.
        sparkle_positions = ((22.6, 5.0), (21.9, 14.1), (11.2, 5.9))
        sx, sy = sparkle_positions[sparkle_slot]
        sy += bob
        px.rect(sx - 0.35, sy - 1.1, sx + 0.35, sy + 1.1, fill=COIN_GOLD_LIGHT)
        px.rect(sx - 1.1, sy - 0.35, sx + 1.1, sy + 0.35, fill=COIN_GOLD_LIGHT)

    sprite = rasterize_logical(LOGICAL, SCALE, painter)
    return bottom_center_canvas(sprite, FRAME)


def _cinder_beacon_frame(animation: str, frame_idx: int, nframes: int) -> Image.Image:
    """Ornate hand lantern with an ember that visibly flickers."""
    bob = [0.0, -0.4, -0.8, -0.3][frame_idx % 4]
    flicker = [0.25, 0.75, 1.0, 0.45][frame_idx % 4]

    def painter(px) -> None:
        # Angular handle approximates a forged arch and keeps the silhouette
        # pixel-clean. It is doubled with an outline like the rest of the prop.
        handle = [
            (9.8, 10.2 + bob),
            (9.8, 7.2 + bob),
            (12.0, 4.8 + bob),
            (16.0, 4.8 + bob),
            (18.2, 7.2 + bob),
            (18.2, 10.2 + bob),
        ]
        px.line(handle, fill=OUTLINE, width=2.2)
        px.line(handle, fill=BRASS, width=1.0)

        # Crown and foot use stepped finials so this reads as an ornate hand
        # lantern rather than a modern camping lamp.
        px.polygon(
            [(9.0, 10.0 + bob), (11.0, 8.5 + bob), (17.0, 8.5 + bob), (19.0, 10.0 + bob), (17.7, 12.0 + bob), (10.3, 12.0 + bob)],
            fill=BRASS_DARK,
            outline=OUTLINE,
            width=0.55,
        )
        px.rect(10.2, 9.6 + bob, 17.8, 11.2 + bob, fill=BRASS_LIGHT)
        px.ellipse(13.0, 7.3 + bob, 15.0, 9.3 + bob, fill=BRASS_LIGHT, outline=OUTLINE, width=0.45)

        # Glass chamber and forged ribs.
        px.polygon(
            [(10.3, 11.0 + bob), (17.7, 11.0 + bob), (18.5, 20.5 + bob), (9.5, 20.5 + bob)],
            fill=LANTERN_GLASS,
            outline=OUTLINE,
            width=0.75,
        )
        px.polygon(
            [(11.4, 12.0 + bob), (16.6, 12.0 + bob), (17.1, 19.4 + bob), (10.9, 19.4 + bob)],
            fill=(118, 46, 28, 120),
        )
        px.line([(11.2, 11.0 + bob), (10.4, 20.5 + bob)], fill=BRASS, width=0.8)
        px.line([(16.8, 11.0 + bob), (17.6, 20.5 + bob)], fill=BRASS, width=0.8)
        px.line([(14.0, 11.0 + bob), (14.0, 20.5 + bob)], fill=BRASS_DARK, width=0.65)

        # Ember flame: broad orange body, bright inner tongue, then a one-pixel
        # white-hot fleck at peak intensity.
        flame_top = 13.2 + bob - flicker * 0.9
        px.polygon(
            [(14.0, flame_top), (16.1, 16.7 + bob), (15.3, 19.0 + bob), (12.7, 19.0 + bob), (11.9, 16.7 + bob)],
            fill=EMBER_ORANGE,
            outline=OUTLINE,
            width=0.45,
        )
        px.polygon(
            [(14.0, 15.0 + bob - flicker * 0.55), (15.0, 17.1 + bob), (14.4, 18.3 + bob), (13.3, 18.3 + bob), (13.0, 17.1 + bob)],
            fill=EMBER_YELLOW,
        )
        if flicker > 0.7:
            px.rect(13.7, 16.3 + bob, 14.3, 17.4 + bob, fill=WHITE)

        # Heavy base, side curls, and jewel-like rivets complete the beacon.
        px.polygon(
            [(9.4, 20.0 + bob), (18.6, 20.0 + bob), (19.2, 22.0 + bob), (17.0, 23.0 + bob), (11.0, 23.0 + bob), (8.8, 22.0 + bob)],
            fill=BRASS_DARK,
            outline=OUTLINE,
            width=0.65,
        )
        px.rect(10.2, 20.3 + bob, 17.8, 21.5 + bob, fill=BRASS_LIGHT)
        px.ellipse(7.8, 14.0 + bob, 10.1, 16.3 + bob, fill=BRASS, outline=OUTLINE, width=0.45)
        px.ellipse(17.9, 14.0 + bob, 20.2, 16.3 + bob, fill=BRASS, outline=OUTLINE, width=0.45)
        px.ellipse(8.45, 14.65 + bob, 9.45, 15.65 + bob, fill=EMBER_ORANGE, outline=None)
        px.ellipse(18.55, 14.65 + bob, 19.55, 15.65 + bob, fill=EMBER_ORANGE, outline=None)

    sprite = rasterize_logical(LOGICAL, SCALE, painter)
    return bottom_center_canvas(sprite, FRAME)


def _cosmic_quasar_frame(animation: str, frame_idx: int, nframes: int) -> Image.Image:
    """Mary-O's cosmic invincibility pickup: a star-core quasar with orbiting light."""
    bob = [0.0, -0.4, -0.8, -0.4, 0.0, -0.2][frame_idx % 6]
    ring_phase = frame_idx % 6
    pulse = [0.3, 0.55, 0.9, 1.0, 0.7, 0.45][frame_idx % 6]

    def painter(px) -> None:
        cx = 14.0
        cy = 13.0 + bob

        # Outer cosmic shell with a strong star silhouette so it still reads at small scale.
        px.polygon(_star_points(cx, cy, 6.4, 3.0), fill=OUTLINE)
        px.polygon(_star_points(cx, cy, 5.5, 2.5), fill=QUASAR_VIOLET)
        px.polygon(_star_points(cx, cy, 4.2, 1.8, rotation=-pi / 2.0 + pi / 10.0), fill=QUASAR_PINK)
        px.ellipse(cx - 2.2, cy - 2.2, cx + 2.2, cy + 2.2, fill=QUASAR_CORE, outline=OUTLINE, width=0.45)
        px.ellipse(cx - 0.9, cy - 1.2, cx + 0.2, cy - 0.1, fill=WHITE, outline=None)

        # Bright equatorial ring shifts through a few orientations to suggest orbital motion.
        ring_y = [0.0, -0.3, -0.6, 0.0, 0.5, 0.2][ring_phase]
        left = [7.0, 7.8, 8.8, 7.2, 8.2, 7.4][ring_phase]
        right = [21.0, 20.2, 19.2, 20.8, 19.8, 20.6][ring_phase]
        px.line([(left, cy + ring_y), (right, cy + ring_y + 0.4)], fill=OUTLINE, width=2.8)
        px.line([(left + 0.4, cy + ring_y), (right - 0.4, cy + ring_y + 0.4)], fill=QUASAR_CYAN, width=1.3)
        px.line([(left + 1.4, cy + ring_y + 0.1), (right - 1.1, cy + ring_y + 0.45)], fill=(214, 255, 255, 255), width=0.45)

        # Small orbiting glint / moonlet.
        orbit_positions = [(22.3, 9.0), (21.1, 7.4), (18.8, 6.4), (6.0, 15.9), (7.5, 18.0), (20.9, 17.2)]
        ox, oy = orbit_positions[ring_phase]
        oy += bob
        px.ellipse(ox - 1.4, oy - 1.4, ox + 1.4, oy + 1.4, fill=QUASAR_CYAN, outline=OUTLINE, width=0.4)
        px.ellipse(ox - 0.55, oy - 0.55, ox + 0.55, oy + 0.55, fill=WHITE, outline=None)

        # Sparse star glints keep the pickup lively without turning into haze.
        sparkle_fill = COIN_GOLD_LIGHT if pulse > 0.75 else QUASAR_CYAN
        for sx, sy in ((5.0, 8.0), (23.0, 13.5), (10.2, 22.0)):
            sy += bob * 0.3
            px.rect(sx - 0.25, sy - 0.9, sx + 0.25, sy + 0.9, fill=sparkle_fill)
            px.rect(sx - 0.9, sy - 0.25, sx + 0.9, sy + 0.25, fill=sparkle_fill)

        if pulse > 0.85:
            px.ellipse(cx - 3.3, cy - 3.3, cx + 3.3, cy + 3.3, fill=(255, 247, 212, 70), outline=None)

    sprite = rasterize_logical(LOGICAL, SCALE, painter)
    return bottom_center_canvas(sprite, FRAME)


def _coin_frame(animation: str, frame_idx: int, nframes: int) -> Image.Image:
    phase = frame_idx % max(1, nframes)
    widths = [7.6, 4.2, 2.4, 4.2, 7.6, 4.8]
    inner = [5.2, 2.2, 0.8, 2.2, 5.2, 2.8]
    w = widths[phase % len(widths)]
    iw = inner[phase % len(inner)]
    left = 14.0 - w / 2.0
    right = 14.0 + w / 2.0

    def painter(px) -> None:
        px.ellipse(left, 8.5, right, 20.5, fill=COIN_GOLD, outline=OUTLINE, width=0.8)
        if iw > 1.0:
            ileft = 14.0 - iw / 2.0
            iright = 14.0 + iw / 2.0
            px.ellipse(ileft, 10.2, iright, 18.8, fill=COIN_GOLD_LIGHT, outline=None)
        px.rect(13.4, 10.8, 14.8, 18.4, fill=OUTLINE)
        px.rect(12.2, 12.0, 15.6, 13.2, fill=OUTLINE)

    sprite = rasterize_logical(LOGICAL, SCALE, painter)
    frame = bottom_center_canvas(sprite, FRAME, offset_y=-4)
    return frame


SPECS: Dict[str, PropSpec] = {
    "super_mary_o_pipe": PropSpec(
        target_name="super_mary_o_pipe",
        display_name="Mary Pipe",
        rows=[("idle", 1, 150)],
        renderer=_pipe_frame,
        traits=("scenery", "pipe", "retro"),
    ),
    "super_mary_o_milk_carton": PropSpec(
        target_name="super_mary_o_milk_carton",
        display_name="Milk Carton Power-Up",
        rows=[("idle", 4, 125)],
        renderer=_milk_frame,
        traits=("pickup", "milk", "powerup", "retro"),
    ),
    "super_mary_o_spark_blossom": PropSpec(
        target_name="super_mary_o_spark_blossom",
        display_name="Spark Blossom Power-Up",
        rows=[("idle", 4, 125)],
        renderer=_spark_blossom_frame,
        traits=("pickup", "spark", "powerup", "retro"),
    ),
    "super_mary_o_star_wand": PropSpec(
        target_name="super_mary_o_star_wand",
        display_name="Starlight Wand Power-Up",
        rows=[("idle", 6, 90)],
        renderer=_star_wand_frame,
        traits=("pickup", "wand", "star", "invincibility", "magic", "retro"),
    ),
    "super_mary_o_cinder_beacon": PropSpec(
        target_name="super_mary_o_cinder_beacon",
        display_name="Cinder Beacon",
        rows=[("idle", 4, 115)],
        renderer=_cinder_beacon_frame,
        traits=("pickup", "lantern", "fire", "magic", "retro"),
    ),
    "super_mary_o_cosmic_quasar": PropSpec(
        target_name="super_mary_o_cosmic_quasar",
        display_name="Cosmic Quasar",
        rows=[("idle", 6, 90)],
        renderer=_cosmic_quasar_frame,
        traits=("pickup", "quasar", "cosmic", "invincibility", "magic", "retro"),
    ),
    "super_mary_o_gasoline_tank": PropSpec(
        target_name="super_mary_o_gasoline_tank",
        display_name="Gasoline Tank Power-Up",
        rows=[("idle", 4, 125)],
        renderer=_gas_tank_frame,
        traits=("pickup", "gasoline", "powerup", "retro"),
    ),
    "super_mary_o_coin": PropSpec(
        target_name="super_mary_o_coin",
        display_name="Mary Coin",
        rows=[("idle", 1, 120), ("spin", 6, 85)],
        renderer=_coin_frame,
        traits=("pickup", "coin", "currency", "retro"),
    ),
}



def _actor_metadata(spec: PropSpec) -> dict:
    return {
        "actor": {"character_id": f"prop_{spec.target_name}", "display_name": spec.display_name},
        "body": {
            "body_plan": "StaticProp",
            "body_kind": "Pickup",
            "mass_class": "Light",
            "locomotion_hint": "None",
            "traits": list(spec.traits),
        },
        "tags": list(spec.traits),
    }



def _render_spec(spec: PropSpec, out_dir: str | Path) -> List[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    outputs = build_sheet(
        target=spec.target_name,
        rows=spec.rows,
        render_fn=spec.renderer,
        out_dir=out_dir,
        frame_size=FRAME,
        label_width=LABEL_WIDTH,
        auto_crop=False,
        actor_metadata=_actor_metadata(spec),
    )
    return [
        outputs[k]
        for k in ("canonical", "canonical_transparent", "spritesheet", "yaml", "ron", "actor", "preview")
    ]



def render(out_dir: str | Path, **opts) -> List[Path]:
    rendered: List[Path] = []
    for spec in SPECS.values():
        rendered.extend(_render_spec(spec, out_dir))
    return rendered


TARGETS = {
    name: {"render": (lambda out_dir, _spec=spec, **opts: _render_spec(_spec, out_dir)), "actor_metadata": _actor_metadata(spec)}
    for name, spec in SPECS.items()
}
