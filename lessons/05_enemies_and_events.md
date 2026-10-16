# Lesson 5: creatures, collisions, and sound events

**Predict.** What changes when Mary-O stomps a shell creature compared with
a simple walker? Does defeating a creature require Pygame to be running?

**Investigate.** Read `_enemy_tick()` and `_player_enemy_contacts()` in
`src/mary_o_lite/game.py`. Each `Enemy` has a `phase`, position, velocity,
and timer. `Game` appends a small `Event` object, and `app.Music` chooses
a sound from that event type. The simulation never imports the mixer.

**Modify.** Make one walker patrol faster, or alter the time a shell remains
still before it wakes up. Add a headless test for the new rule, then play a
level containing that enemy.

**Explain.** Why does `Game` emit an event rather than playing a WAV directly?
How would a no-audio mode or a replay tool benefit from this separation?
