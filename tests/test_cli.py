"""Entry points work on a machine where Pygame is not installed."""
from pathlib import Path
import json
import subprocess
import sys

from mary_o_lite.content import ROOT
from mary_o_lite.app import parse_args, parse_size


def script(*args):
    return subprocess.run([sys.executable,str(ROOT/'main.py'),*args],
                          text=True,capture_output=True,check=True)


def test_main_help_is_stdlib_only():
    assert '--headless' in script('--help').stdout
    assert 'pose-lab' in script('--help').stdout


def test_main_headless_launches_without_binary_art():
    data=json.loads(script('--headless','--ticks','15','--room','mary_o_2_3').stdout)
    assert data['room']=='mary_o_2_3'
    assert data['tick']==15


def test_main_can_list_rooms():
    lines=script('--list-levels').stdout.strip().splitlines()
    assert len(lines)==9 and 'mary_o_warp' in lines


def test_window_size_parse():
    assert parse_size('960x540') == (960,540)
    try:parse_size('4x3')
    except ValueError:pass
    else:raise AssertionError('Tiny window accepted')


def test_gitignore_excludes_every_generated_binary():
    gitignore=(ROOT/'.gitignore').read_text()
    assert 'assets/generated/' in gitignore
    for glob in ('*.png','*.wav','*.ogg','*.jpg','*.mp3','*.ttf'):
        assert glob in gitignore
    assert (ROOT/'assets'/'svg'/'mary_o_v2.svg').exists()
    assert (ROOT/'assets'/'svg'/'player-robot-v3.svg').exists()


def test_generated_art_comes_from_source_svg_and_python():
    code=(ROOT/'tools'/'build_assets.py').read_text()
    assert 'svg2png' in code
    assert 'manifest.json' in code
    assert 'generate_audio' in code
