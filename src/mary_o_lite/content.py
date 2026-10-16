"""Read the original text-based LDtk world; no dependency on LDtk at runtime."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'assets'
TILE = 16
COURSE_ORDER = (
    'mary_o_1_1', 'mary_o_1_2', 'mary_o_1_3', 'mary_o_1_4',
    'mary_o_2_1', 'mary_o_2_2', 'mary_o_2_3', 'mary_o_2_4',
)


@dataclass
class Thing:
    kind: str
    x: float
    y: float
    w: float
    h: float
    fields: dict = field(default_factory=dict)
    identifier: str = ''

    @property
    def right(self):
        return self.x + self.w

    @property
    def bottom(self):
        return self.y + self.h

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2


@dataclass
class Level:
    name: str
    title: str
    biome: str
    next_room: str
    width: int
    height: int
    grid_width: int
    grid_height: int
    collision: list[int]
    things: list[Thing]

    def terrain(self, col: int, row: int) -> int:
        if 0 <= col < self.grid_width and 0 <= row < self.grid_height:
            return self.collision[row * self.grid_width + col]
        return 0

    def nearby_tiles(self, x: float, y: float, w: float, h: float):
        left = max(0, int(x // TILE) - 1)
        right = min(self.grid_width, int((x + w) // TILE) + 2)
        top = max(0, int(y // TILE) - 1)
        bottom = min(self.grid_height, int((y + h) // TILE) + 2)
        for row in range(top, bottom):
            for col in range(left, right):
                value = self.terrain(col, row)
                if value in (1, 2, 5):
                    yield Thing('tile', col * TILE, row * TILE, TILE, TILE, {'value': value})

    def all(self, kind: str) -> list[Thing]:
        return [e for e in self.things if e.kind == kind]

    def spawn(self):
        return next((e for e in self.things if e.kind == 'PlayerStart'),
                    Thing('PlayerStart', 64, 240, 28, 46))


@lru_cache(maxsize=1)
def levels() -> dict[str, Level]:
    doc = json.loads((ASSETS / 'worlds' / 'mary_o.ldtk').read_text(encoding='utf8'))
    result = {}
    for src in doc['levels']:
        fields = {f['__identifier']: f['__value'] for f in src['fieldInstances']}
        collision = next(l for l in src['layerInstances'] if l['__identifier'] == 'Collision')
        things = []
        for layer in src['layerInstances']:
            for entity in layer.get('entityInstances') or []:
                props = {f['__identifier']: f['__value'] for f in entity.get('fieldInstances') or []}
                things.append(Thing(entity['__identifier'], *map(float, entity['px']),
                                    float(entity['width']), float(entity['height']),
                                    props, entity.get('iid', '')))
        level = Level(src['identifier'], fields.get('title', src['identifier']),
                      fields.get('biome', 'starlight'),
                      fields.get('next_room') or 'mary_o_1_1',
                      src['pxWid'], src['pxHei'], collision['__cWid'], collision['__cHei'],
                      collision['intGridCsv'], things)
        result[level.name] = level
    return result


def available_rooms():
    return tuple(COURSE_ORDER) + ('mary_o_warp',)
