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

STEP = 1 / 60
SMALL_H = 32
TALL_H = 62
BLOCK_SCORE = 50


@dataclass
class Command:
    move: int = 0
    jump: bool = False          # Key-down edge, not held state.
    held_jump: bool = False
    fire: bool = False
    down: bool = False          # Held: crouch while standing; enter pipes.
    up: bool = False            # Held: leave downward-facing pipes.
    walk: bool = False
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
    shoot_time: float = 0
    dead_time: float = 0
    crouched: bool = False

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

    @property
    def box(self): return Box(self.x - 9, self.y - 9, 18, 18)


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
        )

    def previous_room(self) -> str | None:
        """Linear course progression has no wraparound at World 1-1."""
        if self.room.name not in COURSE_ORDER:
            return None
        index = COURSE_ORDER.index(self.room.name)
        return COURSE_ORDER[index - 1] if index > 0 else None

    def go_previous(self) -> bool:
        """Classroom shortcut and left-edge exit use the same transition."""
        name = self.previous_room()
        if name is None:
            return False
        self.load_room(name, entry='right')
        return True

    def go_next(self) -> bool:
        """Move forward, retaining history so later rooms can be revisited."""
        name = self.room.next_room
        if name not in self.rooms:
            return False
        self.load_room(name, entry='left')
        return True

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
        p.shoot_time = p.anim_time = 0
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
        self.hazards = self.room.all('DamageVolume')
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
            if e.identifier in self.broken or e.fields.get('kind') == 'Hidden':
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
        """Resolve horizontal then vertical contact, including one-way floors."""
        obj.grounded = False
        dx = obj.vx * dt
        if dx:
            obj.x += dx
            for wall, one_way in self._colliders(obj.box):
                if one_way or not obj.box.overlaps(wall):
                    continue
                if dx > 0:
                    obj.x = min(obj.x, wall.x - obj.w)
                else:
                    obj.x = max(obj.x, wall.x + wall.w)
                obj.vx = -obj.vx if bounce else 0
        dy = obj.vy * dt
        if dy:
            old_bottom, old_top = obj.y + obj.h, obj.y
            obj.y += dy
            for wall, one_way in self._colliders(obj.box):
                if not obj.box.overlaps(wall):
                    continue
                if dy > 0:
                    if old_bottom > wall.y + 2 and one_way:
                        continue
                    obj.y = min(obj.y, wall.y - obj.h)
                    obj.vy = 0
                    obj.grounded = True
                elif not one_way and old_top >= wall.y + wall.h - 2:
                    obj.y = max(obj.y, wall.y + wall.h)
                    obj.vy = 0
                    if obj is self.player and isinstance(wall, Thing) and wall.kind == 'MaryOBlock':
                        self.bonk(wall)
            if dy < 0 and obj is self.player:
                # Hidden blocks are invisible and non-solid until their first
                # upward head contact. They then become spent visible blocks.
                for hidden in self.blocks:
                    if (hidden.fields.get('kind') != 'Hidden'
                            or hidden.identifier in self.spent
                            or hidden.identifier in self.broken):
                        continue
                    if (old_top >= hidden.bottom - 2
                            and obj.box.overlaps(Box(hidden.x, hidden.y, hidden.w, hidden.h))):
                        obj.y = max(obj.y, hidden.bottom)
                        obj.vy = 0
                        self.bonk(hidden)
                        break
        else:
            # Check support, so next tick can accept a newly pressed jump.
            under = Box(obj.x + 2, obj.y + obj.h, max(1,obj.w-4), 1.5)
            obj.grounded = any(under.overlaps(wall) and under.y <= wall.y + 2 for wall, _ in self._colliders(under))
        obj.x = clamp(obj.x, 0, max(0,self.room.width-obj.w))

    def _stand_or_crouch(self, crouch: bool):
        p = self.player
        full_height = SMALL_H if p.form == 'small' else TALL_H
        if p.form == 'small': crouch = False
        desired = 37 if crouch else full_height
        if desired > p.h:
            probe = Box(p.x, p.y + p.h - desired, p.w, desired)
            if self.solid_at(probe):
                crouch = True
                desired = p.h
        p.y += p.h - desired
        p.h = desired
        p.crouched = crouch

    def _change_form(self, form: str, transition: str, length: float):
        p = self.player
        if form == p.form:
            return
        previous_h = p.h
        if form == 'cosmic':
            p.saved_form = p.form
        p.form = form
        p.h = SMALL_H if form == 'small' else TALL_H
        p.y += previous_h - p.h
        p.air_jumps = 0
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
        self.lives -= 1
        p.dead_time = 1.1
        p.vx = 0
        p.vy = -320
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
                # A plant returns into its pot and stays there when Mary-O is near.
                cycle=e.age % 5.5
                exposure = max(0.0,min(1.0,(cycle-.8)/.6,(4.8-cycle)/.6))
                if abs(e.x-p.x)<65 and exposure < .3: exposure=0
                e.y=e.anchor_y-32*exposure
                e.phase='hidden' if exposure<.15 else 'emerged'
                continue
            if e.kind in ('laden_swallow','npc_snakes_on_a_paper_plane','npc_snakes_on_a_cartesian_plane'):
                e.x+=math.sin(e.age*1.8)*dt*42
                e.y=e.anchor_y+math.sin(e.age*3)*14
                if e.kind=='laden_swallow' and int(e.age*1.1)!=int((e.age-dt)*1.1):
                    self.sparks.append(Spark(e.x+e.w/2,e.y+e.h,0,80,True,3.5,0))
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
            if e.kind == 'void_lizard':
                e.vx=e.facing*55
                if e.grounded and int(e.age*1.5)!=int((e.age-dt)*1.5):
                    e.vy=-400
                if int(e.age/.95)!=int((e.age-dt)/.95):
                    self.sparks.append(Spark(e.x+e.w/2,e.y+e.h*.35,e.facing*180,-115,True,3,0))
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
            s.x+=s.vx*dt
            s.vy=min(540,s.vy+900*dt)
            s.y+=s.vy*dt
            if s.y>self.room.height+60 or s.x<0 or s.x>self.room.width: s.life=0;continue
            collisions = list(self._colliders(s.box))
            for wall, one_way in collisions:
                if not s.box.overlaps(wall):continue
                if s.vy>0 and s.bounces>0 and s.y<wall.y+10:
                    s.y=wall.y-10;s.vy=-300;s.bounces-=1
                elif not one_way:
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

    def _moving_tick(self, dt):
        for m in self.moving:
            m.age+=dt
            m.old_x, m.old_y=m.x,m.y
            f=m.thing.fields
            speed=1.0
            # These are authored lifts. Their path shape is selected by level;
            # an oscillating platform is enough without an ECS movement graph.
            travel=96
            axis = 'y' if f.get('path_mode') in ('Vertical','vertical') or 'lift' in str(f.get('name','')).lower() else 'x'
            t=math.sin(m.age*speed)
            m.x=m.start_x+(travel*t if axis=='x' else 0)
            m.y=m.start_y+(travel*t if axis=='y' else 0)
            p=self.player
            if p.vy >= -10 and abs(p.y+p.h-m.old_y)<5 and p.x+p.w>m.old_x and p.x<m.old_x+m.thing.w:
                p.x+=m.x-m.old_x
                p.y+=m.y-m.old_y
                p.grounded=True

    def _player_enemy_contacts(self, previous_bottom: float):
        p=self.player
        for e in self.enemies:
            if not e.alive or e.phase=='hidden' or not p.box.overlaps(e.box):continue
            if p.cosmic or p.quasar>0:
                self._enemy_kill(e)
                continue
            if e.kind != 'void_star' and p.vy>=0 and previous_bottom <= e.y+13:
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
                p.vx=-100*e.facing
                self.events.append(Event('kick',e.x,e.y))
            else:self._hurt(e.x)

    def _hazard_tick(self):
        p=self.player
        for e in self.hazards:
            # The authored fire bar is a sequence of orbs. Rotate about their
            # nearest pivot in presentation while keeping the source hit areas.
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
        if cmd.restart:
            self.load_room(self.room.name, reset=True)
            return
        if p.dead_time>0:
            p.dead_time-=dt
            p.vy+=CLASSIC.gravity*dt
            p.y+=p.vy*dt
            if p.dead_time<=0:
                self.load_room(self.room.name,preserve_form=False,reset=True)
            return
        if self.pipe_state:
            self._pipe_step(dt)
            return
        if self._goal_tick(dt):
            return
        self.clock=max(0,self.clock-dt)
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
        self._stand_or_crouch(bool(cmd.down and p.grounded))
        p.vx=horizontal(p.vx,0 if p.crouched else clamp(cmd.move,-1,1),p.grounded,cmd.walk,tuning,dt)
        if cmd.move and not p.crouched:p.direction=1 if cmd.move>0 else -1
        if cmd.jump and (p.grounded or p.air_jumps<tuning.air_jumps):
            if not p.grounded:p.air_jumps+=1
            else:p.air_jumps=0
            p.vy=jump_velocity(p.vx,tuning)
            p.grounded=False
            self.events.append(Event('jump',p.x,p.y))
        previous_bottom=p.y+p.h
        p.vy=gravity_step(p.vy,cmd.held_jump,tuning,dt)
        self._move(p,dt)
        if p.grounded:p.air_jumps=0
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
        if cmd.fire and p.form in ('fire','cosmic') and p.shot_timer<=0:
            p.shot_timer=.4
            p.shoot_time=.18
            self.sparks.append(Spark(p.foot[0]+p.direction*18,p.y+min(p.h*.45,32),p.direction*300,-140))
            self.events.append(Event('shoot',p.x,p.y))
        self._enemy_tick(dt)
        self._spark_tick(dt)
        self._items_tick(dt)
        self._player_enemy_contacts(previous_bottom)
        self._hazard_tick()
        self._goal_tick(0)
        if self.room.name == 'mary_o_1_1' and p.y<-35:
            self.load_room('mary_o_warp')

    def display_animation(self):
        p=self.player
        if p.dead_time>0:return 'death'
        if p.transition_time>0:return p.transition
        if p.shoot_time>0:return 'shoot'
        if p.crouched:return 'crouch_walk' if abs(p.vx)>35 else 'crouch'
        if not p.grounded:return 'jump' if p.vy<0 else 'fall'
        if abs(p.vx)>85 and p.vx*p.direction<0:return 'skid'
        return 'walk' if abs(p.vx)>20 else 'idle'

    def summary(self):
        return dict(room=self.room.name,form=self.player.form,
                    player=(round(self.player.x,2),round(self.player.y,2)),
                    velocity=(round(self.player.vx,2),round(self.player.vy,2)),
                    lives=self.lives,score=self.score,coins=self.coins,
                    enemies=sum(e.alive for e in self.enemies),
                    cleared=sorted(self.cleared),
                    visited=sorted(self.room_cache),
                    tick=self.tick_count)
