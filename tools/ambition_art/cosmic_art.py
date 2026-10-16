"""Eternal Cosmic Mary-O: the painter of her frames.

Her ultimate form (Jon, 2026-10-11): a gown of the night sky, hair of
starlight in a long tail, wings of crystal that rise over her head, the ring
of a planet about her head, and a star over her cap. She is drawn on the body
of Mary-O v2 (`_draw_side_pose`, the pose tables of `_mary_o_v2_model`), so
each pose her other forms have, she has.

One function, `frame(stage, look)`, draws her from a `Look`: how much of each
part of the form she has, and where her wings are. A row of a sheet is a list
of `Look`s. No sparkle and no glow is in a frame: light about her is the
game's work, not her sheet's.

A `Stage` is the canvas of one sheet and where her body is in it. The
gameplay sheet and the transformation sheet have a stage each.
"""
from __future__ import annotations

import dataclasses
import math
import random
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

from .common import MaryPalette, rasterize_logical
from . import model as M
from .art import _draw_dead_front, _draw_side_pose, _side_pose_head_origin

Pose = M.Pose
#: Pixels to the logical unit. Her other forms are drawn at 3 and published at
#: two times that; this form is published as drawn, so its sheet is a quarter
#: of the area, and its catalog row states her height.
S = 3

#: Where the middle of her gameplay body is in her 24 by 32 frame, and where
#: her feet are (`BODY_BOX_CENTER_X` and `collision_bottom_px` of the model).
BODY_CENTER_X = 11.75
FEET_Y = 95.0 / 3.0
#: Her gameplay body, in logical units: the body of her grown forms.
BODY_W, BODY_H = 28.0 / 3.0, 28.0


@dataclass(frozen=True)
class Stage:
    """The canvas of a sheet, in logical units, and the place of her 24 by 32 frame in it."""

    w: int
    h: int
    ox: float
    oy: float

    @property
    def frame_px(self) -> tuple[int, int]:
        return (self.w * S, self.h * S)

    @property
    def feet_px(self) -> tuple[float, float]:
        return ((self.ox + BODY_CENTER_X) * S, (self.oy + FEET_Y) * S)

    def body_box_px(self) -> dict:
        fx, fy = self.feet_px
        return {"x": int(round(fx - BODY_W * S / 2.0)), "y": int(round(fy - BODY_H * S)), "w": int(round(BODY_W * S)), "h": int(round(BODY_H * S))}


OUTLINE = (28, 22, 19, 255)
NIGHT = (40, 32, 104, 255)
NIGHT_HI = (86, 62, 176, 255)
VIOLET = (140, 84, 214, 255)
PINK = (255, 128, 196, 255)
CYAN = (126, 228, 255, 255)
GOLD = (255, 208, 84, 255)
GOLD_HI = (255, 244, 205, 255)
PEARL = (255, 250, 246, 255)
STARLIGHT = (250, 232, 255, 255)
WHITE = (255, 255, 255, 255)

COSMIC = MaryPalette(cap=(88, 58, 190, 255), shirt=PINK, overalls=NIGHT, buttons=GOLD, gloves=WHITE,
                     hair=STARLIGHT, skin=(252, 198, 152, 255), shoes=GOLD, accent=CYAN)
COSMIC_FORM = dataclasses.replace(M.FIRE_FORM, palette=COSMIC)
IDLE_HEAD = _side_pose_head_origin(COSMIC_FORM, Pose())


@dataclass
class Look:
    pose: Pose = field(default_factory=Pose)
    anim: str = "idle"
    cosmic: bool = True       # the form under the light: fire, or cosmic
    hair: float = 1.0         # how long the long hair is, 0 to 1
    wing: float = 1.0         # how long the feathers are, 0 to 1
    beat: float = 0.0         # the wing about its root, degrees: + is the down stroke
    fan: float = 1.0          # how far apart the feathers are
    ring: float = 1.0         # how much of the ring about her head is there, 0 to 1
    crown: tuple | None = (0.0, 1.0, -90.0)   # the star over her cap: (how far above its place, size, turn)
    light: float = 0.0        # 1: she is a figure of light
    reveal: float = 0.0       # the part of the figure, from her feet up, that is not light
    spin: float = 1.0         # her width, for a turn about her own middle: -1 is her other side
    lift: float = 0.0         # how far off the ground she is
    sway: float = 0.0         # her hair and wings in the air
    burst: float = 0.0        # the star behind her, 0 to 1
    burst_turn: float = 0.0
    column: float = 0.0       # the column of light she stands in, 0 to 1
    sweep: float | None = None  # a ring of light about her at this part of her height (0 feet, 1 head)
    wing_boost: float = 0.9   # the small wings of the fire form (when she is not cosmic)


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def ramp(stops, t):
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            return lerp(c0, c1, (t - t0) / max(t1 - t0, 1e-6))
    return stops[-1][1]


class Layer:
    """A picture in logical units. Each shape has the dark outline of her art."""

    def __init__(self, stage: Stage):
        self.stage = stage
        self.image = Image.new("RGBA", stage.frame_px, (0, 0, 0, 0))

    def _pts(self, pts):
        return [(int(round(x * S)), int(round(y * S))) for x, y in pts]

    def poly(self, pts, fill, outline=OUTLINE, gradient=None):
        mask = Image.new("L", self.image.size, 0)
        ImageDraw.Draw(mask).polygon(self._pts(pts), fill=255)
        box = mask.getbbox()
        if box is None:
            return
        if gradient is None:
            paint = Image.new("RGBA", self.image.size, fill)
        else:
            (ax, ay), (bx, by), stops = gradient
            paint = Image.new("RGBA", self.image.size)
            px = paint.load()
            dx, dy = (bx - ax) * S, (by - ay) * S
            d2 = dx * dx + dy * dy or 1.0
            for y in range(box[1], box[3]):
                for x in range(box[0], box[2]):
                    t = ((x - ax * S) * dx + (y - ay * S) * dy) / d2
                    # Steps, not a smooth ramp: her art is flat colours.
                    px[x, y] = ramp(stops, round(t * 6) / 6)
        self.image.paste(paint, (0, 0), mask)
        if outline is not None:
            ImageDraw.Draw(self.image).line(self._pts(pts) + self._pts(pts[:1]), fill=outline, width=1)

    def dot(self, x, y, colour):
        ImageDraw.Draw(self.image).point((int(x * S), int(y * S)), fill=colour)

    def star(self, cx, cy, outer, inner, fill, outline=OUTLINE, turn=-90.0, points=5):
        n = points * 2
        pts = [(cx + (outer if k % 2 == 0 else inner) * math.cos(math.radians(turn + k * 360.0 / n)),
                cy + (outer if k % 2 == 0 else inner) * math.sin(math.radians(turn + k * 360.0 / n))) for k in range(n)]
        self.poly(pts, fill, outline)


def feather(layer, bx, by, angle, length, width, tip_stops):
    """One feather from `(bx, by)`: `angle` is from the +x axis, up is positive."""
    if length < 1.0:
        return
    a = math.radians(angle)
    ux, uy = math.cos(a), -math.sin(a)
    nx, ny = -uy, ux
    tip = (bx + ux * length, by + uy * length)
    belly = (bx + ux * length * 0.55, by + uy * length * 0.55)
    pts = [(bx - nx * width * 0.35, by - ny * width * 0.35), (belly[0] - nx * width, belly[1] - ny * width), tip,
           (belly[0] + nx * width * 0.7, belly[1] + ny * width * 0.7), (bx + nx * width * 0.35, by + ny * width * 0.35)]
    layer.poly(pts, PEARL, gradient=((bx, by), tip, tip_stops))


#: The feathers of a wing at rest: angle, length, width. The middle of the fan is `WING_MEAN`.
UPPER = ((172, 15, 2.9), (150, 21, 3.3), (128, 24, 3.4), (108, 20, 3.0))
LOWER = ((222, 9, 2.2), (200, 12, 2.5))
WING_MEAN = 140.0


def wings(layer, bx, by, look, far=False):
    """The wing on her back. `look.beat` turns it about its root, and
    `look.fan` opens or closes the fan of its feathers."""
    tips = [(0.0, PEARL), (0.5, PEARL), (0.78, CYAN), (1.0, PINK)]
    beat, fan, size = look.beat, look.fan, look.wing
    if far:
        tips = [(0.0, (206, 198, 240, 255)), (0.6, (180, 170, 232, 255)), (1.0, VIOLET)]
        beat, fan = beat * 0.85 - 8.0, fan * 1.05
    if size <= 0.0:
        return
    for angle, length, width in UPPER:
        feather(layer, bx, by, WING_MEAN + (angle - WING_MEAN) * fan + beat, length * size, width * (0.6 + 0.4 * size), tips)
    if not far:
        for angle, length, width in LOWER:
            feather(layer, bx, by + 1.2, angle + beat * 0.45, length * size, width * (0.6 + 0.4 * size), tips)


def hair(layer, hx, hy, look):
    """Long hair of starlight from the back of her head, to under her knees."""
    t, sway = look.hair, look.sway
    if t <= 0.05:
        return
    full = [(0.0, 0.0), (-3.5, 4 + sway), (-5.5, 10 + sway * 2), (-5.0, 16 + sway * 2), (-8.5, 21 + sway * 3), (-15.0, 23.5 + sway * 4)]
    spine = [(hx + x * t, hy + y * t) for x, y in full]
    widths = [w * (0.55 + 0.45 * t) for w in (1.6, 2.4, 2.7, 2.4, 1.8, 0.2)]
    left, right = [], []
    for k, (x, y) in enumerate(spine):
        x0, y0 = spine[max(k - 1, 0)]
        x1, y1 = spine[min(k + 1, len(spine) - 1)]
        d = math.hypot(x1 - x0, y1 - y0) or 1.0
        nx, ny = -(y1 - y0) / d, (x1 - x0) / d
        left.append((x + nx * widths[k], y + ny * widths[k]))
        right.append((x - nx * widths[k], y - ny * widths[k]))
    stops = [(0.0, STARLIGHT), (0.35, (255, 196, 236, 255)), (0.6, CYAN), (0.85, VIOLET), (1.0, NIGHT_HI)]
    layer.poly(left + right[::-1], STARLIGHT, gradient=(spine[0], spine[-1], stops))
    if t >= 1.0:
        # Stars in her hair: a part of her, as the stars of her gown are.
        rng = random.Random(7)
        for _ in range(6):
            u = rng.uniform(0.35, 0.95) * (len(spine) - 1)
            i = min(int(u), len(spine) - 2)
            layer.dot(spine[i][0] + (spine[i + 1][0] - spine[i][0]) * (u - i) + rng.uniform(-0.8, 0.8),
                      spine[i][1] + (spine[i + 1][1] - spine[i][1]) * (u - i) + rng.uniform(-1.0, 1.0), GOLD_HI)


def ring(layer, cx, cy, rx, ry, tilt, front, part=1.0, colour=GOLD, stars=True, thick=0.55):
    """Half of a ring, as a planet has: the far half or the near half."""
    if part <= 0.0:
        return
    a0 = 0.0 if front else 180.0
    a1 = a0 + 180.0 * min(part, 1.0)
    t = math.radians(tilt)

    def at(deg, grow):
        a = math.radians(deg)
        x, y = (rx + grow) * math.cos(a), (ry + grow * 0.4) * math.sin(a)
        return (cx + x * math.cos(t) - y * math.sin(t), cy + x * math.sin(t) + y * math.cos(t))

    steps = [a0 + (a1 - a0) * k / 20 for k in range(21)]
    layer.poly([at(d, thick) for d in steps] + [at(d, -thick) for d in reversed(steps)], colour)
    if stars and part >= 1.0:
        for deg in ((40, 150) if front else (215, 320)):
            x, y = at(deg, 0.0)
            layer.star(x, y, 1.5, 0.65, GOLD_HI)


def night_gown(body):
    """Her gown: the ivory of the fire form becomes the night, with stars in it."""
    px = body.load()
    rng = random.Random(3)
    ivory, orange, orange_dark, gold_dark = (255, 250, 239, 255), (255, 116, 38, 255), (211, 70, 25, 255), (217, 126, 28, 255)
    ys = [y for y in range(body.height) for x in range(body.width) if px[x, y] == ivory]
    y0, y1 = (min(ys), max(ys)) if ys else (0, 1)
    for y in range(body.height):
        for x in range(body.width):
            c = px[x, y]
            if c == ivory:
                t = (y - y0) / max(y1 - y0, 1)
                px[x, y] = ramp([(0.0, NIGHT), (0.55, NIGHT_HI), (0.85, VIOLET), (1.0, PINK)], round(t * 5) / 5)
                if rng.random() < 0.045:
                    px[x, y] = GOLD_HI
            elif c == orange:
                px[x, y] = GOLD
            elif c == orange_dark:
                px[x, y] = (214, 150, 40, 255)
            elif c == gold_dark:
                px[x, y] = GOLD_HI
    return body


#: The layers of her that are her body: what a barrier about her is drawn
#: about. Her figure, and no more (Jon, 2026-10-11): her long hair, her wings,
#: the ring about her head and the star of her crown are not her body.
BODY_TRACKS = ("body",)


def figure_layers(stage: Stage, look: Look):
    """Her, as the layers she is made of, from the farthest: `(name, image)`.

    The names are the tracks of her part flipbook (`mary_o_v2_cosmic.py`), so a
    reader in the game can tell her body from her wings."""
    OX, W = stage.ox, stage.w
    dead = look.pose.mode == "dead"

    def paint(px):
        form = COSMIC_FORM if look.cosmic else M.FIRE_FORM
        if dead:
            _draw_dead_front(px, form, look.pose)
        elif look.cosmic:
            _draw_side_pose(px, form, look.pose, animation=look.anim, wing_boost=0.0, sleeve_wing_boost=0.0)
        else:
            _draw_side_pose(px, form, look.pose, animation=look.anim, wing_boost=look.wing_boost, sleeve_wing_boost=look.wing_boost)

    body = rasterize_logical(M.LOGICAL_SIZE, S, paint)
    if look.cosmic:
        body = night_gown(body)
    oy = stage.oy - look.lift
    layers = []

    def layer(name):
        made = Layer(stage)
        layers.append((name, made.image))
        return made

    # Where this pose puts her head, from where her idle has it: the things
    # she wears on her head and her back go with it.
    if dead:
        hdx, hdy = 0.0, 0.0
    else:
        hx, hy, _ = _side_pose_head_origin(COSMIC_FORM, look.pose)
        hdx, hdy = hx - IDLE_HEAD[0], hy - IDLE_HEAD[1]
    head = (OX + 10.2 + hdx, oy + 4.2 + hdy)
    worn = look.cosmic and not dead
    if worn:
        wings(layer("far_wing"), OX + 9.0 + hdx, oy + 12.0 + hdy, look, far=True)
        ring(layer("ring_back"), head[0], head[1] - 0.6, 10.5, 3.0, -14.0, front=False, part=look.ring)
        hair(layer("hair"), OX + 5.2 + hdx, oy + 7.0 + hdy, look)
        wings(layer("near_wing"), OX + 7.0 + hdx, oy + 13.6 + hdy, look)
    if look.sweep is not None:
        ring(layer("sweep_back"), OX + 10.5, oy + 31.0 - look.sweep * 30.0, 9.0, 2.2, 0.0, front=False, colour=WHITE, stars=False, thick=0.7)
    layer("body").image.alpha_composite(body, (int(round(OX * S)), int(round(oy * S))))
    if worn:
        ring(layer("ring_front"), head[0], head[1] - 0.6, 10.5, 3.0, -14.0, front=True, part=look.ring)
    if look.sweep is not None:
        ring(layer("sweep_front"), OX + 10.5, oy + 31.0 - look.sweep * 30.0, 9.0, 2.2, 0.0, front=True, colour=WHITE, stars=False, thick=0.7)
    return layers, oy, head


def figure(stage: Stage, look: Look):
    """Her, with no thing of the transformation behind her, as one picture."""
    OX = stage.ox
    layers, oy, head = figure_layers(stage, look)
    image = Layer(stage).image
    for _name, made in layers:
        image.alpha_composite(made)
    if look.light > 0.0:
        # A figure of light: each pixel of her above the line of the reveal.
        px = image.load()
        line = (oy + 32.0 - look.reveal * 46.0) * S
        top, bottom = (oy - 12.0) * S, (oy + 32.0) * S
        for y in range(image.height):
            if y >= line:
                break
            shade = ramp([(0.0, WHITE), (0.45, (255, 214, 240, 255)), (0.8, (200, 236, 255, 255)), (1.0, WHITE)], round((y - top) / (bottom - top) * 8) / 8)
            for x in range(image.width):
                r, g, b, a = px[x, y]
                if a:
                    px[x, y] = lerp((r, g, b, a), shade[:3] + (a,), look.light)
    if look.spin != 1.0:
        # A turn about her own middle: her picture, made narrow, and her other side.
        cx = int(round((OX + BODY_CENTER_X) * S))
        half = max(cx, image.width - cx)
        wide = Image.new("RGBA", (half * 2, image.height), (0, 0, 0, 0))
        wide.alpha_composite(image, (half - cx, 0))
        if look.spin < 0.0:
            wide = wide.transpose(Image.FLIP_LEFT_RIGHT)
        width = max(2, int(round(wide.width * abs(look.spin))))
        narrow = wide.resize((width, wide.height), Image.NEAREST)
        image = Image.new("RGBA", image.size, (0, 0, 0, 0))
        left = cx - width // 2
        image.alpha_composite(narrow.crop((max(0, -left), 0, min(width, image.width - left), narrow.height)), (max(0, left), 0))
    return image, oy, head


def crown_layer(stage: Stage, look: Look, oy: float, head) -> Image.Image:
    """The star over her head: the quasar, made a crown."""
    dy, size, turn = look.crown
    front = Layer(stage)
    front.star(head[0], oy - 6.2 - dy + (head[1] - (oy + 4.2)), 4.2 * size, 1.8 * size, GOLD, turn=turn)
    front.star(head[0], oy - 6.2 - dy + (head[1] - (oy + 4.2)), 2.2 * size, 0.95 * size, GOLD_HI, outline=None, turn=turn)
    return front.image


def is_of_parts(look: Look) -> bool:
    """True when the frame of `look` is its layers and no more: no light on
    the whole figure, no turn, and no thing of the transformation behind her."""
    return look.light <= 0.0 and look.spin == 1.0 and look.sweep is None and look.column <= 0.0 and look.burst <= 0.0


def frame(stage: Stage, look: Look) -> Image.Image:
    """One frame: the things of the transformation behind her, her, and the star of her crown."""
    if is_of_parts(look):
        # Each layer through the seam that records it, so the frame is
        # published as its parts also.
        layers, oy, head = figure_layers(stage, look)
        if look.crown is not None and look.pose.mode != "dead":
            layers.append(("crown", crown_layer(stage, look, oy, head)))
        image = Layer(stage).image
        for name, made in layers:
            if made.getbbox() is not None:
                image.alpha_composite(made)
        return image
    image, oy, head = figure(stage, look)
    back = Layer(stage)
    cx = stage.ox + BODY_CENTER_X
    if look.column > 0.0:
        for half, colour in ((9.0, (255, 150, 214, int(110 * look.column))), (6.0, (255, 214, 240, int(150 * look.column))), (3.0, (255, 255, 255, int(190 * look.column)))):
            back.poly([(cx - half, 0), (cx + half, 0), (cx + half, stage.h), (cx - half, stage.h)], colour, None)
    if look.burst > 0.0:
        middle = (cx, oy + 14.0)
        back.star(*middle, 34.0 * look.burst, 13.0 * look.burst, (255, 170, 226, 255), None, turn=look.burst_turn, points=12)
        back.star(*middle, 27.0 * look.burst, 11.0 * look.burst, GOLD, None, turn=look.burst_turn + 15.0, points=12)
        back.star(*middle, 19.0 * look.burst, 9.0 * look.burst, GOLD_HI, None, turn=look.burst_turn, points=12)
    back.image.alpha_composite(image)
    if look.crown is not None and look.pose.mode != "dead":
        back.image.alpha_composite(crown_layer(stage, look, oy, head))
    return back.image
