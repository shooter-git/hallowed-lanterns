import {
  Color,
  ConeGeometry,
  CubicBezierCurve3,
  DoubleSide,
  Group,
  InstancedMesh,
  Matrix4,
  Mesh,
  MeshStandardMaterial,
  type Object3D,
  Quaternion,
  type Ray,
  SphereGeometry,
  TubeGeometry,
  Vector3,
} from 'three';
import type { ChapterContext } from '../chapters/types.ts';
import { CARVE } from '../engine/carvings.ts';
import type { GlowLight } from '../engine/glowfield.ts';
import { stringLights } from '../engine/lanterns.ts';
import { instanceModel, loadModel } from '../engine/models.ts';
import { PumpkinField, type PumpkinSpec } from '../engine/pumpkins.ts';
import { hallow } from '../engine/shared.ts';
import { pointOnGround } from '../engine/terrain.ts';
import type { SetPiece } from './types.ts';

/**
 * The giant fly-eating Venus flytrap: a trap head as wide as a car on a curving stem, green
 * outside and deep red inside, teeth along its lips, a fly the size of a cat caught between
 * them, and ivy trailing down. Below it, hay bales strung with teal lights and a few glowing
 * pumpkins. The fly buzzes now and then; tap the trap and it snaps shut (the little ones too),
 * holds, and slowly opens again.
 */

/** The lobes hinge about their local x: open a little wider than modelled while waiting, and
 * shut this far past it (the big trap, then the little ones), before the teeth would clash. */
const OPEN = -0.17;
const SHUT = [0.227, 0.28];

interface Lobe {
  node: Object3D;
  rest: number;
  sign: number;
}

export async function flytrap(ctx: ChapterContext, at: Vector3, yaw: number): Promise<SetPiece> {
  const objects: Object3D[] = [];
  const toWorld = (v: Vector3) => v.clone().applyAxisAngle(new Vector3(0, 1, 0), yaw).add(at);
  const group = new Group();
  group.position.copy(at);
  group.rotation.y = yaw;
  objects.push(group);

  const model = await loadModel('venus-flytrap', { glowReceive: 0.7 });
  const lobes: Lobe[][] = []; // the big trap first, then the little ones
  let fly: Object3D | undefined;
  let wings: Object3D[] = [];
  let head = toWorld(new Vector3(0, 3.8, 0.4));
  if (model) {
    group.add(model.root);
    group.updateMatrixWorld(true);
    for (const m of model.glows.values()) m.emissiveIntensity = 1.4;
    const trapLobes = (trap: Object3D | undefined) => {
      if (!trap) return null;
      const upper = trap.getObjectByName('lobe_upper') ?? trap.children.find((c) => /upper/i.test(c.name));
      const lower = trap.getObjectByName('lobe_lower') ?? trap.children.find((c) => /lower/i.test(c.name));
      return [upper, lower]
        .map((node, i) => (node ? { node, rest: node.rotation.x, sign: i === 0 ? 1 : -1 } : null))
        .filter((l): l is Lobe => l !== null);
    };
    const big = model.node('trap');
    const first = trapLobes(big);
    if (first?.length) lobes.push(first);
    for (let k = 1; k < 6; k++) {
      const small = trapLobes(model.node(`trap_small_${k}`));
      if (small?.length) lobes.push(small);
    }
    if (big) head = big.getWorldPosition(new Vector3());
    fly = model.node('fly');
    wings = ['wing_L', 'wing_R'].map((n) => model.node(n)).filter(Boolean) as Object3D[];
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
    const trap = new Group();
    trap.position.set(0, 3.8, 0.3);
    group.add(trap);
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
      trap.add(hinge);
      pair.push({ node: hinge, rest: hinge.rotation.x, sign: side });
    }
    lobes.push(pair);
    const flyMesh = new Mesh(new SphereGeometry(0.32, 16, 10), hallow(new MeshStandardMaterial({ color: 0x0a0a0c, roughness: 0.3, metalness: 0.3 }), { key: 'fly' }));
    flyMesh.position.set(0, 4.35, 0.3);
    group.add(flyMesh);
    fly = flyMesh;
    group.updateMatrixWorld(true);
    head = trap.getWorldPosition(new Vector3());
  }
  const flyRest = fly?.position.clone();
  const wingRest = wings.map((w) => w.rotation.z);

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

  let shut = 0; // 0 open … 1 shut
  let hold = 0;
  let closing = false;
  let nextBuzz = 2 + Math.random() * 3;
  let nextSnap = 30 + Math.random() * 20;
  let time = 0;
  const glow: GlowLight[] = [
    ...leds.lights,
    ...pumpkins.glowLights(1.5, 0.2),
    { x: head.x, z: head.z, radius: 4, color: new Color(1, 0.1, 0.08), intensity: 0.3, flicker: 0 },
  ];
  const near = () => ctx.camera.position.distanceTo(head) < 14;
  const snapShut = () => {
    if (closing || shut > 0.5) return;
    closing = true;
    hold = 2.6;
    void ctx.audio.sfx('flytrap-snap', { at: pointOnGround(head), volume: 1 });
    // the little traps a moment later, out of sympathy
    if (lobes.length > 1) setTimeout(() => void ctx.audio.sfx('flytrap-snap', { at: pointOnGround(head.clone().setY(1.5)), volume: 0.55, rate: 1.25 }), 220);
  };

  return {
    objects,
    glow,
    sources: [
      { position: head.clone().add(new Vector3(0, -0.4, 1.4)), color: new Color(1, 0.2, 0.15), intensity: 4, distance: 6 },
      { position: toWorld(new Vector3(0, 0.8, 3.2)), color: new Color(0.2, 1, 0.85), intensity: 3, distance: 6 },
    ],
    update(dt) {
      time += dt;
      // Snap fast, hold, open slowly.
      if (closing) {
        shut = Math.min(1, shut + dt / 0.14);
        if (shut >= 1) closing = false;
      } else if (hold > 0) {
        hold -= dt;
      } else {
        shut = Math.max(0, shut - dt / 2.4);
      }
      lobes.forEach((pair, k) => {
        const lag = k === 0 ? shut : Math.max(0, shut - 0.15);
        const far = SHUT[k === 0 ? 0 : 1] as number;
        for (const l of pair) l.node.rotation.x = l.rest + l.sign * (OPEN + (far - OPEN) * lag);
      });
      // The fly: wings a blur, a twitch now and then, still when the trap's shut on it.
      if (fly && flyRest) {
        const free = 1 - shut;
        fly.position.set(flyRest.x + Math.sin(time * 9) * 0.015 * free, flyRest.y + Math.sin(time * 13) * 0.01 * free, flyRest.z);
        wings.forEach((w, i) => (w.rotation.z = (wingRest[i] ?? 0) + Math.sin(time * 70 + i * Math.PI) * 0.35 * free));
      }
      nextBuzz -= dt;
      if (nextBuzz <= 0) {
        nextBuzz = 3 + Math.random() * 5;
        if (shut < 0.3 && near()) void ctx.audio.sfx('fly-buzz', { at: pointOnGround(fly ? fly.getWorldPosition(new Vector3()) : head), volume: 0.55 });
      }
      // Left alone, it snaps now and then.
      nextSnap -= dt;
      if (nextSnap <= 0) {
        nextSnap = 25 + Math.random() * 25;
        if (near()) snapShut();
      }
      pumpkins.update(ctx.camera, dt);
    },
    pick(ray: Ray) {
      const target = pointOnGround(head);
      if (ray.distanceSqToPoint(target) > 2.6 && ray.distanceSqToPoint(pointOnGround(head.clone().setY(head.y - 1.6))) > 1.2) return null;
      return () => snapShut();
    },
    dispose() {
      pumpkins.dispose();
      leds.mesh.geometry.dispose();
    },
  };
}
