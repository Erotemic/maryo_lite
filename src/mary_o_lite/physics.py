"""Classic movement based on the authored Ambition Mary-O axis tuning.

No coyote time and no jump buffer. A pressed jump works only if grounded
(or cosmic air-jumps remain). The speed-band law and phased rise gravity
use the same tunings across the original forms; default movement is a walk.
"""
from __future__ import annotations

from dataclasses import dataclass
from .geometry import toward


@dataclass(frozen=True)
class Tuning:
    gravity: float = 2250.0
    max_run: float = 300.0
    run_accel: float = 393.75
    air_accel: float = 393.75
    ground_reverse: float = 1500.0
    air_reverse: float = 900.0
    ground_coast: float = 393.75
    air_coast: float = 0.0
    jump_speed: float = 450.0
    max_fall: float = 480.0
    air_jumps: int = 0


CLASSIC = Tuning()
COSMIC = Tuning(max_run=620, run_accel=1400, air_accel=1400,
                ground_reverse=3200, air_reverse=2400, ground_coast=1400,
                air_coast=700, jump_speed=520, max_fall=300, air_jumps=255)


# From Mary-O's Rust game rules: the unmodified stick walks at 60% throttle.
# The modifier is RUN, not WALK. Slowing down doesn't erase existing momentum.
WALK_THROTTLE = 0.60
# In Rust `ShiftLayer` caps the *input axis* to 0.5 before Mary-O's own
# walk/run policy sees it. Shift+X is therefore a precise half-throttle run;
# Shift alone is half of the ordinary 60%-throttle walk.
SHIFT_AXIS_CAP = 0.50
# Lite allows a slow crouch-walk through 32 px passages. Rust uses the shared
# body-mode movement system, so this is deliberately a separate teaching knob.
CROUCH_SPEED = 90.0


def horizontal(vx: float, direction: int, on_ground: bool, run: bool,
               tuning: Tuning, dt: float, *, crouch: bool = False,
               precision: bool = False) -> float:
    """Approach a target speed without changing velocity instantaneously.

    Run is a held modifier; letting go slows Mary-O toward WALK_THROTTLE
    through normal acceleration. Crouching has an independent crawl cap but
    preserves accumulated velocity, allowing a run-in slide under a gap.
    """
    direction = max(-1, min(1, direction))
    cap = tuning.max_run * (1.0 if run else WALK_THROTTLE)
    if precision:
        cap *= SHIFT_AXIS_CAP
    if crouch:
        cap = min(cap, CROUCH_SPEED)
    if direction:
        reversing = vx * direction < 0
        accel = (tuning.ground_reverse if on_ground else tuning.air_reverse) if reversing else (
            tuning.run_accel if on_ground else tuning.air_accel)
        return toward(vx, direction * cap, accel * dt)
    decel = tuning.ground_coast if on_ground else tuning.air_coast
    return toward(vx, 0, decel * dt)


def jump_velocity(vx: float, tuning: Tuning) -> float:
    speed = abs(vx)
    thresholds = (120.0, 187.5, 210.0)
    band = sum(speed >= threshold for threshold in thresholds)
    return -(tuning.jump_speed + (-30.0, -15.0, 0.0, 30.0)[band])


def gravity_step(vy: float, jump_held: bool, tuning: Tuning, dt: float) -> float:
    gravity = tuning.gravity * (0.2 if jump_held and vy < -240.0 else 1.0)
    return min(tuning.max_fall, vy + gravity * dt)
