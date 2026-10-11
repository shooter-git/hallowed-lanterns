import {
  BufferGeometry,
  Color,
  Float32BufferAttribute,
  Mesh,
  NormalBlending,
  ShaderMaterial,
  type Texture,
  Vector2,
  type Vector4,
} from 'three';
import { SHADER_PARS, shared, VERTEX_TERRAIN } from './shared.ts';

/**
 * Ground fog that rolls along the paths, as from the fog machines in the photos: stacked
 * horizontal slices of drifting noise, densest where the mask's green channel says, lit by the
 * lanterns around it (so it glows red over red lights) and parting around whoever walks through.
 */
export class FogBank {
  readonly mesh: Mesh<BufferGeometry, ShaderMaterial>;
  /** Where people are (x, z): the fog parts around them. Up to 4. */
  readonly walkers: Vector2[] = [new Vector2(1e4, 1e4)];

  constructor(options: {
    bounds: Vector4;
    mask: Texture;
    slices: number;
    /** Top of the fog (m). */
    height: number;
    /** Base colour of the fog where nothing lights it. */
    tint: Color;
    density: number;
    /** How strongly the lanterns light it. */
    glow?: number;
    wind?: Vector2;
  }) {
    const [minX, minZ, sx, sz] = [options.bounds.x, options.bounds.y, options.bounds.z, options.bounds.w];
    const pos: number[] = [];
    const slice: number[] = [];
    const idx: number[] = [];
    // Each slice is a grid (about 2.5 m cells) so it can follow the rise and fall of the ground.
    const nx = Math.max(1, Math.ceil(sx / 2.5));
    const nz = Math.max(1, Math.ceil(sz / 2.5));
    for (let i = 0; i < options.slices; i++) {
      const t = (i + 0.5) / options.slices;
      const y = 0.04 + t * t * options.height;
      const base = pos.length / 3;
      for (let j = 0; j <= nz; j++) {
        for (let k = 0; k <= nx; k++) {
          pos.push(minX + (k / nx) * sx, y, minZ + (j / nz) * sz);
          slice.push(t);
        }
      }
      for (let j = 0; j < nz; j++) {
        for (let k = 0; k < nx; k++) {
          const a = base + j * (nx + 1) + k;
          const b = a + nx + 1;
          idx.push(a, b, a + 1, a + 1, b, b + 1);
        }
      }
    }
    const geo = new BufferGeometry();
    geo.setAttribute('position', new Float32BufferAttribute(pos, 3));
    geo.setAttribute('aSlice', new Float32BufferAttribute(slice, 1));
    geo.setIndex(idx);
    const material = new ShaderMaterial({
      uniforms: {
        ...shared,
        tMask: { value: options.mask },
        uMaskBounds: { value: options.bounds },
        uTint: { value: options.tint },
        uDensity: { value: options.density / options.slices * 8 },
        uLit: { value: options.glow ?? 0.8 },
        uWind: { value: options.wind ?? new Vector2(0.25, -0.1) },
        uWalkers: { value: this.walkers.concat([new Vector2(1e4, 1e4), new Vector2(1e4, 1e4), new Vector2(1e4, 1e4)]).slice(0, 4) },
      },
      vertexShader: /* glsl */ `
        attribute float aSlice;
        varying vec3 vHlWorld;
        varying float vSlice;
        ${VERTEX_TERRAIN}
        void main() {
          vHlWorld = (modelMatrix * vec4(position, 1.0)).xyz;
          vHlWorld.y += hlTerrain(vHlWorld.xz);
          vSlice = aSlice;
          gl_Position = projectionMatrix * viewMatrix * vec4(vHlWorld, 1.0);
        }`,
      fragmentShader: /* glsl */ `
        ${SHADER_PARS}
        uniform sampler2D tMask;
        uniform vec4 uMaskBounds;
        uniform vec3 uTint;
        uniform float uDensity;
        uniform float uLit;
        uniform vec2 uWind;
        uniform vec2 uWalkers[4];
        varying vec3 vHlWorld;
        varying float vSlice;
        void main() {
          vec2 p = vHlWorld.xz;
          vec2 muv = (p - uMaskBounds.xy) / uMaskBounds.zw;
          float src = texture2D(tMask, muv).g;
          if (src < 0.01) discard;
          float t = uHlTime;
          // Two layers of drifting noise, offset per slice so the fog has depth.
          float n1 = hlFbm(p * 0.32 + uWind * t + vSlice * 2.3);
          float n2 = hlFbm(p * 1.05 - uWind * t * 1.7 + vec2(7.1, 3.3) + vSlice * 5.0);
          float billow = n1 * 0.75 + n2 * 0.45;
          float dens = smoothstep(0.42 + vSlice * 0.4, 1.05, billow + src * 0.3) * src;
          dens *= 1.0 - vSlice * 0.6;
          // Parts around people walking through.
          for (int i = 0; i < 4; i++) {
            float d = distance(p, uWalkers[i]);
            dens *= mix(0.15, 1.0, smoothstep(0.35, 1.6, d));
          }
          // Fade right at the eye, so the slices never show their edges.
          float dc = distance(vHlWorld, cameraPosition);
          dens *= smoothstep(0.4, 2.2, dc);
          float a = clamp(dens * uDensity, 0.0, 0.9);
          if (a < 0.003) discard;
          vec3 light = uTint + hlGlow(vHlWorld) * uLit;
          light = hlApplyFog(light, vHlWorld);
          gl_FragColor = vec4(light, a);
        }`,
      transparent: true,
      depthWrite: false,
      blending: NormalBlending,
    });
    this.mesh = new Mesh(geo, material);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = 5;
  }

  update() {
    const w = this.mesh.material.uniforms.uWalkers!.value as Vector2[];
    for (let i = 0; i < 4; i++) {
      const src = this.walkers[i];
      if (src) (w[i] as Vector2).copy(src);
      else (w[i] as Vector2).set(1e4, 1e4);
    }
  }

  dispose() {
    this.mesh.geometry.dispose();
    this.mesh.material.dispose();
  }
}

export const FOG_TINTS = {
  dusk: new Color(0.05, 0.045, 0.06),
  night: new Color(0.012, 0.012, 0.018),
};
