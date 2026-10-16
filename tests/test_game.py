"""Run the game as a simulation without a display or audio."""

from mary_o_lite.content import levels
from mary_o_lite.game import Game, Command, Item, SMALL_H, TALL_H


def grounded(game):
    for _ in range(70):game.step()
    assert game.player.grounded


def test_game_loads_original_world():
    game=Game()
    assert game.room.name=='mary_o_1_1'
    assert len(game.enemies)>5
    assert game.lives==3


def test_jump_requires_fresh_press_and_ground_contact():
    game=Game();grounded(game)
    game.step(Command(jump=True,held_jump=True))
    assert game.player.vy<0
    old_vy=game.player.vy
    game.step(Command(jump=True,held_jump=True))
    assert game.player.vy>old_vy


def test_jump_hold_goes_higher_than_quick_release():
    high=Game();low=Game();grounded(high);grounded(low)
    for i in range(21):
        high.step(Command(jump=i==0,held_jump=True))
        low.step(Command(jump=i==0,held_jump=False))
    assert high.player.y<low.player.y


def test_small_has_no_air_jump():
    game=Game();grounded(game)
    game.step(Command(jump=True,held_jump=True))
    for _ in range(6):game.step(Command(held_jump=True))
    prior=game.player.vy
    game.step(Command(jump=True,held_jump=True))
    assert game.player.vy>prior


def test_wand_lantern_hurt_and_death_forms():
    g=Game(); p=g.player
    g._collect(Item('wand',p.x,p.y))
    assert p.form=='tall' and p.h==TALL_H and p.transition=='grow'
    g._collect(Item('lantern',p.x,p.y))
    assert p.form=='fire' and p.transition=='fire_transform'
    p.invulnerable=0
    g._hurt(p.x-40)
    assert p.form=='tall' and p.transition=='shrink'
    p.invulnerable=0
    g._hurt(p.x-40)
    assert p.form=='small' and p.h==SMALL_H
    p.invulnerable=0
    g._hurt(p.x-40)
    assert p.dead_time>0 and g.lives==2


def test_cosmic_transition_lasts_then_returns_to_previous_form():
    game=Game();grounded(game)
    game.step(Command(utility=True))
    assert game.player.form=='cosmic'
    assert game.player.transition=='cosmic_transform'
    for _ in range(230):game.step()
    assert game.player.transition_time==0
    game.step(Command(utility=True))
    assert game.player.transition=='cosmic_leave'
    for _ in range(125):game.step()
    assert game.player.form=='small'
    assert game.player.transition_time==0


def test_cosmic_can_double_jump_and_fire():
    game=Game();grounded(game)
    game._change_form('cosmic','',0)
    for _ in range(2):game.step(Command())
    game.step(Command(jump=True,held_jump=True))
    for _ in range(5):game.step(Command(held_jump=True))
    game.step(Command(jump=True,held_jump=True))
    assert game.player.air_jumps==1 and game.player.vy<0
    game.step(Command(fire=True))
    assert any(not spark.enemy for spark in game.sparks)


def test_fire_shoot_requires_fire_form_and_has_cooldown():
    g=Game();grounded(g)
    g.step(Command(fire=True));assert not g.sparks
    g._change_form('fire','',0)
    g.step(Command(fire=True));assert len(g.sparks)==1
    g.step(Command(fire=True));assert len(g.sparks)==1


def test_100_coins_adds_life():
    g=Game();g.coins=99;g._coin(0,0)
    assert g.coins==0 and g.lives==4


def test_block_bonk_is_one_time_and_changes_reward():
    g=Game();block=next(b for b in g.blocks if b.fields.get('kind')=='Power')
    before=len(g.items)
    g.bonk(block)
    count=len(g.items)
    assert block.identifier in g.spent and count==before+1
    g.bonk(block)
    assert len(g.items)==count


def test_hidden_block_is_hit_from_below():
    g=Game('mary_o_1_2')
    hidden=next(b for b in g.blocks if b.fields.get('kind')=='Hidden')
    p=g.player
    p.x=hidden.x+4;p.y=hidden.bottom+3;p.vy=-400
    g._move(p,1/60)
    assert hidden.identifier in g.spent
    assert any(i.kind=='quasar' for i in g.items)


def test_world_one_pipe_transits_between_linked_mouths():
    g=Game('mary_o_1_1')
    entrance=next(pipe for pipe in g.pipes if pipe.fields.get('role')=='Entrance' and pipe.fields.get('mouth')=='Up')
    p=g.player;p.x=entrance.cx-p.w/2;p.y=entrance.y-p.h;p.grounded=True
    g.step(Command(down=True))
    assert g.pipe_state=='enter'
    for _ in range(70):g.step()
    assert g.room.name=='mary_o_1_1'
    assert g.pipe_state==''
    assert p.y>entrance.y


def test_secret_warp_pipe_loads_target_level():
    g=Game('mary_o_warp')
    entrance=next(p for p in g.pipes if p.fields.get('link')=='mary_o_2_2')
    p=g.player;p.x=entrance.cx-p.w/2;p.y=entrance.y-p.h;p.grounded=True
    g.step(Command(down=True))
    assert g.pipe_state=='enter'
    for _ in range(70):g.step()
    assert g.room.name=='mary_o_2_2'


def test_end_pole_starts_sequence_and_advances_room():
    g=Game('mary_o_1_1');pole=next(e for e in g.room.all('OneWayPlatform') if e.fields.get('name')=='goal_pole')
    p=g.player;p.x=pole.x-5;p.y=pole.y+8
    g.step()
    assert g.flag_state=='pole'
    for _ in range(265):g.step()
    assert g.room.name=='mary_o_1_2'


def test_castle_switch_activates_on_top_contact_and_destroys_bridge():
    g=Game('mary_o_1_4')
    sw=next(s for s in g.solids if s.fields.get('name')=='goal_switch')
    p=g.player;p.x=sw.x+6;p.y=sw.y-p.h;p.grounded=True
    g.step()
    assert g.flag_state=='castle' and g.switch_pressed
    for _ in range(275):g.step()
    planks=[b for b in g.blocks if b.fields.get('kind')=='Plank']
    assert planks and all(b.identifier in g.broken for b in planks)
    for _ in range(470):g.step()
    assert g.room.name=='mary_o_2_1'


def test_eight_room_progression_has_no_dead_end():
    rooms=levels();name='mary_o_1_1'
    visited=[]
    for _ in range(8):
        visited.append(name)
        name=rooms[name].next_room
    assert len(set(visited))==8 and name=='mary_o_1_1'
