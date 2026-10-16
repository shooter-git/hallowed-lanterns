# Hallowed Lanterns — how it's built

The story is in [STORY.md](STORY.md). This is the technical plan and the conventions that the
code, the models and the sound share.

## Platform

An All the Spaces **creation** (see `shooter-git/all-the-spaces`, `agent-instructions/CREATION.md`
and ADR 0011 "creations from repositories"). The repository root is the creation project:
`ats.json`, `assets.lock.json`, `package.json`, `index.html`. `@allthespaces/portal` and its
bridge protocol are vendored in `vendor/` (they aren't on npm), exactly as a Studio workspace has them.

Hard limits: no network (everything ships in the bundle), sound only through `portal.audio` buses,
**10 MB before `portal.ready()`, 60 MB in total**, `budgetTier: "mid"` (400 draw calls, 1M
triangles, 256 MB textures, 32 voices), and it has to work on a phone held upright or on its side,
on a tablet and on a laptop, with touch or with mouse and keyboard. The top-left 56 × 56 px stays clear.

## Runtime (three.js, WebGL2)

- **One renderer, chapters as modules.** `src/chapters/<id>.ts` each build their own scene and are
  code-split, so only the chapter you're in (and the next one, preloaded while you walk) is in memory.
- **HDR pipeline** (`src/engine/post.ts`): the scene renders to a half-float target, then mip-chain
  bloom, per-chapter colour grade, AgX tone mapping, contrast-adaptive sharpening (the high
  tier), vignette and fine grain, all in about 12 cheap full-screen passes. While a low sun is in
  view (the Arbor at sunset) one more quarter-size pass draws its shafts through the gaps in the
  pergola and the trees: the sky writes alpha 0, so the march only gathers open sky.
- **Hundreds of lights for the price of a few:** a top-down *glow field* (`src/engine/glowfield.ts`)
  accumulates every lantern's light into a small texture each frame, and in its alpha each light's
  height weighted by its brightness, so a surface gets less of the light the further above or below
  it is (the lights in the grass don't light the treetops). The ground, the fog and the foliage
  sample it, and a small pool of real point lights follows the lanterns nearest you.
- **The sky** (`src/engine/sky.ts`): a sunset that keeps its colour from gold through rose and indigo
  to the blue overhead, the Belt of Venus opposite the sun, drifting banks of cloud lit by the sun
  and from below by the farm, stars or the whole Milky Way, and a moon (a disc with faint seas in a
  soft halo that lightens the sky around it: the Pasture's). Toward a low sun the haze glows gold.
- **Noise baked once:** the surfaces that cover most of the screen (the ground, the fog's stacked
  layers, the pumpkins' skins, the clouds, the far tree line) read their noise from a small tiling
  texture made at load time (`src/engine/noisetex.ts`, `hlFbmT`) instead of working out sixteen
  hashes a pixel every frame.
- **Glimmers** (`src/engine/glimmers.ts`): sparks, glitter or plankton in the air around
  you, one draw call per chapter, every one of them moved in the shader. In the Deep, soft shafts
  of light slant down through the water the same way (`src/engine/beams.ts`).
- **Carved lanterns** are instanced: one draw call for hundreds of pumpkins. A shader cuts the
  carving from an atlas of designs (faces, candles, stars, moons, owls) drawn at load time, lights
  the inner flesh, and lets candle light glow through the thin skin around each cut.
- **Fog** is height fog in every material, plus soft, lit fog banks that roll along the ground and
  part around you.
- **Walking** follows each chapter's path: stick or WASD to walk, drag or mouse to look, tap or
  click (or E) to interact. "Walk with me" lets the Ember lead you hands-free.

## Models (Blender → glTF)

Scripts in `tools/blender/` run headless (`blender -b --factory-startup -P tools/blender/<name>.py`)
and write `public/models/<name>.glb`.

- Metres, ground at y = 0, the origin at the model's footprint centre, **facing +Z in glTF** (−Y in Blender).
- Parts that move are separate named nodes with their pivot at the joint (`head`, `arm_R`,
  `tentacle_0`…). Bendable parts carry their 0→1 position along the part in `uv1.x`.
- Materials are Principled BSDF, textures baked at ≤ 1024 px (2048 for a few hero surfaces).
  Self-lit surfaces have names starting `glow_`, so the code can drive their brightness.
- Uncompressed `.glb`: the platform compresses models with meshopt when it publishes.

## Sound

Rendered offline by `tools/audio/` (Python, numpy/scipy, all synthesised: our own work, so
`"license": "own"`) into `public/audio/`, described by `public/audio/manifest.json`.

- Music and ambience loops are files of `loopSeconds + tailSeconds`. The engine starts the next
  pass every `loopSeconds` and crossfades over the tail, so loops never click, whatever the
  decoder does at the start and end of an MP3.
- Mastered to about −16 LUFS with peaks under −1.5 dBTP, so publishing leaves them untouched.
- Spatial sounds (the Ember, lanterns, the giants) use HRTF panning; underwater everything passes
  through a low-pass filter.

## Saved and shared

- `portal.save.personal`: how far you've got, and your settings.
- `portal.save.shared`: candles lit at the ofrenda and wishes on the tree, for everyone in the group.
- `portal.session`: other people's positions (10 per second, smoothed), and who's in which chapter.

## Privacy

The reference photos include family members. They live only in `reference/`, which git ignores;
nothing in the creation shows a real person.
