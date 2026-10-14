import {
  AdditiveBlending,
  Box3,
  BoxGeometry,
  CanvasTexture,
  Color,
  DoubleSide,
  DynamicDrawUsage,
  Group,
  HemisphereLight,
  InstancedBufferAttribute,
  InstancedBufferGeometry,
  InstancedMesh,
  Matrix4,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  type Object3D,
  PlaneGeometry,
  Quaternion,
  type Ray,
  Scene,
  ShaderMaterial,
  SphereGeometry,
  SRGBColorSpace,
  Vector2,
  Vector3,
} from 'three';
import { FogBank } from '../engine/fogbank.ts';
import type { GlowLight } from '../engine/glowfield.ts';
import { type Bounds, ground, GroundMask } from '../engine/ground.ts';
import { stringLights } from '../engine/lanterns.ts';
import type { LightSource } from '../engine/lights.ts';
import { instanceModel, loadModel } from '../engine/models.ts';
import { defaultGrade, type Grade, lerpGrade } from '../engine/post.ts';
import { Path } from '../engine/rig.ts';
import { guitar } from '../scenes/guitar.ts';
import { hallow, SHADER_PARS, shared, VERTEX_TERRAIN } from '../engine/shared.ts';
import { lerpSky, skyState, treeLine } from '../engine/sky.ts';
import { aroundPath, heightAt, pointOnGround, Terrain } from '../engine/terrain.ts';
import { woodland } from '../engine/canopy.ts';
import { forest, lineThePath } from '../engine/trees.ts';
import type { Chapter, ChapterContext, TapAction } from './types.ts';

/**
 * VIII. The Marigold Garden — the finale. The water drains away into marigold-scented mist. An
 * ofrenda glows teal and gold: light a candle for someone you remember and monarch butterflies
 * lift from the marigolds. Beyond it, the Wishing Tree, every leaf a wish: hang your own (kept for
 * your group). Then the Ember settles on a branch and becomes a leaf of light, the night's
 * lanterns rise into the sky, and the whole theme plays.
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

const OFRENDA = new Vector3(0, 0, -10);
const TREE = new Vector3(13, 0, -27);
/** The Wishing Tree faces back up the path, towards where you come in. */
const TREE_YAW = Math.atan2(11.5 - TREE.x, -18.5 - TREE.z);
const UP = new Vector3(0, 1, 0);
/** A point in the tree's own frame (x along its hedge, z out towards you) in the world. */
const byTree = (x: number, z: number) => TREE.clone().add(new Vector3(x, 0, z).applyAxisAngle(UP, TREE_YAW));
/** Whether a point is in the hedged room round the tree (with a margin round it). */
const inTreeRoom = (x: number, z: number, margin: number) => {
  const dx = x - TREE.x;
  const dz = z - TREE.z;
  const u = dx * Math.cos(TREE_YAW) - dz * Math.sin(TREE_YAW);
  const v = dx * Math.sin(TREE_YAW) + dz * Math.cos(TREE_YAW);
  return Math.abs(u) < 6.5 + margin && v > -1.5 - margin && v < 6.5 + margin;
};
const GUITAR = new Vector3(5.8, 0, -3);

type Wish = {
  text: string;
  color: 'coral' | 'teal';
  by: string;
  anchor: number;
};

/** A monarch's wing, drawn once: orange cells, black veins and border, white dots. */
function monarchTexture(): CanvasTexture {
  const c = document.createElement('canvas');
  c.width = 256;
  c.height = 128;
  const g = c.getContext('2d') as CanvasRenderingContext2D;
  for (const side of [-1, 1]) {
    g.save();
    g.translate(128, 64);
    g.scale(side, 1);
    g.fillStyle = '#111';
    g.beginPath();
    g.moveTo(0, -6);
    g.bezierCurveTo(40, -70, 120, -60, 122, -20);
    g.bezierCurveTo(124, 10, 70, 8, 60, 14);
    g.bezierCurveTo(90, 30, 80, 62, 40, 58);
    g.bezierCurveTo(14, 56, 4, 30, 0, 8);
    g.fill();
    g.fillStyle = '#f07a12';
    g.beginPath();
    g.moveTo(6, -6);
    g.bezierCurveTo(40, -58, 110, -52, 112, -22);
    g.bezierCurveTo(112, 2, 70, 2, 56, 10);
    g.bezierCurveTo(80, 28, 72, 52, 40, 50);
    g.bezierCurveTo(18, 48, 8, 28, 6, 8);
    g.fill();
    g.strokeStyle = '#111';
    g.lineWidth = 3;
    for (const [a, b] of [
      [20, -30],
      [50, -40],
      [80, -38],
      [30, 30],
      [55, 36],
    ]) {
      g.beginPath();
      g.moveTo(4, 0);
      g.quadraticCurveTo((a as number) * 0.5, (b as number) * 0.4, a as number, b as number);
      g.stroke();
    }
    g.fillStyle = '#fff';
    for (let k = 0; k < 9; k++) {
      g.beginPath();
      g.arc(90 + k * 3 - (k % 2) * 8, -40 + k * 6, 2.2, 0, Math.PI * 2);
      g.fill();
    }
    g.restore();
  }
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  return t;
}

/** Monarch butterflies: each a pair of flapping wings, spiralling up and drifting away. */
class Butterflies {
  readonly mesh: Mesh<InstancedBufferGeometry, ShaderMaterial>;
  private readonly at: InstancedBufferAttribute;
  private readonly flies: { p: Vector3; v: Vector3; life: number; phase: number }[] = [];
  private next = 0;

  constructor(capacity: number) {
    const plane = new PlaneGeometry(1, 0.5, 2, 1);
    const geo = new InstancedBufferGeometry();
    geo.index = plane.index;
    geo.setAttribute('position', plane.getAttribute('position'));
    geo.setAttribute('uv', plane.getAttribute('uv'));
    this.at = new InstancedBufferAttribute(new Float32Array(capacity * 4), 4);
    this.at.setUsage(DynamicDrawUsage);
    geo.setAttribute('aAt', this.at);
    const ph = new InstancedBufferAttribute(new Float32Array(capacity).map(() => Math.random()), 1);
    geo.setAttribute('aPhase', ph);
    geo.instanceCount = capacity;
    for (let i = 0; i < capacity; i++) this.flies.push({ p: new Vector3(), v: new Vector3(), life: 0, phase: Math.random() });
    this.mesh = new Mesh(
      geo,
      new ShaderMaterial({
        uniforms: { ...shared, tMap: { value: monarchTexture() } },
        vertexShader: /* glsl */ `
          attribute vec4 aAt;      // position, size (0 = hidden)
          attribute float aPhase;
          uniform float uHlTime;
          varying vec2 vUv;
          varying vec3 vHlWorld;
          ${VERTEX_TERRAIN}
          void main() {
            vUv = uv;
            // Wings beat: each half folds up about the body.
            float beat = sin(uHlTime * 14.0 + aPhase * 30.0) * 0.9;
            vec3 p = position * aAt.w;
            float side = sign(position.x);
            float a = beat * side;
            p = vec3(p.x * cos(a), abs(p.x) * sin(beat) * 0.9, p.y);
            // Heading turns slowly.
            float h = aPhase * 6.28 + uHlTime * 0.3;
            p = vec3(p.x * cos(h) - p.z * sin(h), p.y, p.x * sin(h) + p.z * cos(h));
            vec3 w = aAt.xyz + p;
            w.y += hlTerrain(aAt.xz);
            vHlWorld = w;
            gl_Position = projectionMatrix * viewMatrix * vec4(w, 1.0);
          }`,
        fragmentShader: /* glsl */ `
          ${SHADER_PARS}
          uniform sampler2D tMap;
          varying vec2 vUv;
          varying vec3 vHlWorld;
          void main() {
            vec4 t = texture2D(tMap, vUv);
            if (t.a < 0.5) discard;
            vec3 col = t.rgb * (0.5 + hlGlow(vHlWorld) * 2.0) + t.rgb * vec3(1.0, 0.5, 0.15) * 0.4;
            gl_FragColor = vec4(hlApplyFog(col, vHlWorld), 1.0);
          }`,
        side: DoubleSide,
      }),
    );
    this.mesh.frustumCulled = false;
  }

  release(from: Vector3, count: number) {
    for (let k = 0; k < count; k++) {
      const f = this.flies[this.next] as (typeof this.flies)[number];
      this.next = (this.next + 1) % this.flies.length;
      f.p.copy(from).add(new Vector3((Math.random() - 0.5) * 0.6, Math.random() * 0.3, (Math.random() - 0.5) * 0.6));
      f.v.set((Math.random() - 0.5) * 0.6, 0.5 + Math.random() * 0.5, (Math.random() - 0.5) * 0.6);
      f.life = 9 + Math.random() * 6;
    }
  }

  update(dt: number, time: number) {
    this.flies.forEach((f, i) => {
      if (f.life <= 0) {
        this.at.setXYZW(i, 0, -100, 0, 0);
        return;
      }
      f.life -= dt;
      // Fluttering: a wandering spiral, rising and drifting off.
      f.v.x += Math.sin(time * 2.3 + f.phase * 20) * dt * 1.4;
      f.v.z += Math.cos(time * 1.9 + f.phase * 13) * dt * 1.4;
      f.v.y += (0.35 - f.v.y) * dt * 0.5 + Math.sin(time * 5 + f.phase * 7) * dt * 1.5;
      f.v.multiplyScalar(Math.exp(-dt * 0.4));
      f.p.addScaledVector(f.v, dt);
      const size = 0.13 * Math.min(1, f.life / 1.5);
      this.at.setXYZW(i, f.p.x, f.p.y, f.p.z, size);
    });
    this.at.needsUpdate = true;
  }

  dispose() {
    this.mesh.geometry.dispose();
    this.mesh.material.dispose();
  }
}

/** Sky lanterns: hundreds of warm lights lifting slowly into the night, for the ending. */
class SkyLanterns {
  readonly mesh: InstancedMesh;
  private readonly items: { p: Vector3; v: number; delay: number; sway: number }[] = [];
  private t = -1;

  constructor(count: number, centre: Vector3) {
    const geo = new SphereGeometry(0.16, 8, 6);
    geo.scale(1, 1.3, 1);
    const mat = new MeshBasicMaterial({ color: new Color(1, 0.55, 0.18).multiplyScalar(5), transparent: true, blending: AdditiveBlending, depthWrite: false });
    this.mesh = new InstancedMesh(geo, mat, count);
    this.mesh.frustumCulled = false;
    this.mesh.visible = false;
    const rnd = rng(8);
    for (let i = 0; i < count; i++) {
      const a = rnd() * Math.PI * 2;
      const r = 6 + rnd() * 70;
      const p = new Vector3(centre.x + Math.cos(a) * r, -1 - rnd() * 3, centre.z + Math.sin(a) * r);
      this.items.push({ p, v: 0.5 + rnd() * 0.7, delay: rnd() * 14 + r * 0.05, sway: rnd() * 6 });
    }
  }

  start() {
    this.t = 0;
    this.mesh.visible = true;
  }

  update(dt: number) {
    if (this.t < 0) return;
    this.t += dt;
    const m = new Matrix4();
    this.items.forEach((it, i) => {
      const k = Math.max(0, this.t - it.delay);
      const y = it.p.y + k * it.v + heightAt(it.p.x, it.p.z);
      const x = it.p.x + Math.sin(k * 0.3 + it.sway) * 0.8;
      const s = k > 0 ? Math.min(1, k) * (y > 60 ? Math.max(0, 1 - (y - 60) / 30) : 1) : 0;
      m.makeScale(s, s, s).setPosition(x, y, it.p.z);
      this.mesh.setMatrixAt(i, m);
    });
    this.mesh.instanceMatrix.needsUpdate = true;
  }

  dispose() {
    this.mesh.geometry.dispose();
    (this.mesh.material as MeshBasicMaterial).dispose();
  }
}

export async function build(ctx: ChapterContext): Promise<Chapter> {
  const { tier, portal } = ctx;
  const rnd = rng(88);
  const scene = new Scene();
  const bounds: Bounds = [-40, -75, 90, 95];

  const path = new Path(
    [
      [0, 9],
      [0, 0],
      [0.5, -4.5],
      [4.5, -8],
      [9, -13],
      [11.5, -18.5],
      [12.5, -21.5],
      // Into the hedged room round the Wishing Tree, where it opens out to the tree and the table.
      [12.9, -24.8],
    ],
    (s, total) => (s < 12 ? 6 : s > total - 4.5 ? 9 : 4.5),
  );
  const terrain = new Terrain(bounds, aroundPath(path, { profile: (s) => 0.02 * s + 0.15 * Math.sin(s / 6), bank: 0.04, rough: 0.35, seed: 8 }));

  const mask = new GroundMask(bounds, 4);
  mask.stroke(path.points.filter((_, i) => i % 4 === 0).map((p) => [p.x, p.y]), 3.2, 'r', 0.9);
  mask.blob(OFRENDA.x, OFRENDA.z + 3, 5, 'r', 0.9);
  // Mist gathers around the ofrenda and drifts along the walk.
  mask.blob(OFRENDA.x, OFRENDA.z + 2, 9, 'g', 0.7);
  mask.stroke(path.points.filter((_, i) => i % 4 === 0).map((p) => [p.x, p.y]), 6, 'g', 0.35);
  mask.soften(3);
  const floor = ground({ mask, a: ctx.surface('gravel'), aScale: 1.6, b: ctx.surface('lawn'), bScale: 2.2, tone: 0.8 });
  scene.add(floor);

  // Woods all round, darker behind the ofrenda so the crest glows against them.
  const woodsAt = lineThePath(path.points, 8, { spacing: 5, depth: 2, seed: 41 }).filter(
    (t) => !inTreeRoom(t.x, t.z, 1.5) && Math.hypot(t.x - OFRENDA.x, t.z - OFRENDA.z) > 5,
  );
  const woods = forest([
    { species: 'tall', at: woodsAt.filter((_, i) => i % 2 === 0) },
    { species: 'oak', at: woodsAt.filter((_, i) => i % 2 === 1) },
  ]);
  scene.add(woods.group);
  const canopy = woodland(path, {
    canopy: [5.5, 10], reach: 13, skyGap: 0.5, density: tier === 'low' ? 1.2 : 2, wallFrom: 5.5, wallTo: 15, wallHeight: 5, wallDensity: tier === 'low' ? 3 : 4,
    tint: new Color(0.38, 0.45, 0.4), seed: 61,
    clear: (x, z, y) => Math.hypot(x - OFRENDA.x, z - OFRENDA.z) < 8 || (inTreeRoom(x, z, 1) && y < 6.5) || (Math.hypot(x - GUITAR.x, z - GUITAR.z) < 3.5 && y < 7.5),
  });
  scene.add(canopy.mesh);
  scene.add(treeLine({ radius: 110, height: 16, color: new Color(0.004, 0.008, 0.012), under: new Color(0.03, 0.025, 0.012) }));

  // --- The ofrenda. ---
  const ofrenda = await loadModel('ofrenda', { glowReceive: 1 });
  const candleSpots: Vector3[] = [];
  let candleBox = new Box3();
  let ofrendaRoot: Object3D;
  let flames: InstancedMesh | null = null;
  const lit: boolean[] = [];
  const flameLit: Matrix4[] = [];
  if (ofrenda) {
    ofrendaRoot = ofrenda.root;
    const box = new Box3().setFromObject(ofrendaRoot);
    const h = box.max.y - box.min.y;
    if (Math.abs(h - 5.5) / 5.5 > 0.12) ofrendaRoot.scale.multiplyScalar(5.5 / h);
    ofrendaRoot.position.copy(OFRENDA);
    scene.add(ofrendaRoot);
    ofrendaRoot.updateMatrixWorld(true);
    for (const m of ofrenda.glows.values()) m.emissiveIntensity = m.name === 'glow_crest' ? 2.2 : m.name === 'glow_lights' ? 3 : 4;
    // Candles: instanced from the template at every marked spot; flames shown only when lit.
    const template = ofrenda.node('candle_template') as Mesh | undefined;
    const flameT = ofrenda.node('flame_template') as Mesh | undefined;
    const spots = ofrenda.node('candle_spots');
    spots?.traverse((o) => {
      if (o !== spots) candleSpots.push(o.getWorldPosition(new Vector3()));
    });
    if (template && flameT) {
      template.visible = false;
      template.updateMatrixWorld(true);
      const tScale = template.getWorldScale(new Vector3());
      const wax = new InstancedMesh(template.geometry, template.material, candleSpots.length);
      flames = new InstancedMesh(flameT.geometry, flameT.material, candleSpots.length);
      const flameOffset = flameT.position.clone().multiply(tScale);
      candleSpots.forEach((p, i) => {
        const s = tScale.x * (0.8 + rnd() * 0.5);
        const m = new Matrix4().compose(p, new Quaternion(), new Vector3(s, s * (0.8 + rnd() * 0.7), s));
        wax.setMatrixAt(i, m);
        lit.push(rnd() < 0.6);
        flameLit.push(new Matrix4().compose(p.clone().add(flameOffset.clone().multiplyScalar(s / tScale.x)), new Quaternion(), new Vector3(s, s, s)));
      });
      wax.computeBoundingSphere();
      flames.computeBoundingSphere();
      flames.frustumCulled = false;
      scene.add(wax, flames);
    }
    candleBox = new Box3().setFromPoints(candleSpots).expandByScalar(0.25);
  } else {
    ofrendaRoot = new Group();
    const teal = hallow(new MeshStandardMaterial({ color: 0x2a8a8a, emissive: 0x1a6a6a, emissiveIntensity: 0.6 }), { key: 'teal' });
    const frame = new Mesh(new BoxGeometry(4.8, 4.2, 0.3), teal);
    frame.position.set(0, 2.6, -0.4);
    (ofrendaRoot as Group).add(frame);
    ofrendaRoot.position.copy(OFRENDA);
    scene.add(ofrendaRoot);
    for (let i = 0; i < 24; i++) {
      candleSpots.push(OFRENDA.clone().add(new Vector3(-2.2 + (i % 12) * 0.4, 0.45 + Math.floor(i / 12) * 0.35, 1.2 - Math.floor(i / 12) * 0.4)));
      lit.push(rnd() < 0.6);
    }
    candleBox = new Box3().setFromPoints(candleSpots).expandByScalar(0.25);
  }

  // Candles lit by the group are kept: light those too.
  type Candles = { lit: number[] };
  try {
    const saved = await portal.save.shared.get<Candles>('candles');
    for (const i of saved?.lit ?? []) lit[i] = true;
  } catch {
    // Nothing saved yet.
  }
  const hidden = new Matrix4().makeScale(0, 0, 0);
  const setFlame = (i: number, on: boolean) => {
    lit[i] = on;
    const m = flameLit[i];
    if (!flames || !m) return;
    flames.setMatrixAt(i, on ? m : hidden);
    flames.instanceMatrix.needsUpdate = true;
  };
  lit.forEach((on, i) => setFlame(i, on));

  // Marigold bouquets and garlands along the bottom step, glowing orange in the mist.
  const marigoldRuns: { from: Vector3; to: Vector3; sag: number }[] = [];
  marigoldRuns.push({ from: OFRENDA.clone().add(new Vector3(-3.2, 0.05, 2.0)), to: OFRENDA.clone().add(new Vector3(3.2, 0.05, 2.0)), sag: 0 });
  const marigolds = stringLights(marigoldRuns, { spacing: 0.07, color: new Color(1, 0.5, 0.05), brightness: 0.6, size: 0.06, glowEvery: 6, glowRadius: 1.2, glowIntensity: 0.05 });
  (marigolds.mesh.material as MeshStandardMaterial).color.set(0.9, 0.42, 0.03);
  scene.add(marigolds.mesh);

  // --- The Wishing Tree: a white branching cut-out against a boxwood hedge that runs round it, open
  // towards the path, with the wish table along one side. ---
  const wishing = await loadModel('wishing-tree');
  const anchors: Vector3[] = [];
  let treeRoot: Object3D;
  if (wishing) {
    treeRoot = wishing.root;
    treeRoot.position.copy(TREE);
    // The model's front (where the leaves go) is +z, with its hedge behind.
    treeRoot.rotation.y = TREE_YAW;
    scene.add(treeRoot);
    // More of the same hedge: either side of the tree's own (a little behind it, where they
    // overlap), then two arms reaching towards you. Each piece is 6 m long, standing just behind
    // its origin, facing +z.
    const hedgeAt = (x: number, z: number, turn: number, length: number) =>
      new Matrix4().compose(byTree(x, z), new Quaternion().setFromAxisAngle(UP, TREE_YAW + turn), new Vector3(length / 6, 1, 1));
    scene.add(
      instanceModel(
        wishing,
        [
          hedgeAt(-3, -0.08, 0, 6),
          hedgeAt(3, -0.08, 0, 6),
          hedgeAt(-6.04, 2.5, Math.PI / 2, 7),
          hedgeAt(6.04, 2.5, -Math.PI / 2, 7),
        ],
        { only: 'hedge' },
      ),
    );
    treeRoot.updateMatrixWorld(true);
    wishing.node('leaf_anchors')?.traverse((o) => {
      if (o.name.startsWith('anchor_')) anchors.push(o.getWorldPosition(new Vector3()));
    });
  } else {
    // A white tree, flattened into a board.
    const white = forest([{ species: 'oak', at: [{ x: 0, z: 0, scale: 0.62, yaw: 0 }] }], { bark: new Color(0.85, 0.85, 0.82), leafless: true });
    treeRoot = white.group;
    treeRoot.scale.z = 0.08;
    treeRoot.position.copy(TREE);
    treeRoot.rotation.y = 0.5;
    scene.add(treeRoot);
    treeRoot.updateMatrixWorld(true);
    for (const a of white.anchors) anchors.push(a.clone().applyMatrix4(treeRoot.matrixWorld));
    const hedge = new Mesh(new BoxGeometry(9, 3.2, 0.8), hallow(new MeshStandardMaterial({ color: 0x06180a, roughness: 0.95 }), { key: 'hedge', glow: 0.5 }));
    hedge.position.copy(TREE).add(new Vector3(0.6, 1.5, -1.2));
    hedge.rotation.y = 0.5;
    scene.add(hedge);
  }
  // The wish-writing table along the hedge: a black cloth, a little lamp, pencils, leaf cards.
  const table = new Group();
  const cloth = hallow(new MeshStandardMaterial({ color: 0x050506, roughness: 0.85 }), { key: 'cloth', glow: 1 });
  const top = new Mesh(new BoxGeometry(2.6, 0.76, 0.85), cloth);
  top.position.y = 0.38;
  table.add(top);
  const lampMat = hallow(new MeshStandardMaterial({ color: 0x111111, roughness: 0.4, metalness: 0.5 }), { key: 'lamp' });
  const stem = new Mesh(new BoxGeometry(0.02, 0.36, 0.02), lampMat);
  stem.position.set(0.3, 0.94, 0);
  const shade = new Mesh(new BoxGeometry(0.2, 0.04, 0.2), hallow(new MeshStandardMaterial({ color: 0x111111, emissive: 0xdde8ff, emissiveIntensity: 3 }), { key: 'lampglow' }));
  shade.position.set(0.3, 1.13, 0);
  const cup = new Mesh(new BoxGeometry(0.09, 0.12, 0.09), lampMat);
  cup.position.set(0.55, 0.82, 0.15);
  table.add(stem, shade, cup);
  const cardTex = (() => {
    const c = document.createElement('canvas');
    c.width = 128;
    c.height = 96;
    const g = c.getContext('2d') as CanvasRenderingContext2D;
    g.fillStyle = '#f2efe8';
    g.fillRect(0, 0, 128, 96);
    for (let y = 0; y < 4; y++)
      for (let x = 0; x < 6; x++) {
        g.fillStyle = (x + y) % 3 === 0 ? '#3cc4b0' : (x + y) % 3 === 1 ? '#f07a6a' : '#f2a03a';
        g.beginPath();
        g.ellipse(12 + x * 20, 14 + y * 22, 8, 5, 0.6, 0, Math.PI * 2);
        g.fill();
      }
    const t = new CanvasTexture(c);
    t.colorSpace = SRGBColorSpace;
    return t;
  })();
  const cardMat = hallow(new MeshStandardMaterial({ map: cardTex, roughness: 0.8 }), { key: 'card', glow: 1 });
  for (let k = 0; k < 6; k++) {
    const card = new Mesh(new PlaneGeometry(0.28, 0.21), cardMat);
    card.rotation.x = -Math.PI / 2;
    card.rotation.z = (rnd() - 0.5) * 0.6;
    card.position.set(-1.05 + k * 0.33, 0.765, (rnd() - 0.5) * 0.3);
    table.add(card);
  }
  // Along the right-hand arm of the hedge, inside, facing in: the tree is off to your left.
  const TABLE = byTree(5.27, 2.8);
  table.position.copy(TABLE);
  table.rotation.y = TREE_YAW - Math.PI / 2;
  scene.add(table);
  const tableBox = new Box3().setFromObject(table).expandByScalar(0.1);

  // Leaves: hundreds of coral and teal wish tags on the branches (more along each anchor).
  const leafPositions: { p: Vector3; color: Color; spin: number }[] = [];
  const coral = new Color(1, 0.36, 0.3).multiplyScalar(0.86);
  const teal = new Color(0.16, 0.86, 0.74).multiplyScalar(0.78);
  const perAnchor = Math.max(1, Math.round((tier === 'low' ? 320 : 700) / Math.max(1, anchors.length)));
  for (const a of anchors) {
    for (let k = 0; k < perAnchor; k++) {
      leafPositions.push({ p: a.clone().add(new Vector3((rnd() - 0.5) * 0.5, (rnd() - 0.5) * 0.5, (rnd() - 0.5) * 0.08)), color: rnd() < 0.55 ? coral : teal, spin: rnd() * 6.28 });
    }
  }
  const leafGeo = new PlaneGeometry(0.2, 0.1);
  // Leaves read as lit by the tree's white wash; wish leaves glow gold.
  const leafMat = hallow(new MeshBasicMaterial({ color: 0xffffff, side: DoubleSide }), { key: 'wishleaf' });
  const leaves = new InstancedMesh(leafGeo, leafMat, leafPositions.length + 400);
  const yawTree = treeRoot.rotation.y;
  leafPositions.forEach((l, i) => {
    const q = new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), yawTree).multiply(new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), l.spin));
    leaves.setMatrixAt(i, new Matrix4().compose(l.p, q, new Vector3(1, 1, 1)));
    leaves.setColorAt(i, l.color);
  });
  leaves.count = leafPositions.length;
  leaves.computeBoundingSphere();
  leaves.frustumCulled = false;
  scene.add(leaves);

  // Wishes: the group's, kept in its shared saves, shown as golden leaves.
  const wishes: Wish[] = [];
  try {
    const saved = await portal.save.shared.get<Wish[]>('wishes');
    if (saved) wishes.push(...saved);
  } catch {
    // None yet.
  }
  const wishLeaf = new Map<number, Wish>();
  const addWishLeaf = (w: Wish) => {
    const a = anchors[w.anchor % Math.max(1, anchors.length)];
    if (!a) return;
    const i = leaves.count;
    if (i >= leaves.instanceMatrix.count) return;
    leaves.count++;
    const q = new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), yawTree).multiply(new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), w.anchor * 2.4));
    leaves.setMatrixAt(i, new Matrix4().compose(a.clone().add(new Vector3(0, -0.08, 0.06)), q, new Vector3(1.6, 1.6, 1.6)));
    leaves.setColorAt(i, (w.color === 'coral' ? coral : teal).clone().lerp(new Color(1, 0.85, 0.4), 0.5).multiplyScalar(5));
    leaves.instanceMatrix.needsUpdate = true;
    if (leaves.instanceColor) leaves.instanceColor.needsUpdate = true;
    wishLeaf.set(i, w);
  };
  for (const w of wishes) addWishLeaf(w);
  const offSession = portal.session.on<Wish>('wish', (w) => {
    wishes.push(w);
    addWishLeaf(w);
    ctx.ui.showWish(w.text, w.by);
  });
  const offCandle = portal.session.on<{ i: number }>('candle', ({ i }) => lightCandle(i, false));

  // The giant guitar beside the ofrenda, its neon strings rising into green fog.
  const theGuitar = await guitar(ctx, GUITAR, -1.35);
  scene.add(...theGuitar.objects);
  theGuitar.onSong = () => {
    butterflies.release(pointOnGround(GUITAR.clone().setY(1.5)), 14);
    void ctx.audio.sfx('ember-chime-marigold', { at: pointOnGround(GUITAR), volume: 1 });
    ctx.ui.say('The Ember’s song, on the strings of the giant guitar.', 5);
  };
  mask.blob(GUITAR.x, GUITAR.z, 5, 'g', 0.8);

  // Light: the crest's teal, warm candles, a white wash on the tree.
  const glowLights: GlowLight[] = [...marigolds.lights, ...theGuitar.glow];
  candleSpots.forEach((p) => glowLights.push({ x: p.x, z: p.z, radius: 1.2, color: new Color(1, 0.6, 0.25), intensity: 0.1, flicker: 1, phase: Math.random() }));
  glowLights.push({ x: OFRENDA.x, z: OFRENDA.z + 1, radius: 7, color: new Color(0.2, 0.9, 0.75), intensity: 0.35, flicker: 0 });
  glowLights.push({ x: TREE.x, z: TREE.z + 2, radius: 6, color: new Color(1, 0.9, 0.78), intensity: 0.62, flicker: 0 });
  glowLights.push({ x: TABLE.x, z: TABLE.z, radius: 2.2, color: new Color(0.85, 0.9, 1), intensity: 0.6, flicker: 0 });
  const sources: LightSource[] = [
    ...theGuitar.sources,
    { position: OFRENDA.clone().add(new Vector3(0, 4.2, 1.2)), color: new Color(0.3, 1, 0.85), intensity: 5, distance: 9 },
    { position: OFRENDA.clone().add(new Vector3(0, 0.9, 2.2)), color: new Color(1, 0.65, 0.3), intensity: 4, distance: 6 },
    { position: TREE.clone().add(new Vector3(0, 2.5, 3.5)), color: new Color(1, 0.93, 0.8), intensity: 8.5, distance: 10 },
    { position: TABLE.clone().add(new Vector3(0, 1.1, 0)), color: new Color(0.85, 0.9, 1), intensity: 2.5, distance: 3.5 },
  ];
  scene.add(new HemisphereLight(0x284050, 0x080604, 0.3));

  // Low mist.
  const fog = new FogBank({ bounds: mask.bounds, mask: mask.texture(), slices: tier === 'low' ? 4 : 8, height: 1.4, tint: new Color(0.03, 0.045, 0.045), density: 0.3, glow: 1.2 });
  scene.add(fog.mesh);

  const butterflies = new Butterflies(tier === 'low' ? 40 : 90);
  scene.add(butterflies.mesh);
  const sky = new SkyLanterns(tier === 'low' ? 300 : 700, TREE);
  scene.add(sky.mesh);

  const night = skyState({ zenith: new Color(0.003, 0.008, 0.03), horizon: new Color(0.02, 0.04, 0.06), stars: 1.1, lightPollution: new Color(0.04, 0.025, 0.01) });
  const grade: Grade = { ...defaultGrade(), exposure: 1.1, bloom: 0.11, saturation: 1.22, power: 1.08, tint: new Color(0.98, 1.02, 1.0), lift: new Color(0.004, 0.01, 0.014) };

  let time = 0;
  let offerOff: (() => void) | null = null;
  const takeOfferDown = () => {
    offerOff?.();
    offerOff = null;
  };
  let hung = false;
  let atTree = 0;
  let finale = -1;
  let candleHint = false;
  const tmp = new Vector2();

  function lightCandle(i: number, mine: boolean) {
    if (lit[i]) return;
    setFlame(i, true);
    const p = candleSpots[i] as Vector3;
    butterflies.release(p, 6);
    void ctx.audio.sfx('candle-light', { at: pointOnGround(p), volume: 0.8 });
    if (mine) {
      setTimeout(() => void ctx.audio.sfx('butterflies', { at: pointOnGround(p), volume: 0.7 }), 300);
      ctx.ui.say('For someone you remember.', 5);
      void portal.session.send('candle', { i });
      void portal.save.shared
        .update<Candles>('candles', (c) => ({ lit: [...new Set([...(c?.lit ?? []), i])] }))
        .catch(() => undefined);
    }
  }

  // While the wish is being written there's no offer, and none may appear behind the card.
  let writing = false;
  async function hangWish() {
    offerOff?.();
    offerOff = null;
    writing = true;
    const w = await ctx.ui.askWish();
    writing = false;
    if (!w) {
      takeOfferDown();
      offerOff = ctx.ui.offer('Write a wish', () => void hangWish());
      return;
    }
    const used = new Set(wishes.map((x) => x.anchor));
    let anchor = Math.floor(Math.random() * Math.max(1, anchors.length));
    for (let k = 0; k < anchors.length && used.has(anchor); k++) anchor = (anchor + 7) % anchors.length;
    const wish: Wish = { text: w.text.slice(0, 80), color: w.color, by: portal.me.name, anchor };
    wishes.push(wish);
    addWishLeaf(wish);
    void ctx.audio.sfx('wish-hang', { at: pointOnGround(anchors[anchor] ?? TREE), volume: 0.85 });
    void portal.session.send('wish', wish);
    void portal.save.shared.update<Wish[]>('wishes', (list) => [...(list ?? []), wish].slice(-300)).catch(() => undefined);
    hung = true;
    ctx.ui.say('Your wish is on the tree.', 4);
    setTimeout(() => startFinale(), 2500);
  }

  function startFinale() {
    if (finale >= 0) return;
    finale = 0;
    offerOff?.();
    offerOff = null;
    ctx.audio.stopAll(4);
    setTimeout(() => void ctx.audio.cue('finale', 1), 1500);
    ctx.ui.say('The Ember has found where it belongs.', 6);
  }

  const chapter: Chapter = {
    scene,
    path,
    terrain,
    music: 'marigold',
    ambience: 'marigold',
    steps: 'step-gravel',

    enter() {
      ctx.glow.setBounds(bounds[0], bounds[1], bounds[2], bounds[3]);
      ctx.glow.setLights(glowLights);
      ctx.glow.wave = 1e9;
      ctx.lights.sources = sources;
      lerpSky(ctx.sky.state, night, night, 0);
      lerpGrade(ctx.post.grade, grade, grade, 0);
      shared.uFogColor.value.set(0.02, 0.035, 0.04);
      shared.uFogDensity.value = 0.03;
      shared.uFogHeight.value = 6;
      shared.uFogGlow.value = 0.9;
      ctx.ember.presence = 1;
      ctx.ember.place(new Vector3(0, 1.8, 6));
      ctx.audio.preload('marigold', ['candle-light', 'butterflies', 'wish-hang']);
      setTimeout(() => ctx.ui.say('The water drains away. Marigolds, and warm candlelight.', 6), 3000);
    },

    update(dt) {
      time += dt;
      const w = ctx.walker;
      const e = ctx.ember;
      butterflies.update(dt, time);
      theGuitar.update(dt, time);
      sky.update(dt);
      const nearOfrenda = Math.hypot(w.position.x - OFRENDA.x, w.position.z - (OFRENDA.z + 3)) < 6;
      if (nearOfrenda && !candleHint) {
        candleHint = true;
        ctx.ui.say('Tap a candle to light it for someone you remember.', 6);
      }
      const nearTree = Math.hypot(w.position.x - TREE.x, w.position.z - TREE.z) < 9;
      if (nearTree) atTree += dt;
      if (nearTree && !offerOff && !writing && !hung && finale < 0) {
        offerOff = ctx.ui.offer('Write a wish', () => void hangWish());
        ctx.ui.say('Write a wish at the table, and hang it on the tree.', 6);
      }
      if (!nearTree && offerOff && finale < 0) {
        offerOff();
        offerOff = null;
      }
      // If you'd rather just stand and look, the night ends gently anyway.
      if (atTree > 75 && finale < 0) startFinale();

      if (finale >= 0) {
        finale += dt;
        // The Ember settles on a branch and becomes a leaf of light.
        const a = anchors[Math.floor(anchors.length * 0.62)] ?? TREE.clone().add(new Vector3(0, 3, 0));
        e.target.copy(a).add(new Vector3(0, 0.15, 0.1));
        e.agility = 1.4;
        if (finale > 4 && finale < 4.1) {
          addWishLeaf({ text: 'The Ember', color: 'coral', by: '', anchor: anchors.indexOf(a) });
          void ctx.audio.sfx('wish-hang', { at: pointOnGround(a), volume: 0.85 });
        }
        if (finale > 4) e.presence = Math.max(0, e.presence - dt * 0.6);
        if (finale > 6 && finale < 6.1) {
          sky.start();
          ctx.ui.say('And every lantern of the night rises, together.', 7);
        }
        if (finale > 50 && finale < 50.1) ctx.ui.ending(() => ctx.restart());
      } else {
        // The Ember: to the ofrenda first, hovering among the candles, then on to the tree.
        if (w.s < 14) e.target.copy(OFRENDA).add(new Vector3(Math.sin(time * 0.6) * 1.6, 1.4 + Math.sin(time) * 0.2, 1.8));
        else {
          path.at(Math.min(path.length, w.s + 4), tmp);
          e.target.set(tmp.x, 2, tmp.y);
        }
      }
      ctx.glow.moving.length = 0;
      if (e.presence > 0.01) ctx.glow.moving.push(e.glow);
      fog.walkers[0]?.set(w.position.x, w.position.z);
      fog.update();
    },

    pick(ray: Ray): TapAction | null {
      const strum = theGuitar.pick(ray);
      if (strum) return strum;
      if (!hung && finale < 0 && ray.intersectsBox(tableBox.clone().translate(new Vector3(0, heightAt(TABLE.x, TABLE.z), 0)))) return () => void hangWish();
      if (ray.intersectsBox(candleBox.clone().translate(new Vector3(0, heightAt(OFRENDA.x, OFRENDA.z), 0)))) {
        // The nearest unlit candle to the ray.
        let best = -1;
        let bestD = 0.3;
        candleSpots.forEach((p, i) => {
          const d = Math.sqrt(ray.distanceSqToPoint(pointOnGround(p)));
          if (d < bestD && !lit[i]) {
            bestD = d;
            best = i;
          }
        });
        if (best >= 0) return () => lightCandle(best, true);
      }
      // A golden leaf: read its wish.
      for (const [i, wsh] of wishLeaf) {
        const m = new Matrix4();
        leaves.getMatrixAt(i, m);
        const p = new Vector3().setFromMatrixPosition(m);
        if (Math.sqrt(ray.distanceSqToPoint(pointOnGround(p))) < 0.15) return () => ctx.ui.showWish(wsh.text, wsh.by);
      }
      return null;
    },

    finished() {
      return false;
    },

    dispose() {
      theGuitar.dispose();
      offSession();
      offCandle();
      offerOff?.();
      terrain.dispose();
      woods.dispose();
      canopy.dispose();
      butterflies.dispose();
      sky.dispose();
      fog.dispose();
      floor.geometry.dispose();
      leafGeo.dispose();
      leafMat.dispose();
      marigolds.mesh.geometry.dispose();
    },
  };
  return chapter;
}
