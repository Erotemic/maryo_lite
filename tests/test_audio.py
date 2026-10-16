"""The chiptune renderer produces real PCM from tracked note sequences."""
import sys
from pathlib import Path
import wave

from mary_o_lite.content import ROOT
sys.path.insert(0,str(ROOT/'tools'))
from compose_audio import RATE, PITCHES, TRACKS, SOUNDS, effect, hz


def test_tracks_and_effects_are_readable_source_data():
    assert len(TRACKS)==5
    assert all(64==len(item[1]) for item in TRACKS.values())
    assert len(SOUNDS)>=12
    assert hz('A4')==440
    assert hz('-')==0


def test_wav_is_generated_from_math(tmp_path):
    path=tmp_path/'step.wav'
    effect(path,400,.1,'triangle',-100)
    with wave.open(str(path),'rb') as wav:
        assert wav.getnchannels()==1
        assert wav.getframerate()==RATE
        assert wav.getsampwidth()==2
        assert wav.getnframes()>1000
