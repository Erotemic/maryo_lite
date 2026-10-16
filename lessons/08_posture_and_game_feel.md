# Lesson 8: Game feel is a contract between input, physics, and art

**Predict.** Why can small Mary-O run under a low roof when tall Mary-O
cannot? How could we let tall Mary-O use the *same* corridor without making
her standing form smaller? Would releasing Down under the roof be safe?

**Investigate.** Read `SMALL_H`, `TALL_H`, `CROUCH_H`,
`Game._stand_or_crouch()` and `Game._change_form()`. Watch how `p.y` changes
when the height changes, and compare `p.foot` before and after. Open
`tests/test_movement_fidelity.py` to see a real 32 px high corridor.

**Modify.** Change `CROUCH_SPEED` in `physics.py` from 90 to 60, then to
140. Try running into a low tunnel versus entering from a complete stop.
Play with run (X) pressed/released and see how velocity approaches a
new speed rather than jumping to it. Use `F3` to display collision boxes.

**Explain.** What would go wrong if crouch only changed the art, not the
collision box? Why is checking the overhead clearance before expanding
important? Why should walk animation speed depend on how far Mary-O has
actually moved instead of just how many seconds have elapsed?

**Stretch goal.** Add a test for walking into a narrow tunnel while holding
Down across a small ledge. Keep the 0-coyote and 0-buffer jump policy intact.
