import {
  AdditiveBlending,
  BufferGeometry,
  Color,
  Float32BufferAttribute,
  Group,
  Mesh,
  PlaneGeometry,
  PointLight,
  Points,
  ShaderMaterial,
  Vector3,
} from 'three';
import type { GlowLight } from './glowfield.ts';
import { NOISE } from './glsl.ts';
import { shared } from './shared.ts';

const SPARKS = 36;

/**
 * The Ember: a small living candle flame that leads the way. A flickering flame drawn in the
 * shader (always facing you), a soft halo, a trail of sparks, and a real light that moves with it.
 */
export class Ember {
  readonly group = new Group();
  readonly position = new Vector3();
  /** Where it wants to be. */
  readonly target = new Vector3();
  readonly light: PointLight;
  readonly glow: GlowLight;
  /** 0 = not here yet, 1 = fully present. */
  presence = 0;
  /** How fast it follows its target (higher is snappier). */
  agility = 2.2;
  /** Excitement (0–1): bigger, brighter, livelier. */
  excitement = 0;

  private readonly velocity = new Vector3();
  private readonly flame: Mesh<PlaneGeometry, ShaderMaterial>;
  private readonly sparks: Points<BufferGeometry, ShaderMaterial>;
  private readonly sparkData: { p: Vector3; v: Vector3; life: number; max: number }[] = [];
  private t = 0;

  constructor(color = new Color(1.0, 0.58, 0.2)) {
    this.flame = new Mesh(
      new PlaneGeometry(1, 1),
      new ShaderMaterial({
        uniforms: {
          uTime: shared.uHlTime,
          uPresence: { value: 0 },
          uExcite: { value: 0 },
        },
        vertexShader: /* glsl */ `
          varying vec2 vUv;
          uniform float uPresence;
          uniform float uExcite;
          void main() {
            vUv = uv;
            // Billboard: keep the quad facing the camera, upright.
            vec3 centre = (modelViewMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
            float s = 0.42 * uPresence * (1.0 + 0.25 * uExcite);
            vec3 p = centre + vec3(position.x * s, (position.y + 0.18) * s * 1.5, 0.0);
            gl_Position = projectionMatrix * vec4(p, 1.0);
          }`,
        fragmentShader: /* glsl */ `
          varying vec2 vUv;
          uniform float uTime;
          uniform float uPresence;
          uniform float uExcite;
          ${NOISE}
          void main() {
            vec2 p = vUv - vec2(0.5, 0.32);
            // The flame licks upward: distort with rising noise, more toward the tip.
            float rise = vUv.y;
            float n = hlNoise(vec2(p.x * 6.0, p.y * 4.0 - uTime * 4.5)) - 0.5;
            float n2 = hlNoise(vec2(p.x * 13.0 + 3.0, p.y * 9.0 - uTime * 7.0)) - 0.5;
            p.x += (n * 0.16 + n2 * 0.06) * rise * (1.0 + uExcite);
            // Teardrop: round at the bottom, pointed at the top.
            float w = mix(0.2, 0.02, smoothstep(0.0, 0.62, p.y + 0.12)) * (p.y < -0.05 ? 1.0 : 1.0);
            float body = 1.0 - smoothstep(0.0, 1.0, length(vec2(p.x / max(w, 0.02), (p.y + 0.02) / 0.5)));
            body = clamp(body, 0.0, 1.0);
            float core = smoothstep(0.35, 0.9, body);
            vec3 col = mix(vec3(1.0, 0.22, 0.03), vec3(1.0, 0.62, 0.2), smoothstep(0.0, 0.5, body));
            col = mix(col, vec3(1.0, 0.95, 0.8), core);
            // A faint blue root, like a real candle.
            col = mix(col, vec3(0.25, 0.35, 1.0), smoothstep(-0.05, -0.17, p.y) * smoothstep(0.15, 0.6, body) * 0.6);
            float halo = exp(-dot(vUv - vec2(0.5, 0.35), vUv - vec2(0.5, 0.35)) * 22.0);
            vec3 light = col * body * (9.0 + 6.0 * uExcite) + vec3(1.0, 0.55, 0.2) * halo * (0.5 + 0.4 * uExcite);
            gl_FragColor = vec4(light * uPresence, 1.0);
          }`,
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
      }),
    );
    this.flame.frustumCulled = false;
    this.flame.renderOrder = 20;
    this.group.add(this.flame);

    const pos = new Float32Array(SPARKS * 3);
    const life = new Float32Array(SPARKS);
    const geo = new BufferGeometry();
    geo.setAttribute('position', new Float32BufferAttribute(pos, 3));
    geo.setAttribute('aLife', new Float32BufferAttribute(life, 1));
    this.sparks = new Points(
      geo,
      new ShaderMaterial({
        uniforms: { uScale: { value: 300 } },
        vertexShader: /* glsl */ `
          attribute float aLife;
          varying float vLife;
          uniform float uScale;
          void main() {
            vLife = aLife;
            vec4 mv = modelViewMatrix * vec4(position, 1.0);
            gl_PointSize = uScale * 0.02 * aLife / -mv.z;
            gl_Position = projectionMatrix * mv;
          }`,
        fragmentShader: /* glsl */ `
          varying float vLife;
          void main() {
            float d = length(gl_PointCoord - 0.5);
            float a = smoothstep(0.5, 0.0, d) * vLife;
            gl_FragColor = vec4(vec3(1.0, 0.55, 0.18) * a * 6.0, 1.0);
          }`,
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
      }),
    );
    this.sparks.frustumCulled = false;
    this.sparks.renderOrder = 21;
    for (let i = 0; i < SPARKS; i++)
      this.sparkData.push({ p: new Vector3(), v: new Vector3(), life: 0, max: 1 });

    this.light = new PointLight(color, 0, 9, 1.6);
    this.group.add(this.light);
    this.glow = { x: 0, z: 0, radius: 3.2, color, intensity: 0, phase: 0.37, flicker: 1 };
  }

  /** The sparks live in world space; add them to the scene alongside `group`. */
  get trail() {
    return this.sparks;
  }

  /** Jump straight to a place (no flight). */
  place(p: Vector3) {
    this.position.copy(p);
    this.target.copy(p);
    this.velocity.set(0, 0, 0);
  }

  update(dt: number, pixelScale: number) {
    this.t += dt;
    // A springy chase toward the target, with an idle bob and a wandering wobble.
    const k = this.agility;
    const to = new Vector3().subVectors(this.target, this.position);
    this.velocity.addScaledVector(to, k * k * dt);
    this.velocity.multiplyScalar(Math.exp(-2 * k * dt));
    this.position.addScaledVector(this.velocity, dt);
    const bob = Math.sin(this.t * 2.1) * 0.06 + Math.sin(this.t * 3.7) * 0.025;
    const wob = Math.sin(this.t * 1.3) * 0.04;
    this.group.position.set(this.position.x + wob, this.position.y + bob, this.position.z);

    const u = this.flame.material.uniforms;
    u.uPresence!.value = this.presence;
    u.uExcite!.value = this.excitement;
    const fl = 0.85 + 0.1 * Math.sin(this.t * 9.1) + 0.05 * Math.sin(this.t * 17.3);
    this.light.intensity = this.presence * (2.2 + this.excitement * 2) * fl;
    this.glow.x = this.group.position.x;
    this.glow.z = this.group.position.z;
    this.glow.intensity = this.presence * (1.2 + this.excitement);

    // Sparks: shed from the flame, drifting up and away.
    const speed = this.velocity.length();
    const geo = this.sparks.geometry;
    const pos = geo.getAttribute('position') as Float32BufferAttribute;
    const life = geo.getAttribute('aLife') as Float32BufferAttribute;
    const rate = (3 + speed * 10 + this.excitement * 12) * this.presence;
    for (let i = 0; i < SPARKS; i++) {
      const s = this.sparkData[i] as (typeof this.sparkData)[number];
      if (s.life <= 0 && Math.random() < rate * dt / 3) {
        s.p.copy(this.group.position).add(new Vector3((Math.random() - 0.5) * 0.08, 0.05, (Math.random() - 0.5) * 0.08));
        s.v.set((Math.random() - 0.5) * 0.4, 0.4 + Math.random() * 0.5, (Math.random() - 0.5) * 0.4).addScaledVector(this.velocity, -0.3);
        s.max = 0.6 + Math.random() * 0.9;
        s.life = s.max;
      }
      if (s.life > 0) {
        s.life -= dt;
        s.v.y += dt * 0.2;
        s.v.x += (Math.random() - 0.5) * dt * 1.5;
        s.v.z += (Math.random() - 0.5) * dt * 1.5;
        s.p.addScaledVector(s.v, dt);
      }
      pos.setXYZ(i, s.p.x, s.p.y, s.p.z);
      life.setX(i, Math.max(0, s.life / s.max));
    }
    pos.needsUpdate = true;
    life.needsUpdate = true;
    this.sparks.material.uniforms.uScale!.value = pixelScale;
  }

  dispose() {
    this.flame.geometry.dispose();
    this.flame.material.dispose();
    this.sparks.geometry.dispose();
    this.sparks.material.dispose();
    this.light.dispose();
  }
}
