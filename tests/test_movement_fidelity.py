"""Real 60 Hz gameplay assertions for Mary-O's feel and stance geometry.

The compact teaching map keeps every collision deterministic. In particular,
the passage is exactly SMALL_H high; testing poses alone misses the actual bug.
"""
from __future__ import annotations

import pytest

from mary_o_lite.content import Level, Thing
from mary_o_lite.game import Command, Enemy, Game, Item, Moving, SMALL_H, TALL_H, STEP
from mary_o_lite.physics import CLASSIC


def lab(*, roof=True, gap_start=192, gap_end=320, ground_end=1024):
    width, height, ground_y = 1024, 400, 256
    grid_width, grid_height = width // 16, height // 16
    collision = [0] * (grid_width * grid_height)
    for y in range(ground_y // 16, grid_height):
        for x in range(min(grid_width, ground_end // 16)):
            collision[y * grid_width + x] = 1
    if roof:
        for x in range(gap_start // 16, gap_end // 16):
            collision[(ground_y // 16 - 3) * grid_width + x] = 1
    game = Game()
    game.room = Level('teaching_physics_lab', 'Physics Lab', 'starlight', '',
                      width, height, grid_width, grid_height, collision, [])
    game.blocks = []
    game.oneway = []
    game.solids = []
    game.pipes = []
    game.moving = []
    game.enemies = []
    game.items = []
    game.sparks = []
    game.hazards = []
    p = game.player
    p.x, p.y, p.w, p.h = 64.0, ground_y - SMALL_H, 24, SMALL_H
    p.form, p.crouched = 'small', False
    p.vx = p.vy = 0.0
    p.grounded = True
    p.direction = 1
    return game


def test_tall_and_fire_crouch_match_small_player_collision_height():
    for form in ('tall', 'fire', 'cosmic'):
        game = lab()
        p = game.player
        p.form, p.h, p.y = form, TALL_H, 256 - TALL_H
        foot = p.foot[1]
        game._stand_or_crouch(True)
        assert p.crouched and p.h == SMALL_H and p.foot[1] == foot
        game._stand_or_crouch(False)
        assert not p.crouched and p.h == TALL_H and p.foot[1] == foot


def test_tall_can_crawl_through_a_passage_that_fits_small_player():
    game = lab()
    p = game.player
    p.form, p.h, p.y = 'tall', TALL_H, 256 - TALL_H
    initial_foot = p.foot[1]
    for _ in range(360):
        game.step(Command(move=1, down=True, run=True))
        if p.x > 250:
            break
    assert 205 < p.x <= 260, 'Mary-O should advance into the 32px crawl tunnel'
    assert p.h == SMALL_H and p.crouched
    assert p.foot[1] == pytest.approx(initial_foot)
    assert not game.solid_at(p.box)
    # Let go of Down under the roof: no forced stand and no ceiling overlap.
    for _ in range(3):
        game.step(Command(move=1, run=True))
    assert p.crouched and p.h == SMALL_H
    assert not game.solid_at(p.box)
    # Leaving the passage allows Mary-O to stand on her next clear tick.
    for _ in range(180):
        game.step(Command(move=1, run=True))
        if p.x > 325:
            break
    assert not p.crouched and p.h == TALL_H
    assert p.foot[1] == pytest.approx(initial_foot)


def test_entering_crouch_requires_ground_but_crouch_survives_ledge():
    game = lab(roof=False, ground_end=128)
    p = game.player
    p.form, p.h, p.y = 'tall', TALL_H, 256 - TALL_H
    p.grounded = False
    game._stand_or_crouch(True)
    assert p.h == TALL_H, 'Cannot first crouch in midair'
    p.grounded = True
    game._stand_or_crouch(True)
    assert p.h == SMALL_H
    p.x, p.vx = 109, 260
    for _ in range(30):
        game.step(Command(move=1, down=True, run=True))
        if not p.grounded:
            break
    assert not p.grounded
    game.step(Command(move=1, down=True, run=True))
    assert p.crouched and p.h == SMALL_H
    assert game.display_animation() == 'crouch_jump'


def test_upgrading_form_in_small_only_passage_defers_expansion():
    game = lab()
    p = game.player
    p.x = 230
    p.y = 256 - SMALL_H
    game._collect(Item('wand', p.x, p.y))
    assert p.form == 'tall' and p.h == SMALL_H and p.crouched
    assert not game.solid_at(p.box)
    for _ in range(24):
        game.step(Command())
    assert p.h == SMALL_H and p.crouched
    game._collect(Item('lantern', p.x, p.y))
    assert p.form == 'fire' and p.h == SMALL_H
    assert not game.solid_at(p.box)


def test_walk_default_run_modifier_and_momentum_slowdown():
    walk = lab(roof=False)
    run = lab(roof=False)
    for _ in range(155):
        walk.step(Command(move=1))
        run.step(Command(move=1, run=True))
    assert walk.player.vx == pytest.approx(CLASSIC.max_run * .6)
    assert run.player.vx == pytest.approx(CLASSIC.max_run)
    old_run = run.player.vx
    run.step(Command(move=1))
    assert CLASSIC.max_run * .6 < run.player.vx < old_run


def test_reversal_produces_visible_ground_skid():
    game = lab(roof=False)
    p = game.player
    for _ in range(55):
        game.step(Command(move=1, run=True))
    assert p.vx > 200
    game.step(Command(move=-1, run=True))
    assert p.vx > 0 and p.direction == -1
    assert game.display_animation() == 'skid'
    for _ in range(28):
        game.step(Command(move=-1, run=True))
    assert p.vx < 0


def test_repress_does_not_restore_weak_jump_gravity():
    game = lab(roof=False)
    game.step(Command(jump=True, held_jump=True))
    game.step(Command(held_jump=False))
    released_vy = game.player.vy
    assert game.player.jump_hold_cancelled
    game.step(Command(held_jump=True))
    assert game.player.vy == pytest.approx(released_vy + CLASSIC.gravity * STEP)


def test_jump_still_requires_live_ground_contact_no_buffer_or_coyote():
    game = lab(roof=False)
    p = game.player
    p.grounded = False
    p.y = 120
    p.vy = 40
    game.step(Command(jump=True, held_jump=True))
    assert p.vy > 0


def test_walking_enemy_faces_away_after_hitting_wall():
    game = lab(roof=False)
    game.solids.append(Thing('Solid', 112, 0, 16, 260))
    e = Enemy('ai_slop', 87, 170, 24, 24, vx=32, facing=1)
    game.enemies = [e]
    for _ in range(5):
        game._enemy_tick(STEP)
    assert e.facing == -1 and e.vx < 0
    x = e.x
    game._enemy_tick(STEP)
    assert e.x < x, 'Walker must move away from wall, not jitter into it'


def test_airborne_body_near_moving_deck_is_not_carried_sideways():
    game = lab(roof=False)
    deck = Thing('MovingPlatform', 200, 220, 80, 12, {'sweep_dx': 100, 'speed': 60})
    game.moving = [Moving(deck, 200, 220, 200, 220)]
    p = game.player
    p.x, p.y, p.vy = 215, 220 - p.h + 1, 35
    p.grounded = False
    x = p.x
    game._moving_tick(STEP)
    assert p.x == x and not p.grounded


def test_grounded_passenger_follows_platform_but_not_through_wall():
    game = lab(roof=False)
    deck = Thing('MovingPlatform', 200, 220, 80, 12, {'sweep_dx': 100, 'speed': 60})
    game.moving = [Moving(deck, 200, 220, 200, 220)]
    p = game.player
    p.x, p.y, p.vy = 210, 220 - p.h, 0
    p.grounded = True
    game._moving_tick(STEP)
    assert p.x == pytest.approx(211)
    assert p.grounded
    game.solids.append(Thing('Solid', 235, 160, 16, 65))
    p.x = 235 - p.w
    for _ in range(3):
        game._moving_tick(STEP)
    assert p.x + p.w <= 235 + 1e-6


def test_hidden_block_becomes_solid_after_its_first_bonk():
    from mary_o_lite.geometry import Box
    game = Game('mary_o_1_2')
    block = next(b for b in game.blocks if b.fields.get('kind') == 'Hidden')
    volume = Box(block.x + 1, block.y + 1, block.w - 2, block.h - 2)
    assert not game.solid_at(volume), 'Unspent hidden blocks do not block passage'
    game.bonk(block)
    assert block.identifier in game.spent
    assert game.solid_at(volume), 'Visible spent hidden block must have collision'


def test_walk_animation_cadence_follows_ground_distance():
    walk = lab(roof=False)
    run = lab(roof=False)
    for _ in range(75):
        walk.step(Command(move=1))
        run.step(Command(move=1, run=True))
    assert 0 < walk.player.walk_anim_time < run.player.walk_anim_time
    phase = walk.player.walk_anim_time
    for _ in range(12):
        walk.step(Command())
    # Coasting legitimately advances the animation while the feet still move.
    assert walk.player.walk_anim_time > phase
    for _ in range(100):
        walk.step(Command())
    at_rest = walk.player.walk_anim_time
    for _ in range(8):
        walk.step(Command())
    assert walk.player.walk_anim_time == at_rest


def test_run_modifier_press_is_fire_spark_without_repeating_while_held():
    game = lab(roof=False)
    p = game.player
    p.form, p.h, p.y = 'fire', TALL_H, 256 - TALL_H
    game.step(Command(run=True, run_pressed=True))
    assert any(e.kind == 'shoot' for e in game.events)
    for _ in range(35):
        game.step(Command(run=True))
    assert not any(e.kind == 'shoot' for e in game.events)
    game.step(Command(run=True, run_pressed=True))
    assert any(e.kind == 'shoot' for e in game.events)


def test_lifting_deck_does_not_move_passenger_through_ceiling():
    game = lab(roof=False)
    lift = Thing('MovingPlatform', 200, 220, 80, 12,
                 {'loop_dy': -260, 'loop_min_y': -20, 'speed': 60})
    game.moving = [Moving(lift, 200, 220, 200, 220)]
    game.solids = [Thing('Solid', 195, 160, 80, 28)]
    p = game.player
    p.x, p.y, p.vy, p.grounded = 210, 188, 0, True
    game._moving_tick(STEP)
    assert p.y >= 188
    assert not game.solid_at(p.box)
    assert not p.grounded, 'The lift must detach rather than push through the ceiling'
