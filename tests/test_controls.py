"""Verify the keyboard adapter without importing Pygame."""
from collections import defaultdict

from mary_o_lite.app import Keyboard


class FakePG:
    def __init__(self):
        keys=('LEFT','RIGHT','UP','DOWN','a','d','w','s','z','x','j','l',
              'u','p','e','g','k','q',
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


def test_arrows_x_held_runs_and_pressed_sparks_plus_d_cosmic():
    pg=FakePG();keys=Keyboard(pg)
    pg.pressed[pg.K_x]=True
    pg.pressed[pg.K_d]=True
    cmd=keys.command()
    assert cmd.run and cmd.run_pressed and cmd.utility and not cmd.fire
    again=keys.command()
    assert again.run and not again.run_pressed and not again.utility
    pg.pressed[pg.K_x]=False
    assert not keys.command().run
    pg.pressed[pg.K_x]=True
    assert keys.command().run_pressed


def test_wasd_j_is_run_spark_and_shift_is_only_precision():
    pg=FakePG();keys=Keyboard(pg,'wasd')
    for key in ('K_a','K_SPACE','K_j','K_u','K_LSHIFT'):
        pg.pressed[getattr(pg,key)]=True
    cmd=keys.command()
    assert cmd.move==-1 and cmd.jump and cmd.utility and not cmd.fire
    assert cmd.run and cmd.run_pressed and cmd.precision
    assert keys.command().run and not keys.command().run_pressed
    pg.pressed[pg.K_j]=False
    assert not keys.command().run
    assert keys.command().precision


def test_both_other_rust_presets_map_their_real_modifier_and_utility():
    pg=FakePG()
    for preset,jump,modifier,utility in (
        ('arrows-qwer','q','e','g'), ('wasd-uipo','u','p','k'),
    ):
        keys=Keyboard(pg,preset)
        pg.pressed[getattr(pg,'K_'+jump)]=True
        pg.pressed[getattr(pg,'K_'+modifier)]=True
        pg.pressed[getattr(pg,'K_'+utility)]=True
        cmd=keys.command()
        assert cmd.jump and cmd.run and cmd.run_pressed and cmd.utility
        pg.pressed.clear()


def test_shift_does_not_run_by_itself():
    pg=FakePG(); keys=Keyboard(pg)
    pg.pressed[pg.K_LSHIFT]=True
    cmd=keys.command()
    assert not cmd.run and not cmd.run_pressed and cmd.precision


def test_keydown_queue_preserves_tap_between_simulation_steps():
    pg=FakePG(); keys=Keyboard(pg)
    keys.note_keydown(pg.K_z)
    keys.note_keydown(pg.K_x)
    # Both presses were released before the next physics step.
    cmd=keys.command()
    assert cmd.jump and cmd.run_pressed and not cmd.run
    assert not keys.command().jump and not keys.command().run_pressed
    keys.note_keydown(pg.K_x,repeat=True)
    assert not keys.command().run_pressed


def test_queued_edges_are_cleared_when_leaving_pose_lab_or_pausing():
    pg=FakePG();keys=Keyboard(pg)
    keys.note_keydown(pg.K_x)
    keys.clear()
    assert not keys.command().run_pressed


def test_resuming_with_x_held_does_not_fire_accidental_spark():
    pg=FakePG();keys=Keyboard(pg)
    pg.pressed[pg.K_x]=True
    keys.clear(absorb_held=True)
    cmd=keys.command()
    assert cmd.run and not cmd.run_pressed
    pg.pressed[pg.K_x]=False
    keys.command()
    pg.pressed[pg.K_x]=True
    assert keys.command().run_pressed


def test_input_adapter_clear_does_not_leave_edges_stuck():
    pg=FakePG();keys=Keyboard(pg)
    pg.pressed[pg.K_z]=True
    assert keys.command().jump
    assert not keys.command().jump
    keys.clear()
    assert keys.command().jump
