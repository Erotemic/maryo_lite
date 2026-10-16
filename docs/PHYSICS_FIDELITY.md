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
| Run modifier held (X default / J WASD) | 300 px/s | 620 px/s |
| Shift precision layer (without run) | 90 px/s | 186 px/s |
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

**Corrected binding:** The Rust `ArrowsZxc` preset assigns the Modifier slot
to `KeyX`, not Shift. Mary-O reads holding X as run and its new press as spark
when armed. The `WasdJkl` modifier is `KeyJ`. Shift is the separate
`ShiftLayer`, which halves the movement-axis magnitude before Mary-O applies
her 0.6 walk throttle. Holding X reaches 300 px/s, neither gives 180,
Shift alone gives 90, and Shift+X gives 150. Releasing X decelerates naturally.
The spark's 0.4-second refire and two-live-shot cap gate the press edge;
holding X does not repeatedly fire.

The earlier overlay mistakenly used Shift as run and X as a separate attack.
The keyboard adapter now saves KEYDOWN edges from very short taps until the
next simulation step; there is still **no gameplay coyote time or jump buffer**.

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
- The X/Y swept solver selects the nearest wall, floor, or ceiling, rather
  than whichever colliding tile is iterated first. Only the first ceiling
  block bonks, and one-way platforms only support downward contact from above.
- Sparks start horizontally from the authored hand offset (0.5855, -0.0762
  in body-height units), fall at 900 px/s², bounce twice, expire after 1.5
  seconds, and allow at most two live player shots. Source Void Lizard orbs
  have zero gravity (170 px/s); swallow coconuts start at 30 px/s with
  760 px/s² gravity and no bounce. Exact projectile contact details remain
  simplified. A just-kicked snake shell has 0.25 s of player-contact grace.
- Walking and crouch-walking frame progression follows actual ground distance:
  slow walk no longer animates at the same stepping cadence as full run.
- A normal 60+ ms render delay no longer silently drops half the simulation
  time: the main loop allows up to 150 ms of fixed-step catch-up per frame.
- Source `room_rules.ron` sets the death interlude to **3.2 seconds**. Lite
  now stops the body and plays the death pose for that interval, before replaying
  the course. Lives stop at zero and R restarts a new session; the latter is a
  simple Lite game-over policy, not a full port of the Rust roster lifecycle.
  The authored 400-second timer now triggers death on expiration.

## How to validate

```bash
python -m pytest -q tests/test_movement_fidelity.py
python -m pytest -q tests/test_game_feel_pass2.py
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
