import {
  LinearFilter,
  LinearMipmapLinearFilter,
  Mesh,
  OrthographicCamera,
  PlaneGeometry,
  RepeatWrapping,
  ShaderMaterial,
  type Texture,
  UnsignedByteType,
  Vector2,
  type WebGLRenderer,
  WebGLRenderTarget,
} from 'three';
import { NOISE } from './glsl.ts';

/**
 * Bakes tileable surface textures on the GPU at load time (nothing to download): an albedo map
 * (with roughness in alpha) and a normal map (with height in alpha), from a height/colour shader.
 */
export interface SurfaceMaps {
  albedo: Texture;
  normal: Texture;
}

const VERT = /* glsl */ `
varying vec2 vUv;
void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }
`;

/** Shared GLSL: periodic Voronoi (so the textures tile). */
const VORONOI = /* glsl */ `
${NOISE}
// Returns (distance to nearest point, distance to its edge, the cell's random id).
vec3 voronoiP(vec2 p, float period, float seed) {
  vec2 n = floor(p);
  vec2 f = fract(p);
  float d1 = 8.0;
  float d2 = 8.0;
  vec2 best = vec2(0.0);
  for (int j = -1; j <= 1; j++)
  for (int i = -1; i <= 1; i++) {
    vec2 g = vec2(float(i), float(j));
    vec2 cell = mod(n + g, period);
    vec2 o = hlHash22(cell + seed * 13.1);
    vec2 r = g + o - f;
    float d = dot(r, r);
    if (d < d1) { d2 = d1; d1 = d; best = cell; }
    else if (d < d2) { d2 = d; }
  }
  return vec3(sqrt(d1), sqrt(d2) - sqrt(d1), hlHash12(best + seed));
}
float noiseP(vec2 p, float period) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  float a = hlHash12(mod(i, period));
  float b = hlHash12(mod(i + vec2(1.0, 0.0), period));
  float c = hlHash12(mod(i + vec2(0.0, 1.0), period));
  float d = hlHash12(mod(i + vec2(1.0, 1.0), period));
  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}
float noiseP2(vec2 p, vec2 period) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  float a = hlHash12(mod(i, period));
  float b = hlHash12(mod(i + vec2(1.0, 0.0), period));
  float c = hlHash12(mod(i + vec2(0.0, 1.0), period));
  float d = hlHash12(mod(i + vec2(1.0, 1.0), period));
  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}
// Grass blades: stretched noise in four tileable orientations.
float bladesP(vec2 uv, float along, float across, float lo) {
  float b = 0.0;
  vec2 frames[4];
  frames[0] = uv;
  frames[1] = uv.yx;
  frames[2] = vec2(uv.x + uv.y, uv.x - uv.y);
  frames[3] = vec2(uv.x - uv.y, uv.x + uv.y);
  for (int k = 0; k < 4; k++) {
    vec2 q = frames[k] + float(k) * 0.37;
    b = max(b, smoothstep(lo, 0.95, noiseP2(vec2(q.x * across, q.y * along), vec2(across, along))));
  }
  return b;
}
float fbmP(vec2 p, float period) {
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 5; i++) {
    v += a * noiseP(p, period);
    p *= 2.0;
    period *= 2.0;
    a *= 0.5;
  }
  return v;
}
`;

/** Crushed limestone gravel over packed dust (the arbor lane, the octopus beach). */
export const GRAVEL = /* glsl */ `
vec4 surface(vec2 uv, out float height) {
  vec3 big = voronoiP(uv * 34.0, 34.0, 1.0);
  vec3 small = voronoiP(uv * 90.0, 90.0, 2.0);
  float stoneBig = smoothstep(0.0, 0.16, big.y) * (1.0 - big.x * 0.55);
  float stoneSmall = smoothstep(0.0, 0.12, small.y) * (1.0 - small.x * 0.6);
  float dust = fbmP(uv * 8.0, 8.0);
  float h = max(stoneBig * (0.7 + 0.3 * big.z), stoneSmall * 0.55 * step(0.35, small.z));
  height = h;
  vec3 stoneA = vec3(0.58, 0.55, 0.5);
  vec3 stoneB = vec3(0.74, 0.7, 0.62);
  vec3 stoneC = vec3(0.45, 0.42, 0.38);
  float id = big.z;
  vec3 stone = id < 0.15 ? stoneC : mix(stoneA, stoneB, fract(id * 7.3));
  if (stoneSmall * 0.55 * step(0.35, small.z) > stoneBig * (0.7 + 0.3 * big.z))
    stone = mix(stoneA, stoneB, small.z) * 0.95;
  stone *= 0.85 + 0.3 * fbmP(uv * 160.0, 160.0);
  vec3 dirt = mix(vec3(0.22, 0.19, 0.15), vec3(0.36, 0.31, 0.25), dust);
  vec3 col = mix(dirt, stone, smoothstep(0.02, 0.18, h));
  float rough = mix(0.95, 0.75, smoothstep(0.1, 0.5, h));
  return vec4(col, rough);
}
`;

/** Dry, trampled pasture grass over dirt (field edges, the longhorns' pasture). */
export const DRY_GRASS = /* glsl */ `
vec4 surface(vec2 uv, out float height) {
  float patches = fbmP(uv * 4.0, 4.0);
  float fine = fbmP(uv * 40.0, 40.0);
  // Blades: streaks in random directions, made from stretched noise in a few rotated frames.
  float blades = bladesP(uv, 18.0, 260.0, 0.62);
  float grass = smoothstep(0.35, 0.6, patches + fine * 0.3);
  height = blades * grass * 0.8 + fine * 0.2;
  vec3 dirt = mix(vec3(0.2, 0.16, 0.11), vec3(0.32, 0.26, 0.18), fine);
  vec3 straw = mix(vec3(0.42, 0.37, 0.22), vec3(0.6, 0.53, 0.33), fine);
  vec3 green = mix(vec3(0.17, 0.22, 0.09), vec3(0.28, 0.32, 0.13), fine);
  vec3 g = mix(straw, green, smoothstep(0.4, 0.8, patches));
  vec3 col = mix(dirt, g * (0.7 + 0.5 * blades), grass);
  return vec4(col, 0.92);
}
`;

/** Lush mown lawn (the lantern lounge, the wishing tree). */
export const LAWN = /* glsl */ `
vec4 surface(vec2 uv, out float height) {
  float fine = fbmP(uv * 60.0, 60.0);
  float clover = smoothstep(0.55, 0.8, fbmP(uv * 12.0, 12.0));
  float blades = bladesP(uv, 30.0, 320.0, 0.55);
  height = blades * 0.7 + fine * 0.3;
  vec3 col = mix(vec3(0.07, 0.13, 0.04), vec3(0.17, 0.28, 0.08), blades * 0.7 + fine * 0.3);
  col = mix(col, vec3(0.12, 0.22, 0.07), clover * 0.5);
  return vec4(col, 0.85);
}
`;

/** Forest floor: leaf litter, twigs and dark earth (the candle grove, the oak hollow). */
export const LEAF_LITTER = /* glsl */ `
vec4 surface(vec2 uv, out float height) {
  vec3 leaves = voronoiP(uv * 22.0, 22.0, 5.0);
  vec3 leaves2 = voronoiP(uv * 40.0 + 0.5, 40.0, 6.0);
  float leaf = smoothstep(0.0, 0.1, leaves.y) * step(0.3, leaves.z);
  float leaf2 = smoothstep(0.0, 0.08, leaves2.y) * step(0.5, leaves2.z);
  float soil = fbmP(uv * 10.0, 10.0);
  height = max(leaf * (0.6 + 0.4 * leaves.z), leaf2 * 0.5) + soil * 0.15;
  vec3 earth = mix(vec3(0.07, 0.05, 0.035), vec3(0.15, 0.11, 0.07), soil);
  vec3 brown = mix(vec3(0.28, 0.16, 0.07), vec3(0.45, 0.3, 0.12), fract(leaves.z * 5.0));
  vec3 brown2 = mix(vec3(0.35, 0.22, 0.1), vec3(0.2, 0.12, 0.06), fract(leaves2.z * 3.0));
  vec3 col = mix(earth, brown, leaf);
  col = mix(col, brown2, leaf2 * (1.0 - leaf));
  return vec4(col * (0.85 + 0.3 * soil), 0.9);
}
`;

export function bakeSurface(
  renderer: WebGLRenderer,
  surfaceGlsl: string,
  size = 1024,
): SurfaceMaps {
  const cam = new OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const quad = new Mesh(new PlaneGeometry(2, 2));
  const opts = {
    type: UnsignedByteType,
    minFilter: LinearMipmapLinearFilter,
    magFilter: LinearFilter,
    wrapS: RepeatWrapping,
    wrapT: RepeatWrapping,
    generateMipmaps: true,
    depthBuffer: false,
  } as const;
  const albedoRT = new WebGLRenderTarget(size, size, opts);
  const heightRT = new WebGLRenderTarget(size, size, opts);
  const normalRT = new WebGLRenderTarget(size, size, opts);

  // 1. Colour + roughness, and height.
  const colourMat = new ShaderMaterial({
    vertexShader: VERT,
    fragmentShader: `${VORONOI}\n${surfaceGlsl}\nvarying vec2 vUv;
      uniform float uMode;
      void main() {
        float h;
        vec4 s = surface(vUv, h);
        gl_FragColor = uMode < 0.5 ? s : vec4(vec3(h), 1.0);
      }`,
    uniforms: { uMode: { value: 0 } },
  });
  quad.material = colourMat;
  const prev = renderer.getRenderTarget();
  renderer.setRenderTarget(albedoRT);
  renderer.render(quad, cam);
  colourMat.uniforms.uMode!.value = 1;
  renderer.setRenderTarget(heightRT);
  renderer.render(quad, cam);

  // 2. Normals from the height (wrapping, so seams match).
  const normalMat = new ShaderMaterial({
    vertexShader: VERT,
    fragmentShader: /* glsl */ `
      uniform sampler2D tHeight;
      uniform vec2 uTexel;
      uniform float uStrength;
      varying vec2 vUv;
      float h(vec2 o) { return texture2D(tHeight, fract(vUv + o * uTexel)).r; }
      void main() {
        float l = h(vec2(-1.0, 0.0)), r = h(vec2(1.0, 0.0));
        float d = h(vec2(0.0, -1.0)), u = h(vec2(0.0, 1.0));
        vec3 n = normalize(vec3((l - r) * uStrength, (d - u) * uStrength, 1.0));
        gl_FragColor = vec4(n * 0.5 + 0.5, h(vec2(0.0)));
      }`,
    uniforms: {
      tHeight: { value: heightRT.texture },
      uTexel: { value: new Vector2(1 / size, 1 / size) },
      uStrength: { value: 6 },
    },
  });
  quad.material = normalMat;
  renderer.setRenderTarget(normalRT);
  renderer.render(quad, cam);
  renderer.setRenderTarget(prev);

  colourMat.dispose();
  normalMat.dispose();
  quad.geometry.dispose();
  heightRT.dispose();
  albedoRT.texture.anisotropy = 8;
  normalRT.texture.anisotropy = 8;
  return { albedo: albedoRT.texture, normal: normalRT.texture };
}
