"""Pygame shell. Launch from the repository root with `python main.py`."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .content import ASSETS, available_rooms
from .game import Command, Game, STEP


def parse_args(argv=None):
    p=argparse.ArgumentParser(description='Mary-O Lite: a source-driven Python platformer')
    p.add_argument('--room',default='mary_o_1_1',choices=available_rooms(),help='start at a Mary-O room')
    p.add_argument('--controls',choices=('arrows','wasd'),default='arrows')
    p.add_argument('--pose-lab',action='store_true',help='start in the animation inspector')
    p.add_argument('--mute',action='store_true')
    p.add_argument('--size',default='1280x720',help='window size, e.g. 1280x720')
    p.add_argument('--headless',action='store_true',help='run physics without opening a window or installing Pygame')
    p.add_argument('--ticks',type=int,default=600,help='headless simulation steps')
    p.add_argument('--list-levels',action='store_true')
    p.add_argument('--build-assets',action='store_true',help='rebuild source-driven cache and exit')
    return p.parse_args(argv)


class Music:
    def __init__(self,pygame,disabled):
        self.pg=pygame
        self.active=''
        self.sounds={}
        self.ready=False
        if disabled:return
        try:
            pygame.mixer.init(frequency=22050,size=-16,channels=1)
            pygame.mixer.set_num_channels(12)
            directory=ASSETS/'generated'/'audio'
            self.sounds={f.stem:pygame.mixer.Sound(str(f)) for f in directory.glob('*.wav')
                         if f.stem not in ('starlight','starless','stardune','void_castle','cosmic')}
            self.ready=True
        except pygame.error:
            print('Audio device unavailable: running without sound.',file=sys.stderr)

    def update(self,game):
        if not self.ready:return
        name='cosmic' if game.player.cosmic else game.room.biome
        if name==self.active:return
        self.active=name
        music=ASSETS/'generated'/'audio'/(name+'.wav')
        if music.exists():
            self.pg.mixer.music.load(str(music))
            self.pg.mixer.music.set_volume(.47)
            self.pg.mixer.music.play(-1)

    def effects(self,events):
        if not self.ready:return
        for event in events:
            sound=self.sounds.get(event.kind)
            if sound:sound.play()


class Keyboard:
    """An edge-triggered input adapter; no key repeats or sticky actions."""
    def __init__(self,pygame,preset='arrows'):
        self.pg=pygame
        self.preset=preset
        self.prev=set()

    def command(self):
        k=self.pg.key.get_pressed()
        pg=self.pg
        if self.preset=='wasd':
            left,right,up,down,jump,fire=(pg.K_a,pg.K_d,pg.K_w,pg.K_s,pg.K_SPACE,pg.K_j)
            cosmic=pg.K_l
        else:
            left,right,up,down,jump,fire=(pg.K_LEFT,pg.K_RIGHT,pg.K_UP,pg.K_DOWN,pg.K_z,pg.K_x)
            cosmic=pg.K_d
        buttons={'jump':jump,'fire':fire,'cosmic':cosmic,'up':up,'down':down,'restart':pg.K_r}
        held={name for name,key in buttons.items() if k[key]}
        edges=held-self.prev
        self.prev=held
        direction=int(bool(k[right]))-int(bool(k[left]))
        return Command(move=direction,jump='jump' in edges,held_jump='jump' in held,
                       fire='fire' in edges,utility='cosmic' in edges,
                       up='up' in held,down='down' in held,
                       walk=bool(k[pg.K_LSHIFT] or k[pg.K_RSHIFT]),restart='restart' in edges)

    def clear(self):self.prev.clear()


def parse_size(s):
    try:
        a,b=map(int,s.lower().split('x'))
        if min(a,b)<320 or max(a,b)>7680:raise ValueError
        return a,b
    except ValueError as ex:
        raise ValueError(f'Expected --size WIDTHxHEIGHT, got {s!r}') from ex


def run_pygame(args):
    try:
        import pygame
    except ImportError:
        print('Install pygame-ce (or run python main.py to auto-install).',file=sys.stderr)
        return 1
    from .graphics import LOGICAL_SIZE, Painter
    pygame.init()
    screen=pygame.display.set_mode(parse_size(args.size),pygame.RESIZABLE)
    pygame.display.set_caption('Mary-O Lite | Arrow keys + Z/X/D')
    from .content import ROOT
    sys.path.insert(0,str(ROOT/'tools'))
    from build_assets import ensure_assets
    ensure_assets()
    # Convert-alpha surfaces need a display, so the first Painter comes after set_mode.
    painter=Painter()
    painter.pose_lab=args.pose_lab
    game=Game(args.room)
    keys=Keyboard(pygame,args.controls)
    sounds=Music(pygame,args.mute)
    clock=pygame.time.Clock()
    running=True
    paused=False
    accumulator=0.0
    last_time=0.0
    while running:
        dt=min(.05,clock.tick(60)/1000)
        for e in pygame.event.get():
            if e.type==pygame.QUIT:
                running=False
            elif e.type==pygame.KEYDOWN:
                if e.key==pygame.K_F1:painter.help=not painter.help
                elif e.key==pygame.K_F2:
                    painter.pose_lab=not painter.pose_lab
                    keys.clear();accumulator=0
                elif e.key==pygame.K_F3:painter.debug=not painter.debug
                elif e.key==pygame.K_ESCAPE:paused=not paused
                elif painter.pose_lab:
                    forms=['small','tall','fire','cosmic']
                    if e.key in (pygame.K_UP,pygame.K_DOWN):
                        index=forms.index(painter.lab_form)
                        painter.lab_form=forms[(index+(-1 if e.key==pygame.K_UP else 1))%len(forms)]
                        painter.lab_clip='idle';painter.lab_time=0
                    elif e.key in (pygame.K_LEFT,pygame.K_RIGHT):
                        names=painter.lab_clips()
                        try:index=names.index(painter.lab_clip)
                        except ValueError:index=0
                        painter.lab_clip=names[(index+(-1 if e.key==pygame.K_LEFT else 1))%len(names)]
                        painter.lab_time=0
                    elif e.key==pygame.K_TAB:
                        painter.lab_selected+=1
                    elif e.key in (pygame.K_LEFTBRACKET,pygame.K_RIGHTBRACKET):
                        bones=painter.lab_bones()
                        bone=bones[painter.lab_selected%len(bones)]
                        painter.lab_angle[bone]=painter.lab_angle.get(bone,0)+(5 if e.key==pygame.K_RIGHTBRACKET else -5)
                    elif e.key==pygame.K_BACKSPACE:
                        painter.lab_angle.clear()
                    elif e.key==pygame.K_SPACE:painter.lab_play=not painter.lab_play
                    elif e.key==pygame.K_r:painter.lab_time=0
                elif e.key==pygame.K_F5:
                    game.load_room(game.room.next_room)
        if not painter.pose_lab and not paused:
            accumulator+=dt
            while accumulator>=STEP:
                cmd=keys.command()
                game.step(cmd)
                sounds.effects(game.events)
                accumulator-=STEP
        sounds.update(game)
        if painter.pose_lab:
            scene=painter.lab_frame(dt)
        else:
            scene=painter.frame(game,dt)
        if paused:
            shade=pygame.Surface(LOGICAL_SIZE,pygame.SRCALPHA)
            shade.fill((10,14,29,150))
            scene.blit(shade,(0,0))
            painter.letter('PAUSED',(LOGICAL_SIZE[0]/2,LOGICAL_SIZE[1]/2),
                           (255,218,129),big=True,center=True)
        if screen.get_size()==LOGICAL_SIZE:
            screen.blit(scene,(0,0))
        else:
            # Nearest neighbour keeps hand-drawn pixels and vector-part outlines sharp.
            image=pygame.transform.scale(scene,screen.get_size())
            screen.blit(image,(0,0))
        pygame.display.flip()
    pygame.quit()
    return 0


def main(argv=None):
    args=parse_args(argv)
    if args.list_levels:
        print('\n'.join(available_rooms()))
        return 0
    if args.headless:
        game=Game(args.room)
        for t in range(args.ticks):
            game.step(Command(move=1,jump=(t%105==1),held_jump=(t%105)<19))
        print(json.dumps(game.summary(),indent=2,sort_keys=True))
        return 0
    if args.build_assets:
        from .content import ROOT
        sys.path.insert(0,str(ROOT/'tools'))
        from build_assets import ensure_assets
        ensure_assets()
        return 0
    return run_pygame(args)


if __name__=='__main__':
    raise SystemExit(main())
