"""The imported Mary-O text world must remain teachably inspectable."""
from collections import Counter

from mary_o_lite.content import COURSE_ORDER, ASSETS, TILE, levels


def test_world_has_original_world_one_two_and_secret():
    rooms = levels()
    assert set(rooms) == set(COURSE_ORDER) | {'mary_o_warp'}
    assert len(COURSE_ORDER) == 8
    assert rooms['mary_o_1_1'].next_room == 'mary_o_1_2'
    assert rooms['mary_o_1_4'].next_room == 'mary_o_2_1'
    assert rooms['mary_o_2_4'].next_room == 'mary_o_1_1'


def test_every_room_has_spawn_tiles_and_consistent_geometry():
    for room in levels().values():
        assert room.width == room.grid_width * TILE
        assert room.height == room.grid_height * TILE
        assert len(room.collision) == room.grid_width * room.grid_height
        assert room.spawn().kind == 'PlayerStart'
        assert room.next_room in levels()
        assert room.title
        assert room.biome in {'starlight', 'starless', 'stardune', 'void_castle'}


def test_level_artifacts_are_authored_text():
    assert (ASSETS/'worlds'/'mary_o.ldtk').read_text().startswith('{')
    assert (ASSETS/'svg'/'mary_o_v2.svg').read_text().lstrip().startswith('<?xml')
    assert len(levels()['mary_o_1_2'].all('MaryOBlock')) > 300
    assert any(t.fields.get('kind') == 'Hidden' for t in levels()['mary_o_1_2'].all('MaryOBlock'))
    assert len(levels()['mary_o_1_3'].all('MovingPlatform')) >= 3


def test_goal_switch_boss_and_obstacles_present_in_both_castles():
    for name in ('mary_o_1_4', 'mary_o_2_4'):
        room = levels()[name]
        named = {t.fields.get('name') for t in room.all('Solid')}
        assert {'goal_switch', 'goal_gate'} <= named
        assert any(t.fields.get('character_id') == 'void_lizard' for t in room.all('EnemySpawn'))
        assert any(t.fields.get('kind') == 'Plank' for t in room.all('MaryOBlock'))
