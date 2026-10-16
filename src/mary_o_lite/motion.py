"""Small deterministic paths for Mary-O's authored moving hazards and lifts.

Positions are world pixels. All evaluations are functions of elapsed room time,
so simulation, collision, and drawing use the same position without an ECS.
"""
from __future__ import annotations

from functools import lru_cache
import math


def ping_pong(distance: float, speed: float, seconds: float) -> float:
    """Travel 0 -> distance -> 0 at the authored speed (not a sine wave)."""
    if distance == 0 or speed <= 0:
        return 0.0
    extent = abs(distance)
    along = (seconds * speed) % (2 * extent)
    if along > extent:
        along = 2 * extent - along
    return math.copysign(along, distance)


def wrapping_lift(start_y: float, dy: float, min_y: float,
                  speed: float, seconds: float) -> float:
    """Vertical lift that returns to the start of the shaft after each lap.

    The level defines a loop height ``abs(dy)``, a common minimum world Y,
    and a direction. Starting offsets make staggered lifts stay staggered.
    """
    height = abs(dy)
    if height <= 0 or speed <= 0:
        return start_y
    offset = (start_y - min_y) % height
    displacement = seconds * speed * (1 if dy > 0 else -1)
    return min_y + (offset + displacement) % height


@lru_cache(maxsize=512)
def parse_polyline(points: str) -> tuple[tuple[float, float], ...]:
    """Read the original LDtk path_points field, rejecting malformed paths."""
    nodes = []
    for node in points.split(';'):
        if not node.strip():
            continue
        x, y = node.split(',')
        value = (float(x), float(y))
        if not all(math.isfinite(v) for v in value):
            raise ValueError('nonfinite point in path_points')
        nodes.append(value)
    if len(nodes) < 2:
        raise ValueError('path_points needs at least two points')
    return tuple(nodes)


def loop_position(points: tuple[tuple[float, float], ...],
                  speed: float, seconds: float) -> tuple[float, float]:
    """Interpolate over polyline edges, including the last-to-first edge.

    Paths are distance-parametrized so the orbit speed remains constant even
    on diagonals. Each Fire Bar orb's different speed preserves angular phase.
    """
    segments = []
    perimeter = 0.0
    for i, a in enumerate(points):
        b = points[(i + 1) % len(points)]
        length = math.dist(a, b)
        if length:
            segments.append((a, b, length))
            perimeter += length
    if not segments or perimeter == 0 or speed <= 0:
        return points[0]
    distance = (speed * seconds) % perimeter
    for a, b, length in segments:
        if distance <= length:
            t = distance / length
            return (a[0] + (b[0] - a[0]) * t,
                    a[1] + (b[1] - a[1]) * t)
        distance -= length
    return points[0]


def wanted_plant_out(tick: int) -> float:
    """Mary-O's original 330-tick Snake Plant cycle (rise, wait, sink, hide)."""
    at = tick % 330
    if at < 36:
        return at / 36
    if at < 144:
        return 1.0
    if at < 180:
        return 1.0 - (at - 144) / 36
    return 0.0


def next_plant_out(now: float, wanted: float, shy: bool) -> float:
    """Move no more than 1/36 per tick; stay hidden under a nearby player."""
    if shy and now <= 0:
        return 0.0
    change = max(-1 / 36, min(1 / 36, wanted - now))
    return max(0.0, min(1.0, now + change))


def plant_placement(frame_width: int, frame_height: int, bbox_top: int,
                    root_x: float, root_y: float, center_x: float,
                    mouth_y: float, exposure: float, body_height: float):
    """Scaled origin for the plant rig, with its ROOT at the pipe mouth.

    The original 96x128 painter's root is (48,127); using frame bottom or
    union-bbox bottom as a *generic enemy foot* misaligns the plant. For a
    partially emerged plant, the root slides down *inside* the pipe, whose
    foreground lip hides the underground pixels.
    """
    visible_height = max(1, root_y - bbox_top)
    scale = body_height / visible_height
    left = center_x - root_x * scale
    top = mouth_y + (1 - exposure) * body_height - root_y * scale
    return (left, top, frame_width * scale, frame_height * scale)
