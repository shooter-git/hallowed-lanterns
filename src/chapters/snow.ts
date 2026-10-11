import {
  Color,
  ConeGeometry,
  CylinderGeometry,
  Group,
  HemisphereLight,
  Mesh,
  MeshStandardMaterial,
  type Object3D,
  type Ray,
  Scene,
  SphereGeometry,
  Vector2,
  Vector3,
} from 'three';
import type { GlowLight } from '../engine/glowfield.ts';
import { type Bounds, ground, GroundMask } from '../engine/ground.ts';
import { stringLights } from '../engine/lanterns.ts';
import type { LightSource } from '../engine/lights.ts';
import { loadModel } from '../engine/models.ts';
import { defaultGrade, type Grade, lerpGrade } from '../engine/post.ts';
import { PumpkinField, type PumpkinSpec } from '../engine/pumpkins.ts';
import { Path } from '../engine/rig.ts';
import { hallow, shared } from '../engine/shared.ts';
import { lerpSky, skyState, treeLine } from '../engine/sky.ts';
import { forest, lineThePath } from '../engine/trees.ts';
import { Billboards, Breath, Drift, snowflakeTexture } from '../engine/weather.ts';
import type { Chapter, ChapterContext, TapAction } from './types.ts';

/**
 * VI. October Snow — then, impossibly, it begins to snow. A snowman made of striped gourds raises
 * his corn-cob mug in a toast; icicle lights and glowing snowflakes hang in the trees; everything
 * goes hushed and you can see your breath. Near the end the snow slows, stops… and starts to rise.
 */

function rng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const SNOWMAN = new Vector3(0.6, 0, -13);

export async function build(ctx: ChapterContext): Promise<Chapter> {
  const { tier } = ctx;
  const rnd = rng(66);
  const scene = new Scene();
  const bounds: Bounds = [-40, -80, 80, 95];

  const path = new Path(
    [
      [0, 8],
      [0, -2],
      [-1.8, -9.5],
      [-2.6, -15],
      [-1, -24],
      [2.5, -34],
      [1, -46],
      [0, -56],
    ],
    3.4,
  );

  const mask = new GroundMask(bounds, 4);
  mask.stroke(path.points.filter((_, i) => i % 4 === 0).map((p) => [p.x, p.y]), 2.2, 'r', 0.6);
  mask.soften(3);
  // Trodden snow on the path (a little darker), fresh snow everywhere else.
  const floor = ground({ mask, a: ctx.surface('snow'), aScale: 1.8, b: ctx.surface('snow'), bScale: 3.1, tone: 0.85 });
  scene.add(floor);

  // Snowy woods: pale, flocked canopies.
  const treeAt = lineThePath(path.points, 4.4, { spacing: tier === 'low' ? 5.5 : 4, depth: 2, seed: 21 });
  const woods = forest(
    [
      { species: 'young', at: treeAt.filter((_, i) => i % 3 === 0) },
      { species: 'oak', at: treeAt.filter((_, i) => i % 3 === 1) },
      { species: 'tall', at: treeAt.filter((_, i) => i % 3 === 2) },
    ],
    { leafTint: new Color(0.9, 0.95, 1.0), bark: new Color(0.06, 0.05, 0.05) },
  );
  scene.add(woods.group);
  scene.add(treeLine({ radius: 110, height: 16, color: new Color(0.02, 0.025, 0.04), under: new Color(0.02, 0.03, 0.06) }));

  // The snowman: the model, or three striped gourds with a hat, a carrot and a corn-cob mug.
  let snowman: Object3D;
  let toastArm: Object3D | undefined;
  let mug: Object3D | undefined;
  const pumpkinsSpecs: PumpkinSpec[] = [];
  const model = await loadModel('snowman');
  if (model) {
    snowman = model.root;
    toastArm = model.node('arm_R');
    mug = model.node('mug');
  } else {
    snowman = new Group();
    const cream = new Color(0.82, 0.8, 0.68);
    for (const [y, r, h] of [
      [0.7, 0.78, 0.62],
      [1.62, 0.6, 0.48],
      [2.3, 0.4, 0.34],
    ] as [number, number, number][]) {
      pumpkinsSpecs.push({ position: SNOWMAN.clone().add(new Vector3(0, y, 0)), size: new Vector3(r, h, r), yaw: 0, carve: -2, skin: cream, glow: new Color(0, 0, 0) });
    }
    const black = hallow(new MeshStandardMaterial({ color: 0x0a0a0c, roughness: 0.6 }), { key: 'coal' });
    const hat = new Mesh(new CylinderGeometry(0.28, 0.3, 0.42, 20), black);
    hat.position.set(0, 2.85, 0);
    const brim = new Mesh(new CylinderGeometry(0.48, 0.48, 0.04, 24), black);
    brim.position.set(0, 2.64, 0);
    const nose = new Mesh(new ConeGeometry(0.06, 0.32, 10), hallow(new MeshStandardMaterial({ color: 0xd2541a, roughness: 0.6 }), { key: 'carrot' }));
    nose.rotation.x = Math.PI / 2;
    nose.position.set(0, 2.3, 0.48);
    const g = snowman as Group;
    g.add(hat, brim, nose);
    for (const [x, y, z] of [
      [-0.14, 2.42, 0.34],
      [0.14, 2.42, 0.34],
      [0, 1.85, 0.56],
      [0, 1.6, 0.6],
      [0, 1.35, 0.57],
    ] as [number, number, number][]) {
      const coal = new Mesh(new SphereGeometry(0.07, 10, 8), black);
      coal.scale.z = 0.5;
      coal.position.set(x, y, z);
      g.add(coal);
    }
    const bark = hallow(new MeshStandardMaterial({ color: 0x5a4430, roughness: 0.9 }), { key: 'branch' });
    const armL = new Mesh(new CylinderGeometry(0.035, 0.06, 1.2, 6), bark);
    armL.position.set(-0.85, 1.75, 0);
    armL.rotation.z = 1.0;
    const shoulderR = new Group();
    shoulderR.position.set(0.5, 1.8, 0);
    const armR = new Mesh(new CylinderGeometry(0.035, 0.06, 1.1, 6), bark);
    armR.position.set(0.45, 0.2, 0);
    armR.rotation.z = -1.2;
    const cup = new Mesh(new CylinderGeometry(0.11, 0.1, 0.24, 14), hallow(new MeshStandardMaterial({ color: 0xe8c040, roughness: 0.5 }), { key: 'corn' }));
    cup.position.set(0.95, 0.48, 0.08);
    shoulderR.add(armR, cup);
    g.add(armL, shoulderR);
    toastArm = shoulderR;
    mug = cup;
  }
  snowman.position.copy(SNOWMAN);
  scene.add(snowman);
  const pumpkins = pumpkinsSpecs.length ? new PumpkinField(pumpkinsSpecs, ctx.atlas, { detail: [40, 18], simple: [20, 10] }) : null;
  if (pumpkins) scene.add(pumpkins.group);
  const restZ = toastArm?.rotation.z ?? 0;

  // Icicle lights strung between the trees over the path, and glowing snowflakes on branches.
  const icicle = new Color(0.75, 0.88, 1);
  const runs: { from: Vector3; to: Vector3; sag: number }[] = [];
  const tmp = new Vector2();
  const tan = new Vector2();
  for (let s = 4; s < path.length - 4; s += 7) {
    path.at(s, tmp, tan);
    const nx = -tan.y;
    const nz = tan.x;
    const from = new Vector3(tmp.x + nx * 3.4, 3.4, tmp.y + nz * 3.4);
    const to = new Vector3(tmp.x - nx * 3.4, 3.4, tmp.y - nz * 3.4);
    runs.push({ from, to, sag: 0.5 });
    // Drops hanging from it.
    for (let k = 1; k < 9; k++) {
      const p = from.clone().lerp(to, k / 9);
      p.y -= 0.5 * 4 * (k / 9) * (1 - k / 9);
      runs.push({ from: p, to: p.clone().add(new Vector3(0, -0.25 - rnd() * 0.35, 0)), sag: 0 });
    }
  }
  const lights = stringLights(runs, { spacing: 0.08, color: icicle, brightness: 7, size: 0.014, glowEvery: 8, glowRadius: 2, glowIntensity: 0.06 });
  scene.add(lights.mesh);
  const flakes: { position: Vector3; size: number; color: Color; spin?: number }[] = [];
  const anchors = woods.anchors.filter(() => rnd() < 0.18).slice(0, tier === 'low' ? 18 : 40);
  for (const a of anchors) flakes.push({ position: a.clone().add(new Vector3(0, -0.4, 0)), size: 0.45 + rnd() * 0.35, color: new Color(0.7, 0.85, 1).multiplyScalar(2.2), spin: (rnd() - 0.5) * 0.3 });
  // A few on a string beside the snowman, as in the photo.
  for (let k = 0; k < 5; k++) flakes.push({ position: SNOWMAN.clone().add(new Vector3(-1.2 + k * 0.9, 3.4 - (k % 2) * 0.3, -0.8)), size: 0.35, color: new Color(0.8, 0.9, 1).multiplyScalar(2.6), spin: 0.2 });
  const ornaments = new Billboards(flakes, snowflakeTexture());
  scene.add(ornaments.mesh);

  // Falling snow.
  const snow = new Drift({ count: tier === 'low' ? 2500 : tier === 'mid' ? 4500 : 7000, box: 22, size: 0.045, color: new Color(0.85, 0.9, 1), style: 'snow' });
  scene.add(snow.points);
  const breath = new Breath();
  scene.add(breath.mesh);

  const glowLights: GlowLight[] = [...lights.lights];
  for (const f of flakes) glowLights.push({ x: f.position.x, z: f.position.z, radius: 2.4, color: new Color(0.6, 0.8, 1), intensity: 0.12, flicker: 0 });
  glowLights.push({ x: SNOWMAN.x, z: SNOWMAN.z + 1.5, radius: 4, color: new Color(1, 0.85, 0.6), intensity: 0.5, flicker: 0 });
  const sources: LightSource[] = [
    { position: SNOWMAN.clone().add(new Vector3(0, 2.4, 3)), color: new Color(1, 0.88, 0.7), intensity: 6, distance: 9 },
    ...flakes.slice(0, 20).map((f) => ({ position: f.position, color: new Color(0.7, 0.85, 1), intensity: 0.8, distance: 4 })),
  ];
  scene.add(new HemisphereLight(0x5a6c96, 0x202630, 0.35));

  const sky = skyState({ zenith: new Color(0.012, 0.016, 0.04), horizon: new Color(0.06, 0.07, 0.11), stars: 0.15 });
  const grade: Grade = { ...defaultGrade(), exposure: 1.0, bloom: 0.1, saturation: 0.95, power: 1.05, tint: new Color(0.95, 0.99, 1.08), lift: new Color(0.012, 0.014, 0.025) };

  let time = 0;
  let toasted = false;
  let toast = 0;
  let rising = 0;
  let saidRise = false;

  const chapter: Chapter = {
    scene,
    path,
    music: 'snow',
    ambience: 'snow',
    steps: 'step-snow',

    enter() {
      ctx.glow.setBounds(...bounds);
      ctx.glow.setLights(glowLights);
      ctx.glow.wave = 1e9;
      ctx.lights.sources = sources;
      lerpSky(ctx.sky.state, sky, sky, 0);
      lerpGrade(ctx.post.grade, grade, grade, 0);
      shared.uFogColor.value.set(0.05, 0.06, 0.085);
      shared.uFogDensity.value = 0.035;
      shared.uFogHeight.value = 12;
      shared.uFogGlow.value = 0.5;
      ctx.ember.presence = 1;
      ctx.ember.place(new Vector3(0, 1.8, 5));
      ctx.audio.preload('deep', ['snowflake', 'step-snow']);
      setTimeout(() => ctx.ui.say('Snow? In October?', 4.5), 3500);
    },

    update(dt) {
      time += dt;
      const w = ctx.walker;
      const e = ctx.ember;
      const scale = ctx.renderer.domElement.height / (2 * Math.tan((ctx.camera.fov * Math.PI) / 360));
      // The snow slows near the end, stops, and begins to rise — into the deep.
      const end = Math.max(0, Math.min(1, (w.s - (path.length - 16)) / 12));
      rising += (end - rising) * (1 - Math.exp(-dt * 0.8));
      snow.velocity.set(0.08, -0.6 + rising * 1.0, 0);
      if (rising > 0.5 && !saidRise) {
        saidRise = true;
        ctx.ui.say('The snowflakes slow… stop… and start to rise.', 6);
      }
      lerpGrade(ctx.post.grade, grade, { ...grade, tint: new Color(0.7, 0.88, 1.2), exposure: 1.1 }, rising);
      shared.uFogColor.value.set(0.05, 0.06, 0.085).lerp(new Color(0.01, 0.04, 0.12), rising);
      snow.update(dt, scale);
      if (!ctx.reducedMotion) breath.update(dt, ctx.camera);
      breath.mesh.visible = rising < 0.5 && !ctx.reducedMotion;

      // The snowman raises his mug to you.
      const near = Math.hypot(w.position.x - SNOWMAN.x, w.position.z - SNOWMAN.z) < 6;
      if (near && !toasted) {
        toasted = true;
        toast = 0.001;
        void ctx.audio.sfx('snowflake', { at: SNOWMAN.clone().add(new Vector3(0.9, 2.2, 0)), volume: 0.8 });
      }
      if (toast > 0) {
        toast += dt;
        const k = Math.sin(Math.min(1, toast / 2.6) * Math.PI);
        if (toastArm) toastArm.rotation.z = restZ + k * 0.9;
        if (toast > 2.6) toast = 0;
      }
      // The Ember warms itself by the mug, then leads on.
      if (near && mug) e.target.copy(mug.getWorldPosition(new Vector3())).add(new Vector3(0.3, 0.45, 0.3));
      else {
        path.at(Math.min(path.length, w.s + 4.5), tmp);
        e.target.set(tmp.x, 1.7 + Math.sin(time) * 0.2, tmp.y);
      }
      ctx.glow.moving.length = 0;
      ctx.glow.moving.push(e.glow);
      pumpkins?.update(ctx.camera, dt);
    },

    pick(ray: Ray): TapAction | null {
      // Tap a glowing snowflake: it rings.
      let best = -1;
      let bestD = 0.5;
      flakes.forEach((f, i) => {
        const d = Math.sqrt(ray.distanceSqToPoint(f.position)) / Math.max(1, f.position.distanceTo(ray.origin) * 0.08);
        if (d < bestD) {
          bestD = d;
          best = i;
        }
      });
      if (best >= 0) {
        const f = flakes[best] as (typeof flakes)[number];
        return () => {
          ornaments.setColor(best, new Color(1, 1, 1).multiplyScalar(6));
          setTimeout(() => ornaments.setColor(best, f.color), 400);
          void ctx.audio.sfx('snowflake', { at: f.position, volume: 0.8 });
        };
      }
      if (ray.distanceSqToPoint(SNOWMAN.clone().add(new Vector3(0, 1.6, 0))) < 1.2)
        return () => {
          toast = 0.001;
          void ctx.audio.sfx('snowflake', { at: SNOWMAN, volume: 0.7, rate: 0.8 });
        };
      // Anywhere else: catch a snowflake.
      return () => void ctx.audio.sfx('snowflake', { volume: 0.35, rate: 1 + Math.random() * 0.5 });
    },

    finished() {
      return ctx.walker.s > path.length - 1.2;
    },

    dispose() {
      woods.dispose();
      snow.dispose();
      breath.dispose();
      ornaments.dispose();
      pumpkins?.dispose();
      floor.geometry.dispose();
      lights.mesh.geometry.dispose();
    },
  };
  return chapter;
}
