#!/usr/bin/env python3
"""Rasterize the tracked SVG paper doll and compose original chiptune WAVs.

Generated PNG, WAV and manifests live only in assets/generated (Git-ignored).
Requires Pillow and CairoSVG; does not require Pygame or Ambition.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from asset_progress import AssetProgress

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
GENERATED = ASSETS / 'generated'
SVG_NS='http://www.w3.org/2000/svg'
INK_NS='http://www.inkscape.org/namespaces/inkscape'
XLINK_NS='http://www.w3.org/1999/xlink'
DRAWABLE={'path','polygon','polyline','rect','ellipse','circle','line','image','use','text'}
# The fidelity release included this orchestration script in the SVG cache
# fingerprint. Keep its existing generated images on this progress-only upgrade
# when the underlying SVG and rig JSON have not changed. Future stamps depend
# only on the source artwork, not on progress/reporting code.
_LEGACY_RIGS = {
    'fire_front': ('3d75a23a216a4f3965ecb2221cb3e16e9100cd05f540791a524084af483ff389', '65cd5b4893be6e418b10939c172931558194af460691e388191b42ec5f93d363'),
    'fire_side': ('b6ff8da221eba9edbfbe409279198c9514d06aaaf910e07f38b97493e94523bd', '1563b6dd756dfec0d46de1175f271db88f7b190bbcaedbd6632bf1653853ea3c'),
    'small_front': ('706315320d41d1e6c94e4828590f764f825c232728a5340dacef3ad3ac86a988', '0c9c27c2caeed3c40a6e7e92fc289827b9e77406d852229a295737c501f5ab39'),
    'small_side': ('d9aafc7bd354050f156bbdd6bb050fee7ec4f954df48b733b6ae32470643a847', '87222b6bf1c813a284b7c0c0c2ed891a9cdc81db08fe5715e54646c2bb263e34'),
    'tall_front': ('4480712a71082714d5519d5e6b8d23cf1d303bdd15792cae26ecec3c4f86922e', '47608366eae254b070743ce82820bca58197d808fb2f6e83a8c61e9d0207d157'),
    'tall_side': ('7a32cbc3f2248a22dc12de8fac7ef95ad2654150fc60e2e7784bb2e8458fc4b8', '9b127131b51784279965274b89a0a004c7e0e0434a956c687c5a9049678b5f8c'),
}
_LEGACY_ROBOT = ('08316d97b6ecb7dfbe73f4a1776f12ad3c3bdb828a00aacbf37c0ee6585b7d00',
                 '27ecc71a4ddff7d029b958ed271866df5cebaf59597b44f3c335ac481478abf6')


def _stamp_matches(saved: str, current: str, legacy: tuple[str, str] | None) -> bool:
    return saved == current or (legacy is not None and
                                saved == legacy[0] and current == legacy[1])


for prefix, uri in (('',SVG_NS),('inkscape',INK_NS),('xlink',XLINK_NS)):
    ET.register_namespace(prefix,uri)


def local(tag):
    return tag.rsplit('}',1)[-1]


def subset(source: bytes, view: str, includes: list[str]):
    """Isolate an SVG part while retaining Inkscape ancestors and gradients.

    Linked <use> targets are cloned into defs. They may be defined in a
    different view, which is hidden when this part is rasterized.
    """
    root=ET.fromstring(source)
    by_id={n.get('id'):n for n in root.iter() if n.get('id')}
    parent={child:p for p in root.iter() for child in p}
    kept:set[ET.Element]=set()
    kept_uses=[]
    for key in includes:
        if key not in by_id:raise ValueError(f'SVG id {key!r} not found')
        n=by_id[key]
        while True:
            kept.add(n)
            if n not in parent:break
            n=parent[n]
        target=by_id[key]
        for n in target.iter():
            kept.add(n)
            if local(n.tag)=='use':kept_uses.append(n)
    defs=next((n for n in root if local(n.tag)=='defs'),None)
    if defs is None:
        defs=ET.Element(f'{{{SVG_NS}}}defs');root.insert(0,defs)
    copies={}
    def clone(key):
        if key in copies:return copies[key]
        node=by_id.get(key)
        if node is None:return key
        renamed=f'isolated_{len(copies)}_{key}'
        copies[key]=renamed
        duplicate=copy.deepcopy(node)
        duplicate.set('id',renamed)
        for child in duplicate.iter():
            if child is not duplicate:child.attrib.pop('id',None)
            if local(child.tag)=='use':
                href=child.get('href') or child.get(f'{{{XLINK_NS}}}href') or ''
                if href.startswith('#'):
                    ref=clone(href[1:]);child.set('href','#'+ref);child.set(f'{{{XLINK_NS}}}href','#'+ref)
        defs.append(duplicate)
        kept.update(duplicate.iter())
        kept.add(defs)
        return renamed
    for node in kept_uses:
        href=node.get('href') or node.get(f'{{{XLINK_NS}}}href') or ''
        if href.startswith('#'):
            ref=clone(href[1:]);node.set('href','#'+ref);node.set(f'{{{XLINK_NS}}}href','#'+ref)
    # The selected expression may be marked as editor-only in the master SVG.
    for node in root.iter():
        if node in kept and node.get('data-rig-editor-visibility')=='editor-only':
            node.set('style',';'.join(s for s in node.get('style','').split(';')
                                      if s.strip().split(':')[0].strip()!='display'))
    for layer in root:
        label=layer.get(f'{{{INK_NS}}}label')
        if label and label!=view and not any(n in kept for n in layer.iter()):
            layer.set('style',layer.get('style','')+';display:none')
    for node in root.iter():
        if local(node.tag) in DRAWABLE and node not in kept:
            node.set('style',node.get('style','')+';display:none')
    return ET.tostring(root,encoding='utf8')


def generate_art(force=False, progress: AssetProgress | None = None):
    import cairosvg
    from PIL import Image
    source=ASSETS/'svg'/'mary_o_v2.svg'
    svg_bytes=source.read_bytes()
    count=0
    for rig_file in sorted((ASSETS/'rigs').glob('*.json')):
        if progress is not None:
            progress.stage(f'SVG puppet: {rig_file.stem}')
        raw=rig_file.read_bytes()
        rig=json.loads(raw)
        folder=GENERATED/'parts'/rig_file.stem
        stamp=hashlib.sha256(svg_bytes+raw).hexdigest()
        marker=folder/'manifest.json'
        if not force and marker.is_file():
            try:
                cached=json.loads(marker.read_text())
                if (_stamp_matches(cached['stamp'], stamp, _LEGACY_RIGS.get(rig_file.stem))
                    and all((folder/(p['name']+'.png')).exists() for p in rig['parts'])):
                    if cached['stamp'] != stamp:
                        cached['stamp'] = stamp
                        marker.write_text(json.dumps(cached, indent=2) + '\n')
                    if progress is not None:
                        progress.advance(len(rig['parts']),cached=True,item='rig already cached')
                    continue
            except (OSError,KeyError,ValueError):pass
        folder.mkdir(parents=True,exist_ok=True)
        metadata={}
        for part in rig['parts']:
            if progress is not None:
                progress.working(part['name'])
            fragment=subset(svg_bytes,rig['view'],part['include'])
            png=cairosvg.svg2png(bytestring=fragment,dpi=25.4)
            image=Image.open(io.BytesIO(png)).convert('RGBA')
            bbox=image.getbbox()
            if bbox is None:
                raise ValueError(f'Empty SVG part: {rig_file.stem}/{part["name"]}')
            cropped=image.crop(bbox)
            cropped.save(folder/(part['name']+'.png'),optimize=True)
            px,py=part['pivot']
            metadata[part['name']]=[round(px-bbox[0],4),round(py-bbox[1],4)]
            count+=1
            if progress is not None:
                progress.advance(item=part['name'])
        marker.write_text(json.dumps({'stamp':stamp,'pivots':metadata},indent=2)+'\n')
    # Castle rescue NPC; retain editable vector, generate its thumbnail here.
    robot=ASSETS/'svg'/'player-robot-v3.svg'
    if robot.exists():
        if progress is not None:
            progress.stage('Castle rescue robot')
        dst=GENERATED/'robot'/'castle_robot.png'
        marker=dst.parent/'manifest.json'
        signature=hashlib.sha256(robot.read_bytes()).hexdigest()
        try:
            robot_cached = (not force and dst.exists() and marker.exists() and
                            _stamp_matches(json.loads(marker.read_text()).get('stamp'),
                                           signature, _LEGACY_ROBOT))
        except (OSError, ValueError, KeyError):
            robot_cached = False
        if robot_cached:
            old_marker = json.loads(marker.read_text())
            if old_marker['stamp'] != signature:
                old_marker['stamp'] = signature
                marker.write_text(json.dumps(old_marker, indent=2) + '\n')
        if progress is not None:
            progress.working('robot SVG rasterization')
        if not robot_cached:
            dst.parent.mkdir(parents=True,exist_ok=True)
            raw=cairosvg.svg2png(bytestring=robot.read_bytes(),output_width=64,output_height=90)
            image=Image.open(io.BytesIO(raw)).convert('RGBA')
            image=image.crop(image.getbbox())
            image.thumbnail((42,57),Image.Resampling.LANCZOS)
            image.save(dst,optimize=True)
            marker.write_text(json.dumps({'stamp':signature,'source':str(robot.relative_to(ROOT))})+'\n')
            count+=1
        if progress is not None:
            progress.advance(cached=robot_cached, item='castle robot')
    if progress is None:
        print(f'Generated {count} Mary-O SVG part images (cached).')
    # Original Ambition source painters: 89 Cosmic frames plus reusable tiles,
    # animated pickups, enemies, and source SVG birds. Never check in PNGs.
    sys.path.insert(0,str(ROOT/'tools'))
    from ambition_art.build import generate as generate_source_art
    rebuilt=generate_source_art(force=force, progress=progress)
    if progress is None:
        print('Generated Ambition-painted Mary-O art.' if rebuilt else
              'Ambition-painted Mary-O art already cached.')



def generate_audio(force=False, progress: AssetProgress | None = None):
    sys.path.insert(0,str(ROOT/'tools'))
    from compose_audio import build_audio
    build_audio(GENERATED/'audio', force=force, progress=progress)


def planned_assets(*, art=True, audio=True) -> int:
    """Exactly count the generated files so the displayed percent is useful."""
    count = 0
    if art:
        count += sum(len(json.loads(p.read_text())['parts'])
                     for p in sorted((ASSETS/'rigs').glob('*.json')))
        count += int((ASSETS/'svg'/'player-robot-v3.svg').exists())
        sys.path.insert(0, str(ROOT/'tools'))
        from ambition_art.build import total_frames
        count += total_frames()
    if audio:
        sys.path.insert(0, str(ROOT/'tools'))
        from compose_audio import SOUNDS, TRACKS
        count += len(TRACKS) + len(SOUNDS)
    return count


def ensure_assets(force=False, *, art=True, audio=True):
    """Build with live console progress (also used by ``python main.py``)."""
    with AssetProgress(planned_assets(art=art, audio=audio)) as progress:
        if art:
            generate_art(force=force, progress=progress)
        if audio:
            generate_audio(force=force, progress=progress)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--art-only',action='store_true')
    parser.add_argument('--audio-only',action='store_true')
    parser.add_argument('--force',action='store_true')
    args=parser.parse_args()
    if args.art_only and args.audio_only:
        parser.error('--art-only and --audio-only are mutually exclusive')
    ensure_assets(force=args.force, art=not args.audio_only, audio=not args.art_only)


if __name__=='__main__':main()
