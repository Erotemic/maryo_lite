"""Verify the keyboard adapter without importing Pygame."""
from collections import defaultdict

from mary_o_lite.app import Keyboard


class FakePG:
    def __init__(self):
        keys=('LEFT','RIGHT','UP','DOWN','a','d','w','s','z','x','j','l',
              'SPACE','r','LSHIFT','RSHIFT')
        for key in keys:
            setattr(self,'K_'+key,key)
        self.pressed=defaultdict(bool)
        self.key=self

    def get_pressed(self):
        return self.pressed


def test_arrow_keys_z_jump_only_once_while_held():
    pg=FakePG();keys=Keyboard(pg)
    pg.pressed[pg.K_RIGHT]=True
    pg.pressed[pg.K_z]=True
    first=keys.command()
    assert first.move==1 and first.jump and first.held_jump
    second=keys.command()
    assert second.move==1 and not second.jump and second.held_jump
    pg.pressed[pg.K_z]=False
    keys.command()
    pg.pressed[pg.K_z]=True
    assert keys.command().jump


def test_down_is_held_for_continuous_crouch_and_pipes():
    pg=FakePG();keys=Keyboard(pg)
    pg.pressed[pg.K_DOWN]=True
    assert keys.command().down
    assert keys.command().down
    pg.pressed[pg.K_DOWN]=False
    assert not keys.command().down


def test_arrows_attack_and_cosmic_edges():
    pg=FakePG();keys=Keyboard(pg)
    pg.pressed[pg.K_x]=True
    pg.pressed[pg.K_d]=True
    cmd=keys.command()
    assert cmd.fire and cmd.utility
    assert not keys.command().fire and not keys.command().utility


def test_wasd_layout_and_walk_modifier():
    pg=FakePG();keys=Keyboard(pg,'wasd')
    for key in ('K_a','K_SPACE','K_j','K_l','K_LSHIFT'):
        pg.pressed[getattr(pg,key)]=True
    cmd=keys.command()
    assert cmd.move==-1 and cmd.jump and cmd.fire and cmd.utility and cmd.walk


def test_input_adapter_clear_does_not_leave_edges_stuck():
    pg=FakePG();keys=Keyboard(pg)
    pg.pressed[pg.K_z]=True
    assert keys.command().jump
    assert not keys.command().jump
    keys.clear()
    assert keys.command().jump
