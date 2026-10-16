#!/usr/bin/env python3
"""Generate loopable 8-bit-inspired tracks and effects from note sequences.

No checked-in samples, external soundfonts, DAW, or audio processing package.
"""
from __future__ import annotations

from array import array
import math
from pathlib import Path
import random
import wave

RATE=22050
PITCHES={'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}


def hz(note):
    if note=='-':return 0
    number=PITCHES[note[:-1]]+(int(note[-1])+1)*12
    return 440*2**((number-69)/12)


def tone(t,h,shape):
    if not h:return 0
    phase=(t*h)%1
    if shape=='pulse':return 1 if phase<.25 else -.33
    if shape=='square':return 1 if phase<.5 else -1
    if shape=='triangle':return 1-4*abs(phase-.5)
    return math.sin(t*math.tau*h)


def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE)
        samples=array('h',(int(max(-.98,min(.98,x))*32767) for x in data))
        w.writeframes(samples.tobytes())


def add(mix,note,start,duration,volume,shape):
    h=hz(note)
    if not h:return
    at=int(start*RATE)
    for i in range(min(int(duration*RATE),len(mix)-at)):
        t=i/RATE
        attack=min(1,t/.006)
        release=min(1,(duration-t)/.03)
        mix[at+i]+=volume*tone(t,h,shape)*max(0,attack*release)


def song(path,bpm,lead,bass):
    beat=60/bpm
    bars=8
    mix=[0.0]*int(RATE*bars*4*beat)
    for i,n in enumerate(lead):
        add(mix,n,i*beat*.5,beat*.46,.17,'pulse')
        if i%4==0 and n!='-':
            add(mix,n[:-1]+str(int(n[-1])-1),i*beat*.5,beat*.42,.034,'triangle')
    for i in range(bars*2):
        add(mix,bass[i%len(bass)],i*beat*2,beat*1.72,.13,'triangle')
    rng=random.Random(23)
    for i in range(bars*4):
        at=int(i*beat*RATE)
        for j in range(min(int(.12*RATE),len(mix)-at)):
            t=j/RATE
            if i%4 in (0,2):
                v=math.sin((110-60*t/.12)*math.tau*t)*math.exp(-t*26)*.18
            else:
                v=rng.uniform(-1,1)*math.exp(-t*35)*.09
            mix[at+j]+=v
    write(path,mix)


TRACKS={
 'starlight':(154,
  ['E5','G5','B5','E6','D6','B5','A5','G5','E5','G5','A5','B5','G5','E5','D5','-',
   'C5','E5','G5','B5','A5','G5','E5','G5','D5','F5','A5','C6','B5','A5','G5','-',
   'E5','G5','B5','E6','G6','E6','D6','B5','C6','B5','A5','G5','E5','G5','B5','-',
   'F5','A5','C6','A5','G5','E5','D5','F5','E5','G5','B5','G5','E5','D5','E5','-'],
  ['E3','E3','C3','C3','A2','A2','B2','B2','C3','C3','D3','D3','B2','B2','E3','E3']),
 'starless':(126,
  ['A4','-','C5','E5','-','E5','D5','C5','A4','-','G4','A4','-','C5','B4','-',
   'D5','F5','-','E5','C5','-','A4','G4','B4','D5','-','F5','E5','D5','C5','-',
   'A4','C5','E5','-','G5','-','E5','D5','C5','A4','-','G4','A4','C5','-','-',
   'F4','A4','C5','D5','-','C5','A4','G4','E4','G4','B4','-','A4','-','-','-'],
  ['A2','A2','F2','F2','D2','D2','E2','E2','G2','G2','F2','F2','E2','E2','A2','A2']),
 'stardune':(140,
  ['D5','F5','A5','-','C6','A5','F5','D5','E5','G5','B5','-','A5','F5','E5','-',
   'F5','A5','D6','C6','A5','F5','E5','D5','C5','E5','G5','A5','G5','E5','D5','-',
   'A4','D5','F5','-','A5','C6','D6','-','C6','A5','G5','F5','E5','D5','E5','-',
   'D5','F5','A5','C6','B5','A5','F5','E5','D5','-','A4','C5','D5','-','-','-'],
  ['D3','D3','A2','A2','G2','G2','F2','F2','D3','D3','E3','E3','A2','A2','D3','D3']),
 'void_castle':(152,
  ['E5','E5','G5','A#5','A5','G5','F5','-','D5','D5','F5','A5','G5','F5','D5','-',
   'E5','G5','A#5','C6','B5','A#5','G5','F5','E5','G5','B5','A#5','A5','G5','F5','-',
   'G5','A#5','D6','C6','A#5','G5','F5','-','E5','G5','B5','C6','B5','A5','G5','-',
   'E5','F5','G5','A#5','B5','C6','D6','-','C6','A#5','A5','G5','F5','E5','E5','-'],
  ['E2','E2','D2','D2','C2','C2','B2','B2','E2','E2','F2','F2','G2','G2','E2','E2']),
 'cosmic':(166,
  ['G5','B5','D6','G6','F#6','D6','B5','D6','E6','G6','A6','-','G6','E6','D6','-',
   'C6','E6','G6','A6','G6','E6','D6','C6','B5','D6','F#6','A6','G6','F#6','D6','-',
   'G5','B5','D6','G6','A6','B6','A6','G6','F#6','E6','D6','B5','A5','B5','D6','-',
   'E6','G6','B6','A6','G6','F#6','E6','D6','C6','B5','A5','G5','B5','D6','G6','-'],
  ['G3','G3','D3','D3','E3','E3','C3','C3','A2','A2','B2','B2','D3','D3','G3','G3']),
}

SOUNDS={
 'jump':(380,.17,'triangle',300), 'coin':(930,.12,'pulse',270),
 'bonk':(200,.12,'square',-100),'break':(165,.22,'pulse',-140),
 'stomp':(290,.13,'triangle',-180),'kick':(160,.21,'square',-70),
 'shoot':(1000,.15,'pulse',-640),'spark_hit':(270,.17,'square',-160),
 'hurt':(330,.32,'triangle',-220),'die':(380,.58,'pulse',-340),
 'pickup':(720,.43,'triangle',480),'transform':(450,.6,'triangle',350),
 'pipe':(300,.28,'square',-180),'flag':(780,.55,'triangle',190),
 'castle':(200,.6,'pulse',-150),'life':(850,.5,'triangle',350),
}


def effect(path,frequency,duration,shape,glide):
    out=[0.0]*int(RATE*duration)
    for i in range(len(out)):
        t=i/RATE
        amp=min(1,t/.008)*(1-t/duration)**1.8
        out[i]=.31*amp*tone(t,frequency+glide*t/duration,shape)
    write(path,out)


def build_audio(directory: Path,force=False):
    directory.mkdir(parents=True,exist_ok=True)
    generated=0
    for name,(bpm,lead,bass) in TRACKS.items():
        target=directory/(name+'.wav')
        if force or not target.exists():
            song(target,bpm,lead,bass);generated+=1
    for name,params in SOUNDS.items():
        target=directory/(name+'.wav')
        if force or not target.exists():
            effect(target,*params);generated+=1
    print(f'Generated {generated} chiptune tracks/effects (cached).')


if __name__=='__main__':
    build_audio(Path(__file__).resolve().parents[1]/'assets/generated/audio',True)
