"""Bidirectional scrolling and course revisits without losing local progress."""
from mary_o_lite.content import COURSE_ORDER
from mary_o_lite.game import Command, Game, Item


def test_first_course_has_no_previous_and_never_wraps():
    game = Game('mary_o_1_1')
    assert game.previous_room() is None
    assert not game.go_previous()
    assert game.room.name == 'mary_o_1_1'


def test_reverse_links_follow_authored_course_order():
    for previous, current in zip(COURSE_ORDER, COURSE_ORDER[1:]):
        game = Game(current)
        assert game.previous_room() == previous
        assert game.go_previous()
        assert game.room.name == previous
        assert game.player.direction == -1
        assert 0 <= game.player.x <= game.room.width - game.player.w
        assert not game.solid_at(game.player.box)


def test_room_state_and_global_progress_survive_revisits():
    game = Game('mary_o_1_1')
    first = game.room.name
    block = next(b for b in game.blocks if b.fields.get('kind') == 'Power')
    game.bonk(block)
    assert block.identifier in game.spent
    enemy = game.enemies[0]
    enemy.alive = False
    initial_items = len(game.items)
    game.coins = 11
    game.score = 345
    game._collect(Item('wand', game.player.x, game.player.y))
    game.score = 345
    assert game.player.form == 'tall'
    game.go_next()
    assert game.room.name == 'mary_o_1_2'
    game.enemies[0].alive = False
    assert game.go_previous()
    assert game.room.name == first
    assert block.identifier in game.spent
    assert not game.enemies[0].alive
    assert len(game.items) == initial_items
    assert game.coins == 11 and game.score == 345
    assert game.player.form == 'tall'
    game.go_next()
    assert not game.enemies[0].alive


def test_step_moves_through_left_edge_to_previous_room():
    game = Game('mary_o_1_2')
    game.player.x = 0
    game.player.vx = -180
    game.step(Command(move=-1))
    assert game.room.name == 'mary_o_1_1'
    assert game.player.x > game.room.width * .5


def test_cleared_room_can_continue_right_and_go_back_again():
    game = Game('mary_o_1_2')
    game.cleared.add(game.room.name)
    game.player.x = game.room.width - 120
    game.player.vx = 150
    game.step(Command(move=1))
    assert game.room.name == 'mary_o_1_3'
    assert game.go_previous()
    assert game.room.name == 'mary_o_1_2'
    assert not game.flag_state
    assert game.room.name in game.cleared


def test_restarting_one_course_preserves_other_course_history():
    game = Game('mary_o_1_1')
    game.enemies[0].alive = False
    game.go_next()
    game.enemies[0].alive = False
    game.step(Command(restart=True))
    assert game.enemies[0].alive
    game.go_previous()
    assert not game.enemies[0].alive


def test_returning_left_crosses_uncleared_pole_without_autocompleting():
    game = Game('mary_o_1_2')
    game.go_previous()
    pole = next(e for e in game.room.all('OneWayPlatform')
                if e.fields.get('name') == 'goal_pole')
    game.player.x = pole.x - 5
    game.player.y = pole.y + 8
    assert game.returning_left
    assert not game._goal_tick(0)
    assert not game.flag_state
    game.player.x = pole.x - 110
    assert not game._goal_tick(0)
    assert not game.returning_left
    game.player.x = pole.x - 5
    assert game._goal_tick(0)
    assert game.flag_state == 'pole'


def test_course_clock_is_restored_on_revisit():
    game = Game()
    for _ in range(70):
        game.step()
    old = game.clock
    game.go_next()
    game.go_previous()
    assert game.clock == old
