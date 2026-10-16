"""Source-data fidelity and real animated obstacles, without Pygame."""
import math

from mary_o_lite.content import levels
from mary_o_lite.game import Command, Game
from mary_o_lite.motion import (
    parse_polyline, loop_position, ping_pong, wrapping_lift,
    wanted_plant_out, next_plant_out, plant_placement,
)


def test_firestick_content_has_76_authored_orbiting_orbs():
    all_orbs = [h for room in levels().values()
                for h in room.all('DamageVolume') if h.fields.get('path_points')]
    assert len(all_orbs) == 76
    assert {room.name for room in levels().values() if any(
        h.fields.get('path_points') for h in room.all('DamageVolume'))} == {
            'mary_o_1_4', 'mary_o_2_2', 'mary_o_2_4',
        }
    for orb in all_orbs:
        points = parse_polyline(orb.fields['path_points'])
        assert len(points) == 24
        assert float(orb.fields['path_speed']) > 0


def test_firestick_paths_have_real_motion_constant_speed_and_loop():
    orb = next(h for h in levels()['mary_o_1_4'].all('DamageVolume')
               if h.fields.get('path_points'))
    nodes = parse_polyline(orb.fields['path_points'])
    speed = float(orb.fields['path_speed'])
    assert math.dist(loop_position(nodes, speed, 0), nodes[0]) < 1e-6
    assert 0.35 < math.dist(loop_position(nodes, speed, .02), nodes[0]) < .7
    assert math.dist(loop_position(nodes, speed, 1), nodes[0]) > 10
    # Clockwise and counterclockwise paths remain distinct.
    other = next(h for h in levels()['mary_o_1_4'].all('DamageVolume')
                 if h.fields.get('path_points') and 'fire_bar_orb_5' in h.fields.get('name',''))
    assert loop_position(parse_polyline(other.fields['path_points']),
                         float(other.fields['path_speed']), .8) != nodes[0]


def test_simulation_uses_same_moving_firestick_position_for_contact():
    g = Game('mary_o_1_4')
    orb = next(h for h in g.hazards if h.fields.get('path_points'))
    first = (orb.x, orb.y)
    for _ in range(45):
        g._hazards_update(1/60)
    assert math.dist(first, (orb.x,orb.y)) > 8
    # Place Mary-O directly on a current orb. If she is small, it must hurt.
    p = g.player
    p.x, p.y = orb.x, orb.y
    g._hazard_tick()
    assert p.invulnerable > 0 or p.dead_time > 0
    # Room's authored LDtk object must not mutate.
    assert levels()['mary_o_1_4'].all('DamageVolume')[1].x == first[0]


def test_firestick_revisit_restores_local_phase():
    g = Game('mary_o_1_4')
    for _ in range(50):g._hazards_update(1/60)
    x = g.hazards[1].x
    elapsed = g.hazard_elapsed
    g.go_next()
    g.go_previous()
    assert abs(g.hazard_elapsed - elapsed) < 1e-9
    assert abs(g.hazards[1].x - x) < 1e-7


def test_ferries_use_authored_sweep_and_vertical_lift_loop():
    assert ping_pong(416,80,1)==80
    assert ping_pong(416,80,6)==352
    assert ping_pong(416,80,10.4)==0
    assert wrapping_lift(60,736,-32,60,1)==120
    assert wrapping_lift(60,-736,-32,60,1)==0
    g=Game('mary_o_1_3')
    m=next(m for m in g.moving if m.thing.fields.get('sweep_dx'))
    g._moving_tick(1/60)
    assert math.isclose(m.x, m.start_x+float(m.thing.fields['speed'])/60)
    g2=Game('mary_o_1_2')
    lift=next(m for m in g2.moving if m.thing.fields.get('loop_dy')>0)
    g2._moving_tick(1/60)
    assert math.isclose(lift.y,lift.start_y+float(lift.thing.fields['speed'])/60)


def test_snake_plant_rust_cycle_and_pot_alignment():
    assert wanted_plant_out(0)==0
    assert math.isclose(wanted_plant_out(18),.5)
    assert wanted_plant_out(36)==1
    assert wanted_plant_out(143)==1
    assert math.isclose(wanted_plant_out(162),.5)
    assert wanted_plant_out(180)==0
    assert next_plant_out(0,1,True)==0
    assert math.isclose(next_plant_out(0,1,False),1/36)
    assert math.isclose(next_plant_out(1,0,True),35/36)
    g=Game('mary_o_1_3')
    plants=[e for e in g.enemies if e.kind=='snake_plant']
    assert len(plants)==3
    e=plants[0]
    pipe=next(q for q in g.pipes if q.x<=e.x+e.w/2<=q.right)
    assert e.pot_y == pipe.y and e.pot_x==pipe.cx
    assert e.phase=='hidden' and e.exposure==0
    e.age=0
    g.player.x=10000
    g._enemy_tick(1/60)
    assert 0<=e.exposure<=1
    left,top,w,h=plant_placement(96,128,21,48,127,pipe.cx,pipe.y,1,46)
    assert math.isclose(left+w/2,pipe.cx)
    assert math.isclose(top+127*h/128,pipe.y)
    _,partial_top,_,_=plant_placement(96,128,21,48,127,pipe.cx,pipe.y,.5,46)
    assert math.isclose(partial_top-top,23)


def test_snake_plant_is_dangerous_even_when_stomped():
    g=Game('mary_o_1_3')
    snake=next(e for e in g.enemies if e.kind=='snake_plant')
    snake.exposure=1
    snake.phase='emerged'
    snake.y=snake.pot_y-snake.h
    p=g.player
    p.x=snake.x+1;p.y=snake.y-19;p.vy=200
    p.grounded=False
    p.invulnerable=0
    previous_bottom=p.y+p.h
    g._player_enemy_contacts(previous_bottom)
    assert snake.alive
    assert p.dead_time>0 or p.invulnerable>0


def test_all_authored_enemy_kinds_have_source_art_or_vector_source():
    """A copied level must not silently fall back to generic shape enemies."""
    all_kinds = {thing.fields['character_id'] for room in levels().values()
                 for thing in room.all('EnemySpawn')}
    painted = {'ai_slop', 'solid_snake', 'snake_plant', 'void_star',
               'void_lizard', 'npc_snakes_on_a_paper_plane',
               'npc_snakes_on_a_cartesian_plane', 'laden_swallow'}
    assert all_kinds == painted
    from mary_o_lite.content import ASSETS
    assert (ASSETS / 'svg/african_swallow.svg').is_file()
    from ambition_art import snakes_on_planes
    assert snakes_on_planes.PAPER_SPEC.target_name
    assert snakes_on_planes.CARTESIAN_SPEC.target_name


def test_authored_void_orb_coconut_and_fire_orb_are_regenerable():
    from ambition_art import coconut, fire_orb
    fire = fire_orb._render_frame('idle', 0, 8)
    void = fire_orb.render_void_orb('idle', 0, 1)
    nut = coconut._render_frame('idle', 0, 1)
    assert fire.size == void.size == (128, 128)
    assert nut.size == (56, 48)
    assert all(pic.mode == 'RGBA' and pic.getbbox() for pic in (fire, void, nut))
    assert fire.tobytes() != void.tobytes()


def test_enemy_projectiles_remember_which_original_visual_to_draw():
    g = Game('mary_o_1_3')
    bird = next(e for e in g.enemies if e.kind == 'laden_swallow')
    g.player.x = bird.x
    bird.age = .905
    g._enemy_tick(1 / 60)
    assert any(s.enemy and s.visual == 'coconut' for s in g.sparks)
    castle = Game('mary_o_1_4')
    lizard = next(e for e in castle.enemies if e.kind == 'void_lizard')
    castle.player.x = lizard.x
    lizard.age = .949
    castle._enemy_tick(1 / 60)
    assert any(s.enemy and s.visual == 'void_orb' for s in castle.sparks)
