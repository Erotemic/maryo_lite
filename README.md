# Mary-O Lite

**An educational Pygame remake of Ambition's Mary-O.** The game is a new,
standalone Python repository. It uses the original Mary-O vector paper doll,
authored poses, and LDtk level geometry, while replacing the Rust game engine
with a small, understandable 60 Hz simulator and a Pygame renderer.

Mary-O can run, accelerate, skid, and jump through the original Worlds 1 and 2.
Bonk power blocks to transform from **small** to **tall** to **fire**, shoot
sparks in fire form, and toggle **cosmic** form for fast movement and repeated
midair jumps. Ride moving platforms, discover warp pipes, stomp enemies,
collect coins, avoid hazards, hit the castle switch, defeat the Void Lizard,
and meet the robot at the end. The goal is now to share *more* of the
source artwork with Ambition without introducing its runtime or shader stack.

## Play

Requires **Python 3.10+**. From the extracted source directory:

```bash
python main.py
```

If graphical dependencies are missing, the launcher creates a project-local
`.venv` and installs Pygame, Pillow, and CairoSVG on the first run (internet
access is needed the first time). It then rasterizes the SVGs and composes the
chiptune music automatically into Git-ignored files. The next launch uses the
cached environment and binary assets.

The first asset build paints hundreds of sprite frames from the actual Ambition
Python generators. It can be CPU-intensive; a partially interrupted build is
resumable, and subsequent launches reuse the source-stamped cache.

If your system needs the Cairo shared library, on Ubuntu use
`sudo apt install libcairo2`. No Rust toolchain, LDtk app, or DAW is needed
to *play* the imported levels.

**Controls (default: Arrow keys)**

| Key | Action |
|---|---|
| Left / Right | Accelerate, turn, skid |
| Z | Jump; release early for a shorter jump |
| X | Shoot a spark when wearing the fire or cosmic form |
| D | Toggle cosmic form; watch the entry / exit sequences |
| Down | Crouch when tall; descend an upward-facing pipe |
| Up | Enter an upward-facing exit from below |
| Shift | Walk instead of run |
| R | Restart current level |
| F1 | Toggle the on-screen controls |
| F2 | Open/close the rig and animation inspector |
| F3 | Toggle collision and joint debug overlays |
| F5 | Go to next authored room (classroom convenience) |
| F6 | Return to previous authored course (classroom convenience) |
| Esc | Pause |

**Returning to earlier levels:** Walk left toward the starting lane of any
course after 1-1, or use `F6` at any point. The camera pans in both
directions. Cross the old finish line from the right without triggering
its cinematic, and keep defeated enemies, spent blocks, pickups, score, coins,
form, and the room clock. On a completed course, moving right through the
finish area advances again without a replay. `R` resets only the current
course; `F5`/`F6` allow jumping between neighboring courses for lessons.

Alternatively, start with `python main.py --controls wasd`: A/D move,
W/S pipe directions, **Space** jump, **J** shoot, **L** cosmic, Shift walk.

### Pose and animation lab

Press `F2`, or start directly using `python main.py --pose-lab`.

- Up/Down: small, tall, fire, cosmic forms.
- Left/Right: select the clip. All exported gameplay clips are available,
  including walking, skidding, jumping, climbing, swimming, crouching, shooting,
  and front-facing death (as supported by each form).
- The **cosmic form uses the original Ambition source painter**. Its fourteen
  clips include the full 36-frame cosmic transformation and 18-frame exit, plus
  idle, walk, skid, jump, fall, climb, swim, shoot, and crouching poses. The
  painter includes the starfield gown, long hair, wings, ring, and crown star.
- Space pauses; R restarts a preview. For regular SVG-part rigs, Tab selects a
  joint; `[` / `]` adjust its angle, and Backspace resets offsets. Cosmic
  animation is edited as Python source in
  `tools/ambition_art/cosmic_animation.py`, not through joint sliders.

The character is **not one sprite sheet**. Each visible component comes from
an SVG image, with separate joint translations, rotations, mirror state,
vertical squash/stretch, and layered compositing. Try changing a pose in the tracked JSON keyframes and regenerating its
parts if the SVG itself changes. Cosmic uses the upstream Python shape painter
because wings, hair, glowing stars and the gown are not SVG-paper-doll joints.
All its frames are generated from tracked `.py` sources, with no shaders.

### Other useful commands

```bash
python main.py --list-levels
python main.py --room mary_o_1_4
python main.py --mute
python main.py --headless --ticks 600
python main.py --build-assets
python tools/build_assets.py --force
```

`--headless`, `--help`, and `--list-levels` work with standard Python even when
Pygame is absent. `--build-assets` requires Pillow and CairoSVG.

## Working on the code

For an explicit local development environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python main.py
```

There are eight main rooms (`mary_o_1_1` through `mary_o_2_4`) plus
`mary_o_warp`. They are loaded from the same **text** LDtk document as the
Ambition Mary-O game. To edit source level geometry, use LDtk or modify the
JSON carefully. To edit keyframes, see `assets/rigs/*.json`.

| Location | Responsibility |
|---|---|
| `main.py` | Zero-configuration launcher; does not require an editable install |
| `src/mary_o_lite/app.py` | Input handling, display loop, scene selection, pause |
| `src/mary_o_lite/game.py` | Forms, blocks, enemies, pipes, goal sequence, fixed-step game rules |
| `src/mary_o_lite/physics.py` | Classic horizontal acceleration and jump law |
| `src/mary_o_lite/content.py` | LDtk parsing; converts original map into simple room objects |
| `src/mary_o_lite/poses.py` | Per-bone frame interpolation; has no Pygame dependency |
| `src/mary_o_lite/motion.py` | Source-authored Fire Bar orbits, lifts, and plant timing without Pygame |
| `src/mary_o_lite/graphics.py` | Pygame camera and scene composition, reversible scrolling, pose lab |
| `src/mary_o_lite/art_assets.py` | Render-time lookup and timing for the generated Ambition art |
| `tools/ambition_art/` | **Tracked original/adapted Ambition Python painters** for cosmic, enemies, 17 tiles, props, and construction |
| `assets/svg/` | **Tracked** SVG source of Mary-O and the castle robot |
| `assets/rigs/` | **Tracked** source rig/keyframe JSON for three paper-doll forms |
| `assets/worlds/` | **Tracked** LDtk world definition |
| `tools/build_assets.py` | Extracts SVG parts and rebuilds/resumes all Ambition source-painted sprites |
| `tools/compose_audio.py` | Generates five original chiptune loops and synthesized effects |
| `tools/preview_fidelity.py` | Pillow contact sheets for plant/pipe alignment and Fire Bar orbits |
| `assets/generated/` | **Untracked, Git-ignored** PNG/WAV cache, recreated automatically |
| `lessons/` | Predict → Investigate → Modify → Explain guided exercises |

### Git and binaries

**Do not commit generated assets.** The `.gitignore` excludes
`assets/generated/` as well as `*.png`, `*.wav`, `*.mp3`, `*.jpg`, `*.ogg`,
fonts, compiled files, and other binary formats. All runtime character and
robot images are regenerated from tracked SVG and JSON, and all music/SFX
are rendered from readable Python note tables and signal functions. The
original source painters also regenerate the **17 Mary-O terrain/block tiles,
animated powerups, five enemy families, copper pipe pieces, waving goal flag,
clockwork lifts, lava, castle gate and switch, and fire projectiles**. Two
original swallow SVGs are rasterized during the build.

```bash
python tools/build_assets.py
# These cache files should not appear in git status:
git status --short
```

The repository source archive also intentionally omits the generated files.

## Scope and limitations

This is a **teaching-oriented port**, not a bitwise reproduction of Ambition's
Rust engine. It uses the original Mary-O world collision grid, source-painted
cosmic form and both cosmic transition sequences, original tiles, construction
pieces, animated pickups and creatures, 76 authored moving Fire Bar orbs,
39 moving lifts, and original SVG-part poses for the
other forms. Art output can be reproduced without Ambition installed.

The Fire Bars rotate along their LDtk paths and hit where they appear;
Snake Plants grow from behind the pipe mouth instead of being stretched over
it. Original artwork for the two flying snake varieties, swallow coconuts
and Void Lizard projectiles is also generated from source. All moving lifts
and ferries follow the level-authored paths, not generic oscillation.

Remaining differences: the enemy state machines and some mechanics are
simplified, the scenery parallax is still procedurally composed, the music and
SFX are new generated chiptunes rather than Ambition's adaptive audio, and
special shader effects are omitted. Climb/swim clips are viewable but full
climbing and swimming world physics are not implemented. Reversible scrolling
and persistent revisits deliberately differ from Ambition's forward-only
classic course camera.

The Pygame window still needs a local graphical playtest for character
alignment, animated lift collisions and overall movement feel. See [the source-fidelity audit](docs/FIDELITY_AUDIT.md),
[port notes](docs/PORT_NOTES.md), and
[the teacher guide](docs/TEACHER_GUIDE.md). You can inspect the source art
without Pygame using `python tools/preview_fidelity.py`, which creates two
ignored contact sheets in `assets/generated/`.

## Attribution and license

Original Mary-O world, SVGs, and pose data are adapted from Ambition;
original source paths are listed in [NOTICE](NOTICE). Distributed under
[Apache-2.0](LICENSE). Generated chiptune audio is original to this project.
