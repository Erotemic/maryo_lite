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
and meet the robot at the end.

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
| F5 | Skip to next authored room (classroom convenience) |
| Esc | Pause |

Alternatively, start with `python main.py --controls wasd`: A/D move,
W/S pipe directions, **Space** jump, **J** shoot, **L** cosmic, Shift walk.

### Pose and animation lab

Press `F2`, or start directly using `python main.py --pose-lab`.

- Up/Down: small, tall, fire, cosmic forms.
- Left/Right: select the clip. All exported gameplay clips are available,
  including walking, skidding, jumping, climbing, swimming, crouching, shooting,
  and front-facing death (as supported by each form).
- There are also interactive previews of **grow, shrink, fire transform,
  cosmic entry, and cosmic exit**.
- Space: pause/resume; R: restart preview; Tab: choose a body joint;
  `[` and `]`: offset the joint angle by five degrees; Backspace: reset edits.

The character is **not one sprite sheet**. Each visible component comes from
an SVG image, with separate joint translations, rotations, mirror state,
vertical squash/stretch, and layered compositing. Try changing a pose in the
tracked JSON keyframes and regenerating its parts if the SVG itself changes.

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
| `src/mary_o_lite/graphics.py` | Pygame scenery, SVG articulated character, effects, pose lab |
| `assets/svg/` | **Tracked** SVG source of Mary-O and the castle robot |
| `assets/rigs/` | **Tracked** source rig/keyframe JSON for three paper-doll forms |
| `assets/worlds/` | **Tracked** LDtk world definition |
| `tools/build_assets.py` | Extracts each SVG part; writes pivot metadata and robot thumbnail |
| `tools/compose_audio.py` | Generates five original chiptune loops and synthesized effects |
| `assets/generated/` | **Untracked, Git-ignored** PNG/WAV cache, recreated automatically |
| `lessons/` | Predict → Investigate → Modify → Explain guided exercises |

### Git and binaries

**Do not commit generated assets.** The `.gitignore` excludes
`assets/generated/` as well as `*.png`, `*.wav`, `*.mp3`, `*.jpg`, `*.ogg`,
fonts, compiled files, and other binary formats. All runtime character and
robot images are regenerated from tracked SVG and JSON, and all music/SFX
are rendered from readable Python note tables and signal functions.

```bash
python tools/build_assets.py
# These cache files should not appear in git status:
git status --short
```

The repository source archive also intentionally omits the generated files.

## Scope and limitations

This is a **teaching-oriented approximation** of Ambition Mary-O, not a bitwise
port. The original level collision grid, character source art and pose
samples, and baseline movement constants are preserved. Enemy state machines,
rendering, camera transitions, blocks, special attacks, and castle choreography
are simplified. Scenery is drawn procedurally instead of reproducing the
engine's full sprite generation stack; the cosmic form reuses the fire-form
paper doll with software-drawn wings, halo, and star effects rather than the
original shader and sprite pipeline. Climb and swim poses can be inspected in
the pose lab, but full climb/swim world mechanics are not implemented.

The headless physics and content tests run without a display. Real Pygame
performance and game-feel require playing locally, particularly in later,
more complex rooms. See [port notes](docs/PORT_NOTES.md) for coverage and
known gaps, and [the teacher guide](docs/TEACHER_GUIDE.md) for class projects.

## Attribution and license

Original Mary-O world, SVGs, and pose data are adapted from Ambition;
original source paths are listed in [NOTICE](NOTICE). Distributed under
[Apache-2.0](LICENSE). Generated chiptune audio is original to this project.
