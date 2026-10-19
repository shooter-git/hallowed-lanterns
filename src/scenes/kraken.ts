import { Box3, Color, type Object3D, type Ray, Vector3 } from 'three';
import type { ChapterContext } from '../chapters/types.ts';
import type { GlowLight } from '../engine/glowfield.ts';
import { stringLights } from '../engine/lanterns.ts';
import { bendable, loadModel } from '../engine/models.ts';
import { Burst } from '../engine/particles.ts';
import { heightAt, onGround, pointOnGround } from '../engine/terrain.ts';
import type { SetPiece } from './types.ts';

/**
 * The Kraken's Wreck: giant glowing orange tentacles rise out of the sea floor around a great
 * inflatable pumpkin; one arches over a wrecked hull; pumpkin-headed skeleton pirates row a
 * little boat; barrels lie about. Further on, the treasure: a huge open chest heaped with gold on
 * a low platform (you can sit on it), skeletons guarding it, pumpkin palm trees.
 */

interface Placed {
  name: string;
  at: Vector3;
  yaw: number;
  scale?: number;
  /** Raise off the ground (m). */
  lift?: number;
  /** Shift along the model's own +Z (m). */
  out?: number;
}

export async function kraken(ctx: ChapterContext, wreckAt: Vector3, wreckYaw: number, treasureAt: Vector3, treasureYaw: number): Promise<SetPiece & { seat: Vector3 }> {
  const objects: Object3D[] = [];
  const rot = (v: Vector3, yaw: number, at: Vector3) => v.clone().applyAxisAngle(new Vector3(0, 1, 0), yaw).add(at);
  const W = (x: number, z: number) => rot(new Vector3(x, 0, z), wreckYaw, wreckAt);
  const T = (x: number, z: number) => rot(new Vector3(x, 0, z), treasureYaw, treasureAt);
  const placements: Placed[] = [
    { name: 'inflatable-pumpkin', at: W(-2.5, -2.5), yaw: wreckYaw + 0.4 },
    { name: 'kraken-tentacle-a', at: W(-0.5, -1.5), yaw: wreckYaw + 0.2 },
    { name: 'kraken-tentacle-b', at: W(0.9, -2.6), yaw: wreckYaw - 0.3 },
    { name: 'kraken-tentacle-c', at: W(-3.8, 0.4), yaw: wreckYaw + 1.1 },
    { name: 'kraken-arch', at: W(4.6, -1.0), yaw: wreckYaw - 0.6 },
    { name: 'rowboat', at: W(-2.2, 1.6), yaw: wreckYaw + 0.25 },
    { name: 'skeleton-pirate-sit', at: W(-2.6, 1.6), yaw: wreckYaw + 1.7 },
    { name: 'skeleton-pirate-sit', at: W(-1.6, 1.5), yaw: wreckYaw + 1.6 },
    { name: 'skeleton-pirate-stand', at: W(-3.6, 1.9), yaw: wreckYaw + 0.6 },
    { name: 'barrel', at: W(0.6, 1.4), yaw: wreckYaw + 1.3 },
    { name: 'barrel', at: W(3.4, 2.2), yaw: wreckYaw - 0.4 },
    { name: 'treasure-chest', at: T(0, 0), yaw: treasureYaw },
    { name: 'skeleton', at: T(1.6, -0.2), yaw: treasureYaw - 0.5 },
    { name: 'skeleton', at: T(-2.6, -2.2), yaw: treasureYaw + 0.3 },
    { name: 'pumpkin-palm', at: T(-2.1, 0.1), yaw: treasureYaw },
    { name: 'pumpkin-palm', at: T(2.8, -1.4), yaw: treasureYaw + 1 },
    // A taller palm with a skeleton halfway up it (its arms hug a trunk this thick).
    { name: 'pumpkin-palm', at: T(-3.8, -3.6), yaw: treasureYaw + 0.6, scale: 1.5 },
    { name: 'skeleton-climb', at: T(-3.8, -3.6), yaw: treasureYaw + 0.6, lift: 0.55, out: 0.12 },
  ];
  const tentacles: { wave: { value: number } }[] = [];
  let chestLid: Object3D | undefined;
  let chestChains: Object3D | undefined;
  let chestBox: Box3 | null = null;
  // The rowboat marks where its crew sit.
  const crew: Object3D[] = [];
  for (const p of placements) {
    // Each load is its own copy (shared geometry, own materials), so tentacles bend independently.
    const model = await loadModel(p.name, { glowReceive: 0.5 });
    if (!model) continue;
    const root = model.root;
    root.position.copy(p.at);
    root.rotation.y = p.yaw;
    if (p.scale) root.scale.setScalar(p.scale);
    if (p.lift) root.position.y += p.lift;
    if (p.out) root.position.add(new Vector3(Math.sin(p.yaw), 0, Math.cos(p.yaw)).multiplyScalar(p.out));
    const seat = p.name === 'skeleton-pirate-sit' ? crew.shift() : undefined;
    if (seat) {
      seat.updateWorldMatrix(true, false);
      seat.matrixWorld.decompose(root.position, root.quaternion, new Vector3());
    }
    objects.push(root);
    if (p.name === 'rowboat') {
      root.updateMatrixWorld(true);
      for (const k of [0, 1]) {
        const c = model.node(`crew_${k}`);
        if (c) crew.push(c);
      }
    }
    for (const m of model.glows.values()) m.emissiveIntensity = m.name.includes('inflatable') ? 0.9 : m.name.includes('gold') ? 2.6 : 1.4;
    // Whatever carries a bend map (the `along` UV) sways: the tentacles.
    if (p.name.startsWith('kraken')) tentacles.push(...bendable(model, '*', { sway: 0.18, key: `kraken-${p.name}` }));
    if (p.name === 'treasure-chest') {
      chestLid = model.node('lid');
      chestChains = model.node('chains');
      chestBox = new Box3().setFromObject(root);
    }
  }
  const lidRest = chestLid?.rotation.x ?? 0;

  // Orange glow pouring off the inflatables; blue light over the sea-floor leaves.
  const glow: GlowLight[] = [
    ...[W(-0.5, -1.5), W(0.9, -2.6), W(-3.8, 0.4), W(4.6, -1.0), W(-2.5, -2.5)].map((p) => ({ x: p.x, z: p.z, y: 1.5, radius: 5.5, color: new Color(1, 0.45, 0.08), intensity: 0.5, flicker: 0 })),
    ...[T(0, 1), W(0, 3)].map((p) => ({ x: p.x, z: p.z, radius: 5, color: new Color(0.2, 0.25, 1), intensity: 0.35, flicker: 0 })),
  ];
  const sources = [
    { position: W(-0.5, 0.5).setY(2.5), color: new Color(1, 0.5, 0.15), intensity: 7, distance: 12 },
    { position: W(4, 0.5).setY(2.5), color: new Color(1, 0.5, 0.15), intensity: 6, distance: 10 },
    { position: T(0, 2).setY(2.2), color: new Color(1, 0.85, 0.6), intensity: 9, distance: 9 },
    // A lantern over the rowboat, so you can see its crew.
    { position: W(-2.2, 2.6).setY(2.2), color: new Color(1, 0.6, 0.3), intensity: 5, distance: 6 },
  ];
  // The purple LED edge of the path past the treasure, as in the video.
  const edge = stringLights([{ from: T(-4, 3), to: T(4, 3.6), sag: 0 }, { from: T(4, 3.6), to: T(7, 1.5), sag: 0 }], { spacing: 0.2, color: new Color(0.6, 0.2, 1), brightness: 12, glowEvery: 2, glowRadius: 1.2, glowIntensity: 0.25 });
  objects.push(edge.mesh);
  glow.push(...edge.lights);

  const gold = new Burst(160, { gravity: 4, brightness: 3 });
  objects.push(gold.mesh);
  let lidOpen = 0;
  // The tentacles' curl (0 at rest, 1 curled up), moved by a soft spring: a tap pulls them up and holds
  // them there a moment, then lets them sink back. Tapped again while they move, they carry on from where
  // they are (held up longer, or lifted again on the way down), never snapping back to start over.
  const CURL_HOLD = 1.4;
  let clock = 0;
  let curl = 0;
  let curlSpeed = 0;
  let curlUntil = -1;
  const seat = T(0, 0.95);

  return {
    objects,
    seat,
    glow,
    sources,
    update(dt) {
      clock += dt;
      // Up a little quicker than down (as a curl rising from the floor and sinking back to it); in small
      // steps, so a long frame can't throw it.
      for (let left = Math.min(dt, 0.1); left > 1e-6; left -= 1 / 120) {
        const h = Math.min(left, 1 / 120);
        const up = clock < curlUntil;
        const w = up ? 2.8 : 1.8;
        curlSpeed += (w * w * ((up ? 1.06 : 0) - curl) - 2 * w * curlSpeed) * h;
        curl += curlSpeed * h;
      }
      const k = Math.max(0, Math.min(1, curl));
      tentacles.forEach((t, i) => (t.wave.value = i % 2 === 0 ? k : k * 0.5));
      // The lid rests open; a tap lets it drop a little and creak back (the chains can't follow).
      if (chestLid) chestLid.rotation.x = lidRest + Math.sin(lidOpen * Math.PI) * 0.45;
      if (chestChains) chestChains.visible = lidOpen <= 0;
      lidOpen = Math.max(0, lidOpen - dt * 0.5);
      gold.update(dt, heightAt(treasureAt.x, treasureAt.z));
    },
    pick(ray: Ray) {
      if (chestBox && ray.intersectsBox(onGround(chestBox))) {
        return () => {
          lidOpen = 1;
          gold.emit(pointOnGround(T(0, 0).setY(1.1)), 50, [new Color(1, 0.8, 0.25), new Color(1, 0.6, 0.15), new Color(0.9, 0.9, 1)], 3, 2.5);
          void ctx.audio.sfx('chest-open', { at: pointOnGround(T(0, 0)), volume: 0.9 });
          // Sit on the edge of the platform, as people do.
          ctx.ui.say('Sit a while with the treasure. Move to get up.', 4);
          const w = ctx.walker;
          w.position.set(seat.x, heightAt(seat.x, seat.z), seat.z);
          w.yaw = treasureYaw;
          w.seated = true;
        };
      }
      for (const p of [W(-0.5, -1.5), W(0.9, -2.6), W(-3.8, 0.4), W(4.6, -1.0)]) {
        if (ray.distanceSqToPoint(pointOnGround(p.clone().setY(2.5))) < 4) {
          return () => {
            curlUntil = clock + CURL_HOLD;
            void ctx.audio.sfx('tentacle-curl', { at: pointOnGround(p.clone().setY(2)), volume: 0.9 });
            void ctx.audio.sfx('kraken-groan', { at: pointOnGround(W(0, -3)), volume: 0.8 });
          };
        }
      }
      return null;
    },
    dispose() {
      gold.dispose();
      edge.mesh.geometry.dispose();
    },
  };
}
