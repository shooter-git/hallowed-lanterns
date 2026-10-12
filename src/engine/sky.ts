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
import type { Tier } from '../chapters/types.ts';
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
  /**
   * The heavens as a long exposure sees them (0–1): the Milky Way with its star clouds and dust
   * lanes, a dense field of faint stars and a little airglow, in place of the plain stars and
   * faint band (0, the default, is just those).
   */
  milkyWay: number;
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
    milkyWay: 0,
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
  out.milkyWay = a.milkyWay + (b.milkyWay - a.milkyWay) * t;
}

/**
 * Where the galaxy lies in the sky: its bright heart over the trees ahead and to the left (as it
 * sets in the south-west on an October evening), the band climbing from it across the sky ahead,
 * past the zenith, and down behind you to the right.
 */
const GALAXY_CENTRE = new Vector3(-0.55, 0.45, -0.72).normalize();
const GALAXY_POLE = new Vector3().crossVectors(GALAXY_CENTRE, new Vector3(0.5, 1, 0.15).normalize()).normalize();
const GALAXY_SIDE = new Vector3().crossVectors(GALAXY_POLE, GALAXY_CENTRE);

/**
 * The sky dome: a physically-flavoured gradient (deeper overhead, hazier at the horizon), the
 * sun's glow, and stars that twinkle (or, with `milkyWay`, the whole of the heavens). It follows
 * the camera and is drawn behind everything.
 */
export class Sky {
  readonly mesh: Mesh<SphereGeometry, ShaderMaterial>;
  readonly state = skyState();
  /** How much detail the heavens get (fewer layers of stars and of noise on low). */
  tier: Tier = 'mid';

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
        uHeavens: { value: 0 },
        uDetail: { value: 1 },
        uPixelRatio: { value: 1 },
        uGalCentre: { value: GALAXY_CENTRE },
        uGalPole: { value: GALAXY_POLE },
        uGalSide: { value: GALAXY_SIDE },
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
        uniform float uHeavens;
        uniform float uDetail;
        uniform float uPixelRatio;
        uniform vec3 uGalCentre;
        uniform vec3 uGalPole;
        uniform vec3 uGalSide;
        uniform vec3 uFogColor;
        uniform float uTime;
        varying vec3 vDir;
        ${NOISE}
        // Value noise that wraps around every "period" cells in x (the band's longitude goes
        // all the way round the sky), and a few octaves of it.
        float hlRingNoise(vec2 p, float period) {
          vec2 i = floor(p);
          vec2 f = fract(p);
          vec2 u = f * f * (3.0 - 2.0 * f);
          float x0 = mod(i.x, period);
          float x1 = mod(i.x + 1.0, period);
          return mix(mix(hlHash12(vec2(x0, i.y)), hlHash12(vec2(x1, i.y)), u.x),
                     mix(hlHash12(vec2(x0, i.y + 1.0)), hlHash12(vec2(x1, i.y + 1.0)), u.x), u.y);
        }
        float hlRingFbm(vec2 p, float period, float octaves) {
          float v = 0.0;
          float a = 0.5;
          float n = 0.0;
          for (int i = 0; i < 6; i++) {
            if (float(i) >= octaves) break;
            v += a * hlRingNoise(p, period);
            n += a;
            p = p * 2.0 + vec2(0.0, 5.17);
            period *= 2.0;
            a *= 0.5;
          }
          return v / n;
        }
        // Where a direction meets an equi-angular cube around the sky (cells all much the same
        // size, with no pinch overhead): 0–1 across the face, and which face.
        vec3 hlCube(vec3 d) {
          vec3 a = abs(d);
          vec2 uv;
          float face;
          if (a.x >= a.y && a.x >= a.z) {
            uv = d.zy / a.x;
            face = d.x > 0.0 ? 0.0 : 1.0;
          } else if (a.y >= a.z) {
            uv = d.xz / a.y;
            face = d.y > 0.0 ? 2.0 : 3.0;
          } else {
            uv = d.xy / a.z;
            face = d.z > 0.0 ? 4.0 : 5.0;
          }
          return vec3(atan(uv) * 0.63662 + 0.5, face);
        }
        // And back: the direction of a point on a face.
        vec3 hlCubeDir(vec2 uv, float face) {
          vec2 t = tan((uv - 0.5) * 1.5708);
          vec3 d = face < 1.5 ? vec3(face < 0.5 ? 1.0 : -1.0, t.y, t.x)
            : face < 3.5 ? vec3(t.x, face < 2.5 ? 1.0 : -1.0, t.y)
            : vec3(t.x, t.y, face < 4.5 ? 1.0 : -1.0);
          return normalize(d);
        }
        // A star's colour from its temperature (0 hot, 1 cool): blue-white, white, pale yellow,
        // pale orange.
        vec3 hlStarTint(float t) {
          vec3 c = mix(vec3(0.68, 0.79, 1.0), vec3(1.0), smoothstep(0.0, 0.3, t));
          c = mix(c, vec3(1.0, 0.9, 0.74), smoothstep(0.45, 0.75, t));
          return mix(c, vec3(1.0, 0.74, 0.5), smoothstep(0.86, 1.0, t));
        }
        // One layer of stars, at most one to each cell of the cube: soft points a pixel or so
        // across, sized on the screen so they hold still as you turn (px is the angle of a
        // pixel, size the pixel ratio, so a sharp screen shows them the same; a layer too fine
        // to draw cleanly fades out). Brightness falls off as a power law from the faintest, so
        // most are faint and a few are bright; only those carry a halo.
        vec3 hlStarLayer(vec3 d, vec3 cube, float cells, float chance, float faint, float slope, float cap, float px, float size, float seed, float twinkle) {
          float cellPx = 1.5708 / (cells * px);
          float fade = smoothstep(1.5, 2.5, cellPx);
          vec3 sum = vec3(0.0);
          if (fade <= 0.0) return sum;
          vec2 p = cube.xy * cells;
          vec2 base = floor(p - 0.5);
          vec2 key = vec2(cube.z * 113.17 + seed, seed * 3.71 - cube.z * 71.31);
          for (int k = 0; k < 4; k++) {
            vec2 c = base + vec2(k == 1 || k == 3 ? 1.0 : 0.0, k >= 2 ? 1.0 : 0.0);
            if (min(c.x, c.y) < 0.0 || max(c.x, c.y) >= cells) continue;
            if (hlHash12(c + key) > chance) continue;
            vec2 j = hlHash22(c + key + 41.3);
            vec2 q = hlHash22(c.yx * 1.37 + key.yx);
            float dist = length(d - hlCubeDir((c + 0.5 + (j - 0.5) * 0.6) / cells, cube.z)) / px;
            float flux = min(faint * pow(1.0 - 0.999 * q.x, -slope), cap);
            float big = smoothstep(0.6, 4.0, flux);
            float sigma = (0.7 + 0.5 * big) * size;
            float s = exp(-dist * dist / (2.0 * sigma * sigma));
            s += big * 0.06 * exp(-dist * 0.6 / size) * smoothstep(0.62 * cellPx, 0.4 * cellPx, dist);
            float tw = 1.0 + twinkle * (0.6 * sin(uTime * (2.3 + 5.0 * j.x) + q.y * 60.0) + 0.4 * sin(uTime * (6.1 + 4.0 * j.y) + q.x * 90.0));
            vec3 tint = mix(vec3(1.0), hlStarTint(q.y), 0.25 + 0.5 * smoothstep(0.05, 1.5, flux));
            sum += tint * flux * s * tw;
          }
          return sum * fade;
        }
        // The heavens as a long exposure sees them: a little airglow low down, the Milky Way
        // (star clouds and dark dust lanes, warm at its heart and cooler along its arms) and a
        // dense field of stars, crowding into the band and thinning in its dust.
        vec3 hlHeavens(vec3 d, float h, float px) {
          float up = max(h, 0.0);
          // Thicker air toward the horizon: everything dims and the stars twinkle more.
          float air = smoothstep(0.0, 0.32, up);
          vec3 col = vec3(0.0);

          // Airglow: a faint green band some ten or fifteen degrees up, in slow uneven waves,
          // amber beneath it.
          float wave = hlNoise(d.xz / (up + 0.3) * 1.8 + 3.0);
          float band = smoothstep(0.03, 0.22, up) * exp(-max(up - 0.22, 0.0) * 4.5);
          col += vec3(0.006, 0.02, 0.009) * band * (0.55 + 0.9 * wave);
          col += vec3(0.008, 0.005, 0.0015) * smoothstep(0.02, 0.1, up) * exp(-up * 9.0);

          // The galaxy's own coordinates: latitude across the band, longitude along it from the
          // centre.
          float b = asin(clamp(dot(d, uGalPole), -1.0, 1.0));
          float l = atan(dot(d, uGalSide), dot(d, uGalCentre));
          float crowd = 0.0;
          float ab = abs(b);
          if (ab < 0.75) {
            float heart = exp(-l * l * 3.0);
            // The disc, narrow along the arms and swelling toward the centre; the bulge of the
            // core; and a wide faint glow either side.
            float width = 0.075 + 0.1 * heart;
            float disc = exp(-0.5 * b * b / (width * width)) * (0.55 + 0.45 * heart);
            float bulge = exp(-0.5 * (l * l / 0.09 + (b + 0.03) * (b + 0.03) / 0.05));
            float wide = exp(-0.5 * b * b / 0.12) * (0.1 + 0.1 * heart);
            // Star clouds (clumps and knots of light along the band) and dust (dark clouds
            // stretched along the plane, thickest near it, and the Great Rift, a long dark lane
            // splitting the band from near the core up across the sky). Far from the plane, where
            // there's little of either, the noise isn't worth working out.
            float clump = 0.45;
            float tau = 0.0;
            if (ab < 0.5) {
              float clouds = hlRingFbm(vec2(l * 5.093, b * 6.0 + 1.3), 32.0, 3.0 + uDetail);
              clump = mix(0.45, smoothstep(0.25, 0.8, clouds), smoothstep(0.5, 0.38, ab));
              float dn = hlRingFbm(vec2(l * 10.186, b * 24.0 + 7.1), 64.0, 3.0 + uDetail);
              tau = smoothstep(0.47, 0.75, dn) * exp(-0.5 * b * b / 0.02) * (1.7 - 0.8 * heart);
              float riftB = 0.02 + 0.03 * sin(l * 2.3 + 0.6);
              float riftW = 0.025 + 0.03 * hlRingNoise(vec2(l * 6.366, 3.7), 40.0);
              float rift = exp(-0.5 * (b - riftB) * (b - riftB) / (riftW * riftW)) * smoothstep(-0.4, 0.05, l) * smoothstep(1.9, 1.3, l);
              tau += rift * (0.6 + 1.6 * dn);
              if (uDetail > 1.5) {
                // Fine dark filaments.
                float r = 1.0 - abs(2.0 * hlRingFbm(vec2(l * 15.279, b * 36.0 + 2.9), 96.0, 3.0) - 1.0);
                tau += pow(r, 5.0) * 0.45 * exp(-0.5 * b * b / 0.012);
              }
            }
            float light = disc * (0.35 + 1.2 * clump) + bulge * (2.0 + 1.0 * clump) + wide;
            // Dust reddens the light it lets through.
            vec3 through = exp(-tau * vec3(0.8, 1.0, 1.25));
            // Golden at the heart, cool and pale along the arms, bluer in the brightest clouds;
            // a few faint pink glows of hydrogen near the core.
            vec3 tone = mix(vec3(0.8, 0.82, 0.95), vec3(1.0, 0.74, 0.48), smoothstep(0.15, 0.95, heart + bulge * 0.4));
            tone *= mix(vec3(1.0), vec3(0.93, 0.97, 1.08), clump * (1.0 - heart));
            vec2 n1 = vec2(l - 0.1, b + 0.03);
            vec2 n2 = vec2(l + 0.16, b + 0.05);
            float pink = exp(-dot(n1, n1) / 0.0012) + 0.6 * exp(-dot(n2, n2) / 0.0006);
            col += (tone * light * 0.029 + vec3(0.045, 0.007, 0.018) * pink) * through * air * uStars;
            crowd = (disc * (0.3 + 1.1 * clump) + bulge * 0.8) * (through.g * 1.2 - 0.2);
          }

          // The stars: the bright ones scattered evenly, the faint ones crowding into the band.
          if (h > 0.0) {
            vec3 cube = hlCube(d);
            float twinkle = 0.05 + 0.25 * pow(1.0 - up, 4.0);
            float size = clamp(uPixelRatio, 1.0, 2.0);
            vec3 stars = hlStarLayer(d, cube, 90.0, 0.3, 0.01, 1.0, 5.0, px, size, 1.0, twinkle);
            stars += hlStarLayer(d, cube, 200.0, 0.12 + 0.6 * crowd, 0.006, 0.85, 0.3, px, size, 2.0, twinkle);
            if (uDetail > 0.5) stars += hlStarLayer(d, cube, 300.0, 0.04 + 0.85 * crowd, 0.004 + 0.012 * crowd, 0.6, 0.1, px, size, 3.0, twinkle);
            col += stars * air * uStars;
          }
          return col;
        }
        void main() {
          vec3 d = normalize(vDir);
          float h = clamp(d.y, -1.0, 1.0);
          // The angle one pixel covers (for stars drawn a steady size on the screen).
          float px = max(length(dFdx(d)), length(dFdy(d)));
          // Gradient: rapid change near the horizon, slow overhead.
          float t = pow(clamp(h, 0.0, 1.0), 0.45);
          vec3 col = mix(uHorizon, uZenith, t);
          // The sun's glow: a tight bright halo and a wide warm wash along the horizon.
          float mu = max(dot(d, uSunDir), 0.0);
          float horizonBand = exp(-abs(h) * 6.0);
          col += uSunColor * (pow(mu, 600.0) * 30.0 + pow(mu, 24.0) * 1.2 + pow(mu, 3.0) * 0.35) * uSunGlow;
          col += uSunColor * horizonBand * pow(mu, 1.5) * 0.5 * uSunGlow;
          col += uPollution * exp(-max(h, 0.0) * 9.0);
          // Stars: a jittered grid on the sphere, fewer near the hazy horizon (giving way to the
          // full heavens where those are shown).
          float plain = 1.0 - uHeavens;
          if (uStars > 0.001 && h > 0.0 && plain > 0.001) {
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
              col += tint * s * 2.5 * uStars * smoothstep(0.0, 0.25, h) * plain;
            }
            // The faint band of the Milky Way.
            float band = exp(-pow(dot(d, normalize(vec3(0.3, 0.55, -0.78))) * 3.2, 2.0));
            col += vec3(0.6, 0.65, 0.8) * band * hlFbm(sp * 0.05) * 0.012 * uStars * plain;
          }
          if (uHeavens > 0.001 && h > -0.05) col += hlHeavens(d, h, px) * uHeavens;
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
    this.mesh.onBeforeRender = (renderer) => {
      material.uniforms.uPixelRatio!.value = renderer.getPixelRatio();
    };
  }

  update(cameraPosition: Vector3) {
    this.mesh.position.copy(cameraPosition);
    const u = this.mesh.material.uniforms;
    u.uSunGlow!.value = this.state.sunGlow;
    u.uStars!.value = this.state.stars;
    u.uHeavens!.value = this.state.milkyWay;
    u.uDetail!.value = this.tier === 'low' ? 0 : this.tier === 'mid' ? 1 : 2;
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
