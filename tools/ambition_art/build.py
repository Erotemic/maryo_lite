"""Regenerate selected Ambition Mary-O art directly from tracked Python/SVG sources.

The upstream geometry/paint/pose tables are in this package. No binary art
assets are distributed or committed; every sprite frame is reproducible from
these Python sources (and the SVGs copied to assets/svg).
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
from pathlib import Path

from PIL import Image

from . import cosmic_animation, cosmic_art, props, tiles, construction, spark, lift
from . import ai_slop, solid_snake, snake_plant, void_star, void_lizard
from . import snakes_on_planes, fire_orb, coconut

SOURCES = Path(__file__).resolve().parent
ROOT = SOURCES.parents[1]
ASSETS = ROOT / 'assets'
OUTPUT = ASSETS / 'generated' / 'ambition'

ENEMIES = {name: mod for name, mod in (
    ('ai_slop', ai_slop), ('solid_snake', solid_snake),
    ('snake_plant', snake_plant), ('void_star', void_star),
    ('void_lizard', void_lizard),
)}


def _stamp() -> str:
    digest = hashlib.sha256()
    for path in sorted(SOURCES.glob('*.py')) + sorted((ASSETS / 'svg').glob('*swallow.svg')):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _frames(rows, render, folder: Path) -> dict:
    """Save source-painted RGBA frames and a stable, union animation bbox."""
    manifest = {}
    for name, count, delay in rows:
        directory = folder / name
        directory.mkdir(parents=True, exist_ok=True)
        union = None
        first_size = None
        for i in range(count):
            file = directory / f'{i:03d}.png'
            # First launch can be interrupted on a slow CPU. Source-stamped
            # partial builds resume without repainting hundreds of frames.
            img = None
            if file.is_file():
                try:
                    with Image.open(file) as cached:
                        cached.load()  # A killed build may leave a truncated PNG.
                        img = cached.convert('RGBA')
                except (OSError, ValueError):
                    file.unlink(missing_ok=True)
            if img is None:
                img = render(name, i, count)
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                # Never expose half-written frames to subsequent builds.
                temp = file.with_name(file.name + '.tmp')
                img.save(temp, format='PNG', optimize=True)
                temp.replace(file)
            if first_size is None:
                first_size = img.size
            if img.size != first_size:
                raise ValueError(f'{folder.name}/{name}: frame size differs')
            bounds = img.getbbox()
            if bounds:
                if union is None:
                    union = bounds
                else:
                    union = (min(union[0], bounds[0]), min(union[1], bounds[1]),
                             max(union[2], bounds[2]), max(union[3], bounds[3]))
        manifest[name] = dict(count=count, delay_ms=delay, bbox=union,
                              frame_size=first_size)
    return manifest


def _build_cosmic():
    stage = cosmic_animation.STAGE
    transform = cosmic_animation.transformation()
    leave = cosmic_animation.detransformation()

    def painter(name, index, count):
        if name == 'transform':
            look = transform[index]
        elif name == cosmic_animation.LEAVE_ROW:
            look = leave[index]
        else:
            look = cosmic_animation.look_for(name, index)
        return cosmic_art.frame(stage, look)

    folder = OUTPUT / 'cosmic'
    rows = _frames(cosmic_animation.ROWS, painter, folder)
    (folder / 'manifest.json').write_text(json.dumps({
        'source': 'Ambition mary_o_v2_cosmic',
        'origin': 'cosmic_art.py / cosmic_animation.py',
        'rows': rows,
        'feet': stage.feet_px,
        'nominal_body_size': (cosmic_art.BODY_W * cosmic_art.S,
                              cosmic_art.BODY_H * cosmic_art.S),
    }, indent=2) + '\n')


def _build_tiles():
    directory = OUTPUT / 'tiles'
    directory.mkdir(exist_ok=True, parents=True)
    for tile in tiles.TILES:
        tiles._tile_image(tile.key).save(directory / (tile.key + '.png'), optimize=True)
    (directory / 'manifest.json').write_text(json.dumps({
        'source': 'Ambition super_mary_o_tileset',
        'tile_size': tiles.TILE,
        'keys': [spec.key for spec in tiles.TILES],
    }, indent=2) + '\n')


def _build_props():
    for spec in props.SPECS.values():
        folder = OUTPUT / 'props' / spec.target_name
        rows = _frames(spec.rows, spec.renderer, folder)
        (folder / 'manifest.json').write_text(json.dumps({
            'source': 'Ambition super_mary_o_props',
            'rows': rows,
        }, indent=2) + '\n')


def _build_enemies():
    for name, module in ENEMIES.items():
        folder = OUTPUT / 'enemies' / name
        rows = _frames(module.ROWS, module._render_frame, folder)
        extra = {'anchor': snake_plant.ROOT} if name == 'snake_plant' else {}
        (folder / 'manifest.json').write_text(json.dumps({
            'source': f'Ambition {name}', 'rows': rows, **extra,
        }, indent=2) + '\n')
    for kind, spec in (
        ('npc_snakes_on_a_paper_plane', snakes_on_planes.PAPER_SPEC),
        ('npc_snakes_on_a_cartesian_plane', snakes_on_planes.CARTESIAN_SPEC),
    ):
        folder = OUTPUT / 'enemies' / kind
        rows = _frames(snakes_on_planes.ROWS,
                       lambda row, i, n: snakes_on_planes.render_frame(spec, row, i, n),
                       folder)
        (folder / 'manifest.json').write_text(json.dumps({
            'source': f'Ambition {spec.target_name}', 'rows': rows,
        }, indent=2) + '\n')




def _build_construction():
    for spec in construction.SPECS.values():
        folder = OUTPUT / 'construction' / spec.target_name
        rows = _frames(spec.rows, spec.renderer, folder)
        (folder / 'manifest.json').write_text(json.dumps({
            'source': 'Ambition super_mary_o_construction',
            'rows': rows, 'original_frame_size': spec.frame_size,
        }, indent=2) + '\n')
    for kind, module, frame_fn, frames, delay in (
        ('super_mary_o_spark', spark, spark._spark_frame, spark.FRAMES, 60),
        ('super_mary_o_lift', lift, lift._lift_frame, lift.FRAMES, 110),
        ('fire_orb', fire_orb, fire_orb._render_frame, 8, 75),
        ('void_orb', fire_orb, fire_orb.render_void_orb, 1, 150),
        ('coconut', coconut, coconut._render_frame, 1, 200),
    ):
        folder = OUTPUT / 'construction' / kind
        rows = _frames([('idle', frames, delay)], frame_fn, folder)
        (folder / 'manifest.json').write_text(json.dumps({
            'source': 'Ambition ' + kind, 'rows': rows,
        }, indent=2) + '\n')

def _build_birds():
    import cairosvg
    directory = OUTPUT / 'birds'
    directory.mkdir(parents=True, exist_ok=True)
    for species in ('european_swallow', 'african_swallow'):
        source = ASSETS / 'svg' / (species + '.svg')
        data = cairosvg.svg2png(bytestring=source.read_bytes(),
                                output_width=192, output_height=192)
        image = Image.open(io.BytesIO(data)).convert('RGBA')
        if image.getbbox() is None:
            raise ValueError(f'Empty SVG {species}')
        image.save(directory / (species + '.png'), optimize=True)


def generate(force: bool = False) -> bool:
    """Build all source art only when input sources change. True iff rebuilt."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    marker = OUTPUT / 'manifest.json'
    stamp = _stamp()
    # A representative from every source family prevents accepting incomplete
    # outputs after a cancelled first build.
    expected = [OUTPUT / 'cosmic' / 'transform' / '035.png',
                OUTPUT / 'cosmic' / 'shrink' / '017.png',
                OUTPUT / 'tiles' / 'ground_top.png',
                OUTPUT / 'props' / 'super_mary_o_coin' / 'spin' / '005.png',
                OUTPUT / 'enemies' / 'void_lizard' / 'walk' / '007.png',
                OUTPUT / 'enemies' / 'solid_snake' / 'walk' / '007.png',
                OUTPUT / 'enemies' / 'ai_slop' / 'walk' / '007.png',
                OUTPUT / 'enemies' / 'npc_snakes_on_a_paper_plane' / 'fly' / '007.png',
                OUTPUT / 'enemies' / 'npc_snakes_on_a_cartesian_plane' / 'fly' / '007.png',
                OUTPUT / 'construction' / 'fire_orb' / 'idle' / '007.png',
                OUTPUT / 'construction' / 'void_orb' / 'idle' / '000.png',
                OUTPUT / 'construction' / 'coconut' / 'idle' / '000.png',
                OUTPUT / 'birds' / 'european_swallow.png',
                OUTPUT / 'construction' / 'super_mary_o_lift' / 'idle' / '003.png',
                OUTPUT / 'construction' / 'super_mary_o_flag' / 'idle' / '003.png']
    if not force and marker.exists() and all(p.exists() for p in expected):
        try:
            if json.loads(marker.read_text())['stamp'] == stamp:
                return False
        except (OSError, KeyError, ValueError):
            pass
    partial = OUTPUT / '.building.json'
    # A cache is reused ONLY if the source fingerprint matches the previous
    # completed or partial build; changed Python/SVG inputs invalidate it.
    previous = None
    for candidate in (partial, marker):
        if candidate.exists():
            try:
                previous = json.loads(candidate.read_text())['stamp']
                break
            except (OSError, KeyError, ValueError):
                pass
    if force or (previous is not None and previous != stamp):
        shutil.rmtree(OUTPUT)
        OUTPUT.mkdir(parents=True, exist_ok=True)
    partial.write_text(json.dumps({'stamp': stamp}) + '\n')
    _build_cosmic()
    _build_tiles()
    _build_props()
    _build_enemies()
    _build_birds()
    _build_construction()
    marker.write_text(json.dumps({
        'stamp': stamp,
        'sources': ['Ambition source Python painters for tiles, props, enemies, cosmic',
                    'Ambition swallow SVGs'],
        'families': ['cosmic', 'tiles', 'props', 'enemies', 'birds', 'construction'],
    }, indent=2) + '\n')
    partial.unlink(missing_ok=True)
    return True
