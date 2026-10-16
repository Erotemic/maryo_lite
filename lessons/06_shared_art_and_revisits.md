# Lesson 6: Source-generated art and reversible levels

**Predict → Investigate → Modify → Explain**

## Predict

Mary-O can now cross the beginning of a level and return to the one before it.
What should happen to a question block you used and an enemy you defeated
before leaving? Should their state reset or remain changed? Why?

## Investigate

- Open `src/mary_o_lite/game.py`. Find `RoomSnapshot`, `_save_room()`,
  `go_previous()` and `load_room()`.
- Open `src/mary_o_lite/graphics.py`. Look at `track()` and explain why it
  permits the camera to move left again.
- Open `tools/ambition_art/cosmic_animation.py`. Compare `transformation()`
  and `detransformation()` to the smaller `look_for()` poses.
- Run `python main.py --pose-lab`, select Cosmic, and preview its animation
  clips. Watch the 36-frame entry and 18-frame exit.
- Inspect `tools/ambition_art/build.py`: Python and SVG files are inputs;
  Git-ignored PNG sprites are outputs. Why is the source hash useful?

## Modify

1. In `cosmic_animation.py`, adjust one source pose (for instance, the orbit
   radius or a wing spread) and regenerate with
   `python tools/build_assets.py --force --art-only`.
2. Adjust the reversible camera's follow speed in `Painter.track()` while
   leaving the fixed-step simulation and collision physics alone.
3. Add a headless test demonstrating that a spent block stays spent when the
   player leaves a course and returns to it.

## Explain

- Which components are authoritative source? Which are generated binary
  caches? What would happen if you committed the cache to Git?
- Why is an independent level snapshot easier to teach than rollback across
  the entire platformer?
- Why does skipping the old finish pole while travelling left matter?
- Which aesthetic details can use a sprite painter rather than GPU shaders?
