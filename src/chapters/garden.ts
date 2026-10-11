import { Box3, Color, HemisphereLight, type Object3D, type Ray, Scene, Vector2, Vector3 } from 'three';
import type { GlowLight } from '../engine/glowfield.ts';
import { type Bounds, ground, GroundMask } from '../engine/ground.ts';
import { type LanternSpec, LanternField, stringLights } from '../engine/lanterns.ts';
import type { LightSource } from '../engine/lights.ts';
import { loadModel } from '../engine/models.ts';
import { defaultGrade, type Grade, lerpGrade } from '../engine/post.ts';
import { archway, reedFence, standIn, walkwayFrame } from '../engine/props.ts';
import { PUMPKIN_ORANGE, PumpkinField, type PumpkinSpec } from '../engine/pumpkins.ts';
import { Path } from '../engine/rig.ts';
import { owl } from '../scenes/owl.ts';
import { aroundPath, heightAt, onGround, Terrain } from '../engine/terrain.ts';
import { shared } from '../engine/shared.ts';
import { lerpSky, skyState, treeLine } from '../engine/sky.ts';
import { woodland } from '../engine/canopy.ts';
import { forest, lineThePath } from '../engine/trees.ts';
import type { Chapter, ChapterContext, TapAction } from './types.ts';

/**
 * III. The Lantern Garden — nightfall. Through a white archway into a tunnel of red lanterns with
 * gold tassels; the Ember runs ahead lighting them. Then the trees open onto the Lantern Sky — one
 * great tree hung with hundreds of lanterns — and a little lounge beneath it, the one place in the
 * night where you can sit down.
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

const TUNNEL_END = -24;
const SKY_TREE = new Vector3(-2, 0, -54);
const SEAT = new Vector3(9.2, 0, -31.2);
const OWL = new Vector3(-7.6, 0, -29.5);
const OWL_YAW = 1.05;

export async function build(ctx: ChapterContext): Promise<Chapter> {
  const { tier } = ctx;
  const rnd = rng(303);
  const scene = new Scene();
  const bounds: Bounds = [-40, -85, 80, 100];

  const path = new Path(
    [
      [0, 9],
      [0, 0],
      [0, TUNNEL_END],
      [2.5, -30],
      [7, -32.5],
      [4, -37],
      [-4, -39],
      [-12, -38],
      [-19, -33],
    ],
    (s) => (s < 34 ? 2.6 : 6),
  );
  const terrain = new Terrain(bounds, aroundPath(path, { profile: (s) => (s < 25 ? 0 : 0.028 * (s - 25)) + 0.12 * Math.sin(s / 7), bank: 0.03, rough: 0.25, seed: 58 }));

  // Ground: trodden grass path through a lawn.
  const mask = new GroundMask(bounds, 4);
  const line: [number, number][] = path.points.filter((_, i) => i % 4 === 0).map((p) => [p.x, p.y]);
  mask.stroke(line, 2.4, 'r', 0.9);
  mask.blob(SEAT.x, SEAT.z, 4, 'r', 0.5);
  mask.soften(3);
  const floor = ground({ mask, a: ctx.surface('dryGrass'), aScale: 2, b: ctx.surface('lawn'), bScale: 2.2, tone: 0.8 });
  scene.add(floor);

  // The archway and the covered tunnel.
  const arch = archway(4.8, 4.4, 0.55, 0.9);
  arch.position.set(0, 0, 1.5);
  scene.add(arch);
  scene.add(walkwayFrame(1, TUNNEL_END, 2.15, 3.6, 3.2));

  // Reed fences: both walls of the tunnel, the arc in front of the Lantern Sky, the lounge's back.
  const fenceArc: [number, number][] = [];
  for (let a = -1.05; a <= 1.05; a += 0.15) fenceArc.push([SKY_TREE.x + Math.sin(a) * 15, SKY_TREE.z + Math.cos(a) * 15]);
  const lounge: [number, number][] = [
    [5.2, -34.2],
    [9, -34.6],
    [13.2, -33.6],
  ];
  const fences = reedFence(
    [
      [[-2.35, 0.8], [-2.35, TUNNEL_END + 0.5]],
      [[2.35, 0.8], [2.35, TUNNEL_END + 0.5]],
      fenceArc,
      lounge,
    ],
    1.9,
  );
  scene.add(fences);

  // Warm white fairy lights in swags along every fence.
  const runs: { from: Vector3; to: Vector3; sag: number }[] = [];
  for (const x of [-2.3, 2.3]) {
    for (let z = 0.5; z > TUNNEL_END; z -= 2.2) {
      runs.push({ from: new Vector3(x, 1.75, z), to: new Vector3(x, 1.75, z - 2.2), sag: 0.45 });
      runs.push({ from: new Vector3(x, 1.0, z - 1.1), to: new Vector3(x, 1.0, z - 3.3), sag: 0.35 });
    }
  }
  const swag = (pts: [number, number][], h: number, sag: number) => {
    for (let i = 0; i < pts.length - 1; i++) {
      const [x0, z0] = pts[i] as [number, number];
      const [x1, z1] = pts[i + 1] as [number, number];
      runs.push({ from: new Vector3(x0, h, z0), to: new Vector3(x1, h, z1), sag });
    }
  };
  swag(fenceArc, 1.8, 0.35);
  swag(fenceArc, 1.0, 0.25);
  swag(lounge, 1.75, 0.4);
  swag(lounge, 1.1, 0.3);
  const warm = new Color(1, 0.78, 0.48);
  const fairy = stringLights(runs, { spacing: tier === 'low' ? 0.3 : 0.2, color: warm, brightness: 9, glowEvery: 4, glowRadius: 1.4, glowIntensity: 0.07 });
  scene.add(fairy.mesh);

  // The lanterns: the tunnel (dark until the Ember lights them), the Lantern Sky, the lounge.
  const specs: LanternSpec[] = [];
  const tunnelLanterns: number[] = [];
  const red = (k: number) => new Color(1, 0.06 + rnd() * 0.06, 0.035).multiplyScalar(k * 0.65);
  const columns = tier === 'low' ? [-1.5, -0.5, 0.5, 1.5] : [-1.75, -1.05, -0.35, 0.35, 1.05, 1.75];
  for (let z = 0.2; z > TUNNEL_END + 0.5; z -= tier === 'low' ? 0.75 : 0.5) {
    for (const x of columns) {
      const y = 2.35 + rnd() * 1.05;
      tunnelLanterns.push(specs.length);
      specs.push({ position: new Vector3(x + (rnd() - 0.5) * 0.3, y, z + (rnd() - 0.5) * 0.3), radius: 0.15 + rnd() * 0.04, glow: red(2.4 + rnd()), phase: rnd(), hang: 3.6 - y - 0.15, tassel: 0.36 });
    }
  }
  const skyCount = tier === 'low' ? 320 : tier === 'mid' ? 760 : 1000;
  const skyStart = specs.length;
  for (let i = 0; i < skyCount; i++) {
    const a = rnd() * Math.PI * 2;
    const r = Math.sqrt(rnd()) * 19;
    const x = SKY_TREE.x + Math.cos(a) * r;
    const z = SKY_TREE.z + Math.sin(a) * r * 0.85;
    const y = 3.2 + rnd() * 13 * (1 - (r / 19) * 0.5);
    const kind = rnd();
    const glow = kind < 0.62 ? red(2.6) : kind < 0.82 ? new Color(1, 0.08, 0.3).multiplyScalar(1.6) : new Color(1, 0.55, 0.22).multiplyScalar(1.5);
    specs.push({ position: new Vector3(x, y, z), radius: 0.16 + rnd() * 0.07, glow, phase: rnd(), hang: 1 + rnd() * 2, tassel: 0.32 });
  }
  const hookLanterns: number[] = [];
  const hooks = [
    [5.4, -33.4],
    [6.6, -33.8],
    [8.0, -34.0],
    [10.6, -34.0],
    [11.9, -33.6],
    [12.9, -33.0],
    [4.6, -31],
  ];
  for (const [x, z] of hooks) {
    hookLanterns.push(specs.length);
    specs.push({ position: new Vector3(x as number, 1.55 + rnd() * 0.35, z as number), radius: 0.17, glow: red(2.8), phase: rnd(), tassel: 0.3 });
  }
  const lanterns = new LanternField(specs, { segments: tier === 'low' ? [10, 7] : [14, 9] });
  scene.add(lanterns.group);
  void skyStart;
  for (const i of tunnelLanterns) lanterns.setLevel(i, 0.04);

  // The Lantern Sky's great tree, and woods around the clearing.
  const big = forest([{ species: 'oak', at: [{ x: SKY_TREE.x, z: SKY_TREE.z, scale: 2.1, yaw: 0.6 }] }], { leafTint: new Color(0.35, 0.42, 0.33) });
  scene.add(big.group);
  const woodsAt = lineThePath(
    [
      ...Array.from({ length: 30 }, (_, i) => ({ x: -3.5, y: 2 - i })),
      ...Array.from({ length: 30 }, (_, i) => ({ x: 3.5, y: 2 - i })),
    ],
    2.2,
    { spacing: 4, depth: 2, seed: 9 },
  ).filter((t) => Math.abs(t.x) > 4.5);
  const woods = forest([
    { species: 'tall', at: woodsAt.filter((_, i) => i % 2 === 0) },
    { species: 'young', at: woodsAt.filter((_, i) => i % 2 === 1) },
  ]);
  scene.add(woods.group);
  const canopy = woodland(path, {
    canopy: [5.2, 9.5], reach: 11, skyGap: 0.35, density: tier === 'low' ? 1.2 : 2, wallFrom: 3.2, wallTo: 14, wallHeight: 5, wallDensity: tier === 'low' ? 3 : 4,
    tint: new Color(0.4, 0.46, 0.42), seed: 21,
    // Keep the Lantern Sky open above and around its tree, and the lounge's lanterns clear.
    clear: (x, z, y) =>
      (Math.hypot(x - SKY_TREE.x, z - SKY_TREE.z) < 17 && y > 2.2) ||
      (Math.hypot(x - SEAT.x, z - SEAT.z) < 3.5 && y < 3) ||
      (Math.hypot(x - OWL.x, z - OWL.z) < 6.5 && y < 6.5),
  });
  scene.add(canopy.mesh);
  scene.add(treeLine({ radius: 110, height: 17, color: new Color(0.005, 0.007, 0.018), under: new Color(0.06, 0.015, 0.02) }));

  // The lounge: a pallet sofa with a hay-bale seat, pallets of real pumpkins, lanterns on hooks.
  const sofa = await loadModel('pallet-sofa');
  const seatObject: Object3D = sofa?.root ?? standIn(new Vector3(2.2, 0.85, 0.9), new Color(0.35, 0.12, 0.08), new Vector3());
  seatObject.position.copy(SEAT).add(new Vector3(0, 0, -0.9));
  seatObject.rotation.y = 0;
  scene.add(seatObject);
  const pallet = await loadModel('pallet');
  for (const [x, z, yaw] of [
    [9.2, -28.4, 0.05],
    [6, -29.2, 0.4],
  ] as [number, number, number][]) {
    const p = pallet?.root ?? standIn(new Vector3(1.2, 0.14, 1.0), new Color(0.3, 0.22, 0.15), new Vector3());
    p.position.set(x, 0, z);
    p.rotation.y = yaw;
    scene.add(p);
  }
  const hay = await loadModel('hay-bale');
  if (hay) {
    hay.root.position.set(11.8, 0, -31.8);
    scene.add(hay.root);
  }
  const shepherd = await loadModel('shepherd-hook');
  if (shepherd) {
    for (const [x, z] of hooks) {
      const s = shepherd.root.clone(true);
      s.position.set((x as number) - 0.25, 0, z as number);
      scene.add(s);
    }
  }
  // Real pumpkins, warty and round, on the pallets (not carved: these are for sitting with).
  const pspecs: PumpkinSpec[] = [];
  for (let i = 0; i < 14; i++) {
    const big2 = i < 3;
    const w = big2 ? 0.2 + rnd() * 0.04 : 0.08 + rnd() * 0.08;
    const onFirst = i % 2 === 0;
    pspecs.push({
      position: new Vector3((onFirst ? 9.2 : 6) + (rnd() - 0.5) * 1.0, 0.14 + w * 0.65, (onFirst ? -28.4 : -29.2) + (rnd() - 0.5) * 0.8),
      size: new Vector3(w, w * 0.85, w),
      yaw: rnd() * 6.28,
      carve: -1,
      skin: (PUMPKIN_ORANGE[i % PUMPKIN_ORANGE.length] as Color).clone(),
      glow: new Color(0, 0, 0),
    });
  }
  const pumpkins = new PumpkinField(pspecs, ctx.atlas, { detail: [32, 14], simple: [16, 8] });
  scene.add(pumpkins.group);

  // Light.
  // The owl, wings spread in front of a reed fence of fairy lights.
  const theOwl = await owl(ctx, OWL, OWL_YAW);
  scene.add(...theOwl.objects);
  const back = (dx: number, dz: number): [number, number] => {
    const v = new Vector3(dx, 0, dz).applyAxisAngle(new Vector3(0, 1, 0), OWL_YAW).add(OWL);
    return [v.x, v.z];
  };
  const owlFence = reedFence([[back(-6.5, -1.2), back(-2, -1.6), back(2, -1.6), back(6.5, -1.2)]], 1.9);
  scene.add(owlFence);
  const owlRuns: { from: Vector3; to: Vector3; sag: number }[] = [];
  for (const h of [1.75, 1.05]) {
    for (let k = -6; k < 6; k += 2) {
      const [x0, z0] = back(k, -1.5);
      const [x1, z1] = back(k + 2, -1.5);
      owlRuns.push({ from: new Vector3(x0, h, z0), to: new Vector3(x1, h, z1), sag: h > 1.5 ? 0.45 : 0.3 });
    }
  }
  const owlLights = stringLights(owlRuns, { spacing: 0.2, color: new Color(1, 0.78, 0.48), brightness: 9, glowEvery: 4, glowRadius: 1.4, glowIntensity: 0.07 });
  scene.add(owlLights.mesh);
  const glowLights: GlowLight[] = [...lanterns.glowLights(2.6, tier === 'low' ? 0.09 : 0.06), ...fairy.lights, ...theOwl.glow, ...owlLights.lights];
  scene.add(new HemisphereLight(0x22305a, 0x080404, 0.25));
  const sources: LightSource[] = [...theOwl.sources, ...specs.filter((_, i) => i % 2 === 0).map((s) => ({ position: s.position, color: new Color(1, 0.25, 0.12), intensity: 0.6, distance: 4, phase: s.phase as number }))];

  const night = skyState({
    zenith: new Color(0.004, 0.01, 0.045),
    horizon: new Color(0.025, 0.04, 0.11),
    stars: 0.7,
    lightPollution: new Color(0.05, 0.012, 0.012),
  });
  const grade: Grade = {
    ...defaultGrade(),
    exposure: 1.1,
    bloom: 0.11,
    saturation: 1.18,
    power: 1.1,
    tint: new Color(1.03, 0.98, 0.98),
    lift: new Color(0.006, 0.004, 0.018),
  };

  let time = 0;
  let seated = false;
  let litUpTo = 1;
  let sitPrompted = false;
  const tmp = new Vector2();
  const sofaBox = new Box3().setFromObject(seatObject).expandByScalar(0.3);

  const chapter: Chapter = {
    scene,
    path,
    terrain,
    music: 'garden',
    ambience: 'garden',
    steps: 'step-grass',

    enter() {
      ctx.glow.setBounds(...bounds);
      ctx.glow.setLights(glowLights);
      ctx.glow.wave = 1e9;
      ctx.lights.sources = sources;
      lerpSky(ctx.sky.state, night, night, 0);
      lerpGrade(ctx.post.grade, grade, grade, 0);
      shared.uFogColor.value.set(0.018, 0.02, 0.045);
      shared.uFogDensity.value = 0.018;
      shared.uFogHeight.value = 8;
      shared.uFogGlow.value = 0.7;
      ctx.ember.presence = 1;
      ctx.ember.place(new Vector3(0, 1.8, 5));
      ctx.audio.preload('pasture', ['lantern-swing', 'lantern-light', 'step-grass']);
    },

    update(dt) {
      time += dt;
      const w = ctx.walker;
      const e = ctx.ember;

      // The Ember runs ahead down the tunnel, lighting lanterns as it passes over them.
      const lead = Math.min(path.length, w.s + (w.s < 30 ? 6 : 4));
      path.at(lead, tmp);
      if (!seated) e.target.set(tmp.x, w.s < 30 ? 2.6 : 1.8, tmp.y);
      if (e.position.z < litUpTo) {
        for (const i of tunnelLanterns) {
          const s = specs[i] as LanternSpec;
          if (lanterns.level(i) < 1 && s.position.z > e.position.z - 0.4) {
            lanterns.setLevel(i, 1);
            if (Math.random() < 0.18) void ctx.audio.sfx('lantern-light', { at: s.position, volume: 0.35, rate: 0.9 + Math.random() * 0.25 });
          }
        }
        litUpTo = e.position.z;
      }

      // Near the lounge: an invitation to sit.
      if (!sitPrompted && w.position.distanceTo(SEAT) < 5) {
        sitPrompted = true;
        ctx.ui.say('There’s room on the sofa. Tap it to sit for a while.', 6);
      }
      const stick = ctx.portal.input.stick('move');
      if (seated && Math.hypot(stick.x, stick.y) > 0.3) stand();

      ctx.glow.moving.length = 0;
      ctx.glow.moving.push(e.glow);
      lanterns.update(dt, 0.05 + 0.03 * Math.sin(time * 0.3));
      theOwl.update(dt, time);
      pumpkins.update(ctx.camera, dt);
    },

    pick(ray: Ray): TapAction | null {
      const owlTap = theOwl.pick(ray);
      if (owlTap) return owlTap;
      if (ray.intersectsBox(onGround(sofaBox))) return () => (seated ? stand() : sit());
      const i = lanterns.pick(ray, 20);
      if (i >= 0)
        return () => {
          lanterns.push(i, 0.8);
          void ctx.audio.sfx('lantern-swing', { at: (specs[i] as LanternSpec).position, volume: 0.7 });
        };
      return null;
    },

    finished() {
      return ctx.walker.s > path.length - 1.2;
    },

    dispose() {
      theOwl.dispose();
      terrain.dispose();
      lanterns.dispose();
      pumpkins.dispose();
      big.dispose();
      woods.dispose();
      canopy.dispose();
      floor.geometry.dispose();
      fences.geometry.dispose();
      fairy.mesh.geometry.dispose();
    },
  };

  function sit() {
    seated = true;
    const w = ctx.walker;
    w.position.set(SEAT.x, heightAt(SEAT.x, SEAT.z - 0.55), SEAT.z - 0.55);
    w.yaw = Math.atan2(-(SKY_TREE.x - SEAT.x), -(SKY_TREE.z - SEAT.z)) + 0.9;
    w.pitch = 0.18;
    w.seated = true;
    w.auto = false;
    ctx.audio.musicLevel(0.45, 3);
    ctx.ui.say('Listen. The lanterns are swaying together.', 6);
    ctx.ember.target.set(SEAT.x + 0.6, 1.5, SEAT.z - 1.4);
  }

  function stand() {
    seated = false;
    ctx.walker.seated = false;
    ctx.audio.musicLevel(1, 2);
  }

  return chapter;
}
