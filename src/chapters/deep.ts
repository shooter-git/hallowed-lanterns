import {
  AdditiveBlending,
  Box3,
  BufferAttribute,
  BufferGeometry,
  Color,
  DoubleSide,
  ExtrudeGeometry,
  Float32BufferAttribute,
  HemisphereLight,
  InstancedBufferAttribute,
  InstancedBufferGeometry,
  Mesh,
  MeshBasicMaterial as MeshBasicGlow,
  type MeshStandardMaterial,
  type Object3D,
  PlaneGeometry,
  Quaternion,
  type Ray,
  Scene,
  ShaderMaterial,
  Shape,
  Vector2,
  Vector3,
} from 'three';
import { Beams } from '../engine/beams.ts';
import { CARVE } from '../engine/carvings.ts';
import type { GlowLight } from '../engine/glowfield.ts';
import { type Bounds, ground, GroundMask } from '../engine/ground.ts';
import type { LightSource } from '../engine/lights.ts';
import { loadModel } from '../engine/models.ts';
import { defaultGrade, type Grade, lerpGrade } from '../engine/post.ts';
import { clearOf, PumpkinField, type PumpkinSpec } from '../engine/pumpkins.ts';
import { Path } from '../engine/rig.ts';
import { kraken } from '../scenes/kraken.ts';
import { aroundPath, onGround, pointOnGround, Terrain } from '../engine/terrain.ts';
import { hallow, SHADER_PARS, shared, VERTEX_TERRAIN } from '../engine/shared.ts';
import { lerpSky, skyState, treeLine } from '../engine/sky.ts';
import { woodland } from '../engine/canopy.ts';
import { forest, lineThePath } from '../engine/trees.ts';
import { Drift } from '../engine/weather.ts';
import type { Chapter, ChapterContext, TapAction } from './types.ts';

/**
 * VII. The Deep — the snow has become bubbles and blue light pours in: you walk the sea floor
 * under pumpkin jellyfish trailing glowing ribbons, past glowing coral and pufferfish, over beds of
 * blue lights. At the end the Keeper of the Deep rises from waves of light: a giant octopus with a
 * pumpkin for a head and ember-orange eyes. Wave to it, and it waves back.
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

const KEEPER = new Vector3(0, 0, -60);
/**
 * Near the Keeper: from here it rises, asks for a wave (and waves first if you don't), and once it has
 * waved the night goes on from wherever you stand. (Walking by hand, people stop to look well before the
 * path's end, 11 m from it; only "Walk with me" always went all the way.)
 */
const KEEPER_NEAR = 22;
const WRECK = new Vector3(-8.5, 0, -14);
const TREASURE = new Vector3(5.6, 0, -32.5);

/** Ribbons of light along both sides of the path: beds of tiny blue LEDs, twinkling. */
function ledBeds(path: Path, inner: number, outer: number): Mesh {
  const pos: number[] = [];
  const idx: number[] = [];
  const t = new Vector2();
  const p = new Vector2();
  for (const side of [-1, 1]) {
    const base = pos.length / 3;
    let n = 0;
    for (let s = 0; s <= path.length; s += 0.5) {
      path.at(s, p, t);
      const nx = -t.y * side;
      const nz = t.x * side;
      const wobble = Math.sin(s * 0.45 + side) * 0.5;
      pos.push(p.x + nx * inner, 0.012, p.y + nz * inner, p.x + nx * (outer + wobble), 0.012, p.y + nz * (outer + wobble));
      n++;
    }
    for (let i = 0; i < n - 1; i++) {
      const a = base + i * 2;
      idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  const mat = new ShaderMaterial({
    uniforms: { ...shared },
    vertexShader: /* glsl */ `
      varying vec3 vHlWorld;
      ${VERTEX_TERRAIN}
      void main() { vHlWorld = (modelMatrix * vec4(position, 1.0)).xyz; vHlWorld.y += hlTerrain(vHlWorld.xz); gl_Position = projectionMatrix * viewMatrix * vec4(vHlWorld, 1.0); }`,
    fragmentShader: /* glsl */ `
      ${SHADER_PARS}
      varying vec3 vHlWorld;
      void main() {
        vec2 g = vHlWorld.xz / 0.11;
        vec2 cell = floor(g);
        vec2 o = hlHash22(cell) * 0.6 + 0.2;
        float d = length(fract(g) - o);
        float on = step(0.35, hlHash12(cell + 3.1));
        float tw = 0.6 + 0.4 * sin(uHlTime * (1.0 + hlHash12(cell) * 3.0) + hlHash12(cell + 9.0) * 40.0);
        float led = smoothstep(0.14, 0.0, d) * on * tw;
        vec3 col = vec3(0.12, 0.28, 1.0) * led * 9.0;
        col = hlApplyFog(col, vHlWorld);
        gl_FragColor = vec4(col, 1.0);
      }`,
    blending: AdditiveBlending,
    transparent: true,
    depthWrite: false,
  });
  const mesh = new Mesh(g, mat);
  mesh.renderOrder = 2;
  return mesh;
}

/** Light rippling over the sea floor, as through moving water. */
function caustics(bounds: Bounds): Mesh {
  const [minX, minZ, sx, sz] = bounds;
  const geo = new PlaneGeometry(sx, sz, Math.ceil(sx / 1.5), Math.ceil(sz / 1.5));
  geo.rotateX(-Math.PI / 2);
  geo.translate(minX + sx / 2, 0.02, minZ + sz / 2);
  const mat = new ShaderMaterial({
    uniforms: { ...shared },
    vertexShader: /* glsl */ `
      varying vec3 vHlWorld;
      ${VERTEX_TERRAIN}
      void main() { vHlWorld = (modelMatrix * vec4(position, 1.0)).xyz; vHlWorld.y += hlTerrain(vHlWorld.xz); gl_Position = projectionMatrix * viewMatrix * vec4(vHlWorld, 1.0); }`,
    fragmentShader: /* glsl */ `
      ${SHADER_PARS}
      varying vec3 vHlWorld;
      float cell(vec2 p) {
        vec2 n = floor(p); vec2 f = fract(p); float d = 8.0;
        for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
          vec2 g = vec2(float(i), float(j));
          vec2 o = 0.5 + 0.45 * sin(uHlTime * 0.7 + 6.2831 * hlHash22(n + g));
          d = min(d, length(g + o - f));
        }
        return d;
      }
      void main() {
        // Far off the ripples fade to nothing: don't work them out there.
        float fade = exp(-distance(vHlWorld, cameraPosition) * 0.07);
        if (fade < 0.02) discard;
        vec2 p = vHlWorld.xz * 0.9;
        float c = pow(cell(p), 2.5) + pow(cell(p * 1.7 + 3.0), 2.5) * 0.6;
        float k = smoothstep(0.25, 0.85, c);
        vec3 col = vec3(0.25, 0.55, 1.0) * k * 0.35 * fade;
        gl_FragColor = vec4(col, 1.0);
      }`,
    blending: AdditiveBlending,
    transparent: true,
    depthWrite: false,
  });
  const m = new Mesh(geo, mat);
  m.renderOrder = 3;
  return m;
}

/** Jellyfish ribbons: long pale streamers hanging from each bell, swaying in the current. */
function streamers(anchors: { p: Vector3; len: number; phase: number }[]): Mesh<InstancedBufferGeometry, ShaderMaterial> {
  const plane = new PlaneGeometry(0.1, 1, 1, 14);
  plane.translate(0, -0.5, 0);
  const geo = new InstancedBufferGeometry();
  geo.index = plane.index;
  geo.setAttribute('position', plane.getAttribute('position'));
  geo.setAttribute('uv', plane.getAttribute('uv'));
  const at = new Float32Array(anchors.length * 4);
  const ph = new Float32Array(anchors.length);
  anchors.forEach((a, i) => {
    at.set([a.p.x, a.p.y, a.p.z, a.len], i * 4);
    ph[i] = a.phase;
  });
  geo.setAttribute('aAt', new InstancedBufferAttribute(at, 4));
  geo.setAttribute('aPhase', new InstancedBufferAttribute(ph, 1));
  geo.instanceCount = anchors.length;
  const mesh = new Mesh(
    geo,
    new ShaderMaterial({
      uniforms: { ...shared },
      vertexShader: /* glsl */ `
        attribute vec4 aAt;
        attribute float aPhase;
        uniform float uHlTime;
        varying float vT;
        varying float vX;
        varying float vPhase;
        varying vec3 vHlWorld;
        ${VERTEX_TERRAIN}
        void main() {
          float t = -position.y;           // 0 at the bell, 1 at the tip
          vT = t;
          vX = position.x * 20.0;          // -1 … 1 across
          vPhase = aPhase;
          float wave = sin(uHlTime * 1.4 - t * 6.0 + aPhase * 6.28) * 0.12 * t;
          float wave2 = cos(uHlTime * 0.9 - t * 4.0 + aPhase * 3.0) * 0.1 * t;
          vec3 w = aAt.xyz + vec3(wave + cos(aPhase * 6.28) * 0.08, -t * aAt.w + hlTerrain(aAt.xz), wave2 + sin(aPhase * 6.28) * 0.08);
          // Face the camera around the vertical axis.
          vec3 toCam = normalize(vec3(cameraPosition.x - w.x, 0.0, cameraPosition.z - w.z));
          vec3 side = vec3(toCam.z, 0.0, -toCam.x);
          w += side * position.x * (1.0 - t * 0.5);
          // Curl like ribbon.
          w += side * sin(t * 9.0 + aPhase * 10.0) * 0.03;
          vHlWorld = w;
          gl_Position = projectionMatrix * viewMatrix * vec4(w, 1.0);
        }`,
      fragmentShader: /* glsl */ `
        ${SHADER_PARS}
        varying float vT;
        varying float vX;
        varying float vPhase;
        varying vec3 vHlWorld;
        void main() {
          // Translucent: soft across, warm from the bell near the top, thinning to a faint blue
          // toward the tip, and now and then a glow runs down it.
          float across = max(1.0 - vX * vX, 0.0);
          float thin = (1.0 - vT) * (1.0 - vT) * 0.85 + 0.15 * (1.0 - vT);
          vec3 col = mix(vec3(1.0, 0.62, 0.38), vec3(0.6, 0.72, 1.0), vT) * (1.5 * thin + 0.1);
          float run = fract(uHlTime * 0.22 + vPhase);
          col += vec3(0.6, 0.8, 1.0) * smoothstep(0.1, 0.0, abs(vT - run)) * 0.8 * (1.0 - vT);
          col = hlApplyFog(col, vHlWorld) * across;
          gl_FragColor = vec4(col, 1.0);
        }`,
      transparent: true,
      depthWrite: false,
      blending: AdditiveBlending,
      side: DoubleSide,
    }),
  );
  // The ribbons are placed by the shader, all along the path: the geometry's own bounds (one
  // ribbon at the origin) would cull every one of them at once whenever the origin left the view.
  mesh.frustumCulled = false;
  return mesh;
}

/** A flat painted coral cut-out board, branching, in a neon colour. */
function coral(height: number, color: Color, seed: number): Mesh {
  const rnd = rng(seed);
  const s = new Shape();
  // Built as a thick branching outline: trunk then forks, each a rounded finger.
  const fingers: { x: number; h: number; w: number; lean: number }[] = [];
  const n = 3 + Math.floor(rnd() * 3);
  for (let i = 0; i < n; i++) fingers.push({ x: (i / (n - 1) - 0.5) * height * 0.7, h: height * (0.55 + rnd() * 0.45), w: height * 0.07, lean: (rnd() - 0.5) * 0.3 });
  s.moveTo(-height * 0.08, 0);
  for (const f of fingers) {
    const tx = f.x + f.lean * f.h;
    s.lineTo(f.x * 0.25 - f.w, height * 0.25);
    s.quadraticCurveTo(f.x - f.w, f.h * 0.6, tx - f.w, f.h - f.w);
    s.quadraticCurveTo(tx, f.h + f.w * 0.8, tx + f.w, f.h - f.w);
    s.quadraticCurveTo(f.x + f.w, f.h * 0.6, f.x * 0.25 + f.w, height * 0.28);
  }
  s.lineTo(height * 0.08, 0);
  s.lineTo(-height * 0.08, 0);
  const geo = new ExtrudeGeometry(s, { depth: 0.04, bevelEnabled: false, curveSegments: 6 });
  return new Mesh(geo, hallow(new MeshBasicGlow({ color }), { key: 'coral' }));
}

/** Joints along each of the Keeper's arms; the arm bends smoothly between them. */
const ARM_JOINTS = 24;

/**
 * Bends an arm along its length (the model's `along` UVs: 0 at the root, 1 at the tip): every
 * vertex keeps its place around the arm's centre line, which follows the joints (positions and
 * turns from `bendArm`), so the arm curls and sweeps without stretching, its suckers turning with it.
 */
const ARM_VERTEX_PARS = /* glsl */ `
#define HL_JOINTS ${ARM_JOINTS}
uniform vec3 uRest[HL_JOINTS];
uniform vec3 uPos[HL_JOINTS];
uniform vec4 uRot[HL_JOINTS];
vec3 hlTurn(vec4 q, vec3 v) { return v + 2.0 * cross(q.xyz, cross(q.xyz, v) + q.w * v); }
`;
const ARM_NORMAL = /* glsl */ `
#include <beginnormal_vertex>
float hlU = clamp(uv1.x, 0.0, 1.0) * float(HL_JOINTS - 1);
int hlJ = int(min(floor(hlU), float(HL_JOINTS - 2)));
float hlF = hlU - float(hlJ);
vec4 hlQ = normalize(mix(uRot[hlJ], uRot[hlJ + 1], hlF));
objectNormal = hlTurn(hlQ, objectNormal);
`;
const ARM_VERTEX = /* glsl */ `
#include <begin_vertex>
transformed = mix(uPos[hlJ], uPos[hlJ + 1], hlF) + hlTurn(hlQ, transformed - mix(uRest[hlJ], uRest[hlJ + 1], hlF));
`;

/** One of the Keeper's arms: its centre line at rest, and how it's bent now. */
interface Arm {
  /** The centre line at each joint, at rest (in the arm's own space). */
  rest: Vector3[];
  tangent: Vector3[];
  /** Turning about this bends the arm within its own upright plane (+ lifts it). */
  plane: Vector3;
  /** Turning about these (one per joint) bends it out of that plane. */
  side: Vector3[];
  /** Radians each joint turns when the arm is raised (to wave, or a little, in sympathy). */
  raise: number[];
  /** How far the raised arm turns its suckers toward you (radians). */
  twist: number;
  /** 1 for the arm that waves, a little for the others. */
  react: number;
  seed: number;
  /** How far the lift and the sweeps have travelled out along the arm, joint by joint (0–1). */
  lift: Float32Array;
  sweep: Float32Array;
  /** The root's own eased lift and sweep (the first stage of each, so they start gently). */
  drive: [number, number];
  pos: Float32Array;
  rot: Float32Array;
}

/** The arm's centre line at its joints: the middle of each ring of the tube (suckers left out). */
function armCentre(geo: BufferGeometry): Vector3[] {
  const pos = geo.getAttribute('position');
  const uv = geo.getAttribute('uv');
  const along = geo.getAttribute('uv1');
  const rings = new Map<number, Vector3 & { n?: number }>();
  for (let i = 0; i < pos.count; i++) {
    // The suckers are painted from their own corner of the texture, below the arm's.
    if (uv.getY(i) > 0.876) continue;
    const key = Math.round(along.getX(i) * 1e4);
    let r = rings.get(key);
    if (!r) rings.set(key, (r = Object.assign(new Vector3(), { n: 0 })));
    r.x += pos.getX(i);
    r.y += pos.getY(i);
    r.z += pos.getZ(i);
    r.n = (r.n ?? 0) + 1;
  }
  const ring = [...rings].sort((a, b) => a[0] - b[0]).map(([k, r]) => ({ a: k / 1e4, p: r.divideScalar(r.n ?? 1) }));
  const out: Vector3[] = [];
  let j = 0;
  for (let k = 0; k < ARM_JOINTS; k++) {
    const a = k / (ARM_JOINTS - 1);
    while (j < ring.length - 2 && (ring[j + 1] as (typeof ring)[number]).a < a) j++;
    const r0 = ring[j] as (typeof ring)[number];
    const r1 = ring[j + 1] as (typeof ring)[number];
    out.push(r0.p.clone().lerp(r1.p, Math.min(1, Math.max(0, (a - r0.a) / Math.max(1e-6, r1.a - r0.a)))));
  }
  return out;
}

const smooth = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
const DEG = Math.PI / 180;
const _qa = new Quaternion();
const _qb = new Quaternion();
const _qt = new Quaternion();
const _v = new Vector3();
const _p = new Vector3();
const _segs = Array.from({ length: ARM_JOINTS - 1 }, () => new Quaternion());

/**
 * Bends an arm: each joint turns within the arm's plane (`bend`, radians) and out of it (`side`),
 * and the turns add up from the root to the tip; then each ring of the tube turns about the arm
 * by `twist`. Writes the joints' places and turns into the arm's uniforms.
 */
function bendArm(arm: Arm, bend: (k: number) => number, side: (k: number) => number, twist: (k: number) => number) {
  const n = ARM_JOINTS;
  _p.copy(arm.rest[0] as Vector3).toArray(arm.pos, 0);
  for (let k = 0; k < n - 1; k++) {
    const q = (_segs[k] as Quaternion).copy(k ? (_segs[k - 1] as Quaternion) : _qa.identity());
    q.multiply(_qb.setFromAxisAngle(arm.plane, bend(k))).multiply(_qb.setFromAxisAngle(arm.side[k] as Vector3, side(k)));
    _p.add(_v.subVectors(arm.rest[k + 1] as Vector3, arm.rest[k] as Vector3).applyQuaternion(q)).toArray(arm.pos, (k + 1) * 3);
  }
  _qb.identity();
  for (let k = 0; k < n; k++) {
    // At a joint, halfway between the turns of the stretches either side of it.
    const q = _qa.copy(_segs[Math.max(0, k - 1)] as Quaternion);
    if (k > 0 && k < n - 1) q.slerp(_segs[k] as Quaternion, 0.5);
    q.multiply(_qt.setFromAxisAngle(arm.tangent[k] as Vector3, twist(k)));
    // Keep neighbours in the same hemisphere so the shader's blend between them is the short way.
    if (q.dot(_qb) < 0) q.set(-q.x, -q.y, -q.z, -q.w);
    _qb.copy(q).toArray(arm.rot, k * 4);
  }
}

/**
 * Builds the Keeper's arm `index` from its mesh: finds its centre line and its plane, works out
 * the raised pose (for the arm that waves: out from the body and up, the curl at its tip held high)
 * and how far to turn its suckers toward you, and patches its material to bend.
 */
function makeArm(mesh: Mesh, index: number, waver: boolean, reacts: number): Arm {
  const n = ARM_JOINTS;
  const rest = armCentre(mesh.geometry);
  const tangent = rest.map((_, k) => (rest[Math.min(n - 1, k + 1)] as Vector3).clone().sub(rest[Math.max(0, k - 1)] as Vector3).normalize());
  const up = new Vector3(0, 1, 0);
  const out = (rest[Math.round(n * 0.35)] as Vector3).clone().sub(rest[0] as Vector3).setY(0).normalize();
  const plane = out.clone().cross(up).normalize();
  const side = tangent.map((t) => t.clone().cross(plane).normalize());
  // Elevation of each stretch of the arm (radians above the horizontal, outward).
  const elev = rest.slice(0, -1).map((p, k) => {
    _v.subVectors(rest[k + 1] as Vector3, p);
    return Math.atan2(_v.dot(up), _v.dot(out));
  });
  const raise: number[] = [];
  if (waver) {
    // Raised: a long arc out from the body and up beside its head, the curled tip (left as it is)
    // held high and opened a little.
    const curl = 0.72;
    let held = 0;
    let before = 0;
    for (let k = 0; k < n - 1; k++) {
      const a = (k + 0.5) / (n - 1);
      let total: number;
      if (a <= curl) {
        total = (12 + 80 * smooth(0.12, 0.66, a)) * DEG - (elev[k] as number);
        held = total;
      } else total = held - 22 * DEG * smooth(curl, 0.95, a);
      raise.push(total - before);
      before = total;
    }
  } else {
    // In sympathy: the outer arm curls a little (rising arms lean out instead, away from the body).
    const sign = (elev[Math.round(n * 0.6)] as number) > 45 * DEG ? -1 : 1;
    for (let k = 0; k < n - 1; k++) raise.push(sign * reacts * 7 * DEG * smooth(0.45, 0.85, k / (n - 1)));
  }
  const arm: Arm = {
    rest, tangent, plane, side, raise, twist: 0, react: waver ? 1 : reacts, seed: index * 1.7 + 0.4,
    lift: new Float32Array(n), sweep: new Float32Array(n), drive: [0, 0],
    pos: new Float32Array(n * 3), rot: new Float32Array(n * 4),
  };
  if (waver) {
    // Which way round to turn the raised arm so its suckers face you (+z): look at the suckers
    // halfway along, in the raised pose.
    const pos = mesh.geometry.getAttribute('position');
    const uv = mesh.geometry.getAttribute('uv');
    const along = mesh.geometry.getAttribute('uv1');
    const k = Math.round((n - 1) * 0.45);
    const dir = new Vector3();
    for (let i = 0; i < pos.count; i++) {
      const a = along.getX(i) * (n - 1);
      if (uv.getY(i) <= 0.876 || Math.abs(a - k) > 2) continue;
      dir.add(_v.set(pos.getX(i), pos.getY(i), pos.getZ(i)).sub(rest[k] as Vector3));
    }
    dir.addScaledVector(tangent[k] as Vector3, -dir.dot(tangent[k] as Vector3)).normalize();
    bendArm(arm, (j) => arm.raise[j] as number, () => 0, () => 0);
    const q = new Quaternion().fromArray(arm.rot, k * 4);
    const d = dir.applyQuaternion(q);
    const t = (tangent[k] as Vector3).clone().applyQuaternion(q);
    const toYou = new Vector3(0, 0, 1).addScaledVector(t, -t.z).normalize();
    arm.twist = Math.atan2(_v.crossVectors(d, toYou).dot(t), d.dot(toYou));
  }
  bendArm(arm, () => 0, () => 0, () => 0);
  const mat = (mesh.material as MeshStandardMaterial).clone();
  hallow(mat, {
    key: 'keeper-arm',
    glow: 0.3,
    uniforms: { uRest: { value: new Float32Array(rest.flatMap((p) => [p.x, p.y, p.z])) }, uPos: { value: arm.pos }, uRot: { value: arm.rot } },
    vertexPars: ARM_VERTEX_PARS,
    vertex: [
      ['#include <beginnormal_vertex>', ARM_NORMAL],
      ['#include <begin_vertex>', ARM_VERTEX],
    ],
  });
  mat.defines = { ...(mat.defines ?? {}), USE_UV1: '' };
  mesh.material = mat;
  // Raised, the arm reaches far outside its resting bounds.
  mesh.frustumCulled = false;
  return arm;
}

export async function build(ctx: ChapterContext): Promise<Chapter> {
  const { tier } = ctx;
  const rnd = rng(77);
  const scene = new Scene();
  const bounds: Bounds = [-40, -85, 80, 100];

  const path = new Path(
    [
      [0, 8],
      [0, -6],
      [2.5, -18],
      [-1.5, -31],
      [1, -42],
      [0, -49],
    ],
    3.4,
  );
  const terrain = new Terrain(bounds, aroundPath(path, { profile: (s) => -0.055 * Math.min(s, 44) + 0.18 * Math.sin(s / 6), bank: 0.05, rough: 0.5, seed: 7 }));

  const mask = new GroundMask(bounds, 4);
  mask.stroke(path.points.filter((_, i) => i % 4 === 0).map((p) => [p.x, p.y]), 3.6, 'r', 0.95);
  mask.blob(KEEPER.x, KEEPER.z + 6, 9, 'r', 0.9);
  mask.soften(3);
  const floor = ground({ mask, a: ctx.surface('gravel'), aScale: 1.4, b: ctx.surface('leaves'), bScale: 2.2, tone: 0.9 });
  scene.add(floor);
  scene.add(ledBeds(path, 1.75, 3.8));
  scene.add(caustics(bounds));

  // Dark trees (seaweed-dark against the blue), hung with jellyfish.
  // Clearings for the Kraken's Wreck and the treasure, so nothing stands between them and the path.
  const treeAt = lineThePath(path.points, 5, { spacing: 4.5, depth: 2, seed: 31 }).filter(
    (t) => Math.hypot(t.x - WRECK.x, t.z - WRECK.z) > 8 && Math.hypot(t.x - TREASURE.x, t.z - TREASURE.z) > 6.5,
  );
  const woods = forest(
    [
      { species: 'tall', at: treeAt.filter((_, i) => i % 2 === 0) },
      { species: 'young', at: treeAt.filter((_, i) => i % 2 === 1) },
    ],
    { leafTint: new Color(0.25, 0.32, 0.5), bark: new Color(0.03, 0.04, 0.07) },
  );
  scene.add(woods.group);
  const canopy = woodland(path, {
    canopy: [6.2, 10], reach: 10, skyGap: 0.3, density: tier === 'low' ? 1.3 : 2.2, wallFrom: 4.2, wallTo: 13, wallHeight: 5, wallDensity: tier === 'low' ? 3 : 4,
    tint: new Color(0.22, 0.3, 0.55), seed: 51,
    clear: (x, z, y) =>
      (Math.hypot(x - KEEPER.x, z - KEEPER.z) < 9 && y < 8) ||
      (Math.hypot(x - WRECK.x, z - WRECK.z) < 7.5 && y < 8.5) ||
      (Math.hypot(x - TREASURE.x, z - TREASURE.z) < 5 && y < 5),
  });
  scene.add(canopy.mesh);
  scene.add(treeLine({ radius: 110, height: 16, color: new Color(0.004, 0.012, 0.04), under: new Color(0.01, 0.03, 0.12) }));

  // Jellyfish: glowing pumpkin bells with trailing ribbons.
  const specs: PumpkinSpec[] = [];
  const ribbons: { p: Vector3; len: number; phase: number }[] = [];
  const jellies: number[] = [];
  const tmp = new Vector2();
  const tan = new Vector2();
  const count = tier === 'low' ? 70 : tier === 'mid' ? 150 : 200;
  for (let i = 0; i < count; i++) {
    const s = 2 + rnd() * (path.length - 4);
    path.at(s, tmp, tan);
    const off = (rnd() - 0.5) * 2 * (rnd() < 0.6 ? 3.5 : 8);
    const pos = new Vector3(tmp.x - tan.y * off, 2.6 + rnd() * 3.8, tmp.y + tan.x * off);
    if (Math.hypot(pos.x - WRECK.x, pos.z - WRECK.z) < 6.5) continue;
    // Over the path they float high, so their ribbons end above your head, not in your face.
    const overPath = Math.abs(off) < 2.6;
    if (overPath) pos.y = Math.max(pos.y, 4.2);
    const r = 0.16 + rnd() * 0.12;
    // Never one jellyfish inside another.
    if (!clearOf(specs, { position: pos, size: new Vector3(r, r * 0.56, r), anchor: 'centre' }, 0.05)) continue;
    const purple = rnd() < 0.5;
    jellies.push(specs.length);
    specs.push({
      position: pos,
      // A bell, wider than it is tall, held by its middle (its ribbons hang from under it).
      size: new Vector3(r, r * 0.56, r),
      anchor: 'centre',
      yaw: rnd() * 6,
      carve: -3,
      skin: purple ? new Color(0.35, 0.12, 0.55) : new Color(0.9, 0.42, 0.08),
      glow: new Color(1, 0.5, 0.15).multiplyScalar(2.6),
      phase: rnd(),
      hang: 9 - pos.y,
    });
    const len = Math.min(1.1 + rnd() * 1.6, overPath ? (pos.y - 2.4) / 1.1 : 99);
    for (let k = 0; k < (tier === 'low' ? 4 : 7); k++) {
      const a = (k / 8) * Math.PI * 2;
      ribbons.push({ p: pos.clone().add(new Vector3(Math.cos(a) * r * 0.7, -r * 0.45, Math.sin(a) * r * 0.7)), len: len * (0.6 + rnd() * 0.5), phase: rnd() });
    }
  }
  // Pufferfish (lime, spotted) peering from the branches.
  const puffers: number[] = [];
  for (let i = 0; i < (tier === 'low' ? 14 : 36); i++) {
    const s = 3 + rnd() * (path.length - 6);
    path.at(s, tmp, tan);
    const off = (rnd() < 0.5 ? -1 : 1) * (2.6 + rnd() * 2.5);
    puffers.push(specs.length);
    specs.push({
      position: new Vector3(tmp.x - tan.y * off, 1.8 + rnd() * 2.2, tmp.y + tan.x * off),
      size: new Vector3(0.24, 0.22, 0.24),
      yaw: Math.atan2(tmp.x - (tmp.x - tan.y * off), tmp.y - (tmp.y + tan.x * off)),
      carve: 100 + (CARVE.stars[1] as number),
      skin: new Color(0.35, 0.85, 0.15),
      glow: new Color(0.05, 0.2, 0.05),
      phase: rnd(),
      hang: 2,
    });
  }
  // Modelled pufferfish replace the painted-pumpkin stand-ins when we have them.
  const pufferModel = await loadModel('pufferfish', { glowReceive: 0.6, shell: true });
  const pufferObjects: Object3D[] = [];
  if (pufferModel) {
    for (const i of puffers) {
      const s = specs[i] as PumpkinSpec;
      const o = pufferModel.root.clone(true);
      o.position.copy(s.position);
      o.rotation.y = s.yaw;
      o.scale.setScalar(0.9 + Math.random() * 0.5);
      o.userData.base = o.scale.x;
      scene.add(o);
      pufferObjects.push(o);
      s.size.set(0.001, 0.001, 0.001);
    }
    for (const m of pufferModel.glows.values()) m.emissiveIntensity = 1.6;
  }
  const pumpkins = new PumpkinField(specs, ctx.atlas, { detail: [28, 12], simple: [14, 7] });
  scene.add(pumpkins.group);
  const ribbonMesh = streamers(ribbons);
  scene.add(ribbonMesh);

  // Coral boards along the beds.
  const coralColors = [new Color(1, 0.45, 0.1), new Color(1, 0.25, 0.55), new Color(0.75, 1, 0.2), new Color(1, 0.8, 0.2)];
  const corals: Mesh[] = [];
  const coralModels = (await Promise.all(['coral-1', 'coral-2', 'coral-3'].map((n) => loadModel(n, { glowReceive: 0.5 })))).filter(Boolean);
  for (let i = 0; i < (tier === 'low' ? 34 : 80); i++) {
    const s = rnd() * path.length;
    path.at(s, tmp, tan);
    const off = (rnd() < 0.5 ? -1 : 1) * (2.2 + rnd() * 1.6);
    if (Math.hypot(tmp.x - tan.y * off - WRECK.x, tmp.y + tan.x * off - WRECK.z) < 6 || Math.hypot(tmp.x - tan.y * off - TREASURE.x, tmp.y + tan.x * off - TREASURE.z) < 4.5) continue;
    const cm = coralModels[i % Math.max(1, coralModels.length)];
    if (cm && rnd() < 0.6) {
      const o = cm.root.clone(true);
      o.position.set(tmp.x - tan.y * off, 0, tmp.y + tan.x * off);
      o.rotation.y = Math.atan2(-tan.y * -off, tan.x * -off) + (rnd() - 0.5) * 0.8;
      o.scale.setScalar(1.0 + rnd() * 1.2);
      scene.add(o);
      continue;
    }
    const c = coral(1.0 + rnd() * 1.1, (coralColors[i % coralColors.length] as Color).clone().multiplyScalar(1.6), i + 3);
    c.position.set(tmp.x - tan.y * off, 0, tmp.y + tan.x * off);
    c.rotation.y = Math.atan2(-tan.y * -off, tan.x * -off) + (rnd() - 0.5) * 0.8;
    scene.add(c);
    corals.push(c);
  }

  // Giant neon clam shells in the beds, as in the photo.
  for (let k = 0; k < 3; k++) {
    const sh = new Shape();
    const R = 1.0 + k * 0.15;
    sh.moveTo(-R, 0);
    for (let a = 0; a <= 12; a++) {
      const t = Math.PI - (a / 12) * Math.PI;
      const rr = R * (0.92 + 0.08 * Math.cos(a * Math.PI));
      sh.lineTo(Math.cos(t) * rr, Math.sin(t) * rr * 1.1);
    }
    sh.lineTo(R, 0);
    const geo = new ExtrudeGeometry(sh, { depth: 0.08, bevelEnabled: true, bevelSize: 0.03, bevelThickness: 0.03, curveSegments: 4 });
    const clam = new Mesh(geo, hallow(new MeshBasicGlow({ color: new Color(1, 0.3, 0.6).multiplyScalar(1.4) }), { key: 'clam' }));
    const s0 = path.length * (0.3 + k * 0.25);
    path.at(s0, tmp, tan);
    const side = k % 2 ? 1 : -1;
    clam.position.set(tmp.x - tan.y * 3.4 * side, 0, tmp.y + tan.x * 3.4 * side);
    clam.rotation.y = Math.atan2(-tan.y * -side, tan.x * -side) + 0.4 * side;
    clam.rotation.x = -0.25;
    scene.add(clam);
    corals.push(clam);
  }

  // The Kraken's Wreck, and the treasure further on.
  const wreck = await kraken(ctx, WRECK, Math.PI / 2, TREASURE, -Math.PI / 2);
  scene.add(...wreck.objects);

  // The Keeper of the Deep.
  const keeper = await loadModel('octopus', { glowReceive: 0.3, shell: true });
  let keeperRoot: Object3D | null = null;
  const arms: Arm[] = [];
  let eyes: Object3D[] = [];
  let keeperBox = new Box3();
  if (keeper) {
    keeperRoot = keeper.root;
    const box = new Box3().setFromObject(keeperRoot);
    const h = box.max.y - box.min.y;
    if (Math.abs(h - 6.5) / 6.5 > 0.1) keeperRoot.scale.multiplyScalar(6.5 / h);
    keeperRoot.position.copy(KEEPER);
    scene.add(keeperRoot);
    for (const m of keeper.glows.values()) m.emissiveIntensity = m.name === 'glow_eyes' ? 6 : 1.4;
    eyes = ['eye_L', 'eye_R'].map((n) => keeper.node(n)).filter(Boolean) as Object3D[];
    keeperRoot.traverse((o) => {
      const mesh = o as Mesh;
      if (!mesh.isMesh || !o.name.startsWith('tentacle')) return;
      const i = Number(o.name.split('_')[1] ?? 0);
      // It waves with the arm on its left (your right), out to the side; the arms beside it stir.
      arms.push(makeArm(mesh, i, i === 2, i === 0 || i === 4 ? 0.35 : 0.15));
    });
    keeperBox = new Box3().setFromObject(keeperRoot);
    keeperRoot.position.y = -7;
  }

  // Waves of light: translucent blue sheets of fabric strung with tiny lights around the Keeper.
  const sheetMat = new ShaderMaterial({
    uniforms: { ...shared, uBright: { value: 0.3 } },
    vertexShader: /* glsl */ `
      uniform float uHlTime;
      varying vec2 vUv;
      varying vec3 vHlWorld;
      ${VERTEX_TERRAIN}
      void main() {
        vUv = uv;
        vec3 p = position;
        p.z += sin(p.x * 1.3 + uHlTime * 0.8) * 0.35 + sin(p.y * 2.0 + uHlTime * 0.6) * 0.15;
        vHlWorld = (modelMatrix * vec4(p, 1.0)).xyz;
        vHlWorld.y += hlTerrain(vHlWorld.xz);
        gl_Position = projectionMatrix * viewMatrix * vec4(vHlWorld, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      ${SHADER_PARS}
      uniform float uBright;
      varying vec2 vUv;
      varying vec3 vHlWorld;
      void main() {
        float folds = 0.55 + 0.45 * sin(vUv.x * 40.0 + sin(vUv.y * 6.0) * 2.0);
        vec3 col = vec3(0.12, 0.3, 1.0) * folds * 0.35 * uBright;
        vec2 g = vUv * vec2(60.0, 18.0);
        vec2 cell = floor(g);
        float led = smoothstep(0.18, 0.0, length(fract(g) - 0.5 - (hlHash22(cell) - 0.5) * 0.5)) * step(0.55, hlHash12(cell));
        float tw = 0.5 + 0.5 * sin(uHlTime * 2.0 + hlHash12(cell + 2.0) * 30.0);
        col += vec3(0.4, 0.65, 1.0) * led * tw * 4.0 * uBright;
        float edge = smoothstep(0.0, 0.15, vUv.y) * smoothstep(1.0, 0.7, vUv.y);
        gl_FragColor = vec4(col * edge, 1.0);
      }`,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
    side: DoubleSide,
  });
  const sheets: Mesh[] = [];
  for (let i = 0; i < 6; i++) {
    const geo = new PlaneGeometry(7, 2.6, 30, 8);
    // Curl each into a wave crest.
    const pos = geo.getAttribute('position') as BufferAttribute;
    for (let k = 0; k < pos.count; k++) {
      const x = pos.getX(k);
      const y = pos.getY(k) + 1.3;
      pos.setXYZ(k, x, y, Math.pow(y / 2.6, 2) * 1.4);
    }
    geo.computeVertexNormals();
    const sheet = new Mesh(geo, sheetMat);
    const a = -1.2 + i * 0.48;
    sheet.position.set(KEEPER.x + Math.sin(a) * 5, 0, KEEPER.z + Math.cos(a) * 4.2 + 1);
    sheet.rotation.y = a + Math.PI;
    sheet.renderOrder = 6;
    scene.add(sheet);
    sheets.push(sheet);
  }

  const bubbles = new Drift({ count: tier === 'low' ? 900 : 2200, box: 18, size: 0.07, color: new Color(0.5, 0.7, 1), style: 'bubble', opacity: 0.8 });
  bubbles.velocity.set(0.05, 0.55, 0);
  scene.add(bubbles.points);
  // Blue light pouring down through the water in slow, swaying shafts.
  const beams = tier === 'low' ? null : new Beams({ count: 14, box: 30, height: 16, color: new Color(0.12, 0.3, 0.75).multiplyScalar(0.34) });
  if (beams) scene.add(beams.mesh);

  const glowLights: GlowLight[] = [...pumpkins.glowLights(2.2, tier === 'low' ? 0.08 : 0.05), ...wreck.glow];
  for (let s = 0; s <= path.length; s += 1.2) {
    path.at(s, tmp, tan);
    for (const side of [-1, 1]) glowLights.push({ x: tmp.x - tan.y * 2.7 * side, z: tmp.y + tan.x * 2.7 * side, y: 0.05, radius: 2.2, color: new Color(0.15, 0.3, 1), intensity: 0.22, flicker: 0 });
  }
  for (const c of corals) glowLights.push({ x: c.position.x, z: c.position.z, radius: 1.2, color: (c.material as MeshBasicGlow).color, intensity: 0.08, flicker: 0 });
  glowLights.push({ x: KEEPER.x, z: KEEPER.z + 2, y: 3, radius: 9, color: new Color(0.35, 0.2, 1), intensity: 0.5, flicker: 0 });
  const sources: LightSource[] = [
    ...wreck.sources,
    { position: KEEPER.clone().add(new Vector3(0, 1, 4)), color: new Color(0.45, 0.3, 1), intensity: 10, distance: 16 },
    ...specs.filter((_, i) => jellies.includes(i)).slice(0, 60).map((s) => ({ position: s.position, color: new Color(1, 0.5, 0.2), intensity: 0.7, distance: 4 })),
  ];
  scene.add(new HemisphereLight(0x1c3cff, 0x02040c, 0.35));

  const sea = skyState({ zenith: new Color(0.0, 0.01, 0.05), horizon: new Color(0.0, 0.04, 0.14), stars: 0 });
  const grade: Grade = { ...defaultGrade(), exposure: 1.2, bloom: 0.13, saturation: 1.28, power: 1.14, tint: new Color(0.85, 0.95, 1.15), lift: new Color(0.0, 0.006, 0.03) };

  let time = 0;
  let risen = 0;
  let rising = false;
  // The wave (times on the chapter's clock): the arm rises, sweeps from side to side, and lowers.
  const SWEEP_PERIOD = 2.6;
  let waveFrom = -1e9;
  let sweepFrom = -1e9;
  let sweepUntil = -1e9;
  let liftUntil = -1e9;
  let sweepPhase = 0;
  let hinted = 0;
  let wavedBack = false;
  let keeperDistance = Infinity;
  /** When the wave last finished (the arm settled), on the chapter's clock. */
  let stillSince = -1;
  const puffed = new Map<number, number>();

  const chapter: Chapter = {
    scene,
    path,
    terrain,
    music: 'deep',
    ambience: 'deep',
    steps: 'step-sand',
    // The sea's own tiny lights, breathing blue-green, brighter as you pass.
    glimmers: {
      count: 380,
      box: 22,
      height: [0.2, 6],
      colors: [new Color(0.25, 0.85, 1).multiplyScalar(1.6), new Color(0.4, 1, 0.7).multiplyScalar(1.3), new Color(0.55, 0.5, 1).multiplyScalar(1.4)],
      size: 0.022,
      style: 'plankton',
      drift: [0.04, 0.01, 0.02],
    },

    enter() {
      ctx.glow.setBounds(...bounds);
      ctx.glow.setLights(glowLights);
      ctx.glow.wave = 1e9;
      ctx.lights.sources = sources;
      lerpSky(ctx.sky.state, sea, sea, 0);
      lerpGrade(ctx.post.grade, grade, grade, 0);
      shared.uFogColor.value.set(0.004, 0.03, 0.11);
      shared.uFogDensity.value = 0.05;
      shared.uFogHeight.value = 30;
      shared.uFogGlow.value = 0.6;
      ctx.audio.setUnderwater(1);
      ctx.ember.presence = 1;
      ctx.ember.place(new Vector3(0, 1.8, 5));
      ctx.audio.preload('marigold', ['bubble', 'puffer-puff', 'octopus-wave', 'step-sand']);
      setTimeout(() => ctx.ui.say('Everything sounds far away down here.', 5), 4000);
    },

    update(dt) {
      time += dt;
      const w = ctx.walker;
      const e = ctx.ember;
      const scale = ctx.renderer.domElement.height / (2 * Math.tan((ctx.camera.fov * Math.PI) / 360));
      bubbles.update(dt, scale);
      wreck.update(dt, time);
      const stick = ctx.portal.input.stick('move');
      if (w.seated && Math.hypot(stick.x, stick.y) > 0.3) w.seated = false;
      // Jellies pulse, brighter when you pass beneath.
      for (const i of jellies) {
        const s = specs[i] as PumpkinSpec;
        const pulse = Math.sin(time * 1.6 + (s.phase ?? 0) * 6.28);
        pumpkins.pose(i, 1, Math.sin(time * 0.5 + (s.phase ?? 0) * 6) * 0.15, 1 + pulse * 0.08);
        const d = Math.hypot(s.position.x - w.position.x, s.position.z - w.position.z);
        pumpkins.setLevel(i, 1 + Math.max(0, 1 - d / 3) * 1.2);
      }
      for (const [i, t] of puffed) {
        const k = t + dt;
        const big = k < 0.25 ? k / 0.25 : Math.max(0, 1 - (k - 1.5) / 0.6);
        const fish = pufferObjects[puffers.indexOf(i)];
        if (fish) fish.scale.setScalar((fish.userData.base as number) * (1 + big * 0.55));
        else pumpkins.pose(i, 1 + big * 0.45);
        if (k > 2.2) {
          puffed.delete(i);
          if (!fish) pumpkins.pose(i, 1);
        } else puffed.set(i, k);
      }
      // The Keeper rises as you come near.
      if (keeperRoot) {
        const d = Math.hypot(w.position.x - KEEPER.x, w.position.z - KEEPER.z);
        keeperDistance = d;
        if (!rising && d < KEEPER_NEAR) {
          rising = true;
          void ctx.audio.sfx('keeper-rise', { volume: 1 });
          ctx.ui.say('Something enormous is rising…', 5);
        }
        if (rising) risen = Math.min(1, risen + dt / 7);
        const k = risen * risen * (3 - 2 * risen);
        keeperRoot.position.y = -7 * (1 - k) + Math.sin(time * 0.6) * 0.08 * k;
        sheetMat.uniforms.uBright!.value = 0.3 + 0.9 * k;
        // Its eyes follow you.
        for (const eye of eyes) {
          const local = eye.parent ? eye.parent.worldToLocal(ctx.camera.position.clone()) : ctx.camera.position.clone();
          const dir = local.sub(eye.position).normalize();
          eye.rotation.y += (Math.atan2(dir.x, dir.z) * 0.5 - eye.rotation.y) * (1 - Math.exp(-dt * 2));
          eye.rotation.x += (-Math.asin(Math.max(-1, Math.min(1, dir.y))) * 0.4 - eye.rotation.x) * (1 - Math.exp(-dt * 2));
        }
        moveArms(dt);
        if (k > 0.9 && !hinted && d < KEEPER_NEAR) {
          hinted = time;
          ctx.ui.say('Wave to it.', 4);
        }
        // If you don't, it waves first.
        if (hinted && !wavedBack && time - hinted > 10) wave('It waves at you.');
      }
      // The Ember swims ahead, then hovers by the Keeper.
      path.at(Math.min(path.length, w.s + 4), tmp);
      if (risen > 0.6) e.target.copy(KEEPER).add(new Vector3(1.8, 4.2, 2));
      else e.target.set(tmp.x, 2 + Math.sin(time * 0.9) * 0.3, tmp.y);
      ctx.glow.moving.length = 0;
      ctx.glow.moving.push(e.glow);
      pumpkins.update(ctx.camera, dt);
    },

    pick(ray: Ray): TapAction | null {
      const wreckTap = wreck.pick(ray);
      if (wreckTap) return wreckTap;
      if (keeperRoot && risen > 0.5 && ray.intersectsBox(onGround(keeperBox.clone().translate(new Vector3(0, keeperRoot.position.y, 0)))))
        return () => wave('It waves back.');
      for (let k = 0; k < pufferObjects.length; k++) {
        const fish = pufferObjects[k] as Object3D;
        if (ray.distanceSqToPoint(pointOnGround(fish.position)) < 0.18) {
          const i = puffers[k] as number;
          return () => {
            puffed.set(i, 0);
            void ctx.audio.sfx('puffer-puff', { at: pointOnGround(fish.position), volume: 0.8 });
          };
        }
      }
      const i = pumpkins.pick(ray, 18);
      if (i >= 0 && puffers.includes(i))
        return () => {
          puffed.set(i, 0);
          void ctx.audio.sfx('puffer-puff', { at: (specs[i] as PumpkinSpec).position, volume: 0.8 });
        };
      if (i >= 0)
        return () => {
          pumpkins.flare(i);
          void ctx.audio.sfx('bubble', { at: (specs[i] as PumpkinSpec).position, volume: 0.7 });
        };
      return null;
    },

    finished() {
      // (no Keeper, if its model couldn't be loaded: the path's end, as everywhere else)
      if (!keeperRoot) return ctx.walker.s > path.length - 1.2;
      // Once it has risen and waved (and a breath after the arm settles), from the path's end or anywhere near it.
      if (!wavedBack || risen < 1 || waveGoing()) {
        stillSince = -1;
        return false;
      }
      if (stillSince < 0) stillSince = time;
      return time - stillSince > 1.5 && (ctx.walker.s > path.length - 1.2 || keeperDistance < KEEPER_NEAR);
    },

    dispose() {
      beams?.dispose();
      wreck.dispose();
      terrain.dispose();
      ctx.audio.setUnderwater(0);
      pumpkins.dispose();
      woods.dispose();
      canopy.dispose();
      bubbles.dispose();
      floor.geometry.dispose();
      ribbonMesh.geometry.dispose();
      for (const c of corals) c.geometry.dispose();
    },
  };
  if (import.meta.env.DEV) (window as unknown as { deep: unknown }).deep = { rise: () => (risen = 1, rising = true), wave: () => wave('It waves back.') };

  function wave(line: string) {
    wavedBack = true;
    if (time < sweepUntil) {
      // Waving already: a little longer.
      sweepUntil = Math.max(sweepUntil, time + SWEEP_PERIOD * 1.5);
    } else {
      // From rest, or from wherever it had got to on the way down.
      const up = arms.find((a) => a.react === 1)?.lift[ARM_JOINTS >> 1] ?? 0;
      waveFrom = time;
      sweepFrom = time + 1.8 * (1 - up * 0.6);
      sweepUntil = sweepFrom + SWEEP_PERIOD * 2;
      if ((arms.find((a) => a.react === 1)?.drive[1] ?? 0) < 0.02) sweepPhase = 0;
    }
    liftUntil = sweepUntil + 0.7;
    void ctx.audio.sfx('octopus-wave', { at: KEEPER.clone().add(new Vector3(0, 3, 0)), volume: 1 });
    ctx.ui.say(line, 4);
  }

  /** Still waving, or the arm not yet settled back down. */
  function waveGoing() {
    return time < liftUntil || arms.some((a) => (a.lift[ARM_JOINTS - 1] as number) > 0.03 || (a.sweep[ARM_JOINTS - 1] as number) > 0.03);
  }

  /**
   * The Keeper's arms, every frame: a slow drift as the water moves them, and the wave. The lift
   * runs from the root to the tip (each joint following the one before), so the arm peels up off
   * the floor in a curl that travels out along it and later lays itself down the same way; the
   * sweeps travel out along it too, the tip following through, curling and uncurling.
   */
  function moveArms(dt: number) {
    const n = ARM_JOINTS;
    const sweeping = time > sweepFrom && time < sweepUntil;
    if (sweeping || arms.some((a) => a.drive[1] > 1e-3)) sweepPhase += (dt * Math.PI * 2) / SWEEP_PERIOD;
    for (const arm of arms) {
      const waver = arm.react === 1;
      // The others stir a beat later.
      const lifting = time < liftUntil && time > waveFrom + (waver ? 0 : 0.6);
      const swaying = sweeping && time > sweepFrom + (waver ? 0 : 0.5);
      // Up gently; down more gently still.
      const rise = lifting ? 0.7 : 0.9;
      const step = lifting ? 0.06 : 0.075;
      ease(arm.lift, arm.drive, 0, lifting ? 1 : 0, rise, step, dt);
      ease(arm.sweep, arm.drive, 1, swaying ? 1 : 0, 0.55, 0.02, dt);
      const s = arm.seed;
      bendArm(
        arm,
        (k) => {
          const a = k / (n - 1);
          // Drifting: the outer arm lifts a touch and settles, over and over.
          let b = 0.5 * DEG * (0.5 + 0.5 * Math.sin(time * 0.4 + s * 1.3 - a * 1.6)) * smooth(0.3, 0.8, a);
          b += (arm.raise[k] as number) * (arm.lift[k] as number);
          const e = arm.sweep[k] as number;
          if (waver) {
            // The sweeps, from the elbow out (more outward than in, to keep clear of its face), and
            // the tip curling and uncurling through them.
            b += e * 3.1 * DEG * (Math.sin(sweepPhase - a * 1.7) - 0.45) * smooth(0.08, 0.35, a) * (1 - 0.35 * smooth(0.7, 1, a));
            b += e * 10 * DEG * Math.sin(sweepPhase - a * 1.7 - 1.2) * smooth(0.66, 0.85, a);
          } else b += e * arm.react * 4 * DEG * Math.sin(sweepPhase * 0.5 + s - a * 1.5) * smooth(0.35, 0.9, a);
          return b;
        },
        (k) => {
          const a = k / (n - 1);
          let b = 0.6 * DEG * Math.sin(time * 0.55 + s - a * 2) * smooth(0.05, 0.5, a);
          if (waver) b += (arm.sweep[k] as number) * 0.9 * DEG * Math.cos(sweepPhase - a * 1.7) * smooth(0.1, 0.4, a);
          return b;
        },
        (k) => arm.twist * (arm.lift[k] as number) * smooth(0.08, 0.45, k / (n - 1)),
      );
    }
  }

  /**
   * Eases a front along a chain: the root's drive (`drive[slot]`) toward the target, the root
   * toward its drive, and every joint toward the one before it, each with its own lag.
   */
  function ease(chain: Float32Array, drive: [number, number], slot: 0 | 1, target: number, root: number, step: number, dt: number) {
    const kr = 1 - Math.exp(-dt / root);
    const ks = 1 - Math.exp(-dt / step);
    drive[slot] += (target - drive[slot]) * kr;
    chain[0] = (chain[0] as number) + (drive[slot] - (chain[0] as number)) * kr;
    for (let k = 1; k < chain.length; k++) chain[k] = (chain[k] as number) + ((chain[k - 1] as number) - (chain[k] as number)) * ks;
  }

  return chapter;
}
