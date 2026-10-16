# Mary-O Lite: source mapping and fidelity

The target is **similar behavior and recognizable source character**, not a
reimplementation of Ambition's entire engine. This table makes the current
state explicit rather than implying features are exact.

| Source system in Ambition | Lite version | Status |
|---|---|---|
| `ambition_map_assets/.../worlds/mary_o.ldtk` | `assets/worlds/mary_o.ldtk` | Original text LDtk room geometry and entities imported |
| `tools/ambition_sprite2d_renderer/assets/mary_o_v2.svg` | `assets/svg/mary_o_v2.svg` | Original editable SVG |
| `.../targets/characters/_mary_o_v2_svg_poc.py` | `assets/rigs/*.json`; `poses.py` | Six exported rig views, all source side clips, front death, keyframe blending |
| `.../data/characters/player_robot_v3_svg/...` | `assets/svg/player-robot-v3.svg` | Original rescue robot SVG; generated PNG thumbnail |
| `mary_o_rules.ron`, movement systems | `physics.py` | Classic velocity constants, four jump launch bands, held-jump gravity, ground skid and air momentum |
| Mary-O forms and powerups | `game.py` | Small/tall/fire/cosmic, block rewards, damage transitions, quasar |
| Mary-O level 1-1 to 2-4 and warp | `content.py`, `game.py` | Original rooms, basic authored entities, exit sequence, pipe travel |
| SVG part sprites | `tools/build_assets.py`, `graphics.Puppet` | Per-part rasterization, pivot-based transforms, mirroring and vertical scale |
| Original Cosmic painter (`_mary_o_v2_cosmic_art.py`, `mary_o_v2_cosmic.py`) | `tools/ambition_art/cosmic_art.py`, `cosmic_animation.py` | Real source-painted night-sky gown, long hair, wings, crown, ring; all fourteen source rows including the 36/18-frame transform/exit; **no shader required** |
| Original tileset and pickups | `tools/ambition_art/tiles.py`, `props.py` | 17 original tiles, animated coins and powerups |
| Original construction art | `tools/ambition_art/construction.py`, `lift.py`, `spark.py` | Pipe segments, flag and pole, lava, switch, gate, clockwork lift and projectiles |
| Fire Bars | `motion.py`, `game._hazards_update`, source `fire_orb.py` | All 76 orbs follow authored clockwise/counterclockwise LDtk paths; collision and sprites move together |
| Moving ferries and lift chains | `motion.ping_pong`, `motion.wrapping_lift` | All 39 moving platforms use authored sweep/loop and speed, including ride/contact behavior |
| Snake Plant emergence | `motion.wanted_plant_out`, `art_assets.draw_plant` | Original 330-tick rise/hide cycle, pot mouth anchor and pipe occlusion |
| Flying snake art | `tools/ambition_art/snakes_on_planes.py` | Original source painters for paper and Cartesian planes, 17 placed enemies |
| Fire / void orbs and coconuts | `tools/ambition_art/fire_orb.py`, `coconut.py` | Generated source art for moving hazards and enemy projectiles |
| Parallax scenery | `graphics.Painter` | Procedural distance layers and original terrain sprites; still simplified |
| World enemies | `tools/ambition_art/{ai_slop,solid_snake,snake_plant,void_star,void_lizard,snakes_on_planes}.py` | All eight placed character kinds source-painted or from swallow SVG; simplified AI state machines |
| Camera and room history | `Painter.track()`, `Game.room_cache` | Bidirectional follow, left/right course travel and per-room state snapshots on revisit |
| Castle end | `game._goal_tick()` | Switch, sequential broken planks, boss defeat, gate, rescue robot and timed dialogue |
| Engine music/SFX | `tools/compose_audio.py` | Five new chiptune loops and mathematical SFX; not original score |
| Cross-platform/rollback/shaders | None | Not part of this educational project |

## Supported animation names

Source clips differ by form. `small_side` includes `idle`, `walk`, `jump`,
`skid`, `climb`, and `swim`. `tall_side` and `fire_side` also include `crouch`,
`crouch_walk`, and `crouch_jump`; `fire_side` has `shoot`. Each form has a
front-facing `death` view. The editor previews the additional composite
`grow`, `shrink`, `fire_transform`, `cosmic_transform`, `cosmic_leave` stages.
Cosmic has its *own* `idle`, `death`, `walk`, `jump`, `fall`, `skid`, `crouch`,
`crouch_walk`, `crouch_jump`, `climb`, `swim`, `shoot`, `transform` and `shrink`
rows, painted from the actual Ambition sources rather than composed SVG joints.
The runtime uses running, airborne, crouch, shooting, skidding, death and
composite transformations. Climbing/swimming are pose-lab samples, not full
world mechanics in this version.

Read [the enumerated source-fidelity audit](FIDELITY_AUDIT.md) for exact
LDtk entity coverage and known remaining differences.

## Remaining playtest work

- The Pygame window, timing, keyboard feel, sprite alignment, and long rooms
  must be exercised by a person on an actual graphical installation.
- Enemy brains remain simplified. **Hazard paths and lift sweeps now use
  authored values**, but this is not a Rust simulation parity claim.
- Camera zones, every background and foreground source generator, and
  small sound details are not yet ported. Enemies use original sprites but
  their simplified motion/state machines do not necessarily match Rust.
- Reversible course backtracking intentionally changes the classic
  forward-only camera contract.
- The first course and castle goal paths have headless tests; no automated
  playthrough asserts an enemy-free finish through every platform sequence.

## License

Source assets remain attributed to Ambition, with a complete copy of its
Apache-2.0 LICENSE and the source-path mapping in `NOTICE`.
