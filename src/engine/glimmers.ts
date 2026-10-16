import { AdditiveBlending, BufferGeometry, type Color, Float32BufferAttribute, Points, ShaderMaterial, Vector2 } from 'three';
import { NOISE, TERRAIN_PARS } from './glsl.ts';
import { shared } from './shared.ts';

/**
 * Little lights hanging in the air all around you: sparks drifting up from the candles, glitter,
 * the glow of tiny creatures in the sea. Points in a box
 * that wraps around the camera (so they never run out), each wandering on its own path worked out
 * in the shader: one draw call, nothing to update but the time.
 */
export interface GlimmerOptions {
  count: number;
  /** Size of the box around you that they fill (m). */
  box: number;
  /** Between these heights above the ground (m). */
  height: [number, number];
  /** Their colours (each picks one); linear light, brightness included. */
  colors: Color[];
  /** Size of the brightest (m). */
  size: number;
  /**
   * How they shine: 'spark' (a warm flicker, drifting up and fading), 'glitter' (quick twinkles) or
   * 'plankton' (a slow breathing glow that brightens near you).
   */
  style: 'spark' | 'glitter' | 'plankton';
  /** Drift (m/s): x and z, and up. */
  drift?: [number, number, number];
}

const STYLE = { spark: 0, glitter: 1, plankton: 2 } as const;

export class Glimmers {
  readonly points: Points<BufferGeometry, ShaderMaterial>;

  constructor(options: GlimmerOptions) {
    const n = options.count;
    const pos = new Float32Array(n * 3);
    const seed = new Float32Array(n * 2);
    const col = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      pos.set([Math.random() * options.box, Math.random(), Math.random() * options.box], i * 3);
      seed.set([Math.random(), Math.random()], i * 2);
      const c = options.colors[Math.floor(Math.random() * options.colors.length)] as Color;
      col.set([c.r, c.g, c.b], i * 3);
    }
    const geo = new BufferGeometry();
    geo.setAttribute('position', new Float32BufferAttribute(pos, 3));
    geo.setAttribute('aSeed', new Float32BufferAttribute(seed, 2));
    geo.setAttribute('aColor', new Float32BufferAttribute(col, 3));
    const [dx, dz, up] = options.drift ?? [0.05, 0.02, options.style === 'spark' ? 0.25 : 0];
    const material = new ShaderMaterial({
      uniforms: {
        uHlTime: shared.uHlTime,
        uTerrain: shared.uTerrain,
        uTerrainBounds: shared.uTerrainBounds,
        uFogDensity: shared.uFogDensity,
        uBox: { value: options.box },
        uHeight: { value: new Vector2(...options.height) },
        uSize: { value: options.size },
        uScale: { value: 600 },
        uDrift: { value: new Vector2(dx, dz) },
        uRise: { value: up },
        uLevel: { value: 1 },
      },
      defines: { HL_STYLE: STYLE[options.style] },
      vertexShader: /* glsl */ `
        attribute vec2 aSeed;
        attribute vec3 aColor;
        uniform float uHlTime;
        uniform float uBox;
        uniform vec2 uHeight;
        uniform float uSize;
        uniform float uScale;
        uniform vec2 uDrift;
        uniform float uRise;
        uniform float uLevel;
        uniform float uFogDensity;
        varying vec3 vColor;
        ${NOISE}
        ${TERRAIN_PARS}
        void main() {
          float t = uHlTime;
          vec2 s = aSeed;
          // Wander: a slow loop of its own, plus the drift of the air.
          vec3 p = position;
          p.xz += uDrift * t * (0.6 + 0.8 * s.x);
          p.x += sin(t * (0.21 + 0.3 * s.x) + s.y * 40.0) * 1.1 + sin(t * (0.9 + s.y) + s.x * 9.0) * 0.18;
          p.z += cos(t * (0.17 + 0.25 * s.y) + s.x * 31.0) * 1.1 + cos(t * (0.8 + s.x) + s.y * 7.0) * 0.18;
          vec3 c = cameraPosition - vec3(uBox * 0.5);
          p.xz = mod(p.xz - c.xz, uBox) + c.xz;
          // Height: its own level in the band (risers climb through it and start again at the bottom).
          float level = fract(p.y + uRise * t / max(uHeight.y - uHeight.x, 0.1) * (0.6 + 0.8 * s.y));
          float bob = sin(t * (0.5 + s.y) + s.x * 20.0) * 0.12;
          p.y = hlTerrain(p.xz) + mix(uHeight.x, uHeight.y, level) + bob;
          vec4 mv = viewMatrix * vec4(p, 1.0);
          // Fade at the edges of the box (so the wrap never shows), and the risers at the top and
          // bottom of the band.
          vec2 rel = abs(p.xz - cameraPosition.xz) / (uBox * 0.5);
          float fade = 1.0 - smoothstep(0.65, 1.0, max(rel.x, rel.y));
          // Gone right up close, where it would only be a big faint blur filling the view.
          fade *= smoothstep(0.5, 1.2, distance(p, cameraPosition));
          if (uRise > 0.0) fade *= smoothstep(0.0, 0.12, level) * smoothstep(1.0, 0.6, level);
          // How bright it is now.
          float b = 1.0;
          #if HL_STYLE == 0
            b = hlFlicker(t * 1.6, s.x) * (0.6 + 0.4 * s.y);
          #elif HL_STYLE == 1
            b = pow(0.5 + 0.5 * sin(t * (2.0 + 5.0 * s.x) + s.y * 60.0), 12.0) * 1.4 + 0.08;
          #else
            float near = 1.0 - smoothstep(1.0, 4.0, distance(p, cameraPosition));
            b = (0.35 + 0.35 * sin(t * (0.4 + 0.6 * s.x) + s.y * 30.0)) * (1.0 + 2.0 * near);
          #endif
          // Distant ones dim into the haze.
          float dist = -mv.z;
          float haze = exp(-uFogDensity * dist * 1.4);
          vColor = aColor * b * fade * haze * uLevel;
          // At least a pixel and a half across (smaller ones keep their light, spread wider), and at
          // most twenty.
          float px = uSize * (0.55 + 0.45 * s.x) * uScale / max(dist, 0.1);
          float drawn = clamp(px, 1.5, 20.0);
          vColor *= min(1.0, (px * px) / (drawn * drawn));
          gl_PointSize = drawn * 3.0;
          gl_Position = projectionMatrix * mv;
          if (vColor.r + vColor.g + vColor.b < 0.002) gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
        }`,
      fragmentShader: /* glsl */ `
        varying vec3 vColor;
        void main() {
          // A hot little core in a soft halo (the sprite is three times the core's size).
          vec2 q = (gl_PointCoord - 0.5) * 3.0;
          float d2 = dot(q, q);
          float a = exp(-d2 * 2.2) + 0.12 * exp(-d2 * 0.6);
          gl_FragColor = vec4(vColor * a, 1.0);
        }`,
      transparent: true,
      depthWrite: false,
      blending: AdditiveBlending,
    });
    this.points = new Points(geo, material);
    this.points.frustumCulled = false;
    this.points.renderOrder = 9;
  }

  /** Call every frame with the renderer's pixels per metre at 1 m (see the Ember). */
  update(pixelScale: number) {
    this.points.material.uniforms.uScale!.value = pixelScale;
  }

  /** 0 hides them, 1 is as made. */
  set level(v: number) {
    this.points.material.uniforms.uLevel!.value = v;
    this.points.visible = v > 0.001;
  }

  dispose() {
    this.points.geometry.dispose();
    this.points.material.dispose();
  }
}
