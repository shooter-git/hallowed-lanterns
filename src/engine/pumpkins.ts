import {
  BufferAttribute,
  BufferGeometry,
  type Camera,
  Color,
  CylinderGeometry,
  DynamicDrawUsage,
  Float32BufferAttribute,
  Group,
  InstancedBufferAttribute,
  InstancedMesh,
  LineBasicMaterial,
  LineSegments,
  Matrix4,
  MeshStandardMaterial,
  Quaternion,
  type Ray,
  type Texture,
  Vector3,
} from 'three';
import type { GlowLight } from './glowfield.ts';
import { hallow } from './shared.ts';
import { heightAt } from './terrain.ts';

/** One pumpkin (or pumpkin lantern) in a field of them. */
export interface PumpkinSpec {
  /** Centre of the pumpkin. */
  position: Vector3;
  /** Half-width, half-height, half-depth (m). A typical carving pumpkin is ~0.16 × 0.19 × 0.16. */
  size: Vector3;
  /** Which way the carving faces (radians about +y; 0 faces +z). */
  yaw: number;
  /** Small lean (radians), for life. */
  tilt?: number;
  /**
   * Carving atlas cell; or 100 + a cell for a design painted on (in the `glow` colour, no candle);
   * -1 plain, -2 a green-striped carnival squash, -3 a glowing translucent shell, -4 beach-ball
   * paint, -5 a lollipop swirl.
   */
  carve: number;
  skin: Color;
  /** Candle colour × brightness (linear). Black for an unlit pumpkin. */
  glow: Color;
  phase?: number;
  /** Order in the lighting wave (see `PumpkinField.wave`). */
  seq?: number;
  /** Hangs from a string this long above its top (m). */
  hang?: number;
  /** Chunk key: pumpkins with the same key are drawn (and culled) together. */
  chunk?: string;
}

const RIBS = 10;

/** The pumpkin's surface, unit-sized: equator radius 1, height about 1.3 (−0.65 … 0.65). */
function shape(theta: number, phi: number, out: Vector3) {
  const s = Math.sin(phi);
  const c = Math.cos(phi);
  const lobe = Math.abs(Math.cos((RIBS * theta) / 2));
  const groove = (1 - lobe) ** 1.7 * s ** 0.7;
  const r = s * (1 - 0.13 * groove) * (1 + 0.05 * s * s);
  let y = c * 0.82;
  const top = Math.exp(-((phi / 0.42) ** 2));
  const bottom = Math.exp(-(((Math.PI - phi) / 0.45) ** 2));
  y -= top * 0.24;
  y += bottom * 0.2;
  out.set(r * Math.cos(theta), y, r * Math.sin(theta));
  return groove;
}

/** A ribbed pumpkin with seamless normals (computed from the surface, not the triangles). */
export function pumpkinGeometry(lon: number, lat: number): BufferGeometry {
  const pos: number[] = [];
  const nor: number[] = [];
  const uv: number[] = [];
  const rib: number[] = [];
  const p = new Vector3();
  const a = new Vector3();
  const b = new Vector3();
  const n = new Vector3();
  const e = 1e-3;
  for (let j = 0; j <= lat; j++) {
    const phi = Math.min(Math.PI - 0.002, Math.max(0.002, (j / lat) * Math.PI));
    for (let i = 0; i <= lon; i++) {
      const theta = (i / lon) * Math.PI * 2;
      const g = shape(theta, phi, p);
      shape(theta + e, phi, a);
      shape(theta, phi + e, b);
      a.sub(p);
      b.sub(p);
      n.crossVectors(b, a).normalize();
      if (j === 0) n.set(0, 1, 0);
      if (j === lat) n.set(0, -1, 0);
      pos.push(p.x, p.y, p.z);
      nor.push(n.x, n.y, n.z);
      uv.push(i / lon, 1 - j / lat);
      rib.push(g);
    }
  }
  const index: number[] = [];
  for (let j = 0; j < lat; j++) {
    for (let i = 0; i < lon; i++) {
      const v0 = j * (lon + 1) + i;
      const v1 = v0 + 1;
      const v2 = v0 + lon + 1;
      const v3 = v2 + 1;
      if (j > 0) index.push(v0, v1, v2);
      if (j < lat - 1) index.push(v1, v3, v2);
    }
  }
  const geo = new BufferGeometry();
  geo.setIndex(index);
  geo.setAttribute('position', new Float32BufferAttribute(pos, 3));
  geo.setAttribute('normal', new Float32BufferAttribute(nor, 3));
  geo.setAttribute('uv', new Float32BufferAttribute(uv, 2));
  geo.setAttribute('aRib', new Float32BufferAttribute(rib, 1));
  return geo;
}

/** A short, ridged, slightly curved stem sitting in the top dimple. */
function stemGeometry(): BufferGeometry {
  const g = new CylinderGeometry(0.07, 0.11, 0.32, 7, 4, false);
  const p = g.getAttribute('position') as BufferAttribute;
  const v = new Vector3();
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i);
    const t = (v.y + 0.16) / 0.32;
    const twist = t * 0.6;
    const x = v.x * Math.cos(twist) - v.z * Math.sin(twist);
    const z = v.x * Math.sin(twist) + v.z * Math.cos(twist);
    p.setXYZ(i, x + t * t * 0.08, v.y + 0.16 + 0.5, z);
  }
  g.computeVertexNormals();
  return g;
}

const PUMPKIN_VERTEX_PARS = /* glsl */ `
attribute float aRib;
attribute float aCarve;
attribute vec3 aSkin;
attribute vec4 aGlow;   // rgb × brightness, phase
attribute vec2 aWave;   // seq, level
uniform float uWave;
uniform float uWaveSoft;
varying vec3 vLocal;
varying float vRib;
varying float vCarve;
varying vec3 vSkin;
varying vec3 vCandle;
varying vec3 vPaint;
`;

const PUMPKIN_VERTEX = /* glsl */ `
#include <begin_vertex>
vLocal = position;
vRib = aRib;
vCarve = aCarve;
vSkin = aSkin;
float hlOn = clamp((uWave - aWave.x) / uWaveSoft, 0.0, 1.0) * aWave.y;
// Painted pumpkins use their "glow" colour as the paint, and have no candle.
vPaint = aGlow.rgb;
vCandle = aCarve >= 100.0 ? vec3(0.0) : aGlow.rgb * hlOn * hlFlicker(uHlTime, aGlow.w);
`;

const PUMPKIN_FRAGMENT_PARS = /* glsl */ `
uniform sampler2D uAtlas;
varying vec3 vLocal;
varying float vRib;
varying float vCarve;
varying vec3 vSkin;
varying vec3 vCandle;
varying vec3 vPaint;
float hlHole;
float hlPaint;
float hlBand;
float hlHalo;
vec2 hlCuv;
`;

const PUMPKIN_COLOR = /* glsl */ `
#include <color_fragment>
{
  // Skin: deeper and a little greener in the grooves, mottled, with faint streaks along the ribs.
  float ang = atan(vLocal.z, vLocal.x);
  float mott = hlFbmT(vLocal.xy * 9.0 + vLocal.z * 5.0);
  float streak = hlNoise(vec2(ang * 28.0, vLocal.y * 2.0));
  vec3 skin = vSkin * (0.82 + 0.3 * mott) * (0.92 + 0.12 * streak);
  skin = mix(skin, skin * vec3(0.42, 0.3, 0.16), clamp(vRib * 1.5, 0.0, 1.0));
  // Scarred, pale patch underneath where it sat on the ground.
  skin = mix(skin, vec3(0.55, 0.45, 0.25) * vSkin.r, smoothstep(-0.45, -0.62, vLocal.y) * 0.5);
  if (vCarve < -1.5 && vCarve > -2.5) {
    // Carnival squash: creamy skin, dark green stripes down the grooves, green flecks.
    vec3 cream = vSkin * (0.9 + 0.15 * mott);
    float stripe = smoothstep(0.08, 0.3, vRib + (streak - 0.5) * 0.15);
    float fleck = step(0.8, hlNoise(vLocal.xy * 40.0 + vLocal.z * 31.0)) * 0.6;
    skin = mix(cream, vec3(0.03, 0.12, 0.05), max(stripe, fleck));
  }
  if (vCarve < -3.5 && vCarve > -4.5) {
    // Beach-ball paint: bright segments around the ribs.
    float seg = floor((ang / 6.2831853 + 0.5) * 5.0);
    float h = fract(seg * 0.2 + vSkin.r * 3.7);
    skin = clamp(abs(fract(h + vec3(0.0, 0.667, 0.333)) * 6.0 - 3.0) - 1.0, 0.0, 1.0) * 0.8 + 0.03;
    skin *= 0.85 + 0.2 * mott;
  }
  if (vCarve < -4.5 && vCarve > -5.5) {
    // Lollipop swirl on the face.
    float sw = fract(atan(vLocal.y, vLocal.x) / 6.2831853 + length(vLocal.xy) * 1.6);
    vec3 rainbow = clamp(abs(fract(sw + vec3(0.0, 0.667, 0.333)) * 6.0 - 3.0) - 1.0, 0.0, 1.0) * 0.85 + 0.05;
    skin = mix(vec3(0.9), rainbow, smoothstep(0.05, 0.3, vLocal.z));
  }
  hlHole = 0.0; hlBand = 0.0; hlHalo = 0.0; hlCuv = vec2(0.5); hlPaint = 0.0;
  float cellIndex = vCarve >= 100.0 ? vCarve - 100.0 : vCarve;
  if (cellIndex >= 0.0) {
    hlCuv = vec2(vLocal.x * 0.62 + 0.5, vLocal.y * 0.62 + 0.5);
    vec2 cell = vec2(mod(cellIndex, 8.0), floor(cellIndex / 8.0 + 0.001));
    vec2 auv = (cell + clamp(vec2(hlCuv.x, 1.0 - hlCuv.y), 0.01, 0.99)) / 8.0;
    vec4 m = texture2D(uAtlas, vec2(auv.x, 1.0 - auv.y));
    float facing = smoothstep(0.12, 0.4, vLocal.z);
    if (vCarve >= 100.0) {
      // Painted on, not carved.
      hlPaint = smoothstep(0.42, 0.58, m.r) * facing;
    } else {
      hlHole = smoothstep(0.42, 0.58, m.r) * facing;
      hlBand = smoothstep(0.28, 0.55, m.g) * (1.0 - hlHole) * facing;
      hlHalo = m.b * facing;
    }
  }
  vec3 flesh = vec3(0.95, 0.78, 0.42);
  diffuseColor.rgb = mix(skin, flesh, hlBand * 0.85);
  diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.035, 0.02, 0.01), hlHole);
  diffuseColor.rgb = mix(diffuseColor.rgb, vPaint, hlPaint);
}
`;

const PUMPKIN_EMISSIVE = /* glsl */ `
#include <emissivemap_fragment>
{
  // Inside, seen through the cut: hottest low in the middle where the candle sits.
  float hot = 1.0 - 0.5 * smoothstep(0.0, 0.55, length((hlCuv - vec2(0.5, 0.38)) * vec2(1.0, 1.25)));
  totalEmissiveRadiance += vCandle * hot * hlHole;
  // The cut wall, lit by the candle.
  totalEmissiveRadiance += vCandle * vec3(1.0, 0.72, 0.4) * 0.3 * hlBand;
  // Light through the thin skin near the cuts, and faintly through the whole shell.
  totalEmissiveRadiance += vCandle * vSkin * (0.07 * hlHalo + 0.012);
  // A glowing shell (jellyfish bells): lit through, brightest underneath.
  if (vCarve < -2.5) totalEmissiveRadiance += vCandle * vSkin * (0.25 + 0.5 * smoothstep(0.3, -0.6, vLocal.y));
}
`;

interface Chunk {
  hi: InstancedMesh;
  lo: InstancedMesh;
  stem: InstancedMesh;
  center: Vector3;
  radius: number;
  /** Index in the field of each instance in this chunk. */
  members: number[];
  wave: InstancedBufferAttribute;
  carve: InstancedBufferAttribute;
}

/**
 * Hundreds of pumpkins in a few draw calls: instanced in spatial chunks (each culled on its
 * own), detailed near you and simpler far away. Carvings come from the atlas.
 */
export class PumpkinField {
  readonly group = new Group();
  /** Lanterns whose `seq` is below this are lit (fading in over `waveSoftness`). */
  wave = 1e9;
  waveSoftness = 2;
  /** Within this distance (m) a chunk uses the detailed pumpkin. */
  detailDistance = 14;

  private readonly chunks: Chunk[] = [];
  private readonly where: { chunk: Chunk; local: number }[] = [];
  private readonly body: MeshStandardMaterial;
  private readonly stemMat: MeshStandardMaterial;
  private readonly uniforms = { uWave: { value: 1e9 }, uWaveSoft: { value: 2 } };
  private readonly flares = new Map<number, { t: number; base: number }>();

  constructor(
    readonly specs: PumpkinSpec[],
    atlas: Texture,
    options: { detail: [number, number]; simple: [number, number]; chunkSize?: number },
  ) {
    const hiGeo = pumpkinGeometry(options.detail[0], options.detail[1]);
    const loGeo = pumpkinGeometry(options.simple[0], options.simple[1]);
    const stemGeo = stemGeometry();
    // Lit only a little by the glow field: much of it there is the pumpkin's own candle, which
    // lights the inside, not the skin.
    this.body = hallow(new MeshStandardMaterial({ roughness: 0.5, metalness: 0 }), {
      key: 'pumpkin',
      glow: 0.35,
      uniforms: { uAtlas: { value: atlas }, ...this.uniforms },
      vertexPars: PUMPKIN_VERTEX_PARS,
      fragmentPars: PUMPKIN_FRAGMENT_PARS,
      vertex: [['#include <begin_vertex>', PUMPKIN_VERTEX]],
      fragment: [
        ['#include <color_fragment>', PUMPKIN_COLOR],
        ['#include <emissivemap_fragment>', PUMPKIN_EMISSIVE],
      ],
    });
    this.stemMat = hallow(new MeshStandardMaterial({ color: 0x5a5a2a, roughness: 0.85 }), {
      key: 'stem',
      glow: 1,
    });

    // Group into chunks: by the spec's key, or by a 6 m grid.
    const size = options.chunkSize ?? 6;
    const groups = new Map<string, number[]>();
    specs.forEach((s, i) => {
      const key =
        s.chunk ?? `${Math.floor(s.position.x / size)},${Math.floor(s.position.z / size)}`;
      let g = groups.get(key);
      if (!g) groups.set(key, (g = []));
      g.push(i);
    });

    const m = new Matrix4();
    const q = new Quaternion();
    const tiltQ = new Quaternion();
    const yAxis = new Vector3(0, 1, 0);
    const xAxis = new Vector3(1, 0, 0);
    const lines: number[] = [];
    for (const members of groups.values()) {
      const n = members.length;
      const carve = new InstancedBufferAttribute(new Float32Array(n), 1);
      const skin = new InstancedBufferAttribute(new Float32Array(n * 3), 3);
      const glow = new InstancedBufferAttribute(new Float32Array(n * 4), 4);
      const wave = new InstancedBufferAttribute(new Float32Array(n * 2), 2);
      wave.setUsage(DynamicDrawUsage);
      carve.setUsage(DynamicDrawUsage);
      const make = (geo: BufferGeometry, mat: MeshStandardMaterial) => {
        const g = new BufferGeometry();
        for (const name of Object.keys(geo.attributes))
          g.setAttribute(name, geo.getAttribute(name));
        g.setIndex(geo.getIndex());
        g.setAttribute('aCarve', carve);
        g.setAttribute('aSkin', skin);
        g.setAttribute('aGlow', glow);
        g.setAttribute('aWave', wave);
        return new InstancedMesh(g, mat, n);
      };
      const hi = make(hiGeo, this.body);
      const lo = make(loGeo, this.body);
      const stem = new InstancedMesh(stemGeo, this.stemMat, n);
      lo.instanceMatrix = hi.instanceMatrix;
      stem.instanceMatrix = hi.instanceMatrix;
      const center = new Vector3();
      members.forEach((idx, local) => {
        const s = specs[idx] as PumpkinSpec;
        q.setFromAxisAngle(yAxis, s.yaw);
        if (s.tilt) q.multiply(tiltQ.setFromAxisAngle(xAxis, s.tilt));
        m.compose(s.position, q, s.size);
        hi.setMatrixAt(local, m);
        carve.setX(local, s.carve);
        skin.setXYZ(local, s.skin.r, s.skin.g, s.skin.b);
        glow.setXYZW(local, s.glow.r, s.glow.g, s.glow.b, s.phase ?? Math.random());
        wave.setXY(local, s.seq ?? -1e9, 1);
        center.add(s.position);
        if (s.hang) {
          const top = s.position.y + s.size.y * 0.75;
          lines.push(s.position.x, top, s.position.z, s.position.x, top + s.hang, s.position.z);
        }
        this.where[idx] = { chunk: undefined as unknown as Chunk, local };
      });
      center.divideScalar(n);
      let radius = 0;
      for (const idx of members)
        radius = Math.max(radius, (specs[idx] as PumpkinSpec).position.distanceTo(center) + 0.5);
      for (const mesh of [hi, lo, stem]) {
        mesh.computeBoundingSphere();
        this.group.add(mesh);
      }
      const chunk: Chunk = { hi, lo, stem, center, radius, members, wave, carve };
      for (const idx of members) (this.where[idx] as { chunk: Chunk }).chunk = chunk;
      this.chunks.push(chunk);
    }
    if (lines.length) {
      const g = new BufferGeometry();
      g.setAttribute('position', new Float32BufferAttribute(lines, 3));
      const strings = new LineSegments(
        g,
        hallow(new LineBasicMaterial({ color: 0x0b0907, transparent: true, opacity: 0.55 }), { key: 'string', glow: 0.05 }),
      );
      this.group.add(strings);
    }
  }

  /** Detailed pumpkins near the camera, simple ones far away. Call once a frame. */
  update(camera: Camera, dt: number) {
    this.uniforms.uWave.value = this.wave;
    this.uniforms.uWaveSoft.value = this.waveSoftness;
    const cam = camera.position;
    for (const c of this.chunks) {
      const near = c.center.distanceTo(cam) - c.radius < this.detailDistance;
      c.hi.visible = near;
      c.stem.visible = near;
      c.lo.visible = !near;
    }
    for (const [idx, f] of this.flares) {
      f.t += dt;
      const k = f.t < 0.15 ? f.t / 0.15 : Math.max(0, 1 - (f.t - 0.15) / 1.6);
      this.setLevel(idx, f.base + k * 2.2);
      if (f.t > 1.75) {
        this.setLevel(idx, f.base);
        this.flares.delete(idx);
      }
    }
  }

  /** A lantern's brightness (1 = normal, 0 = out). */
  setLevel(index: number, level: number) {
    const w = this.where[index];
    if (!w) return;
    w.chunk.wave.setY(w.local, level);
    w.chunk.wave.needsUpdate = true;
  }

  level(index: number) {
    const w = this.where[index];
    return w ? w.chunk.wave.getY(w.local) : 0;
  }

  /** Changes a lantern's carving (a face that notices you). */
  setCarve(index: number, cell: number) {
    const w = this.where[index];
    if (!w) return;
    w.chunk.carve.setX(w.local, cell);
    w.chunk.carve.needsUpdate = true;
  }

  /** Squash, stretch or lift one pumpkin (1, 0 = as placed). For wobbles and bounces. */
  pose(index: number, scale: number, lift = 0, squash = 1) {
    const w = this.where[index];
    const s = this.specs[index];
    if (!w || !s) return;
    const q = new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), s.yaw);
    if (s.tilt) q.multiply(new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), s.tilt));
    const m = new Matrix4().compose(
      s.position.clone().add(new Vector3(0, lift, 0)),
      q,
      new Vector3(s.size.x * scale / Math.sqrt(squash), s.size.y * scale * squash, s.size.z * scale / Math.sqrt(squash)),
    );
    w.chunk.hi.setMatrixAt(w.local, m);
    w.chunk.hi.instanceMatrix.needsUpdate = true;
  }

  /** A quick bright flare, as if the candle caught a breath of air. */
  flare(index: number) {
    if (this.flares.has(index)) return;
    this.flares.set(index, { t: 0, base: this.level(index) });
  }

  /** The nearest pumpkin the ray hits (treating each as an ellipsoid-ish sphere), or -1. */
  pick(ray: Ray, maxDistance = 30): number {
    let best = -1;
    let bestT = maxDistance;
    const v = new Vector3();
    this.specs.forEach((s, i) => {
      const r = Math.max(s.size.x, s.size.y) * 1.15;
      v.subVectors(s.position, ray.origin);
      v.y += heightAt(s.position.x, s.position.z);
      const t = v.dot(ray.direction);
      if (t < 0 || t > bestT) return;
      const d2 = v.lengthSq() - t * t;
      if (d2 < r * r) {
        best = i;
        bestT = t;
      }
    });
    return best;
  }

  /** Glow-field lights for the lit lanterns (one per lantern, sharing its flicker phase). */
  glowLights(radius = 2.6, gain = 0.6): GlowLight[] {
    const out: GlowLight[] = [];
    this.specs.forEach((s, i) => {
      const w = this.where[i] as { chunk: Chunk; local: number };
      const phase = (w.chunk.hi.geometry.getAttribute('aGlow') as InstancedBufferAttribute).getW(
        w.local,
      );
      if (s.glow.r + s.glow.g + s.glow.b <= 0) return;
      out.push({
        x: s.position.x,
        z: s.position.z,
        radius,
        color: s.glow,
        intensity: gain / Math.max(1, s.glow.r),
        phase,
        flicker: 1,
        y: s.position.y,
        ...(s.seq !== undefined ? { seq: s.seq } : {}),
      });
    });
    return out;
  }

  dispose() {
    for (const c of this.chunks) {
      c.hi.geometry.dispose();
      c.lo.geometry.dispose();
      c.hi.dispose();
      c.lo.dispose();
      c.stem.dispose();
    }
    this.body.dispose();
    this.stemMat.dispose();
  }
}

export const PUMPKIN_ORANGE = [
  new Color(0.72, 0.2, 0.025),
  new Color(0.66, 0.23, 0.03),
  new Color(0.78, 0.28, 0.04),
  new Color(0.58, 0.16, 0.02),
  new Color(0.75, 0.33, 0.07),
];

/** Candle light colours: mostly warm flame, the odd coloured LED. */
export const CANDLE = {
  warm: new Color(1.0, 0.55, 0.16),
  gold: new Color(1.0, 0.72, 0.3),
  red: new Color(1.0, 0.12, 0.08),
  magenta: new Color(1.0, 0.1, 0.55),
  violet: new Color(0.55, 0.15, 1.0),
};
