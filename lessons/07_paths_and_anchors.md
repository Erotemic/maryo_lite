# Lesson 7: A rotating Fire Bar and a Snake Plant in a pipe

**Question:** How can the *same* animation position drive what you see and
what collides with the player?

## Predict

Open `assets/worlds/mary_o.ldtk` and find a `DamageVolume` named
`fire_bar_orb_0`. It contains `path_points` and `path_speed`. Predict what
happens after one second and what would happen if you reversed the list of
points. Find a `MaryOPipe` under a `Snake Plant` and predict what should be
visible at 0%, 25%, 50%, 75% and 100% emergence.

## Investigate

Open `src/mary_o_lite/motion.py`. `loop_position()` traverses a closed
polygon at a constant distance per second; it does not use an arbitrary sine
wave. In `game.py`, `_hazards_update()` writes that result into the hazard's
world hitbox. `graphics.py` then draws the source FireOrb **at the hitbox**.

The plant uses `wanted_plant_out()` and `next_plant_out()` to interpolate a
scalar from 0 to 1. `plant_placement()` keeps the painter's authored root at
`(48,127)` aligned with the mouth. The pipe is drawn *in front* of the plant,
clipping hidden stalk segments.

Generate a contact sheet (no Pygame required):

```bash
python tools/preview_fidelity.py
```

The results go into `assets/generated/` and remain ignored by Git.

## Modify

Try changing `motion.py::ping_pong()` or Fire Bar path speeds in a copy of
the level data. Keep the render and collision calculations unified. Try
moving the plant anchor `root_y` by 15 units and see why its mouth
registration looks wrong, then restore the source value. Compare the pipe
body built from 16-pixel slices with a stretched full-height texture.

## Explain

Why is it helpful to put deterministic motion in a module that imports
neither Pygame nor the asset generator? Why does an animation require an
explicit root/pivot instead of just a bounding rectangle? What does a
one-way foreground clipping mask teach about layering in a platformer?

Run `python -m pytest -q tests/test_maryo_fidelity.py` after making changes.
