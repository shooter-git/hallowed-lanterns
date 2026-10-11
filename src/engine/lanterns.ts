import {
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
  SphereGeometry,
  Vector3,
} from 'three';
import type { GlowLight } from './glowfield.ts';
import { hallow } from './shared.ts';
import { heightAt } from './terrain.ts';

/** One red paper lantern. */
export interface LanternSpec {
  position: Vector3;
  /** Radius (m); the photos' lanterns are about 0.17. */
  radius: number;
  /** Paper colour × the light inside it (linear). */
  glow: Color;
  phase?: number;
  /** String up to whatever it hangs from (m). */
  hang?: number;
  /** Length of the tassel (m). 0 for none. */
  tassel?: number;
  yaw?: number;
}

/**
 * Red paper lanterns with horizontal slits, lit from inside, by the hundred: the lantern tunnel,
 * the Lantern Sky and the lounge's lanterns on hooks. The paper glows red, brighter where you see
 * it face-on; the slits let out the warm candle light; gold caps top and bottom; a gold tassel
 * that sways.
 */
export class LanternField {
  readonly group = new Group();
  private readonly paper: MeshStandardMaterial;
  private readonly sway: InstancedBufferAttribute;
  private readonly body: InstancedMesh;
  private readonly tasselMesh: InstancedMesh;
  private readonly swing = new Map<number, number>();
  private readonly levels: InstancedBufferAttribute;

  constructor(readonly specs: LanternSpec[], options: { segments?: [number, number] } = {}) {
    const n = specs.length;
    const [lon, lat] = options.segments ?? [16, 10];
    const sphere = new SphereGeometry(1, lon, lat);
    // Squash a little, and pinch toward the caps like a real paper lantern.
    const pos = sphere.getAttribute('position');
    const v = new Vector3();
    for (let i = 0; i < pos.count; i++) {
      v.fromBufferAttribute(pos, i);
      const pinch = 1 - 0.18 * Math.abs(v.y) ** 3;
      pos.setXYZ(i, v.x * pinch, v.y * 0.86, v.z * pinch);
    }
    sphere.computeVertexNormals();
    const glow = new InstancedBufferAttribute(new Float32Array(n * 4), 4);
    this.sway = new InstancedBufferAttribute(new Float32Array(n), 1);
    this.sway.setUsage(DynamicDrawUsage);
    this.levels = new InstancedBufferAttribute(new Float32Array(n).fill(1), 1);
    this.levels.setUsage(DynamicDrawUsage);
    specs.forEach((s, i) => glow.setXYZW(i, s.glow.r, s.glow.g, s.glow.b, s.phase ?? Math.random()));
    sphere.setAttribute('aGlow', glow);
    sphere.setAttribute('aSway', this.sway);
    sphere.setAttribute('aLevel', this.levels);

    this.paper = hallow(new MeshStandardMaterial({ color: 0x5a0a06, roughness: 0.75 }), {
      key: 'lantern',
      glow: 0.3,
      vertexPars: /* glsl */ `
        attribute vec4 aGlow;
        attribute float aSway;
        attribute float aLevel;
        varying vec3 vLocal;
        varying vec3 vLight;
        varying vec3 vViewN;
      `,
      vertex: [
        [
          '#include <begin_vertex>',
          /* glsl */ `#include <begin_vertex>
          vLocal = position;
          vLight = aGlow.rgb * hlFlicker(uHlTime, aGlow.w) * aLevel;
          // Swing: tilt about the hanging point above.
          float sw = aSway * sin(uHlTime * 2.6 + aGlow.w * 6.28);
          transformed.x += sw * (1.6 - position.y) * 0.18;
          `,
        ],
        ['#include <defaultnormal_vertex>', '#include <defaultnormal_vertex>\nvViewN = normalize(transformedNormal);'],
      ],
      fragmentPars: /* glsl */ `
        varying vec3 vLocal;
        varying vec3 vLight;
        varying vec3 vViewN;
      `,
      fragment: [
        [
          '#include <emissivemap_fragment>',
          /* glsl */ `#include <emissivemap_fragment>
          {
            // Paper: brighter face-on, deeper red at the rim where the light crosses more of it.
            float facing = clamp(abs(vViewN.z), 0.0, 1.0);
            vec3 paper = vLight * mix(0.18, 0.55, facing * facing);
            // Slits: five horizontal rows, each broken into segments around the lantern.
            float ang = atan(vLocal.z, vLocal.x);
            float row = abs(fract(vLocal.y * 2.6 + 0.5) - 0.5);
            float slit = smoothstep(0.1, 0.05, row) * step(abs(vLocal.y), 0.62);
            slit *= smoothstep(0.15, 0.3, abs(sin(ang * 4.0)));
            vec3 flame = vec3(1.0, 0.45, 0.12) * length(vLight) * 0.55;
            totalEmissiveRadiance += mix(paper, flame, slit);
            // Ribs of the frame show as faint dark lines.
            float rib = smoothstep(0.03, 0.0, abs(sin(ang * 8.0)) * 0.2);
            totalEmissiveRadiance *= 1.0 - rib * 0.35;
          }`,
        ],
      ],
    });

    this.body = new InstancedMesh(sphere, this.paper, n);
    const capGeo = new CylinderGeometry(0.42, 0.5, 0.12, 10);
    const gold = hallow(new MeshStandardMaterial({ color: 0xc9902e, roughness: 0.4, metalness: 0.7 }), { key: 'gold', glow: 0.6 });
    const caps = new InstancedMesh(capGeo, gold, n * 2);
    const tasselGeo = new CylinderGeometry(0.035, 0.1, 1, 6, 1);
    tasselGeo.translate(0, -0.5, 0);
    this.tasselMesh = new InstancedMesh(tasselGeo, hallow(new MeshStandardMaterial({ color: 0xe0b450, roughness: 0.8 }), { key: 'tassel', glow: 1 }), n);
    const m = new Matrix4();
    const q = new Quaternion();
    const lines: number[] = [];
    specs.forEach((s, i) => {
      const r = s.radius;
      q.setFromAxisAngle(new Vector3(0, 1, 0), s.yaw ?? Math.random() * 6.28);
      m.compose(s.position, q, new Vector3(r, r, r));
      this.body.setMatrixAt(i, m);
      m.compose(s.position.clone().add(new Vector3(0, r * 0.86, 0)), q, new Vector3(r * 0.55, r * 0.6, r * 0.55));
      caps.setMatrixAt(i * 2, m);
      m.compose(s.position.clone().add(new Vector3(0, -r * 0.86, 0)), q, new Vector3(r * 0.5, r * 0.5, r * 0.5));
      caps.setMatrixAt(i * 2 + 1, m);
      const t = s.tassel ?? r * 2.2;
      m.compose(s.position.clone().add(new Vector3(0, -r * 0.92, 0)), q, new Vector3(r * 0.35, t, r * 0.35));
      this.tasselMesh.setMatrixAt(i, m);
      if (s.hang) lines.push(s.position.x, s.position.y + r * 0.9, s.position.z, s.position.x, s.position.y + r + s.hang, s.position.z);
    });
    for (const mesh of [this.body, caps, this.tasselMesh]) {
      mesh.computeBoundingSphere();
      this.group.add(mesh);
    }
    if (lines.length) {
      const g = new BufferGeometry();
      g.setAttribute('position', new Float32BufferAttribute(lines, 3));
      this.group.add(new LineSegments(g, hallow(new LineBasicMaterial({ color: 0x0a0806, transparent: true, opacity: 0.5 }), { key: 'string', glow: 0.05 })));
    }
  }

  /** A lantern's brightness (1 = as made, 0 = unlit). */
  setLevel(index: number, level: number) {
    this.levels.setX(index, level);
    this.levels.needsUpdate = true;
  }

  level(index: number) {
    return this.levels.getX(index);
  }

  /** Sets a lantern swinging (it settles by itself). */
  push(index: number, amount = 0.5) {
    this.swing.set(index, Math.min(1, (this.swing.get(index) ?? 0) + amount));
  }

  update(dt: number, breeze = 0.04) {
    for (let i = 0; i < this.specs.length; i++) {
      const extra = this.swing.get(i) ?? 0;
      this.sway.setX(i, breeze + extra);
      if (extra > 0) {
        const next = extra * Math.exp(-dt * 0.6);
        if (next < 0.01) this.swing.delete(i);
        else this.swing.set(i, next);
      }
    }
    this.sway.needsUpdate = true;
  }

  pick(ray: Ray, maxDistance = 25): number {
    let best = -1;
    let bestT = maxDistance;
    const v = new Vector3();
    this.specs.forEach((s, i) => {
      const r = s.radius * 1.4;
      v.subVectors(s.position, ray.origin);
      v.y += heightAt(s.position.x, s.position.z);
      const t = v.dot(ray.direction);
      if (t < 0 || t > bestT) return;
      if (v.lengthSq() - t * t < r * r) {
        best = i;
        bestT = t;
      }
    });
    return best;
  }

  glowLights(radius: number, gain: number): GlowLight[] {
    return this.specs.map((s) => ({
      x: s.position.x,
      z: s.position.z,
      radius,
      color: new Color(1, 0.18, 0.08),
      intensity: gain,
      phase: s.phase ?? 0,
      flicker: 0.6,
    }));
  }

  dispose() {
    this.group.traverse((o) => {
      const m = o as InstancedMesh;
      if (m.geometry) m.geometry.dispose();
    });
    this.paper.dispose();
  }
}

/**
 * Strings of small warm lights (fairy lights, LED rope lights) hung in sagging swags between
 * points. One draw call; returns glow-field lights for every few bulbs.
 */
export function stringLights(
  runs: { from: Vector3; to: Vector3; sag: number }[],
  options: { spacing: number; color: Color; brightness: number; size?: number; glowEvery?: number; glowRadius?: number; glowIntensity?: number; flicker?: number },
): { mesh: InstancedMesh; lights: GlowLight[]; bulbs: Vector3[] } {
  const bulbs: Vector3[] = [];
  for (const r of runs) {
    const len = r.from.distanceTo(r.to);
    const n = Math.max(2, Math.round(len / options.spacing));
    for (let i = 0; i <= n; i++) {
      const t = i / n;
      const p = r.from.clone().lerp(r.to, t);
      p.y -= r.sag * 4 * t * (1 - t);
      bulbs.push(p);
    }
  }
  const geo = new SphereGeometry(options.size ?? 0.018, 6, 4);
  const mat = hallow(new MeshStandardMaterial({ color: 0x000000, emissive: options.color, emissiveIntensity: options.brightness }), { key: 'bulb', glow: 0 });
  const mesh = new InstancedMesh(geo, mat, bulbs.length);
  const m = new Matrix4();
  bulbs.forEach((b, i) => mesh.setMatrixAt(i, m.makeTranslation(b.x, b.y, b.z)));
  mesh.computeBoundingSphere();
  const every = options.glowEvery ?? 3;
  const lights: GlowLight[] = [];
  bulbs.forEach((b, i) => {
    if (i % every === 0)
      lights.push({ x: b.x, z: b.z, radius: options.glowRadius ?? 1.2, color: options.color, intensity: options.glowIntensity ?? 0.15, flicker: options.flicker ?? 0, phase: Math.random() });
  });
  return { mesh, lights, bulbs };
}

/** Tells a camera-facing check: is `p` within `angle` of where the camera looks? */
export function inView(camera: Camera, p: Vector3, angle = 0.5) {
  const f = new Vector3(0, 0, -1).applyQuaternion(camera.quaternion);
  const d = p.clone().sub(camera.position).normalize();
  return f.dot(d) > Math.cos(angle);
}
