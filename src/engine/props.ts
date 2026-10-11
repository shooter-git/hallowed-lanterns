import {
  BoxGeometry,
  BufferGeometry,
  CanvasTexture,
  Color,
  DoubleSide,
  ExtrudeGeometry,
  Float32BufferAttribute,
  Group,
  InstancedMesh,
  Matrix4,
  Mesh,
  MeshStandardMaterial,
  RepeatWrapping,
  Shape,
  SRGBColorSpace,
  Vector3,
} from 'three';
import { hallow } from './shared.ts';

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

let reedTex: CanvasTexture | null = null;
/** Split reeds side by side, tan and uneven, with the odd gap of light between them. */
function reedTexture() {
  if (reedTex) return reedTex;
  const w = 512;
  const h = 256;
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const g = c.getContext('2d') as CanvasRenderingContext2D;
  const rnd = rng(5);
  let x = 0;
  while (x < w) {
    const rw = 3 + rnd() * 4;
    const tone = 0.55 + rnd() * 0.45;
    const r = Math.round(196 * tone);
    const gg = Math.round(160 * tone);
    const b = Math.round(104 * tone);
    const grad = g.createLinearGradient(x, 0, x + rw, 0);
    grad.addColorStop(0, `rgb(${r * 0.6},${gg * 0.6},${b * 0.6})`);
    grad.addColorStop(0.45, `rgb(${r},${gg},${b})`);
    grad.addColorStop(1, `rgb(${r * 0.5},${gg * 0.5},${b * 0.5})`);
    g.fillStyle = grad;
    const top = rnd() * 10;
    g.fillRect(x, top, rw, h - top);
    // Nodes along the reed.
    g.fillStyle = 'rgba(60,40,20,0.35)';
    for (let y = 30 + rnd() * 40; y < h; y += 50 + rnd() * 40) g.fillRect(x, y, rw, 1.5);
    x += rw + (rnd() < 0.12 ? 1.5 : 0);
  }
  // Two binding wires.
  g.fillStyle = 'rgba(30,25,20,0.8)';
  g.fillRect(0, h * 0.2, w, 2);
  g.fillRect(0, h * 0.78, w, 2);
  reedTex = new CanvasTexture(c);
  reedTex.colorSpace = SRGBColorSpace;
  reedTex.wrapS = RepeatWrapping;
  reedTex.anisotropy = 4;
  return reedTex;
}

/** Reed screening fences along polylines (x, z), `height` tall. One draw call. */
export function reedFence(input: [number, number][][], height: number): Mesh {
  // Split long runs into short panels so each one sits on the ground beneath it.
  const lines = input.map((line) => {
    const out: [number, number][] = [line[0] as [number, number]];
    for (let i = 0; i < line.length - 1; i++) {
      const [x0, z0] = line[i] as [number, number];
      const [x1, z1] = line[i + 1] as [number, number];
      const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, z1 - z0) / 1.5));
      for (let k = 1; k <= n; k++) out.push([x0 + ((x1 - x0) * k) / n, z0 + ((z1 - z0) * k) / n]);
    }
    return out;
  });
  const pos: number[] = [];
  const uv: number[] = [];
  const nor: number[] = [];
  const idx: number[] = [];
  for (const line of lines) {
    let u = 0;
    for (let i = 0; i < line.length - 1; i++) {
      const [x0, z0] = line[i] as [number, number];
      const [x1, z1] = line[i + 1] as [number, number];
      const len = Math.hypot(x1 - x0, z1 - z0);
      const nx = -(z1 - z0) / len;
      const nz = (x1 - x0) / len;
      const base = pos.length / 3;
      const u1 = u + len / 1.6;
      pos.push(x0, 0, z0, x1, 0, z1, x1, height, z1, x0, height, z0);
      uv.push(u, 0, u1, 0, u1, 1, u, 1);
      for (let k = 0; k < 4; k++) nor.push(nx, 0, nz);
      idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
      u = u1;
    }
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new Float32BufferAttribute(nor, 3));
  g.setAttribute('uv', new Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  const mat = hallow(new MeshStandardMaterial({ map: reedTexture(), roughness: 0.85, side: DoubleSide }), { key: 'reeds', glow: 1.4 });
  return new Mesh(g, mat);
}

/** A rounded white archway (the entrance to the lantern tunnel). */
export function archway(width: number, height: number, depth: number, radius: number, color = new Color(0.82, 0.78, 0.7)): Mesh {
  const outer = new Shape();
  const w = width / 2;
  outer.moveTo(-w, 0);
  outer.lineTo(-w, height - radius);
  outer.quadraticCurveTo(-w, height, -w + radius, height);
  outer.lineTo(w - radius, height);
  outer.quadraticCurveTo(w, height, w, height - radius);
  outer.lineTo(w, 0);
  // Down the inside of the arch and back out: one U-shaped outline.
  outer.lineTo(w - 0.45, 0);
  const iw = w - 0.45;
  const ih = height - 0.45;
  const ir = radius * 0.8;
  outer.lineTo(iw, ih - ir);
  outer.quadraticCurveTo(iw, ih, iw - ir, ih);
  outer.lineTo(-iw + ir, ih);
  outer.quadraticCurveTo(-iw, ih, -iw, ih - ir);
  outer.lineTo(-iw, 0);
  outer.lineTo(-w, 0);
  const geo = new ExtrudeGeometry(outer, { depth, bevelEnabled: true, bevelSize: 0.04, bevelThickness: 0.04, bevelSegments: 2, curveSegments: 12 });
  geo.translate(0, 0, -depth / 2);
  const mat = hallow(new MeshStandardMaterial({ color, roughness: 0.7 }), { key: 'arch', glow: 1.3 });
  return new Mesh(geo, mat);
}

/** Dark timber frame for a covered walkway: posts, beams and cross-beams, instanced. */
export function walkwayFrame(from: number, to: number, halfWidth: number, height: number, bay: number, color = new Color(0.05, 0.04, 0.035)): Group {
  const group = new Group();
  const mat = hallow(new MeshStandardMaterial({ color, roughness: 0.9 }), { key: 'frame', glow: 1 });
  const bays = Math.max(1, Math.round(Math.abs(from - to) / bay));
  const dir = Math.sign(to - from);
  const posts = new InstancedMesh(new BoxGeometry(0.14, height, 0.14), mat, (bays + 1) * 2);
  const beams = new InstancedMesh(new BoxGeometry(0.12, 0.18, Math.abs(to - from)), mat, 2);
  const cross = new InstancedMesh(new BoxGeometry(halfWidth * 2 + 0.3, 0.14, 0.12), mat, bays + 1);
  const m = new Matrix4();
  for (let i = 0; i <= bays; i++) {
    const z = from + dir * i * (Math.abs(to - from) / bays);
    posts.setMatrixAt(i * 2, m.makeTranslation(-halfWidth, height / 2, z));
    posts.setMatrixAt(i * 2 + 1, m.makeTranslation(halfWidth, height / 2, z));
    cross.setMatrixAt(i, m.makeTranslation(0, height, z));
  }
  beams.setMatrixAt(0, m.makeTranslation(-halfWidth, height, (from + to) / 2));
  beams.setMatrixAt(1, m.makeTranslation(halfWidth, height, (from + to) / 2));
  for (const x of [posts, beams, cross]) {
    x.computeBoundingSphere();
    group.add(x);
  }
  return group;
}

/** A simple stand-in box (used until a modelled prop is available). */
export function standIn(size: Vector3, color: Color, at: Vector3, yaw = 0): Mesh {
  const mesh = new Mesh(new BoxGeometry(size.x, size.y, size.z), hallow(new MeshStandardMaterial({ color, roughness: 0.9 }), { key: 'standin', glow: 1 }));
  mesh.position.copy(at).add(new Vector3(0, size.y / 2, 0));
  mesh.rotation.y = yaw;
  return mesh;
}
