# Lesson 4: generate images and music from tracked source

**Predict.** Will the game still start after you delete the PNG and WAV files
under `assets/generated/`? Will Git show those files as changed?

**Investigate.** Open `tools/build_assets.py` and `tools/compose_audio.py`.
`build_assets.py` isolates the named SVG elements from `assets/svg/`,
rasterizes each one, and writes pivot metadata. `compose_audio.py` turns
readable notes and simple waveforms into PCM WAV files.

**Modify.** Run `python tools/build_assets.py --force`. Change a few lead
notes in `TRACKS['starlight']`, then regenerate only the audio using
`python tools/build_assets.py --audio-only --force`. Observe `git status`.

**Explain.** Why should binary outputs be ignored while SVG, JSON, and
Python source stay in Git? What makes an asset generator reproducible?
