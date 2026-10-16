"""Read and interpolate pose clips with no Pygame dependency.

Every keyframe maps a joint name to five authored values:
  [x, y, angle_degrees, vertical_scale, mirror]
Joint positions, rotations, squash/stretch and mirroring come from the
Ambition Mary-O SVG paper-doll authoring. Presentation chooses the images.
"""
from __future__ import annotations

from functools import lru_cache
import json

from .content import ASSETS


@lru_cache(maxsize=12)
def load_rig(form: str, view: str = 'side') -> dict:
    if form == 'cosmic':
        form = 'fire'  # Cosmic wings and halo are drawn separately.
    if form not in ('small', 'tall', 'fire') or view not in ('side', 'front'):
        raise ValueError(f'Unknown Mary-O rig: {form}_{view}')
    return json.loads((ASSETS / 'rigs' / f'{form}_{view}.json').read_text())


def sample_pose(rig: dict, clip: str, seconds: float) -> dict:
    """Interpolate all authored numeric joint properties at a given time.

    Looping clips wrap; one-shot clips hold their final frame. The discrete
    mirror flag changes at keyframes, never during an in-between frame.
    """
    clips = rig['clips']
    if clip not in clips:
        raise KeyError(f'Clip {clip!r} not in {list(clips)}')
    track = clips[clip]
    frames = track['frames']
    if len(frames) == 1:
        return frames[0]
    pos = max(0, seconds * 1000 / track['ms'])
    if track['loop']:
        pos %= len(frames)
    else:
        pos = min(pos, len(frames) - 1)
    index = int(pos)
    blend = pos - index
    next_index = ((index + 1) % len(frames) if track['loop']
                  else min(len(frames) - 1, index + 1))
    before, after = frames[index], frames[next_index]
    return {
        joint: [value[i] + (after[joint][i] - value[i]) * blend
                if i < 4 else value[i] for i in range(5)]
        for joint, value in before.items()
    }
