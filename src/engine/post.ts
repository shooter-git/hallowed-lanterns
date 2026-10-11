import {
  Color,
  type Camera,
  HalfFloatType,
  LinearFilter,
  Mesh,
  NoBlending,
  OneFactor,
  CustomBlending,
  AddEquation,
  OrthographicCamera,
  PlaneGeometry,
  type Scene,
  ShaderMaterial,
  type Texture,
  Vector2,
  Vector3,
  type WebGLRenderer,
  WebGLRenderTarget,
} from 'three';
import { AGX } from './glsl.ts';

/** How a chapter's picture is finished: exposure, bloom and colour grade. */
export interface Grade {
  exposure: number;
  bloom: number;
  /** AgX look: contrast slope, power and saturation. */
  slope: number;
  power: number;
  saturation: number;
  /** Colour balance multiplied in before tone mapping. */
  tint: Color;
  /** Display-space lift (shadows) colour, small values. */
  lift: Color;
  vignette: number;
  grain: number;
}

export const defaultGrade = (): Grade => ({
  exposure: 1,
  bloom: 0.06,
  slope: 1,
  power: 1.08,
  saturation: 1.12,
  tint: new Color(1, 1, 1),
  lift: new Color(0, 0, 0),
  vignette: 0.32,
  grain: 0.035,
});

const VERT = /* glsl */ `
varying vec2 vUv;
void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }
`;

// Call of Duty-style 13-tap downsample; the first pass averages by brightness so single
// bright pixels (a lantern's hot spot) don't flicker.
const DOWN = /* glsl */ `
uniform sampler2D tSrc;
uniform vec2 uTexel;
uniform float uFirst;
varying vec2 vUv;
vec3 s(vec2 o) { return texture2D(tSrc, vUv + o * uTexel).rgb; }
float w(vec3 c) { return 1.0 / (1.0 + dot(c, vec3(0.2126, 0.7152, 0.0722))); }
void main() {
  vec3 a = s(vec2(-2.0, 2.0)), b = s(vec2(0.0, 2.0)), c = s(vec2(2.0, 2.0));
  vec3 d = s(vec2(-2.0, 0.0)), e = s(vec2(0.0, 0.0)), f = s(vec2(2.0, 0.0));
  vec3 g = s(vec2(-2.0, -2.0)), h = s(vec2(0.0, -2.0)), i = s(vec2(2.0, -2.0));
  vec3 j = s(vec2(-1.0, 1.0)), k = s(vec2(1.0, 1.0)), l = s(vec2(-1.0, -1.0)), m = s(vec2(1.0, -1.0));
  vec3 g0 = (j + k + l + m) * 0.25;
  vec3 g1 = (a + b + d + e) * 0.25;
  vec3 g2 = (b + c + e + f) * 0.25;
  vec3 g3 = (d + e + g + h) * 0.25;
  vec3 g4 = (e + f + h + i) * 0.25;
  vec3 col;
  if (uFirst > 0.5) {
    float w0 = w(g0) * 0.5, w1 = w(g1) * 0.125, w2 = w(g2) * 0.125, w3 = w(g3) * 0.125, w4 = w(g4) * 0.125;
    col = (g0 * w0 + g1 * w1 + g2 * w2 + g3 * w3 + g4 * w4) / (w0 + w1 + w2 + w3 + w4);
  } else {
    col = g0 * 0.5 + (g1 + g2 + g3 + g4) * 0.125;
  }
  gl_FragColor = vec4(max(col, 0.0), 1.0);
}
`;

// 3x3 tent upsample, added onto the next larger mip.
const UP = /* glsl */ `
uniform sampler2D tSrc;
uniform vec2 uTexel;
uniform float uRadius;
varying vec2 vUv;
void main() {
  vec2 r = uTexel * uRadius;
  vec3 c = texture2D(tSrc, vUv).rgb * 4.0;
  c += (texture2D(tSrc, vUv + vec2(-r.x, 0.0)).rgb + texture2D(tSrc, vUv + vec2(r.x, 0.0)).rgb
      + texture2D(tSrc, vUv + vec2(0.0, -r.y)).rgb + texture2D(tSrc, vUv + vec2(0.0, r.y)).rgb) * 2.0;
  c += texture2D(tSrc, vUv + vec2(-r.x, -r.y)).rgb + texture2D(tSrc, vUv + vec2(r.x, -r.y)).rgb
     + texture2D(tSrc, vUv + vec2(-r.x, r.y)).rgb + texture2D(tSrc, vUv + vec2(r.x, r.y)).rgb;
  gl_FragColor = vec4(c / 16.0, 1.0);
}
`;

const COMPOSITE = /* glsl */ `
uniform sampler2D tScene;
uniform sampler2D tBloom;
uniform float uBloom;
uniform float uExposure;
uniform float uSlope;
uniform float uPower;
uniform float uSat;
uniform vec3 uTint;
uniform vec3 uLift;
uniform float uVignette;
uniform float uGrain;
uniform float uTime;
uniform vec2 uRes;
uniform float uFade;
uniform vec3 uFadeColor;
varying vec2 vUv;
${AGX}
float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
void main() {
  vec3 c = texture2D(tScene, vUv).rgb;
  vec3 b = texture2D(tBloom, vUv).rgb;
  c = c + b * uBloom;
  c *= uExposure * uTint;
  // Fades go through the light (a chapter dissolving into fog), before tone mapping.
  c = mix(c, uFadeColor, uFade);
  vec2 q = vUv - 0.5;
  q.x *= uRes.x / uRes.y;
  float vig = 1.0 - uVignette * smoothstep(0.25, 1.05, length(q) * 1.15);
  c *= vig;
  c = hlAgx(c, uSlope, uPower, uSat);
  c = c + uLift * (1.0 - c);
  // sRGB encode.
  c = mix(c * 12.92, 1.055 * pow(max(c, 0.0), vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c));
  // Film grain (stronger in the shadows) and dithering against banding.
  float n = hash(vUv * uRes + fract(uTime * 7.31) * 100.0) - 0.5;
  float lum = dot(c, vec3(0.299, 0.587, 0.114));
  c += n * (uGrain * (1.0 - lum) + 1.5 / 255.0);
  gl_FragColor = vec4(c, 1.0);
}
`;

/**
 * Renders the scene in high dynamic range, then blooms, grades and tone-maps it to the screen.
 * About a dozen small full-screen passes: cheap enough for a phone.
 */
export class Post {
  readonly grade: Grade = defaultGrade();
  /** 0 = clear, 1 = fully faded to `fadeColor` (in scene light units). */
  fade = 0;
  readonly fadeColor = new Color(0, 0, 0);
  /** Draw calls and triangles of the last scene pass (for checking the budget). */
  readonly stats = { calls: 0, triangles: 0 };

  private readonly target: WebGLRenderTarget;
  private readonly mips: WebGLRenderTarget[] = [];
  private readonly quad: Mesh;
  private readonly cam = new OrthographicCamera(-1, 1, 1, -1, 0, 1);
  private readonly down: ShaderMaterial;
  private readonly up: ShaderMaterial;
  private readonly composite: ShaderMaterial;
  private readonly size = new Vector2();

  constructor(
    private readonly renderer: WebGLRenderer,
    private readonly options: { samples: number; levels: number },
  ) {
    this.target = new WebGLRenderTarget(1, 1, {
      type: HalfFloatType,
      samples: options.samples,
      minFilter: LinearFilter,
      magFilter: LinearFilter,
      depthBuffer: true,
    });
    for (let i = 0; i < options.levels; i++) {
      this.mips.push(
        new WebGLRenderTarget(1, 1, {
          type: HalfFloatType,
          minFilter: LinearFilter,
          magFilter: LinearFilter,
          depthBuffer: false,
        }),
      );
    }
    this.down = new ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: DOWN,
      uniforms: { tSrc: { value: null }, uTexel: { value: new Vector2() }, uFirst: { value: 0 } },
      blending: NoBlending,
      depthTest: false,
      depthWrite: false,
    });
    this.up = new ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: UP,
      uniforms: { tSrc: { value: null }, uTexel: { value: new Vector2() }, uRadius: { value: 1 } },
      blending: CustomBlending,
      blendEquation: AddEquation,
      blendSrc: OneFactor,
      blendDst: OneFactor,
      depthTest: false,
      depthWrite: false,
    });
    this.composite = new ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: COMPOSITE,
      uniforms: {
        tScene: { value: this.target.texture },
        tBloom: { value: null },
        uBloom: { value: 0.05 },
        uExposure: { value: 1 },
        uSlope: { value: 1 },
        uPower: { value: 1 },
        uSat: { value: 1 },
        uTint: { value: new Vector3(1, 1, 1) },
        uLift: { value: new Vector3() },
        uVignette: { value: 0.3 },
        uGrain: { value: 0.03 },
        uTime: { value: 0 },
        uRes: { value: new Vector2(1, 1) },
        uFade: { value: 0 },
        uFadeColor: { value: new Vector3() },
      },
      depthTest: false,
      depthWrite: false,
    });
    this.quad = new Mesh(new PlaneGeometry(2, 2), this.composite);
    this.quad.frustumCulled = false;
  }

  /** The HDR scene buffer (for effects that want to read last frame's picture). */
  get sceneTexture(): Texture {
    return this.target.texture;
  }

  private resize() {
    this.renderer.getDrawingBufferSize(this.size);
    const w = Math.max(1, Math.floor(this.size.x));
    const h = Math.max(1, Math.floor(this.size.y));
    if (this.target.width === w && this.target.height === h) return;
    this.target.setSize(w, h);
    let mw = w;
    let mh = h;
    for (const m of this.mips) {
      mw = Math.max(1, Math.floor(mw / 2));
      mh = Math.max(1, Math.floor(mh / 2));
      m.setSize(mw, mh);
    }
  }

  render(scene: Scene, camera: Camera, time: number) {
    const r = this.renderer;
    this.resize();
    r.setRenderTarget(this.target);
    r.render(scene, camera);
    this.stats.calls = r.info.render.calls;
    this.stats.triangles = r.info.render.triangles;

    // Bloom: down the mip chain, then back up adding each level onto the next.
    let src: Texture = this.target.texture;
    let sw = this.target.width;
    let sh = this.target.height;
    this.quad.material = this.down;
    for (let i = 0; i < this.mips.length; i++) {
      const m = this.mips[i] as WebGLRenderTarget;
      this.down.uniforms.tSrc!.value = src;
      (this.down.uniforms.uTexel!.value as Vector2).set(1 / sw, 1 / sh);
      this.down.uniforms.uFirst!.value = i === 0 ? 1 : 0;
      r.setRenderTarget(m);
      r.render(this.quad, this.cam);
      src = m.texture;
      sw = m.width;
      sh = m.height;
    }
    this.quad.material = this.up;
    const auto = r.autoClear;
    r.autoClear = false;
    for (let i = this.mips.length - 1; i > 0; i--) {
      const from = this.mips[i] as WebGLRenderTarget;
      const to = this.mips[i - 1] as WebGLRenderTarget;
      this.up.uniforms.tSrc!.value = from.texture;
      (this.up.uniforms.uTexel!.value as Vector2).set(1 / from.width, 1 / from.height);
      r.setRenderTarget(to);
      r.render(this.quad, this.cam);
    }
    r.autoClear = auto;

    const g = this.grade;
    const u = this.composite.uniforms;
    u.tBloom!.value = (this.mips[0] as WebGLRenderTarget).texture;
    u.uBloom!.value = g.bloom;
    u.uExposure!.value = g.exposure;
    u.uSlope!.value = g.slope;
    u.uPower!.value = g.power;
    u.uSat!.value = g.saturation;
    (u.uTint!.value as Vector3).set(g.tint.r, g.tint.g, g.tint.b);
    (u.uLift!.value as Vector3).set(g.lift.r, g.lift.g, g.lift.b);
    u.uVignette!.value = g.vignette;
    u.uGrain!.value = g.grain;
    u.uTime!.value = time;
    (u.uRes!.value as Vector2).set(this.target.width, this.target.height);
    u.uFade!.value = this.fade;
    (u.uFadeColor!.value as Vector3).set(this.fadeColor.r, this.fadeColor.g, this.fadeColor.b);
    this.quad.material = this.composite;
    r.setRenderTarget(null);
    r.render(this.quad, this.cam);
  }

  dispose() {
    this.target.dispose();
    for (const m of this.mips) m.dispose();
    this.down.dispose();
    this.up.dispose();
    this.composite.dispose();
    this.quad.geometry.dispose();
  }
}

/** Blends one grade toward another (for chapter transitions and time-of-day changes). */
export function lerpGrade(out: Grade, a: Grade, b: Grade, t: number) {
  const l = (x: number, y: number) => x + (y - x) * t;
  out.exposure = l(a.exposure, b.exposure);
  out.bloom = l(a.bloom, b.bloom);
  out.slope = l(a.slope, b.slope);
  out.power = l(a.power, b.power);
  out.saturation = l(a.saturation, b.saturation);
  out.tint.copy(a.tint).lerp(b.tint, t);
  out.lift.copy(a.lift).lerp(b.lift, t);
  out.vignette = l(a.vignette, b.vignette);
  out.grain = l(a.grain, b.grain);
}
