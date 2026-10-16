# Teacher guide: Mary-O Lite

**Audience:** beginners who know Python functions and basic classes; suitable
for students moving from console games to frame-based games.

## Teaching pattern

Each lesson uses four stages:

1. **Predict.** Tell students what will happen from the current rule.
2. **Investigate.** Read the smallest function involved and run a test or game.
3. **Modify.** Change exactly one value or behavior in a new branch.
4. **Explain.** Compare the observed result with the prediction.

Students begin with `python main.py`. Running `python main.py --headless` can
explain why a game simulation still works without images or audio. The
art/animation inspector (`F2`) is useful when introducing transformation
hierarchies, rotations, keyframes, pivot points, and interpolation.

## Recommended workshop sequence

| Lesson | Main idea | Edit location |
|---|---|---|
| `lessons/01_running_and_jump.md` | Velocity, acceleration, jump bands | `physics.py` |
| `lessons/02_blocks_and_forms.md` | Stateful world objects and rewards | `game.py` |
| `lessons/03_pose_transforms.md` | Joint pivots, interpolation, squash/stretch | `poses.py`, `assets/rigs` |
| `lessons/04_source_to_assets.md` | SVG to cached PNG, reproducible asset builds | `tools/build_assets.py` |
| `lessons/05_enemies_and_events.md` | Enemy state machines, events and audio | `game.py`, `tools/compose_audio.py` |

Students can run `python -m pytest -q` after each exercise. Do not make a
student's gameplay change depend on reinstalling the Rust engine or working
with large generated sprite sheets. Keep source SVG, rig JSON, and source
music notes under version control; do not check in PNG/WAV outputs.

## Practical setup

For classroom machines without internet, preinstall a Python environment with
`pygame-ce`, `Pillow`, and `CairoSVG` and run the asset builder once per device.
A network connection is only needed for the first-run dependency install,
not to play or regenerate assets once the packages are available.

The game intentionally lacks networking, rollback, elaborate validation,
and shaders. Students should implement a new behavior in a small Python
function before considering abstractions that span multiple systems.
