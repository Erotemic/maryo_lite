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
| Cosmic renderer and shaders | `graphics.draw_cosmic()` | Shader-free procedural wings, crown, halo and aura; approximate visuals |
| Parallax and props | `graphics.Painter` | Simple Pygame parallax, biome palettes, coins, blocks, pipes, platforms |
| World enemies | `game._enemy_tick()` | Slop, snakes, plant, swallow, star, planes, void lizard with simplified behaviors |
| Castle end | `game._goal_tick()` | Switch, sequential broken planks, boss defeat, gate, rescue robot and timed dialogue |
| Engine music/SFX | `tools/compose_audio.py` | Five new chiptune loops and mathematical SFX; not original score |
| Cross-platform/rollback/shaders | None | Not part of this educational project |

## Supported animation names

Source clips differ by form. `small_side` includes `idle`, `walk`, `jump`,
`skid`, `climb`, and `swim`. `tall_side` and `fire_side` also include `crouch`,
`crouch_walk`, and `crouch_jump`; `fire_side` has `shoot`. Each form has a
front-facing `death` view. The editor previews the additional composite
`grow`, `shrink`, `fire_transform`, `cosmic_transform`, `cosmic_leave` stages.
The runtime uses running, airborne, crouch, shooting, skidding, death and
composite transformations. Climbing/swimming are pose-lab samples, not full
world mechanics in this version.

## Remaining playtest work

- The Pygame window, timing, keyboard feel, sprite alignment, and long rooms
  must be exercised by a person on an actual graphical installation.
- Enemy behaviors and hazard trajectories are approximations; Rust test
  outcomes do not imply parity with this Python implementation.
- Camera zones, special foreground sprites, small sound details, and every
  source creature's generated artwork have not been ported.
- Cosmic wings and transformation embellishments are drawn procedurally,
  rather than exporting the original frame-by-frame cosmic sprite generator.
- The first course and castle goal paths have headless tests; no automated
  playthrough asserts an enemy-free finish through every platform sequence.

## License

Source assets remain attributed to Ambition, with a complete copy of its
Apache-2.0 LICENSE and the source-path mapping in `NOTICE`.
