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

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
GENERATED = ASSETS / 'generated'
SVG_NS='http://www.w3.org/2000/svg'
INK_NS='http://www.inkscape.org/namespaces/inkscape'
XLINK_NS='http://www.w3.org/1999/xlink'
DRAWABLE={'path','polygon','polyline','rect','ellipse','circle','line','image','use','text'}
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


def generate_art(force=False):
    import cairosvg
    from PIL import Image
    source=ASSETS/'svg'/'mary_o_v2.svg'
    svg_bytes=source.read_bytes()
    count=0
    for rig_file in sorted((ASSETS/'rigs').glob('*.json')):
        raw=rig_file.read_bytes()
        rig=json.loads(raw)
        folder=GENERATED/'parts'/rig_file.stem
        stamp=hashlib.sha256(svg_bytes+raw+Path(__file__).read_bytes()).hexdigest()
        marker=folder/'manifest.json'
        if not force and marker.is_file():
            try:
                cached=json.loads(marker.read_text())
                if cached['stamp']==stamp and all((folder/(p['name']+'.png')).exists() for p in rig['parts']):
                    continue
            except (OSError,KeyError,ValueError):pass
        folder.mkdir(parents=True,exist_ok=True)
        metadata={}
        for part in rig['parts']:
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
        marker.write_text(json.dumps({'stamp':stamp,'pivots':metadata},indent=2)+'\n')
    # Castle rescue NPC; retain editable vector, generate its thumbnail here.
    robot=ASSETS/'svg'/'player-robot-v3.svg'
    if robot.exists():
        dst=GENERATED/'robot'/'castle_robot.png'
        marker=dst.parent/'manifest.json'
        signature=hashlib.sha256(robot.read_bytes()+Path(__file__).read_bytes()).hexdigest()
        if force or not dst.exists() or not marker.exists() or json.loads(marker.read_text()).get('stamp')!=signature:
            dst.parent.mkdir(parents=True,exist_ok=True)
            raw=cairosvg.svg2png(bytestring=robot.read_bytes(),output_width=64,output_height=90)
            image=Image.open(io.BytesIO(raw)).convert('RGBA')
            image=image.crop(image.getbbox())
            image.thumbnail((42,57),Image.Resampling.LANCZOS)
            image.save(dst,optimize=True)
            marker.write_text(json.dumps({'stamp':signature,'source':str(robot.relative_to(ROOT))})+'\n')
            count+=1
    print(f'Generated {count} Mary-O SVG part images (cached).')
    # Original Ambition source painters: 89 Cosmic frames plus reusable tiles,
    # animated pickups, enemies, and source SVG birds. Never check in PNGs.
    sys.path.insert(0,str(ROOT/'tools'))
    from ambition_art.build import generate as generate_source_art
    rebuilt=generate_source_art(force=force)
    print('Generated Ambition-painted Mary-O art.' if rebuilt else
          'Ambition-painted Mary-O art already cached.')



def generate_audio(force=False):
    sys.path.insert(0,str(ROOT/'tools'))
    from compose_audio import build_audio
    build_audio(GENERATED/'audio',force=force)


def ensure_assets():
    generate_art()
    generate_audio()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--art-only',action='store_true')
    parser.add_argument('--audio-only',action='store_true')
    parser.add_argument('--force',action='store_true')
    args=parser.parse_args()
    if not args.audio_only:generate_art(args.force)
    if not args.art_only:generate_audio(args.force)


if __name__=='__main__':main()
