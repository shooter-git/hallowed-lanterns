import {
  Box3,
  BoxGeometry,
  Color,
  ConeGeometry,
  Group,
  HemisphereLight,
  Mesh,
  MeshStandardMaterial,
  type Object3D,
  type Ray,
  Scene,
  Vector2,
  Vector3,
} from 'three';
import { FogBank } from '../engine/fogbank.ts';
import type { GlowLight } from '../engine/glowfield.ts';
import { type Bounds, ground, GroundMask } from '../engine/ground.ts';
import { stringLights } from '../engine/lanterns.ts';
import type { LightSource } from '../engine/lights.ts';
import { type LoadedModel, loadModel } from '../engine/models.ts';
import { defaultGrade, type Grade, lerpGrade } from '../engine/post.ts';
import { standIn } from '../engine/props.ts';
import { Path } from '../engine/rig.ts';
import { forest } from '../engine/trees.ts';
import { pictureShow } from '../scenes/pictureShow.ts';
import { aroundPath, onGround, Terrain } from '../engine/terrain.ts';
import { hallow, shared } from '../engine/shared.ts';
import { lerpSky, skyState, treeLine } from '../engine/sky.ts';
import type { Chapter, ChapterContext, TapAction } from './types.ts';

/**
 * IV. The Pasture of Giants — deep night. An open field under the stars, a rope line of red and
 * amber lights, and three enormous glowing longhorns: one grazing, one lying down, one standing
 * tall. They breathe. Come close and the standing one lowers its great head to look at you.
 */

interface Giant {
  model: LoadedModel;
  root: Object3D;
  head: Object3D | undefined;
  headRest: { x: number; y: number };
  phase: number;
  box: Box3;
  lights: number[];
  flare: number;
  base: Vector3;
}

/** Real-world heights, from the photo: a 1.2 m child barely reaches the standing one's knee. */
const HEIGHT: Record<string, number> = { 'longhorn-standing': 7.0, 'longhorn-grazing': 5.2, 'longhorn-lying': 4.6 };

export async function build(ctx: ChapterContext): Promise<Chapter> {
  const { tier } = ctx;
  const scene = new Scene();
  const bounds: Bounds = [-45, -115, 90, 130];

  const path = new Path(
    [
      [0, 8],
      [0, -4],
      [-3, -14],
      [1, -24],
      [7, -33],
      [4, -46],
      [-3, -56],
      [-6, -68],
      [-10, -80],
      [-12, -88],
      [-4, -95],
      [5, -99],
    ],
    (s) => (s < 82 ? 9 : 7),
  );
  const terrain = new Terrain(bounds, aroundPath(path, { profile: (s) => 0.85 * Math.sin(s / 19) + 0.35 * Math.sin(s / 8 + 2), bank: 0.04, rough: 1.0, seed: 62 }));

  const mask = new GroundMask(bounds, 3);
  const line: [number, number][] = path.points.filter((_, i) => i % 6 === 0).map((p) => [p.x, p.y]);
  mask.stroke(line, 2.2, 'r', 0.55);
  mask.stroke(line, 18, 'g', 0.35);
  mask.soften(4);
  const floor = ground({ mask, a: ctx.surface('dryGrass'), aScale: 1.4, b: ctx.surface('dryGrass'), bScale: 2.6, tone: 0.75 });
  scene.add(floor);

  // The giants.
  const giants: Giant[] = [];
  const place = async (name: string, at: Vector3, yaw: number, phase: number) => {
    const model = await loadModel(name, { glowReceive: 0.2 });
    const root: Object3D = model?.root ?? standIn(new Vector3(3, HEIGHT[name] ?? 4, 6), new Color(0.9, 0.9, 0.88), new Vector3());
    // Make sure they're as huge as they really were.
    const box = new Box3().setFromObject(root);
    const h = box.max.y - box.min.y;
    const want = HEIGHT[name] ?? h;
    if (model && Math.abs(h - want) / want > 0.08) root.scale.multiplyScalar(want / h);
    root.position.copy(at);
    root.rotation.y = yaw;
    scene.add(root);
    for (const m of model?.glows.values() ?? []) {
      m.emissiveIntensity = 2.2;
      m.color.multiplyScalar(0.6);
    }
    const head = model?.node('head');
    giants.push({
      model: model as LoadedModel,
      root,
      head,
      headRest: { x: head?.rotation.x ?? 0, y: head?.rotation.y ?? 0 },
      phase,
      box: new Box3().setFromObject(root),
      lights: [],
      flare: 0,
      base: root.scale.clone(),
    });
  };
  await place('longhorn-standing', new Vector3(6.5, 0, -28), -0.55, 0);
  await place('longhorn-grazing', new Vector3(-9, 0, -21), 0.9, 1.7);
  await place('longhorn-lying', new Vector3(-5, 0, -39), 0.3, 3.1);
  const blower = await loadModel('longhorn-blower');
  if (blower) {
    blower.root.position.set(-1.2, 0, -35.5);
    scene.add(blower.root);
  }

  // The rope line of red and amber lights, low across the field behind the herd.
  const rope: [number, number][] = [
    [-22, -6],
    [-18, -30],
    [-12, -48],
    [0, -54],
    [14, -48],
    [20, -32],
    [24, -12],
  ];
  const runs: { from: Vector3; to: Vector3; sag: number }[] = [];
  for (let i = 0; i < rope.length - 1; i++) {
    const [x0, z0] = rope[i] as [number, number];
    const [x1, z1] = rope[i + 1] as [number, number];
    const n = Math.ceil(Math.hypot(x1 - x0, z1 - z0) / 3);
    for (let k = 0; k < n; k++) {
      const a = k / n;
      const b = (k + 1) / n;
      runs.push({ from: new Vector3(x0 + (x1 - x0) * a, 0.55, z0 + (z1 - z0) * a), to: new Vector3(x0 + (x1 - x0) * b, 0.55, z0 + (z1 - z0) * b), sag: 0.12 });
    }
  }
  const redLights = stringLights(runs.filter((_, i) => i % 2 === 0), { spacing: 0.16, color: new Color(1, 0.08, 0.04), brightness: 12, size: 0.022, glowEvery: 3, glowRadius: 1.2, glowIntensity: 0.18 });
  const amberLights = stringLights(runs.filter((_, i) => i % 2 === 1), { spacing: 0.16, color: new Color(1, 0.55, 0.12), brightness: 10, size: 0.022, glowEvery: 3, glowRadius: 1.2, glowIntensity: 0.16 });
  scene.add(redLights.mesh, amberLights.mesh);
  // Stakes the rope hangs from.
  const stakeMat = hallow(new MeshStandardMaterial({ color: 0x1a120c, roughness: 0.9 }), { key: 'stake' });
  const stakes = new Group();
  for (const r of runs) {
    const s = new Mesh(new BoxGeometry(0.05, 0.62, 0.05), stakeMat);
    s.position.set(r.from.x, 0.31, r.from.z);
    stakes.add(s);
  }
  scene.add(stakes);

  // A red barn and a stand of trees far off, as in the photo.
  const barnMat = hallow(new MeshStandardMaterial({ color: 0x3a0e0a, roughness: 0.9 }), { key: 'barn', glow: 0.5 });
  const barn = new Group();
  const walls = new Mesh(new BoxGeometry(12, 6, 9), barnMat);
  walls.position.y = 3;
  const roof = new Mesh(new ConeGeometry(8.2, 3.5, 4, 1), barnMat);
  roof.position.y = 7.6;
  roof.rotation.y = Math.PI / 4;
  roof.scale.set(1, 1, 0.78);
  barn.add(walls, roof);
  barn.position.set(34, 0, -44);
  barn.rotation.y = -0.4;
  scene.add(barn);
  scene.add(treeLine({ radius: 140, height: 14, color: new Color(0.004, 0.006, 0.014), under: new Color(0.02, 0.012, 0.012), seed: 3 }));

  const fog = new FogBank({
    bounds: mask.bounds,
    mask: mask.texture(),
    slices: tier === 'low' ? 3 : 6,
    height: 0.6,
    tint: new Color(0.01, 0.012, 0.02),
    density: 0.08,
    glow: 1.4,
  });
  scene.add(fog.mesh);
  scene.add(new HemisphereLight(0x1b2448, 0x050403, 0.22));

  // The picture show, in a clearing at the far side of the pasture, ringed by trees.
  const SHOW = new Vector3(-13, 0, -104);
  const show = await pictureShow(ctx, SHOW, 0.25);
  scene.add(...show.objects);
  const ring = forest([
    { species: 'oak', at: [-26, -20, -12, -4, 4].map((x, i) => ({ x: SHOW.x + x + 4, z: SHOW.z - 7 - (i % 2) * 3, scale: 0.9 + (i % 3) * 0.15, yaw: i })) },
    { species: 'tall', at: [-30, -23, -16, -8, 0, 8].map((x, i) => ({ x: SHOW.x + x + 6, z: SHOW.z - 11 - (i % 2) * 2, scale: 1, yaw: i * 2 })) },
  ]);
  scene.add(ring.group);

  // Each giant pours white light onto the grass around it.
  const glowLights: GlowLight[] = [...redLights.lights, ...amberLights.lights, ...show.glow];
  const white = new Color(0.95, 0.97, 1.0);
  for (const g of giants) {
    const c = g.box.getCenter(new Vector3());
    const size = g.box.getSize(new Vector3());
    for (const [dx, dz] of [
      [0, 0],
      [0.3, 0.3],
      [-0.3, -0.3],
      [0.3, -0.3],
      [-0.3, 0.3],
    ] as [number, number][]) {
      g.lights.push(glowLights.length);
      glowLights.push({ x: c.x + dx * size.x, z: c.z + dz * size.z, radius: Math.max(size.x, size.z) * 0.75, color: white, intensity: 0.32, flicker: 0 });
    }
  }
  const sources: LightSource[] = [...show.sources, ...giants.map((g) => ({
    position: g.box.getCenter(new Vector3()).setY(1.6),
    color: new Color(0.9, 0.95, 1),
    intensity: 4,
    distance: 14,
  }))];

  // Out in the open, far from the lights: the heavens as a long exposure sees them.
  const night = skyState({
    zenith: new Color(0.003, 0.006, 0.03),
    horizon: new Color(0.018, 0.026, 0.07),
    stars: 1.3,
    lightPollution: new Color(0.03, 0.015, 0.01),
    milkyWay: 1,
  });
  const grade: Grade = { ...defaultGrade(), exposure: 1.05, bloom: 0.12, saturation: 1.1, power: 1.08, tint: new Color(0.98, 1.0, 1.05), lift: new Color(0.004, 0.006, 0.018) };

  let time = 0;
  const tmp = new Vector2();
  const near = new Vector3();
  const standing = giants[0] as Giant;
  let greeted = false;
  let showHinted = false;

  const chapter: Chapter = {
    scene,
    path,
    terrain,
    music: 'pasture',
    ambience: 'pasture',
    steps: 'step-meadow', // wading through the field's long grass

    enter() {
      ctx.glow.setBounds(...bounds);
      ctx.glow.setLights(glowLights);
      ctx.glow.wave = 1e9;
      ctx.lights.sources = sources;
      lerpSky(ctx.sky.state, night, night, 0);
      lerpGrade(ctx.post.grade, grade, grade, 0);
      shared.uFogColor.value.set(0.012, 0.016, 0.035);
      shared.uFogDensity.value = 0.012;
      shared.uFogHeight.value = 10;
      shared.uFogGlow.value = 0.9;
      ctx.ember.presence = 1;
      ctx.ember.place(new Vector3(0, 1.8, 4));
      ctx.audio.preload('hollow', ['giant-low', 'fly-buzz', 'flytrap-snap', 'flytrap-stir', 'flytrap-lunge', 'fly-buzz-trapped']);
    },

    update(dt) {
      time += dt;
      const w = ctx.walker;
      const e = ctx.ember;
      // Breathing: a slow swell, the glow and the light on the grass rising with it.
      for (const g of giants) {
        const b = Math.sin(time * 0.9 + g.phase);
        const k = 1 + b * 0.012;
        g.root.scale.set(g.base.x * k, g.base.y * (1 + b * 0.018), g.base.z * k);
        g.flare = Math.max(0, g.flare - dt * 0.6);
        const level = 1 + b * 0.06 + g.flare * 0.8;
        for (const m of g.model?.glows.values() ?? []) m.emissiveIntensity = 2.2 * level;
        for (const i of g.lights) ctx.glow.setLevel(i, level);
      }
      // The standing giant notices you and lowers its head to look.
      if (standing.head) {
        const headWorld = standing.head.getWorldPosition(near);
        const d = Math.hypot(w.position.x - headWorld.x, w.position.z - headWorld.z);
        const interest = Math.max(0, Math.min(1, (16 - d) / 8));
        const local = standing.root.worldToLocal(new Vector3(w.position.x, 1.6, w.position.z));
        const yawTo = Math.atan2(local.x, local.z);
        const wantY = standing.headRest.y + Math.max(-0.6, Math.min(0.6, yawTo)) * interest;
        const wantX = standing.headRest.x + 0.35 * interest;
        standing.head.rotation.y += (wantY - standing.head.rotation.y) * (1 - Math.exp(-dt * 0.9));
        standing.head.rotation.x += (wantX - standing.head.rotation.x) * (1 - Math.exp(-dt * 0.7));
        if (interest > 0.6 && !greeted) {
          greeted = true;
          ctx.ui.say('It lowers its great head to look at you.', 6);
          void ctx.audio.sfx('giant-low', { at: headWorld, volume: 0.9 });
        }
        if (interest > 0.3) {
          // The Ember settles between its horns.
          e.target.copy(headWorld).add(new Vector3(0, 1.3, 0));
        } else {
          path.at(Math.min(path.length, w.s + 5), tmp);
          e.target.set(tmp.x, 2 + Math.sin(time * 0.6) * 0.3, tmp.y);
        }
      }
      show.update(dt, time);
      // Up from the bench: back to the night's own music.
      const stick = ctx.portal.input.stick('move');
      if (w.seated && Math.hypot(stick.x, stick.y) > 0.3) {
        w.seated = false;
        void ctx.audio.setScene('pasture', 'pasture', 3);
      }
      if (!showHinted && Math.hypot(w.position.x - SHOW.x, w.position.z - SHOW.z) < 18) {
        showHinted = true;
        ctx.ui.say('A picture show in the clearing. Tap a bench to sit and watch.', 6);
      }
      ctx.glow.moving.length = 0;
      ctx.glow.moving.push(e.glow);
      fog.walkers[0]?.set(w.position.x, w.position.z);
      fog.update();
    },

    pick(ray: Ray): TapAction | null {
      const sit = show.pick(ray);
      if (sit) return sit;
      for (const g of giants) {
        if (ray.intersectsBox(onGround(g.box))) {
          return () => {
            g.flare = 1;
            const at = g.head?.getWorldPosition(new Vector3()) ?? g.box.getCenter(new Vector3());
            void ctx.audio.sfx('giant-low', { at, volume: 1 });
          };
        }
      }
      return null;
    },

    finished() {
      return ctx.walker.s > path.length - 1.5;
    },

    dispose() {
      show.dispose();
      ring.dispose();
      terrain.dispose();
      fog.dispose();
      floor.geometry.dispose();
      redLights.mesh.geometry.dispose();
      amberLights.mesh.geometry.dispose();
    },
  };
  return chapter;
}
