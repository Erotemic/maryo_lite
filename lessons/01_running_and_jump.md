# Lesson 1: running speed changes a jump

**Predict.** Which jump gets the most height: Mary-O at rest, walking, or
running at full speed? Does holding the jump key longer matter?

**Investigate.** Open `src/mary_o_lite/physics.py` and find
`jump_velocity()` and `gravity_step()`. There are four jump-launch bands,
and the first part of a held jump uses lower upward gravity. Run
`python -m pytest -q tests/test_physics.py`.

**Modify.** Increase the highest-speed jump bonus by 20. Run the game with
`python main.py`; run and jump over the first level. Try a short press and a
long press of Z, then put the bonus back and change the run acceleration.

**Explain.** Why is `horizontal()` separate from `jump_velocity()`? When
can a speed band change even though the jump button stays the same?
