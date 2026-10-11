import {
  BoxGeometry,
  Color,
  Group,
  InstancedMesh,
  Matrix4,
  Mesh,
  MeshStandardMaterial,
  type Object3D,
  PlaneGeometry,
  type Ray,
  ShaderMaterial,
  Vector3,
} from 'three';
import type { ChapterContext } from '../chapters/types.ts';
import { stringLights } from '../engine/lanterns.ts';
import { loadModel } from '../engine/models.ts';
import { hallow, shared } from '../engine/shared.ts';
import { heightAt, pointOnGround } from '../engine/terrain.ts';
import type { SetPiece } from './types.ts';

/**
 * The picture show: a screen in a clearing in front of a stage of hay bales, white benches, and
 * strings of purple and blue globe lights overhead. The film is our own — a shadow-puppet tale of
 * the Ember's night (the moon rising over the jack-o'-lanterns, the Ember hopping out, bats, a
 * longhorn, a spider on its thread), drawn live in the shader on a warm, flickering screen.
 */

const FILM = /* glsl */ `
uniform float uTime;
uniform float uOn;
varying vec2 vUv;
float sdCircle(vec2 p, float r) { return length(p) - r; }
float sdBox(vec2 p, vec2 b) { vec2 d = abs(p) - b; return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0); }
float sdTri(vec2 p, float r) { const float k = 1.7320508; p.x = abs(p.x) - r; p.y = p.y + r / k; if (p.x + k * p.y > 0.0) p = vec2(p.x - k * p.y, -k * p.x - p.y) / 2.0; p.x -= clamp(p.x, -2.0 * r, 0.0); return -length(p) * sign(p.y); }
float fill(float d) { return smoothstep(0.004, -0.004, d); }
// A jack-o'-lantern silhouette (with its face as light) at p, size s.
float jack(vec2 p, float s) {
  float body = sdCircle(p * vec2(1.0, 1.15), s);
  float stem = sdBox(p - vec2(0.0, s * 1.05), vec2(s * 0.12, s * 0.2));
  float face = min(min(sdTri((p - vec2(-s * 0.38, s * 0.15)) / s, 0.22) * s, sdTri((p - vec2(s * 0.38, s * 0.15)) / s, 0.22) * s),
                   sdBox(p - vec2(0.0, -s * 0.35), vec2(s * 0.5, s * 0.08)));
  return fill(min(body, stem)) * (1.0 - fill(face));
}
float bat(vec2 p, float s, float t) {
  float flap = sin(t * 14.0) * 0.4;
  float b = sdCircle(p, s * 0.25);
  vec2 q = vec2(abs(p.x), p.y);
  float w = sdBox(q - vec2(s * 0.55, s * (0.1 + flap * 0.4)), vec2(s * 0.45, s * 0.08));
  return fill(min(b, w));
}
float longhorn(vec2 p, float s, float t) {
  float body = sdBox(p, vec2(s * 0.9, s * 0.38)) - s * 0.15;
  float stride = sin(t * 3.0);
  float legs = min(min(sdBox(p - vec2(-s * 0.6, -s * (0.75 + stride * 0.05)), vec2(s * 0.08, s * 0.4)), sdBox(p - vec2(s * 0.6, -s * (0.75 - stride * 0.05)), vec2(s * 0.08, s * 0.4))),
                   min(sdBox(p - vec2(-s * 0.3, -s * (0.75 - stride * 0.05)), vec2(s * 0.08, s * 0.4)), sdBox(p - vec2(s * 0.3, -s * (0.75 + stride * 0.05)), vec2(s * 0.08, s * 0.4))));
  vec2 h = p - vec2(s * 1.15, s * 0.3);
  float head = sdCircle(h * vec2(1.0, 0.8), s * 0.32);
  vec2 hq = vec2(h.x, h.y - s * 0.25);
  float horns = abs(length(hq - vec2(0.0, -s * 1.2)) - s * 1.45) - s * 0.05;
  horns = max(horns, -hq.y);
  horns = max(horns, abs(hq.x) - s * 1.4);
  return fill(min(min(body, legs), min(head, horns)));
}
float hills(vec2 p) { return fill(p.y - (0.18 + 0.04 * sin(p.x * 7.0) + 0.03 * sin(p.x * 13.0 + 1.0))); }
void main() {
  vec2 p = vUv;
  float t = mod(uTime, 64.0);
  float scene = floor(t / 16.0);
  float st = mod(t, 16.0);
  // The warm screen: brightest in the middle, flickering like an old projector.
  float flick = 0.92 + 0.06 * sin(uTime * 47.0) + 0.03 * sin(uTime * 13.0);
  vec3 screen = mix(vec3(0.55, 0.42, 0.3), vec3(1.0, 0.86, 0.64), smoothstep(0.75, 0.0, length((p - 0.5) * vec2(1.0, 1.4)))) * flick;
  float shadow = hills(p);
  vec3 ember = vec3(0.0);
  vec2 ep = vec2(-1.0);
  if (scene < 0.5) {
    // The moon rises over a row of jack-o'-lanterns; one sputters, and the Ember hops out.
    float moon = fill(sdCircle(p - vec2(0.75, 0.3 + st * 0.03), 0.09));
    screen = mix(screen, screen * 1.25 + vec3(0.15, 0.1, 0.0), moon);
    for (int i = 0; i < 5; i++) shadow = max(shadow, jack(p - vec2(0.15 + float(i) * 0.17, 0.27), 0.055));
    float hop = clamp((st - 8.0) / 6.0, 0.0, 1.0);
    ep = vec2(0.49 + hop * 0.35, 0.3 + sin(hop * 9.42) * 0.12 * (1.0 - hop) + hop * 0.15);
  } else if (scene < 1.5) {
    // Through the woods: trunks, the Ember bouncing along, bats.
    for (int i = 0; i < 6; i++) {
      float x = fract(float(i) * 0.19 - st * 0.02) * 1.2 - 0.1;
      shadow = max(shadow, fill(sdBox(p - vec2(x, 0.5), vec2(0.018, 0.45))));
    }
    for (int i = 0; i < 3; i++) shadow = max(shadow, bat(p - vec2(fract(st * 0.07 + float(i) * 0.33) * 1.2 - 0.1, 0.75 + 0.05 * sin(st + float(i))), 0.05, st + float(i)));
    ep = vec2(0.2 + st * 0.04, 0.24 + abs(sin(st * 3.0)) * 0.1);
  } else if (scene < 2.5) {
    // A longhorn walks; the Ember rides between its horns.
    vec2 lp = vec2(fract(st * 0.03) * 1.6 - 0.3, 0.32);
    shadow = max(shadow, longhorn(p - lp, 0.09, st));
    ep = lp + vec2(0.1, 0.17);
  } else {
    // A spider lets itself down on a thread; the Ember waves, and floats up to the moon.
    float drop = min(1.0, st / 5.0);
    vec2 sp = vec2(0.6, 0.9 - drop * 0.4);
    shadow = max(shadow, fill(sdBox(p - vec2(0.6, (0.95 + sp.y) * 0.5), vec2(0.002, (0.95 - sp.y) * 0.5))));
    shadow = max(shadow, jack(p - sp, 0.05));
    for (int i = 0; i < 4; i++) {
      float a = float(i) * 0.5 - 0.75;
      shadow = max(shadow, fill(sdBox(p - sp - vec2(0.07 * cos(a), 0.03 * sin(a + st * 4.0)), vec2(0.045, 0.004))));
      shadow = max(shadow, fill(sdBox(p - sp + vec2(0.07 * cos(a), -0.03 * sin(a + st * 4.0)), vec2(0.045, 0.004))));
    }
    float rise = clamp((st - 8.0) / 8.0, 0.0, 1.0);
    ep = vec2(0.35 + rise * 0.4, 0.3 + rise * 0.45);
    float moon = fill(sdCircle(p - vec2(0.8, 0.78), 0.08));
    screen = mix(screen, screen * 1.25 + vec3(0.15, 0.1, 0.0), moon);
  }
  vec3 col = mix(screen, vec3(0.03, 0.02, 0.02), shadow);
  // The Ember: the only colour in the film, a bright little flame.
  if (ep.x > -0.5) {
    vec2 q = (p - ep) * vec2(1.0, 0.7);
    float f = smoothstep(0.03, 0.0, length(q)) ;
    col += vec3(1.0, 0.55, 0.15) * (f * 3.0 + smoothstep(0.12, 0.0, length(q)) * 0.5);
  }
  // Scene changes fade through dark, like reels.
  float fade = smoothstep(0.0, 0.8, st) * smoothstep(16.0, 15.2, st);
  col *= mix(0.15, 1.0, fade);
  // Grain and scratches.
  float g = fract(sin(dot(p * 300.0 + uTime, vec2(12.9898, 78.233))) * 43758.5453);
  col *= 0.94 + 0.06 * g;
  col *= 1.0 - smoothstep(0.996, 1.0, fract(p.x * 13.0 + floor(uTime * 8.0) * 0.37)) * 0.3;
  gl_FragColor = vec4(col * uOn * 2.2, 1.0);
}
`;

export async function pictureShow(ctx: ChapterContext, at: Vector3, yaw: number): Promise<SetPiece & { seat: Vector3 }> {
  const objects: Object3D[] = [];
  const toWorld = (v: Vector3) => v.clone().applyAxisAngle(new Vector3(0, 1, 0), yaw).add(at);
  const group = new Group();
  group.position.copy(at);
  group.rotation.y = yaw;
  objects.push(group);

  const film = new ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uOn: { value: 1 } },
    vertexShader: /* glsl */ `varying vec2 vUv;
      uniform sampler2D uTerrain; uniform vec4 uTerrainBounds;
      void main() { vUv = uv; vec4 w = modelMatrix * vec4(position, 1.0);
        vec2 tuv = clamp((w.xz - uTerrainBounds.xy) / uTerrainBounds.zw, 0.0, 1.0);
        w.y += texture2D(uTerrain, tuv).r;
        gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: FILM,
  });
  Object.assign(film.uniforms, { uTerrain: shared.uTerrain, uTerrainBounds: shared.uTerrainBounds });

  const screenModel = await loadModel('movie-screen');
  if (screenModel) {
    group.add(screenModel.root);
    const screen = screenModel.node('screen') as Mesh | undefined;
    if (screen) screen.material = film;
  } else {
    const frame = hallow(new MeshStandardMaterial({ color: 0xb8bcc4, roughness: 0.4, metalness: 0.7 }), { key: 'truss' });
    for (const x of [-3.2, 3.2]) {
      const post = new Mesh(new BoxGeometry(0.22, 4.4, 0.22), frame);
      post.position.set(x, 2.2, 0);
      group.add(post);
    }
    const top = new Mesh(new BoxGeometry(6.6, 0.22, 0.22), frame);
    top.position.set(0, 4.3, 0);
    group.add(top);
    const screen = new Mesh(new PlaneGeometry(6, 3.4), film);
    screen.position.set(0, 2.5, 0.02);
    group.add(screen);
  }
  // A low stage of hay bales in front of the screen.
  const stage = await loadModel('hay-stage');
  if (stage) {
    stage.root.position.set(0, 0, 1.2);
    group.add(stage.root);
  } else {
    const hay = await loadModel('hay-bale');
    if (hay) {
      for (let k = 0; k < 10; k++) {
        const b = hay.root.clone(true);
        b.position.set(-2.4 + (k % 5) * 1.0, k < 5 ? 0 : 0.38, 1.2 + (k < 5 ? 0 : -0.3));
        group.add(b);
      }
    }
  }
  // White benches in rows.
  const bench = await loadModel('bench');
  const seats: Vector3[] = [];
  for (let row = 0; row < 3; row++) {
    for (let k = 0; k < 3; k++) {
      const p = new Vector3(-3.4 + k * 3.4 + (row % 2) * 0.6, 0, 7 + row * 2.4);
      seats.push(toWorld(p));
      if (bench) {
        const b = bench.root.clone(true);
        b.position.copy(p);
        group.add(b);
      } else {
        const b = new Mesh(new BoxGeometry(1.8, 0.45, 0.3), hallow(new MeshStandardMaterial({ color: 0xf2f0ea, roughness: 0.5 }), { key: 'bench' }));
        b.position.copy(p).setY(0.22);
        group.add(b);
      }
    }
  }
  // Globe lights on wires overhead, purple and blue; green LEDs along the stage.
  const runs: { from: Vector3; to: Vector3; sag: number }[] = [];
  for (const [a, b] of [
    [new Vector3(-8, 5.5, 14), new Vector3(8, 5.2, -1)],
    [new Vector3(-8, 5.2, 0), new Vector3(8, 5.5, 13)],
    [new Vector3(-9, 5.0, 6), new Vector3(9, 5.0, 6)],
  ] as [Vector3, Vector3][]) runs.push({ from: toWorld(a), to: toWorld(b), sag: 0.9 });
  const globes = stringLights(runs, { spacing: 1.1, color: new Color(0.65, 0.25, 1), brightness: 14, size: 0.09, glowEvery: 1, glowRadius: 3.2, glowIntensity: 0.12 });
  const blues = stringLights(runs.map((r) => ({ from: r.from.clone().add(new Vector3(0.5, 0, 0)), to: r.to.clone().add(new Vector3(0.5, 0, 0)), sag: r.sag })), { spacing: 3.3, color: new Color(0.2, 0.45, 1), brightness: 14, size: 0.09, glowEvery: 1, glowRadius: 3, glowIntensity: 0.1 });
  const leds = stringLights([{ from: toWorld(new Vector3(-9, 0.3, 1.6)), to: toWorld(new Vector3(9, 0.3, 1.6)), sag: 0 }], { spacing: 0.25, color: new Color(0.2, 1, 0.3), brightness: 10, glowEvery: 2, glowRadius: 1.2, glowIntensity: 0.2 });
  objects.push(globes.mesh, blues.mesh, leds.mesh);
  // Poles for the wires.
  const poleMat = hallow(new MeshStandardMaterial({ color: 0x222222, roughness: 0.8 }), { key: 'pole-dark' });
  const poles = new InstancedMesh(new BoxGeometry(0.1, 5.6, 0.1), poleMat, runs.length * 2);
  runs.forEach((r, i) => {
    poles.setMatrixAt(i * 2, new Matrix4().makeTranslation(r.from.x, 2.8, r.from.z));
    poles.setMatrixAt(i * 2 + 1, new Matrix4().makeTranslation(r.to.x, 2.8, r.to.z));
  });
  poles.computeBoundingSphere();
  objects.push(poles);

  const screenCentre = toWorld(new Vector3(0, 2.5, 0.5));
  let time = 0;
  return {
    objects,
    seat: seats[4] as Vector3,
    glow: [
      ...globes.lights,
      ...blues.lights,
      ...leds.lights,
      { x: screenCentre.x, z: screenCentre.z + 0, radius: 9, color: new Color(1, 0.85, 0.6), intensity: 0.25, flicker: 0.3 },
    ],
    sources: [{ position: toWorld(new Vector3(0, 2, 4)), color: new Color(1, 0.88, 0.7), intensity: 3, distance: 12 }],
    update(dt) {
      time += dt;
      film.uniforms.uTime!.value = time;
    },
    pick(ray: Ray) {
      for (const s of seats) {
        if (ray.distanceSqToPoint(pointOnGround(s.clone().setY(0.45))) < 0.5) {
          return () => {
            const w = ctx.walker;
            w.position.set(s.x, heightAt(s.x, s.z), s.z);
            w.yaw = Math.atan2(-(screenCentre.x - s.x), -(screenCentre.z - s.z));
            w.pitch = 0.08;
            w.seated = true;
            w.auto = false;
            ctx.ui.say('The picture show. Move to get up again.', 4);
            void ctx.audio.setScene('picture-show', 'projector', 3);
          };
        }
      }
      return null;
    },
    dispose() {
      film.dispose();
      globes.mesh.geometry.dispose();
      blues.mesh.geometry.dispose();
      leds.mesh.geometry.dispose();
    },
  };
}
