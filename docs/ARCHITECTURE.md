# Architecture: Mary-O Lite

The design keeps small concepts separate so a student can find a mechanic,
change it, and see one predictable consequence. It is not a miniature ECS.

## One simulation; three inputs

At each 60 Hz step:

1. `Keyboard.command()` translates held keys and new key presses into `Command`.
2. `Game.step(command)` updates a plain `Player`, enemy lists, items,
   projectiles, room objects, goals, and a list of one-frame events.
3. `Painter.frame(game, dt)` projects the world, interpolates body-part poses,
   and draws a screen. `Music.effects(game.events)` converts event kinds into
   chiptune sounds. Drawing and sound do not change the game simulation.

The physics and content code import no Pygame. Run `python main.py --headless`
to examine the rules without displaying images.

## Gameplay data

- `physics.py`: immutable classic and cosmic velocity values. The jump launch
  has four running-speed bands; releasing jump returns to full gravity.
- `game.py`: `Player`, `Enemy`, `Item`, `Spark`, and a single `Game`. Solids are
  axis-aligned boxes; movement checks X then Y. Tiles marked 2 are one-way.
- `content.py`: reads the source LDtk JSON file at launch into `Level` and
  `Thing` objects. No Rust runtime, prefab backend, or procedural validation
  framework is necessary to open these rooms.

`Game.load_room()` retains lives and coins across rooms, repopulates authored
enemies, resets spent blocks, and returns the player to the room spawn.

## Animations and transforms

Mary-O's body is a set of SVG elements bound to pose bones. The files under
`assets/rigs` contain a list of parts (SVG ids, drawing order, local pivot,
attached bone) and clips (keyframes per bone). Each bone state is:

```
[x, y, angle_degrees, vertical_scale, mirror]
```

`poses.sample_pose()` linearly interpolates numeric properties of adjacent
keyframes and selects the previous mirror flag. The renderer positions each
part by its pivot, mirrors if needed, vertically stretches or compresses it,
rotates it, and draws it in part Z-order. `Puppet.transform()` caches rotated
images for reusable poses; these cached pixels live only in memory.

`tools/build_assets.py` isolates the relevant XML nodes from the tracked SVG,
keeps their `<use>` references and parent transforms, and rasterizes cropped
individual PNG parts using CairoSVG/Pillow. It writes the matching adjusted
pivot locations to a JSON manifest in `assets/generated/`. Nothing in this
process needs Ambition installed, and its binary outputs are Git-ignored.

There are three paper-doll body geometries: small, tall, and fire, each with
side and front (death) views. Cosmic mode uses fire-body parts and separately
drawn wings and star effects. The growth and power transformation sequences
cross-fade the source rigs, while cosmic entry and exit use timed drawn
ornaments without shaders. The pose lab exposes these transitions and the
climb/swim clips (the latter do not yet have gameplay collision zones).

## Classroom changes that stay small

- Change `CLASSIC.max_run`, then watch how the four jump-speed thresholds feel.
- Change `Enemy` motion inside `_enemy_tick()`, then write a headless test.
- Add a block reward in `Game.bonk()` and use the existing `Item` type.
- Adjust a keyframe's arm or leg angle in tracked JSON and rerun the pose lab.
- Edit the `TRACKS` note lists and regenerate audio: no DAW required.

Do not add a scene graph, rollback, networking, shaders, Rust bindings, or
validation services to solve an exercise that can be explained with simple
Python functions.
