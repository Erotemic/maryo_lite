"""Tests for the classic Mary-O velocity contract."""
import pytest
from mary_o_lite.physics import CLASSIC, COSMIC, horizontal, gravity_step, jump_velocity


@pytest.mark.parametrize('speed,expected', [(0,-420),(120,-435),(187.5,-450),(210,-480)])
def test_running_start_raises_jump(speed,expected):
    assert jump_velocity(speed,CLASSIC)==expected


def test_holding_jump_reduces_upward_gravity():
    fast=gravity_step(-350,True,CLASSIC,1/60)
    short=gravity_step(-350,False,CLASSIC,1/60)
    assert fast < short < 0


def test_air_momentum_is_preserved_with_no_steering():
    assert horizontal(100,0,False,False,CLASSIC,1/60) == 100
    assert horizontal(100,0,True,False,CLASSIC,1/60) < 100


def test_reverse_does_not_teleport_to_opposite_speed():
    assert 0<horizontal(120,-1,True,False,CLASSIC,1/60)<120


def test_walk_by_default_and_run_when_modifier_held():
    v=0
    for _ in range(180):v=horizontal(v,1,True,False,CLASSIC,1/60)
    assert v==pytest.approx(CLASSIC.max_run*.6)
    for _ in range(180):v=horizontal(v,1,True,True,CLASSIC,1/60)
    assert v==pytest.approx(CLASSIC.max_run)


def test_releasing_run_preserves_momentum_and_brakes_toward_walk():
    v=horizontal(300,1,True,False,CLASSIC,1/60)
    assert CLASSIC.max_run*.6<v<300


def test_shift_layer_caps_axis_before_mary_o_walk_run_policy():
    walk=0.0
    run=0.0
    for _ in range(180):
        walk=horizontal(walk,1,True,False,CLASSIC,1/60,precision=True)
        run=horizontal(run,1,True,True,CLASSIC,1/60,precision=True)
    assert walk==pytest.approx(90.0)  # .5 axis * .6 Mary-O throttle
    assert run==pytest.approx(150.0)  # .5 axis * full X-run throttle


def test_crouch_has_a_slow_target_but_retains_incoming_speed():
    v=horizontal(300,1,True,True,CLASSIC,1/60,crouch=True)
    assert 90<v<300
    for _ in range(180):v=horizontal(v,1,True,True,CLASSIC,1/60,crouch=True)
    assert v==pytest.approx(90.0)


def test_cosmic_faster_with_air_jumps():
    assert COSMIC.max_run>CLASSIC.max_run
    assert COSMIC.air_jumps>200
