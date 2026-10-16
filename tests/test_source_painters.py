"""Regenerate source art without importing Ambition's engine or Pygame."""
from pathlib import Path
import sys

from PIL import Image

from mary_o_lite.content import ROOT

sys.path.insert(0,str(ROOT/'tools'))
from ambition_art import cosmic_art, cosmic_animation, tiles, construction, spark, lift
from ambition_art.build import _frames, _stamp


def test_real_cosmic_rows_and_hand_authored_transformation_sequences():
    rows = {name: (count,delay) for name,count,delay in cosmic_animation.ROWS}
    assert rows['transform'] == (36,95)
    assert rows['shrink'] == (18,95)
    assert len(cosmic_animation.transformation()) == 36
    assert len(cosmic_animation.detransformation()) == 18
    for clip in ('idle','walk','jump','crouch','climb','swim','shoot'):
        assert clip in rows
    stage = cosmic_animation.STAGE
    images = [cosmic_art.frame(stage, look) for look in
              (cosmic_animation.look_for('idle',0),
               cosmic_animation.transformation()[5],
               cosmic_animation.detransformation()[5])]
    assert len({image.tobytes() for image in images}) == 3
    assert all(image.mode == 'RGBA' and image.getbbox() for image in images)


def test_original_maryo_tile_source_is_reproducible():
    names = {t.key for t in tiles.TILES}
    assert {'ground_top','block_spent','pipe_cap_left','pipe_body_right'} <= names
    tile = tiles._tile_image('ground_top')
    assert tile.size == (16,16)
    assert tile.getbbox()


def test_source_construction_and_projectile_painters_are_available():
    for name in ('super_mary_o_flag','super_mary_o_pipe_top',
                 'super_mary_o_lava_top','super_mary_o_switch',
                 'super_mary_o_gate'):
        spec = construction.SPECS[name]
        row, count, _delay = spec.rows[0]
        image = spec.renderer(row,0,count)
        assert image.mode == 'RGBA' and image.getbbox()
    assert lift._lift_frame('idle',0,4).getbbox()
    assert spark._spark_frame('idle',0,6).getbbox()


def test_source_png_cache_is_atomic_and_recovers_from_truncation(tmp_path):
    target = tmp_path/'sample'
    calls = []
    def render(name,index,count):
        calls.append(index)
        return Image.new('RGBA',(16,16),(120,30+index,40,255))
    rows = [('idle',3,100)]
    first = _frames(rows,render,target)
    assert calls == [0,1,2]
    assert first['idle']['count'] == 3
    calls.clear()
    assert _frames(rows,render,target) == first
    assert not calls
    (target/'idle/001.png').write_bytes(b'corrupted partial image')
    _frames(rows,render,target)
    assert calls == [1]
    assert Image.open(target/'idle/001.png').getpixel((0,0))[1] == 31
    assert not list(tmp_path.rglob('*.tmp'))


def test_generator_sources_and_gitignore_prevent_binary_checkins():
    assert len(_stamp()) == 64
    ignore = (ROOT/'.gitignore').read_text()
    for pattern in ('assets/generated/', '*.png', '*.wav'):
        assert pattern in ignore
    assert (ROOT/'tools/ambition_art/cosmic_art.py').is_file()
    assert (ROOT/'assets/svg/european_swallow.svg').is_file()
    assert (ROOT/'assets/svg/african_swallow.svg').is_file()
