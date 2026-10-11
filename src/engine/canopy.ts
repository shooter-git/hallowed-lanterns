import {
  BufferGeometry,
  CanvasTexture,
  Color,
  DoubleSide,
  Float32BufferAttribute,
  InstancedMesh,
  Matrix4,
  MeshStandardMaterial,
  Quaternion,
  SRGBColorSpace,
  Vector2,
  Vector3,
} from 'three';
import type { Path } from './rig.ts';
import { hallow } from './shared.ts';

/**
 * The woods closing in: a canopy of leaves arching over the path (with only small gaps of sky,
 * as in the photos) and thick undergrowth on both sides, so there is never a wide empty space.
 * Thousands of crossed leaf-cluster cards in one draw call, lit from below by the lanterns and
 * stirring in the breeze. Cheap: a few thousand triangles, alpha-tested (no blending).
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

let tex: CanvasTexture | null = null;
/** A full leafy cluster with a ragged edge, darker inside, a few twigs. */
function clusterTexture(): CanvasTexture {
  if (tex) return tex;
  const size = 512;
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d') as CanvasRenderingContext2D;
  const rnd = rng(7);
  g.strokeStyle = 'rgb(40,30,20)';
  g.lineWidth = 5;
  for (let i = 0; i < 6; i++) {
    g.beginPath();
    g.moveTo(size / 2, size / 2);
    const a = rnd() * Math.PI * 2;
    g.quadraticCurveTo(size / 2 + Math.cos(a + 0.4) * 120, size / 2 + Math.sin(a + 0.4) * 120, size / 2 + Math.cos(a) * 220, size / 2 + Math.sin(a) * 220);
    g.stroke();
  }
  for (let i = 0; i < 420; i++) {
    const a = rnd() * Math.PI * 2;
    const r = Math.pow(rnd(), 0.7) * size * 0.46;
    const x = size / 2 + Math.cos(a) * r;
    const y = size / 2 + Math.sin(a) * r;
    const len = size * (0.045 + rnd() * 0.04);
    const shade = (0.45 + rnd() * 0.55) * (1 - (r / (size * 0.46)) * 0.25);
    const hue = rnd();
    g.save();
    g.translate(x, y);
    g.rotate(rnd() * Math.PI * 2);
    g.fillStyle = `rgb(${Math.round((44 + hue * 60) * shade)},${Math.round((78 + hue * 40) * shade)},${Math.round((30 + hue * 10) * shade)})`;
    g.beginPath();
    g.moveTo(0, 0);
    g.quadraticCurveTo(len * 0.5, -len * 0.42, len, 0);
    g.quadraticCurveTo(len * 0.5, len * 0.42, 0, 0);
    g.fill();
    g.restore();
  }
  tex = new CanvasTexture(c);
  tex.colorSpace = SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

/** Two crossed quads, centred, with normals bent outward like a rounded clump. */
function clump(): BufferGeometry {
  const pos: number[] = [];
  const nor: number[] = [];
  const uv: number[] = [];
  const idx: number[] = [];
  for (let k = 0; k < 3; k++) {
    const a = (k * Math.PI) / 3;
    const ca = Math.cos(a);
    const sa = Math.sin(a);
    const base = pos.length / 3;
    for (const [u, v] of [
      [-0.5, -0.5],
      [0.5, -0.5],
      [0.5, 0.5],
      [-0.5, 0.5],
    ] as [number, number][]) {
      const x = u * ca;
      const z = u * sa;
      pos.push(x, v * 0.8, z);
      const n = new Vector3(x * 1.4, v * 0.8 + 0.25, z * 1.4).normalize();
      nor.push(n.x, n.y, n.z);
      uv.push(u + 0.5, v + 0.5);
    }
    idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new Float32BufferAttribute(nor, 3));
  g.setAttribute('uv', new Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  return g;
}

export interface WoodlandOptions {
  /** Canopy band height above the ground (m). */
  canopy: [number, number];
  /** How far either side of the path's centre the canopy reaches (m). */
  reach: number;
  /** 0 = closed overhead, 1 = an open gap of sky along the path's centre line. */
  skyGap: number;
  /** Canopy clumps per metre of path. */
  density: number;
  /** Undergrowth: from this far out from the centre line, to `wallTo`, up to `wallHeight` m. */
  wallFrom: number;
  wallTo: number;
  wallHeight: number;
  wallDensity: number;
  tint?: Color;
  /** How strongly the lanterns light the leaves from below. */
  glow?: number;
  seed?: number;
  /** Leave clearings: return true for places with no foliage. */
  clear?: (x: number, z: number, y: number) => boolean;
}

export function woodland(path: Path, options: WoodlandOptions) {
  const rnd = rng(options.seed ?? 3);
  const mats: Matrix4[] = [];
  const p = new Vector2();
  const t = new Vector2();
  const q = new Quaternion();
  const m = new Matrix4();
  const add = (x: number, y: number, z: number, s: number) => {
    if (options.clear?.(x, z, y)) return;
    q.setFromAxisAngle(new Vector3(rnd() - 0.5, 1, rnd() - 0.5).normalize(), rnd() * Math.PI * 2);
    m.compose(new Vector3(x, y, z), q, new Vector3(s, s * (0.75 + rnd() * 0.4), s));
    mats.push(m.clone());
  };
  const step = 1 / options.density;
  for (let s = -6; s < path.length + 6; s += step) {
    path.at(Math.max(0, Math.min(path.length, s)), p, t);
    const ext = s < 0 ? s : s > path.length ? s - path.length : 0;
    const cx = p.x + t.x * ext;
    const cz = p.y + t.y * ext;
    const nx = -t.y;
    const nz = t.x;
    // Canopy: thicker toward the sides, thinner over the middle, arching lower at the edges.
    for (let k = 0; k < 3; k++) {
      let lat = (rnd() * 2 - 1) * options.reach;
      const centre = 1 - Math.abs(lat) / options.reach;
      if (rnd() < options.skyGap * Math.pow(centre, 3)) lat = Math.sign(lat || 1) * options.reach * (0.4 + rnd() * 0.6);
      const arch = 1 - Math.pow(Math.abs(lat) / options.reach, 2) * 0.35;
      const y = (options.canopy[0] + rnd() * (options.canopy[1] - options.canopy[0])) * arch;
      add(cx + nx * lat + (rnd() - 0.5) * step, y, cz + nz * lat + (rnd() - 0.5) * step, 2.2 + rnd() * 2.6);
    }
    // Undergrowth walls on both sides.
    for (let k = 0; k < options.wallDensity; k++) {
      const side = rnd() < 0.5 ? -1 : 1;
      const lat = side * (options.wallFrom + rnd() * (options.wallTo - options.wallFrom));
      const y = 0.4 + Math.pow(rnd(), 1.4) * options.wallHeight;
      add(cx + nx * lat, y, cz + nz * lat, 1.3 + rnd() * 1.8 + y * 0.25);
    }
  }
  const material = hallow(
    new MeshStandardMaterial({ map: clusterTexture(), color: options.tint ?? new Color(0.5, 0.58, 0.48), alphaTest: 0.5, side: DoubleSide, roughness: 0.85 }),
    {
      key: 'canopy',
      glow: options.glow ?? 0.45,
      vertex: [
        [
          '#include <begin_vertex>',
          /* glsl */ `#include <begin_vertex>
          {
            #ifdef USE_INSTANCING
              vec3 at = instanceMatrix[3].xyz;
            #else
              vec3 at = vec3(0.0);
            #endif
            float w = uHlTime * 0.9 + at.x * 0.13 + at.z * 0.17;
            transformed.x += sin(w) * 0.05 * (0.5 + position.y);
            transformed.z += cos(w * 0.8) * 0.04 * (0.5 + position.y);
          }`,
        ],
      ],
    },
  );
  const mesh = new InstancedMesh(clump(), material, mats.length);
  mats.forEach((mm, i) => mesh.setMatrixAt(i, mm));
  mesh.computeBoundingSphere();
  return {
    mesh,
    count: mats.length,
    dispose() {
      mesh.geometry.dispose();
      material.dispose();
    },
  };
}
