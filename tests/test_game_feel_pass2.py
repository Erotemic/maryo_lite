"""Movement and source-rule parity checks for the X-run fidelity pass.

These exercise geometry and authored projectile behavior, not slide text or
rendering labels. They deliberately use plain Python without Pygame.
"""
from __future__ import annotations

import pytest

from mary_o_lite.content import Level, Thing
from mary_o_lite.game import Command, DEATH_DWELL, Enemy, Game, Spark, STEP, TALL_H


def empty_room():
    game = Game()
    game.room = Level('contact_lab', 'Contact Lab', 'starlight', '',
                      1200, 512, 75, 32, [0] * (75 * 32), [])
    game.solids = []
    game.oneway = []
    game.blocks = []
    game.pipes = []
    game.moving = []
    game.enemies = []
    game.hazards = []
    game.items = []
    game.sparks = []
    p = game.player
    p.x, p.y, p.w, p.h = 200., 160., 24., 32.
    p.vx = p.vy = 0
    p.grounded = False
    return game


def test_horizontal_sweep_stops_at_first_wall_not_last_list_member():
    g = empty_room()
    p = g.player
    p.vx = 1200.0
    # Reverse authored insertion order to prove contact follows geometry.
    g.solids = [Thing('Solid', 250, 145, 12, 60),
                Thing('Solid', 228, 145, 12, 60)]
    g._move(p, STEP)
    assert p.x == pytest.approx(204.0)
    assert p.vx == 0
    assert not g.solid_at(p.box)


def test_head_bonk_resolves_nearest_ceiling_and_just_one_block():
    g = empty_room()
    p = g.player
    p.y = 240
    p.vy = -3000  # Stress the sweep with a jump that crosses two obstacles.
    near = Thing('MaryOBlock', 200, 207, 24, 10,
                 {'kind': 'Question', 'contents': 'Coin'}, 'near')
    far = Thing('MaryOBlock', 200, 185, 24, 10,
                {'kind': 'Question', 'contents': 'Coin'}, 'far')
    g.blocks = [far, near]
    g._move(p, STEP)
    assert p.y == pytest.approx(217)
    assert p.vy == 0
    assert g.spent == {'near'}
    assert 'far' not in g.spent


def test_oneway_deck_only_supports_from_above():
    g = empty_room()
    p = g.player
    g.oneway = [Thing('OneWayPlatform', 175, 220, 100, 12)]
    p.y = 231
    p.vy = -480
    g._move(p, STEP)
    assert p.y == pytest.approx(223)
    assert not p.grounded
    p.y = 181
    p.vy = 480
    g._move(p, STEP)
    assert p.y == pytest.approx(188)
    assert p.grounded  # Falling from above reaches the top face this tick.
    g._move(p, STEP)
    assert p.y == pytest.approx(188)
    assert p.grounded  # Resting on its top retains ground support.


def test_falling_from_a_small_gap_never_snaps_to_a_remote_ceiling():
    g = empty_room()
    p = g.player
    p.y = 140
    p.vy = 480
    g.solids = [Thing('Solid', 200, 190, 24, 16),
                Thing('Solid', 200, 250, 24, 16)]
    for _ in range(10):
        g._move(p, STEP)
    assert p.y == pytest.approx(158)
    assert p.grounded
    assert p.vy == 0


def test_x_run_press_shoots_once_and_cap_is_two_live_sparks():
    g = empty_room()
    g.solids.append(Thing('Solid', 0, 265, 1200, 20))
    p = g.player
    p.form, p.h, p.y = 'fire', TALL_H, 128
    p.grounded = True
    p.direction = 1
    g.step(Command(run=True, run_pressed=True))
    assert len(g.sparks) == 1
    s = g.sparks[0]
    assert s.vx == 300 and s.gravity == 900
    # The projectile is simulated once in the creation tick (5px horizontal).
    assert s.x == pytest.approx(p.foot[0] + TALL_H * .5855 + 300 * STEP)
    assert s.y == pytest.approx(p.y + TALL_H * (.5 - .0762) + 900 * STEP**2)
    assert (s.box.w, s.box.h) == (20, 20)
    for _ in range(25):
        g.step(Command(run=True))
    assert not any(event.kind == 'shoot' for event in g.events)
    g.step(Command(run=True, run_pressed=True))
    assert len(g.sparks) == 2
    for _ in range(25):
        g.step(Command(run=True))
    g.step(Command(run=True, run_pressed=True))
    assert len(g.sparks) == 2
    assert not any(event.kind == 'shoot' for event in g.events)


def test_enemy_bolts_and_coconuts_do_not_share_spark_gravity():
    g = empty_room()
    bolt = Spark(200, 100, 170, 0, True, 3.5, 0, 'void_orb', 0)
    coconut = Spark(250, 100, 0, 30, True, 4., 0, 'coconut', 760)
    player_spark = Spark(300, 100, 300, 0)
    g.sparks = [bolt, coconut, player_spark]
    g._spark_tick(STEP)
    assert bolt.vy == 0
    assert bolt.box.w == 24
    assert coconut.vy == pytest.approx(30 + 760 * STEP)
    assert player_spark.vy == pytest.approx(900 * STEP)


def test_fresh_kick_does_not_hurt_player_on_overlap():
    g = empty_room()
    p = g.player
    p.x, p.y = 195, 160
    p.grounded = True
    shell = Enemy('solid_snake', 210, 160, 24, 32, phase='shell')
    g.enemies = [shell]
    g._player_enemy_contacts(p.y + p.h)
    assert shell.phase == 'rolling'
    assert shell.kick_grace == pytest.approx(.25)
    g._player_enemy_contacts(p.y + p.h)
    assert p.dead_time == 0
    shell.kick_grace = 0
    g._player_enemy_contacts(p.y + p.h)
    assert p.dead_time > 0


def test_crouch_height_remains_small_form_size_after_hitting_wall():
    g = empty_room()
    p = g.player
    p.form, p.h, p.y = 'tall', TALL_H, 128
    p.grounded = True
    p.y = 250 - TALL_H
    g.solids = [Thing('Solid', 235, 186, 16, 90),
                Thing('Solid', 230, 186, 5, 32)]
    g._stand_or_crouch(True)
    assert p.h == 32 and p.crouched
    p.vx = 300
    g._move(p, STEP)
    assert p.h == 32
    assert not g.solid_at(p.box)


def test_rust_death_interlude_is_3_2_seconds_and_pins_body():
    g = empty_room()
    p = g.player
    before = (p.x, p.y)
    g.die()
    assert p.dead_time == pytest.approx(DEATH_DWELL)
    assert g.lives == 2
    for _ in range(60):
        g.step(Command(move=1, jump=True, run=True, held_jump=True))
    assert (p.x, p.y) == before
    assert p.anim_time > 0
    assert p.dead_time == pytest.approx(DEATH_DWELL - 1)


def test_lives_never_go_negative_and_game_over_requires_restarting():
    g = Game()
    g.lives = 1
    g.die()
    assert g.lives == 0
    for _ in range(round(DEATH_DWELL / STEP) + 2):
        g.step()
    assert g.game_over
    position = g.player.x, g.player.y
    for _ in range(200):
        g.step(Command(move=1, run=True, jump=True))
    assert g.lives == 0 and g.game_over
    assert (g.player.x, g.player.y) == position
    g.step(Command(restart=True))
    assert g.lives == 3
    assert not g.game_over
    assert g.room.name == 'mary_o_1_1'


def test_exhausted_course_clock_causes_death_not_free_play():
    g = empty_room()
    g.clock = STEP * .5
    g.step()
    assert g.clock == 0
    assert g.player.dead_time == DEATH_DWELL
