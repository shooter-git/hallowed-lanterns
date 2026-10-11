# Hallowed Lanterns: Blender models

Every model in `public/models/` is made by a procedural Blender script in this folder: no
downloaded assets, no hand-edited `.blend` files. Each script is re-runnable and writes its
`.glb` files from scratch:

```sh
blender -b --factory-startup -P tools/blender/<script>.py
```

| Script | Writes |
|---|---|
| `longhorn.py` | `longhorn-standing.glb`, `longhorn-grazing.glb`, `longhorn-lying.glb`, `longhorn-blower.glb` |
| `octopus.py` | `octopus.glb` |
| `snowman.py` | `snowman.glb` |
| `ofrenda.py` | `ofrenda.glb` |
| `candy.py` | `candy-bucket.glb`, `candy-corn.glb`, `gummy-bear.glb`, `lollipop.glb`, `skewer.glb`, `cake-pop.glb` |
| `wishing-tree.py` | `wishing-tree.glb` |
| `lounge.py` | `pallet-sofa.glb`, `pallet.glb`, `hay-bale.glb`, `reed-fence.glb`, `shepherd-hook.glb`, `red-lantern.glb` |
| `arbor.py` | `arbor.glb`, `fence-post.glb`, `barbed-wire.glb` |
| `trees.py` | `tree-oak.glb`, `tree-tall.glb`, `tree-young.glb` |
| `pufferfish.py` | `pufferfish.glb` |
| `coral.py` | `coral-1.glb`, `coral-2.glb`, `coral-3.glb` |

To check a model the way the engine will get it (re-imported from the `.glb`, with a report of
nodes, pivots, materials, textures, triangles and bounds, and preview renders in `preview/`,
which git ignores):

```sh
blender -b --factory-startup -P tools/blender/preview.py -- <name> [studio|night|clay] [views] [size]
# views: front,three,side,back,top,low,iso,left or close@x:y:z:distance:azimuth:elevation; "-" = report only
```

## How it fits together

- `lib.py`: shared code for the Blender side: a mesh builder (`MB`) with per-corner UVs and an
  optional second UV set `along`, smooth lofted tubes (`Loft`: sections, domed/flat/pointed
  caps, rotation-minimising frames), ribbed pumpkins and gourds, chamfered timbers, lumps,
  outline extrusion, inflatable panel seams, an atlas packer, Principled-BSDF materials and the
  glTF export (`lib.export`).
- `texlib.py` and `tex_*.py`: the texture painters. Blender's own Python may lack numpy, so
  textures are painted by small numpy + Pillow + scipy (+ OpenCV for traced outlines) scripts
  that `lib.paint()` runs with an external `python3` (or `$HL_PYTHON`). Results are cached in
  `.cache/` (git-ignored) and repainted only when a painter or its parameters change.
- Blender 3.4's glTF add-on itself needs numpy. If Blender runs on a system Python without it,
  put a numpy built for that Python version in `.cache/pylib<ver>/` (or point
  `$HL_BLENDER_PYLIB` at one), e.g. `python3.11 -m pip install --target tools/blender/.cache/pylib311 numpy`.
  `lib.py` adds it to the path and restores the old `np.bool`-style aliases the 3.4 importer uses.

## Conventions (the contract with the engine)

- Metres, real scale. Each model stands on y = 0 with its origin at its footprint centre and
  faces +Z in glTF (-Y in Blender), except the floating/hanging ones noted below.
- Moving parts are separate nodes with their pivot at the joint. Bendable parts carry their
  0 → 1 position along the part (root → tip) in the second UV set (`TEXCOORD_1`, x; y = 0).
- Principled BSDF materials only. Names starting `glow_` are self-lit and always have an
  emissive texture or colour (the engine scales their brightness). Textures are 1024 px or less,
  except the three hero surfaces: the longhorn glow (2048²), the octopus skin (2048²) and the
  ofrenda crest (2048 × 1024). Some materials use `KHR_materials_specular` / `_ior` (three.js
  reads both).
- L/R in node names are as seen from the front (the viewer's left/right): `_R` is on +X.
- Uncompressed `.glb`; modifiers applied; no cameras or lights.

## The models

Sizes are the glTF bounding box, x × y (up) × z (front-back), in metres.

### Longhorns (`longhorn.py`) — Pasture of Giants

| File | Size | Tris |
|---|---|---|
| `longhorn-standing.glb` | 8.27 × 6.19 × 6.68 (head top ~4.6 m, horn tips 6.2 m) | 40.6k |
| `longhorn-grazing.glb` | 8.27 × 4.43 × 6.71 (back ~3.7 m, muzzle on the ground) | 40.8k |
| `longhorn-lying.glb` | 8.03 × 4.81 × 7.28 (head ~2.8 m) | 40.0k |
| `longhorn-blower.glb` | 0.32 × 0.48 × 1.12 (with its outlet tube) | 2.2k |

- Nodes: `body` (root) → `head` (neck, head, horns, ears, eyes), pivot at the base of the neck
  inside the chest. Rotating `head` about its local +X lowers the head (positive = down);
  about +Y turns it. The standing pose's head can lower about 30° before the muzzle meets the
  chest line.
- Materials: `glow_inflatable` (white fabric; one 2048² texture used as base colour *and*
  emission: panels glow brighter in their middles, darker toward the stitched seams, which are
  pinched into the geometry at the same places), `eye_dark` (eyes, nostrils, mouth). All three
  poses share one UV layout and an identical texture. Blower: `plastic_yellow`,
  `plastic_black`, `fabric`.

### Octopus (`octopus.py`) — the Keeper of the Deep

`octopus.glb`, 8.48 × 5.84 × 7.65, 57.6k tris.
- `body` (root: purple ribbed pumpkin mantle, green stem, the head with its eye sockets),
  children `eye_L`, `eye_R` (pivots at the eyeball centres; the pupils look along +Z at rest:
  aim the nodes to make the Keeper look at you) and `tentacle_0` … `tentacle_7` (pivots at the
  arm roots inside the crown; `along` UV 0 at the root → 1 at the tip, the suckers carry the
  value of where they sit). Arms 4 and 5 rise up behind, curling over; the others curl up off
  the ground.
- Materials: `glow_uvpaint` (skin, 2048²; emission 1024² = the fluorescent paint: ring spots,
  piping along the arms, suckers, stem), `glow_eyes` (orange pupils).

### Snowman (`snowman.py`) — October Snow

`snowman.glb`, 2.24 × 2.63 × 1.21, 29.0k tris.
- `body` (root) → `arm_L`, `arm_R` (pivots at the shoulders); `arm_R` → `mug` (pivot at the
  mug's centre). To raise the mug in a toast rotate `arm_R` about glTF +Z (positive raises it;
  `arm_L` raises with negative).
- Materials: `gourd` (striped carnival squash + normal map), `snowman_props` (atlas: bark, mossy
  bark, pallet wood, corn-cob kernels, carrot, hat felt, coal + normal map), `snow`.

### Ofrenda (`ofrenda.py`) — the Marigold Garden

`ofrenda.glb`, 5.61 × 5.41 × 2.58, 52.2k tris.
- `ofrenda` (root, static) → `crest` (the glowing cut-out sign), `candle_spots` (33 empties
  `candle_000`… on the steps; each one's uniform scale is that candle's size relative to the
  template) and `candle_template` (one drippy candle, pivot at its base, standing on
  `candle_000`) → `flame_template` (the flame and the glow in the cup).
- Materials: `ofrenda_paint` (atlas: teal, lime, purple, hay, runner, marigolds, baskets, fruit,
  skulls), `glow_crest`, `papel_picado` (alpha MASK, double-sided: banner flags and resting
  monarchs), `glow_lights` (little pumpkins, vases, bottles), `candle_wax`, `glow_flame`.

### Sweet Hollow (`candy.py`)

| File | Size | Tris | Notes |
|---|---|---|---|
| `candy-bucket.glb` | 2.16 × 3.31 × 2.14 | 11.8k | open top; child `handle` (pivot at the rim centre), `glow_handle` spiral; `bucket_paint`, `handle_black` |
| `candy-corn.glb` | 1.10 × 2.50 × 0.14 | 0.5k | `candy_corn` |
| `gummy-bear.glb` | 0.44 × 0.65 × 0.34 | 3.6k | `gummy`: neutral map × baseColorFactor (blue); set the material colour for other bears |
| `lollipop.glb` | 0.49 × 1.61 × 0.34 | 3.2k | `lollipop` |
| `skewer.glb` | 0.31 × 2.62 × 0.31 | 5.2k | nine beach-ball pumpkins, `skewer` |
| `cake-pop.glb` | 0.38 × 1.39 × 0.38 | 2.4k | `cake_pop` |

### Wishing Tree (`wishing-tree.py`)

`wishing-tree.glb`, 6.04 × 3.95 × 0.97, 17.6k tris.
- `wishing_tree` (root empty) → `tree` (the 4 cm white board, `board`), `hedge` (6 × 2.6 m
  boxwood wall with pom-poms; `hedge` tiles at 1 m, `pompom`) and `leaf_anchors` → 306 empties
  `anchor_000`…: on the front face of the branches at their edges; local +X points along the
  leaf (outward from the branch, a little toward its tip), local +Z out of the board toward
  the viewer.

### Lantern lounge (`lounge.py`)

| File | Size | Tris | Notes |
|---|---|---|---|
| `pallet-sofa.glb` | 2.45 × 1.09 × 1.26 | 12.4k | `wood`, `hay`, `throw` (dragon fleece, cloth-simulated drape, double-sided), `cushion` |
| `pallet.glb` | 1.21 × 0.14 × 1.00 | 0.6k | `wood` |
| `hay-bale.glb` | 0.94 × 0.38 × 0.48 | 2.0k | `hay` |
| `reed-fence.glb` | 4.00 × 1.90 × 0.07 | 0.2k | `reed` (alpha MASK, double-sided); repeat every 4 m along X; `fairy_lights` → `strand_0`, `strand_1` → `bulb_<s>_<nnn>` (41 each, in order along the wire, 0.1 m apart) |
| `shepherd-hook.glb` | 0.27 × 2.19 × 0.01 | 1.1k | `metal_black`; `hang_point` empty where a lantern's ring sits |
| `red-lantern.glb` | 0.35 × 0.72 × 0.35 | 2.2k | hangs **from its origin** (the top of its ring; everything is below y = 0); child `tassel` (pivot at the bottom cap); `glow_lantern` (red skin, bright slits), `gold`, `tassel` |

### Arbor of Faces (`arbor.py`)

| File | Size | Tris | Notes |
|---|---|---|---|
| `arbor.glb` | 5.20 × 3.53 × 4.30 | 1.9k | one 4 m bay; the lane runs along glTF Z; posts 4.6 m apart, 3.2 m tall. Root `arbor` has the posts/header at z = +2 plus beams, braces, purlins and 8 pumpkin wires; child `end_frame` the posts/header at z = −2 (show it only on the last bay). `hang_points` → `hang_<wire>_<n>` (8 × 8). `timber`, `wire` |
| `fence-post.glb` | 0.15 × 1.50 × 0.13 | 0.8k | `cedar` |
| `barbed-wire.glb` | 3.00 × 0.03 × 0.03 | 2.4k | along X from −1.5 to 1.5 at y = 0; `wire` |

### Trees (`trees.py`) — optional: the engine now grows its own trees in code

| File | Size | Tris |
|---|---|---|
| `tree-oak.glb` | 12.35 × 10.09 × 11.45 | 15.8k |
| `tree-tall.glb` | 6.75 × 14.83 × 5.75 | 13.4k |
| `tree-young.glb` | 3.37 × 5.56 × 3.31 | 2.8k |

Root mesh `<name>` (`bark`) → `foliage` (`foliage`, alpha MASK; two-sided cards built as
geometry, normals bent out from the crown's centre) and `hang_points` → `hang_##` under
level branches 2.5–6.5 m up (13 on the oak, 4 on the sapling, none on the tall tree, whose
branches are higher).

### The Deep (`pufferfish.py`, `coral.py`)

- `pufferfish.glb`, 0.54 × 0.42 × 0.62, 2.5k tris. It floats: the origin is the body's centre
  (scale the root to puff it up). Children `tail` (wag about its local Y), `fin_L`, `fin_R`,
  `hang_point` (top of the stem). `glow_uvpaint`, `glow_eyes`.
- `coral-1.glb` (orange staghorn, 0.52 × 0.99), `coral-2.glb` (pink candelabra, 0.69 × 1.23),
  `coral-3.glb` (lime kelp, 0.70 × 1.00): 2 cm painted cut-out boards, 0.4–1.1k tris,
  `glow_uvpaint`.
