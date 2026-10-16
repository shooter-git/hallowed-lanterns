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
 * longhorn, an owl, a spider on its thread), drawn live in the shader on a warm, flickering screen.
 */

const FILM = /* glsl */ `
uniform float uTime;
uniform float uOn;
varying vec2 vUv;
// Shapes are drawn in q: x across the screen (it's 5:3, so 1.667 wide), y up, 0..1.
const float AR = 1.667;
float sdCircle(vec2 p, float r) { return length(p) - r; }
float sdBox(vec2 p, vec2 b) { vec2 d = abs(p) - b; return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0); }
float sdSeg(vec2 p, vec2 a, vec2 b, float r) { vec2 pa = p - a, ba = b - a; float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0); return length(pa - ba * h) - r; }
float sdTri(vec2 p, float r) { const float k = 1.7320508; p.x = abs(p.x) - r; p.y = p.y + r / k; if (p.x + k * p.y > 0.0) p = vec2(p.x - k * p.y, -k * p.x - p.y) / 2.0; p.x -= clamp(p.x, -2.0 * r, 0.0); return -length(p) * sign(p.y); }
float smin(float a, float b, float k) { float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0); return mix(b, a, h) - k * h * (1.0 - h); }
float fill(float d) { return smoothstep(0.003, -0.003, d); }
float hills(vec2 q) { return q.y - (0.2 + 0.03 * sin(q.x * 5.0 + 1.0) + 0.02 * sin(q.x * 11.0)); }

// A jack-o'-lantern: ribbed body, stem, and a carved face that lets the light through.
float jack(vec2 q, float s) {
  vec2 p = q / s;
  float body = smin(sdCircle((p - vec2(-0.42, 0.0)) * vec2(1.0, 1.08), 0.68), sdCircle((p - vec2(0.42, 0.0)) * vec2(1.0, 1.08), 0.68), 0.3);
  body = smin(body, sdCircle(p * vec2(1.0, 1.04), 0.84), 0.2);
  float stem = sdSeg(p, vec2(0.0, 0.72), vec2(0.14, 1.06), 0.1);
  float eyes = min(sdTri((p - vec2(-0.36, 0.2)) / 0.3, 1.0) * 0.3, sdTri((p - vec2(0.36, 0.2)) / 0.3, 1.0) * 0.3);
  float grin = max(sdCircle(p - vec2(0.0, 0.02), 0.56), -sdCircle(p - vec2(0.0, 0.32), 0.62));
  return max(min(body, stem), -min(eyes, grin)) * s;
}
// A bare tree, leaning by side (+1 leans right), with a branch reaching in for the owl.
float tree(vec2 q, float x, float side) {
  float d = sdSeg(q, vec2(x, 0.1), vec2(x + side * 0.04, 1.1), 0.04);
  d = min(d, sdSeg(q, vec2(x + side * 0.02, 0.62), vec2(x - side * 0.24, 0.88), 0.018));
  d = min(d, sdSeg(q, vec2(x + side * 0.03, 0.78), vec2(x + side * 0.22, 1.0), 0.015));
  d = min(d, sdSeg(q, vec2(x - side * 0.12, 0.74), vec2(x - side * 0.2, 0.97), 0.011));
  return min(d, sdSeg(q, vec2(x + side * 0.01, 0.5), vec2(x + side * 0.24, 0.56), 0.014));
}
// An owl, sitting: round body, round head, ear tufts, two eyes of light (they close to blink).
float owl(vec2 q, float s, float blink) {
  vec2 p = q / s;
  float body = smin(sdCircle((p - vec2(0.0, -0.1)) * vec2(1.0, 0.78), 0.6), sdCircle(p - vec2(0.0, 0.62), 0.42), 0.15);
  body = min(body, min(sdSeg(p, vec2(-0.24, 0.9), vec2(-0.36, 1.2), 0.08), sdSeg(p, vec2(0.24, 0.9), vec2(0.36, 1.2), 0.08)));
  float eyes = min(sdCircle(p - vec2(-0.17, 0.64), 0.13), sdCircle(p - vec2(0.17, 0.64), 0.13));
  eyes = max(eyes, abs(p.y - 0.64) - 0.13 * (1.0 - blink));
  return max(body, -eyes) * s;
}
float bat(vec2 q, float s, float t) {
  vec2 p = q / s;
  float f = sin(t * 12.0);
  vec2 a = vec2(abs(p.x), p.y);
  float body = sdCircle(p * vec2(1.4, 1.0), 0.25);
  float wing = min(sdSeg(a, vec2(0.15, 0.0), vec2(0.9, 0.1 + 0.35 * f), 0.12), sdSeg(a, vec2(0.5, 0.1 + 0.2 * f), vec2(1.0, -0.1 + 0.3 * f), 0.08));
  return min(body, wing) * s;
}
// A longhorn walking right: body, hump, legs in stride, a tail, a lowered head and long horns.
float longhorn(vec2 q, float s, float t) {
  vec2 p = q / s;
  float body = smin(sdBox(p, vec2(0.85, 0.3)) - 0.18, sdCircle(p - vec2(-0.75, 0.1), 0.36), 0.2);
  body = smin(body, sdCircle(p - vec2(0.5, 0.3), 0.3), 0.2);
  float st = sin(t * 2.6) * 0.18;
  float legs = min(min(sdSeg(p, vec2(-0.62, -0.2), vec2(-0.62 + st, -1.0), 0.09), sdSeg(p, vec2(-0.36, -0.2), vec2(-0.36 - st, -1.0), 0.09)),
                   min(sdSeg(p, vec2(0.46, -0.2), vec2(0.46 - st, -1.0), 0.09), sdSeg(p, vec2(0.7, -0.2), vec2(0.7 + st, -1.0), 0.09)));
  float neck = sdSeg(p, vec2(0.85, 0.2), vec2(1.15, 0.18), 0.2);
  vec2 h = p - vec2(1.28, 0.05);
  float head = sdBox(vec2(h.x * 0.88 + h.y * 0.48, -h.x * 0.48 + h.y * 0.88), vec2(0.24, 0.13)) - 0.08;
  float horns = min(min(sdSeg(p, vec2(1.16, 0.36), vec2(1.72, 0.52), 0.045), sdSeg(p, vec2(1.72, 0.52), vec2(1.92, 0.84), 0.034)),
                    min(sdSeg(p, vec2(1.16, 0.36), vec2(0.66, 0.58), 0.045), sdSeg(p, vec2(0.66, 0.58), vec2(0.52, 0.88), 0.034)));
  float tail = sdSeg(p, vec2(-1.05, 0.18), vec2(-1.14, -0.5), 0.035);
  return min(min(min(body, legs), min(head, neck)), min(horns, tail)) * s;
}
// A cobweb in the top-left corner: spokes and rings.
float web(vec2 q) {
  vec2 d = q - vec2(-0.86, 1.02);
  float r = length(d);
  if (r > 0.62 || d.x < 0.0 || d.y > 0.0) return 1.0;
  float a = atan(-d.y, d.x);
  float spokes = abs(fract(a / 0.22) - 0.5) * 0.22 * r - 0.0025;
  float rings = max(abs(fract(r / 0.085) - 0.5) * 0.085 - 0.0028, r - 0.58);
  return min(spokes, rings);
}
float spider(vec2 q, float s, float t) {
  vec2 p = q / s;
  float body = smin(sdCircle(p - vec2(0.0, 0.25), 0.42), sdCircle(p - vec2(0.0, -0.32), 0.28), 0.1);
  vec2 a = vec2(abs(p.x), p.y);
  float legs = 1.0;
  for (int i = 0; i < 4; i++) {
    float fi = float(i);
    float y = 0.2 - fi * 0.18;
    vec2 knee = vec2(0.72, y + 0.36 + sin(t * 6.0 + fi) * 0.08);
    legs = min(legs, min(sdSeg(a, vec2(0.2, y), knee, 0.05), sdSeg(a, knee, vec2(1.08, y - 0.38), 0.04)));
  }
  return min(body, legs) * s;
}

void main() {
  vec2 p = vUv;
  vec2 q = vec2((p.x - 0.5) * AR, p.y);
  float t = mod(uTime, 64.0);
  float scene = floor(t / 16.0);
  float st = mod(t, 16.0);
  // The warm screen: brightest in the middle, flickering like an old projector.
  float flick = 0.92 + 0.06 * sin(uTime * 47.0) + 0.03 * sin(uTime * 13.0);
  vec3 screen = mix(vec3(0.5, 0.38, 0.27), vec3(1.0, 0.86, 0.64), smoothstep(0.85, 0.0, length((p - 0.5) * vec2(1.0, 1.3)))) * flick;
  vec3 moonLight = vec3(0.12, 0.09, 0.03);
  float d = hills(q);
  vec2 ep = vec2(-9.0);
  float inside = 0.0; // the Ember still inside its pumpkin: it shows only through the face
  vec2 moon = vec2(-9.0);
  if (scene < 0.5) {
    // Moonrise over three jack-o'-lanterns; the middle one's flame hops out.
    moon = vec2(0.5, 0.42 + st * 0.024);
    for (int i = 0; i < 3; i++) {
      float x = -0.45 + float(i) * 0.45;
      d = min(d, jack(q - vec2(x, 0.33), 0.11));
    }
    float hop = clamp((st - 7.5) / 7.0, 0.0, 1.0);
    if (st < 7.5) { ep = vec2(0.0, 0.31); inside = 1.0; }
    else ep = vec2(hop * 0.36, 0.38 + abs(sin(hop * 9.42)) * 0.16 * (1.0 - hop * 0.5) + hop * 0.14);
  } else if (scene < 1.5) {
    // Into the woods: trees on both sides, an owl blinking on a branch, bats crossing.
    d = min(d, min(tree(q, -0.62, 1.0), tree(q, 0.64, -1.0)));
    d = min(d, sdSeg(q, vec2(0.28, 0.1), vec2(0.3, 1.1), 0.022));
    float blink = step(fract(st * 0.27), 0.06);
    d = min(d, owl(q - vec2(-0.43, 0.63), 0.065, blink));
    for (int i = 0; i < 2; i++) d = min(d, bat(q - vec2(0.9 - fract(st * 0.06 + float(i) * 0.5) * 1.9, 0.82 + 0.04 * sin(st * 2.0 + float(i))), 0.05, st + float(i)));
    ep = vec2(-0.55 + st * 0.07, 0.42 + 0.04 * sin(st * 2.2));
  } else if (scene < 2.5) {
    // The giant: a longhorn walks across, and the Ember rides between its horns.
    moon = vec2(0.6, 0.8);
    vec2 lp = vec2(-1.15 + st * 0.085, 0.38);
    d = min(d, longhorn(q - lp, 0.16, st));
    ep = lp + vec2(1.22, 0.74) * 0.16;
  } else {
    // The web and the moon: a spider lowers itself; the Ember slips free and floats into the moon.
    moon = vec2(0.55, 0.78);
    d = min(d, web(q));
    float drop = min(1.0, st / 5.0) - clamp((st - 9.0) / 5.0, 0.0, 1.0);
    vec2 sp = vec2(0.05, 1.1 - drop * 0.46);
    d = min(d, sdSeg(q, vec2(sp.x, 1.05), sp + vec2(0.0, 0.04), 0.002));
    d = min(d, spider(q - sp, 0.075, st));
    float rise = clamp((st - 7.0) / 8.0, 0.0, 1.0);
    float wiggle = smoothstep(3.0, 4.0, st) * (1.0 - smoothstep(6.5, 7.0, st));
    ep = mix(vec2(0.08, 0.38), moon, rise * rise * (3.0 - 2.0 * rise)) + vec2(sin(st * 25.0) * 0.012 * wiggle, 0.0);
  }
  // The moon is part of the light, behind the shadows.
  if (moon.x > -5.0) {
    float m = sdCircle(q - moon, 0.11);
    screen += moonLight * 1.5 * smoothstep(0.12, 0.0, m);
    screen = mix(screen, screen * 1.45 + moonLight * 2.0, smoothstep(0.004, -0.004, m));
  }
  float shadow = fill(d);
  vec3 col = mix(screen, vec3(0.025, 0.02, 0.02), shadow);
  // The Ember: the only colour in the film, a bright little flame.
  if (ep.x > -5.0) {
    vec2 e = (q - ep) * vec2(1.0, 0.75);
    vec3 flame = vec3(1.0, 0.55, 0.15) * (smoothstep(0.03, 0.0, length(e)) * 3.0 + smoothstep(0.14, 0.0, length(e)) * 0.6);
    col += flame * mix(1.0, 1.0 - shadow, inside) * (inside > 0.5 ? 2.0 : 1.0);
  }
  // Scene changes fade through dark, like reels; grain and a scratch or two.
  float fade = smoothstep(0.0, 0.8, st) * smoothstep(16.0, 15.2, st);
  col *= mix(0.15, 1.0, fade);
  float g = fract(sin(dot(p * 300.0 + uTime, vec2(12.9898, 78.233))) * 43758.5453);
  col *= 0.94 + 0.06 * g;
  col *= 1.0 - smoothstep(0.996, 1.0, fract(p.x * 13.0 + floor(uTime * 8.0) * 0.37)) * 0.3;
  // A soft vignette, as the projector's beam falls off.
  col *= smoothstep(1.05, 0.45, length((p - 0.5) * vec2(1.2, 1.5)));
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
    // uFlip: the model's screen counts its texture from the top (as glTF does), the film from the
    // bottom.
    uniforms: { uTime: { value: 0 }, uOn: { value: 1 }, uFlip: { value: 0 } },
    vertexShader: /* glsl */ `varying vec2 vUv;
      uniform sampler2D uTerrain; uniform vec4 uTerrainBounds; uniform float uFlip;
      void main() { vUv = vec2(uv.x, mix(uv.y, 1.0 - uv.y, uFlip)); vec4 w = modelMatrix * vec4(position, 1.0);
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
    if (screen) {
      screen.material = film;
      film.uniforms.uFlip!.value = 1;
    }
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
      { x: screenCentre.x, z: screenCentre.z + 0, y: screenCentre.y, radius: 9, color: new Color(1, 0.85, 0.6), intensity: 0.25, flicker: 0.3 },
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
            // The film starts from its first scene as its music begins, so the music can score it.
            const fresh = ctx.audio.currentMusic !== 'picture-show';
            void ctx.audio.setScene('picture-show', 'projector', 3).then(() => {
              if (fresh) time = 0;
            });
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
