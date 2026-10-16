#!/usr/bin/env python3
"""Build an offline QA contact sheet of the actual source-generated assets.

No Pygame/display or source PNGs in Git. Helps students inspect anchors,
pipe clipping, Fire Bar orbital paths, and the two airborne enemy families.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
from mary_o_lite.content import levels
from mary_o_lite.motion import plant_placement, parse_polyline, loop_position
from ambition_art.build import generate

ART = ROOT / 'assets/generated/ambition'
WHITE = '#f5ede4'


def sprite(family, kind, row, index):
    return Image.open(ART / family / kind / row / f'{index:03d}.png').convert('RGBA')


def put(canvas, sprite, x, y, size=None):
    if size:
        sprite = sprite.resize(tuple(map(round,size)), Image.Resampling.LANCZOS)
    canvas.alpha_composite(sprite, (round(x),round(y)))


def snake_scene(exposure):
    scene = Image.new('RGBA',(235,216),'#242d48')
    d = ImageDraw.Draw(scene)
    d.text((14,12),f'Snake Plant  {exposure:.0%}', fill=WHITE)
    center, mouth, height = 119, 133, 46
    d.rectangle((0,mouth+69,235,216), fill='#6f5346')
    plant = sprite('enemies','snake_plant','idle',3)
    placement = plant_placement(*plant.size, 21, 48,127,center,mouth,exposure,height)
    x,y,w,h = placement
    plant=plant.resize((round(w),round(h)),Image.Resampling.LANCZOS)
    # Actual runtime's above-mouth clip (pipe foreground also covers the rest).
    if exposure >= .12:
        clip=Image.new('RGBA',scene.size,(0,0,0,0))
        put(clip,plant,x,y)
        clip=clip.crop((0,0,scene.width,mouth))
        scene.alpha_composite(clip,(0,0))
    for j in range(4):
        y=mouth+j*16
        key='super_mary_o_pipe_top' if j==0 else 'super_mary_o_pipe_body'
        put(scene,sprite('construction',key,'idle',0),center-48,y,(96,16))
    return scene


def fire_scene(t):
    scene=Image.new('RGBA',(260,216),'#28223f')
    d=ImageDraw.Draw(scene)
    d.text((10,12),f'Fire Bar  t={t:.1f}s', fill=WHITE)
    hazards=[h for h in levels()['mary_o_1_4'].all('DamageVolume')
             if h.fields.get('path_points')][:5]
    start=(hazards[0].x+hazards[0].w/2,hazards[0].y+hazards[0].h/2)
    cx,cy=117,119
    # Each path is centered on the same pivot. The first point is radius 16.
    pivot=(start[0]-16,start[1])
    put(scene,Image.open(ART/'tiles/ground_fill.png').convert('RGBA'),cx-8,cy-8,(16,16))
    for h in hazards:
        wx,wy=loop_position(parse_polyline(h.fields['path_points']),
                            float(h.fields['path_speed']),t)
        orb=sprite('construction','fire_orb','idle',int(t*12)%8)
        put(scene,orb,cx+(wx-pivot[0])-15,cy+(wy-pivot[1])-15,(30,30))
    return scene


def plane_scene(kind,title):
    scene=Image.new('RGBA',(420,216),'#26364a')
    d=ImageDraw.Draw(scene)
    d.text((10,12),title,fill=WHITE)
    for i in range(3):
        art=sprite('enemies',kind,'fly',i*2)
        put(scene,art,i*130+5,48,(140,112))
    return scene


def build(path: Path):
    generate()
    sheet=Image.new('RGB',(1410,475),'#151c32')
    x=0
    for pct in (0,.25,.5,.75,1):
        shot=snake_scene(pct)
        sheet.paste(shot,(x,0),shot)
        x+=235
    shot=fire_scene(.0);sheet.paste(shot,(1170,0),shot)
    for i, t in enumerate((.5,1.0,1.5,2.0,2.5)):
        shot=fire_scene(t)
        sheet.paste(shot,(i*260,240),shot)
    # A separate small sheet keeps the source animations identifiable.
    path.parent.mkdir(parents=True,exist_ok=True)
    sheet.save(path)
    planes=Image.new('RGB',(850,225),'#151c32')
    for i,(key,title) in enumerate((
            ('npc_snakes_on_a_paper_plane','Snakes on a Paper Plane'),
            ('npc_snakes_on_a_cartesian_plane','Snakes on a Cartesian Plane'))):
        art=plane_scene(key,title);planes.paste(art,(i*425,0),art)
    planes.save(path.with_name(path.stem+'_planes.png'))
    return path


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'assets/generated/maryo_fidelity_preview.png')
    args=parser.parse_args()
    print(build(args.out))
