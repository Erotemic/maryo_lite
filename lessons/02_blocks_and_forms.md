# Lesson 2: a block has memory

**Predict.** What happens if Mary-O hits the same question block twice? What
if she is already wearing the tall form when a block grants a wand?

**Investigate.** Read `Game.bonk()`, `_collect()`, and `_change_form()` in
`src/mary_o_lite/game.py`. Look for `spent`, `broken`, and `Item.kind`. Run
`python -m pytest -q tests/test_game.py`.

**Modify.** Change the block score or adjust how many coins grant a life.
Write one new test showing your expected behavior before changing the code.
Observe the outcome in the game using the original World 1-1 blocks.

**Explain.** Why does a room need a `spent` set instead of deleting a block?
Why do the different player forms share the same position and velocity?
