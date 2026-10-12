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

## Second modeller: the Kraken's Wreck, the Web, the owl, the guitar and the picture show

Same conventions as above (metres, ground at y = 0, front +Z in glTF, `_R` on +X, `glow_*` are
self-lit). Scripts and their painters:

| Script | Painters | Writes |
|---|---|---|
| `kraken.py` | `tex_kraken.py`, `tex_wood.py` | `kraken-tentacle-a/-b/-c.glb`, `kraken-arch.glb`, `inflatable-pumpkin.glb` |
| `skeletons.py` | `tex_pirates.py` | `skeleton-pirate-sit.glb`, `skeleton-pirate-stand.glb`, `skeleton.glb`, `skeleton-climb.glb` |
| `treasure.py` | `tex_wood.py`, `tex_pirates.py` | `rowboat.glb`, `treasure-chest.glb`, `pumpkin-palm.glb`, `barrel.glb` |
| `web.py` | `tex_web.py` | `pumpkin-spider.glb`, `praying-mantis.glb`, `web-pumpkin.glb` |
| `owl.py` | `tex_owl.py`, `tex_pirates.py` | `pumpkin-owl.glb` |
| `guitar.py` | `tex_wood.py`, `tex_owl.py` | `pumpkin-guitar.glb` |
| `picture.py` | `tex_lounge.py` (the shared hay) | `movie-screen.glb`, `bench.glb`, `hay-stage.glb` |

Each script takes `-- only=<keys>` to build some of its models (see its docstring).
`lib.paint_named()` (added to `lib.py`) gives every texture its own cache stamp when one painter
is called many times with the same output keys. `tex_wood.py` is a generic tileable plank
painter (colour + normal; one plank per row band, `row_tones` to keep two woods in one tile).

### The Kraken's Wreck (`kraken.py`, `skeletons.py`, `treasure.py`)

| File | Size (x × y × z) | Tris | Nodes / notes |
|---|---|---|---|
| `kraken-tentacle-a.glb` | 2.65 × 6.35 × 1.64 | 9.8k | one mesh `tentacle` (pivot at the footprint centre) |
| `kraken-tentacle-b.glb` | 1.80 × 4.98 × 1.36 | 8.2k | 〃 |
| `kraken-tentacle-c.glb` | 1.99 × 3.99 × 1.28 | 8.5k | 〃, the tip curled right over |
| `kraken-arch.glb` | 5.58 × 4.98 × 4.41 | 19.4k | `wreck` → `hull` (static), `tentacle` (pivot where it leaves the ground, glTF (-1.55, 0, 1.45)) |
| `inflatable-pumpkin.glb` | 3.12 × 2.98 × 3.24 | 6.6k | `pumpkin` |
| `rowboat.glb` | 3.29 × 0.80 × 1.36 | 5.4k | `rowboat` → empties `crew_0`, `crew_1` |
| `skeleton-pirate-sit.glb` | 1.90 × 1.30 × 0.82 | 9.7k | `skeleton` → `head`, `oar` |
| `skeleton-pirate-stand.glb` | 0.86 × 1.81 × 0.50 | 7.3k | `skeleton` → `head` |
| `skeleton.glb` | 0.51 × 1.74 × 0.39 | 7.4k | `skeleton` → `head` |
| `skeleton-climb.glb` | 0.68 × 1.94 × 0.64 | 7.4k | `skeleton` → `head` |
| `treasure-chest.glb` | 3.50 × 2.39 × 2.11 | 18.4k | `treasure` → `chest` → `lid`, `chains` |
| `pumpkin-palm.glb` | 2.21 × 2.22 × 2.01 | 5.9k | `palm` |
| `barrel.glb` | 0.90 × 0.63 × 0.63 | 2.8k | `barrel` (lying on its side, axis along X) |

- **Tentacles** (all four): orange inflatable tubes rising in an S, the tip curling over toward
  +X. TEXCOORD_1 (`along`): x = 0 at the root → 1 at the tip (suckers and the blower port carry
  the value of where they sit; y = 0): bend/sway them in a vertex shader by `along`, e.g. an
  angle growing with `along²` about the axis through the pivot. The inner edge (the concave side,
  +X at the root, turned a little toward the viewer) is a lemon band with scalloped borders and a
  zigzag of suckers. Materials `glow_inflatable` (one 1024² texture as base colour and emission:
  panels brightest low down, seams, tie-down tabs), `glow_suckers` (256²), `blower_port` (black).
  The arch's hull adds `hull_wood` (+ normal map).
- **Pumpkin**: 10 gores with seams in the grooves, a curled stem, a dark vent; `glow_inflatable`.
- **Pirate skeletons**: carved jack-o'-lantern heads whose face cut-outs are `glow_carving`
  (pink on the seated one, orange on the standing one; plain emissive colour). `head` pivots at
  the top of the neck (turn it about glTF Y, nod about X). The seated one sits on a 0.36 m seat:
  its origin is on the floor under the seat point; in the rowboat put its origin on `crew_0` /
  `crew_1` (they face the stern). Its `oar` pivots at the upper hand. Materials `bone`,
  `pirate_cloth` (atlas, double-sided), `pumpkin_skin`, `glow_carving`.
- **Skeletons**: `bone` only. `skeleton-climb` hugs a trunk of radius 0.2 m whose axis is the
  vertical line through its origin; it faces -Z (glTF) into the trunk and its lowest foot is at
  y = 0, so lift it up the trunk and turn it about Y as you like.
- **Treasure chest**: platform 3.5 × 1.4 × 0.45 m (the free strip in front of the chest, glTF z ≈ 0.35 → 0.7, is the seat),
  chest 2 × 1 × 0.95 m. `lid` pivots on the hinge line along X: its mesh is modelled closed and
  the node carries the open angle (-110° about X), so rotation 0 closes it; hide `chains` when
  the lid moves. Materials `chest_wood` (+ normal), `glow_gold` (coins, gems, pearls, crown,
  chains; emissive factor 0.35), `bone` (the skulls), `pumpkin_skin` (the pale pumpkin).
- **Palm**: `pumpkin_skin`, `glow_fronds` (alpha MASK, double-sided; also the three green lights
  in the crown). **Rowboat**: `boat_wood` (+ normal), `iron`. **Barrel**: `barrel_wood`, `iron`.

### The Web (`web.py`)

| File | Size | Tris | Nodes |
|---|---|---|---|
| `pumpkin-spider.glb` | 7.00 × 3.03 × 5.51 | 23.2k | `spider` → `leg_<k>` → `tibia_<k>` → empty `foot_<k>` (k = 0 … 7), `baby` |
| `praying-mantis.glb` | 3.71 × 3.39 × 2.97 | 11.0k | `mantis` → `abdomen`, `thorax` → `head` → `antenna_L`, `antenna_R`; `thorax` → `foreleg_L`/`_R` → `femur_L`/`_R` → `tibia_L`/`_R` |
| `web-pumpkin.glb` | 0.51 × 0.75 × 0.53 | 3.8k | `web_pumpkin` → empty `hang_point` |

- **Spider**: each leg is two segments: `leg_<k>` (the femur) pivots at the hip inside the
  body, `leg_0`–`leg_3` on +X front to back, `leg_4`–`leg_7` on -X front to back; its child
  `tibia_<k>` (the rest of the leg) pivots at the knee, about 2.4–2.5 m up; the empty `foot_<k>`
  marks the foot's centre (y = 0.10). The scene walks it by placing the feet and bending hip and
  knee to reach them.
  `baby` (the green spiderling on the abdomen) pivots where it sits. Materials `glow_uvpaint`
  (2048² base + 1024² emission: the neon lightning patches, polka dots, pale lower legs and the
  baby glow; the maroon pumpkins stay dark) and `glow_eyes` (the domed pink spirals).
- **Mantis**: sits on its mid and hind legs (part of `mantis`), forelegs raised and folded.
  `abdomen` pivots where it joins the thorax; `thorax` (the prothorax) at its base; each
  raptorial foreleg is a chain, `foreleg_L/_R` (coxa, at the shoulder) → `femur_L/_R` (at the
  elbow) → `tibia_L/_R` (the claw); `head` pivots at the neck (eyes, palps and collar go with
  it) and carries `antenna_L/_R`, pivoting at their roots. Materials `glow_uv` (lime foam tubes and
  the orange gourd abdomen; emission = base) and `glow_eyes`.
- **Web pumpkin**: stands on the ground; the five threads meet at `hang_point` 0.42 m above the
  stem, to hang it in the web instead. `pumpkin_skin`, `glow_web` (strands, double-sided,
  faint lavender emission), `glow_uv` (the two tiny spiders).

### The owl (`owl.py`)

`pumpkin-owl.glb`, 10.27 × 4.42 × 1.52, 15.2k tris. `owl` (the ivy egg body) → `head` (pivot at
the neck), `wing_L`, `wing_R` (pivots at the shoulders, glTF (∓0.8, 2.62, -0.14); ruffle them by
small rotations about their local Z/Y), `body_spots` → `spot_00` … `spot_41`: where the engine
places glowing carved pumpkins (each spot's local +Z points out of the body, +Y up; its uniform
scale is the suggested pumpkin diameter in metres, 0.38–0.46). Materials `ivy` (+ normal),
`pumpkin_skin`, `glow_eyes` (carved sockets and teal pupils), `glow_uv` (beak, ear tufts, curly
stem) and `glow_feathers` (double-sided): five, because the brief names all of them.

### The guitar (`guitar.py`)

`pumpkin-guitar.glb`, 2.56 × 6.28 × 1.47 (body 3.2 m), 3.4k tris. `guitar` (board, ivy face,
raised rim, back struts, bridge, the dark rods that carry the strings, tuning pegs) with
`pumpkin_spots` → `spot_00`–`spot_15` (the big carved pumpkins inside the body, scale 0.42) and
`spot_16`–`spot_53` (the small ones round the rim, scale 0.26), same orientation convention as
the owl's (here simply the model's axes); and `string_bottom_0..5` (at the bridge),
`string_bend_0..5` (where each string leaves the straight neck) and `string_top_0..5` (its
peg): draw each glowing string as bottom → bend → top. Strings 0–2 go to the left pegs, 3–5 to
the right. Materials `guitar_wood` (+ normal), `ivy` (+ normal), `rods`.

### The picture show (`picture.py`)

| File | Size | Tris | Nodes / materials |
|---|---|---|---|
| `movie-screen.glb` | 7.30 × 4.72 × 2.35 | 6.7k | `movie_screen` (box truss, back props; `truss`) → `screen` |
| `bench.glb` | 1.83 × 0.43 × 0.28 | 0.9k | `bench`; `plastic_white`, `steel` |
| `hay-stage.glb` | 5.29 × 0.74 × 1.04 | 7.0k | `hay_stage`; `hay` (same texture as `hay-bale.glb`) |

`screen` is a 6 × 3.6 m grid (bottom edge 0.55 m up, 0.18 m in front of the truss) with UVs
0..1 across it (u left → right, v bottom → top seen from the front) and a plain white `screen`
material: put the film on it.

### The magic well and the Venus flytrap (`magic-well.py`, `venus-flytrap.py`)

Painters `tex_well.py` (stone, shaft, rope, ivy leaf) and `tex_flytrap.py` (trap, plant, fly);
wood and shingles from `tex_wood.py`. Axes below are glTF / three.js.

| File | Size (x × y × z) | Tris | Nodes |
|---|---|---|---|
| `magic-well.glb` | 1.98 × 2.58 × 1.64 | 16.5k | `magic_well` → `windlass`, `crank`, empties `fog_source`, `coin_drop` |
| `venus-flytrap.glb` | 3.4 × 4.1 × 3.1 | 25.4k | `venus_flytrap` → `stem_0` → … → `stem_4` → `trap` → `lobe_upper` (→ `fly_land`, `fly_hair`), `lobe_lower`, `fly` → `wing_L`, `wing_R`, `vines_L`, `vines_R`; `trap_small_1`, `trap_small_2` → `trap_small_<n>_upper`, `trap_small_<n>_lower` |

- **Well** (Candle Grove): wall of fieldstones 1.3 m across, 0.85 m to the capstone tops; two
  ivy-wound posts, shingled roof (ridge 2.5 m). The shaft (`glow_well_inner`) goes down to
  y = 0.02 and glows red just under the rim, fading into the dark. `fog_source` is at the
  shaft's centre 0.3 m below the rim (y = 0.55); `coin_drop` is 0.45 m above the opening.
  `crank` (pivot glTF (0.82, 1.55, 0)) and `windlass` (drum + rope coil, pivot (0, 1.55, 0))
  both turn about their local **X** (the axle runs left-right). Materials `stone` (+ normal),
  `wood` (+ normal), `shingle`, `ivy` (alpha MASK), `rope`, `glow_well_inner`.
- **Flytrap** (Sweet Hollow): origin at the middle of the rosette; the big head (2.6 m across)
  hangs over the front (+Z), top 4.1 m up, underside ~2.7 m. All traps hinge on their node's
  local **X**; the mouth faces local +Z, a little upward. Close: `lobe_upper` +13°,
  `lobe_lower` −13° about local X (the small traps: ±16°); the opposite signs open wider. The
  teeth of the two lobes interlock when closed. `fly` pivots in its thorax; `wing_L`/`wing_R`
  flap about their local Z (the body axis). The main stem is a chain of five rigid segments,
  `stem_0` (pivot at the ground) to `stem_4`, jointed at 20/40/58/76 % of its length with a
  dome over each joint, so bending the chain bends the stem without a seam; `trap` hangs off
  `stem_4` on its hinge line. The vines (`vines_L`, `vines_R`) pivot where they hang from the
  hinge ends, so the code keeps them hanging as the head moves. Three trigger hairs stand on
  each lobe of the big trap; the empties `fly_land` and `fly_hair` (under `lobe_upper`) mark
  where the fly lands on the roof of the mouth and where it stops by a hair.
  Materials `stem`, `leaf`, `trap_outer` (base + dim emission), `glow_trap`, `teeth` (dim
  emission), `fly_body`, `fly_wing` (alpha BLEND, double-sided), `vine` (alpha MASK).
