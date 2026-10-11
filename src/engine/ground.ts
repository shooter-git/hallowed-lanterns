import {
  CanvasTexture,
  LinearFilter,
  Mesh,
  MeshStandardMaterial,
  NoColorSpace,
  PlaneGeometry,
  type Texture,
  Vector4,
} from 'three';
import { hallow } from './shared.ts';
import type { SurfaceMaps } from './texgen.ts';

export type Bounds = [minX: number, minZ: number, sizeX: number, sizeZ: number];

/**
 * A top-down mask over a chapter, drawn with canvas: red = the path's surface, green = where
 * ground fog gathers, blue = where tall grass grows.
 */
export class GroundMask {
  readonly canvas = document.createElement('canvas');
  readonly ctx: CanvasRenderingContext2D;
  readonly bounds: Vector4;

  constructor(
    readonly area: Bounds,
    readonly pxPerMetre = 4,
  ) {
    this.canvas.width = Math.min(2048, Math.ceil(area[2] * pxPerMetre));
    this.canvas.height = Math.min(2048, Math.ceil(area[3] * pxPerMetre));
    this.ctx = this.canvas.getContext('2d', { willReadFrequently: false }) as CanvasRenderingContext2D;
    this.ctx.fillStyle = '#000';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    this.bounds = new Vector4(...area);
  }

  /** Canvas pixel for a world x/z. */
  px(x: number, z: number): [number, number] {
    const [minX, minZ, sx, sz] = this.area;
    return [
      ((x - minX) / sx) * this.canvas.width,
      (1 - (z - minZ) / sz) * this.canvas.height,
    ];
  }

  metres(m: number) {
    return (m / this.area[2]) * this.canvas.width;
  }

  /** Strokes a polyline in one channel ('r', 'g' or 'b'), adding to what's there. */
  stroke(points: [number, number][], width: number, channel: 'r' | 'g' | 'b', amount = 1) {
    const c = this.ctx;
    c.save();
    c.globalCompositeOperation = 'lighter';
    const v = Math.round(255 * amount);
    c.strokeStyle = channel === 'r' ? `rgb(${v},0,0)` : channel === 'g' ? `rgb(0,${v},0)` : `rgb(0,0,${v})`;
    c.lineWidth = this.metres(width);
    c.lineCap = 'round';
    c.lineJoin = 'round';
    c.beginPath();
    points.forEach(([x, z], i) => {
      const [px, py] = this.px(x, z);
      i ? c.lineTo(px, py) : c.moveTo(px, py);
    });
    c.stroke();
    c.restore();
  }

  /** A soft round blob in one channel. */
  blob(x: number, z: number, radius: number, channel: 'r' | 'g' | 'b', amount = 1) {
    const c = this.ctx;
    const [px, py] = this.px(x, z);
    const r = this.metres(radius);
    const v = Math.round(255 * amount);
    const col = channel === 'r' ? [v, 0, 0] : channel === 'g' ? [0, v, 0] : [0, 0, v];
    const g = c.createRadialGradient(px, py, 0, px, py, r);
    g.addColorStop(0, `rgba(${col.join(',')},1)`);
    g.addColorStop(1, `rgba(${col.join(',')},0)`);
    c.save();
    c.globalCompositeOperation = 'lighter';
    c.fillStyle = g;
    c.fillRect(px - r, py - r, r * 2, r * 2);
    c.restore();
  }

  /** Softens everything drawn so far (edges of paths blend into the grass). */
  soften(factor = 4) {
    const small = document.createElement('canvas');
    small.width = Math.max(1, Math.floor(this.canvas.width / factor));
    small.height = Math.max(1, Math.floor(this.canvas.height / factor));
    const sc = small.getContext('2d') as CanvasRenderingContext2D;
    sc.imageSmoothingQuality = 'high';
    sc.drawImage(this.canvas, 0, 0, small.width, small.height);
    this.ctx.imageSmoothingQuality = 'high';
    this.ctx.drawImage(small, 0, 0, this.canvas.width, this.canvas.height);
  }

  private tex: Texture | null = null;

  /** The mask as a texture (made once: draw everything first). */
  texture(): Texture {
    if (this.tex) return this.tex;
    const t = new CanvasTexture(this.canvas);
    this.tex = t;
    t.colorSpace = NoColorSpace;
    t.minFilter = LinearFilter;
    t.magFilter = LinearFilter;
    t.generateMipmaps = false;
    return t;
  }
}

/**
 * The ground: two baked surfaces (say gravel and grass) blended by the mask, with large-scale
 * variation so the tiling never shows, lit by the glow field and fogged like everything else.
 */
export function ground(options: {
  mask: GroundMask;
  /** Where the mask is red. */
  a: SurfaceMaps;
  /** Size of one tile of `a` (m). */
  aScale: number;
  /** Everywhere else. */
  b: SurfaceMaps;
  bScale: number;
  /** How far the ground reaches beyond the mask (m). */
  extent?: number;
  /** Overall brightness of the albedo (for wet or dusty looks). */
  tone?: number;
}): Mesh {
  const [minX, minZ, sx, sz] = options.mask.area;
  const extent = options.extent ?? 220;
  // Detailed over the chapter so it can follow the rises and dips; a coarse skirt out to the
  // horizon, a little lower so the detailed ground always wins where they overlap.
  const geo = new PlaneGeometry(sx, sz, Math.ceil(sx / 1.2), Math.ceil(sz / 1.2));
  geo.rotateX(-Math.PI / 2);
  geo.translate(minX + sx / 2, 0, minZ + sz / 2);
  const skirtGeo = new PlaneGeometry(sx + extent * 2, sz + extent * 2, 48, 48);
  skirtGeo.rotateX(-Math.PI / 2);
  skirtGeo.translate(minX + sx / 2, -0.12, minZ + sz / 2);
  const material = hallow(new MeshStandardMaterial({ roughness: 1, metalness: 0 }), {
    key: 'ground',
    glow: 1,
    uniforms: {
      tA: { value: options.a.albedo },
      tAN: { value: options.a.normal },
      tB: { value: options.b.albedo },
      tBN: { value: options.b.normal },
      uScaleA: { value: options.aScale },
      uScaleB: { value: options.bScale },
      tMask: { value: options.mask.texture() },
      uMaskBounds: { value: options.mask.bounds },
      uTone: { value: options.tone ?? 1 },
    },
    fragmentPars: /* glsl */ `
      uniform sampler2D tA;
      uniform sampler2D tAN;
      uniform sampler2D tB;
      uniform sampler2D tBN;
      uniform float uScaleA;
      uniform float uScaleB;
      uniform sampler2D tMask;
      uniform vec4 uMaskBounds;
      uniform float uTone;
      float hlRough;
      float hlW;
    `,
    fragment: [
      [
        '#include <map_fragment>',
        /* glsl */ `
        {
          vec2 g = vHlWorld.xz;
          vec2 muv = (g - uMaskBounds.xy) / uMaskBounds.zw;
          float inside = step(0.0, muv.x) * step(muv.x, 1.0) * step(0.0, muv.y) * step(muv.y, 1.0);
          float m = texture2D(tMask, muv).r * inside;
          vec2 ua = g / uScaleA;
          vec2 ub = g / uScaleB;
          vec4 a = texture2D(tA, ua);
          float ha = texture2D(tAN, ua).a;
          // Two scales of the second surface, rotated, so its tiling never lines up.
          vec4 b1 = texture2D(tB, ub);
          vec4 b2 = texture2D(tB, mat2(0.8, 0.6, -0.6, 0.8) * ub * 0.37 + 0.31);
          vec4 b = mix(b1, b2, 0.4);
          // Stones poke through at the path's edge rather than a soft smear.
          hlW = smoothstep(0.35, 0.65, m + (ha - 0.4) * 0.5 * (1.0 - abs(m * 2.0 - 1.0)));
          vec4 s = mix(b, a, hlW);
          float macro = hlFbm(g * 0.08) * 0.5 + hlFbm(g * 0.6) * 0.5;
          diffuseColor.rgb *= s.rgb * (0.72 + 0.56 * macro) * uTone;
          hlRough = s.a;
        }
        `,
      ],
      ['#include <roughnessmap_fragment>', 'float roughnessFactor = hlRough;'],
      [
        '#include <normal_fragment_maps>',
        /* glsl */ `
        {
          vec2 g = vHlWorld.xz;
          vec3 na = texture2D(tAN, g / uScaleA).xyz * 2.0 - 1.0;
          vec3 nb = texture2D(tBN, g / uScaleB).xyz * 2.0 - 1.0;
          vec3 n = normalize(mix(nb, na, hlW));
          vec3 wn = normalize(vec3(n.x, n.z, n.y));
          normal = normalize((viewMatrix * vec4(wn, 0.0)).xyz);
        }
        `,
      ],
    ],
  });
  const mesh = new Mesh(geo, material);
  mesh.receiveShadow = true;
  mesh.name = 'ground';
  const skirt = new Mesh(skirtGeo, material);
  skirt.name = 'ground-skirt';
  mesh.add(skirt);
  return mesh;
}
