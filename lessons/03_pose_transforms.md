# Lesson 3: animate SVG parts, not whole frames

**Predict.** If the near arm rotates by 25 degrees, how should the hand
move? Why is the pivot different from the image's upper-left corner?

**Investigate.** Start `python main.py --pose-lab`. Cycle small/tall/fire,
select walking or shooting, pause with Space, choose a joint with Tab, and
rotate it with `[` or `]`. Read `poses.sample_pose()` and the matching
`assets/rigs/*_side.json`. Look for `[x, y, angle, scale_y, mirror]`.

**Modify.** Change one arm angle in one frame of the `walk` clip. Try
changing a leg's `scale_y` from 1 to 0.7; this makes squash/stretch visible.
The JSON is loaded when a Pygame session starts, so restart the app after a
source change. Binary images do not need to be regenerated for pose edits.

**Explain.** Which information belongs in an SVG part, and which belongs in
a pose? What would break if every pose was stored as one large PNG?
