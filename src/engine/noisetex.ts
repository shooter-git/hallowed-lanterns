import { DataTexture, LinearFilter, LinearMipmapLinearFilter, RedFormat, RepeatWrapping, UnsignedByteType } from 'three';

/** How many noise cells the texture spans before it repeats (see `hlFbmT`). */
export const NOISE_PERIOD = 16;

/**
 * The same four-octave value noise as `hlFbm`, worked out once into a small tiling texture, so the
 * shaders that cover most of the screen (the ground, the fog's stacked layers, the pumpkins' skins)
 * read it in one lookup instead of working out sixteen hashes a pixel, every frame.
 */
export function fbmTexture(size = 256): DataTexture {
  const lattice = (period: number, seed: number) => {
    const v = new Float32Array(period * period);
    let s = seed >>> 0;
    for (let i = 0; i < v.length; i++) {
      s = (s + 0x6d2b79f5) >>> 0;
      let t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      v[i] = ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    }
    return v;
  };
  const octaves = [0, 1, 2, 3].map((o) => ({ period: NOISE_PERIOD << o, amp: 0.5 / (1 << o), v: lattice(NOISE_PERIOD << o, 977 + o * 131) }));
  // Eight bits are plenty for noise, and every device can filter and mipmap them.
  const data = new Uint8Array(size * size);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      let sum = 0;
      for (const { period, amp, v } of octaves) {
        const fx = (x / size) * period;
        const fy = (y / size) * period;
        const ix = Math.floor(fx);
        const iy = Math.floor(fy);
        let ux = fx - ix;
        let uy = fy - iy;
        ux = ux * ux * (3 - 2 * ux);
        uy = uy * uy * (3 - 2 * uy);
        const x0 = ix % period;
        const x1 = (ix + 1) % period;
        const y0 = (iy % period) * period;
        const y1 = ((iy + 1) % period) * period;
        const a = v[y0 + x0] as number;
        const b = v[y0 + x1] as number;
        const c = v[y1 + x0] as number;
        const d = v[y1 + x1] as number;
        sum += amp * (a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy);
      }
      data[y * size + x] = Math.round(sum * 255);
    }
  }
  const tex = new DataTexture(data, size, size, RedFormat, UnsignedByteType);
  tex.wrapS = tex.wrapT = RepeatWrapping;
  tex.magFilter = LinearFilter;
  tex.minFilter = LinearMipmapLinearFilter;
  tex.generateMipmaps = true;
  tex.needsUpdate = true;
  return tex;
}
