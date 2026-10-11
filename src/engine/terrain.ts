import { type Box3, DataTexture, DataUtils, HalfFloatType, LinearFilter, RedFormat, Vector2, Vector3, Vector4 } from 'three';
import type { Path } from './rig.ts';

type Bounds = [number, number, number, number];

function hash(x: number, z: number) {
  const s = Math.sin(x * 127.1 + z * 311.7) * 43758.5453;
  return s - Math.floor(s);
}
function noise(x: number, z: number) {
  const ix = Math.floor(x);
  const iz = Math.floor(z);
  const fx = x - ix;
  const fz = z - iz;
  const ux = fx * fx * (3 - 2 * fx);
  const uz = fz * fz * (3 - 2 * fz);
  const a = hash(ix, iz);
  const b = hash(ix + 1, iz);
  const c = hash(ix, iz + 1);
  const d = hash(ix + 1, iz + 1);
  return a + (b - a) * ux + (c - a) * uz + (a - b - c + d) * ux * uz;
}
function fbm(x: number, z: number) {
  return noise(x, z) * 0.6 + noise(x * 2.1 + 5, z * 2.1 + 3) * 0.28 + noise(x * 4.3 + 9, z * 4.3 + 1) * 0.12;
}

/**
 * The lie of the land: gentle rises and dips under a chapter, as a height grid. Everything drawn
 * with the world's materials is lifted onto it in the vertex shader (see `hallow`), so lanterns,
 * trees and posts all stand on the slopes; the walk, the Ember and the lights use `height()`.
 */
export class Terrain {
  readonly texture: DataTexture;
  readonly bounds: Vector4;
  private readonly grid: Float32Array;
  private readonly nx: number;
  private readonly nz: number;

  constructor(
    readonly area: Bounds,
    fn: (x: number, z: number) => number,
    readonly res = 1,
  ) {
    const [minX, minZ, sx, sz] = area;
    this.nx = Math.max(2, Math.ceil(sx / res) + 1);
    this.nz = Math.max(2, Math.ceil(sz / res) + 1);
    this.grid = new Float32Array(this.nx * this.nz);
    const half = new Uint16Array(this.nx * this.nz);
    for (let j = 0; j < this.nz; j++) {
      for (let i = 0; i < this.nx; i++) {
        const x = minX + (i / (this.nx - 1)) * sx;
        const z = minZ + (j / (this.nz - 1)) * sz;
        const h = fn(x, z);
        this.grid[j * this.nx + i] = h;
        half[j * this.nx + i] = DataUtils.toHalfFloat(h);
      }
    }
    this.texture = new DataTexture(half, this.nx, this.nz, RedFormat, HalfFloatType);
    this.texture.minFilter = LinearFilter;
    this.texture.magFilter = LinearFilter;
    this.texture.needsUpdate = true;
    this.bounds = new Vector4(...area);
  }

  /** Ground height at x, z (clamped to the edge outside the area). */
  height(x: number, z: number): number {
    const [minX, minZ, sx, sz] = this.area;
    const fx = Math.max(0, Math.min(1, (x - minX) / sx)) * (this.nx - 1);
    const fz = Math.max(0, Math.min(1, (z - minZ) / sz)) * (this.nz - 1);
    const i = Math.min(this.nx - 2, Math.floor(fx));
    const j = Math.min(this.nz - 2, Math.floor(fz));
    const u = fx - i;
    const v = fz - j;
    const g = this.grid;
    const a = g[j * this.nx + i] as number;
    const b = g[j * this.nx + i + 1] as number;
    const c = g[(j + 1) * this.nx + i] as number;
    const d = g[(j + 1) * this.nx + i + 1] as number;
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  }

  dispose() {
    this.texture.dispose();
  }
}

/**
 * Land shaped around a walk: the path follows `profile(s)` (its height `s` metres along), smooth
 * underfoot; away from it the ground rises into gentle banks and gets lumpier.
 */
export function aroundPath(
  path: Path,
  options: {
    profile: (s: number, length: number) => number;
    /** How much the ground rises per metre away from the path's edge (a gentle bank). */
    bank?: number;
    /** Size of the lumps off the path (m). */
    rough?: number;
    seed?: number;
  },
): (x: number, z: number) => number {
  const p = new Vector2();
  const seed = options.seed ?? 1;
  return (x, z) => {
    p.set(x, z);
    const n = path.nearest(p);
    const base = options.profile(n.s, path.length);
    const away = Math.max(0, Math.abs(n.lateral) - n.width / 2);
    const bank = (options.bank ?? 0.05) * Math.min(away, 25) * (1 - Math.exp(-away / 6));
    const lumps = (options.rough ?? 0.4) * (fbm(x * 0.09 + seed, z * 0.09 - seed) - 0.5) * 2 * Math.min(1, away / 4);
    return base + bank + lumps;
  };
}

/** The terrain of the chapter you're in (for the walk, the Ember, lights and taps). */
let current: Terrain | null = null;

export function setCurrentTerrain(t: Terrain | null) {
  current = t;
}

/** Ground height under x, z in the chapter you're in. */
export function heightAt(x: number, z: number): number {
  return current ? current.height(x, z) : 0;
}

/** A box (or point) as it stands on the ground: shifted up by the ground height under it. */
export function onGround(box: Box3): Box3 {
  const c = box.getCenter(new Vector3());
  return box.clone().translate(new Vector3(0, heightAt(c.x, c.z), 0));
}

export function pointOnGround(p: Vector3): Vector3 {
  return p.clone().setY(p.y + heightAt(p.x, p.z));
}
