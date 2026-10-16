# Lesson 9: One button, two meanings — and contact geometry

**Predict.** When Mary-O is small, what happens when you press and hold X?
When she has the fire power-up, does holding X repeatedly fire sparks? Why is
Shift different from X in the original Rust input bindings?

**Investigate.** Read `Keyboard.PRESETS`, `Keyboard.command()`, and
`Game.step()` in `app.py` and `game.py`. Run
`python -m pytest -q tests/test_controls.py tests/test_game_feel_pass2.py`.
The keyboard supplies a **level** (`run=True` while held) and a **press edge**
(`run_pressed=True` once) from the same key. Shift caps the movement axis but
does not supply the run or attack edge. If you are using the WASD preset,
replace X with J; the two meanings stay together.

**Modify.** Change the `WALK_THROTTLE` setting in `physics.py`, then change
`SHIFT_AXIS_CAP`, and predict which combinations of X and Shift change the
horizontal target speed. Compare the time taken to reach each target from
rest; `horizontal()` never teleports velocity. Put the values back and try
changing the spark's lifetime or its two-live-shot limit in `game.py`.

**Explain.** Why do fast taps need to be delivered to the next 60 Hz step,
while coyote time and jump buffering can remain zero? Why is it important to
compute the **first** wall or ceiling encountered, rather than stopping at
the first collider returned by the world query? What happens when a crouched
tall Mary-O runs through a passage with a ceiling exactly 32 pixels above
the floor?

**Stretch goal.** Add two closely spaced blocks to the contact lab in
`test_game_feel_pass2.py`. Write a test that proves only the closest is bonked
by an upward jump, regardless of the order in which they are stored in the
level. Then change the block layout to include a one-way platform that Mary-O
can jump through and land on without colliding with its underside.
