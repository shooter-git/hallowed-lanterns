import {
  AdditiveBlending,
  BufferGeometry,
  CanvasTexture,
  Color,
  Float32BufferAttribute,
  InstancedBufferAttribute,
  InstancedBufferGeometry,
  Mesh,
  NormalBlending,
  PlaneGeometry,
  Points,
  ShaderMaterial,
  SRGBColorSpace,
  type Texture,
  Vector3,
} from 'three';
import { SHADER_PARS, shared } from './shared.ts';

/**
 * Things drifting in the air all around you — snowflakes, bubbles, pollen, dust in the light:
 * points in a box that wraps around the camera, so they never run out. The drift velocity can
 * change at any moment (snow that slows, stops and starts to rise).
 */
export class Drift {
  readonly points: Points<BufferGeometry, ShaderMaterial>;
  /** m/s; change it freely. */
  readonly velocity = new Vector3(0, -0.6, 0);
  private readonly offset = new Vector3();

  constructor(options: { count: number; box: number; size: number; color: Color; style: 'snow' | 'bubble' | 'mote'; opacity?: number }) {
    const pos = new Float32Array(options.count * 3);
    const seed = new Float32Array(options.count);
    for (let i = 0; i < options.count; i++) {
      pos.set([Math.random() * options.box, Math.random() * options.box, Math.random() * options.box], i * 3);
      seed[i] = Math.random();
    }
    const geo = new BufferGeometry();
    geo.setAttribute('position', new Float32BufferAttribute(pos, 3));
    geo.setAttribute('aSeed', new Float32BufferAttribute(seed, 1));
    const bubble = options.style === 'bubble';
    const material = new ShaderMaterial({
      uniforms: {
        ...shared,
        uOffset: { value: this.offset },
        uBox: { value: options.box },
        uSize: { value: options.size },
        uScale: { value: 600 },
        uColor: { value: options.color },
        uOpacity: { value: options.opacity ?? 1 },
      },
      vertexShader: /* glsl */ `
        attribute float aSeed;
        uniform vec3 uOffset;
        uniform float uBox;
        uniform float uSize;
        uniform float uScale;
        uniform float uHlTime;
        varying float vSeed;
        varying vec3 vHlWorld;
        varying float vFade;
        void main() {
          vSeed = aSeed;
          float t = uHlTime;
          vec3 p = position + uOffset * (0.7 + aSeed * 0.6);
          // Each flake sways on its own little path.
          p.x += sin(t * (0.6 + aSeed) + aSeed * 40.0) * 0.35;
          p.z += cos(t * (0.5 + aSeed * 0.8) + aSeed * 17.0) * 0.35;
          vec3 c = cameraPosition - vec3(uBox * 0.5);
          vec3 w = mod(p - c, uBox) + c;
          vHlWorld = w;
          vec4 mv = viewMatrix * vec4(w, 1.0);
          // Fade out at the edges of the box so the wrap never shows.
          vec3 rel = abs(w - cameraPosition) / (uBox * 0.5);
          vFade = 1.0 - smoothstep(0.7, 1.0, max(rel.x, max(rel.y, rel.z)));
          gl_PointSize = uSize * (0.6 + aSeed * 0.8) * uScale / max(-mv.z, 0.1);
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: /* glsl */ `
        ${SHADER_PARS}
        uniform vec3 uColor;
        uniform float uOpacity;
        varying float vSeed;
        varying float vFade;
        varying vec3 vHlWorld;
        void main() {
          vec2 q = gl_PointCoord - 0.5;
          float d = length(q);
          ${
            bubble
              ? `float ring = smoothstep(0.5, 0.42, d) * smoothstep(0.28, 0.44, d);
                 float glint = smoothstep(0.12, 0.0, length(q - vec2(-0.16, -0.16)));
                 float a = (ring * 0.7 + glint) * vFade * uOpacity;
                 vec3 col = uColor * (0.6 + hlGlow(vHlWorld) * 1.5) + glint;`
              : `float a = smoothstep(0.5, 0.1, d) * vFade * uOpacity;
                 vec3 col = uColor + hlGlow(vHlWorld) * 0.8;`
          }
          if (a < 0.01) discard;
          col = hlApplyFog(col, vHlWorld);
          gl_FragColor = vec4(col, a);
        }`,
      transparent: true,
      depthWrite: false,
      blending: NormalBlending,
    });
    this.points = new Points(geo, material);
    this.points.frustumCulled = false;
    this.points.renderOrder = 8;
  }

  update(dt: number, pixelScale: number) {
    this.offset.addScaledVector(this.velocity, dt);
    this.points.material.uniforms.uScale!.value = pixelScale;
  }

  set opacity(v: number) {
    this.points.material.uniforms.uOpacity!.value = v;
  }

  dispose() {
    this.points.geometry.dispose();
    this.points.material.dispose();
  }
}

/** A six-armed snowflake ornament, drawn once. */
export function snowflakeTexture(): CanvasTexture {
  const s = 256;
  const c = document.createElement('canvas');
  c.width = c.height = s;
  const g = c.getContext('2d') as CanvasRenderingContext2D;
  g.translate(s / 2, s / 2);
  g.strokeStyle = '#fff';
  g.lineCap = 'round';
  g.shadowColor = 'rgba(200,230,255,1)';
  g.shadowBlur = 10;
  for (let k = 0; k < 6; k++) {
    g.save();
    g.rotate((k * Math.PI) / 3);
    g.lineWidth = 9;
    g.beginPath();
    g.moveTo(0, 0);
    g.lineTo(0, -110);
    g.stroke();
    g.lineWidth = 6;
    for (const [y, l] of [
      [-40, 26],
      [-70, 22],
      [-95, 14],
    ] as [number, number][]) {
      g.beginPath();
      g.moveTo(0, y);
      g.lineTo(-l, y - l);
      g.moveTo(0, y);
      g.lineTo(l, y - l);
      g.stroke();
    }
    g.restore();
  }
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  return t;
}

/** Camera-facing glowing cards (snowflake ornaments, butterflies' glints…), one draw call. */
export class Billboards {
  readonly mesh: Mesh<InstancedBufferGeometry, ShaderMaterial>;
  private readonly colors: InstancedBufferAttribute;

  constructor(items: { position: Vector3; size: number; color: Color; spin?: number }[], texture: Texture) {
    const plane = new PlaneGeometry(1, 1);
    const geo = new InstancedBufferGeometry();
    geo.index = plane.index;
    geo.setAttribute('position', plane.getAttribute('position'));
    geo.setAttribute('uv', plane.getAttribute('uv'));
    const at = new Float32Array(items.length * 4);
    const col = new Float32Array(items.length * 4);
    items.forEach((it, i) => {
      at.set([it.position.x, it.position.y, it.position.z, it.size], i * 4);
      col.set([it.color.r, it.color.g, it.color.b, it.spin ?? 0], i * 4);
    });
    geo.setAttribute('aAt', new InstancedBufferAttribute(at, 4));
    this.colors = new InstancedBufferAttribute(col, 4);
    geo.setAttribute('aCol', this.colors);
    geo.instanceCount = items.length;
    this.mesh = new Mesh(
      geo,
      new ShaderMaterial({
        uniforms: { ...shared, tMap: { value: texture } },
        vertexShader: /* glsl */ `
          attribute vec4 aAt;
          attribute vec4 aCol;
          uniform float uHlTime;
          varying vec2 vUv;
          varying vec3 vCol;
          varying vec3 vHlWorld;
          void main() {
            vUv = uv;
            vCol = aCol.rgb;
            float a = uHlTime * aCol.w;
            vec2 r = mat2(cos(a), -sin(a), sin(a), cos(a)) * position.xy * aAt.w;
            vec4 mv = viewMatrix * vec4(aAt.xyz, 1.0);
            mv.xy += r;
            vHlWorld = aAt.xyz;
            gl_Position = projectionMatrix * mv;
          }`,
        fragmentShader: /* glsl */ `
          ${SHADER_PARS}
          uniform sampler2D tMap;
          varying vec2 vUv;
          varying vec3 vCol;
          varying vec3 vHlWorld;
          void main() {
            vec4 t = texture2D(tMap, vUv);
            vec3 c = vCol * t.rgb * t.a;
            gl_FragColor = vec4(c, 1.0);
          }`,
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
      }),
    );
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = 9;
  }

  setColor(index: number, c: Color) {
    this.colors.setXYZ(index, c.r, c.g, c.b);
    this.colors.needsUpdate = true;
  }

  dispose() {
    this.mesh.geometry.dispose();
    this.mesh.material.dispose();
  }
}

/**
 * Your breath on a cold night: a small soft cloud that drifts up from just below your eyes and
 * fades, every few seconds.
 */
export class Breath {
  readonly mesh: Mesh<PlaneGeometry, ShaderMaterial>;
  private t = 10;

  constructor() {
    this.mesh = new Mesh(
      new PlaneGeometry(0.5, 0.5),
      new ShaderMaterial({
        uniforms: { uAge: { value: 1 }, uTime: shared.uHlTime },
        vertexShader: /* glsl */ `
          varying vec2 vUv;
          void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: /* glsl */ `
          uniform float uAge;
          uniform float uTime;
          varying vec2 vUv;
          float h(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
          float n(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
            return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }
          void main() {
            vec2 q = vUv - 0.5;
            float puff = smoothstep(0.5, 0.0, length(q * vec2(1.0, 1.3)));
            float wisp = n(vUv * 5.0 + vec2(0.0, -uTime * 0.8)) * n(vUv * 11.0 - uTime * 0.5);
            float a = puff * (0.4 + wisp) * (1.0 - uAge) * smoothstep(0.0, 0.15, uAge) * 0.22;
            gl_FragColor = vec4(vec3(0.85, 0.88, 0.95), a);
          }`,
        transparent: true,
        depthWrite: false,
        depthTest: false,
      }),
    );
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = 50;
  }

  /** Follows the camera: call each frame with the camera's position and orientation. */
  update(dt: number, camera: { position: Vector3; quaternion: import('three').Quaternion }, every = 3.6) {
    this.t += dt;
    if (this.t > every) this.t = 0;
    const age = Math.min(1, this.t / 2.2);
    this.mesh.material.uniforms.uAge!.value = age;
    const fwd = new Vector3(0, -0.28 + age * 0.22, -0.55 - age * 0.25).applyQuaternion(camera.quaternion);
    this.mesh.position.copy(camera.position).add(fwd);
    this.mesh.quaternion.copy(camera.quaternion);
    const s = 0.6 + age * 1.1;
    this.mesh.scale.set(s, s, s);
  }

  dispose() {
    this.mesh.geometry.dispose();
    this.mesh.material.dispose();
  }
}
