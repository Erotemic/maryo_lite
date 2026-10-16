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


def test_walk_modifier_lowers_top_speed():
    v=0
    for _ in range(180):v=horizontal(v,1,True,True,CLASSIC,1/60)
    assert v==pytest.approx(CLASSIC.max_run*.6)


def test_cosmic_faster_with_air_jumps():
    assert COSMIC.max_run>CLASSIC.max_run
    assert COSMIC.air_jumps>200
