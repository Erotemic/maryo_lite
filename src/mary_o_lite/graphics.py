"""The Pygame view. The world does not know how it is drawn.

Mary-O is NOT a flattened animation strip. Each tick blends the exported
bone poses and transforms independently generated SVG-part rasters.
"""
from __future__ import annotations

from functools import lru_cache
import json
import math
from pathlib import Path

import pygame

from .content import ASSETS, TILE
from .geometry import clamp
from .poses import sample_pose

LOGICAL_SIZE=(960,540)
THEMES={
 'starlight':((20,31,65),(49,74,105),(42,65,81),(55,86,85),(93,126,95),(94,80,124)),
 'starless':((13,19,34),(22,28,46),(29,39,54),(35,44,54),(68,68,77),(71,75,91)),
 'stardune':((56,56,91),(102,88,117),(93,78,108),(161,114,108),(204,145,99),(169,117,107)),
 'void_castle':((29,14,39),(57,24,61),(44,25,62),(66,36,77),(112,47,72),(96,56,83)),
}
WHITE=(252,239,217)
INK=(18,24,42)
GOLD=(250,201,85)


def rect(surface,color,box,width=0,radius=0):
    r=pygame.Rect(round(box[0]),round(box[1]),max(1,round(box[2])),max(1,round(box[3])))
    pygame.draw.rect(surface,color,r,width,border_radius=radius)


def star_points(x,y,r_outer,r_inner,count=5,turn=0):
    points=[]
    for i in range(count*2):
        theta=math.tau*i/(count*2)-math.pi/2+turn
        r=r_outer if i%2==0 else r_inner
        points.append((int(x+r*math.cos(theta)),int(y+r*math.sin(theta))))
    return points


class Puppet:
    def __init__(self, name: str):
        self.name=name
        rig=json.loads((ASSETS/'rigs'/(name+'.json')).read_text())
        self.rig=rig
        directory=ASSETS/'generated'/'parts'/name
        self.pivots=json.loads((directory/'manifest.json').read_text())['pivots']
        self.parts=sorted(rig['parts'],key=lambda p:p['z'])
        self.images={part['name']:pygame.image.load(str(directory/(part['name']+'.png'))).convert_alpha()
                     for part in self.parts}

    @lru_cache(maxsize=1000)
    def transform(self,name,degrees,facing,percent,flipped,stretch):
        img=self.images[name]
        if facing<0 or flipped:
            img=pygame.transform.flip(img,True,False)
        if stretch != 100:
            img=pygame.transform.scale(img,(img.get_width(),
                max(1,round(img.get_height()*stretch/100))))
        return pygame.transform.rotozoom(img,-degrees,percent/100)

    def sample(self,clip: str,seconds: float):
        # Keep animation interpolation independent of Pygame and SVG IO.
        clips=self.rig['clips']
        fallback='idle' if 'idle' in clips else 'death'
        return sample_pose(self.rig,clip if clip in clips else fallback,seconds)

    def draw(self,screen,feet,clip,seconds,*,facing=1,zoom=1,alpha=255,adjust=None,debug=False):
        poses=self.sample(clip,seconds)
        frame=self.rig['frame']
        cx,ground=frame['center_x'],frame['ground_y']
        zoom_pct=int(zoom*100)
        for part in self.parts:
            val=poses[part['bone']]
            x,y,angle,scale_y,flip=val
            if adjust and part['bone'] in adjust: angle+=adjust[part['bone']]
            # Each pose retains the SVG part pivot, rotation, X/Y position,
            # Y-axis squash/stretch, and authored mirroring flag.
            dx=(x-cx)*zoom*facing
            dy=(y-ground)*zoom
            original=self.images[part['name']]
            px,py=self.pivots[part['name']]
            eff_flip=int(bool(flip))
            if facing<0 or eff_flip:px=original.get_width()-px
            degree=int(round(angle*facing/2))*2
            stretch=max(10,min(300,int(round(scale_y*100))))
            src=self.transform(part['name'],degree,facing,zoom_pct,eff_flip,stretch)
            theta=math.radians(degree)
            sx=(px-original.get_width()*.5)*zoom
            sy=(py-original.get_height()*.5)*zoom*stretch/100
            off_x=sx*math.cos(theta)-sy*math.sin(theta)
            off_y=sx*math.sin(theta)+sy*math.cos(theta)
            target_x=feet[0]+dx-src.get_width()*.5-off_x
            target_y=feet[1]+dy-src.get_height()*.5-off_y
            if alpha<255:
                src=src.copy();src.set_alpha(alpha)
            screen.blit(src,(round(target_x),round(target_y)))
            if debug:
                pygame.draw.circle(screen,(255,136,75),(round(feet[0]+dx),round(feet[1]+dy)),2)


class Painter:
    def __init__(self):
        self.view=pygame.Surface(LOGICAL_SIZE).convert()
        self.w,self.h=LOGICAL_SIZE
        self.font=pygame.font.Font(None,26)
        self.small_font=pygame.font.Font(None,21)
        self.big_font=pygame.font.Font(None,78)
        self.title_font=pygame.font.Font(None,44)
        self.puppets={f: Puppet(f) for f in ('small_side','small_front','tall_side','tall_front','fire_side','fire_front')}
        self.robot=pygame.image.load(str(ASSETS/'generated'/'robot'/'castle_robot.png')).convert_alpha()
        self.camera_x=0.0
        self.camera_y=0.0
        self.last_room=''
        self.fx=[]
        self.debug=False
        self.help=True
        self.pose_lab=False
        self.lab_form='small'
        self.lab_clip='idle'
        self.lab_time=0.0
        self.lab_play=True
        self.lab_angle={}
        self.lab_selected=0

    def lab_clips(self):
        form='fire' if self.lab_form=='cosmic' else self.lab_form
        clips=list(self.puppets[form+'_side'].rig['clips'])
        return clips+['death','grow','shrink','fire_transform','cosmic_transform','cosmic_leave']

    def lab_bones(self):
        form='fire' if self.lab_form=='cosmic' else self.lab_form
        rig=self.puppets[form+'_side'].rig
        return sorted({part['bone'] for part in rig['parts']})

    def letter(self,text,pos,color=WHITE,*,big=False,center=False,small=False):
        font=self.title_font if big else self.small_font if small else self.font
        surface=font.render(str(text),True,color)
        r=surface.get_rect(center=pos) if center else surface.get_rect(topleft=pos)
        self.view.blit(surface,r)

    def project(self,x,y):
        return (x-self.camera_x,y-self.camera_y)

    def track(self,game,dt):
        if self.last_room!=game.room.name:
            self.last_room=game.room.name
            self.camera_x=self.camera_y=0
            self.fx=[]
        p=game.player
        target=max(0,min(game.room.width-self.w,p.x-self.w*.30))
        # Forward-only camera matches Mary-O's original platformer contract.
        self.camera_x=max(self.camera_x,self.camera_x+(target-self.camera_x)*min(1,dt*8))
        target_y=clamp(p.y-self.h*.64,0,max(0,game.room.height-self.h))
        self.camera_y+=(target_y-self.camera_y)*min(1,dt*5)
        for ev in game.events:
            if ev.kind not in ('room','pipe_exit'):
                self.fx.append([ev.kind,ev.x,ev.y,.45,ev.value])
        for e in self.fx:e[3]-=dt
        self.fx=[e for e in self.fx if e[3]>0]

    def background(self,game):
        biome=game.room.biome
        top,bot,near,mid,low,stone=THEMES.get(biome,THEMES['starlight'])
        screen=self.view
        for y in range(self.h):
            f=y/self.h
            color=tuple(round(a*(1-f)+b*f) for a,b in zip(top,bot))
            pygame.draw.line(screen,color,(0,y),(self.w,y))
        # Stable stars do not slide with camera motion.
        for i in range(110 if biome!='void_castle' else 35):
            x=(i*233+61)%self.w;y=(i*139+33)%300
            if (i+int(self.camera_x*.004))%4!=0:
                color=(161,180,198) if biome!='void_castle' else (183,123,166)
                pygame.draw.circle(screen,color,(x,y),1 if i%5 else 2)
        for parallax,base,amp,col in ((.1,290,54,near),(.25,345,67,mid),(.4,423,45,low)):
            points=[(-10,self.h)]
            for px in range(-20,self.w+41,20):
                wave=math.sin((px+self.camera_x*parallax)/143)*amp
                wave+=math.sin((px+self.camera_x*parallax)/47)*amp*.2
                world_y=base+wave-self.camera_y*.08
                points.append((px,int(world_y)))
            points.append((self.w+10,self.h))
            pygame.draw.polygon(screen,col,points)
        if biome=='starlight':
            moon=(int(756-self.camera_x*.035)%1300,98)
            pygame.draw.circle(screen,(219,219,181),moon,43)
            pygame.draw.circle(screen,(181,192,183),moon,41,2)
        elif biome=='void_castle':
            for i in range(12):
                x=int(i*120-self.camera_x*.16)% (self.w+120)
                pygame.draw.rect(screen,(27,22,48),(x,190,47,310))
                pygame.draw.polygon(screen,(63,28,76),[(x-10,190),(x+23,140),(x+57,190)])
                pygame.draw.rect(screen,(173,65,93),(x+14,238,20,60))
                pygame.draw.line(screen,(229,147,105),(x+24,238),(x+24,298),2)
        elif biome=='stardune':
            pygame.draw.circle(screen,(252,190,132),(770,142),61)

    def ground_tile(self,x,y,tile,biome,t):
        fg={
            'starlight':((71,106,94),(39,62,61),(110,163,128)),
            'starless':((78,81,103),(39,40,60),(111,117,136)),
            'stardune':((192,143,100),(132,85,94),(239,189,124)),
            'void_castle':((95,64,91),(54,35,71),(160,95,112)),
        }.get(biome,((71,106,94),(39,62,61),(110,163,128)))
        face,outline,edge=fg
        sx,sy=self.project(x,y)
        if sx<-TILE or sx>self.w or sy<-TILE or sy>self.h:return
        rect(self.view,outline,(sx,sy,TILE,TILE))
        rect(self.view,face,(sx+1,sy+1,TILE-2,TILE-2))
        if tile==1:
            pygame.draw.line(self.view,edge,(round(sx+2),round(sy+2)),(round(sx+13),round(sy+2)),2)
            if (int(x//16)*7+int(y//16)*13)%5==0:
                pygame.draw.line(self.view,outline,(round(sx+6),round(sy+8)),(round(sx+11),round(sy+8)))
        elif tile==2:
            rect(self.view,edge,(sx,sy,16,3))

    def draw_course(self,game):
        l=game.room
        left=max(0,int(self.camera_x//TILE)-1)
        right=min(l.grid_width,int((self.camera_x+self.w)//TILE)+2)
        top=max(0,int(self.camera_y//TILE)-1)
        bottom=min(l.grid_height,int((self.camera_y+self.h)//TILE)+2)
        for row in range(top,bottom):
            for col in range(left,right):
                value=l.terrain(col,row)
                if value:
                    self.ground_tile(col*TILE,row*TILE,value,l.biome,game.elapsed)
        for s in game.solids:
            if s.fields.get('name')=='goal_gate' and game.switch_pressed:continue
            x,y=self.project(s.x,s.y)
            if x+s.w<0 or x>self.w:continue
            if s.fields.get('name')=='goal_switch':
                self.draw_switch(x,y,s.w,s.h,game.switch_pressed)
            else:
                c=(102,74,111) if l.biome=='void_castle' else (85,112,105)
                rect(self.view,(29,34,53),(x,y,s.w,s.h),radius=2)
                rect(self.view,c,(x+3,y+3,s.w-6,s.h-6),radius=1)
        for b in game.blocks:
            if b.identifier in game.broken:continue
            self.draw_block(b, b.identifier in game.spent, game.elapsed)
        for p in game.pipes:self.draw_pipe(p)
        for m in game.moving:self.draw_platform(m.box.x,m.box.y,m.box.w,m.box.h)
        for p in game.oneway:self.draw_platform(p.x,p.y,p.w,p.h)
        for pole in game.room.all('OneWayPlatform'):
            if pole.fields.get('name')!='goal_pole':continue
            x,y=self.project(pole.x,pole.y)
            rect(self.view,(226,226,209),(x,y,7,pole.h))
            rect(self.view,(254,219,104),(x-6,y-7,20,11),radius=5)
            pygame.draw.polygon(self.view,(224,85,128),[(x+6,y+18),(x+64,y+29),(x+6,y+48)])
        for h in game.hazards:self.draw_hazard(h,game.elapsed)
        if l.biome=='void_castle':
            for s in game.solids:
                if s.fields.get('name')=='goal_gate' and not game.switch_pressed:
                    sx,sy=self.project(s.x,s.y)
                    for yy in range(0,int(s.h),16):rect(self.view,(132,91,137),(sx,sy+yy,s.w,6))
        for npc in game.room.all('NpcSpawn'):
            if npc.fields.get('character_id')=='mary_o_robot':
                sx,sy=self.project(npc.cx,npc.bottom)
                self.view.blit(self.robot,(round(sx-self.robot.get_width()/2),
                                           round(sy-self.robot.get_height())))
        if game.room.name=='mary_o_warp':
            for pipe in game.pipes:
                x,y=self.project(pipe.cx,pipe.y-35)
                self.letter(pipe.fields.get('link','').replace('mary_o_','').replace('_','-'),
                            (round(x),round(y)),WHITE,center=True)

    def draw_block(self,b,spent,t):
        kind=b.fields.get('kind','Question')
        if kind=='Hidden' and not spent:return
        sx,sy=self.project(b.x,b.y)
        if sx<-36 or sx>self.w or sy<-36 or sy>self.h:return
        if kind=='Plank':
            rect(self.view,(57,34,57),(sx,sy,b.w,b.h),radius=2)
            rect(self.view,(157,106,90),(sx+2,sy+2,b.w-4,b.h-6),radius=3)
            for i in range(2):rect(self.view,(205,151,103),(sx+2,sy+4+i*12,b.w-4,3))
            return
        if kind=='Brick':
            rect(self.view,(64,50,70),(sx,sy,b.w,b.h),radius=2)
            for dy in (0,16):
                shift=0 if dy==0 else 8
                for dx in (-16+shift,shift,16+shift):
                    rect(self.view,(148,93,87),(sx+dx+1,sy+dy+1,14,14))
            return
        rect(self.view,(90,64,53),(sx,sy,b.w,b.h),radius=4)
        color=(158,155,149) if spent else (236,168,72)
        rect(self.view,color,(sx+3,sy+3,b.w-6,b.h-6),radius=3)
        for dx in (6,b.w-6):
            for dy in (6,b.h-6):
                pygame.draw.circle(self.view,(90,69,67),(round(sx+dx),round(sy+dy)),2)
        if not spent:self.letter('?',(round(sx+b.w/2),round(sy+b.h/2)),(255,248,194),center=True)

    def draw_pipe(self,p):
        x,y=self.project(p.x,p.y)
        if x+p.w<0 or x>self.w:return
        main=(43,125,105);side=(28,83,79);shine=(116,204,133)
        rect(self.view,side,(x+7,y+7,p.w-14,p.h-7),radius=4)
        rect(self.view,main,(x+13,y+11,p.w-26,p.h-14),radius=3)
        pygame.draw.line(self.view,shine,(round(x+18),round(y+14)),(round(x+18),round(y+p.h-6)),4)
        if p.fields.get('mouth','Up')=='Up':
            rect(self.view,(18,74,76),(x,y,p.w,19),radius=3)
            rect(self.view,(64,169,112),(x+4,y+3,p.w-8,12),radius=2)
            rect(self.view,(150,216,145),(x+12,y+4,p.w*.21,4),radius=2)
        else:
            rect(self.view,(18,74,76),(x,y+p.h-19,p.w,19),radius=3)
            rect(self.view,(64,169,112),(x+4,y+p.h-15,p.w-8,12),radius=2)

    def draw_platform(self,x,y,w,h):
        sx,sy=self.project(x,y)
        if sx+w<0 or sx>self.w:return
        rect(self.view,(41,49,62),(sx,sy,w,max(8,h)),radius=3)
        rect(self.view,(183,139,88),(sx+1,sy+1,w-2,7),radius=2)
        for dx in range(9,int(w),18):
            pygame.draw.circle(self.view,(237,202,120),(round(sx+dx),round(sy+5)),2)

    def draw_hazard(self,h,t):
        sx,sy=self.project(h.x,h.y)
        if sx+h.w<0 or sx>self.w:return
        name=str(h.fields.get('name',''))
        if name.startswith('lava'):
            rect(self.view,(151,49,72),(sx,sy,h.w,h.h))
            for dx in range(0,max(0,int(h.w)),16):
                yy=3*math.sin(t*4+dx*.14)
                pygame.draw.ellipse(self.view,(242,124,81),(sx+dx,sy+yy-5,21,9))
        else:
            r=max(5,min(11,h.w*.6))
            color=(255,109,72)
            pygame.draw.circle(self.view,(79,32,61),(round(sx+h.w/2),round(sy+h.h/2)),round(r)+2)
            pygame.draw.circle(self.view,color,(round(sx+h.w/2),round(sy+h.h/2)),round(r))
            pygame.draw.circle(self.view,(255,218,130),(round(sx+h.w/2-2),round(sy+h.h/2-2)),3)

    def draw_switch(self,x,y,w,h,pressed):
        rect(self.view,(48,37,61),(x,y,w,h))
        rect(self.view,(189,80,107),(x+4,y+3+(7 if pressed else 0),w-8,max(4,h*.3)))
        rect(self.view,(248,177,110),(x+7,y+5+(7 if pressed else 0),w-14,3))

    def draw_item(self,item,t):
        x,y=self.project(item.x+item.w/2,item.y+item.h/2)
        if x<-25 or x>self.w+25:return
        if item.kind=='coin':
            w=6+4*abs(math.cos(t*3+item.x))
            pygame.draw.ellipse(self.view,(91,60,75),(x-w-2,y-12,2*w+4,24))
            pygame.draw.ellipse(self.view,(255,206,80),(x-w,y-10,2*w,20))
            pygame.draw.line(self.view,(255,247,162),(x,y-7),(x,y+7),2)
        elif item.kind=='wand':
            pygame.draw.polygon(self.view,(255,224,109),star_points(x,y,12,5,5,t))
            pygame.draw.line(self.view,(222,112,149),(x+5,y+5),(x+12,y+20),5)
        elif item.kind=='lantern':
            pygame.draw.polygon(self.view,(255,133,79),star_points(x,y,15,7,6,t))
            pygame.draw.circle(self.view,(255,235,167),(round(x),round(y)),6)
        else:
            pygame.draw.polygon(self.view,(252,224,126),star_points(x,y,15,6,5,t*2))

    def draw_enemy(self,e,t):
        x,y=self.project(e.x,e.y)
        if x+e.w<-30 or x>self.w+30 or y+e.h<-60 or y>self.h+50:return
        cx=x+e.w/2;cy=y+e.h/2
        if e.kind=='ai_slop':
            pygame.draw.ellipse(self.view,(23,52,57),(x-2,y+2,e.w+4,e.h))
            pygame.draw.ellipse(self.view,(133,181,110),(x,y+4,e.w,e.h-5))
            for dx in (-6,6):pygame.draw.circle(self.view,(255,239,213),(round(cx+dx),round(cy-2)),4)
            pygame.draw.arc(self.view,(38,53,58),(x+5,y+e.h*.42,e.w-10,e.h*.35),0,math.pi,2)
        elif e.kind=='solid_snake':
            # Side view of a shelled creature, including its shell phase.
            pygame.draw.ellipse(self.view,(45,69,69),(x-4,y+6,e.w+8,e.h-7))
            pygame.draw.ellipse(self.view,(73,149,121),(x-2,y+6,e.w+4,e.h-10))
            pygame.draw.ellipse(self.view,(172,119,113),(x+3,y+2,e.w-6,e.h*.74))
            for dx in (8,17):pygame.draw.line(self.view,(99,67,81),(x+dx,y+6),(x+dx+4,y+e.h*.64),2)
            if e.phase=='walk':
                pygame.draw.circle(self.view,(110,192,139),(round(x+e.w*(.77 if e.facing>0 else .22)),round(y+10)),8)
                pygame.draw.circle(self.view,INK,(round(x+e.w*(.8 if e.facing>0 else .2)),round(y+7)),2)
        elif e.kind=='void_star':
            pygame.draw.polygon(self.view,(235,237,229),star_points(cx,cy,max(10,e.w*.6),6,5,t*.3))
            pygame.draw.polygon(self.view,(27,28,44),star_points(cx,cy,max(8,e.w*.52),5,5,t*.3))
            for dx in (-4,4):pygame.draw.circle(self.view,(255,252,239),(round(cx+dx),round(cy)),2)
        elif e.kind=='snake_plant':
            if e.phase=='hidden':return
            pygame.draw.ellipse(self.view,(46,151,100),(x,y,e.w,e.h))
            pygame.draw.ellipse(self.view,(255,142,146),(x+e.w*.65,y+e.h*.3,e.w*.3,e.h*.22))
            pygame.draw.circle(self.view,(254,250,199),(round(cx-4),round(cy-3)),4)
        elif e.kind=='laden_swallow' or 'plane' in e.kind:
            pygame.draw.ellipse(self.view,(220,207,187),(x+2,y+7,e.w-3,e.h-9))
            pygame.draw.polygon(self.view,(153,185,189),[(x+e.w/2,y+4),(x-8,y-7),(x+e.w*.38,y+e.h*.5)])
            pygame.draw.polygon(self.view,(103,134,158),[(x+e.w/2,y+4),(x+e.w+8,y-7),(x+e.w*.55,y+e.h*.5)])
            pygame.draw.circle(self.view,INK,(round(x+e.w*.74),round(y+e.h*.45)),2)
        elif e.kind=='void_lizard':
            pygame.draw.ellipse(self.view,(210,216,224),(x-5,y+e.h*.2,e.w+10,e.h*.7))
            pygame.draw.ellipse(self.view,(35,34,52),(x,y+e.h*.25,e.w,e.h*.65))
            for i in range(5):
                tx=x+i*e.w/5
                pygame.draw.polygon(self.view,(236,236,238),[(tx,y+e.h*.29),(tx+e.w*.1,y+e.h*.02),(tx+e.w*.2,y+e.h*.29)])
            pygame.draw.circle(self.view,(255,243,225),(round(x+e.w*.76),round(y+e.h*.48)),5)
            pygame.draw.circle(self.view,(188,53,86),(round(x+e.w*.78),round(y+e.h*.48)),2)

    def draw_spark(self,s,t):
        x,y=self.project(s.x,s.y)
        c=(211,210,220) if s.enemy else (255,173,93)
        pygame.draw.polygon(self.view,(255,245,171) if not s.enemy else (242,239,240),
                            star_points(x,y,11,5,6,t*5))
        pygame.draw.circle(self.view,c,(round(x),round(y)),4)

    def draw_cosmic(self,feet,t,wing_scale=1.0,opacity=255,transform=False):
        """Software-drawn wings, star crown, and aura: no shader dependency."""
        x,y=feet
        swing=math.sin(t*9)*.23
        for direction in (-1,1):
            outer=direction*(22+13*wing_scale)
            lift=(16+16*wing_scale)*(1+swing)
            poly=[(x+direction*6,y-46),(x+outer*.63,y-65-lift),
                  (x+outer*1.2,y-72-lift),(x+outer*1.4,y-40-lift*.45),
                  (x+direction*7,y-34)]
            pygame.draw.polygon(self.view,(188,218,248),poly)
            pygame.draw.lines(self.view,(255,248,247),False,poly,2)
            pygame.draw.line(self.view,(238,176,229),(x+direction*8,y-42),
                             (x+outer,y-61-lift),3)
        for r,c in ((27,(229,158,227)),(20,(255,216,146))):
            pygame.draw.arc(self.view,c,(x-r,y-62-r//2,2*r,r),math.pi,math.tau,2)
        pygame.draw.polygon(self.view,(255,232,136),star_points(x,y-76,12,5,5,t*.7))
        if transform:
            for i in range(16):
                phase=i*math.tau/16+t*3
                bx=x+math.cos(phase)*(.5+wing_scale)*41
                by=y-40+math.sin(phase)*(.5+wing_scale)*54
                pygame.draw.circle(self.view,(255,227,176),(round(bx),round(by)),2)

    def lab_cosmic(self,feet,t,wing_scale=1.0,transform=False):
        # Reuse the gameplay-drawn cosmic ornaments at the pose-lab's 3x zoom.
        old=self.view
        tile=pygame.Surface((160,180),pygame.SRCALPHA)
        try:
            self.view=tile
            self.draw_cosmic((80,160),t,wing_scale,transform=transform)
        finally:
            self.view=old
        x,y=feet
        zoomed=pygame.transform.scale(tile,(480,540))
        self.view.blit(zoomed,(round(x-240),round(y-480)))

    def draw_player(self,game):
        p=game.player
        px,py=self.project(*p.foot)
        clip=game.display_animation()
        form=p.form
        if p.invulnerable>0 and int(game.elapsed*15)%2 and p.transition_time<=0:
            return
        if p.quasar>0 and not p.cosmic:
            for i in range(5):
                col=((255,214,125),(169,221,251),(245,169,220))[i%3]
                pygame.draw.circle(self.view,col,(round(px),round(py-27)),round(21+i*3),1)
        if p.transition_time>0:
            if clip=='cosmic_transform':
                phase=1-p.transition_time/(36*.095)
                self.draw_cosmic((px,py),game.elapsed,clamp(phase*2,0.2,1.4),transform=True)
                puppet=self.puppets['fire_side']
                puppet.draw(self.view,(px,py),'idle',0,facing=p.direction)
                for i in range(12):
                    a=i*math.tau/12+game.elapsed*4
                    r=(16+phase*51)
                    pygame.draw.circle(self.view,(247,233,191),(round(px+math.cos(a)*r),round(py-40+math.sin(a)*r)),3)
                return
            if clip=='cosmic_leave':
                self.draw_cosmic((px,py),game.elapsed,max(0,p.transition_time/1.91),transform=True)
                self.puppets['fire_side'].draw(self.view,(px,py),'idle',0,facing=p.direction)
                return
            if clip in ('grow','shrink','fire_transform'):
                self.draw_transition(game,(px,py))
                return
        if form=='cosmic':
            self.draw_cosmic((px,py),game.elapsed,1.0+0.1*math.sin(game.elapsed*9))
            puppet=self.puppets['fire_side']
            puppet.draw(self.view,(px,py),clip if clip in puppet.rig['clips'] else 'idle',
                        p.anim_time,facing=p.direction)
        else:
            projection='front' if clip=='death' else 'side'
            puppet=self.puppets[form+'_'+projection]
            if clip not in puppet.rig['clips']:clip='jump' if clip=='fall' else 'idle'
            puppet.draw(self.view,(px,py),clip,p.anim_time,facing=p.direction,debug=self.debug)
        if self.debug:
            rect(self.view,(255,99,82),(p.x-self.camera_x,p.y-self.camera_y,p.w,p.h),width=1)

    def draw_transition(self,game,feet):
        p=game.player
        total={'grow':.28,'shrink':.51,'fire_transform':.85}.get(p.transition, .34)
        fraction=clamp(1-p.transition_time/total,0,1)
        if p.transition=='grow':
            from_form,to_form='small','tall'
        elif p.transition=='shrink':
            from_form,to_form=('tall','small') if p.form=='small' else ('fire','tall')
        else:
            from_form,to_form='tall','fire'
        earlier=self.puppets[from_form+'_side']
        later=self.puppets[to_form+'_side']
        earlier.draw(self.view,feet,'idle',0,facing=p.direction,alpha=max(0,int(255*(1-fraction))))
        later.draw(self.view,feet,'idle',0,facing=p.direction,alpha=min(255,int(255*fraction)))
        if p.transition=='fire_transform':
            for i in range(8):
                r=15+fraction*26
                a=i*math.tau/8+game.elapsed*3
                pygame.draw.circle(self.view,(255,211,124),
                                   (round(feet[0]+math.cos(a)*r),round(feet[1]-35+math.sin(a)*r)),3)

    def draw_effects(self):
        for name,x,y,left,value in self.fx:
            sx,sy=self.project(x,y)
            f=left/.45
            if name in ('coin','pickup','flag','castle','life'):
                msg=('+'+str(value)) if value>0 else ('+200' if name=='coin' else '+')
                self.letter(msg,(round(sx),round(sy-28*(1-f))),GOLD,center=True)
            elif name in ('bonk','break','stomp','spark_hit','shoot'):
                for i in range(5):
                    a=i*math.tau/5+f
                    d=(1-f)*22
                    pygame.draw.circle(self.view,(255,209,126),
                                       (round(sx+math.cos(a)*d),round(sy+math.sin(a)*d)),max(1,int(f*4)))

    def hud(self,game):
        rect(self.view,(16,23,41),(0,0,self.w,46))
        p=game.player
        self.letter('MARY-O', (19,12), (250,171,191))
        self.letter(f'{game.score:07d}',(126,12))
        self.letter(f'COINS  {game.coins:02d}',(322,12),GOLD)
        self.letter(game.room.title,(514,12))
        self.letter(f'TIME  {math.ceil(game.clock):03d}',(734,12))
        self.letter(f'x{game.lives}',(897,12))
        if self.help:
            rect(self.view,(18,30,54),(8,self.h-38,self.w-16,30),radius=4)
            self.letter('ARROWS move / aim    Z jump    X spark (Fire)    D cosmic    SHIFT walk    DOWN pipe    F1 help    F2 poses',
                        (19,self.h-31),WHITE,small=True)
        if game.flag_state == 'castle' and 5.8 < game.castle_timer < 9.8:
            rect(self.view,(25,29,53),(self.w/2-260,self.h-155,520,63),radius=6)
            self.letter('ROBOT: "Thank you, Mary-O. You saved me."',
                        (self.w/2,self.h-122),GOLD,center=True)
        if game.flag_state == 'tally' or (game.flag_state == 'castle' and game.castle_timer > 9.8):
            rect(self.view,(26,29,49),(self.w/2-245,150,490,185),radius=9)
            self.letter('COURSE CLEAR!' if game.flag_state=='tally' else 'THE VOID BRIDGE FALLS',
                        (self.w/2,215),GOLD,big=True,center=True)
            self.letter('Next world is loading...', (self.w/2,279),WHITE,center=True)
        if game.elapsed < 2 and game.tick_count<120:
            rect(self.view,(24,32,57),(self.w/2-215,150,430,128),radius=10)
            self.letter(game.room.title,(self.w/2,187),GOLD,big=True,center=True)
            self.letter(f'MARY-O   x{game.lives}',(self.w/2,234),WHITE,center=True)

    def frame(self,game,dt):
        self.track(game,dt)
        self.background(game)
        self.draw_course(game)
        for item in game.items:self.draw_item(item,game.elapsed)
        for e in game.enemies:
            if e.alive:self.draw_enemy(e,game.elapsed)
        for s in game.sparks:self.draw_spark(s,game.elapsed)
        self.draw_player(game)
        self.draw_effects()
        self.hud(game)
        return self.view

    def lab_frame(self,dt):
        self.lab_time+=dt if self.lab_play else 0
        self.view.fill((26,31,57))
        for i in range(65):
            x=(i*101+27)%self.w;y=(i*79+19)%self.h
            pygame.draw.circle(self.view,(87,112,153),(x,y),1)
        self.letter('MARY-O POSE LAB',(self.w/2,50),GOLD,big=True,center=True)
        self.letter('UP/DOWN form  LEFT/RIGHT clip  TAB joint  [/] angle  SPACE pause  R reset  F2 return',
                    (self.w/2,91),WHITE,center=True,small=True)
        name=self.lab_form+('_front' if self.lab_clip=='death' else '_side')
        if self.lab_form=='cosmic':
            name='fire_front' if self.lab_clip=='death' else 'fire_side'
        puppet=self.puppets[name]
        clip=self.lab_clip if self.lab_clip in puppet.rig['clips'] else 'idle'
        cx,cy=self.w/2,self.h*.78
        pygame.draw.line(self.view,(84,110,133),(90,cy),(self.w-90,cy),2)
        # The transition previews use the same compositing principles as
        # normal gameplay, including the two long cosmic sequences.
        if self.lab_clip in ('grow','shrink','fire_transform'):
            if self.lab_clip=='grow':
                earlier,later,duration='small','tall',.28
            elif self.lab_clip=='shrink':
                earlier,later,duration='tall','small',.51
            else:
                earlier,later,duration='tall','fire',.85
            fraction=min(1,(self.lab_time%(duration+.7))/duration)
            self.puppets[earlier+'_side'].draw(self.view,(cx,cy),'idle',0,zoom=3,
                                               alpha=round(255*(1-fraction)))
            self.puppets[later+'_side'].draw(self.view,(cx,cy),'idle',0,zoom=3,
                                             alpha=round(255*fraction))
        elif self.lab_clip in ('cosmic_transform','cosmic_leave'):
            duration=36*.095 if self.lab_clip=='cosmic_transform' else 18*.095+.2
            fraction=min(1,(self.lab_time%(duration+.75))/duration)
            if self.lab_clip=='cosmic_leave': fraction=1-fraction
            puppet=self.puppets['fire_side']
            self.lab_cosmic((cx,cy),self.lab_time,max(.1,fraction*3),transform=True)
            puppet.draw(self.view,(cx,cy),'idle',0,zoom=3,alpha=255)
        else:
            if self.lab_form=='cosmic' and self.lab_clip!='death':
                self.lab_cosmic((cx,cy),self.lab_time,1.2)
            puppet.draw(self.view,(cx,cy),clip,self.lab_time,zoom=3,
                        adjust=self.lab_angle,debug=self.debug)
        bones=self.lab_bones()
        bone=bones[self.lab_selected%len(bones)]
        self.letter(f'{self.lab_form.upper()} / {self.lab_clip.upper()}  t={self.lab_time:0.2f}s',
                    (self.w/2,self.h-88),WHITE,center=True)
        self.letter(f'Tab joint: {bone}  angle offset: {self.lab_angle.get(bone,0):+d}  [ ] rotate  Backspace clear',
                    (self.w/2,self.h-61),WHITE,center=True,small=True)
        self.letter('SVG: assets/svg/mary_o_v2.svg    Keyframes: assets/rigs/*.json    Generated PNG/WAV: Git-ignored',
                    (self.w/2,self.h-28),(154,176,193),center=True,small=True)
        return self.view
