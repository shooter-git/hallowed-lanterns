import {
  BackSide,
  Color,
  CylinderGeometry,
  DoubleSide,
  Mesh,
  ShaderMaterial,
  SphereGeometry,
  Vector3,
} from 'three';
import { NOISE } from './glsl.ts';
import { shared } from './shared.ts';

/** A moment in the sky's evening, from sunset to deep night. */
export interface SkyState {
  zenith: Color;
  horizon: Color;
  /** The glow around the sun (or the last light where it set). */
  sunColor: Color;
  /** Direction toward the sun (y can be below 0 once it has set). */
  sunDir: Vector3;
  sunGlow: number;
  stars: number;
  /** A faint warm dome of light near the horizon (towns, the farm's lights). */
  lightPollution: Color;
}

export function skyState(partial: Partial<SkyState> = {}): SkyState {
  return {
    zenith: new Color(0.01, 0.015, 0.04),
    horizon: new Color(0.03, 0.035, 0.07),
    sunColor: new Color(0, 0, 0),
    sunDir: new Vector3(0, -0.3, -1).normalize(),
    sunGlow: 0,
    stars: 1,
    lightPollution: new Color(0.02, 0.012, 0.008),
    ...partial,
  };
}

export function lerpSky(out: SkyState, a: SkyState, b: SkyState, t: number) {
  out.zenith.copy(a.zenith).lerp(b.zenith, t);
  out.horizon.copy(a.horizon).lerp(b.horizon, t);
  out.sunColor.copy(a.sunColor).lerp(b.sunColor, t);
  out.sunDir.copy(a.sunDir).lerp(b.sunDir, t).normalize();
  out.sunGlow = a.sunGlow + (b.sunGlow - a.sunGlow) * t;
  out.stars = a.stars + (b.stars - a.stars) * t;
  out.lightPollution.copy(a.lightPollution).lerp(b.lightPollution, t);
}

/**
 * The sky dome: a physically-flavoured gradient (deeper overhead, hazier at the horizon), the
 * sun's glow, and stars that twinkle. It follows the camera and is drawn behind everything.
 */
export class Sky {
  readonly mesh: Mesh<SphereGeometry, ShaderMaterial>;
  readonly state = skyState();

  constructor() {
    const material = new ShaderMaterial({
      uniforms: {
        uZenith: { value: this.state.zenith },
        uHorizon: { value: this.state.horizon },
        uSunColor: { value: this.state.sunColor },
        uSunDir: { value: this.state.sunDir },
        uSunGlow: { value: 0 },
        uStars: { value: 1 },
        uPollution: { value: this.state.lightPollution },
        uFogColor: shared.uFogColor,
        uTime: shared.uHlTime,
      },
      vertexShader: /* glsl */ `
        varying vec3 vDir;
        void main() {
          vDir = position;
          vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          gl_Position = vec4(p.xy, p.w * 0.99999, p.w);
        }`,
      fragmentShader: /* glsl */ `
        uniform vec3 uZenith;
        uniform vec3 uHorizon;
        uniform vec3 uSunColor;
        uniform vec3 uSunDir;
        uniform float uSunGlow;
        uniform float uStars;
        uniform vec3 uPollution;
        uniform vec3 uFogColor;
        uniform float uTime;
        varying vec3 vDir;
        ${NOISE}
        void main() {
          vec3 d = normalize(vDir);
          float h = clamp(d.y, -1.0, 1.0);
          // Gradient: rapid change near the horizon, slow overhead.
          float t = pow(clamp(h, 0.0, 1.0), 0.45);
          vec3 col = mix(uHorizon, uZenith, t);
          // The sun's glow: a tight bright halo and a wide warm wash along the horizon.
          float mu = max(dot(d, uSunDir), 0.0);
          float horizonBand = exp(-abs(h) * 6.0);
          col += uSunColor * (pow(mu, 600.0) * 30.0 + pow(mu, 24.0) * 1.2 + pow(mu, 3.0) * 0.35) * uSunGlow;
          col += uSunColor * horizonBand * pow(mu, 1.5) * 0.5 * uSunGlow;
          col += uPollution * exp(-max(h, 0.0) * 9.0);
          // Stars: a jittered grid on the sphere, fewer near the hazy horizon.
          if (uStars > 0.001 && h > 0.0) {
            vec2 sp = vec2(atan(d.z, d.x), asin(h)) * 120.0;
            vec2 cell = floor(sp);
            vec2 f = fract(sp) - 0.5;
            float r = hlHash12(cell);
            if (r > 0.965) {
              vec2 o = (hlHash22(cell) - 0.5) * 0.6;
              float dist = length(f - o);
              float mag = pow((r - 0.965) / 0.035, 3.0);
              float tw = 0.75 + 0.25 * sin(uTime * (1.5 + r * 4.0) + r * 100.0);
              float s = smoothstep(0.16, 0.0, dist) * mag * tw;
              vec3 tint = mix(vec3(0.75, 0.82, 1.0), vec3(1.0, 0.9, 0.75), hlHash12(cell + 7.0));
              col += tint * s * 2.5 * uStars * smoothstep(0.0, 0.25, h);
            }
            // The faint band of the Milky Way.
            float band = exp(-pow(dot(d, normalize(vec3(0.3, 0.55, -0.78))) * 3.2, 2.0));
            col += vec3(0.6, 0.65, 0.8) * band * hlFbm(sp * 0.05) * 0.012 * uStars;
          }
          // Below the horizon, and near it, the air is the fog.
          col = mix(col, uFogColor, smoothstep(0.08, -0.04, h));
          gl_FragColor = vec4(col, 1.0);
        }`,
      side: BackSide,
      depthWrite: false,
    });
    this.mesh = new Mesh(new SphereGeometry(900, 48, 24), material);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = -10;
  }

  update(cameraPosition: Vector3) {
    this.mesh.position.copy(cameraPosition);
    const u = this.mesh.material.uniforms;
    u.uSunGlow!.value = this.state.sunGlow;
    u.uStars!.value = this.state.stars;
  }

  dispose() {
    this.mesh.geometry.dispose();
    this.mesh.material.dispose();
  }
}

/**
 * A ring of distant tree-tops against the sky: a silhouette with ragged, leafy edges, lit faintly
 * from below by whatever glows on the farm.
 */
export function treeLine(options: {
  radius: number;
  height: number;
  color: Color;
  /** Light from below (the farm's lanterns, reflected off the haze). */
  under: Color;
  seed?: number;
}): Mesh {
  const geo = new CylinderGeometry(options.radius, options.radius, options.height * 2, 160, 1, true);
  geo.translate(0, options.height, 0);
  const material = new ShaderMaterial({
    uniforms: {
      uColor: { value: options.color },
      uUnder: { value: options.under },
      uHeight: { value: options.height },
      uSeed: { value: options.seed ?? 1 },
      uFogColor: shared.uFogColor,
    },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      varying float vY;
      void main() {
        vUv = uv;
        vY = position.y;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      uniform vec3 uUnder;
      uniform float uHeight;
      uniform float uSeed;
      uniform vec3 uFogColor;
      varying vec2 vUv;
      varying float vY;
      ${NOISE}
      void main() {
        float x = vUv.x * 160.0 + uSeed * 17.0;
        // Crowns of different heights, with leafy noise on their edges.
        float crowns = 0.55 + 0.3 * hlNoise(vec2(x * 0.18, uSeed)) + 0.15 * hlNoise(vec2(x * 0.6, uSeed + 3.0));
        float leafy = hlFbm(vec2(x * 2.5, vY * 0.9)) * 0.22;
        float top = (crowns + leafy - 0.1) * uHeight;
        if (vY > top) discard;
        float depth = clamp(vY / max(top, 0.01), 0.0, 1.0);
        vec3 col = uColor + uUnder * (1.0 - depth) * (0.6 + 0.4 * hlNoise(vec2(x, vY)));
        // Distance haze, slight: at dusk the trees are silhouettes.
        col = mix(col, uFogColor, 0.12);
        gl_FragColor = vec4(col, 1.0);
      }`,
    side: DoubleSide,
  });
  const mesh = new Mesh(geo, material);
  mesh.renderOrder = -5;
  return mesh;
}
