import {
  AddEquation,
  type Color,
  CustomBlending,
  DynamicDrawUsage,
  HalfFloatType,
  InstancedBufferAttribute,
  InstancedBufferGeometry,
  LinearFilter,
  Mesh,
  OneFactor,
  OrthographicCamera,
  PlaneGeometry,
  Scene,
  ShaderMaterial,
  Vector4,
  type WebGLRenderer,
  WebGLRenderTarget,
} from 'three';
import { NOISE } from './glsl.ts';
import { shared } from './shared.ts';

export interface GlowLight {
  x: number;
  z: number;
  /** How far its light reaches across the ground (m). */
  radius: number;
  color: Color;
  /** Brightness (linear light units at the centre). */
  intensity: number;
  /** Flicker phase (0–1); match the lantern's own so they flicker together. */
  phase?: number;
  /** 0 = steady (an LED), 1 = a candle. */
  flicker?: number;
  /** Order in which a "wave" lights it (see `wave`); leave out to be always on. */
  seq?: number;
  /**
   * How high it hangs above the ground (m): surfaces well above or below it get less of its
   * light (a string of lights in the grass doesn't light the treetops). 1.5 if left out.
   */
  y?: number;
}

/** Height of a glow light that doesn't say. */
const DEFAULT_Y = 1.5;

/**
 * Lantern light pooled into a top-down texture each frame: every light is a soft additive splat,
 * and the alpha gathers how high the light at each spot hangs. Every material samples it (see
 * `hlGlow`), so hundreds of lanterns light the ground, the fog and each other for the cost of one
 * draw call.
 */
export class GlowField {
  /** Lights whose `seq` is below this are on (fading in over `waveSoftness`). */
  wave = 1e9;
  waveSoftness = 2;
  private readonly target: WebGLRenderTarget;
  private readonly scene = new Scene();
  private readonly camera = new OrthographicCamera(-1, 1, 1, -1, 0, 1);
  private readonly material: ShaderMaterial;
  private mesh: Mesh<InstancedBufferGeometry, ShaderMaterial> | null = null;
  private levels: InstancedBufferAttribute | null = null;
  private count = 0;
  private readonly bounds = new Vector4(0, 0, 1, 1);
  /** Lights that move (the Ember, a swinging lantern): re-uploaded every frame. Up to 16. */
  readonly moving: GlowLight[] = [];
  private movingMesh: Mesh<InstancedBufferGeometry, ShaderMaterial> | null = null;

  constructor(size: number) {
    this.target = new WebGLRenderTarget(size, size, {
      type: HalfFloatType,
      minFilter: LinearFilter,
      magFilter: LinearFilter,
      depthBuffer: false,
    });
    this.material = new ShaderMaterial({
      uniforms: {
        uBounds: { value: this.bounds },
        uTime: shared.uHlTime,
        uWave: { value: 1e9 },
        uWaveSoft: { value: 2 },
      },
      vertexShader: /* glsl */ `
        attribute vec4 aLight;   // x, z, radius, height
        attribute vec4 aColor;   // rgb * intensity, phase
        attribute vec3 aMore;    // flicker, seq, level
        uniform vec4 uBounds;
        uniform float uTime;
        uniform float uWave;
        uniform float uWaveSoft;
        varying vec2 vC;
        varying vec3 vCol;
        varying float vY;
        ${NOISE}
        void main() {
          vec2 c = aLight.xy + position.xy * aLight.z;
          vec2 uv = (c - uBounds.xy) / uBounds.zw;
          gl_Position = vec4(uv * 2.0 - 1.0, 0.0, 1.0);
          vC = position.xy;
          vY = aLight.w;
          float on = clamp((uWave - aMore.y) / uWaveSoft, 0.0, 1.0);
          float fl = mix(1.0, hlFlicker(uTime, aColor.w), aMore.x);
          vCol = aColor.rgb * fl * on * aMore.z;
        }`,
      fragmentShader: /* glsl */ `
        varying vec2 vC;
        varying vec3 vCol;
        varying float vY;
        void main() {
          float d = dot(vC, vC);
          float a = max(0.0, 1.0 - d);
          // Soft edge, bright core: roughly inverse-square near the light, smooth to zero at the edge.
          a = a * a / (1.0 + 10.0 * d);
          vec3 c = vCol * a;
          // Alpha gathers each light's height, weighted by its brightness (hlGlow divides it out).
          gl_FragColor = vec4(c, dot(c, vec3(0.2126, 0.7152, 0.0722)) * vY);
        }`,
      blending: CustomBlending,
      blendEquation: AddEquation,
      blendSrc: OneFactor,
      blendDst: OneFactor,
      depthTest: false,
      depthWrite: false,
    });
    shared.uGlowMap.value = this.target.texture;
  }

  /** The area covered (world x/z). Lights outside it are lost. */
  setBounds(minX: number, minZ: number, sizeX: number, sizeZ: number) {
    this.bounds.set(minX, minZ, sizeX, sizeZ);
    shared.uGlowBounds.value.copy(this.bounds);
  }

  /** Replaces all the lights. */
  setLights(lights: GlowLight[]) {
    this.mesh?.geometry.dispose();
    if (this.mesh) this.scene.remove(this.mesh);
    this.count = lights.length;
    const geo = new InstancedBufferGeometry();
    const plane = new PlaneGeometry(2, 2);
    geo.index = plane.index;
    geo.setAttribute('position', plane.getAttribute('position'));
    const light = new Float32Array(lights.length * 4);
    const color = new Float32Array(lights.length * 4);
    const more = new Float32Array(lights.length * 3);
    lights.forEach((l, i) => {
      light.set([l.x, l.z, l.radius, l.y ?? DEFAULT_Y], i * 4);
      color.set(
        [l.color.r * l.intensity, l.color.g * l.intensity, l.color.b * l.intensity, l.phase ?? 0],
        i * 4,
      );
      more.set([l.flicker ?? 0, l.seq ?? -1e9, 1], i * 3);
    });
    geo.setAttribute('aLight', new InstancedBufferAttribute(light, 4));
    geo.setAttribute('aColor', new InstancedBufferAttribute(color, 4));
    this.levels = new InstancedBufferAttribute(more, 3);
    this.levels.setUsage(DynamicDrawUsage);
    geo.setAttribute('aMore', this.levels);
    geo.instanceCount = lights.length;
    this.mesh = new Mesh(geo, this.material);
    this.mesh.frustumCulled = false;
    this.scene.add(this.mesh);
  }

  private uploadMoving() {
    if (!this.movingMesh) {
      const geo = new InstancedBufferGeometry();
      const plane = new PlaneGeometry(2, 2);
      geo.index = plane.index;
      geo.setAttribute('position', plane.getAttribute('position'));
      for (const [name, size] of [
        ['aLight', 4],
        ['aColor', 4],
        ['aMore', 3],
      ] as const) {
        const a = new InstancedBufferAttribute(new Float32Array(16 * size), size);
        a.setUsage(DynamicDrawUsage);
        geo.setAttribute(name, a);
      }
      this.movingMesh = new Mesh(geo, this.material);
      this.movingMesh.frustumCulled = false;
      this.scene.add(this.movingMesh);
    }
    const geo = this.movingMesh.geometry;
    const light = geo.getAttribute('aLight') as InstancedBufferAttribute;
    const color = geo.getAttribute('aColor') as InstancedBufferAttribute;
    const more = geo.getAttribute('aMore') as InstancedBufferAttribute;
    const n = Math.min(16, this.moving.length);
    for (let i = 0; i < n; i++) {
      const l = this.moving[i] as GlowLight;
      light.setXYZW(i, l.x, l.z, l.radius, l.y ?? DEFAULT_Y);
      color.setXYZW(i, l.color.r * l.intensity, l.color.g * l.intensity, l.color.b * l.intensity, l.phase ?? 0);
      more.setXYZ(i, l.flicker ?? 0, l.seq ?? -1e9, 1);
    }
    light.needsUpdate = color.needsUpdate = more.needsUpdate = true;
    geo.instanceCount = n;
  }

  /** Dims or brightens one light (1 = as added). */
  setLevel(index: number, level: number) {
    if (!this.levels || index < 0 || index >= this.count) return;
    this.levels.setZ(index, level);
    this.levels.needsUpdate = true;
  }

  render(renderer: WebGLRenderer) {
    this.material.uniforms.uWave!.value = this.wave;
    this.material.uniforms.uWaveSoft!.value = this.waveSoftness;
    const prev = renderer.getRenderTarget();
    renderer.setRenderTarget(this.target);
    renderer.setClearColor(0x000000, 0);
    renderer.clear(true, false, false);
    renderer.setClearColor(0x000000, 1);
    this.uploadMoving();
    if (this.count || this.moving.length) renderer.render(this.scene, this.camera);
    renderer.setRenderTarget(prev);
  }

  dispose() {
    this.target.dispose();
    this.material.dispose();
    this.mesh?.geometry.dispose();
    this.movingMesh?.geometry.dispose();
  }
}
