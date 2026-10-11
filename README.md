# Hallowed Lanterns

One October night at the pumpkin patch, as an immersive walk: follow a runaway candle flame — the
Ember — from a sunset tunnel of jack-o'-lanterns, through a candle-lit grove, a garden of red
lanterns, a pasture of glowing giants, a hollow full of candy, an impossible October snow and a
deep blue sea, to an ofrenda and a Wishing Tree.

It's an [All the Spaces](https://github.com/shooter-git/all-the-spaces) **creation**: people open it
from an object in their space, together, on a phone, a tablet or a laptop. It runs entirely in the
browser (three.js, WebGL2), with no network once loaded.

The story, chapter by chapter, is in [docs/STORY.md](docs/STORY.md); how it's built, in
[docs/DESIGN.md](docs/DESIGN.md).

## The night

| | Chapter | |
|---|---|---|
| I | The Arbor of Faces | The hay-bale sign at sunset, then a lane under hundreds of carved jack-o'-lanterns that wake as the sun goes. One loses its flame. |
| II | The Candle Grove | Blue hour. Candle-carved pumpkins hang in the trees over red-lit rolling fog; the Ember plays hide and seek. |
| III | The Lantern Garden | A tunnel of red lanterns the Ember lights as it runs ahead, the Lantern Sky, and a lounge where you can sit. |
| IV | The Pasture of Giants | Three enormous glowing longhorns breathe under the stars; the tall one lowers its head to look at you. |
| V | Sweet Hollow | Candy land under a violet oak. Play the Ember's song on the letter pumpkins. |
| VI | October Snow | It snows; a gourd snowman raises his corn-cob mug; the snowflakes slow, stop, and rise… |
| VII | The Deep | …into bubbles. Pumpkin jellyfish, coral, and the Keeper of the Deep, who waves back. |
| VIII | The Marigold Garden | Light a candle at the ofrenda, write a wish and hang it on the Wishing Tree. |

You walk at your own pace the whole way (or let "Walk with me" walk for you). Candles you light
and wishes you hang are kept for your group, and everyone in the session walks the same night as a
light in their own colour.

## Running it

```bash
pnpm install
pnpm dev        # http://localhost:5173 — on its own, you're the only player
pnpm build      # dist/ is what publishing builds (with the platform's own settings)
pnpm typecheck
```

While developing, `?at=<metres>` starts straight away partway along the first chapter,
`?chapter=<n>` starts at chapter n (0–7), and `?tier=low|mid|high` forces a quality level.

## Putting it on an object in a space

This repository is shaped the way All the Spaces expects a creation from a repository to be
(`ats.json`, `assets.lock.json`, `package.json`, `index.html` at the root; the portal SDK vendored
in `vendor/`), so a server can follow it:

1. On the server, allow this repository in a source definition — `sources/github.json` in the
   install folder (and, for a private repository, a read-only token in `sources.env`):

   ```json
   { "id": "github", "displayName": "GitHub", "kind": "github",
     "tokenEnv": "ATS_SOURCE_GITHUB_TOKEN", "repositories": ["shooter-git/hallowed-lanterns"] }
   ```

2. In the Studio's **Creations** page, choose the object, then **Make a creation from a
   repository**: `shooter-git/hallowed-lanterns`, folder `/`, following **releases** (the default).
3. Publish a release here (a tag) whenever you want the space to pick up changes; Architects see
   it and press **Update**. Every version is checked on a phone, a tablet and a laptop first.

## How it's made

- `src/engine/` — the renderer (HDR, bloom, AgX), the glow field that lets hundreds of lanterns
  light the ground and fog, carved-pumpkin and paper-lantern shaders, the terrain, the walk,
  the Ember, sound, the people walking with you, the interface.
- `src/chapters/` — one module per chapter, each loaded only when you get there.
- `tools/blender/` — Blender scripts that model the longhorns, the octopus, the snowman, the
  ofrenda and the rest (`blender -b --factory-startup -P tools/blender/<name>.py`).
- `tools/audio/` — the soundtrack and every sound, synthesised from scratch in Python
  (see its README).
- `node tools/lock-assets.mjs` — records new models and sounds in `assets.lock.json` as our own.

Every picture, model and sound is made by this project's own tools; nothing is downloaded.

## Privacy

The reference photos this was built from include family members. They stay on the computer that
built it, in `reference/`, which git ignores. Nothing in the creation shows a real person.
