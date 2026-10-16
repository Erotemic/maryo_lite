"""Source-driven SVG extraction does not depend on the Rust renderer."""
import sys
import xml.etree.ElementTree as ET

from mary_o_lite.content import ASSETS, ROOT
from mary_o_lite.poses import load_rig

sys.path.insert(0,str(ROOT/'tools'))
from build_assets import subset, DRAWABLE, local


def test_isolated_svg_still_has_usable_vector_data():
    source=(ASSETS/'svg'/'mary_o_v2.svg').read_bytes()
    part=load_rig('small')['parts'][0]
    fragment=subset(source,load_rig('small')['view'],part['include'])
    root=ET.fromstring(fragment)
    assert root.tag.endswith('svg')
    assert any(local(node.tag) in DRAWABLE for node in root.iter())
    assert len(fragment)>1000


def test_asset_generation_is_separate_from_runtime():
    assert not list((ROOT/'src').rglob('*.png'))
    assert not list((ROOT/'src').rglob('*.wav'))
