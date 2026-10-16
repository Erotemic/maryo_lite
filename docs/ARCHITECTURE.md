# Architecture: Mary-O Lite

The design keeps small concepts separate so a student can find a mechanic,
change it, and see one predictable consequence. It is not a miniature ECS.

## One simulation; three inputs

At each 60 Hz step:

1. `Keyboard.note_keydown()` retains very short button presses until the next
   simulation step, and `Keyboard.command()` translates held keys and press
   edges into `Command`. X supplies both a run *level* and a spark *edge*.
2. `Game.step(command)` updates a plain `Player`, enemy lists, items,
   projectiles, room objects, goals, and a list of one-frame events.
3. `Painter.frame(game, dt)` projects the world, interpolates body-part poses,
   and draws a screen. `Music.effects(game.events)` converts event kinds into
   chiptune sounds. Drawing and sound do not change the game simulation.

The physics and content code import no Pygame. Run `python main.py --headless`
to examine the rules without displaying images.

## Gameplay data

- `physics.py`: immutable classic and cosmic velocity values. Movement walks
  by default, runs while X (or the preset's modifier) is held, and accelerates
  toward a speed target. Shift caps the movement input axis at 0.5, as in the
  Rust input adapter. Four launch bands affect jump speed; releasing Jump
  ends weak-ascent gravity until the next jump.
- `game.py`: `Player`, `Enemy`, `Item`, `Spark`, and a single `Game`. Movement
  sweeps AABBs along X and then Y, resolves the first wall or floor crossed,
  and bonks only the first ceiling block contacted. Tile value 2 is one-way.
  Sparks and enemy bolts/coconuts have distinct gravity values; at most two
  player sparks can be flying simultaneously.
- `content.py`: reads the source LDtk JSON file at launch into `Level` and
  `Thing` objects. No Rust runtime, prefab backend, or procedural validation
  framework is necessary to open these rooms.

`Game.load_room()` retains global lives, score, coins, and form. When exiting a
course, it saves a `RoomSnapshot` of enemies, spent/broken blocks, pickups,
platforms, and the clock. Revisiting restores the snapshot. Returning from the
next room places Mary-O near the right goal area, with goal triggering
suppressed until she has crossed it from right to left. Leftward exits use the
reachable spawn lane because several source rooms have solid end walls.

The 24 x 32 small body and crouched grown body fit the same low passages.
Stand-up is blocked while any solid overlaps the taller 24 x 62 standing
box. A crouch may be carried into the air while Down remains held. The
source-backed tuning and Lite-specific simplifications are detailed in
[PHYSICS_FIDELITY.md](PHYSICS_FIDELITY.md).

The camera follows horizontally **in both directions**. `go_previous()` and
`go_next()` support classroom shortcuts and normal edge travel; they do not
change the fixed-step simulation's timing or collision rules.

When Mary-O loses her last life, `Game.game_over` blocks input and course
travel until `R` invokes `Game.restart_session()`. The body stays motionless
through the 3.2-second death interlude while the death animation advances.

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

There are three normal paper-doll body geometries: small, tall, and fire,
each with side and front views. **Cosmic is the real, independent source-painted
Ambition form**, using editable Python pose tables and an RGBA painter in
`tools/ambition_art/`. It supplies the source night-sky gown, hair, wings,
planetary ring and crown, rather than compositing effects onto the fire puppet.
Its fourteen animated rows include 36 entry and 18 exit frames. Those are
rasterized once to Git-ignored caches and selected with their authored timing.
No shader or Rust compiler is required.

Other copied/adapted source painters create 17 terrain/block tiles, five enemy
families, animated pickups, copper pipes, castle goal pieces, the clockwork
lift, lava and spark projectiles. `SourceArt` in `art_assets.py` loads their
manifests and caches scaled surfaces. The Python animation tables, not
pre-rendered PNGs, are the authoritative sources. A source hash invalidates
the cache, and atomic writes let a canceled first build resume.

The pose lab supports joint manipulation for SVG-part bodies. For Cosmic,
edit the source painter or its animation tables and rebuild with
`python tools/build_assets.py --force`; the inspector previews every clip,
including transformations and climb/swim poses.

## Classroom changes that stay small

- Change `CLASSIC.max_run`, then watch how the four jump-speed thresholds feel.
- Change `Enemy` motion inside `_enemy_tick()`, then write a headless test.
- Add a block reward in `Game.bonk()` and use the existing `Item` type.
- Adjust a keyframe's arm or leg angle in tracked JSON and rerun the pose lab.
- Edit the `TRACKS` note lists and regenerate audio: no DAW required.

Do not add a scene graph, rollback, networking, shaders, Rust bindings, or
validation services to solve an exercise that can be explained with simple
Python functions.
