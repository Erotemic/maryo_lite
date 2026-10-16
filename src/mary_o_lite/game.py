"""Mary-O game rules. This module works without Pygame or generated images.

Every form uses one player body and one collision solver. The form changes its
height, abilities and art; it does not swap to another physics implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import copy
import math

from .content import COURSE_ORDER, Level, Thing, levels
from .geometry import Box, clamp, toward
from .physics import CLASSIC, COSMIC, gravity_step, horizontal, jump_velocity
from .motion import (ping_pong, wrapping_lift, parse_polyline, loop_position,
                     wanted_plant_out, next_plant_out)

STEP = 1 / 60
SMALL_H = 32
TALL_H = 62
# Small-form passages must also fit a tall / fire / cosmic form while crouched.
CROUCH_H = SMALL_H
BLOCK_SCORE = 50
# Source `assets/data/room_rules.ron`: the four-bar death interlude is 3.2s.
DEATH_DWELL = 3.2


@dataclass
class Command:
    move: int = 0
    jump: bool = False          # Key-down edge, not held state.
    held_jump: bool = False
    fire: bool = False          # Programmatic action; keyboards use run_pressed.
    down: bool = False          # Held: crouch while standing; enter pipes.
    up: bool = False            # Held: leave downward-facing pipes.
    run: bool = False          # Hold X (Arrows) / J (WASD), not Shift.
    run_pressed: bool = False  # Its press edge also fires a spark when armed.
    precision: bool = False    # Shift caps the movement axis at 50%.
    utility: bool = False
    restart: bool = False


@dataclass
class Player:
    x: float = 64
    y: float = 350
    w: float = 24
    h: float = SMALL_H
    vx: float = 0
    vy: float = 0
    direction: int = 1
    grounded: bool = False
    form: str = 'small'
    saved_form: str = 'small'
    air_jumps: int = 0
    invulnerable: float = 0
    quasar: float = 0
    shot_timer: float = 0
    transition: str = ''
    transition_time: float = 0
    anim_time: float = 0
    walk_anim_time: float = 0  # Strides follow distance, not a fixed clock.
    shoot_time: float = 0
    dead_time: float = 0
    crouched: bool = False
    jump_hold_cancelled: bool = False  # Re-pressing jump cannot re-enter weak ascent.

    @property
    def box(self): return Box(self.x, self.y, self.w, self.h)
    @property
    def foot(self): return (self.x + self.w / 2, self.y + self.h)
    @property
    def cosmic(self): return self.form == 'cosmic'


@dataclass
class Enemy:
    kind: str
    x: float
    y: float
    w: float
    h: float
    vx: float = 0
    vy: float = 0
    facing: int = -1
    hp: int = 1
    alive: bool = True
    phase: str = 'walk'
    age: float = 0
    anchor_y: float = 0
    timer: float = 0
    grounded: bool = False
    pot_y: float | None = None
    pot_x: float = 0.0
    exposure: float = 1.0
    pot_left: float = 0.0
    pot_right: float = 0.0
    pot_bottom: float = 0.0
    plant_offset: int = 0
    kick_grace: float = 0.0

    @property
    def box(self): return Box(self.x, self.y, self.w, self.h)


@dataclass
class Item:
    kind: str
    x: float
    y: float
    w: float = 24
    h: float = 24
    vx: float = 0
    vy: float = 0
    live: bool = True
    age: float = 0

    @property
    def box(self): return Box(self.x, self.y, self.w, self.h)


@dataclass
class Spark:
    x: float
    y: float
    vx: float
    vy: float
    enemy: bool = False
    life: float = 1.5
    bounces: int = 2
    visual: str = ''  # Name of the source sprite family, not an untracked PNG.
    gravity: float = 900.0

    @property
    def box(self):
        half_extent = 12 if self.visual == 'void_orb' else 10 if not self.enemy else 9
        return Box(self.x - half_extent, self.y - half_extent,
                   half_extent * 2, half_extent * 2)


@dataclass
class Moving:
    thing: Thing
    x: float
    y: float
    start_x: float
    start_y: float
    old_x: float = 0
    old_y: float = 0
    age: float = 0

    @property
    def box(self): return Box(self.x, self.y, self.thing.w, self.thing.h)


@dataclass
class Event:
    kind: str
    x: float = 0
    y: float = 0
    value: int = 0


@dataclass
class RoomSnapshot:
    """Progress in a room, saved while its actors are not being simulated.

    Only local objects belong here. Lives, score, form and collected coins are
    global game state and therefore do not roll back when travelling left.
    """
    spent: set[str]
    broken: set[str]
    enemies: list[Enemy]
    items: list[Item]
    moving: list[Moving]
    switch_pressed: bool
    bridge_retracted: int
    clock: float
    hazard_elapsed: float


class Game:
    """A fixed-step, independently testable platformer."""

    def __init__(self, room: str = 'mary_o_1_1'):
        self.rooms = levels()
        if room not in self.rooms:
            raise ValueError(f'Unknown room {room!r}; choose from {list(self.rooms)}')
        self.player = Player()
        self.room_cache: dict[str, RoomSnapshot] = {}
        self._room_initialized = False
        self.returning_left = False
        self.cleared: set[str] = set()
        self.score = 0
        self.coins = 0
        self.lives = 3
        self.game_over = False
        self.clock = 400.0
        self.elapsed = 0.0
        self.tick_count = 0
        self.room = self.rooms[room]
        self.enemies: list[Enemy] = []
        self.items: list[Item] = []
        self.sparks: list[Spark] = []
        self.blocks: list[Thing] = []
        self.spent: set[str] = set()
        self.broken: set[str] = set()
        self.pipes: list[Thing] = []
        self.solids: list[Thing] = []
        self.oneway: list[Thing] = []
        self.moving: list[Moving] = []
        self.hazards: list[Thing] = []
        self.hazard_elapsed = 0.0
        self.events: list[Event] = []
        self.flag_state = ''
        self.flag_timer = 0.0
        self.switch_pressed = False
        self.castle_timer = 0.0
        self.bridge_retracted = 0
        self.pipe_state = ''
        self.pipe_timer = 0.0
        self.pipe_destination: Thing | None = None
        self.pipe_destination_room = ''
        self.pipe_origin: Thing | None = None
        self.load_room(room)

    def _save_room(self):
        """Remember the room's mutable objects before a course transition."""
        if not self._room_initialized:
            return
        self.room_cache[self.room.name] = RoomSnapshot(
            set(self.spent), set(self.broken), copy.deepcopy(self.enemies),
            copy.deepcopy(self.items), copy.deepcopy(self.moving),
            self.switch_pressed, self.bridge_retracted, self.clock,
            self.hazard_elapsed,
        )

    def previous_room(self) -> str | None:
        """Linear course progression has no wraparound at World 1-1."""
        if self.room.name not in COURSE_ORDER:
            return None
        index = COURSE_ORDER.index(self.room.name)
        return COURSE_ORDER[index - 1] if index > 0 else None

    def go_previous(self) -> bool:
        """Classroom shortcut and left-edge exit use the same transition."""
        if self.game_over:
            return False
        name = self.previous_room()
        if name is None:
            return False
        self.load_room(name, entry='right')
        return True

    def go_next(self) -> bool:
        """Move forward, retaining history so later rooms can be revisited."""
        if self.game_over:
            return False
        name = self.room.next_room
        if name not in self.rooms:
            return False
        self.load_room(name, entry='left')
        return True

    def restart_session(self):
        """Start a fresh run after exhausting all lives; R restarts a game over."""
        self.room_cache.clear()
        self.cleared.clear()
        self.score = self.coins = 0
        self.lives = 3
        self.game_over = False
        self.elapsed = 0
        self.player = Player()
        self._room_initialized = False
        self.load_room('mary_o_1_1', preserve_form=False, reset=True)

    def _arrival_from_right(self):
        """Find a safe ground near the far exit, without hardcoded room coords.

        Castle exits have gaps, so search leftward for an exposed tile top.
        The selector also avoids blocks, pipes, and hazard volumes.
        """
        p = self.player
        room = self.room
        for cx in range(max(0, room.grid_width - 5),
                        max(-1, room.grid_width - 90), -1):
            x = cx * 16 + 4
            for row in range(room.grid_height - 1, 2, -1):
                if room.terrain(cx, row) != 1 or room.terrain(cx, row - 1) != 0:
                    continue
                y = row * 16 - p.h
                candidate = Box(x, y, p.w, p.h)
                # Avoid hazards on the platform and entities obstructing spawn.
                if y < 30 or any(candidate.overlaps(Box(h.x,h.y,h.w,h.h)) for h in self.hazards):
                    continue
                if self.solid_at(candidate):
                    continue
                p.x, p.y = x, y
                p.grounded = True
                p.direction = -1
                return
        # A fallback for unusual room geometry; never silently warp outside it.
        spawn = room.spawn()
        p.x = max(0, room.width - 320)
        p.y = spawn.y + spawn.h - p.h
        p.grounded = False
        p.direction = -1

    def load_room(self, name: str, *, preserve_form=True, entry='spawn', reset=False):
        """Load a course, optionally revisiting its saved mutable state.

        `entry='right'` is used when coming *back* from the next course.
        `reset=True` restarts the current room without clearing other rooms.
        """
        if name not in self.rooms:
            raise ValueError(f'Unknown room {name!r}')
        self._save_room()
        if reset:
            self.room_cache.pop(name, None)
            self.cleared.discard(name)
        self.room = self.rooms[name]
        p = self.player
        spawn = self.room.spawn()
        p.h = TALL_H if p.form != 'small' else SMALL_H
        p.x, p.y = spawn.x + (spawn.w - p.w) / 2, spawn.y + spawn.h - p.h
        p.vx = p.vy = 0
        p.grounded = False
        p.direction = 1
        p.air_jumps = 0
        p.jump_hold_cancelled = False
        p.shoot_time = p.anim_time = p.walk_anim_time = 0
        p.crouched = False
        if not preserve_form:
            p.form = p.saved_form = 'small'
            p.h = SMALL_H
            p.y = spawn.y + spawn.h - p.h
        p.transition = ''
        p.transition_time = 0.0
        self.enemies = []
        self.items = []
        self.sparks = []
        self.blocks = self.room.all('MaryOBlock')
        self.spent = set()
        self.broken = set()
        self.pipes = self.room.all('MaryOPipe')
        self.solids = self.room.all('Solid')
        self.oneway = [e for e in self.room.all('OneWayPlatform') if not str(e.fields.get('name', '')).startswith('goal_pole')]
        self.moving = [Moving(e, e.x, e.y, e.x, e.y) for e in self.room.all('MovingPlatform')]
        # Mutable copies: the LDtk level is immutable source content, while
        # Fire Bar orb positions advance in this room each 60 Hz tick.
        self.hazards = copy.deepcopy(self.room.all('DamageVolume'))
        self.hazard_elapsed = 0.0
        self.flag_state = ''
        self.flag_timer = 0
        self.switch_pressed = False
        self.castle_timer = 0
        self.bridge_retracted = 0
        self.pipe_state = ''
        self.pipe_timer = 0
        self.pipe_origin = None
        self.pipe_destination = None
        self.pipe_destination_room = ''
        self.clock = 400
        self.returning_left = entry == 'right'
        for e in self.room.all('EnemySpawn'):
            kind = e.fields.get('character_id', 'ai_slop')
            if kind not in {'ai_slop', 'solid_snake', 'snake_plant', 'laden_swallow',
                            'void_star', 'void_lizard', 'npc_snakes_on_a_paper_plane',
                            'npc_snakes_on_a_cartesian_plane'}:
                continue
            hp = 5 if kind == 'void_lizard' else 1
            enemy = Enemy(kind, e.x, e.y, e.w, e.h, hp=hp, anchor_y=e.y)
            enemy.facing = 1 if e.fields.get('facing') == 'Right' else -1
            enemy.vx = enemy.facing * (32 if kind == 'ai_slop' else 46)
            if kind == 'void_lizard': enemy.vx = enemy.facing * 44
            if kind == 'snake_plant':
                pots = [pot for pot in self.pipes if pot.fields.get('mouth') == 'Up'
                        and pot.x <= e.cx <= pot.right]
                if pots:
                    pot = min(pots, key=lambda q: abs(q.y - e.bottom))
                    enemy.pot_y = pot.y
                    enemy.pot_x = pot.cx
                    enemy.pot_left = pot.x
                    enemy.pot_right = pot.right
                    enemy.pot_bottom = pot.bottom
                    enemy.plant_offset = max(0, int(pot.x / 16)) * 53
                    enemy.exposure = 0.0
                    enemy.phase = 'hidden'
                    enemy.x = pot.cx - enemy.w / 2
                    enemy.y = pot.y
            self.enemies.append(enemy)
        for e in self.room.all('PickupSpawn'):
            if str(e.fields.get('kind', '')).startswith('currency:'):
                self.items.append(Item('coin', e.x, e.y, e.w, e.h))
        snapshot = self.room_cache.get(name)
        if snapshot is not None:
            self.spent = set(snapshot.spent)
            self.broken = set(snapshot.broken)
            self.enemies = copy.deepcopy(snapshot.enemies)
            self.items = copy.deepcopy(snapshot.items)
            self.moving = copy.deepcopy(snapshot.moving)
            self.switch_pressed = snapshot.switch_pressed
            self.bridge_retracted = snapshot.bridge_retracted
            self.clock = snapshot.clock
            self.hazard_elapsed = snapshot.hazard_elapsed
        self._hazards_update(0.0)
        if entry == 'right':
            self._arrival_from_right()
        elif entry == 'left':
            # A revisited room may be entered from the previously visited exit.
            p.x = max(16, p.x)
        self.events = [Event('room', p.x, p.y)]
        self._room_initialized = True

    def _colliders(self, box: Box):
        for t in self.room.nearby_tiles(box.x, box.y, box.w, box.h):
            if t.fields['value'] == 1:
                yield t, False
            elif t.fields['value'] == 2:
                yield t, True
        for e in self.solids:
            if e.fields.get('name') == 'goal_gate' and self.switch_pressed:
                continue
            if Box(e.x,e.y,e.w,e.h).overlaps(box):
                yield e, False
        for e in self.blocks:
            if (e.identifier in self.broken or
                    (e.fields.get('kind') == 'Hidden' and e.identifier not in self.spent)):
                continue
            if Box(e.x,e.y,e.w,e.h).overlaps(box):
                yield e, False
        for e in self.pipes:
            if Box(e.x,e.y,e.w,e.h).overlaps(box):
                yield e, False
        for e in self.oneway:
            if Box(e.x,e.y,e.w,e.h).overlaps(box):
                yield e, True
        for m in self.moving:
            if m.box.overlaps(box):
                yield m.box, True

    def solid_at(self, box: Box) -> bool:
        return any(not one_way and box.overlaps(t) for t, one_way in self._colliders(box))

    def _move(self, obj, dt: float, *, bounce=False):
        """Swept axis movement: resolve the *first* face reached, not tile order.

        This is intentionally a small AABB solver for students. Using each
        axis's leading edge avoids corner teleports, repeated bonks, and
        clipping across thin blocks at high speed. One-way decks block only
        downward crossings from their top; hidden blocks only upward heads.
        """
        epsilon = 1e-6
        obj.grounded = False
        start_x = obj.x
        dx = obj.vx * dt
        if dx:
            sweep = Box(min(start_x, start_x + dx), obj.y,
                        obj.w + abs(dx), obj.h)
            hit = None
            distance = abs(dx)
            for wall, one_way in self._colliders(sweep):
                if one_way or not (obj.y < wall.y + wall.h and obj.y + obj.h > wall.y):
                    continue
                if dx > 0 and start_x + obj.w <= wall.x + epsilon:
                    gap = wall.x - (start_x + obj.w)
                elif dx < 0 and start_x >= wall.x + wall.w - epsilon:
                    gap = start_x - (wall.x + wall.w)
                else:
                    continue
                if -epsilon <= gap <= distance + epsilon and gap <= distance:
                    distance, hit = max(0, gap), wall
            obj.x = start_x + (distance if dx > 0 else -distance)
            if hit is not None:
                if bounce:
                    obj.vx = -obj.vx
                    if hasattr(obj, 'facing'):
                        obj.facing = 1 if obj.vx > 0 else -1
                else:
                    obj.vx = 0
        clamped_x = clamp(obj.x, 0, max(0, self.room.width - obj.w))
        if clamped_x != obj.x:
            obj.x = clamped_x
            if not bounce:
                obj.vx = 0

        start_y = obj.y
        dy = obj.vy * dt
        if dy:
            sweep = Box(obj.x, min(start_y, start_y + dy),
                        obj.w, obj.h + abs(dy))
            contacts = list(self._colliders(sweep))
            if dy < 0 and obj is self.player:
                # Include undiscovered blocks in the *same* nearest-contact
                # search. The first ceiling hit, not an arbitrary later block,
                # is the only block which should activate this tick.
                for block in self.blocks:
                    if (block.fields.get('kind') == 'Hidden'
                            and block.identifier not in self.spent
                            and block.identifier not in self.broken
                            and sweep.overlaps(Box(block.x,block.y,block.w,block.h))):
                        contacts.append((block, False))
            hit = None
            distance = abs(dy)
            for wall, one_way in contacts:
                if not (obj.x < wall.x + wall.w and obj.x + obj.w > wall.x):
                    continue
                if dy > 0 and start_y + obj.h <= wall.y + epsilon:
                    gap = wall.y - (start_y + obj.h)
                elif dy < 0 and not one_way and start_y >= wall.y + wall.h - epsilon:
                    gap = start_y - (wall.y + wall.h)
                else:
                    continue
                if -epsilon <= gap <= distance + epsilon and gap <= distance:
                    distance, hit = max(0, gap), wall
            obj.y = start_y + (distance if dy > 0 else -distance)
            if hit is not None:
                obj.vy = 0
                if dy > 0:
                    obj.grounded = True
                elif obj is self.player and isinstance(hit, Thing) and hit.kind == 'MaryOBlock':
                    self.bonk(hit)
        else:
            # Probe only from above so a player passing *through* a one-way
            # deck is never treated as standing on its underside.
            under = Box(obj.x + 2, obj.y + obj.h, max(1,obj.w - 4), 1.5)
            obj.grounded = any(under.overlaps(wall) and under.y <= wall.y + 2
                               for wall, _ in self._colliders(under))

    def _stand_or_crouch(self, down_held: bool):
        """Change posture about the *feet*, never the top of the sprite.

        Starting a crouch requires ground contact. Once crouched, holding
        Down carries that posture across a ledge (as in Rust Mary-O). A low
        ceiling prevents standing, even if Down has been released; Mary-O
        may walk out of the tunnel and stand up on the next clear frame.
        """
        p = self.player
        can_crouch = p.form != 'small'
        wants_crouch = can_crouch and down_held and (p.grounded or p.crouched)
        full_height = SMALL_H if not can_crouch else TALL_H
        desired = CROUCH_H if wants_crouch else full_height
        if desired > p.h:
            probe = Box(p.x, p.y + p.h - desired, p.w, desired)
            if self.solid_at(probe):
                # Don't expand into terrain, solid blocks, or a pipe roof.
                # Maintain small-form clearance until the whole head is free.
                desired = p.h
        p.y += p.h - desired
        p.h = desired
        p.crouched = can_crouch and p.h < full_height

    def _change_form(self, form: str, transition: str, length: float):
        p = self.player
        if form == p.form:
            return
        previous_h = p.h
        if form == 'cosmic':
            p.saved_form = p.form
        p.form = form
        wanted_h = SMALL_H if form == 'small' else TALL_H
        # A wand or beacon collected under a low ceiling must not insert a
        # 62px collider into a 32px opening. Grant the form but retain a
        # crouched body until the standing headroom becomes available.
        if wanted_h > previous_h:
            probe = Box(p.x, p.y + previous_h - wanted_h, p.w, wanted_h)
            if self.solid_at(probe):
                wanted_h = previous_h
        p.h = wanted_h
        p.y += previous_h - p.h
        p.crouched = form != 'small' and p.h < TALL_H
        p.air_jumps = 0
        p.jump_hold_cancelled = False
        p.transition = transition
        p.transition_time = length
        p.invulnerable = max(p.invulnerable, length + .3)
        self.events.append(Event('transform', p.x, p.y))

    def bonk(self, block: Thing):
        if block.identifier in self.spent or block.identifier in self.broken:
            self.events.append(Event('bump', block.x, block.y))
            return
        look = block.fields.get('kind','Question')
        contents = str(block.fields.get('contents') or '')
        if look == 'Brick' and not contents:
            if self.player.form != 'small':
                self.broken.add(block.identifier)
                self.score += BLOCK_SCORE
                self.events.append(Event('break', block.x, block.y))
            else:
                self.events.append(Event('bump', block.x, block.y))
            return
        self.spent.add(block.identifier)
        if not contents:
            contents = 'Coin' if look == 'Hidden' else 'TowardLantern'
        if contents in ('Coin','Coins'):
            self._coin(block.x, block.y)
            return
        if contents in ('AlwaysWand','TowardWand'):
            kind = 'wand'
        elif contents == 'AlwaysLantern':
            kind = 'lantern'
        elif contents == 'AlwaysQuasar':
            kind = 'quasar'
        elif contents == 'TowardLantern':
            kind = 'wand' if self.player.form == 'small' else 'lantern'
        else:
            kind = 'coin' if contents != 'Empty' else 'none'
        if kind != 'none':
            self.items.append(Item(kind, block.x + 4, block.y - 28, 24, 24,
                                   vx=55 if kind=='wand' else 0, vy=-40))
            self.events.append(Event('block', block.x, block.y))

    def _coin(self, x: float, y: float):
        self.coins += 1
        self.score += 200
        if self.coins >= 100:
            self.coins -= 100
            self.lives += 1
            self.events.append(Event('life', x, y))
        self.events.append(Event('coin', x, y))

    def _collect(self, item: Item):
        p = self.player
        item.live = False
        self.events.append(Event('pickup', item.x, item.y))
        if item.kind == 'coin':
            self._coin(item.x, item.y)
        elif item.kind == 'wand':
            if p.form == 'small':
                self._change_form('tall', 'grow', .28)
                self.score += 1000
            else: self._coin(item.x,item.y)
        elif item.kind == 'lantern':
            if p.form in ('small','tall'):
                self._change_form('fire', 'fire_transform', .85)
                self.score += 1000
            else: self._coin(item.x,item.y)
        elif item.kind == 'quasar':
            p.quasar = 10.0
            self.score += 1000

    def _hurt(self, source_x: float):
        p = self.player
        if p.invulnerable > 0 or p.quasar > 0 or p.cosmic or p.dead_time > 0 or self.flag_state:
            return
        if p.form == 'fire':
            self._change_form('tall', 'shrink', .51)
        elif p.form == 'tall':
            self._change_form('small', 'shrink', .34)
        else:
            self.die()
            return
        p.invulnerable = 1.5
        p.vx = 150 if p.foot[0] >= source_x else -150
        p.vy = -180
        self.events.append(Event('hurt',p.x,p.y))

    def die(self):
        p=self.player
        if p.cosmic or p.quasar > 0 or p.dead_time > 0:
            return
        self.lives = max(0, self.lives - 1)
        p.dead_time = DEATH_DWELL
        p.vx = 0
        p.vy = 0
        p.anim_time = 0
        p.jump_hold_cancelled = True
        self.events.append(Event('die',p.x,p.y))

    def _pipe_trigger(self, cmd: Command):
        p = self.player
        for pipe in self.pipes:
            role = pipe.fields.get('role','Entrance')
            mouth = pipe.fields.get('mouth','Up')
            if role not in ('Entrance','Warp') or not (cmd.down if mouth=='Up' else cmd.up):
                continue
            if abs(p.foot[0] - pipe.cx) > max(12,pipe.w*.42):
                continue
            if mouth == 'Up' and (abs(p.foot[1]-pipe.y)>9 or not p.grounded):
                continue
            if mouth == 'Down' and abs(p.y-pipe.bottom)>15:
                continue
            link = str(pipe.fields.get('link',''))
            if role == 'Warp':
                target_name = link
                destination = None
            else:
                destination = next((q for q in self.pipes if q is not pipe
                                    and q.fields.get('link')==link
                                    and q.fields.get('role')=='Exit'),None)
                target_name = self.room.name
            if target_name not in self.rooms or (role == 'Entrance' and destination is None):
                continue
            self.pipe_origin = pipe
            self.pipe_destination = destination
            self.pipe_destination_room = target_name
            self.pipe_state = 'enter'
            self.pipe_timer = .5
            p.vx = p.vy = 0
            self.events.append(Event('pipe',p.x,p.y))
            return True
        return False

    def _pipe_step(self, dt: float):
        p = self.player
        self.pipe_timer -= dt
        if self.pipe_state == 'enter' and self.pipe_origin:
            pipe=self.pipe_origin
            p.x=toward(p.x,pipe.cx-p.w/2,300*dt)
            p.y+=(90 if pipe.fields.get('mouth') == 'Up' else -90)*dt
            if self.pipe_timer <= 0:
                dest = self.pipe_destination
                name = self.pipe_destination_room
                if name != self.room.name:
                    self.load_room(name)
                    p = self.player
                elif dest is not None:
                    p.x=dest.cx-p.w/2
                    p.y=dest.y-p.h+10 if dest.fields.get('mouth')=='Up' else dest.bottom-10
                p.vx=p.vy=0
                p.grounded=False
                self.pipe_state='exit'
                self.pipe_timer=.5
                self.pipe_destination=dest
                self.events.append(Event('pipe_exit',p.x,p.y))
        elif self.pipe_state == 'exit':
            if self.pipe_destination is not None:
                direction=-1 if self.pipe_destination.fields.get('mouth')=='Up' else 1
                p.y+=direction*90*dt
            if self.pipe_timer<=0:
                self.pipe_state=''
                p.grounded=False
                self.pipe_origin=None
                self.pipe_destination=None

    def _enemy_kill(self, e: Enemy):
        if not e.alive: return
        e.alive=False
        self.score += 100 if e.kind != 'void_lizard' else 5000
        self.events.append(Event('stomp', e.x,e.y))

    def _enemy_tick(self, dt):
        p=self.player
        for e in self.enemies:
            if not e.alive or abs(e.x-p.x)>950: continue
            e.age+=dt
            if e.kind == 'snake_plant':
                if e.pot_y is not None:
                    # Rust Mary-O: the pot controls position, not gravity or
                    # a bounce. Stagger the cycle by the pot's tile column.
                    tick = int(e.age * 60) + e.plant_offset
                    wanted = wanted_plant_out(tick)
                    shy = (p.x + p.w > e.pot_left - 40
                           and p.x < e.pot_right + 40
                           and p.y + p.h <= e.pot_bottom)
                    e.exposure = next_plant_out(e.exposure, wanted, shy)
                    e.x = e.pot_x - e.w / 2
                    e.y = e.pot_y - e.h * e.exposure
                    e.phase = 'hidden' if e.exposure < 0.12 else 'emerged'
                else:
                    e.phase = 'emerged'
                continue
            if e.kind in ('laden_swallow','npc_snakes_on_a_paper_plane','npc_snakes_on_a_cartesian_plane'):
                e.x+=math.sin(e.age*1.8)*dt*42
                e.y=e.anchor_y+math.sin(e.age*3)*14
                if e.kind=='laden_swallow' and int(e.age*1.1)!=int((e.age-dt)*1.1):
                    # Authored coconut: 30px/s initial drop, 760px/s^2 pull,
                    # four seconds maximum, no floor bounce.
                    self.sparks.append(Spark(e.x+e.w/2,e.y+e.h,0,30,
                                             True,4.0,0,'coconut',760))
                continue
            if e.kind == 'solid_snake' and e.phase == 'shell':
                e.vx=0
                e.timer-=dt
                if e.timer <= 0:
                    e.phase='walk'
                    e.vx=e.facing*46
                continue
            if e.kind == 'solid_snake' and e.phase == 'rolling':
                e.vx=e.facing*300
                e.kick_grace = max(0, e.kick_grace - dt)
            if e.kind == 'void_lizard':
                e.vx=e.facing*55
                if e.grounded and int(e.age*1.5)!=int((e.age-dt)*1.5):
                    e.vy=-400
                if int(e.age/.95)!=int((e.age-dt)/.95):
                    # The Void Lizard's bolt travels along the bridge: the
                    # authored flight has *zero* gravity, unlike a spark.
                    self.sparks.append(Spark(e.x+e.w/2,e.y+e.h*.35,
                                             e.facing*170,0,True,3.5,0,
                                             'void_orb',0))
            if e.kind == 'ai_slop': e.vx=e.facing*32
            if e.kind == 'solid_snake' and e.phase=='walk': e.vx=e.facing*46
            if e.kind == 'void_star': e.vx=e.facing*85
            old_x=e.x
            e.vy=gravity_step(e.vy,False,CLASSIC,dt)
            self._move(e,dt,bounce=True)
            if abs(e.x-old_x)<.01 and abs(e.vx)<.01:
                e.facing*=-1
                e.vx=e.facing*(300 if e.phase=='rolling' else 48)
            if e.y>self.room.height+80: e.alive=False
        for shell in self.enemies:
            if not shell.alive or shell.phase!='rolling': continue
            for e in self.enemies:
                if e is not shell and e.alive and shell.box.overlaps(e.box):
                    self._enemy_kill(e)

    def _spark_tick(self, dt):
        for s in self.sparks:
            if s.life<=0:continue
            s.life-=dt
            old_y = s.y
            s.x+=s.vx*dt
            s.vy=min(540,s.vy+s.gravity*dt)
            s.y+=s.vy*dt
            if s.y>self.room.height+60 or s.x<0 or s.x>self.room.width: s.life=0;continue
            box = s.box
            # Include the swept vertical range so a fast falling projectile
            # cannot cross a thin one-way deck between two physics frames.
            sweep = Box(box.x, min(old_y, s.y) - box.h/2,
                        box.w, box.h + abs(s.y-old_y))
            collisions = list(self._colliders(sweep))
            for wall, one_way in collisions:
                if not sweep.overlaps(wall):continue
                # Floor-only bounce; one-way decks do not stop an ascending
                # spark or bolt. Enemy bolts and coconuts never bounce.
                on_top = (s.vy>0 and old_y + box.h/2 <= wall.y + 1e-6
                          and s.y + box.h/2 >= wall.y)
                if on_top and s.bounces > 0:
                    s.y=wall.y-box.h/2
                    s.vy=-300
                    s.bounces-=1
                elif not one_way or on_top:
                    s.life=0
                break
            if s.enemy:
                if s.box.overlaps(self.player.box):
                    self._hurt(s.x);s.life=0
            else:
                for e in self.enemies:
                    if e.alive and s.box.overlaps(e.box):
                        if e.kind=='void_lizard':
                            e.hp-=1
                            if e.hp<=0:self._enemy_kill(e)
                        elif e.kind != 'void_star': self._enemy_kill(e)
                        s.life=0
                        self.events.append(Event('spark_hit',s.x,s.y))
                        break
        self.sparks=[s for s in self.sparks if s.life>0]

    def _items_tick(self, dt):
        for item in self.items:
            if not item.live:continue
            item.age+=dt
            if item.kind!='coin':
                item.vy=gravity_step(item.vy,False,CLASSIC,dt)
                item.x+=item.vx*dt
                item.y+=item.vy*dt
                # Use the world tiles as support; items need no entity physics.
                under=Box(item.x+2,item.y+item.h,max(1,item.w-4),2)
                for wall, _ in self._colliders(under):
                    if under.overlaps(wall) and item.vy>=0:
                        item.y=min(item.y,wall.y-item.h)
                        item.vy=0
                        break
            if item.box.overlaps(self.player.box):self._collect(item)
        self.items=[i for i in self.items if i.live]

    def _carry_on_platform(self, dx: float, dy: float):
        """Move a grounded passenger by the platform delta, without phasing walls.

        Platform movement is independent of player input velocity. Test only
        solid walls/ceilings against the passenger; one-way decks are support,
        not lateral barriers. World bounds are still authoritative.
        """
        p = self.player
        if dx:
            p.x = clamp(p.x + dx, 0, max(0, self.room.width - p.w))
            for wall, one_way in self._colliders(p.box):
                if one_way or not p.box.overlaps(wall):
                    continue
                p.x = min(p.x, wall.x - p.w) if dx > 0 else max(p.x, wall.x + wall.w)
                p.vx = 0 if p.vx * dx > 0 else p.vx
        if dy:
            p.y += dy
            for wall, one_way in self._colliders(p.box):
                if one_way or not p.box.overlaps(wall):
                    continue
                p.y = max(p.y, wall.y + wall.h) if dy < 0 else min(p.y, wall.y - p.h)
                # If the shaft is too low for a passenger, the deck must not
                # carry that passenger through the ceiling.
                p.grounded = False
                return
        p.grounded = True

    def _moving_tick(self, dt):
        for m in self.moving:
            m.age += dt
            m.old_x, m.old_y = m.x, m.y
            f = m.thing.fields
            speed = float(f.get('speed') or 0)
            if f.get('sweep_dx') is not None:
                # Authored ferries run to the end of their span, reverse, and
                # return at a constant speed, rather than easing sinusoidally.
                dx = float(f['sweep_dx'])
                m.x = m.start_x + ping_pong(dx, speed, m.age)
                m.y = m.start_y
            elif f.get('loop_dy') is not None:
                # Staggered lift chains loop through the actual room-height
                # shaft. Crossing the wrap boundary is a teleport for the
                # platform, not a 700 px impulse to its passenger.
                m.x = m.start_x
                m.y = wrapping_lift(m.start_y, float(f['loop_dy']),
                                    float(f.get('loop_min_y', -32)), speed, m.age)
            else:
                m.x, m.y = m.start_x, m.start_y
            p = self.player
            dy = m.y - m.old_y
            wrapping = (f.get('loop_dy') is not None
                        and abs(dy) > abs(float(f['loop_dy'])) * .5)
            # Only a passenger grounded on the *previous* deck may ride it.
            # A falling body near the deck should land through the ordinary
            # swept collision, not snap sideways toward its new position.
            if (not wrapping and p.grounded and p.vy >= 0 and
                    abs(p.y + p.h - m.old_y) <= 2 and
                    p.x + p.w > m.old_x and p.x < m.old_x + m.thing.w):
                self._carry_on_platform(m.x - m.old_x, dy)

    def _hazards_update(self, dt: float):
        """Move fire orbs on their real LDtk polygonal circular paths."""
        self.hazard_elapsed += dt
        for orb in self.hazards:
            spec = orb.fields.get('path_points')
            if spec:
                center = loop_position(parse_polyline(spec),
                                       float(orb.fields['path_speed']),
                                       self.hazard_elapsed)
                orb.x = center[0] - orb.w / 2
                orb.y = center[1] - orb.h / 2

    def _player_enemy_contacts(self, previous_bottom: float):
        p=self.player
        for e in self.enemies:
            if not e.alive or e.phase=='hidden' or not p.box.overlaps(e.box):continue
            if p.cosmic or p.quasar>0:
                self._enemy_kill(e)
                continue
            if e.kind not in ('void_star', 'snake_plant') and p.vy>=0 and previous_bottom <= e.y+13:
                if e.kind=='void_lizard':
                    e.hp-=1
                    if e.hp<=0:self._enemy_kill(e)
                elif e.kind=='solid_snake':
                    if e.phase == 'walk':
                        e.phase='shell';e.timer=5;e.vx=0
                    elif e.phase=='shell':
                        e.phase='rolling';e.facing=1 if p.foot[0]<e.box.cx else -1
                    else:
                        e.phase='shell';e.timer=5;e.vx=0
                else:self._enemy_kill(e)
                p.vy=-430
                p.grounded=False
                self.events.append(Event('stomp',e.x,e.y))
            elif e.kind=='solid_snake' and e.phase=='shell':
                e.phase='rolling'
                e.facing=1 if p.foot[0]<e.box.cx else -1
                # Kicking begins with Mary-O touching the shell: it must not
                # damage the kicker for the first quarter-second (Rust rule).
                e.kick_grace=.25
                p.vx=-100*e.facing
                self.events.append(Event('kick',e.x,e.y))
            elif e.kind=='solid_snake' and e.phase=='rolling' and e.kick_grace>0:
                continue
            else:self._hurt(e.x)

    def _hazard_tick(self):
        p=self.player
        for e in self.hazards:
            # Hitboxes and source-rendered Fire Orbs share the same path sample.
            if p.box.overlaps(Box(e.x,e.y,e.w,e.h)):
                self._hurt(e.x)
                break
        if p.y>self.room.height+40:
            self.die()

    def _goal_tick(self, dt):
        p=self.player
        if self.flag_state:
            self.flag_timer+=dt
            if self.flag_state=='pole':
                p.vx=0
                p.y+=min(220*dt,max(0,self.flag_bottom-p.foot[1]))
                if self.flag_timer>1.1:self.flag_state='walk';self.flag_timer=0
            elif self.flag_state=='walk':
                p.x+=90*dt
                if self.flag_timer>1.1:self.flag_state='tally';self.flag_timer=0
            elif self.flag_state=='tally' and self.flag_timer>2:
                self.cleared.add(self.room.name)
                self.load_room(self.room.next_room)
            elif self.flag_state=='castle':
                self.castle_timer += dt
                planks = sorted((b for b in self.blocks if b.fields.get('kind') == 'Plank'),
                                key=lambda b: b.x, reverse=True)
                self.bridge_retracted = min(len(planks), int(max(0, self.castle_timer-1.4)*8))
                for plank in planks[:self.bridge_retracted]:
                    if plank.identifier not in self.broken:
                        self.broken.add(plank.identifier)
                        self.events.append(Event('break', plank.x, plank.y))
                for e in self.enemies:
                    if e.kind == 'void_lizard' and e.alive and self.castle_timer > 2.5:
                        e.y += 190*dt
                        if self.castle_timer > 4: self._enemy_kill(e)
                if self.castle_timer > 4.5:
                    robot = next((n for n in self.room.all('NpcSpawn')
                                  if n.fields.get('character_id') == 'mary_o_robot'), None)
                    if robot:
                        p.x = toward(p.x, robot.x-48, 95*dt)
                        p.y = toward(p.y, robot.bottom-p.h, 120*dt)
                        p.direction = 1
                if self.castle_timer > 11.8:
                    self.cleared.add(self.room.name)
                    self.load_room(self.room.next_room)
            return True
        if self.room.name == 'mary_o_warp' or self.room.name in self.cleared:return False
        if self.returning_left:
            # A player entering from the *right* must be able to cross the
            # old finish line without retriggering it. Once they are to the
            # left of that line, it can be earned normally in either direction.
            gates = [q.x for q in self.room.all('OneWayPlatform')
                     if q.fields.get('name') == 'goal_pole']
            gates += [q.x for q in self.solids
                      if q.fields.get('name') == 'goal_switch']
            if gates and p.x + p.w >= min(gates) - 32:
                return False
            self.returning_left = False
        if self.room.biome=='void_castle':
            sw=next((s for s in self.solids if s.fields.get('name')=='goal_switch'),None)
            # The switch is a solid platform, so a grounded actor normally
            # touches its *top* without overlapping its rectangle.
            touching = sw is not None and (
                p.box.overlaps(Box(sw.x, sw.y, sw.w, sw.h)) or
                (p.x < sw.x + sw.w and p.x + p.w > sw.x and
                 abs(p.foot[1] - sw.y) <= 3 and p.vy >= 0)
            )
            if touching:
                self.switch_pressed=True
                self.flag_state='castle';self.flag_timer=0
                self.events.append(Event('castle',p.x,p.y,5000))
                self.score+=5000
                return True
        for pole in self.room.all('OneWayPlatform'):
            if pole.fields.get('name')=='goal_pole' and p.box.overlaps(Box(pole.x-4,pole.y,pole.w+8,pole.h)):
                score=int(5000 if p.y<pole.y+20 else 2000 if p.y<pole.y+90 else 800 if p.y<pole.y+160 else 400)
                self.score+=score
                self.flag_state='pole';self.flag_timer=0
                self.flag_bottom=pole.bottom
                self.events.append(Event('flag',p.x,p.y,score))
                return True
        return False

    def step(self, cmd: Command | None = None, dt: float = STEP):
        """Advance exactly one simulation step. Call at a fixed 60 Hz."""
        cmd=cmd or Command()
        if abs(dt-STEP)>1e-8:
            raise ValueError('Fixed-step simulation expects dt=1/60')
        self.tick_count+=1
        self.elapsed+=dt
        self.events=[]
        p=self.player
        if self.game_over:
            if cmd.restart:
                self.restart_session()
            return
        if cmd.restart:
            self.load_room(self.room.name, reset=True)
            return
        if p.dead_time>0:
            p.dead_time-=dt
            # Rust death interlude holds the body in place until the course
            # replay. The authored death row still advances visually.
            p.anim_time+=dt
            if p.dead_time<=0:
                if self.lives == 0:
                    self.game_over = True
                    p.dead_time = 0
                else:
                    self.load_room(self.room.name,preserve_form=False,reset=True)
            return
        if self.pipe_state:
            self._pipe_step(dt)
            return
        if self._goal_tick(dt):
            return
        self.clock=max(0,self.clock-dt)
        if self.clock == 0:
            self.die()
            return
        p.invulnerable=max(0,p.invulnerable-dt)
        p.quasar=max(0,p.quasar-dt)
        p.shot_timer=max(0,p.shot_timer-dt)
        p.shoot_time=max(0,p.shoot_time-dt)
        p.anim_time+=dt
        if p.transition_time>0:
            p.transition_time=max(0,p.transition_time-dt)
            if p.transition_time==0:
                if p.transition=='cosmic_leave':
                    form=p.saved_form
                    self._change_form(form,'land',0)
                p.transition=''
        if cmd.utility and not p.transition_time:
            if p.cosmic:
                p.transition='cosmic_leave'
                p.transition_time=18*.095+.20
                p.vx=p.vy=0
                self.events.append(Event('transform',p.x,p.y))
            else:
                self._change_form('cosmic','cosmic_transform',36*.095)
                p.vx=p.vy=0
        if p.transition_time>0:
            return
        self._moving_tick(dt)
        if self._pipe_trigger(cmd):return
        tuning=COSMIC if p.cosmic else CLASSIC
        self._stand_or_crouch(cmd.down)
        p.vx = horizontal(p.vx, clamp(cmd.move,-1,1), p.grounded, cmd.run,
                          tuning, dt, crouch=p.crouched, precision=cmd.precision)
        if cmd.move:
            p.direction = 1 if cmd.move > 0 else -1
        if cmd.jump and (p.grounded or p.air_jumps<tuning.air_jumps):
            if not p.grounded:p.air_jumps+=1
            else:p.air_jumps=0
            p.vy = jump_velocity(p.vx, tuning)
            p.grounded = False
            p.jump_hold_cancelled = False
            self.events.append(Event('jump', p.x, p.y))
        previous_bottom = p.y + p.h
        stride_start_x = p.x
        # Rust's phased jump remembers an early release: tapping Jump again
        # in midair without a new jump grant does not restart weak gravity.
        if p.vy < 0 and not cmd.held_jump:
            p.jump_hold_cancelled = True
        held_ascent = cmd.held_jump and not p.jump_hold_cancelled
        p.vy = gravity_step(p.vy, held_ascent, tuning, dt)
        self._move(p, dt)
        if p.grounded and abs(p.x - stride_start_x) > 1e-6:
            # The SVG walk clip is three 95ms frames at a full 300px/s run.
            # Keeping roughly the same stride at slower speeds avoids the
            # ice-skating look when Mary-O walks at the 60% throttle.
            distance = 45.0 if p.crouched else 85.0
            cycle = 0.330 if p.crouched else 0.285
            p.walk_anim_time += abs(p.x - stride_start_x) / distance * cycle
        if p.grounded:
            p.air_jumps = 0
            p.jump_hold_cancelled = False
        # The original renderer locked the camera forward. Lite intentionally
        # permits both scrolling left in long rooms and exiting through their
        # left boundary, returning to the preceding course.
        # LDtk's course bounds usually contain solid end walls, so a literal
        # x==0 / x==width trigger is unreachable in some rooms. Treat the left
        # starting lane and the cleared course's right goal area as exits.
        # This lets a player walk backwards, not just use F6.
        spawn = self.room.spawn()
        left_exit = max(64, spawn.x + 8)
        if cmd.move < 0 and p.x <= left_exit and self.previous_room() is not None:
            self.go_previous()
            return
        # Cleared courses may be traversed again without redoing a cinematic.
        goals = [q.x for q in self.room.all('OneWayPlatform')
                 if q.fields.get('name') == 'goal_pole']
        goals += [q.x for q in self.solids
                  if q.fields.get('name') == 'goal_switch']
        right_exit = max(self.room.width - 320, max(goals, default=0) + 90)
        if (cmd.move > 0 and self.room.name in self.cleared
                and p.x >= right_exit):
            self.go_next()
            return
        live_sparks = sum(not shot.enemy and shot.life>0 for shot in self.sparks)
        if ((cmd.fire or cmd.run_pressed) and p.form in ('fire','cosmic')
                and p.shot_timer<=0 and live_sparks<2):
            p.shot_timer=.4
            p.shoot_time=.18
            # Rust spark muzzle: offset (0.5855, -0.0762) of body height,
            # relative to its centre. Horizontal launch; gravity bends it.
            self.sparks.append(Spark(p.foot[0] + p.direction*p.h*.5855,
                                     p.y+p.h*(.5-.0762),p.direction*300,0))
            self.events.append(Event('shoot',p.x,p.y))
        self._enemy_tick(dt)
        self._spark_tick(dt)
        self._items_tick(dt)
        self._player_enemy_contacts(previous_bottom)
        self._hazards_update(dt)
        self._hazard_tick()
        self._goal_tick(0)
        if self.room.name == 'mary_o_1_1' and p.y<-35:
            self.load_room('mary_o_warp')

    def display_animation(self):
        p=self.player
        if p.dead_time>0:return 'death'
        if p.transition_time>0:return p.transition
        if p.shoot_time>0:return 'shoot'
        if p.crouched:
            if not p.grounded:return 'crouch_jump'
            return 'crouch_walk' if abs(p.vx)>20 else 'crouch'
        if not p.grounded:return 'jump' if p.vy<0 else 'fall'
        if abs(p.vx)>85 and p.vx*p.direction<0:return 'skid'
        return 'walk' if abs(p.vx)>20 else 'idle'

    def summary(self):
        return dict(room=self.room.name,form=self.player.form,
                    player=(round(self.player.x,2),round(self.player.y,2)),
                    velocity=(round(self.player.vx,2),round(self.player.vy,2)),
                    lives=self.lives,score=self.score,coins=self.coins,
                    game_over=self.game_over,
                    enemies=sum(e.alive for e in self.enemies),
                    cleared=sorted(self.cleared),
                    visited=sorted(self.room_cache),
                    tick=self.tick_count)
