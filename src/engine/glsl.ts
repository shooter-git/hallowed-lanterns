/**
 * Shader snippets shared by every material: noise, the glow field (lantern light pooled into a
 * top-down texture), height fog lit by that glow, candle flicker and AgX tone mapping.
 */

/** Hash and value/gradient noise, cheap enough for phones. */
export const NOISE = /* glsl */ `
float hlHash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}
vec2 hlHash22(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.xx + p3.yz) * p3.zy);
}
float hlNoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hlHash12(i), hlHash12(i + vec2(1.0, 0.0)), u.x),
             mix(hlHash12(i + vec2(0.0, 1.0)), hlHash12(i + vec2(1.0, 1.0)), u.x), u.y);
}
float hlFbm(vec2 p) {
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 4; i++) {
    v += a * hlNoise(p);
    p = mat2(1.6, 1.2, -1.2, 1.6) * p;
    a *= 0.5;
  }
  return v;
}
// A candle's flicker: mostly steady, with small fast wobbles and the odd gust.
float hlFlicker(float t, float phase) {
  float f = 0.82
    + 0.07 * sin(t * 7.3 + phase * 6.28)
    + 0.05 * sin(t * 13.1 + phase * 17.0)
    + 0.04 * sin(t * 2.1 + phase * 3.0);
  float gust = hlNoise(vec2(t * 1.7, phase * 31.0));
  f -= 0.18 * smoothstep(0.82, 1.0, gust);
  return f;
}
`;

/** Glow field + fog. Needs `vHlWorld` (the fragment's world position) and three's `cameraPosition`. */
export const GLOW_FOG_PARS = /* glsl */ `
uniform sampler2D uGlowMap;
uniform vec4 uGlowBounds;
uniform float uGlowGain;
uniform vec3 uFogColor;
uniform float uFogDensity;
uniform float uFogHeight;
uniform float uFogGlow;
uniform float uHlTime;

vec3 hlGlow(vec3 wp) {
  vec2 uv = (wp.xz - uGlowBounds.xy) / uGlowBounds.zw;
  vec2 inside = step(vec2(0.0), uv) * step(uv, vec2(1.0));
  // Lanterns hang overhead: surfaces nearer their height catch more of their light.
  float lift = 1.0 + 0.6 * clamp(wp.y / 3.0, 0.0, 1.0);
  return texture2D(uGlowMap, uv).rgb * (inside.x * inside.y) * uGlowGain * lift;
}

vec3 hlApplyFog(vec3 col, vec3 wp) {
  vec3 ray = wp - cameraPosition;
  float d = length(ray);
  float k = 1.0 / uFogHeight;
  float y0 = max(cameraPosition.y, -1.0);
  float y1 = max(wp.y, -1.0);
  float dy = y1 - y0;
  // Mean density of exponential height fog along the ray.
  float mean = abs(dy) > 0.01 ? (exp(-k * y0) - exp(-k * y1)) / (k * dy) : exp(-k * y0);
  float f = 1.0 - exp(-uFogDensity * d * mean);
  // The fog is lit by the lanterns it passes: sample the glow along the ray.
  vec3 lit = (hlGlow(cameraPosition + ray * 0.2) + hlGlow(cameraPosition + ray * 0.5) + hlGlow(wp)) * (uFogGlow / 3.0);
  return mix(col, uFogColor + lit, f);
}
`;

/** Puts the world position in `vHlWorld` (after `#include <project_vertex>`). Handles instancing. */
export const WORLD_POS_VERTEX = /* glsl */ `
{
  vec4 hlWp = vec4(transformed, 1.0);
  #ifdef USE_BATCHING
    hlWp = batchingMatrix * hlWp;
  #endif
  #ifdef USE_INSTANCING
    hlWp = instanceMatrix * hlWp;
  #endif
  vHlWorld = (modelMatrix * hlWp).xyz;
}
`;

/** AgX (Blender/Filament) with a "look": slope, power and saturation applied in log space. */
export const AGX = /* glsl */ `
const mat3 HL_SRGB_TO_2020 = mat3(
  vec3(0.6274, 0.0691, 0.0164),
  vec3(0.3293, 0.9195, 0.0880),
  vec3(0.0433, 0.0113, 0.8956));
const mat3 HL_2020_TO_SRGB = mat3(
  vec3(1.6605, -0.1246, -0.0182),
  vec3(-0.5876, 1.1329, -0.1006),
  vec3(-0.0728, -0.0083, 1.1187));
const mat3 HL_AGX_INSET = mat3(
  vec3(0.856627153315983, 0.137318972929847, 0.11189821299995),
  vec3(0.0951212405381588, 0.761241990602591, 0.0767994186031903),
  vec3(0.0482516061458583, 0.101439036467562, 0.811302368396859));
const mat3 HL_AGX_OUTSET = mat3(
  vec3(1.1271005818144368, -0.1413297634984383, -0.14132976349843826),
  vec3(-0.11060664309660323, 1.157823702216272, -0.11060664309660294),
  vec3(-0.016493938717834573, -0.016493938717834257, 1.2519364065950405));
vec3 hlAgxContrast(vec3 x) {
  vec3 x2 = x * x;
  vec3 x4 = x2 * x2;
  return 15.5 * x4 * x2 - 40.14 * x4 * x + 31.96 * x4 - 6.868 * x2 * x + 0.4298 * x2 + 0.1191 * x - 0.00232;
}
vec3 hlAgx(vec3 color, float slope, float power, float sat) {
  color = HL_AGX_INSET * (HL_SRGB_TO_2020 * color);
  color = max(color, 1e-10);
  color = clamp((log2(color) + 12.47393) / 16.5, 0.0, 1.0);
  color = hlAgxContrast(color);
  // Look (ASC CDL-style).
  color = pow(max(color * slope, 0.0), vec3(power));
  float luma = dot(color, vec3(0.2126, 0.7152, 0.0722));
  color = luma + sat * (color - luma);
  color = HL_AGX_OUTSET * color;
  color = pow(max(vec3(0.0), color), vec3(2.2));
  return clamp(HL_2020_TO_SRGB * color, 0.0, 1.0);
}
`;
