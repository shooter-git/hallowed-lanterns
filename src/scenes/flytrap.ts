import {
  AdditiveBlending,
  CanvasTexture,
  Color,
  ConeGeometry,
  CubicBezierCurve3,
  DoubleSide,
  Euler,
  Group,
  InstancedMesh,
  Matrix4,
  Mesh,
  MeshStandardMaterial,
  Object3D,
  OctahedronGeometry,
  Quaternion,
  type Ray,
  SphereGeometry,
  Sprite,
  SpriteMaterial,
  TubeGeometry,
  Vector3,
} from 'three';
import type { ChapterContext } from '../chapters/types.ts';
import { CARVE } from '../engine/carvings.ts';
import type { GlowLight } from '../engine/glowfield.ts';
import { stringLights } from '../engine/lanterns.ts';
import type { LightSource } from '../engine/lights.ts';
import { instanceModel, loadModel } from '../engine/models.ts';
import { Burst } from '../engine/particles.ts';
import { PumpkinField, type PumpkinSpec } from '../engine/pumpkins.ts';
import { hallow } from '../engine/shared.ts';
import { heightAt, pointOnGround } from '../engine/terrain.ts';
import type { SetPiece } from './types.ts';

/**
 * The giant fly-eating Venus flytrap: a trap head as wide as a car on a curving stem, green
 * outside and deep red inside, teeth along its lips, and ivy trailing down. Below it, hay bales
 * strung with teal lights and a few glowing pumpkins.
 *
 * A fly the size of a cat buzzes round the head in darts, hovers and little loops, then lands
 * upside down on the red roof of the mouth and walks to a trigger hair. The first touch stirs
 * the trap (its lobes quiver, its glow rises); the second and it snaps shut in a tenth of a
 * second, teeth interlocking, the jolt throwing the head back on its stem; spores puff from its
 * lips and the little traps snap in sympathy. The fly buzzes inside for a while, then the trap
 * digests in slow squeezes, its glow throbbing, and at last opens again, shakily and empty,
 * until another fly comes. Idle, the head breathes and sways on its stem and turns a little to
 * watch you; tap it while it's empty and it lunges at you and snaps at the air.
 */

/** The lobes hinge about their local x: open a little wider than modelled while waiting, and
 * shut this far past it (the big trap, then the little ones), before the teeth would clash. */
const OPEN = -0.17;
const SHUT = [0.227, 0.28];
/** How far shut the lobes are when the teeth first interlock (they seal later, digesting). */
const CAGE = 0.93;
/** The snap sound's clap comes this long after it starts (s, at rate 1). */
const CLAP = 0.19;
/** The lunge: when the bite starts (s into it), and how far the stem leans (rad). */
const BITE = 0.55;
const LUNGE = 0.62;
/** The fly's walk on the roof of the mouth: [seconds, how far from where it landed to the
 * trigger hair (0 … 1)]: a few steps, a pause, a step to the hair, a pause, a last step. */
const WALK: [number, number][] = [
  [0.7, 0],
  [1.9, 0.55],
  [2.7, 0.55],
  [3.2, 0.82],
  [4.1, 0.82],
  [4.45, 1],
];
/** When it touches the hair: once (the trap stirs), and again (it snaps). */
const TOUCH = 3.2;
const TOUCH_AGAIN = 4.45;

interface Lobe {
  node: Object3D;
  rest: number;
  sign: number;
}

/** A damped spring chasing its target (`hz` its natural frequency, `damp` its damping ratio). */
class Spring {
  x = 0;
  v = 0;
  target = 0;
  constructor(
    public hz: number,
    public damp: number,
  ) {}

  step(dt: number) {
    const w = 2 * Math.PI * this.hz;
    const n = Math.max(1, Math.ceil(dt * 240));
    const h = dt / n;
    for (let i = 0; i < n; i++) {
      this.v += (-w * w * (this.x - this.target) - 2 * this.damp * w * this.v) * h;
      this.x += this.v * h;
    }
  }
}

/** A soft round glow (white in the middle, fading to nothing). */
function haloTexture(): CanvasTexture {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d') as CanvasRenderingContext2D;
  const r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  r.addColorStop(0, 'rgba(255,255,255,1)');
  r.addColorStop(0.3, 'rgba(255,255,255,0.5)');
  r.addColorStop(0.65, 'rgba(255,255,255,0.12)');
  r.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = r;
  g.fillRect(0, 0, 64, 64);
  return new CanvasTexture(c);
}

const ease = (k: number) => (k <= 0 ? 0 : k >= 1 ? 1 : k * k * (3 - 2 * k));
/** A tremble: not quite periodic, so it never reads as a wobble. */
const tremor = (t: number) => Math.sin(t * 97) * 0.6 + Math.sin(t * 61 + 1) * 0.4;

/** After the snap, the teeth interlock and the lobes bounce open a hair, twice, and settle. */
const bounce = (t: number) => CAGE - 0.075 * Math.exp(-t / 0.09) * Math.abs(Math.sin(t * 34));

export async function flytrap(ctx: ChapterContext, at: Vector3, yaw: number): Promise<SetPiece> {
  const objects: Object3D[] = [];
  const toWorld = (v: Vector3) => v.clone().applyAxisAngle(new Vector3(0, 1, 0), yaw).add(at);
  const group = new Group();
  group.position.copy(at);
  group.rotation.y = yaw;
  objects.push(group);

  const model = await loadModel('venus-flytrap', { glowReceive: 0.7 });
  const lobes: Lobe[][] = []; // the big trap first, then the little ones
  const smallTraps: Object3D[] = [];
  const chain: Object3D[] = []; // the big trap's stem, from the ground up
  const vines: Object3D[] = []; // trailing from the ends of its hinge
  let trap: Object3D | undefined;
  let fly: Object3D | undefined;
  let wings: Object3D[] = [];
  let landAt: Object3D | undefined; // where the fly lands, and where it stops by the trigger hair
  let hairAt: Object3D | undefined;
  const glowMats: MeshStandardMaterial[] = [];
  const skinMats: MeshStandardMaterial[] = [];
  if (model) {
    group.add(model.root);
    group.updateMatrixWorld(true);
    for (const m of model.glows.values()) {
      m.emissiveIntensity = 1.4;
      glowMats.push(m);
    }
    model.root.traverse((o) => {
      const mat = (o as Mesh).material as MeshStandardMaterial | undefined;
      if ((o as Mesh).isMesh && mat?.name === 'trap_outer' && !skinMats.includes(mat)) skinMats.push(mat);
    });
    const trapLobes = (t: Object3D | undefined) => {
      if (!t) return null;
      const upper = t.getObjectByName('lobe_upper') ?? t.children.find((c) => /upper/i.test(c.name));
      const lower = t.getObjectByName('lobe_lower') ?? t.children.find((c) => /lower/i.test(c.name));
      return [upper, lower]
        .map((node, i) => (node ? { node, rest: node.rotation.x, sign: i === 0 ? 1 : -1 } : null))
        .filter((l): l is Lobe => l !== null);
    };
    trap = model.node('trap');
    const first = trapLobes(trap);
    if (first?.length) lobes.push(first);
    for (let k = 1; k < 6; k++) {
      const node = model.node(`trap_small_${k}`);
      const small = trapLobes(node);
      if (node && small?.length) {
        lobes.push(small);
        smallTraps.push(node);
      }
    }
    for (let k = 0; model.node(`stem_${k}`); k++) chain.push(model.node(`stem_${k}`) as Object3D);
    for (const n of ['vines_L', 'vines_R']) {
      const v = model.node(n);
      if (v) vines.push(v);
    }
    fly = model.node('fly');
    wings = ['wing_L', 'wing_R'].map((n) => model.node(n)).filter(Boolean) as Object3D[];
    landAt = model.node('fly_land');
    hairAt = model.node('fly_hair');
  } else {
    // A stand-in: a curving stem, two half-shell lobes (green outside, red within) with teeth, and
    // a dark fly between them.
    const stemMat = hallow(new MeshStandardMaterial({ color: 0x2f5a3a, roughness: 0.8 }), { key: 'trap-stem', glow: 1.2 });
    const stem = new Mesh(
      new TubeGeometry(new CubicBezierCurve3(new Vector3(0, 0, 0), new Vector3(-0.6, 1.4, 0), new Vector3(0.7, 2.6, 0.2), new Vector3(0, 3.6, 0.3)), 24, 0.16, 8),
      stemMat,
    );
    group.add(stem);
    const outer = hallow(new MeshStandardMaterial({ color: 0x3f8a6e, emissive: 0x0d3a2c, emissiveIntensity: 0.6, roughness: 0.6, side: DoubleSide }), { key: 'trap-outer', glow: 1.3 });
    const inner = new MeshStandardMaterial({ color: 0x400000, emissive: 0xff1a10, emissiveIntensity: 1.2, side: DoubleSide });
    const teethMat = hallow(new MeshStandardMaterial({ color: 0xd8e6c8, roughness: 0.6 }), { key: 'trap-teeth', glow: 1 });
    const head = new Group();
    head.position.set(0, 3.8, 0.3);
    group.add(head);
    const pair: Lobe[] = [];
    for (const side of [1, -1]) {
      const hinge = new Group();
      const shell = new Mesh(new SphereGeometry(1.3, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), outer);
      shell.scale.set(1, 0.55, 0.8);
      const lining = new Mesh(new SphereGeometry(1.26, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), inner);
      lining.scale.set(1, 0.52, 0.77);
      const teeth = new InstancedMesh(new ConeGeometry(0.035, 0.38, 5), teethMat, 26);
      for (let i = 0; i < 26; i++) {
        const a = (i / 26) * Math.PI * 2;
        teeth.setMatrixAt(i, new Matrix4().compose(new Vector3(Math.cos(a) * 1.3, 0.12, Math.sin(a) * 1.04), new Quaternion(), new Vector3(1, 1, 1)));
      }
      hinge.add(shell, lining, teeth);
      hinge.rotation.x = side > 0 ? -Math.PI / 2 + 0.5 : Math.PI / 2 - 0.5;
      head.add(hinge);
      pair.push({ node: hinge, rest: hinge.rotation.x, sign: side });
    }
    lobes.push(pair);
    glowMats.push(inner);
    trap = head;
    const flyMesh = new Mesh(new SphereGeometry(0.32, 16, 10), hallow(new MeshStandardMaterial({ color: 0x0a0a0c, roughness: 0.3, metalness: 0.3 }), { key: 'fly' }));
    flyMesh.position.set(0, 4.35, 0.3);
    group.add(flyMesh);
    fly = flyMesh;
  }
  // Without the model's marks, the fly lands under the roof of the stand-in's mouth.
  if (trap && (!landAt || !hairAt)) {
    const upside = new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), Math.PI);
    landAt = new Object3D();
    landAt.position.set(-0.4, 0.15, 0.7);
    landAt.quaternion.copy(upside);
    hairAt = landAt.clone();
    hairAt.position.x = 0;
    trap.add(landAt, hairAt);
  }
  group.updateMatrixWorld(true);
  const wingRest = wings.map((w) => w.rotation.z);
  const chainRest = chain.map((c) => c.quaternion.clone());
  const trapRest = trap?.quaternion.clone() ?? new Quaternion();
  const smallRest = smallTraps.map((t) => t.quaternion.clone());
  // The vines go on hanging however the head moves, and swing: little pendulums (in the set
  // piece's space) pushed about as the head accelerates.
  const groupInv = group.quaternion.clone().invert();
  const hanging = vines.map((v) => ({
    node: v,
    rest: groupInv.clone().multiply(v.getWorldQuaternion(new Quaternion())),
    x: new Spring(0.42, 0.15),
    z: new Spring(0.42, 0.15),
    at: group.worldToLocal(v.getWorldPosition(new Vector3())),
    vel: new Vector3(),
  }));
  // The fly flies free in the set piece's own space.
  if (fly) group.attach(fly);
  /** The middle of the mouth (trap space). */
  const MOUTH = new Vector3(0, 0, 0.55);
  const head = trap ? trap.localToWorld(MOUTH.clone()) : toWorld(new Vector3(0, 3.8, 0.9));
  const headRest = group.worldToLocal(head.clone());
  const hinge = trap ? trap.getWorldPosition(new Vector3()) : toWorld(new Vector3(0, 3.8, 0.4));
  // The stem bends as a chain: a lean is spread mostly low down (the whole stem swings), a bend
  // mostly high up (the head rocks on its neck), a turn through the middle.
  const spread = (f: (u: number) => number) => {
    const w = chain.map((_, i) => f(chain.length > 1 ? i / (chain.length - 1) : 1));
    const sum = w.reduce((a, b) => a + b, 0) || 1;
    return w.map((x) => x / sum);
  };
  const LEAN_W = spread((u) => (u === 0 ? 0.15 : 1 - 0.6 * u));
  const BEND_W = spread((u) => 0.2 + u);
  const TURN_W = spread((u) => Math.sin(Math.PI * u));

  // Hay bales in an arc in front, strung with teal lights, and pumpkins glowing among them.
  const hay = await loadModel('hay-bale');
  const balesAt = [-2.6, -1.3, 0, 1.3, 2.6].map((x, i) => ({ p: new Vector3(x, 0, 2.6 - Math.abs(x) * 0.25), turn: (x / 2.6) * -0.35 + (i % 2) * 0.05 }));
  if (hay) {
    const mats = balesAt.map(({ p, turn }) => new Matrix4().compose(toWorld(p), new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), yaw + turn), new Vector3(1, 1, 1)));
    objects.push(instanceModel(hay, mats));
  }
  const runs = [
    { from: toWorld(new Vector3(-3.3, 0.55, 2.0)), to: toWorld(new Vector3(0, 0.62, 2.7)), sag: 0.08 },
    { from: toWorld(new Vector3(0, 0.62, 2.7)), to: toWorld(new Vector3(3.3, 0.55, 2.0)), sag: 0.08 },
    { from: toWorld(new Vector3(-3.0, 0.2, 2.3)), to: toWorld(new Vector3(3.0, 0.2, 2.3)), sag: 0.02 },
  ];
  const leds = stringLights(runs, { spacing: 0.16, color: new Color(0.2, 1, 0.85), brightness: 9, glowEvery: 3, glowRadius: 1.2, glowIntensity: 0.18 });
  objects.push(leds.mesh);
  const specs: PumpkinSpec[] = [-0.7, 0, 0.6, -0.25, 0.35].map((x, i) => ({
    position: toWorld(new Vector3(x, 0.18 + (i > 2 ? 0.28 : 0), 1.3 + (i % 2) * 0.25)),
    size: new Vector3(0.24, 0.2, 0.24).multiplyScalar(i > 2 ? 0.75 : 1),
    yaw: yaw + (i - 2) * 0.3,
    carve: CARVE.faces[(i * 5) % CARVE.faces.length] as number,
    skin: new Color(0.72, 0.3, 0.06),
    glow: new Color(1, 0.55, 0.15).multiplyScalar(3),
    phase: i * 0.7,
  }));
  const pumpkins = new PumpkinField(specs, ctx.atlas, { detail: [28, 12], simple: [14, 7] });
  objects.push(pumpkins.group);

  // Spores and droplets puffed from the lips when it snaps.
  const puffCount = ctx.tier === 'low' ? 16 : ctx.tier === 'mid' ? 28 : 44;
  const spores = new Burst(puffCount * 2, { geometry: new OctahedronGeometry(0.034, 0), gravity: 0.3, drag: 2.2, brightness: 3 });
  objects.push(spores.mesh);
  const SPORES = [new Color(0.75, 1, 0.55), new Color(1, 0.35, 0.28), new Color(1, 0.85, 0.7)];
  // A flash of the trap's glow as it snaps: a red halo flaring round the head for a moment (set
  // behind it, so it shows round its rim).
  const halo = new Sprite(new SpriteMaterial({ map: haloTexture(), color: new Color(1, 0.25, 0.15), blending: AdditiveBlending, transparent: true, depthWrite: false, opacity: 0 }));
  halo.scale.setScalar(4.6);
  objects.push(halo);
  ctx.audio.preload('', ['flytrap-snap', 'fly-buzz']);

  const glow: GlowLight[] = [
    ...leds.lights,
    ...pumpkins.glowLights(1.5, 0.2),
    { x: hinge.x, z: hinge.z, y: hinge.y, radius: 4, color: new Color(1, 0.1, 0.08), intensity: 0.3, flicker: 0 },
  ];
  const red: LightSource = { position: hinge.clone().add(new Vector3(0, -0.4, 1.4)), color: new Color(1, 0.2, 0.15), intensity: 4, distance: 6, rank: 4 };

  // ---- The plant's state -------------------------------------------------------------------
  type Phase = 'open' | 'snap' | 'caught' | 'digest' | 'reopen' | 'lunge';
  let phase: Phase = 'open';
  let clock = 0; // seconds into the phase (the snap starts below 0: the moment before)
  let shut = 0; // the big trap: 0 open … 1 shut (below 0 gaping)
  let shutFrom = 0;
  let snapWait = 0.2;
  let reopenFor = 5.5;
  let alert = 0; // stirred by a touch: the lobes quiver, the glow rises
  let flash = 0;
  let squeeze = 0;
  let shudder = 0;
  let struggle = 0;
  let nextStruggle = 0;
  let clapped = false;
  let aim = 0; // toward the visitor (rad about y)
  let watch = 0;
  let time = 0;
  let frames = 0;
  const lean = new Spring(1.0, 0.25);
  const bend = new Spring(1.1, 0.14);
  const side = new Spring(0.9, 0.15);
  const turn = new Spring(0.45, 0.7);
  const nod = new Spring(1.6, 0.22);
  // The little traps: each snaps on its own, a beat after the big one.
  const small = smallTraps.map((_, k) => ({ shut: 0, clock: -1, wait: -1, hold: 2, sounded: true, rate: 1.3 + k * 0.12, nod: new Spring(2.4, 0.2) }));

  // ---- The fly -----------------------------------------------------------------------------
  type FlyState = 'away' | 'fly' | 'land' | 'walk' | 'caught' | 'gone';
  let flyState: FlyState = fly ? 'fly' : 'gone';
  let flyClock = 0;
  let flyFor = 5 + Math.random() * 4; // buzzing about before it lands
  let walked = 0; // 0 at the landing mark … 1 by the trigger hair
  let touches = 0;
  let squeezed = -1; // the last digesting squeeze that squelched
  let landStage = 0; // 0 coming in, 1 hovering under the roof, 2 up onto it
  const fp = fly ? fly.position.clone() : new Vector3();
  const fv = new Vector3();
  const goal = new Vector3();
  const loopAxis = new Vector3();
  let mode: 'dart' | 'hover' | 'loop' = 'dart';
  let goalFor = 0;
  let speed = 2.5;
  let heading = 0;
  let bank = 0;
  let pitch = 0;
  let nextBuzz = 0.5;
  const fq = new Quaternion();
  const flyEuler = new Euler(0, 0, 0, 'YXZ');
  const touchFrom = new Quaternion();
  const touchPos = new Vector3();
  const landP = new Vector3();
  const underP = new Vector3();

  const tmp = new Vector3();
  const tmp2 = new Vector3();
  const jitter = new Vector3();
  const tq = new Quaternion();
  const sq = new Quaternion();
  /** The head, as the fly keeps out of it: an ellipsoid round the mouth (radii, m). */
  const HEAD = new Vector3(1.5, 0.8, 1.0);
  const te = new Euler();
  const X = new Vector3(1, 0, 0);
  const visitor = new Vector3();
  const mouth = headRest.clone(); // the mouth's middle now, in the set piece's space
  const stemMid = head.clone();
  let far = 99;

  const near = () => far < 16;
  const flyWorld = () => (fly ? fly.getWorldPosition(new Vector3()) : head.clone());
  const sound = (key: string, where: Vector3, volume: number, rate = 1) => void ctx.audio.sfx(key, { at: pointOnGround(where), volume, rate });

  /** Puffs spores from along the lips. */
  const puff = (amount: number) => {
    if (!trap) return;
    const n = Math.max(1, Math.round((puffCount * amount) / 7));
    for (let i = 0; i < 7; i++) {
      const a = Math.PI * (0.15 + (0.7 * i) / 6);
      spores.emit(trap.localToWorld(tmp.set(1.25 * Math.cos(a), 0.05, 1.05 * Math.sin(a))), n, SPORES, 0.9 + amount * 0.5, 1.8);
    }
  };

  /** Closes the big trap: a breath of anticipation (`wait` s), then the snap. */
  const snapShut = (wait: number) => {
    if (phase !== 'open') return;
    phase = 'snap';
    clock = -wait;
    snapWait = wait;
    shutFrom = shut;
    clapped = false;
  };

  /** The little traps follow, out of sympathy. */
  const sympathy = (delay: number) => {
    small.forEach((s, k) => {
      if (s.clock < 0 && s.wait < 0) {
        s.wait = delay + k * 0.13 + Math.random() * 0.05;
        s.sounded = false;
      }
    });
  };

  /** Startles the fly off into the dark for a moment: off to one side and up (not at you). */
  const startle = () => {
    if (flyState !== 'fly' && flyState !== 'land') return;
    flyState = 'fly';
    mode = 'dart';
    const s = fp.x < mouth.x ? -1 : 1;
    goal.set(mouth.x + s * (3.5 + Math.random() * 1.5), mouth.y + 0.8 + Math.random(), mouth.z - 1 + Math.random() * 1.5);
    goalFor = 1;
    speed = 5;
    flyFor = 5 + Math.random() * 4;
  };

  const lungeAt = () => {
    if (phase !== 'open') return;
    phase = 'lunge';
    clock = 0;
    shutFrom = shut;
    clapped = false;
    startle();
    sound('flytrap-lunge', head, 0.8);
  };

  /** Tapped: an empty trap lunges at you; with the fly on it, it snaps; full, it shudders. */
  const tap = () => {
    if (phase === 'open') {
      if (flyState === 'walk') snapShut(0.22);
      else lungeAt();
    } else if (phase !== 'lunge' && phase !== 'snap') {
      shudder = 1;
      nod.v += (Math.random() < 0.5 ? -1 : 1) * 0.5;
      bend.v -= 0.15;
      if (flyState === 'caught') sound('fly-buzz-trapped', head, 0.5);
    }
  };

  // ---- The big trap's moves ----------------------------------------------------------------
  const stepTrap = (dt: number) => {
    clock += dt;
    const breathe = 0.012 * Math.sin(time * 1.25 + 1.2);
    let glowUp = 0;
    lean.hz = 1.0;
    lean.damp = 0.25;
    nod.hz = 1.6;
    // Watching you while it waits (coming round to it slowly): a little lean, the mouth turned your way.
    watch += ((phase === 'open' && far < 12 ? 1 : 0) - watch) * (1 - Math.exp(-dt * 0.8));
    const drop = Math.atan2(Math.max(0, headRest.y - 1.6), Math.max(1, Math.hypot(visitor.x - headRest.x, visitor.z - headRest.z)));
    lean.target = 0.04 * watch;
    nod.target = Math.min(0.16, 0.35 * drop) * watch;
    turn.target = aim * 0.45 * watch;
    squeeze = 0;
    switch (phase) {
      case 'open':
        shut = breathe + alert * (0.05 + 0.03 * tremor(time));
        break;
      case 'snap':
        if (clock < 0) {
          alert = 1;
          shut = shutFrom + (0.06 - shutFrom) * ease(1 + clock / snapWait) + 0.035 * tremor(time);
        } else if (clock < 0.1) {
          if (clock - dt < 0) shutFrom = shut;
          shut = shutFrom + (CAGE - shutFrom) * (clock / 0.1) ** 2;
          flash = Math.max(flash, clock / 0.1);
        } else {
          shut = bounce(clock - 0.1);
        }
        if (!clapped && clock >= 0.1 - CLAP) {
          clapped = true;
          sound('flytrap-snap', head, 1, 0.95 + Math.random() * 0.1);
          sympathy(0.22);
        }
        if (clock >= 0.1 && clock - dt < 0.1) {
          // The jolt throws the head back on its stem; a flash, a puff of spores.
          flash = 1;
          bend.v -= ctx.reducedMotion ? 0.5 : 1.3;
          nod.v -= ctx.reducedMotion ? 1 : 2.4;
          side.v += (Math.random() - 0.5) * 0.6;
          puff(1);
          shutFrom = CAGE;
        }
        if (clock > 0.7) {
          if (flyState === 'walk' || flyState === 'caught') {
            phase = 'caught';
            flyState = 'caught';
            nextStruggle = 0.3;
          } else {
            phase = 'reopen';
            reopenFor = 3.5;
            sound('flytrap-reopen', head, 0.45, 1.35);
          }
          clock = 0;
        }
        break;
      case 'caught': {
        // The fly fights it: the lobes shudder in bursts.
        nextStruggle -= dt;
        if (nextStruggle <= 0 && clock < 4) {
          struggle = 1;
          nextStruggle = 0.7 + Math.random() * 0.9;
          if (near() && Math.random() < 0.6) sound('fly-buzz-trapped', head, 0.55 - clock * 0.08);
        }
        shut = CAGE - 0.05 * struggle + 0.03 * struggle * tremor(time * 1.3);
        nod.v += (Math.random() - 0.5) * 16 * dt * struggle;
        side.v += (Math.random() - 0.5) * 5 * dt * struggle;
        glowUp = 0.6 * struggle;
        if (clock > 4.5) {
          phase = 'digest';
          clock = 0;
          squeezed = -1;
        }
        break;
      }
      case 'digest': {
        // It seals (all but a slit of glow between its lips), then squeezes in slow pulses, the
        // glow throbbing; the head dips with each.
        const u = (clock - 2.5) / 4.6;
        const fade = ease((22 - clock) / 3);
        squeeze = clock > 2.5 ? Math.max(0, Math.sin(2 * Math.PI * u)) ** 2 * fade : 0;
        if (clock > 2.5 && clock < 19 && Math.floor(u) > squeezed) {
          squeezed = Math.floor(u);
          if (near()) sound('flytrap-digest', head, 0.6);
        }
        shut = CAGE + (0.97 - CAGE) * ease(clock / 3) + 0.01 * squeeze;
        nod.target += 0.05 * squeeze;
        glowUp = 2 * squeeze;
        if (clock > 22) {
          phase = 'reopen';
          clock = 0;
          reopenFor = 5.5;
          shutFrom = shut;
          if (near()) sound('flytrap-reopen', head, 0.5);
        }
        break;
      }
      case 'reopen': {
        // Slowly and shakily, in fits and starts.
        const k = clock / reopenFor;
        const e = Math.min(1, Math.max(0, ease(k) + 0.035 * Math.sin(k * 29) * Math.sin(Math.PI * k)));
        shut = shutFrom * (1 - e) + 0.004 * tremor(time) * (1 - k);
        nod.target -= 0.04 * Math.sin(Math.PI * Math.min(1, k));
        if (k >= 1) {
          phase = 'open';
          clock = 0;
          shut = 0;
        }
        break;
      }
      case 'lunge': {
        // Rears back gaping, whips forward at you, bites the air, and pulls back.
        const reach = ctx.reducedMotion ? 0.25 : 1;
        if (clock < 0.38) {
          shut = shutFrom + (-0.45 - shutFrom) * ease(clock / 0.38);
          lean.target = -0.1 * reach;
          nod.target = -0.22 * reach;
          turn.target = aim * 0.5;
          lean.hz = 1.6;
          lean.damp = 0.7;
        } else if (clock < 0.95) {
          lean.target = LUNGE * reach;
          nod.target = 0.05;
          turn.target = aim * 0.85;
          lean.hz = 2.3;
          lean.damp = 0.55;
          nod.hz = 2.5;
          glowUp = 0.8;
          shut = clock < BITE ? -0.45 + 0.02 * tremor(time) : clock < BITE + 0.09 ? -0.45 + (CAGE + 0.45) * ((clock - BITE) / 0.09) ** 2 : bounce(clock - BITE - 0.09);
        } else {
          shut = CAGE * (1 - ease((clock - 1.1) / 0.9));
        }
        if (!clapped && clock >= BITE + 0.09 - CLAP / 0.9) {
          clapped = true;
          sound('flytrap-snap', head, 0.9, 0.9);
          sympathy(0.25);
        }
        if (clock >= BITE + 0.09 && clock - dt < BITE + 0.09) {
          flash = 0.6;
          nod.v -= 1;
          puff(0.5);
        }
        if (clock > 2.6) {
          phase = 'open';
          clock = 0;
        }
        break;
      }
    }
    alert = Math.max(0, alert - dt * 0.55);
    flash *= Math.exp(-dt * 4);
    struggle *= Math.exp(-dt * 3.5);
    shudder *= Math.exp(-dt * 3);
    shut += 0.02 * shudder * tremor(time * 1.4);
    nod.v += (Math.random() - 0.5) * 4 * dt * shudder;
    for (const s of [lean, bend, side, turn, nod]) s.step(dt);

    // The glow: brighter as it stirs, a flash as it snaps, throbbing as it digests.
    for (const m of glowMats) m.emissiveIntensity = 1.4 + 1.1 * alert + 2.6 * flash + glowUp;
    for (const m of skinMats) m.emissiveIntensity = 1 + 0.9 * flash + squeeze;
    red.intensity = 4 * (1 + 0.35 * alert + flash + 0.8 * squeeze);
  };

  const stepSmall = (dt: number) => {
    small.forEach((s, k) => {
      if (s.wait >= 0) {
        s.wait -= dt;
        // (its clap timed to land as it shuts, 0.08 s after it starts to close)
        if (!s.sounded && s.wait < CLAP / s.rate - 0.08) {
          s.sounded = true;
          sound('flytrap-snap', head.clone().setY(1.2), k === 0 ? 0.55 : 0.35, s.rate);
        }
        if (s.wait < 0) {
          s.clock = 0;
          s.hold = 1.8 + Math.random() * 0.8;
        }
      }
      if (s.clock >= 0) {
        s.clock += dt;
        const c = s.clock;
        if (c < 0.08) s.shut = (c / 0.08) ** 2;
        else if (c < 0.08 + s.hold) s.shut = 1 - 0.07 * Math.exp(-(c - 0.08) / 0.08) * Math.abs(Math.sin((c - 0.08) * 38));
        else s.shut = 1 - ease((c - 0.08 - s.hold) / 2.5);
        if (c >= 0.08 && c - dt < 0.08) s.nod.v -= 3;
        if (c > s.hold + 2.6) s.clock = -1;
      } else {
        s.shut = 0.015 * Math.sin(time * 1.4 + s.hold) + alert * 0.5 * (0.04 + 0.03 * tremor(time + s.hold));
      }
      s.nod.step(dt);
    });
  };

  /** Poses the stem chain, the head on it, the lobes and the little traps. */
  const pose = () => {
    const sway = 0.014 * Math.sin(time * 0.83) + 0.006 * Math.sin(time * 2.1 + 0.4);
    const rock = 0.01 * Math.sin(time * 1.25);
    chain.forEach((node, i) => {
      te.set(
        (LEAN_W[i] as number) * lean.x + (BEND_W[i] as number) * (bend.x + rock),
        (TURN_W[i] as number) * turn.x,
        (BEND_W[i] as number) * (side.x + sway),
      );
      node.quaternion.copy(chainRest[i] as Quaternion).multiply(tq.setFromEuler(te));
    });
    if (trap) trap.quaternion.copy(trapRest).multiply(tq.setFromAxisAngle(X, nod.x + 0.02 * Math.sin(time * 1.25 + 0.6)));
    smallTraps.forEach((t, k) => t.quaternion.copy(smallRest[k] as Quaternion).multiply(tq.setFromAxisAngle(X, (small[k] as (typeof small)[number]).nod.x)));
    lobes.forEach((pair, k) => {
      const s = k === 0 ? shut : (small[k - 1]?.shut ?? 0);
      const full = SHUT[k === 0 ? 0 : 1] as number;
      for (const l of pair) {
        l.node.rotation.x = l.rest + l.sign * (OPEN + (full - OPEN) * s);
        if (k === 0) l.node.scale.y = 1 - 0.1 * squeeze;
      }
    });
    group.updateMatrixWorld(true);
  };

  /** Swings the vines from the head's motion and keeps them hanging. */
  const swing = (dt: number) => {
    if (!trap || !hanging.length || dt <= 0) return;
    const headQ = groupInv.clone().multiply(trap.getWorldQuaternion(tq)).invert();
    for (const h of hanging) {
      const p = group.worldToLocal(h.node.getWorldPosition(tmp));
      const v = tmp2.copy(p).sub(h.at).divideScalar(dt);
      const a = h.vel.sub(v).multiplyScalar(-1 / dt).clampLength(0, 40);
      h.x.v += (a.z / 1.6) * dt;
      h.z.v -= (a.x / 1.6) * dt;
      for (const s of [h.x, h.z]) {
        s.step(dt);
        if (Math.abs(s.x) > 0.6) {
          s.x = Math.sign(s.x) * 0.6;
          s.v = 0;
        }
      }
      h.at.copy(p);
      h.vel.copy(v);
      h.node.quaternion.copy(headQ).multiply(sq.setFromEuler(te.set(h.x.x, 0, h.z.x))).multiply(h.rest);
    }
  };

  // ---- The fly's moves ---------------------------------------------------------------------
  /** A new leg of its flight: a dart somewhere round the head, a hover, or a little loop. */
  const nextLeg = () => {
    const r = Math.random();
    if (r < 0.6) {
      mode = 'dart';
      // mostly in front of the mouth, a little below its lips: between you and the glow
      goal.set(mouth.x + (Math.random() - 0.5) * 4.2, Math.max(1.3, mouth.y - 0.55 + (Math.random() - 0.5) * 1.2), mouth.z + 1.3 + (Math.random() - 0.5));
      speed = 2.2 + Math.random() * 1.8;
      goalFor = 0.25 + Math.random() * 0.45;
    } else if (r < 0.82) {
      mode = 'hover';
      goal.copy(fp).add(tmp.set(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).multiplyScalar(0.3));
      goalFor = 0.35 + Math.random() * 0.55;
    } else {
      mode = 'loop';
      if (fv.lengthSq() < 0.5) fv.set(Math.random() - 0.5, 0, Math.random() - 0.5).setLength(2.4);
      // a vertical loop over its path, or a tight circle
      loopAxis.copy(Math.random() < 0.6 ? tmp.crossVectors(fv, new Vector3(0, 1, 0)) : tmp.set(0, Math.random() < 0.5 ? 1 : -1, 0));
      if (loopAxis.lengthSq() < 0.01) loopAxis.set(1, 0, 0);
      loopAxis.normalize();
      goalFor = 0.5 + Math.random() * 0.3;
    }
  };

  /** Flies: steering after its goal with a quick, jerky hand, kept out of the head and the ground. */
  const flyAbout = (dt: number, avoid: boolean) => {
    const before = tmp2.copy(fv);
    if (mode === 'loop') {
      fv.setLength(Math.max(2, Math.min(3, fv.length()))).applyAxisAngle(loopAxis, 9 * dt);
    } else {
      const want = tmp.copy(goal).sub(fp);
      const d = want.length();
      if (mode === 'hover') want.multiplyScalar(3).add(jitter.set(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).multiplyScalar(1.6));
      else want.setLength(speed * Math.min(1, d / 0.4));
      const dv = want.sub(fv);
      const most = (mode === 'hover' ? 10 : 16) * dt;
      if (dv.length() > most) dv.setLength(most);
      fv.add(dv);
    }
    fp.addScaledVector(fv, dt);
    if (avoid) {
      // Out of the head (an ellipsoid round the mouth) …
      const q = tmp.copy(fp).sub(mouth).divide(HEAD);
      const k = q.length();
      if (k < 1) {
        q.setLength(1 - k).multiply(HEAD);
        fp.add(q);
        const n = q.normalize();
        const into = fv.dot(n);
        if (into < 0) fv.addScaledVector(n, -into * 1.5);
      }
      // … out of your face …
      const off = tmp.copy(fp).sub(visitor);
      if (off.lengthSq() < 4.8) {
        fp.copy(visitor).add(off.setLength(2.2));
        fv.addScaledVector(off.normalize(), 0.5);
      }
      // … and up off the ground.
      if (fp.y < 0.9) {
        fp.y = 0.9;
        fv.y = Math.abs(fv.y);
      }
    }
    // Facing where it flies (or, hovering, the trap), banked into its turns, nose down as it speeds up.
    const accel = before.sub(fv).multiplyScalar(-1 / Math.max(dt, 1e-3));
    const flat = Math.hypot(fv.x, fv.z);
    const want = flat > 0.5 ? Math.atan2(-fv.x, -fv.z) : Math.atan2(fp.x - mouth.x, fp.z - mouth.z);
    let dh = want - heading;
    dh = Math.atan2(Math.sin(dh), Math.cos(dh));
    heading += dh * (1 - Math.exp(-dt * 12));
    const lateral = accel.x * Math.cos(heading) - accel.z * Math.sin(heading);
    const forward = -accel.x * Math.sin(heading) - accel.z * Math.cos(heading);
    bank += (Math.max(-0.7, Math.min(0.7, -lateral * 0.05)) - bank) * (1 - Math.exp(-dt * 10));
    pitch += (Math.max(-0.5, Math.min(0.4, -forward * 0.025 + fv.y * 0.12)) - pitch) * (1 - Math.exp(-dt * 10));
    fq.setFromEuler(flyEuler.set(pitch, heading, bank));
  };

  /** The wings: a blur in the air (a different angle every frame), folded on the trap. */
  const flap = (blur: number) => {
    const odd = frames % 2;
    wings.forEach((w, i) => {
      const a = blur > 0 ? (odd ? 0.15 : 0.95) * (0.6 + 0.4 * Math.random()) * blur : 0;
      w.rotation.z = (wingRest[i] ?? 0) + (i === 0 ? -a : a);
    });
  };

  const stepFly = (dt: number) => {
    if (!fly || !trap || !landAt || !hairAt) return;
    flyClock += dt;
    switch (flyState) {
      case 'away':
        // Coming back from somewhere out in the dark, behind the plant.
        if (flyClock > 0) {
          flyState = 'fly';
          fly.visible = true;
          group.attach(fly);
          const s = Math.random() < 0.5 ? -1 : 1;
          fp.set(mouth.x + s * (6 + Math.random() * 3), 1.5 + Math.random() * 2.5, mouth.z - 3 - Math.random() * 3);
          fv.set(-s * 2, 0, 1.5);
          goal.copy(mouth).add(new Vector3(0, 0.2, 1.4));
          mode = 'dart';
          speed = 3.2;
          goalFor = 2.2;
          flyFor = 6 + Math.random() * 6;
          flyClock = 0;
        }
        break;
      case 'fly': {
        goalFor -= dt;
        if (goalFor <= 0) nextLeg();
        flyAbout(dt, true);
        fly.position.copy(fp);
        fly.quaternion.copy(fq);
        flap(1);
        flyFor -= dt;
        if (flyFor <= 0) {
          // It lands only while you're there to see it (and the trap's ready).
          if (phase === 'open' && near()) {
            flyState = 'land';
            landStage = 0;
            flyClock = 0;
          } else flyFor = 2;
        }
        break;
      }
      case 'land': {
        // In under the roof of the mouth, a hover, then up onto it, flipping over.
        const land = group.worldToLocal(landAt.getWorldPosition(landP));
        const back = tmp2.set(0, 1, 0).applyQuaternion(landAt.getWorldQuaternion(tq)).applyQuaternion(groupInv);
        const under = underP.copy(land).addScaledVector(back, 0.3);
        if (landStage === 0) {
          mode = 'dart';
          speed = 1.8;
          goal.copy(under).add(tmp.set(0, -0.15, fp.distanceTo(under) > 1.2 ? 0.9 : 0));
          flyAbout(dt, fp.distanceTo(under) > 1.2);
          if (fp.distanceTo(under) < 0.2) {
            landStage = 1;
            flyClock = 0;
          }
        } else if (landStage === 1) {
          mode = 'hover';
          goal.copy(under);
          flyAbout(dt, false);
          if (flyClock > 0.45) {
            landStage = 2;
            flyClock = 0;
            touchFrom.copy(fq);
            touchPos.copy(fp);
          }
        } else {
          const k = ease(flyClock / 0.3);
          fp.lerpVectors(touchPos, land, k);
          const target = tq.copy(groupInv).multiply(landAt.getWorldQuaternion(sq));
          fq.slerpQuaternions(touchFrom, target, k);
          if (flyClock >= 0.3) {
            // Down: from here on it rides on the lobe.
            landAt.parent?.attach(fly);
            fly.position.copy(landAt.position);
            fly.quaternion.copy(landAt.quaternion);
            flyState = 'walk';
            flyClock = 0;
            walked = 0;
            touches = 0;
            flap(0);
            break;
          }
        }
        fly.position.copy(fp);
        fly.quaternion.copy(fq);
        flap(landStage === 2 ? 1 - flyClock / 0.3 : 1);
        break;
      }
      case 'walk': {
        // A few steps, a pause, a step to the hair (the trap stirs), a pause, and a last step;
        // caught mid-stride if the trap shuts on it first.
        if (phase !== 'open') flyClock -= dt;
        const c = flyClock;
        let from = 0;
        let to = 0;
        let k = 0;
        let moving = false;
        for (let i = 0; i < WALK.length; i++) {
          const [t1, w1] = WALK[i] as [number, number];
          const [t0, w0] = i === 0 ? [0, 0] : (WALK[i - 1] as [number, number]);
          if (c <= t1 || i === WALK.length - 1) {
            from = w0;
            to = w1;
            k = Math.min(1, (c - t0) / (t1 - t0));
            moving = w1 !== w0 && k < 1;
            break;
          }
        }
        // stepping: progress in little surges, the body rocking from leg to leg
        const steps = Math.max(1, Math.round((to - from) * 6));
        const stepK = moving ? (Math.floor(k * steps) + ease((k * steps) % 1)) / steps : k;
        walked = from + (to - from) * Math.min(1, stepK);
        fly.position.lerpVectors(landAt.position, hairAt.position, walked);
        fly.quaternion.slerpQuaternions(landAt.quaternion, hairAt.quaternion, walked);
        if (moving) {
          fly.translateY(-0.012 * Math.abs(Math.sin(k * steps * Math.PI)));
          fly.rotateZ(0.05 * Math.sin(k * steps * Math.PI));
        }
        // reaching for the hair with its front legs as it touches it
        const reach = touches > 0 && c < TOUCH + 0.4 ? 1 - (c - TOUCH) / 0.4 : c > TOUCH_AGAIN ? 1 : 0;
        if (reach > 0) fly.rotateX(-0.12 * Math.max(0, Math.min(1, reach)));
        flap(c > 2.1 && c < 2.35 ? 0.5 : 0);
        if (touches === 0 && c >= TOUCH) {
          touches = 1;
          alert = 1;
          nod.v += 0.25;
          sound('flytrap-stir', head, 0.7);
        }
        if (touches === 1 && c >= TOUCH_AGAIN) {
          touches = 2;
          snapShut(0.12);
        }
        break;
      }
      case 'caught': {
        // Struggling inside: a twitch and a buzz now and then, fainter, then still.
        fly.position.lerpVectors(landAt.position, hairAt.position, walked);
        fly.position.x += (Math.random() - 0.5) * 0.03 * struggle;
        fly.position.z += (Math.random() - 0.5) * 0.03 * struggle;
        flap(struggle > 0.3 ? 0.6 : 0);
        if (phase === 'digest' && clock > 3) {
          flyState = 'gone';
          fly.visible = false;
        }
        break;
      }
      case 'gone':
        // When the trap's open again (empty), another fly comes along a while later.
        if (phase === 'open') {
          flyState = 'away';
          flyClock = -(6 + Math.random() * 8);
        }
        break;
    }
    // Its buzz, as it flies about near you.
    nextBuzz -= dt;
    if (nextBuzz <= 0) {
      nextBuzz = 1.8 + Math.random() * 0.7;
      if ((flyState === 'fly' || flyState === 'land') && near()) {
        sound('fly-buzz', flyWorld(), mode === 'hover' ? 0.32 : 0.42, mode === 'hover' ? 0.9 : 0.95 + fv.length() * 0.03 + Math.random() * 0.06);
      }
    }
  };

  if (import.meta.env.DEV)
    (window as unknown as { flytrap: unknown }).flytrap = {
      tap,
      land: () => (flyFor = 0),
      snap: () => snapShut(0.25),
      lunge: lungeAt,
      state: () => ({ phase, clock, fly: flyState, shut, lean: lean.x, bend: bend.x, nod: nod.x, turn: turn.x, aim, watch }),
    };

  return {
    objects,
    glow,
    sources: [red, { position: toWorld(new Vector3(0, 0.8, 3.2)), color: new Color(0.2, 1, 0.85), intensity: 3, distance: 6 }],
    update(dt) {
      time += dt;
      frames++;
      // Where you are, seen from the plant.
      visitor.copy(ctx.camera.position);
      visitor.y -= heightAt(visitor.x, visitor.z);
      group.worldToLocal(visitor);
      far = Math.hypot(visitor.x - headRest.x, visitor.z - headRest.z);
      aim = Math.max(-0.6, Math.min(0.6, Math.atan2(visitor.x - headRest.x, visitor.z - headRest.z)));
      stepTrap(dt);
      stepSmall(dt);
      pose();
      swing(dt);
      if (trap) {
        trap.localToWorld(head.copy(MOUTH));
        group.worldToLocal(mouth.copy(head));
      }
      (chain[2] ?? trap)?.getWorldPosition(stemMid);
      halo.material.opacity = flash > 0.03 ? 0.7 * flash * flash : 0;
      if (flash > 0.03) {
        halo.position.copy(pointOnGround(head));
        halo.position.addScaledVector(tmp.copy(halo.position).sub(ctx.camera.position).normalize(), 1.3);
      }
      stepFly(dt);
      spores.update(dt, 0);
      pumpkins.update(ctx.camera, dt);
    },
    pick(ray: Ray) {
      if (ray.distanceSqToPoint(pointOnGround(head)) > 2.6 && ray.distanceSqToPoint(pointOnGround(stemMid)) > 1.2) return null;
      return tap;
    },
    dispose() {
      pumpkins.dispose();
      spores.dispose();
      halo.material.map?.dispose();
      halo.material.dispose();
      leds.mesh.geometry.dispose();
    },
  };
}
