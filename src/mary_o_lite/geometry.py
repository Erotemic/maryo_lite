"""AABB boxes, simple collision tests, and scalar motion helpers."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def left(self): return self.x
    @property
    def right(self): return self.x + self.w
    @property
    def top(self): return self.y
    @property
    def bottom(self): return self.y + self.h
    @property
    def cx(self): return self.x + self.w / 2
    @property
    def cy(self): return self.y + self.h / 2

    def overlaps(self, other) -> bool:
        return self.right > other.x and self.x < other.x + other.w and self.bottom > other.y and self.y < other.y + other.h


def toward(value: float, goal: float, step: float) -> float:
    if value < goal:
        return min(goal, value + step)
    return max(goal, value - step)


def clamp(value, minimum, maximum):
    return min(max(value, minimum), maximum)
