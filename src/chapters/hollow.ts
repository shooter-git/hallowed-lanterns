import {
  BufferAttribute,
  Color,
  CylinderGeometry,
  ExtrudeGeometry,
  HemisphereLight,
  InstancedMesh,
  Matrix4,
  Mesh,
  MeshStandardMaterial,
  type Object3D,
  type Ray,
  Scene,
  Shape,
  TorusGeometry,
  Vector2,
  Vector3,
} from 'three';
import { CARVE } from '../engine/carvings.ts';
import type { GlowLight } from '../engine/glowfield.ts';
import { type Bounds, ground, GroundMask } from '../engine/ground.ts';
import { stringLights } from '../engine/lanterns.ts';
import type { LightSource } from '../engine/lights.ts';
import { loadModel } from '../engine/models.ts';
import { Burst, RAINBOW } from '../engine/particles.ts';
import { defaultGrade, type Grade, lerpGrade } from '../engine/post.ts';
import { PUMPKIN_ORANGE, PumpkinField, type PumpkinSpec } from '../engine/pumpkins.ts';
import { Path } from '../engine/rig.ts';
import { flytrap } from '../scenes/flytrap.ts';
import { web } from '../scenes/web.ts';
import { aroundPath, pointOnGround, Terrain } from '../engine/terrain.ts';
import { hallow, shared } from '../engine/shared.ts';
import { lerpSky, skyState, treeLine } from '../engine/sky.ts';
import { woodland } from '../engine/canopy.ts';
import { forest, lineThePath } from '../engine/trees.ts';
import type { Chapter, ChapterContext, TapAction } from './types.ts';

/**
 * V. Sweet Hollow — candy land under an old oak washed in violet light: a giant jack-o'-lantern
 * candy bucket, towers of candy corn, rainbow pumpkins on skewers, lollipop pumpkins, gummy
 * bears, and a row of letter pumpkins you can play like a xylophone. Play the Ember's song and
 * the whole hollow bursts into sprinkles.
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

const STAGE = new Vector3(0, 0, -12);

/** A thick candy-corn board: white tip, orange middle, yellow base. */
function candyCorn(height: number): Mesh {
  const w = height * 0.36;
  const s = new Shape();
  s.moveTo(-w, 0);
  s.lineTo(w, 0);
  s.quadraticCurveTo(w * 0.9, height * 0.55, w * 0.18, height * 0.97);
  s.quadraticCurveTo(0, height * 1.02, -w * 0.18, height * 0.97);
  s.quadraticCurveTo(-w * 0.9, height * 0.55, -w, 0);
  const geo = new ExtrudeGeometry(s, { depth: 0.12, bevelEnabled: true, bevelSize: 0.03, bevelThickness: 0.03, bevelSegments: 2, curveSegments: 16 });
  const pos = geo.getAttribute('position') as BufferAttribute;
  const col = new Float32Array(pos.count * 3);
  const yellow = new Color(0.95, 0.62, 0.05);
  const orange = new Color(0.95, 0.32, 0.03);
  const white = new Color(0.92, 0.9, 0.86);
  for (let i = 0; i < pos.count; i++) {
    const t = pos.getY(i) / height;
    const c = t < 0.38 ? yellow : t < 0.72 ? orange : white;
    col.set([c.r, c.g, c.b], i * 3);
  }
  geo.setAttribute('color', new BufferAttribute(col, 3));
  return new Mesh(geo, hallow(new MeshStandardMaterial({ vertexColors: true, roughness: 0.45 }), { key: 'candycorn', glow: 1.2 }));
}

export async function build(ctx: ChapterContext): Promise<Chapter> {
  const { tier } = ctx;
  const rnd = rng(55);
  const scene = new Scene();
  const bounds: Bounds = [-40, -70, 80, 118];
  const WEB = new Vector3(0, 0, 24);
  // Just past the Web, set back on the right: the giant flytrap over its hay bales.
  const FLYTRAP = new Vector3(5.8, 0, 8.5);

  const path = new Path(
    [
      [0, 40],
      [0, 24],
      [0, 10],
      [0, 2],
      [0, -5.5],
      [4, -7],
      [9, -10],
      [12, -18],
      [10, -30],
    ],
    (s) => (s < 30 ? 4 : s < 43 ? 5 : 3),
  );
  const terrain = new Terrain(bounds, aroundPath(path, { profile: (s) => (s < 30 ? 0.03 * (30 - s) : 0) + (s > 46 ? 0.05 * (s - 46) : 0), bank: 0.05, rough: 0.35, seed: 41 }));

  const mask = new GroundMask(bounds, 4);
  mask.stroke(path.points.filter((_, i) => i % 4 === 0).map((p) => [p.x, p.y]), 2.6, 'r', 0.8);
  mask.soften(3);
  const floor = ground({ mask, a: ctx.surface('gravel'), aScale: 1.6, b: ctx.surface('leaves'), bScale: 2.2, tone: 0.7 });
  scene.add(floor);

  // The old oak behind the display, and dark woods all round.
  const oak = forest([{ species: 'oak', at: [{ x: STAGE.x + 0.4, z: STAGE.z - 2.2, scale: 1.5, yaw: 2 }] }], { leafTint: new Color(0.4, 0.45, 0.42) });
  scene.add(oak.group);
  const ring = lineThePath(path.points, 6.5, { spacing: 5, depth: 2, seed: 15 }).filter(
    (t) => Math.hypot(t.x - STAGE.x, t.z - STAGE.z) > 6 && !(Math.abs(t.x - WEB.x) < 9 && Math.abs(t.z - WEB.z) < 9.5) && Math.hypot(t.x - FLYTRAP.x, t.z - FLYTRAP.z) > 5,
  );
  const woods = forest([
    { species: 'tall', at: ring.filter((_, i) => i % 2 === 0) },
    { species: 'oak', at: ring.filter((_, i) => i % 2 === 1) },
  ]);
  scene.add(woods.group);
  const canopy = woodland(path, {
    canopy: [5.5, 10], reach: 12, skyGap: 0.4, density: tier === 'low' ? 1.4 : 2.4, wallFrom: 4.5, wallTo: 14, wallHeight: 5, wallDensity: tier === 'low' ? 3 : 4,
    tint: new Color(0.38, 0.42, 0.5), seed: 31,
    clear: (x, z, y) => (Math.hypot(x - STAGE.x, z - STAGE.z) < 7.5 && y < 5.5) || (Math.abs(x - WEB.x) < 8.2 && Math.abs(z - WEB.z) < 8.5 && y < 4.8) || (Math.hypot(x - FLYTRAP.x, z - FLYTRAP.z) < 4.8 && y < 6.2),
  });
  scene.add(canopy.mesh);
  scene.add(treeLine({ radius: 100, height: 16, color: new Color(0.004, 0.006, 0.02), under: new Color(0.02, 0.02, 0.06) }));

  // The Web, on the way in.
  const theWeb = await web(ctx, WEB, 0);
  scene.add(...theWeb.objects);
  // Facing the path (its hay bales towards you).
  const theTrap = await flytrap(ctx, FLYTRAP, -Math.PI / 2);
  scene.add(...theTrap.objects);
  let webState: 'waiting' | 'caught' | 'free' = 'waiting';
  theWeb.hooks.onFree = () => {
    webState = 'free';
    ctx.ember.excitement = 1;
    setTimeout(() => (ctx.ember.excitement = 0), 1500);
    void ctx.audio.sfx('ember-chime-hollow', { at: pointOnGround(theWeb.snare), volume: 0.9 });
    ctx.ui.say('Free! It shakes off the web and zooms ahead.', 5);
  };

  // Pumpkins of every kind.
  const specs: PumpkinSpec[] = [];
  const add = (spec: Partial<PumpkinSpec> & { position: Vector3; size: Vector3 }) => {
    specs.push({ yaw: 0, carve: -1, skin: PUMPKIN_ORANGE[0] as Color, glow: new Color(0, 0, 0), phase: rnd(), ...spec });
    return specs.length - 1;
  };
  // The bucket itself, if there's no model: a huge pumpkin with a painted face.
  const bucketModel = await loadModel('candy-bucket');
  if (bucketModel) {
    bucketModel.root.position.copy(STAGE);
    scene.add(bucketModel.root);
  } else {
    add({ position: STAGE.clone().add(new Vector3(0, 1.0, 0)), size: new Vector3(1.15, 0.95, 1.05), carve: CARVE.faces[0] as number, skin: new Color(0.85, 0.28, 0.04), glow: new Color(0, 0, 0) });
    const handle = new Mesh(new TorusGeometry(1.0, 0.04, 8, 40, Math.PI), hallow(new MeshStandardMaterial({ color: 0x111111, emissive: 0xff66cc, emissiveIntensity: 2.5 }), { key: 'handle' }));
    handle.position.copy(STAGE).add(new Vector3(0, 1.7, 0));
    scene.add(handle);
  }
  // The candy: Blender models where we have them (skewers, lollipops, cake pops), pumpkins
  // painted to match where we don't.
  const poleMat = hallow(new MeshStandardMaterial({ color: 0xdddddd, roughness: 0.5 }), { key: 'pole' });
  const poles = new InstancedMesh(new CylinderGeometry(0.025, 0.025, 1, 6), poleMat, 8);
  const m = new Matrix4();
  const [skewerM, lollipopM, cakePopM] = await Promise.all([loadModel('skewer'), loadModel('lollipop'), loadModel('cake-pop')]);
  const placeModel = (model: { root: Object3D } | null, x: number, z: number, yaw: number) => {
    if (!model) return false;
    const o = model.root.clone(true);
    o.position.set(STAGE.x + x, 0, STAGE.z + z);
    o.rotation.y = yaw;
    scene.add(o);
    return true;
  };
  let poleCount = 0;
  [-2.9, -1.75, 1.75, 2.9].forEach((x) => {
    if (placeModel(skewerM, x, -0.4, rnd() * 6)) return;
    for (let i = 0; i < 8; i++) {
      add({ position: STAGE.clone().add(new Vector3(x, 0.55 + i * 0.3, -0.4)), size: new Vector3(0.15, 0.13, 0.15), carve: -4, skin: new Color(rnd(), 0.5, 0.5), yaw: rnd() * 6 });
    }
    m.makeScale(1, 2.8, 1).setPosition(STAGE.x + x, 1.4, STAGE.z - 0.4);
    poles.setMatrixAt(poleCount++, m);
  });
  for (const [x, z] of [
    [-3.8, 0.4],
    [2.2, 0.6],
    [4.4, 0.2],
    [-5.2, -0.2],
    [5.4, 0.9],
  ] as [number, number][]) {
    if (placeModel(lollipopM, x, z, (rnd() - 0.5) * 0.5)) continue;
    add({ position: STAGE.clone().add(new Vector3(x, 1.4, z)), size: new Vector3(0.28, 0.26, 0.2), carve: -5 });
    m.makeScale(1, 1.3, 1).setPosition(STAGE.x + x, 0.65, STAGE.z + z);
    if (poleCount < 8) poles.setMatrixAt(poleCount++, m);
  }
  poles.count = poleCount;
  poles.computeBoundingSphere();
  scene.add(poles);
  for (const [x, z] of [
    [-2.4, -1.0],
    [3.4, -1.2],
    [5.6, -0.8],
  ] as [number, number][]) {
    if (placeModel(cakePopM, x, z, rnd() * 6)) continue;
    add({ position: STAGE.clone().add(new Vector3(x, 1.25, z)), size: new Vector3(0.32, 0.36, 0.32), skin: new Color(0.55, 0.03, 0.05) });
  }
  // Gummy-bear pumpkins (models if we have them).
  const gummy = await loadModel('gummy-bear');
  const gummyColors = [new Color(0.1, 0.25, 0.95), new Color(0.1, 0.7, 0.4), new Color(0.95, 0.4, 0.1), new Color(0.9, 0.15, 0.5)];
  const gummies: Object3D[] = [];
  [
    [-4.6, 1.2],
    [-1.6, 1.4],
    [1.5, 1.3],
    [4.0, 1.0],
  ].forEach(([x, z], i) => {
    if (gummy) {
      const g = gummy.root.clone(true);
      g.position.set(STAGE.x + (x as number), 0, STAGE.z + (z as number));
      g.traverse((o) => {
        const mesh = o as Mesh;
        if (mesh.isMesh) {
          const mat = (mesh.material as MeshStandardMaterial).clone();
          mat.color.copy(gummyColors[i] as Color);
          mesh.material = mat;
        }
      });
      scene.add(g);
      gummies.push(g);
    } else {
      add({ position: STAGE.clone().add(new Vector3(x as number, 0.4, z as number)), size: new Vector3(0.28, 0.36, 0.26), skin: gummyColors[i] as Color });
    }
  });
  // The xylophone: eight letter pumpkins on a low bench at the front, m s m s…
  const benchMat = hallow(new MeshStandardMaterial({ color: 0x2a1c12, roughness: 0.9 }), { key: 'bench' });
  const bench = new Mesh(new CylinderGeometry(0.1, 0.1, 3.6, 6), benchMat);
  bench.rotation.z = Math.PI / 2;
  bench.position.copy(STAGE).add(new Vector3(0, 0.25, 2.2));
  bench.scale.set(1, 1, 2.2);
  scene.add(bench);
  const xylo: number[] = [];
  const paint = [new Color(0.95, 0.75, 0.1), new Color(0.95, 0.45, 0.08), new Color(0.98, 0.9, 0.3)];
  const shells = [new Color(0.35, 0.06, 0.03), new Color(0.06, 0.04, 0.1), new Color(0.5, 0.05, 0.04), new Color(0.32, 0.12, 0.32), new Color(0.6, 0.25, 0.04)];
  for (let i = 0; i < 8; i++) {
    const r = 0.195 - i * 0.007; // bigger pumpkins ring lower
    xylo.push(
      add({
        position: STAGE.clone().add(new Vector3(-1.6 + i * 0.46, 0.35 + r * 0.6, 2.25)),
        size: new Vector3(r, r * 0.85, r),
        carve: 100 + (CARVE.letters[i % 2] as number),
        skin: (shells[i % shells.length] as Color).clone(),
        glow: (paint[i % paint.length] as Color).clone(),
      }),
    );
  }
  // A second row of little carved pumpkins lit in candy colours, and plain ones.
  const candy = [new Color(0.3, 1, 0.2), new Color(1, 0.2, 0.1), new Color(1, 0.65, 0.15), new Color(0.7, 0.3, 1)];
  for (let i = 0; i < 14; i++) {
    const x = -3.4 + i * 0.52 + (rnd() - 0.5) * 0.1;
    const carved = rnd() < 0.6;
    add({
      position: STAGE.clone().add(new Vector3(x, 0.17, 2.9 + (rnd() - 0.5) * 0.2)),
      size: new Vector3(0.16, 0.14, 0.16),
      carve: carved ? (CARVE.faces[Math.floor(rnd() * CARVE.faces.length)] as number) : -1,
      skin: carved ? (PUMPKIN_ORANGE[i % 5] as Color).clone() : (shells[i % shells.length] as Color).clone(),
      glow: carved ? (candy[i % candy.length] as Color).clone().multiplyScalar(3.5) : new Color(0, 0, 0),
      yaw: (rnd() - 0.5) * 0.4,
    });
  }
  // A third row up on a ledge behind: more letters, faces lit in candy colours, painted ones.
  for (let i = 0; i < 13; i++) {
    const x = -3.1 + i * 0.52 + (rnd() - 0.5) * 0.08;
    const kind = rnd();
    const r = 0.15 + rnd() * 0.05;
    add({
      position: STAGE.clone().add(new Vector3(x, 0.62 + r * 0.6, 1.55 + (rnd() - 0.5) * 0.15)),
      size: new Vector3(r, r * 0.85, r),
      carve: kind < 0.35 ? 100 + (CARVE.letters[i % 2] as number) : kind < 0.75 ? (CARVE.faces[Math.floor(rnd() * CARVE.faces.length)] as number) : -1,
      skin: (shells[(i + 2) % shells.length] as Color).clone(),
      glow: kind < 0.35 ? (paint[i % paint.length] as Color).clone() : kind < 0.75 ? (candy[(i + 1) % candy.length] as Color).clone().multiplyScalar(3.2) : new Color(0, 0, 0),
      yaw: (rnd() - 0.5) * 0.3,
    });
  }
  const ledge = new Mesh(new CylinderGeometry(0.06, 0.06, 7.2, 6), benchMat);
  ledge.rotation.z = Math.PI / 2;
  ledge.position.copy(STAGE).add(new Vector3(0, 0.58, 1.55));
  ledge.scale.set(1, 1, 3);
  scene.add(ledge);
  const pumpkins = new PumpkinField(specs, ctx.atlas, { detail: [36, 16], simple: [16, 8] });
  pumpkins.detailDistance = 16;
  scene.add(pumpkins.group);

  // Candy corn towers.
  const corns: Mesh[] = [];
  const cornM = await loadModel('candy-corn');
  for (const [x, z, h, yaw] of [
    [-6.4, -0.6, 2.4, 0.2],
    [-4.6, -1.6, 2.9, 0.05],
    [4.8, -1.5, 3.0, -0.1],
    [6.6, -0.4, 2.5, -0.25],
  ] as [number, number, number, number][]) {
    if (cornM) {
      const o = cornM.root.clone(true);
      o.position.set(STAGE.x + x, 0, STAGE.z + z);
      o.rotation.y = yaw;
      o.scale.setScalar(h / 2.5);
      scene.add(o);
      continue;
    }
    const corn = candyCorn(h);
    corn.position.set(STAGE.x + x, 0, STAGE.z + z);
    corn.rotation.y = yaw;
    scene.add(corn);
    corns.push(corn);
  }

  // A glowing white-and-pink spiral light around the bucket's handle.
  const spiral: { from: Vector3; to: Vector3; sag: number }[] = [];
  for (let a = 0; a < Math.PI; a += Math.PI / 30) {
    const p0 = new Vector3(Math.cos(a) * 1.05, Math.sin(a) * 1.05 + 1.7, 0).add(STAGE);
    const p1 = new Vector3(Math.cos(a + Math.PI / 30) * 1.05, Math.sin(a + Math.PI / 30) * 1.05 + 1.7, 0).add(STAGE);
    spiral.push({ from: p0, to: p1, sag: 0 });
  }
  const handleLights = stringLights(spiral, { spacing: 0.05, color: new Color(1, 0.75, 0.9), brightness: 8, size: 0.02, glowEvery: 6, glowRadius: 1.4, glowIntensity: 0.2 });
  // The model has its own glowing spiral handle; the string is only for the stand-in.
  if (!bucketModel) scene.add(handleLights.mesh);
  for (const g of bucketModel?.glows.values() ?? []) g.emissiveIntensity = 3;

  // Coloured uplights: violet on the oak, magenta and amber on the candy, blue in the woods.
  const glowLights: GlowLight[] = [...pumpkins.glowLights(1.6, 0.35), ...handleLights.lights, ...theWeb.glow, ...theTrap.glow];
  const wash = (x: number, z: number, c: Color, r: number, i: number) => glowLights.push({ x: STAGE.x + x, z: STAGE.z + z, radius: r, color: c, intensity: i, flicker: 0 });
  wash(0.4, -2.2, new Color(0.45, 0.2, 1), 5, 0.7);
  wash(-5.5, -1, new Color(1, 0.2, 0.7), 4, 0.5);
  wash(5.5, -1, new Color(1, 0.35, 0.6), 4, 0.5);
  wash(0, 2.5, new Color(1, 0.7, 0.4), 4, 0.45);
  for (let i = 0; i < 10; i++) wash((rnd() - 0.5) * 30, -6 - rnd() * 14, new Color(0.15, 0.3, 1), 5, 0.4);
  const sources: LightSource[] = [
    ...theWeb.sources,
    ...theTrap.sources,
    { position: STAGE.clone().add(new Vector3(0.4, 0.5, -1.2)), color: new Color(0.55, 0.25, 1), intensity: 6, distance: 9 },
    { position: STAGE.clone().add(new Vector3(-4.5, 0.4, 0.8)), color: new Color(1, 0.3, 0.75), intensity: 4, distance: 6 },
    { position: STAGE.clone().add(new Vector3(4.5, 0.4, 0.8)), color: new Color(1, 0.45, 0.6), intensity: 4, distance: 6 },
    { position: STAGE.clone().add(new Vector3(0, 2.6, 3.2)), color: new Color(1, 0.85, 0.7), intensity: 3, distance: 8 },
  ];
  scene.add(new HemisphereLight(0x2a2a70, 0x080410, 0.3));

  const sprinkles = new Burst(tier === 'low' ? 300 : 700);
  scene.add(sprinkles.mesh);

  const night = skyState({ zenith: new Color(0.004, 0.008, 0.04), horizon: new Color(0.02, 0.03, 0.09), stars: 0.9 });
  const grade: Grade = { ...defaultGrade(), exposure: 1.1, bloom: 0.1, saturation: 1.38, power: 1.08, tint: new Color(1.0, 0.98, 1.04), lift: new Color(0.008, 0.004, 0.025) };

  let time = 0;
  const played: number[] = [];
  let solved = false;
  const bounces = new Map<number, number>();
  const motif = ctx.audio.manifest?.motif?.xylo ?? [0, 4, 3, 2, 3];
  let emberPlan: 'lead' | 'dive' | 'inside' | 'pop' = 'lead';
  let emberClock = 0;
  let hinted = false;
  const tmp = new Vector2();

  const chapter: Chapter = {
    scene,
    path,
    terrain,
    music: 'hollow',
    ambience: 'hollow',
    steps: 'step-leaves',

    enter() {
      ctx.glow.setBounds(...bounds);
      ctx.glow.setLights(glowLights);
      ctx.glow.wave = 1e9;
      ctx.lights.sources = sources;
      lerpSky(ctx.sky.state, night, night, 0);
      lerpGrade(ctx.post.grade, grade, grade, 0);
      shared.uFogColor.value.set(0.015, 0.015, 0.05);
      shared.uFogDensity.value = 0.02;
      shared.uFogHeight.value = 8;
      shared.uFogGlow.value = 0.8;
      ctx.ember.presence = 1;
      ctx.ember.place(new Vector3(0, 1.8, 36));
      ctx.audio.preload('snow', ['xylo', 'gummy-squeak', 'sprinkle-burst']);
    },

    update(dt) {
      time += dt;
      const w = ctx.walker;
      const e = ctx.ember;
      const atStage = Math.hypot(w.position.x - STAGE.x, w.position.z - (STAGE.z + 4)) < 4.5;
      if (atStage && !hinted) {
        hinted = true;
        ctx.ui.say('The letter pumpkins ring when you tap them. Can you play the Ember’s song?', 7);
      }
      // The Ember dives into the bucket and pops back out.
      emberClock += dt;
      // In the Web: the Ember flies in and gets stuck until you free it (or you walk on past).
      const nearWeb = Math.hypot(w.position.x - WEB.x, w.position.z - WEB.z);
      if (webState === 'waiting' && nearWeb < 9) {
        webState = 'caught';
        ctx.ui.say('Oh no — the Ember is caught in the web! Tap the web to free it.', 6);
        void ctx.audio.sfx('web-stretch', { at: pointOnGround(theWeb.snare), volume: 0.8 });
      }
      if (webState === 'caught') {
        e.target.copy(theWeb.snare).add(new Vector3(Math.sin(time * 23) * 0.04, Math.sin(time * 17) * 0.03, 0));
        if (w.position.z < WEB.z - 9) theWeb.hooks.onFree?.();
      } else if (emberPlan === 'lead') {
        path.at(Math.min(path.length, w.s + 4), tmp);
        e.target.set(tmp.x, 1.8, tmp.y);
        if (atStage) {
          emberPlan = 'dive';
          emberClock = 0;
        }
      } else if (emberPlan === 'dive') {
        e.target.copy(STAGE).add(new Vector3(0, emberClock < 1.2 ? 2.6 : 1.2, 0));
        if (emberClock > 2) {
          emberPlan = 'inside';
          emberClock = 0;
        }
      } else if (emberPlan === 'inside') {
        e.presence = Math.max(0, e.presence - dt * 3);
        if (emberClock > 2.2) {
          emberPlan = 'pop';
          emberClock = 0;
          e.place(STAGE.clone().add(new Vector3(0, 1.6, 0)));
          e.kick(new Vector3(0, 5, 1.5));
          e.excitement = 1;
          sprinkles.emit(STAGE.clone().add(new Vector3(0, 1.8, 0)), 60, RAINBOW, 3);
          void ctx.audio.sfx('ember-chime-hollow', { at: STAGE, volume: 0.9 });
        }
      } else {
        e.presence = Math.min(1, e.presence + dt * 2);
        e.excitement = Math.max(0, e.excitement - dt * 0.5);
        e.target.copy(STAGE).add(new Vector3(-0.8 + Math.sin(time * 0.8) * 1.6, 2.4 + Math.sin(time * 1.3) * 0.3, 1.6));
        if (!atStage && w.s > 14) {
          path.at(Math.min(path.length, w.s + 4), tmp);
          e.target.set(tmp.x, 1.8, tmp.y);
        }
      }
      // Bounces of tapped pumpkins settle.
      for (const [i, t] of bounces) {
        const k = t + dt;
        const wob = Math.exp(-k * 5) * Math.sin(k * 26);
        pumpkins.pose(i, 1, Math.max(0, wob) * 0.04, 1 + wob * 0.18);
        if (k > 1.2) {
          pumpkins.pose(i, 1, 0, 1);
          bounces.delete(i);
        } else bounces.set(i, k);
      }
      for (const g of gummies) g.scale.y += (1 - g.scale.y) * (1 - Math.exp(-dt * 6));
      sprinkles.update(dt, 0);
      theWeb.update(dt, time);
      theTrap.update(dt, time);
      ctx.glow.moving.length = 0;
      if (e.presence > 0.01) ctx.glow.moving.push(e.glow);
      pumpkins.update(ctx.camera, dt);
    },

    pick(ray: Ray): TapAction | null {
      const webTap = theWeb.pick(ray);
      if (webTap) return webTap;
      const trapTap = theTrap.pick(ray);
      if (trapTap) return trapTap;
      const i = pumpkins.pick(ray, 12);
      if (i >= 0) {
        const note = xylo.indexOf(i);
        if (note >= 0)
          return () => {
            bounces.set(i, 0);
            void ctx.audio.sfxIndex('xylo', note, { at: (specs[i] as PumpkinSpec).position, volume: 0.9 });
            played.push(note);
            if (played.length > 5) played.shift();
            if (!solved && played.length === 5 && played.every((n, k) => n === motif[k])) celebrate();
          };
        return () => {
          bounces.set(i, 0);
          pumpkins.flare(i);
          void ctx.audio.sfx('gummy-squeak', { at: (specs[i] as PumpkinSpec).position, volume: 0.6, rate: 0.9 + Math.random() * 0.3 });
        };
      }
      for (const g of gummies) {
        const p = pointOnGround(g.position.clone().add(new Vector3(0, 0.35, 0)));
        if (ray.distanceSqToPoint(p) < 0.12)
          return () => {
            g.scale.y = 0.7;
            void ctx.audio.sfx('gummy-squeak', { at: p, volume: 0.7, rate: 0.9 + Math.random() * 0.3 });
          };
      }
      return null;
    },

    finished() {
      return ctx.walker.s > path.length - 1.2;
    },

    dispose() {
      theWeb.dispose();
      theTrap.dispose();
      terrain.dispose();
      pumpkins.dispose();
      oak.dispose();
      woods.dispose();
      canopy.dispose();
      sprinkles.dispose();
      floor.geometry.dispose();
      for (const c of corns) c.geometry.dispose();
    },
  };

  function celebrate() {
    solved = true;
    ctx.ui.say('That’s its song! The whole hollow is singing.', 6);
    void ctx.audio.sfx('sprinkle-burst', { at: STAGE, volume: 1 });
    void ctx.audio.sfx('ember-chime-hollow', { at: STAGE, volume: 1 });
    for (let k = 0; k < 6; k++) {
      setTimeout(() => sprinkles.emit(STAGE.clone().add(new Vector3((Math.random() - 0.5) * 8, 1.5 + Math.random() * 2, (Math.random() - 0.5) * 3)), 90, RAINBOW, 4.5, 4), k * 220);
    }
    specs.forEach((s, i) => {
      if (s.glow.r + s.glow.g > 0 && s.carve < 100) pumpkins.flare(i);
      setTimeout(() => bounces.set(i, 0), Math.random() * 600);
    });
    ctx.ember.excitement = 1;
  }

  return chapter;
}
