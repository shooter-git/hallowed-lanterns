import {
  BufferGeometry,
  CanvasTexture,
  Color,
  DoubleSide,
  Float32BufferAttribute,
  Group,
  InstancedMesh,
  Matrix4,
  MeshStandardMaterial,
  Quaternion,
  SRGBColorSpace,
  Vector3,
} from 'three';
import { hallow } from './shared.ts';

/**
 * Woodland trees, grown in code: a few species of branching skeleton, each made once as bark
 * tubes and leaf-cluster cards, then instanced across a chapter (two draw calls per species). At
 * night they are mostly silhouettes against the sky, lit from below by the lanterns — so form,
 * canopy and the way light catches the undersides of the leaves matter most.
 */

export interface TreeSpecies {
  height: number;
  trunkRadius: number;
  /** How far branches spread, relative to height. */
  spread: number;
  /** Branching levels below the trunk. */
  depth: number;
  /** Children per branch. */
  children: number;
  /** Where on the trunk branching starts (0–1). */
  crownStart: number;
  /** Leaf cluster size (m). */
  leafSize: number;
  /** Leaf clusters per terminal branch. */
  leafDensity: number;
  /** Upward tendency of branches (0 = level, 1 = straight up). */
  lift: number;
  seed: number;
}

export const SPECIES: Record<'oak' | 'tall' | 'young' | 'bush' | 'pole', TreeSpecies> = {
  oak: { height: 9, trunkRadius: 0.32, spread: 0.75, depth: 3, children: 4, crownStart: 0.3, leafSize: 1.5, leafDensity: 4, lift: 0.25, seed: 11 },
  tall: { height: 12, trunkRadius: 0.22, spread: 0.42, depth: 3, children: 3, crownStart: 0.45, leafSize: 1.3, leafDensity: 4, lift: 0.55, seed: 23 },
  young: { height: 6, trunkRadius: 0.12, spread: 0.5, depth: 2, children: 4, crownStart: 0.35, leafSize: 1.1, leafDensity: 5, lift: 0.45, seed: 37 },
  /** Undergrowth: low, dense, many-stemmed. */
  /** A tall bare trunk with a few big limbs (the woodland canopy cards give it its leaves). */
  pole: { height: 11, trunkRadius: 0.2, spread: 0.38, depth: 1, children: 3, crownStart: 0.55, leafSize: 1, leafDensity: 0, lift: 0.5, seed: 53 },
  bush: { height: 1.8, trunkRadius: 0.04, spread: 0.9, depth: 2, children: 5, crownStart: 0.05, leafSize: 0.75, leafDensity: 5, lift: 0.4, seed: 41 },
};

interface Branch {
  points: Vector3[];
  radii: number[];
  level: number;
}

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

/** A leaf-cluster texture: dozens of overlapping leaves on a transparent card. */
function leafTexture(): CanvasTexture {
  const size = 512;
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d') as CanvasRenderingContext2D;
  const rnd = rng(99);
  for (let i = 0; i < 150; i++) {
    const a = rnd() * Math.PI * 2;
    const r = Math.sqrt(rnd()) * size * 0.42;
    const x = size / 2 + Math.cos(a) * r;
    const y = size / 2 + Math.sin(a) * r;
    const len = size * (0.06 + rnd() * 0.05);
    const ang = rnd() * Math.PI * 2;
    const shade = 0.55 + rnd() * 0.45;
    const hue = rnd();
    g.save();
    g.translate(x, y);
    g.rotate(ang);
    g.fillStyle = `rgb(${Math.round((40 + hue * 50) * shade)},${Math.round((70 + hue * 30) * shade)},${Math.round(28 * shade)})`;
    g.beginPath();
    g.moveTo(0, 0);
    g.quadraticCurveTo(len * 0.5, -len * 0.38, len, 0);
    g.quadraticCurveTo(len * 0.5, len * 0.38, 0, 0);
    g.fill();
    g.restore();
  }
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

/** Grows a skeleton of branches. */
function grow(sp: TreeSpecies): { branches: Branch[]; tips: { p: Vector3; dir: Vector3; level: number }[] } {
  const rnd = rng(sp.seed);
  const branches: Branch[] = [];
  const tips: { p: Vector3; dir: Vector3; level: number }[] = [];
  const up = new Vector3(0, 1, 0);

  const make = (start: Vector3, dir: Vector3, length: number, radius: number, level: number) => {
    const segs = Math.max(3, 7 - level * 2);
    const pts: Vector3[] = [start.clone()];
    const radii: number[] = [radius];
    const d = dir.clone().normalize();
    const p = start.clone();
    for (let i = 1; i <= segs; i++) {
      // Wander, droop under their own weight, and reach a little toward the light.
      d.add(new Vector3((rnd() - 0.5) * 0.35, (rnd() - 0.5) * 0.2 + sp.lift * 0.08 - level * 0.03, (rnd() - 0.5) * 0.35)).normalize();
      p.addScaledVector(d, length / segs);
      pts.push(p.clone());
      radii.push(radius * (1 - (i / segs) * 0.75));
    }
    const b: Branch = { points: pts, radii, level };
    branches.push(b);
    if (level < sp.depth) {
      const n = level === 0 ? sp.children + 2 : sp.children;
      for (let k = 0; k < n; k++) {
        const at = level === 0 ? sp.crownStart + (1 - sp.crownStart) * (k / n) * 0.9 + rnd() * 0.05 : 0.35 + rnd() * 0.6;
        const idx = Math.min(pts.length - 2, Math.floor(at * (pts.length - 1)));
        const from = pts[idx] as Vector3;
        const along = (pts[idx + 1] as Vector3).clone().sub(from).normalize();
        const az = (k / n) * Math.PI * 2 + rnd() * 1.2;
        const out = new Vector3(Math.cos(az), 0, Math.sin(az));
        const childDir = out.multiplyScalar(1 - sp.lift).add(along.clone().multiplyScalar(0.4)).add(up.clone().multiplyScalar(sp.lift)).normalize();
        const childLen = length * (level === 0 ? sp.spread : 0.62) * (0.7 + rnd() * 0.5);
        make(from, childDir, childLen, (radii[idx] as number) * 0.6, level + 1);
      }
    } else {
      for (let k = 0; k < sp.leafDensity; k++) {
        const t = 0.3 + rnd() * 0.7;
        const idx = Math.floor(t * (pts.length - 1));
        tips.push({ p: (pts[idx] as Vector3).clone(), dir: dir.clone(), level });
      }
    }
  };
  make(new Vector3(0, -0.3, 0), new Vector3((rnd() - 0.5) * 0.15, 1, (rnd() - 0.5) * 0.15), sp.height * 0.72, sp.trunkRadius, 0);
  return { branches, tips };
}

/** Tubes along each branch, merged into one geometry. */
function barkGeometry(branches: Branch[]): BufferGeometry {
  const pos: number[] = [];
  const nor: number[] = [];
  const uv: number[] = [];
  const idx: number[] = [];
  const t = new Vector3();
  const n1 = new Vector3();
  const n2 = new Vector3();
  const helper = new Vector3();
  for (const b of branches) {
    const sides = b.level === 0 ? 9 : b.level === 1 ? 6 : 4;
    const base = pos.length / 3;
    b.points.forEach((p, i) => {
      const next = b.points[Math.min(i + 1, b.points.length - 1)] as Vector3;
      const prev = b.points[Math.max(i - 1, 0)] as Vector3;
      t.subVectors(next, prev).normalize();
      helper.set(0, 1, 0);
      if (Math.abs(t.y) > 0.9) helper.set(1, 0, 0);
      n1.crossVectors(t, helper).normalize();
      n2.crossVectors(t, n1).normalize();
      // Roots flare at the base of the trunk.
      const flare = b.level === 0 && i === 0 ? 1.6 : 1;
      const r = (b.radii[i] as number) * flare;
      for (let s = 0; s <= sides; s++) {
        const a = (s / sides) * Math.PI * 2;
        const nx = n1.x * Math.cos(a) + n2.x * Math.sin(a);
        const ny = n1.y * Math.cos(a) + n2.y * Math.sin(a);
        const nz = n1.z * Math.cos(a) + n2.z * Math.sin(a);
        pos.push(p.x + nx * r, p.y + ny * r, p.z + nz * r);
        nor.push(nx, ny, nz);
        uv.push(s / sides, i);
      }
    });
    const rings = b.points.length;
    for (let i = 0; i < rings - 1; i++) {
      for (let s = 0; s < sides; s++) {
        const a = base + i * (sides + 1) + s;
        const c = a + sides + 1;
        idx.push(a, c, a + 1, a + 1, c, c + 1);
      }
    }
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new Float32BufferAttribute(nor, 3));
  g.setAttribute('uv', new Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  return g;
}

/** Leaf clusters: pairs of crossed cards facing out from the crown, with normals bent outward. */
function foliageGeometry(tips: { p: Vector3; dir: Vector3 }[], size: number, centre: Vector3, seed: number): BufferGeometry {
  const rnd = rng(seed);
  const pos: number[] = [];
  const nor: number[] = [];
  const uv: number[] = [];
  const sway: number[] = [];
  const idx: number[] = [];
  const q = new Quaternion();
  const corners = [
    [-0.5, -0.5],
    [0.5, -0.5],
    [0.5, 0.5],
    [-0.5, 0.5],
  ];
  for (const tip of tips) {
    const s = size * (0.7 + rnd() * 0.6);
    const out = tip.p.clone().sub(centre).normalize();
    for (let card = 0; card < 2; card++) {
      q.setFromAxisAngle(new Vector3(0, 1, 0), rnd() * Math.PI + card * Math.PI * 0.5);
      const tilt = new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), (rnd() - 0.5) * 1.2);
      q.multiply(tilt);
      const base = pos.length / 3;
      for (const [cx, cy] of corners) {
        const v = new Vector3((cx as number) * s, (cy as number) * s, 0).applyQuaternion(q).add(tip.p);
        pos.push(v.x, v.y, v.z);
        // Normals point away from the crown's centre, so the canopy shades like a rounded mass.
        const nrm = v.clone().sub(centre).normalize().lerp(out, 0.5).normalize();
        nor.push(nrm.x, nrm.y, nrm.z);
        uv.push((cx as number) + 0.5, (cy as number) + 0.5);
        sway.push(rnd());
      }
      idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
    }
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new Float32BufferAttribute(nor, 3));
  g.setAttribute('uv', new Float32BufferAttribute(uv, 2));
  g.setAttribute('aSway', new Float32BufferAttribute(sway, 1));
  g.setIndex(idx);
  return g;
}

export interface TreePlacement {
  x: number;
  z: number;
  scale?: number;
  yaw?: number;
}

export interface Forest {
  group: Group;
  /** Points out on branches (world space) where things can hang from. */
  anchors: Vector3[];
  dispose: () => void;
}

/** Plants trees of one or more species at the given places. */
export function forest(
  placements: { species: keyof typeof SPECIES; at: TreePlacement[] }[],
  options: { leafTint?: Color; bark?: Color; leafless?: boolean } = {},
): Forest {
  const group = new Group();
  const anchors: Vector3[] = [];
  const tex = leafTexture();
  const barkMat = hallow(new MeshStandardMaterial({ color: options.bark ?? new Color(0.09, 0.07, 0.055), roughness: 0.95 }), {
    key: 'bark',
    glow: 0.7,
  });
  const leafMat = hallow(
    new MeshStandardMaterial({
      map: tex,
      color: options.leafTint ?? new Color(0.55, 0.62, 0.5),
      alphaTest: 0.45,
      side: DoubleSide,
      roughness: 0.8,
    }),
    {
      key: 'leaves',
      glow: 0.55,
      vertexPars: 'attribute float aSway;',
      vertex: [
        [
          '#include <begin_vertex>',
          /* glsl */ `#include <begin_vertex>
          {
            // Leaves stir in the breeze, more toward the top of the tree.
            float w = uHlTime * 1.3 + aSway * 6.28 + position.x * 0.3;
            transformed.x += sin(w) * 0.06 * position.y * 0.12;
            transformed.z += cos(w * 0.8) * 0.05 * position.y * 0.12;
            transformed.y += sin(w * 1.7) * 0.02;
          }`,
        ],
      ],
    },
  );
  const disposables: BufferGeometry[] = [];
  const m = new Matrix4();
  const q = new Quaternion();
  for (const { species, at } of placements) {
    if (!at.length) continue;
    const sp = SPECIES[species];
    const { branches, tips } = grow(sp);
    const bark = barkGeometry(branches);
    const centre = new Vector3(0, sp.height * 0.7, 0);
    const leaves = foliageGeometry(tips, sp.leafSize, centre, sp.seed + 1);
    disposables.push(bark, leaves);
    const barkMesh = new InstancedMesh(bark, barkMat, at.length);
    const leafMesh = options.leafless || tips.length === 0 ? null : new InstancedMesh(leaves, leafMat, at.length);
    at.forEach((p, i) => {
      const s = p.scale ?? 1;
      q.setFromAxisAngle(new Vector3(0, 1, 0), p.yaw ?? 0);
      m.compose(new Vector3(p.x, 0, p.z), q, new Vector3(s, s, s));
      barkMesh.setMatrixAt(i, m);
      leafMesh?.setMatrixAt(i, m);
      // Anchors: points along mid-level branches.
      for (const b of branches) {
        if (b.level < 1 || b.level > 2) continue;
        const pt = b.points[Math.floor(b.points.length * 0.7)] as Vector3;
        anchors.push(pt.clone().applyMatrix4(m));
      }
    });
    for (const mesh of [barkMesh, leafMesh]) {
      if (!mesh) continue;
      mesh.computeBoundingSphere();
      group.add(mesh);
    }
  }
  return {
    group,
    anchors,
    dispose: () => {
      for (const g of disposables) g.dispose();
      barkMat.dispose();
      leafMat.dispose();
      tex.dispose();
    },
  };
}

/** Places trees along both sides of a path, keeping its corridor clear. */
export function lineThePath(
  points: { x: number; y: number }[],
  clear: number,
  options: { spacing: number; depth: number; seed: number; jitter?: number },
): TreePlacement[] {
  const rnd = rng(options.seed);
  const out: TreePlacement[] = [];
  const step = Math.max(1, Math.round(options.spacing / 0.25));
  for (let i = 0; i < points.length - 1; i += step) {
    const p = points[i] as { x: number; y: number };
    const q = points[Math.min(points.length - 1, i + 1)] as { x: number; y: number };
    const tx = q.x - p.x;
    const tz = q.y - p.y;
    const len = Math.hypot(tx, tz) || 1;
    const nx = -tz / len;
    const nz = tx / len;
    for (const side of [-1, 1]) {
      for (let row = 0; row < options.depth; row++) {
        const d = clear + row * options.spacing * 1.1 + rnd() * options.spacing * 0.8;
        const along = (rnd() - 0.5) * options.spacing * (options.jitter ?? 0.8);
        const x = p.x + nx * d * side + (tx / len) * along;
        const z = p.y + nz * d * side + (tz / len) * along;
        // Keep away from every part of the path, not just this point.
        let ok = true;
        for (let k = 0; k < points.length; k += 4) {
          const o = points[k] as { x: number; y: number };
          if (Math.hypot(o.x - x, o.y - z) < clear * 0.9) {
            ok = false;
            break;
          }
        }
        if (ok) out.push({ x, z, scale: 0.8 + rnd() * 0.45, yaw: rnd() * Math.PI * 2 });
      }
    }
  }
  return out;
}
