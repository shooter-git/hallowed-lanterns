import {
  AdditiveBlending,
  BufferGeometry,
  Color,
  DoubleSide,
  Float32BufferAttribute,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  type Object3D,
  PlaneGeometry,
  type Ray,
  ShaderMaterial,
  Vector3,
} from 'three';
import type { ChapterContext } from '../chapters/types.ts';
import { CARVE } from '../engine/carvings.ts';
import { stringLights } from '../engine/lanterns.ts';
import { loadModel } from '../engine/models.ts';
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
        vec2 p = vHlWorld.xz * 0.0 + vec2(vUv.x * 9.0, vUv.y * 6.0);
        float big = strands(p * vec2(1.0, 0.8));
        float fine = strands(p * 2.7 + 3.0);
        float web = smoothstep(0.12, 0.0, big) + smoothstep(0.06, 0.0, fine) * 0.5;
        // Sheets of web between the strands, here and there.
        web += smoothstep(0.5, 0.75, hlNoise(p * 1.3)) * 0.18;
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
  const curtain = webMaterial(1);
  const ceiling = webMaterial(0.7);
  // Curtains on both sides and behind the spider, a ceiling overhead (the path runs along local z).
  const sheets: { w: number; h: number; p: Vector3; ry: number; rx?: number; mat: ShaderMaterial }[] = [
    { w: 14, h: 4.6, p: new Vector3(-4.2, 2.3, 0), ry: Math.PI / 2, mat: curtain },
    { w: 14, h: 4.6, p: new Vector3(4.2, 2.3, 0), ry: -Math.PI / 2, mat: curtain },
    { w: 9, h: 4.6, p: new Vector3(-6.5, 2.3, -2), ry: Math.PI / 2.4, mat: curtain },
    { w: 9, h: 4.6, p: new Vector3(6.5, 2.3, 2), ry: -Math.PI / 2.4, mat: curtain },
    { w: 9, h: 14, p: new Vector3(0, 4.3, 0), ry: 0, rx: -Math.PI / 2, mat: ceiling },
  ];
  for (const s of sheets) {
    const m = new Mesh(new PlaneGeometry(s.w, s.h, 24, 12), s.mat);
    m.position.copy(toWorld(s.p));
    m.rotation.set(s.rx ?? 0, yaw + s.ry, 0, 'YXZ');
    m.renderOrder = 7;
    objects.push(m);
  }
  // Strands hanging from the ceiling everywhere.
  const lines: number[] = [];
  for (let i = 0; i < 160; i++) {
    const p = toWorld(new Vector3((Math.random() - 0.5) * 8, 4.3, (Math.random() - 0.5) * 14));
    const len = 0.6 + Math.random() * 2.6;
    lines.push(p.x, p.y, p.z, p.x + (Math.random() - 0.5) * 0.2, p.y - len, p.z + (Math.random() - 0.5) * 0.2);
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new Float32BufferAttribute(lines, 3));
  const strands = new LineSegments(g, hallow(new LineBasicMaterial({ color: new Color(0.7, 0.55, 1).multiplyScalar(1.4), transparent: true, opacity: 0.6, blending: AdditiveBlending, depthWrite: false }), { key: 'strand' }));
  objects.push(strands);

  // The spider and the mantis.
  const spider = await loadModel('pumpkin-spider', { glowReceive: 0.6 });
  const legs: Object3D[] = [];
  if (spider) {
    spider.root.position.copy(toWorld(new Vector3(-1.5, 0, -1.2)));
    spider.root.rotation.y = yaw + 0.5;
    objects.push(spider.root);
    for (let k = 0; k < 8; k++) {
      const l = spider.node(`leg_${k}`);
      if (l) legs.push(l);
    }
    for (const m of spider.glows.values()) m.emissiveIntensity = 2.5;
  }
  const legRest = legs.map((l) => l.rotation.clone());
  const mantis = await loadModel('praying-mantis', { glowReceive: 0.6 });
  const mantisHead = mantis?.node('head');
  if (mantis) {
    mantis.root.position.copy(toWorld(new Vector3(2.4, 0, 2.2)));
    mantis.root.rotation.y = yaw - 1.1;
    objects.push(mantis.root);
    for (const m of mantis.glows.values()) m.emissiveIntensity = 2.2;
  }

  // Pumpkins wrapped in web, with little neon spiders on them, hanging in the web.
  const specs: PumpkinSpec[] = [];
  for (let i = 0; i < 12; i++) {
    const side = i % 2 ? 1 : -1;
    specs.push({
      position: toWorld(new Vector3(side * (2.6 + Math.random() * 1.2), 1.2 + Math.random() * 2.4, (Math.random() - 0.5) * 12)),
      size: new Vector3(0.22, 0.27, 0.22),
      yaw: yaw + (side > 0 ? -1.4 : 1.4),
      carve: 100 + (CARVE.creatures[5] as number),
      skin: new Color(0.42, 0.22, 0.3),
      glow: new Color(0.4, 1.2, 0.3),
      hang: 4.3 - 2.6,
    });
  }
  const pumpkins = new PumpkinField(specs, ctx.atlas, { detail: [28, 12], simple: [14, 7] });
  objects.push(pumpkins.group);

  // Purple LEDs along the ground under the webs.
  const runs = [-1, 1].map((s) => ({ from: toWorld(new Vector3(s * 3.6, 0.06, -7)), to: toWorld(new Vector3(s * 3.6, 0.06, 7)), sag: 0 }));
  const leds = stringLights(runs, { spacing: 0.22, color: new Color(0.6, 0.2, 1), brightness: 12, glowEvery: 2, glowRadius: 1.4, glowIntensity: 0.25 });
  objects.push(leds.mesh);

  const snare = toWorld(new Vector3(-3.3, 2.1, 1.5));
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
      { position: toWorld(new Vector3(-1.5, 1.5, 1)), color: new Color(0.6, 0.35, 1), intensity: 5, distance: 7 },
    ],
    update(dt, time) {
      // The spider's legs twitch now and then; the mantis turns its head to you.
      twitch = Math.max(0, twitch - dt);
      legs.forEach((l, i) => {
        const r = legRest[i];
        if (!r) return;
        l.rotation.x = r.x + Math.sin(time * 1.3 + i) * 0.03 + Math.sin(time * 18 + i) * 0.08 * twitch;
      });
      if (mantisHead && mantis) {
        const local = mantis.root.worldToLocal(ctx.camera.position.clone());
        const want = Math.max(-0.7, Math.min(0.7, Math.atan2(local.x, local.z)));
        mantisHead.rotation.y += (want - mantisHead.rotation.y) * (1 - Math.exp(-dt * 1.5));
      }
      pumpkins.update(ctx.camera, dt);
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
      if (mantis && ray.distanceSqToPoint(pointOnGround(mantis.root.position.clone().setY(1.6))) < 2) {
        return () => void ctx.audio.sfx('mantis-click', { at: pointOnGround(mantis.root.position), volume: 0.8 });
      }
      const i = pumpkins.pick(ray, 15);
      if (i >= 0) return () => void ctx.audio.sfx('web-stretch', { at: pointOnGround((specs[i] as PumpkinSpec).position), volume: 0.6 });
      return null;
    },
    dispose() {
      curtain.dispose();
      ceiling.dispose();
      g.dispose();
      pumpkins.dispose();
      leds.mesh.geometry.dispose();
    },
  };
}
