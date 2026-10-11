import {
  Color,
  DataTexture,
  HalfFloatType,
  type Material,
  RGBAFormat,
  type Texture,
  Vector4,
  type WebGLProgramParametersWithUniforms,
} from 'three';
import { GLOW_FOG_PARS, NOISE, WORLD_POS_VERTEX } from './glsl.ts';

const black = new DataTexture(new Uint16Array(4), 1, 1, RGBAFormat, HalfFloatType);
black.needsUpdate = true;

/**
 * Uniforms every material shares (the same objects, so setting one updates them all): the glow
 * field, the fog, and the time.
 */
export const shared = {
  uGlowMap: { value: black as Texture },
  /** minX, minZ, sizeX, sizeZ of the area the glow field covers. */
  uGlowBounds: { value: new Vector4(-50, -50, 100, 100) },
  uGlowGain: { value: 1 },
  uFogColor: { value: new Color(0.02, 0.02, 0.03) },
  uFogDensity: { value: 0.02 },
  /** Height (m) over which the fog thins by e. */
  uFogHeight: { value: 4 },
  /** How much the lanterns light the fog. */
  uFogGlow: { value: 0.6 },
  uHlTime: { value: 0 },
};

export interface HallowOptions {
  /** How strongly the surface is lit by the glow field (default 1). */
  glow?: number;
  /** Extra GLSL in the fragment shader's declarations. */
  fragmentPars?: string;
  /** Extra GLSL in the vertex shader's declarations. */
  vertexPars?: string;
  /** Replacements applied to the vertex shader: [find, replace]. */
  vertex?: [string, string][];
  /** Replacements applied to the fragment shader: [find, replace]. */
  fragment?: [string, string][];
  /** Extra uniforms. */
  uniforms?: Record<string, { value: unknown }>;
  /** Distinguishes compiled programs that differ only in these patches. */
  key: string;
}

/**
 * Makes one of three's built-in materials part of this world: lit by the glow field, fogged by
 * our height fog (lit by the lanterns), and optionally patched further.
 */
export function hallow<T extends Material>(material: T, options: HallowOptions): T {
  const glow = (options.glow ?? 1).toFixed(3);
  material.onBeforeCompile = (shader: WebGLProgramParametersWithUniforms) => {
    Object.assign(shader.uniforms, shared, options.uniforms ?? {});
    let vs = shader.vertexShader
      .replace(
        '#include <common>',
        `#include <common>\nvarying vec3 vHlWorld;\nuniform float uHlTime;\n${NOISE}\n${options.vertexPars ?? ''}`,
      )
      .replace('#include <fog_vertex>', `#include <fog_vertex>\n${WORLD_POS_VERTEX}`);
    for (const [a, b] of options.vertex ?? []) vs = vs.replace(a, b);
    let fs = shader.fragmentShader
      .replace(
        '#include <common>',
        `#include <common>\nvarying vec3 vHlWorld;\n${NOISE}\n${GLOW_FOG_PARS}\n${options.fragmentPars ?? ''}`,
      )
      .replace(
        '#include <lights_fragment_end>',
        `#include <lights_fragment_end>\nreflectedLight.indirectDiffuse += diffuseColor.rgb * hlGlow(vHlWorld) * ${glow};`,
      )
      .replace('#include <fog_fragment>', 'gl_FragColor.rgb = hlApplyFog(gl_FragColor.rgb, vHlWorld);');
    for (const [a, b] of options.fragment ?? []) fs = fs.replace(a, b);
    shader.vertexShader = vs;
    shader.fragmentShader = fs;
  };
  material.customProgramCacheKey = () => `hallow:${options.key}:${glow}`;
  return material;
}

/** Declarations a hand-written ShaderMaterial needs to use the glow and fog. */
export const SHADER_PARS = `${NOISE}\n${GLOW_FOG_PARS}`;
