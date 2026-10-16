"""Authored data for Mary-O v2.

This module contains no drawing code. It owns palettes, form geometry, pose
records, animation row declarations, and palette-transition helpers.
"""

from __future__ import annotations

import dataclasses

from dataclasses import dataclass, replace
from typing import Dict, List, Tuple

from .common import MaryPalette

TARGET_BASE = "mary_o_v2"
OUTPUT_RESOLUTION_SCALE = 2.0
AUTHORING_FRAME_SIZE = (80, 96)
FRAME_SIZE = tuple(
    round(value * OUTPUT_RESOLUTION_SCALE)
    for value in AUTHORING_FRAME_SIZE
)
LOGICAL_SIZE = (24, 32)
SCALE = 3
LABEL_WIDTH = round(122 * OUTPUT_RESOLUTION_SCALE)

MARY_NORMAL = MaryPalette(
    cap=(188, 48, 92, 255),
    shirt=(223, 83, 76, 255),
    overalls=(38, 135, 160, 255),
    buttons=(255, 220, 91, 255),
    gloves=(248, 245, 239, 255),
    hair=(94, 54, 36, 255),
    skin=(251, 194, 148, 255),
    shoes=(96, 61, 42, 255),
    accent=(255, 155, 189, 255),
)

MARY_FIRE = MaryPalette(
    cap=(236, 88, 58, 255),
    shirt=(242, 112, 56, 255),
    overalls=(246, 242, 232, 255),
    buttons=(255, 190, 75, 255),
    gloves=(255, 251, 246, 255),
    hair=(98, 55, 35, 255),
    skin=(252, 198, 152, 255),
    shoes=(103, 65, 43, 255),
    accent=(255, 219, 108, 255),
)

MARY_FIRE_FLASH = MaryPalette(
    cap=(255, 176, 120, 255),
    shirt=(255, 237, 162, 255),
    overalls=(255, 252, 248, 255),
    buttons=(255, 232, 152, 255),
    gloves=(255, 255, 250, 255),
    hair=MARY_NORMAL.hair,
    skin=MARY_NORMAL.skin,
    shoes=(168, 116, 76, 255),
    accent=(255, 242, 178, 255),
)

MARY_FIRE_BLAST = MaryPalette(
    cap=(255, 246, 208, 255),
    shirt=(255, 255, 252, 255),
    overalls=(255, 255, 255, 255),
    buttons=(255, 240, 174, 255),
    gloves=(255, 255, 255, 255),
    hair=MARY_NORMAL.hair,
    skin=MARY_NORMAL.skin,
    shoes=(255, 226, 160, 255),
    accent=(255, 228, 148, 255),
)

RIBBON_PINK = (231, 120, 170, 255)
BROOCH_GOLD = (255, 208, 84, 255)
BROOCH_LIGHT = (255, 244, 205, 255)
EMBER_ORANGE = (255, 159, 76, 255)
EMBER_CORE = (255, 240, 190, 255)
BLUSH = (244, 157, 146, 255)
LIP = (178, 89, 91, 255)
WING_PEARL = (255, 246, 235, 255)
AURA_PINK = (244, 162, 202, 255)
AURA_GOLD = (255, 213, 118, 255)

# A form-transition clip is authored on the sheet of the form it ARRIVES AT, so
# the runtime plays it from the identity it has already switched to and nothing
# has to defer a swap to show it. Read the three lists together and each sheet
# answers "how did I get here":
#
#   short:  shrink (from tall), big_shrink (from fire)
#   tall:   grow   (from short), shrink     (from fire)
#   fire:   transform (from tall)
#
# The frames themselves draw whatever silhouettes the transition needs — the
# short sheet's `shrink` opens on the TALL body — so hosting is about who OWNS
# the clip, not about which forms appear in it.
SHORT_ROWS: List[Tuple[str, int, int]] = [
    ("idle", 1, 160),
    ("death", 1, 120),
    ("walk", 3, 95),
    ("jump", 1, 120),
    ("skid", 1, 110),
    ("climb", 2, 120),
    ("swim", 4, 100),
    ("shrink", 4, 85),
    ("big_shrink", 8, 85),
]

TALL_ROWS: List[Tuple[str, int, int]] = [
    ("idle", 1, 160),
    ("death", 1, 120),
    ("walk", 3, 95),
    ("jump", 1, 120),
    ("skid", 1, 110),
    ("crouch", 1, 120),
    ("crouch_walk", 3, 110),
    ("crouch_jump", 1, 120),
    ("climb", 2, 120),
    ("swim", 6, 100),
    ("grow", 4, 70),
    ("shrink", 6, 85),
]

FIRE_ROWS: List[Tuple[str, int, int]] = [
    ("idle", 1, 160),
    ("death", 1, 120),
    ("walk", 3, 95),
    ("jump", 1, 120),
    ("skid", 1, 110),
    ("crouch", 1, 120),
    ("crouch_walk", 3, 110),
    ("crouch_jump", 1, 120),
    ("climb", 2, 120),
    ("swim", 6, 100),
    # The engine names the row a firing body shows `shoot`. Three frames in the
    # 0.18 s that the pose holds: the reach, the release, the follow-through.
    ("shoot", 3, 60),
    ("transform", 11, 80),
]


@dataclass(frozen=True)
class Pose:
    bob: float = 0.0
    body_lean: float = 0.0
    head_dx: float = 0.0
    head_dy: float = 0.0
    arm_front_dx: float = 0.0
    arm_front_dy: float = 0.0
    arm_back_dx: float = 0.0
    arm_back_dy: float = 0.0
    leg_front_dx: float = 0.0
    leg_front_dy: float = 0.0
    leg_back_dx: float = 0.0
    leg_back_dy: float = 0.0
    arm_front_angle: float | None = None
    arm_back_angle: float | None = None
    leg_front_angle: float | None = None
    leg_back_angle: float | None = None
    crouch: float = 0.0
    #: Extra drop of the TORSO alone, in the same authored units as `head_dx`.
    #: A crouch folds the body down into the legs; nothing else moves with it.
    body_dy: float = 0.0
    #: Vertical squash of the torso about its pivot. 1.0 is unsquashed.
    torso_scale: float = 1.0
    #: Vertical squash of the HEAD about its own pivot. 1.0 is unsquashed.
    #:
    #: Her head is most of what is left once the body folds, so squashing it is
    #: how a deep crouch stays a CHARACTER rather than a head with shoes: the
    #: crown comes down and the face goes wide, and the body underneath is still
    #: visible. Sinking the head instead buys the same height by hiding the
    #: torso behind it, which is what "her whole head became her body" looked
    #: like.
    head_scale: float = 1.0
    mode: str = "side"


# --- Authored gameplay collision box -----------------------------------------
#
# The sheet builder's default body box is the idle frame's ALPHA bbox, which
# swallows her cap tip, her ponytail, her sleeves, and (on fire) the flame
# frills. Colliding on any of those reads as unfair, and it also let the fire
# form drift 22% wider than the tall form purely on decoration. So the gameplay
# body is stated here instead of measured.
#
# Use one collision width for every form, centered on the shared leg column.
# Visual growth may widen decoration without changing gameplay width.
#
# Use one 56 px gameplay width for every form. It clears the narrow short-form
# drawing while still closely covering the grown torso.
BODY_BOX_WIDTH = 56
BODY_BOX_CENTER_X = 78.5

# Per-form top/bottom in frame pixels. The bottom is her shoe line, because the
# box bottom is what stands on the ground. The top is set below the cap's narrow
# tip so a ceiling catches her head, not her hat.
#
# The tall/short height ratio is held at the shipped 88/63 = 1.397 (168/120 =
# 1.400, a 0.2% difference), so every pipe and ceiling in the level still fits
# her exactly as it does today.


@dataclass(frozen=True)
class FormSpec:
    target_name: str
    display_name: str
    body_height: float
    leg_height: float
    body_width: float
    palette: MaryPalette
    power: str
    tall: bool
    magic_stage: int
    rows: List[Tuple[str, int, int]]
    collision_top_px: int
    collision_bottom_px: int
    # How far the ponytail hangs, as a fraction of the grown form's drop.
    #  hair is drawn from FIXED head-local polygons, so it does NOT shrink when
    # a form's body and legs do — halve the body without this and the ponytail
    # reaches past her feet, which is exactly what the first attempt looked like.
    hair_drop: float = 1.0
    #: How far the crouch sinks her head onto her shoulders, in authored units.
    #:
    #: A crouch is HALF HEIGHT — that is what `BodyMode::Crouching` does to her
    #: collision box, and the drawing has to agree or she ducks under a ceiling
    #: her art still occupies. Folding the body into the legs (`crouch`) and
    #: squashing the torso (`torso_scale`) get her to 75%; the last quarter has
    #: to come out of her NECK, because her head alone is most of what remains.
    #:
    #: ⛔ per-FORM, and not because the drawing differs — it does not. The two
    #: grown forms author collision tops 2 px apart (24 vs 22), so the halved
    #: box they have to reach differs by 1 px. Measured: ~6 px of art per unit.
    #: 0.0 for a form with no crouch row.
    crouch_head_dy: float = 0.0
    # Head scale relative to the grown form; short and grown forms use different
    # head/body/leg proportions.
    head_scale: float = 1.0
    # How far the head sits ABOVE the torso, in model units.  this is the knob
    # that puts the TOP OF HER HEAD on an exact world height: scaling the body to
    # reach a target moves every proportion, translating the head moves only
    # where the silhouette ends.
    head_offset: float = 10.0
    # Shift the TORSO (and the head riding on it) down, in model units.
    #  this is how a form reaches a target height without cramping: pulling the
    # HEAD down to shorten the silhouette buries the neck in the shoulders,
    # whereas dropping the whole body keeps the head's own spacing and lowers the
    # top of the sprite by the same amount.
    body_dy: float = 0.0
    # Vertical squish on the legs and feet — 1.0 leaves them as drawn. Separate
    # from `leg_height` because that moves where the hip sits; this shortens the
    # limb and its shoe together so a small form's feet stay in proportion.
    leg_squish: float = 1.0
    # Shift the TORSO sideways, in model units.  the head and the feet are
    # placed from their own anchors, so a re-proportioned torso can end up
    # offset from both — this is how it is brought back onto the line they
    # share, without moving anything that was already right.
    body_dx: float = 0.0
    # Nudge the WEST (back) arm alone, in model units — 6 frame px per unit.
    # Separate from `body_dx` because the two arms sit at different depths: the
    # back one reads against the hair and the front one against the torso, so a
    # re-proportioned form can need them apart.
    #:  how high the whole figure sits in its frame, in units (negative is
    #: up). The one lever that moves head, torso, arms, legs and shoes TOGETHER,
    #: so it corrects where a form stands without disturbing any of the relative
    #: nudges tuned against each other. Reach for this — not a second offset on
    #: one part — when the drawing sits off its shoe line.
    foot_dy: float = 0.0
    back_arm_dx: float = 0.0
    #  where the hanging back arm meets the shoulder. Authored per form because
    # the two forms' arms were tuned by eye at different sizes; the rig supplies
    # the shoulder, this says how far below it the arm hangs.
    back_arm_dy: float = 0.0
    # Nudge the EAST (front) arm alone — the sibling of `back_arm_dx`.
    front_arm_dx: float = 0.0
    # Vertical nudge for the EAST (front) arm alone.
    front_arm_dy: float = 0.0
    # Translate the LEG + FOOT assembly down, in model units, without moving the
    # torso, head or arms.  this is how a form recovers height after its legs
    # were shortened: the hip stays where it was placed and the stance reaches
    # further down, rather than the whole figure sliding.
    leg_dy: float = 0.0
    # Translate the LEG + FOOT assembly sideways (negative = west), in model
    # units — 6 frame px per unit.
    leg_dx: float = 0.0
    # Horizontal squish on the leg and its shoe, about the limb's own centre.
    # The vertical sibling of `leg_squish`; a stance can need narrowing without
    # being shortened.
    leg_squish_x: float = 1.0


#: Anchor fractions derived from the shipped grown form. Reusing fractions at
#: other sizes preserves part relationships instead of absolute pixel offsets.
#:
#:  the shoulders are ASYMMETRIC on purpose — this is a side view, so the near
#: shoulder sits at the body's edge and the far one is tucked behind the torso.
#: A symmetric rig would have quietly straightened her.
#
#  anchors are fractions of the AUTHORED body, measured from a torso EDGE.
#
# Every number here was solved from the shipped grown form, so the rig places
# its parts exactly where they already are and re-proportioning any other form
# carries them along.
#
# The torso's west edge is fixed while crouching widens eastward. Anchor the
# back shoulder, hips, and legs from that fixed edge; only the front shoulder
# follows the moving east edge.
#  written as the RATIOS they were solved from, against the grown form's
# authored 9.4-wide, 9.5-tall torso. A rounded decimal is off by a millionth of
# a unit, which is invisible until it lands on a pixel boundary and flips one
# scanline of a form that was supposed to be untouched.
_REF_W, _REF_H = 9.4, 9.5
SHOULDER_BACK_X = 1.8 / _REF_W  #: in from the WEST edge
SHOULDER_FRONT_X = 0.2 / _REF_W  #: in from the EAST edge, which crouch moves
SHOULDER_BACK_Y = 1.4 / _REF_H
SHOULDER_FRONT_Y = 1.2 / _REF_H
HIP_BACK_X = 3.0 / _REF_W
HIP_FRONT_X = 6.3 / _REF_W
#: where a hanging arm and a straight leg sit, same convention
#  solved from the grown form's ACTUAL hang, which was `-1.4` — not `-1.4 ×
# arm_k`, because `arm_k` clamps at 1.0 and the grown form is wider than the
# reference the arms were drawn for, so the clamp was silently active.
ARM_HANG_X = -1.4 / _REF_W
ARM_HANG_Y = 1.1 / _REF_H
LEG_BACK_X = 2.1 / _REF_W
LEG_FRONT_X = 5.1 / _REF_W

#  the FRONT view is symmetric, so its anchors hang off the MIDLINE rather
# than an edge. The front torso is drawn from `body_x + 1.2` and is
# `body_width` wide, so its midline is where the brooch star already sits.
DEAD_HIP_X = (-1.0 / _REF_W, 1.4 / _REF_W)  #: splayed, so not symmetric
DEAD_ARM_X = (-2.9 / _REF_W, 3.1 / _REF_W)
DEAD_WING_X = 0.1 / _REF_W
DEAD_SHOULDER_Y = 1.0 / _REF_H
DEAD_WING_Y = 2.3 / _REF_H
DEAD_HIP_Y = 0.3 / _REF_H


@dataclass(frozen=True)
class FormRig:
    """**Where every part of one form belongs, derived rather than authored.**

    ⭐⭐ **why this exists.** The art was written as one drawing at one size:
    heads, hands, buttons, sleeves, shoe highlights and fasteners all carried
    absolute offsets that happened to agree at the proportions they were drawn
    for. Re-proportioning broke that agreement one part at a time — SEVEN
    separate "X doesn't follow the body" defects in a single session, each found
    only by looking at a render — because nothing stated where anything belonged.

    A rig is that statement. Parts hang off ANCHORS and the anchors are computed
    from the form's own authored sizes, so changing a size moves everything
    together by construction rather than by remembering.

    The fractions are solved from the grown form, so migrating it onto the rig
    preserves its authored geometry. The short form is re-proportioned from its
    own dimensions instead of inheriting grown-form absolute offsets.
    Under the rig those nudges double-count — `leg_dx = -0.833` dragged her feet
    out from under her — so they are zeroed where the rig now does the work.
    """

    height: float
    foot_y: float
    crown_y: float
    head_bottom_y: float
    shoulder_y: float
    waist_y: float
    hip_y: float
    west_x: float
    east_x: float
    width: float
    body_height: float
    scale: float

    @property
    def centre_x(self) -> float:
        return (self.west_x + self.east_x) * 0.5

    @property
    def head_height(self) -> float:
        return self.head_bottom_y - self.crown_y

    @property
    def torso_height(self) -> float:
        return self.hip_y - self.head_bottom_y

    @property
    def leg_height(self) -> float:
        return self.foot_y - self.hip_y

    def _west(self, frac: float) -> float:
        return self.west_x + frac * self.width

    def shoulder(self, side: int) -> tuple[float, float]:
        """`side` −1 = west / back, +1 = east / front."""
        if side < 0:
            return (self._west(SHOULDER_BACK_X),
                    self.head_bottom_y + SHOULDER_BACK_Y * self.body_height)
        return (self.east_x - SHOULDER_FRONT_X * self.width,
                self.head_bottom_y + SHOULDER_FRONT_Y * self.body_height)

    def hip(self, side: int) -> tuple[float, float]:
        """⚠ the hip's height is TAKEN from the pose, not derived from the torso.

        A derived hip sits at the waistline of an UNCROUCHED torso, so legs drawn
        from it float off a crouching body.
        """
        return (self._west(HIP_BACK_X if side < 0 else HIP_FRONT_X), self.hip_y)

    def arm_hang(self) -> tuple[float, float]:
        """Where a straight, hanging back arm meets the body."""
        return (self._west(ARM_HANG_X),
                self.head_bottom_y + ARM_HANG_Y * self.body_height)

    def mid(self, frac: float) -> float:
        """A point on the FRONT view's midline, `frac` of a body-width aside."""
        return self.centre_x + frac * self.width

    def leg_x(self, side: int) -> float:
        return self._west(LEG_BACK_X if side < 0 else LEG_FRONT_X)


def rig_for(
    form: FormSpec,
    *,
    foot_y: float,
    hip_y: float,
    body_top: float,
    body_left: float,
    body_right: float,
    guide_height: float = 28.0,
) -> FormRig:
    """Build a rig from the POSE's resolved torso placement and the form's AUTHORED size.

    ⛔⛔ **the split between those two inputs is the whole correctness argument,
    and getting it wrong is not visible without a render.**

    - `body_top` / `body_left` / `hip_y` come from the POSE. They already carry
      crouch, lean and bob, so anchors ride along with a leaning or crouching
      body for free.
    - the FRACTIONS multiply the form's **authored** `body_height` / `body_width`
      — never the pose's momentarily-narrowed crouch width. The drawing has
      always placed shoulders at a fixed offset from the torso corner, so
      scaling them by a squashed width moves an arm that used to hold still.

    ⇒ two earlier attempts got this backwards. Deriving the hip from the form
    alone dropped crouch entirely (14,780 pixels moved on the approved grown
    form); scaling x by the crouched width moved every skid and crouch frame.
    Both rendered fine at a glance and were caught only by differencing against
    a control render.

    ⭐ so migrating a pose onto this rig is **pixel-identical by construction**:
    every anchor is still `body_left + k` and `body_top + k`, with `k` now
    expressed as a fraction of the size it was always secretly proportional to.
    That is what makes re-proportioning a form move its parts together.
    """
    total = form.body_height + form.leg_height + form.head_offset
    return FormRig(
        height=total,
        foot_y=foot_y,
        crown_y=body_top - form.head_offset,
        head_bottom_y=body_top,
        shoulder_y=body_top + form.body_height * SHOULDER_BACK_Y,
        waist_y=body_top + form.body_height * 0.62,
        hip_y=hip_y,
        west_x=body_left,
        east_x=body_right,
        width=form.body_width,
        body_height=form.body_height,
        scale=total / guide_height,
    )


def form_collision_box(form: FormSpec) -> Dict[str, int]:
    """The authored gameplay body box for one form, in frame pixels."""
    return {
        "x": int(round(BODY_BOX_CENTER_X - BODY_BOX_WIDTH / 2.0)),
        "y": form.collision_top_px,
        "w": BODY_BOX_WIDTH,
        "h": form.collision_bottom_px - form.collision_top_px,
    }


SHORT_FORM = FormSpec(
    target_name=TARGET_BASE,
    display_name="Mary-O v2",
    # Short form uses half the grown gameplay height. The head is intentionally
    # not halved so the one-tile form retains its large-head silhouette.
    body_height=3.0,
    leg_height=2.177,
    body_width=5.4,
    palette=MARY_NORMAL,
    power="short",
    tall=False,
    magic_stage=0,
    rows=SHORT_ROWS,
    # Her shoe line is unchanged at 190; the top follows the shorter art.
    collision_top_px=106,
    collision_bottom_px=190,
    # A one-brick character cannot wear a two-brick ponytail.
    hair_drop=0.52,
    head_scale=0.72,
    head_offset=9.666,
    body_dy=0.976,
    leg_squish=0.42,
    body_dx=1.5,
    back_arm_dx=1.0,
    front_arm_dx=0.333,
    leg_dy=1.14,
    leg_squish_x=0.6,
    #  ZERO on purpose. This was `-0.833`, a hand nudge that dragged the legs
    # west because the old code placed them at the GROWN form's absolute offsets
    # on a torso barely half as wide. The rig now places them at a fraction of
    # THIS form's width, so the nudge would double-count and put her feet out
    # from under her.
    leg_dx=0.0,
    front_arm_dy=0.333,
)

TALL_FORM = FormSpec(
    target_name=f"{TARGET_BASE}_tall",
    display_name="Mary-O v2 Tall",
    body_height=9.5,
    leg_height=8.6,
    body_width=9.4,
    palette=MARY_NORMAL,
    power="tall",
    tall=True,
    magic_stage=1,
    rows=TALL_ROWS,
    # Cap tip starts at y=8.
    collision_top_px=24,
    collision_bottom_px=192,
    head_scale=1.0,
    head_offset=10.0,
    body_dy=2.4,
    # Puts her crouched crown on y=108, which is `collision_bottom - 168/2`.
    # Smaller than it was because `head_scale` now carries most of the depth.
    crouch_head_dy=4.6,
)

FIRE_FORM = FormSpec(
    target_name=f"{TARGET_BASE}_fire",
    display_name="Mary-O v2 Fire",
    body_height=9.7,
    leg_height=8.5,
    body_width=9.6,
    palette=MARY_FIRE,
    power="fire",
    tall=True,
    magic_stage=2,
    rows=FIRE_ROWS,
    # Same height as tall: the fire form is the same body wearing flames.
    collision_top_px=22,
    collision_bottom_px=190,
    # Her drawn crown lands on y=108, the same as tall's — her authored box
    # sits 2 px ABOVE her drawing and keeps that margin in every pose, so the
    # PUBLISHED crouch rectangle lands on y=106 and is exactly half her
    # standing 168. Solved against the published rect, not the drawing.
    crouch_head_dy=4.4,
)


def _crouch_variants(crouch: Pose) -> Dict[str, List[Pose]]:
    """`crouch_walk` and `crouch_jump`, derived from the crouch she holds.

    Both are the crouch pose with the LIMBS moved — deriving them rather than
    re-authoring the stance is what keeps all three at the same height when the
    crouch's depth is retuned. A crouch walk that stood 8 px taller than the
    crouch it comes out of would pop on every step.

    The shuffle is deliberately smaller than her walk's stride: her knees are
    already folded, so the same swing would put a foot through the floor.
    """
    return {
        "crouch_walk": [
            dataclasses.replace(
                crouch, leg_front_dx=0.9, leg_back_dx=-0.7, arm_front_dx=1.1, arm_back_dx=-0.7
            ),
            dataclasses.replace(crouch, leg_front_dx=0.2, leg_back_dx=-0.2),
            dataclasses.replace(
                crouch, leg_front_dx=-0.6, leg_back_dx=1.0, arm_front_dx=-0.5, arm_back_dx=1.0
            ),
        ],
        # Legs tucked under a ducked body — the crouch is what she LEFT the
        # ground in, so it is what she keeps while she is off it.
        "crouch_jump": [
            dataclasses.replace(
                crouch,
                leg_front_angle=38,
                leg_back_angle=-34,
                arm_front_angle=132,
                arm_back_angle=-12,
            )
        ],
    }


def poses_for_form(form: FormSpec) -> Dict[str, List[Pose]]:
    """The pose table one form animates from.

    ⛔ **the ONE place that answers this.** The rig-document builder and the
    drawing each used to reach for `TALL_LIKE_POSES` / `SHORT_POSES` directly,
    which is two answers to one question — a crouch depth taught to the rig
    builder alone changed nothing at all, because the pixels come from the other
    one.

    The crouch's head drop is the one pose value that is a FORM fact rather than
    a shape fact: it is solved so her drawn crown lands on the halved collision
    box, and the two grown forms author that box 2 px apart. The shared pose
    keeps the shared shape; the form states its own depth.
    """
    poses = TALL_LIKE_POSES if form.tall else SHORT_POSES
    if "crouch" in poses:
        poses = {**poses, **_crouch_variants(poses["crouch"][0])}
    if form.crouch_head_dy and "crouch" in poses:
        poses = {
            **poses,
            **{
                row: [
                    dataclasses.replace(pose, head_dy=form.crouch_head_dy)
                    for pose in poses[row]
                ]
                for row in ("crouch", "crouch_walk", "crouch_jump")
                if row in poses
            },
        }
    return poses


def _lerp_rgba(a: tuple[int, int, int, int], b: tuple[int, int, int, int], t: float) -> tuple[int, int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def _mix_outfit_palette(base: MaryPalette, target: MaryPalette, t: float) -> MaryPalette:
    return MaryPalette(
        cap=_lerp_rgba(base.cap, target.cap, t),
        shirt=_lerp_rgba(base.shirt, target.shirt, t),
        overalls=_lerp_rgba(base.overalls, target.overalls, t),
        buttons=_lerp_rgba(base.buttons, target.buttons, t),
        gloves=_lerp_rgba(base.gloves, target.gloves, t),
        hair=base.hair,
        skin=base.skin,
        shoes=_lerp_rgba(base.shoes, target.shoes, t),
        accent=_lerp_rgba(base.accent, target.accent, t),
    )


def _form_with_palette(form: FormSpec, palette: MaryPalette) -> FormSpec:
    return replace(form, palette=palette)


def _transition_form(form: FormSpec, palette: MaryPalette, *, stage: float | None = None, power: str | None = None) -> FormSpec:
    updates = {"palette": palette}
    if stage is not None:
        updates["magic_stage"] = stage
    if power is not None:
        updates["power"] = power
    return replace(form, **updates)


def _magic_stage_value(form: FormSpec) -> float:
    return float(form.magic_stage)


def _fire_transition_t(form: FormSpec) -> float:
    return max(0.0, min(1.0, _magic_stage_value(form) - 1.0))


def _fire_accessory_t(form: FormSpec) -> float:
    return max(0.0, min(1.0, (_magic_stage_value(form) - 1.35) / 0.65))


SHORT_POSES: Dict[str, List[Pose]] = {
    "idle": [Pose()],
    "death": [Pose(mode="dead", bob=-4.2)],
    # Her arms SWING about the shoulder, counter to her legs: the front arm
    # goes back while the front leg goes forward. Before, each arm kept its
    # angle and moved as a whole (`arm_*_dx` / `arm_*_dy`), so the arms slid
    # on the body and did not swing. She is drawn three-quarter on, with one
    # shoulder on each side of her body: the forward swing of the back arm and
    # the back swing of the front arm go across her body, and are smaller.
    "walk": [
        Pose(
            body_lean=0.5,
            arm_front_angle=-14,
            arm_front_dy=0.3,
            arm_back_angle=18,
            arm_back_dy=-0.4,
            leg_front_dx=1.3,
            leg_back_dx=-0.9,
            #  A LIFT, and this was `+1.0` — a SINK. `+dy` is down, so the
            # trailing leg was extended THROUGH the floor at toe-off: measured
            # 1.00u past her own standing line on the small form and 1.33u on the
            # grown one, which is the whole of why her walk frames were the ones
            # the frame-clipping guard named. A foot pushing off rises.
            leg_back_dy=-1.0,
        ),
        Pose(
            # The passing pose is the HIGHEST beat of a walk, not the lowest;
            # `+0.4` sank it 0.33u below the standing line for nothing.
            bob=0.0,
            arm_front_angle=7,
            arm_back_angle=-3,
            leg_front_dx=0.2,
            leg_back_dx=-0.2,
        ),
        Pose(
            body_lean=-0.4,
            arm_front_angle=28,
            arm_front_dy=-0.4,
            arm_back_angle=-24,
            arm_back_dy=0.3,
            leg_front_dx=-0.8,
            leg_front_dy=-1.0,
            leg_back_dx=1.4,
        ),
    ],
    "jump": [
        Pose(
            bob=-1.8,
            arm_front_dx=0.6,
            arm_front_dy=-0.4,
            arm_back_dx=-0.5,
            arm_back_dy=0.3,
            arm_front_angle=145,
            arm_back_angle=-18,
            leg_front_angle=45,
            leg_back_angle=-45,
        ),
    ],
    "skid": [
        Pose(
            mode="lookback",
            body_lean=-1.6,
            head_dx=-1.1,
            arm_front_dx=0.5,
            arm_front_dy=-0.5,
            arm_back_dx=0.8,
            arm_back_dy=1.0,
            leg_front_angle=-36,
            leg_back_angle=-58,
            leg_front_dy=0.5,
            leg_back_dy=1.0,
        ),
    ],
    "climb": [
        Pose(mode="climb", bob=-0.2, arm_front_angle=88, arm_back_angle=82, leg_front_angle=92, leg_back_angle=86),
        Pose(mode="climb", bob=0.2, arm_front_angle=126, arm_back_angle=112, leg_front_angle=54, leg_back_angle=68),
    ],
    "swim": [
        Pose(mode="swim", bob=-0.7, arm_front_angle=125, arm_back_angle=45, leg_front_angle=25, leg_back_angle=-12),
        Pose(mode="swim", bob=-0.9, arm_front_angle=92, arm_back_angle=12, leg_front_angle=5, leg_back_angle=18),
        Pose(mode="swim", bob=-0.5, arm_front_angle=48, arm_back_angle=-25, leg_front_angle=-18, leg_back_angle=28),
        Pose(mode="swim", bob=-0.8, body_lean=-0.2, arm_front_angle=8, arm_back_angle=78, leg_front_angle=16, leg_back_angle=-22),
    ],
}

TALL_LIKE_POSES: Dict[str, List[Pose]] = {
    "idle": [Pose()],
    "death": [Pose(mode="dead", bob=-4.4)],
    # The arm swing of the short form (see `SHORT_POSES`).
    "walk": [
        Pose(
            body_lean=0.5,
            arm_front_angle=-14,
            arm_front_dy=0.3,
            arm_back_angle=18,
            arm_back_dy=-0.4,
            leg_front_dx=1.4,
            leg_back_dx=-1.0,
            leg_back_dy=-1.2,
        ),
        Pose(
            bob=0.0,
            arm_front_angle=7,
            arm_back_angle=-3,
            leg_front_dx=0.3,
            leg_back_dx=-0.2,
        ),
        Pose(
            body_lean=-0.5,
            arm_front_angle=28,
            arm_front_dy=-0.4,
            arm_back_angle=-24,
            arm_back_dy=0.3,
            leg_front_dx=-0.8,
            leg_front_dy=-1.1,
            leg_back_dx=1.5,
        ),
    ],
    "jump": [
        Pose(
            bob=-2.0,
            arm_front_dx=0.8,
            arm_front_dy=-0.5,
            arm_back_dx=-0.6,
            arm_back_dy=0.4,
            arm_front_angle=148,
            arm_back_angle=-22,
            leg_front_angle=45,
            leg_back_angle=-32,
        ),
    ],
    "skid": [
        Pose(
            mode="lookback",
            body_lean=-1.8,
            head_dx=-1.5,
            arm_front_dx=0.7,
            arm_front_dy=-0.5,
            arm_back_dx=1.0,
            arm_back_dy=1.1,
            leg_front_angle=-38,
            leg_back_angle=-62,
            leg_front_dy=0.6,
            leg_back_dy=1.2,
        ),
    ],
    "crouch": [
        Pose(
            mode="crouch",
            crouch=2.4,
            # placed by hand on the pose sheet, then read back
            body_dy=4.28,
            torso_scale=0.5,
            # Her head is most of what is left once the body folds, so the last
            # of the depth comes out of the HEAD rather than out of her neck: at
            # 1.0 the crown only reaches the halved box by sinking far enough to
            # hide the torso behind it, and she reads as a head with shoes.
            # Swept 1.0/0.85/0.75/0.65 against the drawing — 0.7 is where the
            # dress and both legs are back and the face is still hers.
            head_scale=0.7,
            head_dx=0.6,
            arm_front_dx=0.8,
            arm_back_dx=-0.4,
            leg_front_dx=0.3,
            leg_back_dx=-0.2,
        )
    ],
    "climb": [
        Pose(mode="climb", bob=-0.2, arm_front_angle=88, arm_back_angle=82, leg_front_angle=92, leg_back_angle=86),
        Pose(mode="climb", bob=0.2, arm_front_angle=126, arm_back_angle=112, leg_front_angle=54, leg_back_angle=68),
    ],
    "swim": [
        Pose(mode="swim", bob=-0.6, arm_front_angle=132, arm_back_angle=52, leg_front_angle=30, leg_back_angle=-10),
        Pose(mode="swim", bob=-0.8, arm_front_angle=108, arm_back_angle=25, leg_front_angle=15, leg_back_angle=6),
        Pose(mode="swim", bob=-1.0, arm_front_angle=82, arm_back_angle=-8, leg_front_angle=-2, leg_back_angle=18),
        Pose(mode="swim", bob=-0.8, arm_front_angle=48, arm_back_angle=-35, leg_front_angle=-20, leg_back_angle=26),
        Pose(mode="swim", bob=-0.6, arm_front_angle=18, arm_back_angle=8, leg_front_angle=6, leg_back_angle=-16),
        Pose(mode="swim", bob=-0.7, body_lean=-0.2, arm_front_angle=2, arm_back_angle=88, leg_front_angle=22, leg_back_angle=-24),
    ],
    # She throws the spark with her front hand. The game makes the spark at the
    # hand of the MIDDLE frame (the release), so that frame has the longest
    # reach. No frame draws an orb: the spark is its own sprite from the tick
    # she fires.
    "shoot": [
        Pose(mode="fireball", body_lean=0.3, arm_front_angle=62, arm_back_angle=-20, leg_front_dx=0.5),
        Pose(
            mode="fireball",
            body_lean=0.8,
            arm_front_angle=96,
            arm_back_angle=-38,
            leg_front_dx=1.0,
            leg_back_dx=-0.5,
        ),
        Pose(
            mode="fireball",
            body_lean=0.5,
            arm_front_angle=76,
            arm_back_angle=-24,
            leg_front_dx=0.8,
            leg_back_dx=-0.3,
        ),
    ],
}

#: The last frame of `transform`: she holds the orb of her new power in her
#: front hand. The frame draws the orb; this pose puts the hand under it.
FIRE_ORB_POSE = Pose(
    mode="fireball",
    body_lean=0.3,
    arm_front_angle=92,
    arm_back_angle=-12,
    leg_front_dx=0.8,
)

ACTOR_METADATA_BASE = {
    "body": {
        "body_plan": "HumanoidBiped",
        "mass_class": "Light",
        "locomotion_hint": "Walk",
    },
    "capabilities": {
        "traversal": {
            "walk": True,
            "jump": {"height_px": 48, "distance_px": 80, "source": "super_mary_o"},
            "climb": None,
            "crawl": None,
            "fly": None,
            "swim": None,
            "use_lifts": True,
            "door_access": [],
        },
        "interactions": {"talk": None, "trade": None, "carry": True, "open_doors": []},
    },
    "brain": {"default_preset": "wanderer_puppy_slug"},
    "actions": {"default_preset": "peaceful_float"},
    "animation_bindings": {
        "default": {"animation": "idle", "events": []},
        "locomotion.walk": {"animation": "walk", "events": []},
        "locomotion.run": {"animation": "walk", "events": []},
        "locomotion.jump": {"animation": "jump", "events": []},
        "locomotion.fall": {"animation": "jump", "events": []},
        "locomotion.skid": {"animation": "skid", "events": []},
        "locomotion.climb": {"animation": "climb", "events": []},
        "locomotion.swim": {"animation": "swim", "events": []},
        "state.dead": {"animation": "death", "events": []},
    },
    "tags": ["hero", "platformer", "mary_o", "retro"],
}
