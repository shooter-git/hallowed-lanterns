import {
  AdditiveBlending,
  BufferGeometry,
  type Camera,
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
import { instanceModel, type LoadedModel, loadModel } from '../engine/models.ts';
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

const UP = new Vector3(0, 1, 0);
const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
const smooth = (x: number) => {
  const t = clamp01(x);
  return t * t * (3 - 2 * t);
};
const wrap = (a: number) => Math.atan2(Math.sin(a), Math.cos(a));
/** A dash: up to speed over the first `a` of the way, flat out, then braking over the last `b`. */
function dash(u: number, a: number, b: number): number {
  if (u <= 0) return 0;
  if (u >= 1) return 1;
  const all = 1 - a / 2 - b / 2;
  if (u < a) return (u * u) / (2 * a) / all;
  if (u < 1 - b) return (a / 2 + u - a) / all;
  return (all - ((1 - u) * (1 - u)) / (2 * b)) / all;
}
/** Keyframes [seconds, value…]: column `c` at time t, eased in and out between keys. */
function keyed(keys: number[][], c: number, t: number): number {
  let i = 0;
  while (i < keys.length - 2 && t >= (keys[i + 1]?.[0] as number)) i++;
  const a = keys[i] as number[];
  const b = keys[i + 1] as number[];
  return (a[c] as number) + ((b[c] as number) - (a[c] as number)) * smooth((t - (a[0] as number)) / ((b[0] as number) - (a[0] as number)));
}

interface Pose {
  x: number;
  z: number;
  yaw: number;
}

interface SpiderLeg {
  femur: Object3D;
  tibia: Object3D;
  /** The hip, the leg's outward (level) direction and the axis that lifts it: in the body's frame. */
  hip: Vector3;
  out: Vector3;
  axis: Vector3;
  upper: number;
  lower: number;
  /** At rest: the femur's angle above level and the lower leg's angle to the femur. */
  rise: number;
  bend: number;
  /** Where the foot stands (body frame) and where it is now (world, on the ground). */
  home: Vector3;
  foot: Vector3;
  step: { from: Vector3; to: Vector3; t: number; time: number; height: number } | null;
  /** Poses on top of standing: the femur raised, the knee opened, the leg turned. */
  raise: number;
  open: number;
  turn: number;
  /** Which set of four it steps with, the step it's on, and which way is forward for its turn. */
  set: number;
  cycle: number;
  fore: number;
}

interface Walk {
  from: Pose;
  to: Pose;
  t: number;
  time: number;
  period: number;
  swing: number;
  height: number;
  low: number;
  bob: number;
  ease: (u: number) => number;
}

/** Legs 0-3 run down the spider's right (+x) front to back, 4-7 its left: L1 R2 L3 R4 step together, then R1 L2 R3 L4. */
const TETRAPOD = [1, 0, 1, 0, 0, 1, 0, 1];

/**
 * The pumpkin spider. Like a real one it is mostly perfectly still: now and then it shifts a foot
 * or feels about with a front leg. Tapped, it bolts a short way on the alternating gait, stops dead,
 * rears its front legs at you and, a while later, creeps back to its place. Its feet stay where
 * they're planted: each leg reaches its foot with a hip that swings and lifts and a knee that bends.
 */
function pumpkinSpider(model: LoadedModel, home: Pose, away: (from: Pose) => Pose) {
  const root = model.root;
  const legs: SpiderLeg[] = [];
  for (let k = 0; k < 8; k++) {
    const femur = model.node(`leg_${k}`);
    const tibia = model.node(`tibia_${k}`);
    const foot = model.node(`foot_${k}`);
    if (!femur || !tibia || !foot) continue;
    const knee = tibia.position.clone();
    const toe = knee.clone().add(foot.position);
    const out = new Vector3(toe.x, 0, toe.z).normalize();
    const along = (v: Vector3) => v.x * out.x + v.z * out.z;
    const rise = Math.atan2(knee.y, along(knee));
    legs.push({
      femur,
      tibia,
      hip: femur.position.clone(),
      out,
      axis: out.clone().cross(UP),
      upper: knee.length(),
      lower: foot.position.length(),
      rise,
      bend: Math.atan2(toe.y - knee.y, along(toe) - along(knee)) - rise,
      home: femur.position.clone().add(toe),
      foot: new Vector3(),
      step: null,
      raise: 0,
      open: 0,
      turn: 0,
      set: TETRAPOD[k] as number,
      cycle: 0,
      fore: out.x > 0 ? -1 : 1,
    });
  }
  const front = legs.filter((l) => l.home.z > 1.5);
  const second = legs.filter((l) => l.home.z > 0.5 && l.home.z <= 1.5);
  const baby = model.node('baby');
  const babyRest = baby?.position.clone();

  // Where the body is (x, z, yaw from walking; height and tilt from the gait and the rearing).
  const body = { ...home, y: 0, pitch: 0, roll: 0 };
  root.position.set(body.x, 0, body.z);
  root.rotation.set(0, body.yaw, 0, 'YXZ');
  const standAt = (l: SpiderLeg, p: Pose, out = new Vector3()) =>
    out.copy(l.home).applyAxisAngle(UP, p.yaw).add(new Vector3(p.x, 0, p.z));
  for (const l of legs) standAt(l, body, l.foot);
  const stepTo = (l: SpiderLeg, to: Vector3, time: number, height: number) => {
    l.step = { from: l.foot.clone(), to, t: 0, time, height };
  };

  // Idle: a foot shifted, or a front leg feeling about and tapping the ground.
  let fidget = 2 + Math.random() * 4;
  let feel: { leg: SpiderLeg; t: number; time: number; taps: number[] } | null = null;
  let state: 'home' | 'bolt' | 'rear' | 'wait' | 'creep' = 'home';
  let clock = 0;
  let wait = 0;
  let walk: Walk | null = null;
  const walkAt = (w: Walk, t: number): Pose => {
    const u = w.ease(clamp01(t / w.time));
    return { x: w.from.x + (w.to.x - w.from.x) * u, z: w.from.z + (w.to.z - w.from.z) * u, yaw: w.from.yaw + wrap(w.to.yaw - w.from.yaw) * u };
  };
  const setOff = (to: Pose, fast: boolean) => {
    const from = { x: body.x, z: body.z, yaw: body.yaw };
    const dist = Math.hypot(to.x - from.x, to.z - from.z);
    // Bolting: crouched, quick short steps, flat out and stopping dead, about as long as its
    // scurrying sound (1 s). Creeping home: slow, careful steps.
    walk = fast
      ? { from, to, t: 0, time: Math.min(1.05, Math.max(0.7, 0.55 + dist * 0.3)), period: 0.26, swing: 0.48, height: 0.3, low: 0.08, bob: 0.03, ease: (u) => dash(u, 0.14, 0.05) }
      : { from, to, t: 0, time: Math.max(3, dist / 0.32), period: 1.15, swing: 0.4, height: 0.2, low: 0.03, bob: 0.015, ease: (u) => dash(u, 0.25, 0.25) };
    // The set that steps first goes at once, the other half a stride later.
    for (const l of legs) l.cycle = l.set ? 0 : -1;
    feel = null;
  };

  // Lag from the body's starts and stops (a tilt), for the body and, looser, for the baby.
  const lag = { x: 0, z: 0, vx: 0, vz: 0 };
  const babyLag = { x: 0, z: 0, vx: 0, vz: 0 };
  let last = { x: body.x, z: body.z, vx: 0, vz: 0 };
  const q = new Quaternion();
  const d = new Vector3();
  const local = new Vector3();
  const inverse = new Matrix4();

  return {
    get position() {
      return root.position;
    },
    /** Tapped: bolts (unless it's already running or rearing). Returns whether it did. */
    tap(): boolean {
      if (state === 'bolt' || state === 'rear') return false;
      setOff(away({ x: body.x, z: body.z, yaw: body.yaw }), true);
      state = 'bolt';
      clock = 0;
      return true;
    },
    update(dt: number) {
      dt = Math.min(dt, 0.1);
      clock += dt;
      // What it's doing.
      if (state === 'bolt' || state === 'creep') {
        const w = walk as Walk;
        w.t += dt;
        const phase = w.t / w.period;
        for (const l of legs) {
          const n = Math.floor(phase + (l.set ? 0.5 : 0));
          if (n <= l.cycle) continue;
          l.cycle = n;
          if (w.t >= w.time) continue;
          // Plant where its spot will be halfway through the coming stance.
          const time = w.period * w.swing;
          const to = standAt(l, walkAt(w, w.t + time + (w.period - time) / 2));
          if (to.distanceTo(l.foot) > 0.03) stepTo(l, to, time, w.height);
        }
        Object.assign(body, walkAt(w, w.t));
        if (w.t >= w.time && legs.every((l) => !l.step)) {
          walk = null;
          clock = 0;
          if (state === 'bolt') {
            state = 'rear';
          } else {
            state = 'home';
            fidget = 1.5 + Math.random() * 2;
          }
        }
      } else if (state === 'rear' && clock > 2.3) {
        state = 'wait';
        clock = 0;
        wait = 2.5 + Math.random() * 2;
      } else if (state === 'wait' && clock > wait && !feel && legs.every((l) => !l.step)) {
        state = 'creep';
        clock = 0;
        setOff(home, false);
      }
      // Fidgets, when it's standing about.
      if (legs.length && (state === 'home' || (state === 'wait' && clock > 0.8)) && !feel && legs.every((l) => !l.step)) {
        fidget -= dt;
        if (fidget <= 0) {
          fidget = 2.5 + Math.random() * 5;
          const off = legs.map((l) => standAt(l, body).distanceTo(l.foot));
          const worst = off.indexOf(Math.max(...off));
          if (Math.random() < 0.45 && front.length) {
            // Feel about with a front leg: up, a slow reach, two or three taps.
            const leg = front[Math.floor(Math.random() * front.length)] as SpiderLeg;
            const time = 2.6 + Math.random() * 1.6;
            const taps = Math.random() < 0.5 ? [0.4, 0.6] : [0.33, 0.5, 0.67];
            feel = { leg, t: 0, time, taps };
          } else {
            // Shift a foot: the one furthest from where it would stand, or any but the front pair.
            const others = legs.filter((l) => !front.includes(l));
            const leg = (off[worst] as number) > 0.09 ? (legs[worst] as SpiderLeg) : (others[Math.floor(Math.random() * others.length)] as SpiderLeg);
            const to = standAt(leg, body).add(new Vector3((Math.random() - 0.5) * 0.16, 0, (Math.random() - 0.5) * 0.16));
            stepTo(leg, to, 0.32, 0.14);
          }
        }
      }

      // The feet in the air.
      for (const l of legs) {
        const s = l.step;
        if (!s) continue;
        s.t = Math.min(1, s.t + dt / s.time);
        l.foot.lerpVectors(s.from, s.to, smooth(s.t));
        l.foot.y += Math.sin(Math.PI * Math.pow(s.t, 0.8)) * s.height;
        if (s.t >= 1) l.step = null;
      }

      // Extra poses: rearing up at you, or feeling about.
      const rear = state === 'rear' ? smooth((clock - 0.18) / 0.3) * (1 - smooth((clock - 1.75) / 0.5)) : 0;
      if (feel) {
        feel.t += dt;
        if (feel.t >= feel.time) feel = null;
      }
      for (const l of legs) {
        let raise = 0;
        let open = 0;
        let turn = 0;
        if (rear > 0 && front.includes(l)) {
          // Front legs up and toward you, waving slowly; the next pair braced a little higher.
          const wave = Math.sin(clock * 2.4 + l.fore * 1.3) * 0.08;
          raise = rear * (0.7 + wave);
          open = rear * (0.55 - wave * 0.5);
          turn = rear * 0.3 * l.fore;
        } else if (rear > 0 && second.includes(l)) {
          raise = rear * 0.1;
          turn = rear * 0.1 * l.fore;
        }
        if (feel && feel.leg === l) {
          const u = feel.t / feel.time;
          const up = smooth(u / 0.18) * (1 - smooth((u - 0.8) / 0.2));
          const tap = Math.min(1, 1.6 * Math.max(...feel.taps.map((c) => Math.exp(-(((u - c) / 0.05) ** 2)))));
          raise += up * 0.13 * (1 - tap);
          open += up * 0.12 * (1 - tap);
          turn += up * l.fore * (0.04 + 0.06 * Math.sin(u * 4.5));
        }
        const k = 1 - Math.exp(-dt * 24);
        l.raise += (raise - l.raise) * k;
        l.open += (open - l.open) * k;
        l.turn += (turn - l.turn) * k;
      }

      // The body: low and bobbing with the steps as it runs, up and back as it rears, and a lurch
      // as it sets off and stops dead.
      const w = walk as Walk | null;
      const going = w ? smooth(w.t / 0.12) * (1 - smooth((w.t - w.time + 0.05) / 0.08)) : 0;
      const phase = w ? w.t / w.period : 0;
      body.y = w ? going * (-w.low + w.bob * Math.sin(Math.PI * 2 * phase) ** 2) : 0;
      body.y += rear * 0.07;
      const vx = (body.x - last.x) / Math.max(dt, 1e-4);
      const vz = (body.z - last.z) / Math.max(dt, 1e-4);
      // The change in velocity, turned into the body's frame.
      const cos = Math.cos(body.yaw);
      const sin = Math.sin(body.yaw);
      const dvx = vx - last.vx;
      const dvz = vz - last.vz;
      const ax = dvx * cos - dvz * sin;
      const az = dvx * sin + dvz * cos;
      last = { x: body.x, z: body.z, vx, vz };
      for (const [s, f, damp] of [
        [lag, 15, 11],
        [babyLag, 9, 4],
      ] as const) {
        s.vx -= ax;
        s.vz -= az;
        // In small steps, so the spring stays steady however slowly the frames come.
        const steps = Math.ceil(dt / 0.016);
        const h = dt / steps;
        for (let k = 0; k < steps; k++) {
          s.vx += (-f * f * s.x - damp * s.vx) * h;
          s.vz += (-f * f * s.z - damp * s.vz) * h;
          s.x += s.vx * h;
          s.z += s.vz * h;
        }
        if (!Number.isFinite(s.x + s.z + s.vx + s.vz)) s.x = s.z = s.vx = s.vz = 0;
      }
      body.pitch = Math.max(-0.12, Math.min(0.12, lag.z * 1.1)) - rear * 0.08;
      body.roll = Math.max(-0.1, Math.min(0.1, -lag.x * 1.1)) + (w ? going * Math.sin(Math.PI * 2 * phase) * 0.02 : 0);

      root.position.set(body.x, body.y, body.z);
      root.rotation.set(body.pitch, body.yaw, body.roll, 'YXZ');
      root.updateMatrix();
      inverse.copy(root.matrix).invert();

      // Each leg reaches its foot: turn the hip toward it, then hip and knee as a two-bone reach.
      for (const l of legs) {
        local.copy(l.foot).applyMatrix4(inverse);
        d.subVectors(local, l.hip);
        const reach = Math.hypot(d.x, d.z);
        const yaw = wrap(Math.atan2(-d.z, d.x) - Math.atan2(-l.out.z, l.out.x));
        const far = Math.min(l.upper + l.lower - 0.01, Math.max(Math.abs(l.upper - l.lower) + 0.01, Math.hypot(reach, d.y)));
        const a1 = Math.atan2(d.y, reach) + Math.acos(Math.min(1, Math.max(-1, (l.upper * l.upper + far * far - l.lower * l.lower) / (2 * l.upper * far))));
        const a2 = Math.atan2(d.y - l.upper * Math.sin(a1), reach - l.upper * Math.cos(a1));
        l.femur.quaternion.setFromAxisAngle(UP, yaw + l.turn).multiply(q.setFromAxisAngle(l.axis, a1 - l.rise + l.raise));
        l.tibia.quaternion.setFromAxisAngle(l.axis, a2 - a1 - l.bend + l.open);
      }

      // The baby holds on: it rocks with the starts and stops and bobs with the steps.
      if (baby && babyRest) {
        baby.rotation.x = Math.max(-0.25, Math.min(0.25, babyLag.z * 2.2));
        baby.rotation.z = Math.max(-0.25, Math.min(0.25, -babyLag.x * 2.2));
        baby.position.y = babyRest.y + (w ? going * Math.abs(Math.sin(Math.PI * 2 * phase)) * 0.025 : 0);
      }
    },
  };
}

/**
 * The mantis sits praying. Now and then it rocks from side to side like a leaf in a breeze; it
 * watches you, with a tilt of the head now and then. Tapped, it strikes: a twitch back, the
 * forelegs whip out, the claws snap shut (with the click), it holds its catch to its mouth for a
 * nibble, then folds back to praying.
 */
function prayingMantis(model: LoadedModel, camera: Camera, click: () => void) {
  const thorax = model.node('thorax');
  const abdomen = model.node('abdomen');
  const head = model.node('head');
  const arms = ['L', 'R'].map((s) => ({ coxa: model.node(`foreleg_${s}`), femur: model.node(`femur_${s}`), tibia: model.node(`tibia_${s}`) }));
  const antennae = ['L', 'R'].map((s, i) => ({ node: model.node(`antenna_${s}`), kick: 0, flick: 0, side: i ? 1 : -1 }));
  if (head) head.rotation.order = 'YXZ';
  if (thorax) thorax.rotation.order = 'YXZ';
  // The strike, in seconds from the tap: [t, lean, coxa, femur, tibia, nod]. The forelegs are
  // modelled folded (all 0): the coxa swings forward with -, the femur opens away from it with +,
  // the claw (tibia) opens with - and shuts with +.
  // A deliberate wind-up you can see, a quarter-second reach, then the snap.
  const STRIKE = [
    [0, 0, 0, 0, 0, 0],
    [0.35, -0.08, 0.2, -0.12, -0.35, -0.08],
    [0.6, 0.2, -0.95, 1.85, -1.5, 0.14],
    [0.72, 0.15, -0.55, 0.62, 0.16, 0.12],
    [0.8, 0.13, -0.5, 0.52, -0.07, 0.1],
    [0.9, 0.12, -0.48, 0.5, 0.03, 0.1],
    [1.01, 0.1, -0.45, 0.48, 0, 0.12],
    [1.65, 0.08, -0.42, 0.45, 0, 0.12],
    [2.85, 0, 0, 0, 0, 0],
  ];
  const SNAP = 0.72;
  const HELD = 1.7; // past the hold: a tap now strikes again as it lets go
  const now = [0, 0, 0, 0, 0];
  let strike = -1;
  let clicked = false;
  let queued = false;
  let time = 0;
  // Rocking: bouts of a few slow sways, now and then.
  let rock = 0;
  let rockPhase = 0;
  let rockFor = 0;
  let nextRock = 2 + Math.random() * 4;
  let tilt = 0;
  let tiltTo = 0;
  let nextTilt = 3 + Math.random() * 4;
  let nextFlick = 1 + Math.random() * 3;
  const begin = () => {
    // From wherever it is now (it may still be folding back from the last one).
    STRIKE[0] = [0, ...now];
    strike = 0;
    clicked = false;
    queued = false;
  };
  return {
    /** Tapped: strikes; tapped again once it's past the snap, it strikes again as it lets go. */
    tap() {
      if (strike < 0 || strike > HELD) begin();
      else if (strike > SNAP + 0.1) queued = true;
    },
    update(dt: number) {
      dt = Math.min(dt, 0.1);
      time += dt;
      if (strike >= 0) {
        strike += dt;
        if (!clicked && strike >= SNAP) {
          clicked = true;
          click();
        }
        if (strike >= (STRIKE[STRIKE.length - 1]?.[0] as number)) strike = -1;
      }
      if (queued && strike > HELD) begin();
      const s = Math.max(strike, 0);
      for (let c = 0; c < 5; c++) now[c] = strike >= 0 ? keyed(STRIKE, c + 1, s) : 0;
      // A nibble at what it caught: the claws grip twice and the head dips.
      const pulse = (at: number, width: number) => (strike >= 0 ? Math.exp(-(((s - at) / width) ** 2)) : 0);
      const grip = (pulse(SNAP + 0.15, 0.025) + pulse(SNAP + 0.225, 0.025)) * 0.07;
      const nibble = pulse(SNAP + 0.5, 0.06) * 0.14;
      // Still while it strikes (settling out of a sway as it winds up), back to itself as it folds.
      const calm = strike >= 0 ? Math.max(1 - smooth(s / 0.3), smooth((s - 1.75) / 1.1)) : 1;

      // Rocking like a leaf, now and then.
      nextRock -= dt;
      if (nextRock <= 0 && rockFor <= 0 && strike < 0) {
        rockFor = 2 + Math.random() * 2.5;
        nextRock = rockFor + 3 + Math.random() * 6;
      }
      rockFor -= dt;
      rock += ((rockFor > 0 ? 1 : 0) - rock) * (1 - Math.exp(-dt * 2.2));
      rockPhase += dt * Math.PI * 2 * (1.05 + 0.25 * Math.sin(time * 0.7));
      const sway = rock * calm * (Math.sin(rockPhase) + 0.2 * Math.sin(rockPhase * 2 + 0.6));
      if (thorax) thorax.rotation.set(now[0] as number, sway * 0.025, sway * 0.07);
      if (abdomen) {
        abdomen.rotation.x = Math.max(0, now[0] as number) * 0.2;
        abdomen.rotation.y = -sway * 0.035;
      }
      arms.forEach((a, i) => {
        // The forelegs sway a touch behind the body.
        const side = i ? 1 : -1;
        if (a.coxa) a.coxa.rotation.set(now[1] as number, 0, -sway * 0.02 * side);
        if (a.femur) a.femur.rotation.x = now[2] as number;
        if (a.tibia) a.tibia.rotation.x = (now[3] as number) + grip;
      });

      // The head follows you, with a curious tilt now and then.
      nextTilt -= dt;
      if (nextTilt <= 0) {
        tiltTo = tiltTo ? 0 : (Math.random() < 0.5 ? -1 : 1) * (0.2 + Math.random() * 0.15);
        nextTilt = tiltTo ? 1 + Math.random() * 1.8 : 3 + Math.random() * 6;
      }
      tilt += (tiltTo - tilt) * (1 - Math.exp(-dt * 5));
      if (head && thorax) {
        const at = thorax.worldToLocal(camera.position.clone()).sub(head.position);
        const want = Math.max(-0.7, Math.min(0.7, Math.atan2(at.x, at.z)));
        head.rotation.y += (want - head.rotation.y) * (1 - Math.exp(-dt * 1.5));
        head.rotation.x = (now[4] as number) + nibble;
        head.rotation.z = tilt - sway * 0.04;
      }

      // Antennae: a slow drift, a flick now and then, swept back as it strikes.
      nextFlick -= dt;
      if (nextFlick <= 0) {
        nextFlick = 0.8 + Math.random() * 3.5;
        const a = antennae[Math.floor(Math.random() * 2)];
        if (a) a.kick = (Math.random() - 0.3) * 0.5;
      }
      const back = strike >= 0 ? pulse(0.6, 0.2) * 0.4 : 0;
      for (const a of antennae) {
        a.flick += (a.kick - a.flick) * (1 - Math.exp(-dt * 30));
        a.kick *= Math.exp(-dt * 3);
        if (a.node) {
          a.node.rotation.x = Math.sin(time * 0.8 + a.side) * 0.05 + a.flick - back;
          a.node.rotation.z = Math.sin(time * 0.6 + a.side * 2) * 0.05 + a.flick * 0.5 * a.side;
        }
      }
    },
  };
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
  // Tapped, the spider bolts this far along the web, away from you.
  const ROAM = 1.4;
  // Keep strands and pumpkins out of the two creatures (and of where the spider runs to).
  const free = (x: number, z: number) => !(x < -1.6 && Math.abs(z - SPIDER.z) < 3.8 + ROAM) && !(x > 2.4 && Math.abs(z - MANTIS.z) < 2);
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
  let crawler: ReturnType<typeof pumpkinSpider> | null = null;
  if (spider) {
    objects.push(spider.root);
    for (const m of spider.glows.values()) m.emissiveIntensity = 2.5;
    const homeYaw = yaw + Math.PI / 2 - 0.15;
    const at = toWorld(SPIDER);
    // Its spots: home, or a little way along the web either side, a touch further back.
    const spots = [SPIDER, SPIDER.clone().add(new Vector3(-0.15, 0, -ROAM)), SPIDER.clone().add(new Vector3(-0.15, 0, ROAM))].map(toWorld);
    crawler = pumpkinSpider(spider, { x: at.x, z: at.z, yaw: homeYaw }, (from) => {
      // The spot furthest from you (that isn't where it is), turned a little toward you.
      const eye = ctx.camera.position;
      const spot = spots
        .filter((p) => Math.hypot(p.x - from.x, p.z - from.z) > 0.8)
        .reduce((a, b) => (Math.hypot(b.x - eye.x, b.z - eye.z) > Math.hypot(a.x - eye.x, a.z - eye.z) ? b : a));
      const facing = wrap(Math.atan2(eye.x - spot.x, eye.z - spot.z) - homeYaw);
      return { x: spot.x, z: spot.z, yaw: homeYaw + (spot === spots[0] ? 0 : Math.max(-0.22, Math.min(0.22, facing))) };
    });
  }
  const mantis = await loadModel('praying-mantis', { glowReceive: 0.6 });
  let praying: ReturnType<typeof prayingMantis> | null = null;
  if (mantis) {
    mantis.root.position.copy(toWorld(MANTIS));
    mantis.root.rotation.y = yaw - Math.PI / 2 + 0.35;
    objects.push(mantis.root);
    for (const m of mantis.glows.values()) m.emissiveIntensity = 2.2;
    // The click is the claws snapping shut.
    praying = prayingMantis(mantis, ctx.camera, () => void ctx.audio.sfx('mantis-click', { at: pointOnGround(mantis.root.position.clone().setY(1.8)), volume: 0.8 }));
  }

  // Pumpkins wrapped in web, with little neon spiders on them, hanging on threads from the web.
  const hangAt: Vector3[] = [];
  for (let tries = 0; hangAt.length < 12 && tries < 800; tries++) {
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
  return {
    objects,
    snare,
    hooks,
    glow: [
      ...leds.lights,
      ...[-4, 0, 4].map((z) => {
        const p = toWorld(new Vector3(0, 0, z));
        return { x: p.x, z: p.z, y: 2, radius: 6, color: new Color(0.5, 0.25, 1), intensity: 0.55, flicker: 0 };
      }),
    ],
    sources: [
      { position: toWorld(new Vector3(0, 3, 0)), color: new Color(0.55, 0.3, 1), intensity: 8, distance: 12 },
      { position: toWorld(SPIDER.clone().add(new Vector3(2.2, 2.2, 0))), color: new Color(0.6, 0.35, 1), intensity: 6, distance: 8 },
      { position: toWorld(MANTIS.clone().add(new Vector3(-1.6, 2.4, 0))), color: new Color(0.55, 0.4, 1), intensity: 4, distance: 6 },
    ],
    update(dt) {
      crawler?.update(dt);
      praying?.update(dt);
      pumpkins?.update(ctx.camera, dt);
    },
    pick(ray: Ray) {
      // Whatever you tapped that's nearest along your line of sight (the snare is behind the
      // mantis from some places).
      const hits: { at: Vector3; act: () => void }[] = [];
      // Free the Ember: tap the web where it's caught.
      if (!freed && ray.distanceSqToPoint(pointOnGround(snare)) < 1.2) {
        hits.push({
          at: pointOnGround(snare),
          act: () => {
            freed = true;
            void ctx.audio.sfx('web-stretch', { at: pointOnGround(snare), volume: 0.9 });
            hooks.onFree?.();
          },
        });
      }
      // (The spider is wherever it has run to.)
      const spiderAt = crawler ? pointOnGround(crawler.position.clone().setY(2)) : null;
      if (crawler && spiderAt && ray.distanceSqToPoint(spiderAt) < 4) {
        const c = crawler;
        hits.push({
          at: spiderAt,
          act: () => {
            if (c.tap()) void ctx.audio.sfx('spider-scurry', { at: spiderAt, volume: 0.8 });
          },
        });
      }
      const mantisAt = mantis ? pointOnGround(mantis.root.position.clone().setY(2)) : null;
      if (mantisAt && praying && ray.distanceSqToPoint(mantisAt) < 2.5) {
        const p = praying;
        hits.push({ at: mantisAt, act: () => p.tap() });
      }
      if (hits.length) {
        const along = (h: { at: Vector3 }) => h.at.clone().sub(ray.origin).dot(ray.direction);
        hits.sort((a, b) => along(a) - along(b));
        return (hits[0] as { act: () => void }).act;
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
