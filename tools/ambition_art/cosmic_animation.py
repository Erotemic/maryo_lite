"""Ported source animation pose/transform sequence tables for Cosmic Mary-O."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image

from . import model as M
from .cosmic_art import COSMIC_FORM, Look, Pose, Stage, frame

TARGET = "mary_o_v2_cosmic"
LABEL_WIDTH = 122

#: The canvas of each frame: room for her wings over her head and behind
#: her, and, in the transformation, for the star that comes down, for the
#: column of light, and for the star behind her last pose.
STAGE = Stage(w=72, h=84, ox=24.0, oy=38.0)

TRANSFORM_FRAMES = 36
TRANSFORM_FRAME_MS = 95
#: Her way out of the form (`detransformation`).
LEAVE_ROW = "shrink"
LEAVE_FRAMES = 18
LEAVE_FRAME_MS = 95

ROWS: List[Tuple[str, int, int]] = [
    ("idle", 4, 180),
    ("death", 1, 120),
    ("walk", 3, 95),
    # A jump is one beat of her wings: up, hard down, and back. The row goes
    # round while she rises, so a line of jumps in the air is a flight.
    ("jump", 8, 70),
    ("fall", 2, 140),
    ("skid", 1, 110),
    ("crouch", 1, 120),
    ("crouch_walk", 3, 110),
    ("crouch_jump", 1, 120),
    ("climb", 2, 120),
    ("swim", 6, 100),
    ("shoot", 3, 60),
    # The transformation, from her fire form. The game holds her in this row
    # for as long as it takes to draw (`cosmic.rs`).
    ("transform", TRANSFORM_FRAMES, TRANSFORM_FRAME_MS),
    # Her way out of the form. The picture is of this form, so the row is on
    # this sheet, the sheet of the form she leaves: the game plays it and then
    # changes her character (`cosmic.rs`). It ends in light, so each form she
    # can come back to follows it.
    (LEAVE_ROW, LEAVE_FRAMES, LEAVE_FRAME_MS),
]

POSES: Dict[str, List[Pose]] = M.poses_for_form(COSMIC_FORM)

#: The beat of her wings in a jump: `(beat, fan, sway of her hair)`.
WING_BEAT = ((-22, 1.2, -0.6), (-34, 1.3, -1.0), (14, 1.0, 0.4), (58, 0.72, 1.6), (74, 0.6, 1.9), (46, 0.8, 1.0), (16, 0.95, 0.3), (0, 1.0, 0.0))


def mix(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


def look_for(animation: str, frame_idx: int) -> Look:
    """Her look in one frame of a row of the form."""
    poses = POSES.get(animation) or POSES["jump" if animation == "fall" else "idle"]
    pose = poses[frame_idx % len(poses)]
    if animation == "idle":
        breath = (0.0, 0.5, 1.0, 0.5)[frame_idx % 4]
        return Look(pose=pose, anim=animation, beat=-7.0 * breath, sway=0.5 * breath, crown=(0.4 * breath, 1.0, -90.0))
    if animation == "jump":
        beat, fan, sway = WING_BEAT[frame_idx % len(WING_BEAT)]
        return Look(pose=pose, anim=animation, beat=beat, fan=fan, sway=sway)
    if animation == "fall":
        # Her wings are wide and high, and they hold the air: she comes down slowly.
        return Look(pose=pose, anim="jump", beat=(-24.0, -19.0)[frame_idx % 2], fan=1.28, sway=-1.2)
    if animation in ("walk", "crouch_walk", "climb", "swim"):
        swing = (1.0, 0.0, -1.0, 0.0)[frame_idx % 4]
        return Look(pose=pose, anim=animation, beat=4.0 * swing, sway=0.4 * swing)
    if animation in ("crouch", "crouch_jump"):
        # Her wings are closed at her back: she is as small as she can be.
        return Look(pose=pose, anim=animation, beat=34.0, fan=0.6)
    return Look(pose=pose, anim=animation)


def transformation() -> List[Look]:
    """The transformation, from her fire form: 36 frames."""
    looks: List[Look] = []
    reach = Pose(bob=-0.4, arm_front_angle=165, arm_back_angle=-12, leg_front_angle=4, leg_back_angle=-4)
    # 1. The call: she lifts her hand, and the star comes down to her in a column of light.
    for i in range(6):
        t = i / 5
        looks.append(Look(cosmic=False, pose=Pose(bob=-0.4 * t, arm_front_angle=mix(15, 165, t), arm_back_angle=mix(0, -12, t)),
                          crown=(mix(34, 9, t), mix(0.6, 1.1, t), -90 + i * 24), column=t, lift=mix(0, 1.5, t)))
    # 2. Light: she is a figure of light, and she turns one time about.
    for i, spin in enumerate((1.0, 0.45, -0.45, -1.0, -0.45, 0.45)):
        looks.append(Look(cosmic=i >= 3, hair=0, wing=0, ring=0, pose=reach, light=min(1.0, 0.55 + i * 0.45), spin=spin,
                          crown=(9, 1.1, -90 + (6 + i) * 24), column=1.0, lift=mix(1.5, 5, i / 5), wing_boost=0.9 if i < 3 else 0.0))
    # 3. The gown: a ring of light goes up her, and under it she is the new form.
    for i in range(5):
        t = i / 4
        looks.append(Look(hair=0, wing=0, ring=0, pose=reach, light=1.0, reveal=t * 0.86, sweep=t * 0.9, crown=(9, 1.1, -90 + (12 + i) * 24), column=1.0, lift=5))
    # 4. Her hair: out and down, in three steps.
    for i, t in enumerate((0.35, 0.75, 1.0)):
        looks.append(Look(hair=t, wing=0, ring=0, sway=-1.5 + i * 0.6, pose=Pose(bob=-0.4, arm_front_angle=mix(165, 120, t), arm_back_angle=-12),
                          crown=(9, 1.1, -90 + (17 + i) * 24), column=mix(1.0, 0.6, t), lift=5))
    # 5. The ring, and the star comes down on her head.
    for i, t in enumerate((0.34, 0.67, 1.0)):
        looks.append(Look(wing=0, ring=t, pose=Pose(bob=-0.4, arm_front_angle=mix(120, 60, t), arm_back_angle=-12),
                          crown=(mix(9, 0, t), mix(1.1, 1.0, t), -90 + (20 + i) * 24 * (1 - t)), column=mix(0.6, 0.25, t), lift=5))
    # 6. Her wings: from closed at her back to open over her head.
    for i, (size, beat, fan) in enumerate(((0.35, 62, 0.45), (0.65, 40, 0.7), (0.9, 8, 1.0), (1.0, -26, 1.25))):
        looks.append(Look(wing=size, beat=beat, fan=fan, pose=Pose(bob=-0.4, arm_front_angle=mix(60, 30, i / 3), arm_back_angle=mix(-12, -30, i / 3)), column=mix(0.25, 0.0, i / 3), lift=5))
    # 7. The pose: her hand up, her wings wide, and a star behind her.
    final = Pose(bob=-0.8, body_lean=0.3, arm_front_angle=152, arm_back_angle=-46, leg_front_angle=16, leg_back_angle=-12)
    for i, (burst, beat, fan) in enumerate(((0.55, -30, 1.3), (1.0, -34, 1.35), (1.0, -30, 1.3), (0.9, -26, 1.28), (0.6, -22, 1.2))):
        looks.append(Look(pose=final, anim="jump", beat=beat, fan=fan, burst=burst, burst_turn=i * 7.5, lift=5 + (1.0 if i in (1, 2) else 0.0), sway=-0.8))
    # 8. She comes down to the ground, and her wings come to rest. The last
    # frame is the first frame of her idle.
    for i in range(4):
        t = (i + 1) / 4
        if i == 3:
            looks.append(look_for("idle", 0))
            break
        looks.append(Look(pose=Pose(bob=-0.8 * (1 - t), arm_front_angle=mix(152, 10, t), arm_back_angle=mix(-46, 0, t)), beat=mix(-22, 0, t), fan=mix(1.2, 1.0, t), lift=mix(5, 0, t), sway=mix(-0.8, 0, t)))
    assert len(looks) == TRANSFORM_FRAMES, len(looks)
    return looks


def detransformation() -> List[Look]:
    """Her way out of the form: 18 frames. The form goes from her in the
    order it came to her, last thing first, and she goes out in light."""
    looks: List[Look] = []
    rest = Pose(bob=-0.2, arm_front_angle=8, arm_back_angle=0)
    low = Pose(bob=-0.4, arm_front_angle=-18, arm_back_angle=14, leg_front_angle=3, leg_back_angle=-3)
    # 1. Her wings close at her back, and she comes off the ground.
    for i, (beat, fan) in enumerate(((18, 0.9), (44, 0.65), (62, 0.45))):
        looks.append(Look(pose=rest, beat=beat, fan=fan, lift=mix(0, 3, (i + 1) / 3), sway=0.4 * i))
    # 2. Her wings go, and the star lifts off her head.
    for i, size in enumerate((0.65, 0.35, 0.0)):
        t = (i + 1) / 3
        looks.append(Look(pose=low, wing=size, beat=62, fan=0.45, lift=mix(3, 5, t), crown=(mix(0, 9, t), mix(1.0, 1.1, t), -90 + (i + 1) * 24), column=0.3 * t))
    # 3. The ring goes from her head, and her hair comes in.
    for i, t in enumerate((0.5, 1.0)):
        looks.append(Look(pose=low, wing=0, ring=1.0 - t, hair=mix(1.0, 0.3, t), sway=-0.6 * t, lift=5, crown=(9, 1.1, -90 + (4 + i) * 24), column=mix(0.3, 0.7, t)))
    # 4. A ring of light goes down her, and over it she is light.
    for i in range(4):
        t = (i + 1) / 4
        looks.append(Look(pose=low, hair=0, wing=0, ring=0, light=1.0, reveal=0.86 * (1 - t), sweep=0.9 * (1 - t), lift=5, crown=(9, 1.1, -90 + (6 + i) * 24), column=mix(0.7, 1.0, t)))
    # 5. A figure of light: she turns one time about, and the star goes up from her.
    for i, spin in enumerate((0.45, -0.45, -1.0)):
        looks.append(Look(pose=low, hair=0, wing=0, ring=0, light=1.0, spin=spin, lift=mix(5, 3, (i + 1) / 3), crown=(mix(9, 26, (i + 1) / 3), mix(1.1, 0.8, (i + 1) / 3), -90 + (10 + i) * 30), column=1.0))
    # 6. She goes out in a star of light, and comes down. The star over her
    # is gone. The last frame is light and no more, so each form follows it.
    for i, (burst, column) in enumerate(((0.45, 0.8), (0.8, 0.5), (1.0, 0.2))):
        looks.append(Look(pose=low, hair=0, wing=0, ring=0, light=1.0, lift=mix(3, 0, (i + 1) / 3), crown=None, burst=burst, burst_turn=i * 12.0, column=column))
    assert len(looks) == LEAVE_FRAMES, len(looks)
    return looks


