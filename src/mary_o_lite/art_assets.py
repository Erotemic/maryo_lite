"""Pygame reader for generated original Ambition Mary-O art frames.

All PNGs here are caches rendered from tracked Python painters and SVGs by
`tools/build_assets.py`; this reader never reaches into Ambition at runtime.
"""
from __future__ import annotations

from functools import lru_cache
import json
import math

import pygame

from .content import ASSETS
from .motion import plant_placement


class SourceArt:
    def __init__(self):
        self.root = ASSETS / 'generated' / 'ambition'
        self.cosmic = self._manifest('cosmic')
        self.enemies = {
            kind: self._manifest('enemies', kind)
            for kind in ('ai_slop', 'solid_snake', 'snake_plant', 'void_star', 'void_lizard',
                         'npc_snakes_on_a_paper_plane',
                         'npc_snakes_on_a_cartesian_plane')
        }
        self.props = {
            kind: self._manifest('props', kind)
            for kind in ('super_mary_o_coin', 'super_mary_o_star_wand',
                         'super_mary_o_cinder_beacon', 'super_mary_o_cosmic_quasar',
                         'super_mary_o_milk_carton', 'super_mary_o_spark_blossom',
                         'super_mary_o_pipe', 'super_mary_o_gasoline_tank')
        }
        construction = self.root / 'construction'
        self.construction = {
            folder.name: self._manifest('construction', folder.name)
            for folder in construction.iterdir() if folder.is_dir()
        }
        self.tiles = {
            key: self._image(str(self.root / 'tiles' / (key + '.png')))
            for key in json.loads((self.root / 'tiles' / 'manifest.json').read_text())['keys']
        }

    def _manifest(self, *bits):
        return json.loads((self.root.joinpath(*bits) / 'manifest.json').read_text())

    @staticmethod
    @lru_cache(maxsize=1200)
    def _image(path: str):
        return pygame.image.load(path).convert_alpha()

    @staticmethod
    @lru_cache(maxsize=1200)
    def _scaled(path: str, width: int, height: int, flip: bool, smooth: bool):
        image = SourceArt._image(path)
        if (width, height) != image.get_size():
            transform = pygame.transform.smoothscale if smooth else pygame.transform.scale
            image = transform(image, (max(1, width), max(1, height)))
        if flip:
            image = pygame.transform.flip(image, True, False)
        return image

    @staticmethod
    def row_frame(meta, row, seconds, *, one_shot=False):
        """Frame index from original source cadence; one-shots never wrap."""
        rows = meta['rows']
        if row not in rows:
            row = 'idle' if 'idle' in rows else next(iter(rows))
        data = rows[row]
        index = max(0, math.floor(seconds * 1000 / data['delay_ms']))
        if one_shot:
            index = min(data['count'] - 1, index)
        else:
            index %= data['count']
        return row, index

    def frame(self, family, kind, clip, seconds, *, one_shot=False):
        if family == 'cosmic':
            meta = self.cosmic
            directory = self.root / 'cosmic'
        else:
            meta = ({'enemies': self.enemies, 'props': self.props,
                     'construction': self.construction}[family])[kind]
            directory = self.root / family / kind
        row, index = self.row_frame(meta, clip, seconds, one_shot=one_shot)
        path = str(directory / row / f'{index:03d}.png')
        return self._image(path), meta['rows'][row], path

    def tile(self, canvas, key, pos, size=(16,16), *, dark=False):
        src = self.tiles[key]
        if size == src.get_size() and not dark:
            canvas.blit(src, pos)
            return
        target = pygame.transform.scale(src, (round(size[0]),round(size[1])))
        if dark:
            target = target.copy()
            target.fill((170,158,193,255), special_flags=pygame.BLEND_RGBA_MULT)
        canvas.blit(target, (round(pos[0]),round(pos[1])))

    def draw_construction(self, canvas, kind, clip, seconds, pos, size, *, flip_y=False):
        if kind not in self.construction:
            raise KeyError(kind)
        _src, _meta, path = self.frame('construction',kind,clip,seconds)
        w,h=max(1,round(size[0])),max(1,round(size[1]))
        image = self._scaled(path,w,h,False,False)
        if flip_y:
            image=pygame.transform.flip(image,False,True)
        canvas.blit(image,(round(pos[0]),round(pos[1])))

    def draw_cosmic(self, canvas, feet, clip, seconds, *, facing=1, zoom=1.0, one_shot=False):
        original, _data, path = self.frame('cosmic', None, clip, seconds, one_shot=one_shot)
        # Source body is 84 pixels high (28 logical px at 3x). World grown
        # Mary-O is 62 px high. Extra headroom holds wings and effects.
        scale = 62 / 84 * zoom
        w,h = original.get_size()
        img = self._scaled(path, round(w*scale), round(h*scale), facing<0, True)
        fx,fy = self.cosmic['feet']
        if facing<0:
            fx = w - fx
        canvas.blit(img,(round(feet[0]-fx*scale),round(feet[1]-fy*scale)))

    def draw_prop(self, canvas, kind, clip, seconds, center_bottom, *, width=40, height=40):
        _src, _data, path = self.frame('props', kind, clip, seconds)
        # Props are authored on 96x96 frames. The artwork is bottom-centred
        # inside that canvas; preserve the intended position as it animates.
        img = self._scaled(path, round(width),round(height), False, True)
        canvas.blit(img,(round(center_bottom[0]-width/2),round(center_bottom[1]-height)))

    def draw_fire_orb(self, canvas, center, seconds, *, diameter=30):
        # Source-painted FireOrb asset; its animation and hitbox share the
        # position sampled by game._hazards_update at the same 60 Hz tick.
        _image, _data, path = self.frame('construction', 'fire_orb', 'idle', seconds)
        sprite = self._scaled(path, round(diameter), round(diameter), False, True)
        canvas.blit(sprite, (round(center[0] - diameter/2), round(center[1] - diameter/2)))

    def draw_enemy_projectile(self, canvas, kind, center, seconds):
        """The authored Void Orb and Laden Swallow coconut, no star placeholder."""
        diameter = {'void_orb': 24, 'coconut': 21}[kind]
        _src, _meta, path = self.frame('construction', kind, 'idle', seconds)
        sprite = self._scaled(path, diameter, diameter, False, True)
        canvas.blit(sprite, (round(center[0]-diameter/2),
                             round(center[1]-diameter/2)))

    def draw_plant(self, canvas, enemy, feet, seconds):
        if enemy.phase == 'hidden':
            return
        src, data, path = self.frame('enemies', 'snake_plant', 'idle', seconds)
        bbox = data['bbox']
        anchor = self.enemies['snake_plant']['anchor']
        # `feet` are screen coordinates; convert the mouth to screen space
        # with the same camera offset used for every other enemy.
        mouth_y = ((feet[1] - (enemy.y + enemy.h)) + enemy.pot_y
                   if enemy.pot_y is not None else feet[1])
        left, top, w, h = plant_placement(src.get_width(), src.get_height(),
                                          bbox[1], anchor[0], anchor[1],
                                          feet[0], mouth_y,
                                          enemy.exposure, enemy.h)
        sprite = self._scaled(path, round(w), round(h), enemy.facing < 0, True)
        # The same pipe mouth bounds both sprite emergence and hitbox logic.
        # The painter draws the pipe in a later foreground pass, while this
        # clip prevents the root from leaking through adjacent world tiles.
        if enemy.pot_y is not None:
            old = canvas.get_clip()
            canvas.set_clip(old.clip(pygame.Rect(0, 0, canvas.get_width(),
                                                  max(0, round(mouth_y)))))
            canvas.blit(sprite, (round(left), round(top)))
            canvas.set_clip(old)
        else:
            canvas.blit(sprite, (round(left), round(top)))

    def draw_enemy(self, canvas, enemy, feet, seconds):
        kind = enemy.kind
        if kind == 'laden_swallow':
            filename = str(self.root / 'birds' / 'african_swallow.png')
            src = self._image(filename)
            bbox = src.get_bounding_rect()
            scale = (enemy.h * 1.25) / max(1, bbox.h)
            w,h=src.get_size()
            w,h=round(w*scale),round(h*scale)
            image=self._scaled(filename,w,h,enemy.facing<0,True)
            # The authored SVG centers the bird on its own canvas.
            canvas.blit(image,(round(feet[0]-w*.5),round(feet[1]-src.get_height()*scale*.82)))
            return True
        if kind not in self.enemies:
            return False
        if kind == 'snake_plant':
            self.draw_plant(canvas, enemy, feet, seconds)
            return True
        clip = 'walk'
        if kind == 'solid_snake':
            clip = ('boxed_idle' if enemy.phase == 'shell' else
                    'boxed_idle' if enemy.phase == 'rolling' else 'walk')
        elif kind == 'void_lizard':
            clip = 'fire' if enemy.age % .95 < .23 else 'walk'
        elif kind.startswith('npc_snakes_on_a_'):
            clip = 'fly'
        src, data, path = self.frame('enemies', kind, clip, seconds)
        # A single union bbox is stored for each row, so the art cannot
        # wobble from arbitrary frame cropping. Source sprites use large
        # transparent canvases around the collision bodies.
        bbox = data['bbox'] or (0, 0, *src.get_size())
        bh = max(1, bbox[3] - bbox[1])
        if kind.startswith('npc_snakes_on_a_'):
            # The authored planes have broad wings and shallow hitboxes.
            # Their rendered union artwork should span the collision width.
            scale = enemy.w * 1.25 / max(1, bbox[2] - bbox[0])
        else:
            scale = (enemy.h * (1.1 if kind != 'void_lizard' else 1.35)) / bh
        w,h=src.get_size()
        image=self._scaled(path,round(w*scale),round(h*scale),enemy.facing<0,True)
        cx = (bbox[0]+bbox[2])*.5
        if enemy.facing<0: cx = w-cx
        # Ground line is the artist's full-frame bottom for snake/plant/star;
        # some idle frames include shadow beyond the collision box.
        # Flying planes are center anchored, while walkers sit on their feet.
        y = (feet[1] - enemy.h*.5 - (bbox[1]+bbox[3])*.5*scale
             if kind.startswith('npc_snakes_on_a_') else feet[1]-bbox[3]*scale)
        canvas.blit(image,(round(feet[0]-cx*scale), round(y)))
        return True
