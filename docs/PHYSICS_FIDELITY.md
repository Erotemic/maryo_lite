# Physics and game-feel port: Mary-O Lite

These changes compare Lite against the supplied Ambition source snapshot, not
against a commercial platformer's physics. The goal is close behavior with
readable Python, not copying the complete Bevy collision engine.

## Shared, source-backed movement rules

The authoritative Rust rows are in
`game/ambition_demo_mary_o/assets/data/character_catalog.ron` and
`assets/data/mary_o_rules.ron`; the input policy is in
`game/ambition_demo_mary_o/src/movement.rs`.

| Rule | Small / tall / fire | Cosmic |
|---|---:|---:|
| Default gait | Walk = 60% of cap (180 px/s) | Walk = 372 px/s |
| Run modifier held | 300 px/s | 620 px/s |
| Run/air acceleration | 393.75 px/s² | 1400 px/s² |
| Reverse on ground | 1500 px/s² | 3200 px/s² |
| Reverse in air | 900 px/s² | 2400 px/s² |
| Neutral ground coast | 393.75 px/s² | 1400 px/s² |
| Neutral air coast | 0 | 700 px/s² |
| Gravity | 2250 px/s² | 2250 px/s² |
| Terminal fall | 480 px/s | 300 px/s |
| Speed-band jump launches (classic) | 420, 435, 450, 480 px/s | From cosmic base speed |
| Jump held while rising faster than 240 px/s | 20% gravity | 20% gravity |
| Coyote time / jump buffer | 0 / 0 | 0 / 0 |

The previously inverted modifier caused all normal walking to reach 300 px/s
and Shift to cut the target to 180 px/s. Shift now increases the target speed,
without an immediate velocity snap; letting it go lets Mary-O decelerate.
For a fire/cosmic form the *press* edge on Shift also emits one spark, subject
to the 0.4-second shot cooldown. X remains a separate fire shortcut.

Jump release now latches the end of weak-gravity ascent for the rest of that
jump. Re-pressing Jump in the air without a fresh jump grant cannot resume
20%-gravity ascent.

## Collider geometry and posture

- Small body: 24 × 32 world pixels.
- Tall/fire/cosmic standing: 24 × 62 world pixels.
- Tall/fire/cosmic crouched: **24 × 32 world pixels**, equal to small Mary-O.
- Shrinking and growing preserve the **feet position**.
- First crouching requires ground contact. Keeping Down held retains crouch
  across ledges, including the `crouch_jump` animation while airborne.
- Releasing Down under a ceiling **does not stand through the solid**. The
  standing box is retried on subsequent ticks; exiting the low passage
  restores the full standing height.
- A power-up acquired under a ceiling grants the new form but starts it in a
  crouched 32-pixel box until expansion is safe.
- Crouch movement has a Lite-specific 90 px/s target cap to allow traversal
  through long low tunnels. Entering a crouch retains accumulated sliding
  momentum instead of stopping instantly.

The *equal-height crouch* requirement comes from Ambition's own
`powerups.rs::her_grown_crouch_fits_where_her_small_form_fits` regression.
The *carry crouch off ledges* behavior is described in the engine's
`body_mode/mechanics/mod.rs`. Lite's simplified crouch-walk throttle is not
claimed to be identical to the full Rust body-mode driver.

## Collision and animation corrections

- Enemy wall bounces flip both velocity and AI facing. They no longer drive
  back into the same wall each frame.
- Only actors already grounded on a platform can be carried by its displacement.
  Passing close to the platform during a fall no longer snaps the actor onto it.
- Platform carry checks solid walls and ceilings instead of moving Mary-O
  straight through them. This deliberately detaches when a lift is blocked.
- Hidden blocks become solid **when bonked and made visible**, not only when
  painted. Collision and drawing use the same `spent` state.
- Walking and crouch-walking frame progression follows actual ground distance:
  slow walk no longer animates at the same stepping cadence as full run.
- A normal 60+ ms render delay no longer silently drops half the simulation
  time: the main loop allows up to 150 ms of fixed-step catch-up per frame.

## How to validate

```bash
python -m pytest -q tests/test_movement_fidelity.py
python -m pytest -q
python main.py --headless --ticks 600
python main.py
```

`tests/test_movement_fidelity.py` constructs a small 60 Hz level with exactly
32 px of vertical clearance. It tests the *whole simulation* rather than just
asking whether a pose looks small. It also tests wall reversals, repeated
jump presses, walk/run wind-up, form transformations under a ceiling, and
moving-platform contact semantics.

## Remaining differences

This is not verified graphical/runtime parity with Ambition. The Rust engine
has a swept multi-body contact solver and full body modes, while Lite has a
single educational AABB solver and a simplified crouch-walk speed. Moving
platform corner-crush rules, precise sprite collision masks, enemy attack
phase timings, camera behavior, pipe choreography, and animation timing should
still be compared in an actual playtest. Climbing and swimming remain pose
lab animations rather than world locomotion. No artificial coyote time,
jump buffer, or instantaneous directional steering was added just for
convenience; those would contradict the source tuning.
