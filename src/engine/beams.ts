import {
  AdditiveBlending,
  type Color,
  InstancedBufferAttribute,
  InstancedBufferGeometry,
  Mesh,
  PlaneGeometry,
  ShaderMaterial,
  Vector2,
} from 'three';
import { NOISE, TERRAIN_PARS } from './glsl.ts';
import { shared } from './shared.ts';

/**
 * Light pouring down from above in soft slanting shafts (the sea's light, falling through the
 * water): a few tall planes that turn to face you about their own length, sway, waver and fade
 * toward the ground. They fill a box around the camera, wrapping as you walk, so there are always
 * some ahead. One draw call; blended additively.
 */
export class Beams {
  readonly mesh: Mesh<InstancedBufferGeometry, ShaderMaterial>;

  constructor(options: { count: number; box: number; height: number; color: Color; lean?: [number, number] }) {
    const plane = new PlaneGeometry(1, 1);
    plane.translate(0, 0.5, 0);
    const geo = new InstancedBufferGeometry();
    geo.index = plane.index;
    geo.setAttribute('position', plane.getAttribute('position'));
    geo.setAttribute('uv', plane.getAttribute('uv'));
    const at = new Float32Array(options.count * 4);
    for (let i = 0; i < options.count; i++) {
      at.set([Math.random() * options.box, Math.random() * options.box, 0.8 + Math.random() * 2.2, Math.random()], i * 4);
    }
    geo.setAttribute('aBeam', new InstancedBufferAttribute(at, 4));
    geo.instanceCount = options.count;
    const [lx, lz] = options.lean ?? [0.18, -0.08];
    this.mesh = new Mesh(
      geo,
      new ShaderMaterial({
        uniforms: {
          uHlTime: shared.uHlTime,
          uTerrain: shared.uTerrain,
          uTerrainBounds: shared.uTerrainBounds,
          uBox: { value: options.box },
          uHeight: { value: options.height },
          uColor: { value: options.color },
          uLean: { value: new Vector2(lx, lz) },
        },
        vertexShader: /* glsl */ `
          attribute vec4 aBeam; // x, z in the box, width, seed
          uniform float uHlTime;
          uniform float uBox;
          uniform float uHeight;
          uniform vec2 uLean;
          varying vec2 vUv;
          varying float vSeed;
          varying float vFade;
          ${NOISE}
          ${TERRAIN_PARS}
          void main() {
            vUv = uv;
            vSeed = aBeam.w;
            float t = uHlTime;
            vec3 c = cameraPosition - vec3(uBox * 0.5);
            vec2 base = mod(aBeam.xy + vec2(t * 0.05, t * 0.02) - c.xz, uBox) + c.xz;
            // Sways slowly at the top, as the surface moves.
            vec2 lean = uLean + 0.05 * vec2(sin(t * 0.21 + aBeam.w * 20.0), cos(t * 0.17 + aBeam.w * 13.0));
            float y = position.y * uHeight;
            vec3 axis = vec3(base.x, hlTerrain(base) - 0.5, base.y) + vec3(lean.x, 1.0, lean.y) * y;
            // Turned to face the camera about the shaft's own (nearly upright) length.
            vec3 toCam = cameraPosition - axis;
            vec3 side = normalize(cross(vec3(lean.x, 1.0, lean.y), toCam));
            vec3 p = axis + side * position.x * aBeam.z;
            // Gone near the edges of the box (no popping as they wrap) and right up close.
            vec2 rel = abs(base - cameraPosition.xz) / (uBox * 0.5);
            vFade = (1.0 - smoothstep(0.55, 1.0, max(rel.x, rel.y))) * smoothstep(1.5, 4.0, length(toCam.xz));
            gl_Position = projectionMatrix * viewMatrix * vec4(p, 1.0);
          }`,
        fragmentShader: /* glsl */ `
          uniform vec3 uColor;
          uniform float uHlTime;
          varying vec2 vUv;
          varying float vSeed;
          varying float vFade;
          ${NOISE}
          void main() {
            // Soft across, brightest toward the top, gone before it reaches the floor; ripples
            // run down it and it breathes brighter and dimmer.
            float ax = (vUv.x - 0.5) * 3.2;
            float across = exp(-ax * ax);
            float down = smoothstep(0.0, 0.35, vUv.y) * (0.45 + 0.55 * vUv.y);
            float ripple = 0.7 + 0.3 * hlNoise(vec2(vUv.x * 4.0 + vSeed * 9.0, vUv.y * 6.0 + uHlTime * 0.6));
            float breathe = 0.55 + 0.45 * sin(uHlTime * (0.3 + 0.2 * vSeed) + vSeed * 40.0);
            gl_FragColor = vec4(uColor * across * down * ripple * breathe * vFade, 1.0);
          }`,
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
      }),
    );
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = 7;
  }

  dispose() {
    this.mesh.geometry.dispose();
    this.mesh.material.dispose();
  }
}
