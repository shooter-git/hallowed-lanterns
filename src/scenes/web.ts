import {
  AdditiveBlending,
  BufferGeometry,
  Color,
  DoubleSide,
  Float32BufferAttribute,
  LineBasicMaterial,
  LineSegments,
  Matrix4,
  Mesh,
  type Object3D,
  PlaneGeometry,
  Quaternion,
  type Ray,
  ShaderMaterial,
  Vector3,
} from 'three';
import type { ChapterContext } from '../chapters/types.ts';
import { CARVE } from '../engine/carvings.ts';
import { stringLights } from '../engine/lanterns.ts';
import { instanceModel, loadModel } from '../engine/models.ts';
import { PumpkinField, type PumpkinSpec } from '../engine/pumpkins.ts';
import { hallow, SHADER_PARS, shared, VERTEX_TERRAIN } from '../engine/shared.ts';
import { pointOnGround } from '../engine/terrain.ts';
import type { SetPiece } from './types.ts';

/**
 * The Web: a clearing draped in stretchy white cobweb that glows violet under blacklight — walls of
 * it, a ceiling of it, strands hanging everywhere — a giant friendly pumpkin spider with spiral
 * eyes, a neon praying mantis, and pumpkins wrapped in web with little green spiders on them.
 * The Ember flies into the web and gets stuck; you free it.
 */

/** Stretched cobweb: strands around irregular holes, thicker where they meet. */
function webMaterial(strength: number): ShaderMaterial {
  return new ShaderMaterial({
    uniforms: { ...shared, uStrength: { value: strength } },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      varying vec3 vHlWorld;
      uniform float uHlTime;
      ${VERTEX_TERRAIN}
      void main() {
        vUv = uv;
        vec3 p = position;
        p.z += sin(p.x * 0.8 + uHlTime * 0.5) * 0.06 + sin(p.y * 1.3 + uHlTime * 0.4) * 0.04;
        vec4 w = modelMatrix * vec4(p, 1.0);
        w.y += hlTerrain(w.xz);
        vHlWorld = w.xyz;
        gl_Position = projectionMatrix * viewMatrix * w;
      }`,
    fragmentShader: /* glsl */ `
      ${SHADER_PARS}
      uniform float uStrength;
      varying vec2 vUv;
      varying vec3 vHlWorld;
      // Edge distance in a stretched Voronoi pattern: the strands between holes.
      float strands(vec2 p) {
        vec2 n = floor(p);
        vec2 f = fract(p);
        float d1 = 8.0;
        float d2 = 8.0;
        for (int j = -1; j <= 1; j++)
        for (int i = -1; i <= 1; i++) {
          vec2 g = vec2(float(i), float(j));
          vec2 o = hlHash22(n + g) * 0.8 + 0.1;
          float d = length(g + o - f);
          if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) d2 = d;
        }
        return d2 - d1;
      }
      void main() {
        // Stretched web: cells pulled long, wobbling strands, torn open in places and matted thick in others.
        vec2 p = vec2(vUv.x * 9.0, vUv.y * 6.0);
        p += vec2(hlNoise(p * 0.7), hlNoise(p * 0.7 + 7.0)) * 0.6;
        float big = strands(p * vec2(1.0, 0.45));
        float fine = strands(p * vec2(2.6, 1.4) + 3.0);
        float matted = smoothstep(0.25, 0.65, hlNoise(p * 0.45 + 11.0));
        float web = smoothstep(0.05, 0.0, big) * (0.35 + matted) + smoothstep(0.03, 0.0, fine) * 0.45 * matted;
        // Sheets of web between the strands, here and there.
        web += smoothstep(0.55, 0.8, hlNoise(p * 1.3)) * 0.14 * matted;
        // Ragged edges.
        float edge = smoothstep(0.0, 0.08, vUv.y) * smoothstep(1.0, 0.92, vUv.y) * smoothstep(0.0, 0.05, vUv.x) * smoothstep(1.0, 0.95, vUv.x);
        web *= edge;
        if (web < 0.02) discard;
        vec3 tint = vec3(0.55, 0.42, 1.0) * (1.2 + hlGlow(vHlWorld) * 0.6);
        vec3 col = hlApplyFog(tint * web * uStrength, vHlWorld);
        gl_FragColor = vec4(col, 1.0);
      }`,
    blending: AdditiveBlending,
    transparent: true,
    depthWrite: false,
    side: DoubleSide,
  });
}

export async function web(ctx: ChapterContext, at: Vector3, yaw: number): Promise<SetPiece & { snare: Vector3; hooks: { onFree: (() => void) | null } }> {
  const hooks: { onFree: (() => void) | null } = { onFree: null };
  const objects: Object3D[] = [];
  const toWorld = (v: Vector3) => v.clone().applyAxisAngle(new Vector3(0, 1, 0), yaw).add(at);
  const curtain = webMaterial(0.85);
  const ceiling = webMaterial(0.5);
  // The path runs along local z. The spider sits in the web on the left, the mantis on the right;
  // walls of web behind them, a ceiling overhead, and the ends drawn in towards the path.
  const sheets: { w: number; h: number; p: Vector3; ry: number; rx?: number; mat: ShaderMaterial }[] = [
    { w: 16, h: 4.6, p: new Vector3(-7.6, 2.3, 0), ry: Math.PI / 2, mat: curtain },
    { w: 16, h: 4.6, p: new Vector3(6.4, 2.3, 0), ry: -Math.PI / 2, mat: curtain },
    { w: 6.5, h: 4.6, p: new Vector3(-4.6, 2.3, -7.4), ry: Math.PI / 3.2, mat: curtain },
    { w: 5.5, h: 4.6, p: new Vector3(4.0, 2.3, 7.4), ry: -Math.PI / 3.2, mat: curtain },
    { w: 14, h: 16, p: new Vector3(-0.6, 4.3, 0), ry: 0, rx: -Math.PI / 2, mat: ceiling },
  ];
  const SPIDER = new Vector3(-4.6, 0, -1.5);
  const MANTIS = new Vector3(4.3, 0, 3.0);
  // Keep strands and pumpkins out of the two creatures.
  const free = (x: number, z: number) => !(x < -1.6 && Math.abs(z - SPIDER.z) < 3.8) && !(x > 2.4 && Math.abs(z - MANTIS.z) < 2);
  for (const s of sheets) {
    const m = new Mesh(new PlaneGeometry(s.w, s.h, 24, 12), s.mat);
    m.position.copy(toWorld(s.p));
    m.rotation.set(s.rx ?? 0, yaw + s.ry, 0, 'YXZ');
    m.renderOrder = 7;
    objects.push(m);
  }
  // Strands hanging from the ceiling everywhere.
  const lines: number[] = [];
  for (let i = 0; i < 220; i++) {
    const lx = -7 + Math.random() * 13;
    const lz = (Math.random() - 0.5) * 15;
    if (!free(lx, lz)) continue;
    const p = toWorld(new Vector3(lx, 4.3, lz));
    // Over the path they stop above head height.
    const len = Math.abs(lx) < 1.6 ? 0.4 + Math.random() * 1.4 : 0.6 + Math.random() * 2.6;
    lines.push(p.x, p.y, p.z, p.x + (Math.random() - 0.5) * 0.2, p.y - len, p.z + (Math.random() - 0.5) * 0.2);
  }

  // The spider and the mantis.
  const spider = await loadModel('pumpkin-spider', { glowReceive: 0.6 });
  const legs: Object3D[] = [];
  if (spider) {
    spider.root.position.copy(toWorld(SPIDER));
    spider.root.rotation.y = yaw + Math.PI / 2 - 0.15;
    objects.push(spider.root);
    for (let k = 0; k < 8; k++) {
      const l = spider.node(`leg_${k}`);
      if (l) legs.push(l);
    }
    for (const m of spider.glows.values()) m.emissiveIntensity = 2.5;
  }
  const legRest = legs.map((l) => l.rotation.clone());
  const baby = spider?.node('baby');
  const babyRest = baby?.position.clone();
  const mantis = await loadModel('praying-mantis', { glowReceive: 0.6 });
  const mantisHead = mantis?.node('head');
  if (mantis) {
    mantis.root.position.copy(toWorld(MANTIS));
    mantis.root.rotation.y = yaw - Math.PI / 2 + 0.35;
    objects.push(mantis.root);
    for (const m of mantis.glows.values()) m.emissiveIntensity = 2.2;
  }

  // Pumpkins wrapped in web, with little neon spiders on them, hanging on threads from the web.
  const hangAt: Vector3[] = [];
  for (let tries = 0; hangAt.length < 12 && tries < 200; tries++) {
    const side = hangAt.length % 2 ? 1 : -1;
    const lx = side * (2.1 + Math.random() * 1.6);
    const lz = (Math.random() - 0.5) * 14;
    if (free(lx, lz) && hangAt.every((h) => Math.hypot(h.x - lx, h.z - lz) > 1.2)) hangAt.push(new Vector3(lx, 1.1 + Math.random() * 1.6, lz));
  }
  const webPumpkin = await loadModel('web-pumpkin', { glowReceive: 0.6 });
  const specs: PumpkinSpec[] = [];
  let pumpkins: PumpkinField | null = null;
  if (webPumpkin) {
    for (const m of webPumpkin.glows.values()) m.emissiveIntensity = 1.6;
    const top = webPumpkin.node('hang_point')?.position.y ?? 0.75;
    const mats = hangAt.map((h) => {
      const s = 0.9 + Math.random() * 0.35;
      // The thread from the hang point up to the ceiling.
      const p = toWorld(h.clone().setY(h.y + top * s));
      lines.push(p.x, p.y, p.z, p.x, 4.3, p.z);
      return new Matrix4().compose(toWorld(h), new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), Math.random() * 6.28), new Vector3(s, s, s));
    });
    objects.push(instanceModel(webPumpkin, mats));
  } else {
    for (const [i, h] of hangAt.entries()) {
      specs.push({
        position: toWorld(h),
        size: new Vector3(0.22, 0.27, 0.22),
        yaw: yaw + (h.x > 0 ? -1.4 : 1.4),
        carve: 100 + (CARVE.creatures[5] as number),
        skin: new Color(0.42, 0.22, 0.3),
        glow: new Color(0.4, 1.2, 0.3),
        hang: 4.3 - h.y,
        phase: i,
      });
    }
    pumpkins = new PumpkinField(specs, ctx.atlas, { detail: [28, 12], simple: [14, 7] });
    objects.push(pumpkins.group);
  }

  // All the hanging strands and threads, one draw call.
  const g = new BufferGeometry();
  g.setAttribute('position', new Float32BufferAttribute(lines, 3));
  const strands = new LineSegments(g, hallow(new LineBasicMaterial({ color: new Color(0.7, 0.55, 1).multiplyScalar(1.4), transparent: true, opacity: 0.6, blending: AdditiveBlending, depthWrite: false }), { key: 'strand' }));
  objects.push(strands);

  // Purple LEDs along the ground under the webs.
  const runs = [-1, 1].map((s) => ({ from: toWorld(new Vector3(s * 1.7, 0.06, -7.5)), to: toWorld(new Vector3(s * 1.7, 0.06, 7.5)), sag: 0 }));
  const leds = stringLights(runs, { spacing: 0.22, color: new Color(0.6, 0.2, 1), brightness: 12, glowEvery: 2, glowRadius: 1.4, glowIntensity: 0.25 });
  objects.push(leds.mesh);

  const snare = toWorld(new Vector3(2.5, 2.2, -1.8));
  let freed = false;
  let twitch = 0;
  return {
    objects,
    snare,
    hooks,
    glow: [
      ...leds.lights,
      ...[-4, 0, 4].map((z) => {
        const p = toWorld(new Vector3(0, 0, z));
        return { x: p.x, z: p.z, radius: 6, color: new Color(0.5, 0.25, 1), intensity: 0.55, flicker: 0 };
      }),
    ],
    sources: [
      { position: toWorld(new Vector3(0, 3, 0)), color: new Color(0.55, 0.3, 1), intensity: 8, distance: 12 },
      { position: toWorld(SPIDER.clone().add(new Vector3(2.2, 2.2, 0))), color: new Color(0.6, 0.35, 1), intensity: 6, distance: 8 },
      { position: toWorld(MANTIS.clone().add(new Vector3(-1.6, 2.4, 0))), color: new Color(0.55, 0.4, 1), intensity: 4, distance: 6 },
    ],
    update(dt, time) {
      // The spider's legs twitch now and then; the mantis turns its head to you.
      twitch = Math.max(0, twitch - dt);
      legs.forEach((l, i) => {
        const r = legRest[i];
        if (!r) return;
        // Legs 0-3 reach out along +x, 4-7 along -x: lifting one is a turn about z.
        const lift = Math.sin(time * 1.3 + i) * 0.03 + Math.max(0, Math.sin(time * 18 + i * 1.7)) * 0.12 * twitch;
        l.rotation.z = r.z + (i < 4 ? lift : -lift);
      });
      if (baby && babyRest) {
        baby.position.y = babyRest.y + Math.abs(Math.sin(time * 2.1)) * 0.02 + twitch * 0.05;
        baby.rotation.y += dt * twitch * 6;
      }
      if (mantisHead && mantis) {
        const local = mantis.root.worldToLocal(ctx.camera.position.clone());
        const want = Math.max(-0.7, Math.min(0.7, Math.atan2(local.x, local.z)));
        mantisHead.rotation.y += (want - mantisHead.rotation.y) * (1 - Math.exp(-dt * 1.5));
      }
      pumpkins?.update(ctx.camera, dt);
    },
    pick(ray: Ray) {
      // Free the Ember: tap the web where it's caught.
      if (!freed && ray.distanceSqToPoint(pointOnGround(snare)) < 1.2) {
        return () => {
          freed = true;
          void ctx.audio.sfx('web-stretch', { at: pointOnGround(snare), volume: 0.9 });
          hooks.onFree?.();
        };
      }
      const spiderAt = spider ? pointOnGround(spider.root.position.clone().setY(2)) : null;
      if (spiderAt && ray.distanceSqToPoint(spiderAt) < 4) {
        return () => {
          twitch = 1;
          void ctx.audio.sfx('spider-scurry', { at: spiderAt, volume: 0.8 });
        };
      }
      if (mantis && ray.distanceSqToPoint(pointOnGround(mantis.root.position.clone().setY(2))) < 2.5) {
        return () => void ctx.audio.sfx('mantis-click', { at: pointOnGround(mantis.root.position), volume: 0.8 });
      }
      const hit = hangAt.map((h) => pointOnGround(toWorld(h))).find((p) => ray.distanceSqToPoint(p) < 0.2 && ray.origin.distanceTo(p) < 15);
      if (hit) return () => void ctx.audio.sfx('web-stretch', { at: hit, volume: 0.6 });
      return null;
    },
    dispose() {
      curtain.dispose();
      ceiling.dispose();
      g.dispose();
      pumpkins?.dispose();
      leds.mesh.geometry.dispose();
    },
  };
}
