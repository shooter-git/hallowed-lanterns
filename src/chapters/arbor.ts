import {
  BoxGeometry,
  Color,
  DirectionalLight,
  HemisphereLight,
  InstancedMesh,
  Matrix4,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Quaternion,
  type Ray,
  Scene,
  SphereGeometry,
  Vector2,
  Vector3,
} from 'three';
import { CARVE } from '../engine/carvings.ts';
import { FogBank } from '../engine/fogbank.ts';
import type { GlowLight } from '../engine/glowfield.ts';
import { type Bounds, ground, GroundMask } from '../engine/ground.ts';
import type { LightSource } from '../engine/lights.ts';
import { defaultGrade, type Grade, lerpGrade } from '../engine/post.ts';
import { PUMPKIN_ORANGE, PumpkinField, type PumpkinSpec } from '../engine/pumpkins.ts';
import { instanceModel, loadModel, modelSize } from '../engine/models.ts';
import { Path } from '../engine/rig.ts';
import { aroundPath, Terrain } from '../engine/terrain.ts';
import { hallow, shared } from '../engine/shared.ts';
import { lerpSky, skyState, treeLine } from '../engine/sky.ts';
import { forest } from '../engine/trees.ts';
import { buildEntrance } from './entrance.ts';
import type { Chapter, ChapterContext, TapAction } from './types.ts';

/**
 * I. The Arbor of Faces — sunset. A gravel lane under a long pergola hung with hundreds of
 * carved jack-o'-lanterns. They wake in a wave as the sun goes; near the end, one of them loses
 * its flame — and the flame looks back at you.
 */

const LANE_START = 2;
const ENTRANCE = new Vector3(-6.5, 0, 21.5);
const ENTRANCE_YAW = 0.82;
const LANE_END = -50;
const BAY = 4;
const HALF = 2.75;

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

export async function build(ctx: ChapterContext): Promise<Chapter> {
  const { tier } = ctx;
  const rnd = rng(20261011);
  const scene = new Scene();
  const bounds: Bounds = [-40, -80, 80, 125];

  // --- The walk: in under the pergola, down the lane, then off left into the trees. ---
  // You begin in front of the hay-bale sign, then walk to the pergola.
  const path = new Path(
    [
      [1, 27.5],
      [1, 20],
      [0, 9],
      [0, 0],
      [0, -20],
      [0, -40],
      [0, -50],
      [-1.5, -56],
      [-5, -61],
      [-9, -64],
    ],
    (s) => (s < 17 ? 7 : s < 77 ? 3.4 : 2.4),
  );
  const terrain = new Terrain(bounds, aroundPath(path, { profile: (s) => -0.022 * s + 0.22 * Math.sin(s / 9) + (s > 77 ? -0.06 * (s - 77) : 0) + (s < 17 ? 0.012 * (17 - s) : 0), bank: 0.05, rough: 0.45, seed: 12 }));

  // --- The entrance: the hay-bale wall with the night's name. ---
  const entrance = buildEntrance(ctx, ENTRANCE, ENTRANCE_YAW, rnd);
  scene.add(entrance.group, ...entrance.world);

  // --- Ground: gravel lane, dry grass all around. ---
  const mask = new GroundMask(bounds, 4);
  const lane: [number, number][] = path.points.filter((_, i) => i % 4 === 0).map((p) => [p.x, p.y]);
  mask.stroke(lane, 4.6, 'r');
  mask.stroke(lane.slice(Math.floor(lane.length * 0.25), Math.floor(lane.length * 0.85)), 5, 'g', 0.55);
  for (let i = 0; i < 14; i++) mask.blob((rnd() - 0.5) * 6, LANE_START - rnd() * 52, 2 + rnd() * 3, 'g', 0.5);
  mask.soften(4);
  const floor = ground({
    mask,
    a: ctx.surface('gravel'),
    aScale: 1.6,
    b: ctx.surface('dryGrass'),
    bScale: 2.2,
    tone: 0.75,
  });
  scene.add(floor);

  // --- The pergola: dark timber posts, beams along the lane, cross beams each bay. ---
  const timber = hallow(new MeshStandardMaterial({ color: 0x2a1d14, roughness: 0.92 }), { key: 'timber' });
  const bays = Math.round((LANE_START - LANE_END) / BAY);
  const posts = new InstancedMesh(new BoxGeometry(0.16, 3.5, 0.16), timber, (bays + 1) * 2);
  const beams = new InstancedMesh(new BoxGeometry(0.12, 0.2, BAY + 0.1), timber, bays * 2);
  const cross = new InstancedMesh(new BoxGeometry(HALF * 2 + 0.4, 0.14, 0.1), timber, bays + 1);
  const m = new Matrix4();
  for (let i = 0; i <= bays; i++) {
    const z = LANE_START - i * BAY;
    for (const side of [-1, 1]) {
      m.makeRotationY((rnd() - 0.5) * 0.04).setPosition(side * HALF, 1.75, z);
      posts.setMatrixAt(i * 2 + (side > 0 ? 1 : 0), m);
    }
    m.identity().setPosition(0, 3.48, z);
    cross.setMatrixAt(i, m);
    if (i < bays) {
      for (const side of [-1, 1]) {
        m.identity().setPosition(side * HALF, 3.42, z - BAY / 2);
        beams.setMatrixAt(i * 2 + (side > 0 ? 1 : 0), m);
      }
    }
  }
  // The real pergola (Blender: weathered posts, braces, beams and wires) where we have it.
  const bayModel = await loadModel('arbor', { glowReceive: 1 });
  if (bayModel) {
    const size = modelSize(bayModel);
    const scale = new Vector3((HALF * 2 + 0.2) / size.x, 3.55 / size.y, BAY / size.z);
    const at: Matrix4[] = [];
    for (let i = 0; i < bays; i++) at.push(new Matrix4().compose(new Vector3(0, 0, LANE_START - (i + 0.5) * BAY), new Quaternion(), scale));
    scene.add(instanceModel(bayModel, at, { skip: 'end_frame' }));
    // The far end of the last bay closes the pergola.
    scene.add(instanceModel(bayModel, [at[at.length - 1] as Matrix4], { only: 'end_frame' }));
  } else {
    for (const mesh of [posts, beams, cross]) {
      mesh.computeBoundingSphere();
      scene.add(mesh);
    }
  }

  // --- Fence posts and barbed wire out in the field on the right. ---
  const fence = new InstancedMesh(new BoxGeometry(0.12, 1.5, 0.12), timber, 26);
  for (let i = 0; i < 26; i++) {
    m.makeRotationZ((rnd() - 0.5) * 0.08).setPosition(7.5 + (rnd() - 0.5) * 0.2, 0.75, 6 - i * 3.2);
    fence.setMatrixAt(i, m);
  }
  fence.computeBoundingSphere();
  scene.add(fence);

  // --- The lanterns. ---
  const specs: PumpkinSpec[] = [];
  // As packed as the real arbor: eight rows overhead, two tiers along each side, nearly touching.
  const overheadRows = tier === 'low' ? [-2.0, -1.2, -0.45, 0.45, 1.2, 2.0] : [-2.2, -1.65, -1.1, -0.55, 0.55, 1.1, 1.65, 2.2];
  const sideRows = tier === 'low' ? [1.4] : [1.35, 2.2];
  const spacing = tier === 'low' ? 0.48 : 0.36;
  const lanternColour = (r: number) => {
    if (r < 0.025) return new Color(1, 0.08, 0.1).multiplyScalar(4);
    if (r < 0.045) return new Color(1, 0.1, 0.55).multiplyScalar(3.5);
    if (r < 0.06) return new Color(0.6, 0.18, 1).multiplyScalar(3.5);
    return new Color(1, 0.5 + rnd() * 0.14, 0.12 + rnd() * 0.06).multiplyScalar(3 + rnd() * 1.4);
  };
  const face = () => {
    const r = rnd();
    if (r < 0.04) return CARVE.creatures[Math.floor(rnd() * CARVE.creatures.length)] as number;
    if (r < 0.05) return CARVE.heartSkull;
    return CARVE.faces[Math.floor(rnd() * CARVE.faces.length)] as number;
  };
  const add = (x: number, y: number, z: number, yaw: number, hang: number) => {
    const w = 0.15 + rnd() * 0.035;
    const h = w * (1.12 + rnd() * 0.22);
    const bay = Math.floor((LANE_START - z) / BAY);
    specs.push({
      position: new Vector3(x + (rnd() - 0.5) * 0.04, y + (rnd() - 0.5) * 0.08, z),
      size: new Vector3(w, h, w * (0.95 + rnd() * 0.1)),
      yaw: yaw + (rnd() - 0.5) * 0.35,
      tilt: (rnd() - 0.5) * 0.12,
      carve: face(),
      skin: (PUMPKIN_ORANGE[Math.floor(rnd() * PUMPKIN_ORANGE.length)] as Color).clone().multiplyScalar(0.9 + rnd() * 0.2),
      glow: lanternColour(rnd()),
      phase: rnd(),
      seq: LANE_START - z + rnd() * 1.2,
      hang,
      chunk: `bay${bay}`,
    });
  };
  for (let z = LANE_START - 0.3; z > LANE_END + 0.2; z -= spacing) {
    for (const x of overheadRows) add(x, 3.05 - Math.abs(x) * 0.09 + (rnd() - 0.5) * 0.1, z + (rnd() - 0.5) * 0.08, 0, 0.3);
    for (const y of sideRows) {
      add(-HALF - 0.05, y, z + (rnd() - 0.5) * 0.1, Math.PI / 2, 0.22);
      add(HALF + 0.05, y, z + (rnd() - 0.5) * 0.1, -Math.PI / 2, 0.22);
    }
  }
  // The one that holds the Ember: low over the middle of the lane, near the end.
  const emberZ = -43.2;
  let emberIndex = 0;
  let bestD = 1e9;
  specs.forEach((s, i) => {
    const d = Math.abs(s.position.z - emberZ) + Math.abs(s.position.x - 0.45) * 2;
    if (d < bestD && s.position.y > 2.5) {
      bestD = d;
      emberIndex = i;
    }
  });
  const emberSpec = specs[emberIndex] as PumpkinSpec;
  emberSpec.carve = CARVE.happy[0] as number;
  emberSpec.glow = new Color(1, 0.55, 0.16).multiplyScalar(5);

  const pumpkins = new PumpkinField(specs, ctx.atlas, {
    detail: tier === 'low' ? [22, 10] : [28, 12],
    simple: [12, 6],
  });
  pumpkins.detailDistance = tier === 'low' ? 7 : 11;
  pumpkins.wave = -10;
  scene.add(pumpkins.group);

  // --- Path lights: purple and orange LED strings along both edges of the gravel. ---
  const ledGeo = new SphereGeometry(0.022, 6, 4);
  const ledMat = hallow(new MeshBasicMaterial({ color: 0xffffff }), { key: 'led' });
  const ledPositions: { p: Vector3; c: Color }[] = [];
  const purple = new Color(0.55, 0.12, 1.0);
  const orange = new Color(1.0, 0.35, 0.05);
  for (let z = LANE_START + 3; z > LANE_END; z -= 0.28) {
    for (const side of [-1, 1]) {
      const c = rnd() < 0.72 ? purple : orange;
      ledPositions.push({ p: new Vector3(side * 2.05 + (rnd() - 0.5) * 0.05, 0.03, z), c });
    }
  }
  const leds = new InstancedMesh(ledGeo, ledMat, ledPositions.length);
  ledPositions.forEach((l, i) => {
    m.makeTranslation(l.p.x, l.p.y, l.p.z);
    leds.setMatrixAt(i, m);
    leds.setColorAt(i, l.c.clone().multiplyScalar(14));
  });
  leds.computeBoundingSphere();
  scene.add(leds);

  // --- Glow field: every lantern and LED pools light on the gravel, the posts and the fog. ---
  const glowLights: GlowLight[] = pumpkins.glowLights(2.4, tier === 'low' ? 0.12 : 0.06);
  for (const l of ledPositions) {
    glowLights.push({ x: l.p.x, z: l.p.z, y: l.p.y, radius: 0.6, color: l.c, intensity: 0.35, flicker: 0 });
  }
  glowLights.push(...entrance.glow);

  // --- Light, sky, fog. ---
  const hemi = new HemisphereLight(0xffc9a0, 0x1a1210, 0.5);
  const sun = new DirectionalLight(0xffa860, 1.0);
  scene.add(hemi, sun, sun.target);
  const far = treeLine({ radius: 150, height: 16, color: new Color(0.012, 0.012, 0.02), under: new Color(0.05, 0.03, 0.03) });
  scene.add(far);
  // Real woods along the left of the lane (behind the pumpkins, as in the photo) and behind the
  // hay-bale wall; the field stays open on the right.
  const woodAt: { x: number; z: number; scale: number; yaw: number }[] = [];
  // None on the path where it turns off into them (one stood in the middle of it at the end).
  const onPath = (x: number, z: number) => {
    const n = path.nearest(new Vector2(x, z));
    const c = path.points[n.index] as Vector2;
    return Math.hypot(x - c.x, z - c.y) < n.width / 2 + 2.5;
  };
  for (let z = 30; z > -66; z -= tier === 'low' ? 4.5 : 3.2) {
    for (let row = 0; row < (tier === 'low' ? 2 : 3); row++) {
      const x = -6.5 - row * 4.5 - rnd() * 2.5 + (z > 12 ? -6 : 0);
      const tree = { x, z: z + (rnd() - 0.5) * 2.5, scale: 0.85 + rnd() * 0.5, yaw: rnd() * 6.28 };
      if (!onPath(tree.x, tree.z)) woodAt.push(tree);
    }
  }
  const woods = forest(
    [
      { species: 'oak', at: woodAt.filter((_, i) => i % 3 === 0) },
      { species: 'tall', at: woodAt.filter((_, i) => i % 3 === 1) },
      { species: 'young', at: woodAt.filter((_, i) => i % 3 === 2) },
    ],
    { leafTint: new Color(0.4, 0.42, 0.36) },
  );
  scene.add(woods.group);

  const fog = new FogBank({
    bounds: mask.bounds,
    mask: mask.texture(),
    slices: tier === 'low' ? 4 : 9,
    height: 1.3,
    tint: new Color(0.04, 0.026, 0.038),
    density: 0.075,
    glow: 0.9,
    wind: new Vector2(0.18, -0.12),
  });
  scene.add(fog.mesh);

  // Sunset at the entrance, dusk by the time you reach the trees.
  const sunset = skyState({
    zenith: new Color(0.05, 0.08, 0.24),
    horizon: new Color(1.0, 0.48, 0.2),
    sunColor: new Color(1.0, 0.5, 0.2),
    sunDir: new Vector3(0.35, 0.03, -1).normalize(),
    sunGlow: 1.1,
    stars: 0,
    lightPollution: new Color(0.05, 0.03, 0.02),
    clouds: 0.5,
  });
  const dusk = skyState({
    zenith: new Color(0.012, 0.02, 0.07),
    horizon: new Color(0.2, 0.11, 0.14),
    sunColor: new Color(0.8, 0.3, 0.15),
    sunDir: new Vector3(0.35, -0.08, -1).normalize(),
    sunGlow: 0.35,
    stars: 0.35,
    lightPollution: new Color(0.03, 0.018, 0.012),
    clouds: 0.42,
  });
  const gradeSunset: Grade = {
    ...defaultGrade(),
    exposure: 1.0,
    bloom: 0.1,
    // AgX pales bright warm light: a richer look keeps the sunset's colour.
    saturation: 1.36,
    power: 1.3,
    tint: new Color(1.04, 0.98, 0.94),
    lift: new Color(0.004, 0.003, 0.009),
  };
  const gradeDusk: Grade = {
    ...defaultGrade(),
    exposure: 1.3,
    bloom: 0.11,
    saturation: 1.26,
    power: 1.26,
    tint: new Color(0.96, 0.97, 1.06),
    lift: new Color(0.003, 0.004, 0.012),
  };
  // Cooler haze away from the sun; toward it the sky's own light warms it (see hlApplyFog).
  const fogSunset = new Color(0.095, 0.07, 0.085);
  const fogDusk = new Color(0.035, 0.035, 0.06);

  // The lights that follow you.
  const sources: LightSource[] = [...entrance.sources, ...specs.filter((_, i) => i % 3 === 0).map((s) => ({
    position: s.position.clone().add(new Vector3(0, -0.05, 0.12)),
    color: s.glow.clone().multiplyScalar(1 / Math.max(1, s.glow.r)),
    intensity: 0.9,
    distance: 4.5,
    phase: s.phase as number,
  }))];

  // --- Story state. ---
  let time = 0;
  let waveStarted = -1;
  let emberStage = 0; // 0 waiting, 1 sputtering, 2 out and born, 3 leading
  let emberClock = 0;
  const happyUntil = new Map<number, { until: number; carve: number }>();
  const tmp = new Vector3();
  const tmp2 = new Vector2();

  const chapter: Chapter = {
    scene,
    path,
    terrain,
    startYaw: Math.atan2(-(ENTRANCE.x - 1), -(ENTRANCE.z + 1.5 - 27.5)) - 0.12,
    // Over the title: the sun going down over the field, the lane and its pergola off to the left,
    // the hay-bale sign (which says the same as the title) just out of sight.
    titleView: { yaw: -0.34, pitch: 0.09, leftOf: 0.2 },
    music: 'arbor',
    ambience: 'arbor',
    steps: 'step-gravel',

    enter() {
      ctx.glow.setBounds(...bounds);
      ctx.glow.setLights(glowLights);
      ctx.glow.wave = -10;
      ctx.glow.waveSoftness = 1.5;
      ctx.lights.sources = sources;
      ctx.ember.presence = 0;
      // Clear evening air: the field keeps its shape out to the trees.
      shared.uFogDensity.value = 0.0055;
      shared.uFogHeight.value = 5;
      shared.uFogGlow.value = 0.55;
      ctx.audio.preload('arbor', ['pumpkin-flare', 'ember-chime-arbor', 'step-gravel']);
      ctx.audio.preload('grove', ['well-coin']);
    },

    update(dt) {
      time += dt;
      const w = ctx.walker;
      const progress = Math.min(1, Math.max(0, w.s / (path.length - 6)));

      // The wave: the lanterns wake from the entrance to the far end, as you come near.
      if (waveStarted < 0 && (w.position.z < 15 || time > 45)) waveStarted = time + 0.4;
      if (waveStarted >= 0 && time > waveStarted) {
        const front = (time - waveStarted) * 6.5 - 4;
        pumpkins.wave = front;
        ctx.glow.wave = front;
        if (time - waveStarted > 0.4 && time - waveStarted < 0.5) ctx.ui.say('The sun is going down. The lanterns are waking up.', 6);
      }

      // Sky and light: sunset to dusk as you walk.
      const t = progress ** 1.2;
      lerpSky(ctx.sky.state, sunset, dusk, t);
      lerpGrade(ctx.post.grade, gradeSunset, gradeDusk, t);
      shared.uFogColor.value.copy(fogSunset).lerp(fogDusk, t);
      ctx.sky.mesh.material.uniforms.uSunColor!.value = ctx.sky.state.sunColor;
      // Backlit by the low sun: the sky's fill is soft, so the land stays darker than the sunset.
      hemi.intensity = 0.36 * (1 - t) + 0.1 * t;
      hemi.color.setRGB(1, 0.78 - 0.3 * t, 0.62 - 0.1 * t);
      sun.intensity = 1.0 * (1 - t) ** 2;
      sun.position.copy(ctx.sky.state.sunDir).multiplyScalar(50).add(ctx.camera.position);
      sun.target.position.copy(ctx.camera.position);

      // Faces that were tapped smile for a while, then go back.
      for (const [i, h] of happyUntil) {
        if (time > h.until) {
          pumpkins.setCarve(i, h.carve);
          happyUntil.delete(i);
        }
      }

      // The Ember.
      const e = ctx.ember;
      const ep = emberSpec.position;
      if (emberStage === 0 && w.position.z < emberZ + 9) {
        emberStage = 1;
        emberClock = 0;
      }
      if (emberStage === 1) {
        emberClock += dt;
        // Sputters: bright, dim, bright, out.
        const k = emberClock;
        const lvl = k < 1.6 ? 1 + Math.sin(k * 22) * 0.6 * Math.min(1, k) : Math.max(0, 1 - (k - 1.6) * 3);
        pumpkins.setLevel(emberIndex, lvl);
        if (k > 1.6 && emberStage === 1) {
          emberStage = 2;
          emberClock = 0;
          e.place(tmp.copy(ep).add(new Vector3(0, -0.02, 0.1)));
          e.agility = 1.6;
          // the cue sings the motif itself (the chime answers a few seconds later, as the Ember leads on)
          void ctx.audio.cue('ember-born', 0.9);
        }
      }
      if (emberStage === 2) {
        emberClock += dt;
        e.presence = Math.min(1, emberClock * 1.5);
        e.excitement = Math.max(0, 1 - emberClock * 0.5);
        // Hops out and comes to look at you, just above eye height, a little way ahead.
        const look = tmp.set(w.position.x, 0, w.position.z).add(new Vector3(0.4, 1.85, -2.2));
        if (emberClock > 0.6) e.target.copy(look);
        if (emberClock > 1.4 && emberClock < 1.5) ctx.ui.say('One little flame has other plans.', 5);
        if (emberClock > 4.5) {
          emberStage = 3;
          e.agility = 2.0;
          // its chime once the birth cue has sung the motif through (the two never overlap)
          setTimeout(() => void ctx.audio.sfx('ember-chime-arbor', { at: e.position, volume: 0.7 }), 3600);
        }
      }
      if (emberStage === 3) {
        // Leads the way, a few metres ahead; waits if you stop.
        path.at(Math.min(path.length, w.s + 4.5), tmp2);
        e.target.set(tmp2.x, 1.5 + Math.sin(time * 0.7) * 0.25, tmp2.y);
        e.presence = 1;
        if (w.auto) w.autoTarget = null;
      }

      ctx.glow.moving.length = 0;
      if (e.presence > 0) ctx.glow.moving.push(e.glow);
      fog.walkers[0]?.set(w.position.x, w.position.z);
      fog.update();
      pumpkins.update(ctx.camera, dt);
      entrance.pumpkins.update(ctx.camera, dt);
    },

    pick(ray: Ray): TapAction | null {
      const i = pumpkins.pick(ray, 25);
      if (i < 0 || i === emberIndex) return null;
      return () => {
        pumpkins.flare(i);
        const s = specs[i] as PumpkinSpec;
        if (!happyUntil.has(i) && s.carve !== CARVE.heartSkull) {
          happyUntil.set(i, { until: time + 4, carve: s.carve });
          pumpkins.setCarve(i, CARVE.happy[Math.floor(Math.random() * CARVE.happy.length)] as number);
        }
        void ctx.audio.sfx('pumpkin-flare', { at: s.position, volume: 0.8 }); // its chime at its own pitch (in key)
      };
    },

    finished() {
      return emberStage === 3 && ctx.walker.s > path.length - 1.2;
    },

    dispose() {
      terrain.dispose();
      woods.dispose();
      entrance.dispose();
      pumpkins.dispose();
      fog.dispose();
      floor.geometry.dispose();
      for (const mesh of [posts, beams, cross, fence, leds]) mesh.geometry.dispose();
      timber.dispose();
      ledMat.dispose();
    },
  };
  if (import.meta.env.DEV)
    (window as unknown as { arbor: unknown }).arbor = { pumpkins, specs, glowLights, skip: (s: number) => (time += s) };
  return chapter;
}
