import {
  Color,
  DoubleSide,
  Group,
  InstancedMesh,
  Matrix4,
  MeshStandardMaterial,
  type Object3D,
  Quaternion,
  type Ray,
  Shape,
  ShapeGeometry,
  Vector3,
} from 'three';
import type { ChapterContext } from '../chapters/types.ts';
import { CARVE } from '../engine/carvings.ts';
import { loadModel } from '../engine/models.ts';
import { PumpkinField, type PumpkinSpec } from '../engine/pumpkins.ts';
import { hallow } from '../engine/shared.ts';
import { pointOnGround } from '../engine/terrain.ts';
import type { SetPiece } from './types.ts';

/**
 * The giant owl: a pumpkin head with huge round eyes, a body of glowing pumpkins carved with
 * feathers, and enormous wings of hundreds of pale blue-teal feathers, in front of a reed fence
 * strung with fairy lights. Tap it: it hoots, blinks, turns its head to you and, slowly, as
 * something so big would, raises its wings and gives two great beats.
 */
export async function owl(ctx: ChapterContext, at: Vector3, yaw: number): Promise<SetPiece> {
  const objects: Object3D[] = [];
  const group = new Group();
  group.position.copy(at);
  group.rotation.y = yaw;
  objects.push(group);
  const toWorld = (v: Vector3) => v.clone().applyAxisAngle(new Vector3(0, 1, 0), yaw).add(at);

  const model = await loadModel('pumpkin-owl', { glowReceive: 0.6 });
  const specs: PumpkinSpec[] = [];
  const feather = (i: number) => ({
    position: new Vector3(),
    size: new Vector3(0.24, 0.27, 0.22),
    yaw,
    carve: CARVE.feathers,
    skin: new Color(0.7, 0.26, 0.05),
    glow: new Color(1, 0.55, 0.15).multiplyScalar(3.2),
    phase: i * 0.37,
  });
  let wings: Object3D[] = [];
  let head = -1;
  const headNode = model?.node('head');
  const eyes = model?.glows.get('glow_eyes');
  if (model) {
    group.add(model.root);
    for (const m of model.glows.values()) m.emissiveIntensity = m.name === 'glow_feathers' ? 1.2 : 2.5;
    wings = ['wing_L', 'wing_R'].map((n) => model.node(n)).filter(Boolean) as Object3D[];
    group.updateMatrixWorld(true);
    model.node('body_spots')?.traverse((o) => {
      if (!o.name.startsWith('spot_')) return;
      const s = feather(specs.length);
      s.position.copy(o.getWorldPosition(new Vector3()));
      // Each spot's +Z points out of the body, and its scale is the pumpkin's diameter.
      const out = new Vector3(0, 0, 1).applyQuaternion(o.getWorldQuaternion(new Quaternion()));
      s.yaw = Math.atan2(out.x, out.z);
      const r = o.getWorldScale(new Vector3()).x / 2;
      s.size = new Vector3(r, r * 1.1, r * 0.92);
      specs.push(s);
    });
  } else {
    // The body: an egg of carved feather pumpkins.
    for (let r = 0; r < 7; r++) {
      const y = 0.35 + r * 0.38;
      const rad = 0.95 * Math.sin(((r + 0.6) / 7.4) * Math.PI) + 0.15;
      const n = Math.max(3, Math.round(rad * 5));
      for (let k = 0; k < n; k++) {
        const a = -0.9 + (k / Math.max(1, n - 1)) * 1.8;
        const s = feather(specs.length);
        s.position.copy(toWorld(new Vector3(Math.sin(a) * rad, y, Math.cos(a) * rad * 0.7)));
        s.yaw = yaw + a * 0.8;
        specs.push(s);
      }
    }
    // The head: a big pumpkin with the eyes painted on, green ear tufts.
    head = specs.length;
    specs.push({ position: toWorld(new Vector3(0, 3.45, 0.1)), size: new Vector3(0.8, 0.7, 0.75), yaw, carve: 100 + CARVE.owlEyes, skin: new Color(0.72, 0.28, 0.05), glow: new Color(0.95, 0.88, 0.7) });
    // Wings: overlapping pointed feathers in fanned rows.
    const shape = new Shape();
    shape.moveTo(0, 0);
    shape.quadraticCurveTo(0.12, 0.18, 0.05, 0.55);
    shape.lineTo(0, 0.62);
    shape.lineTo(-0.05, 0.55);
    shape.quadraticCurveTo(-0.12, 0.18, 0, 0);
    const geo = new ShapeGeometry(shape, 4);
    const mat = hallow(new MeshStandardMaterial({ color: new Color(0.55, 0.78, 0.85), emissive: new Color(0.1, 0.45, 0.55), emissiveIntensity: 0.9, side: DoubleSide, roughness: 0.6 }), { key: 'feather', glow: 0.8 });
    for (const side of [-1, 1]) {
      const wing = new Group();
      wing.position.set(side * 0.9, 2.6, 0);
      const list: Matrix4[] = [];
      for (let row = 0; row < 7; row++) {
        const len = 4.2 - row * 0.35;
        const count = 26 - row * 2;
        for (let k = 0; k < count; k++) {
          const t = k / (count - 1);
          const x = side * (0.2 + t * len);
          const y = 0.9 - row * 0.32 + Math.sin(t * Math.PI) * 0.6 - t * 0.6;
          const q = new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), side * (-0.6 - t * 0.9) + (Math.random() - 0.5) * 0.15);
          list.push(new Matrix4().compose(new Vector3(x, y, -row * 0.03), q, new Vector3(1.2, 1.2 + row * 0.08, 1)));
        }
      }
      const mesh = new InstancedMesh(geo, mat, list.length);
      list.forEach((m, i) => mesh.setMatrixAt(i, m));
      mesh.computeBoundingSphere();
      wing.add(mesh);
      group.add(wing);
      wings.push(wing);
    }
  }
  const pumpkins = new PumpkinField(specs, ctx.atlas, { detail: [32, 14], simple: [16, 8] });
  objects.push(pumpkins.group);

  // The display, in seconds since the tap (-1 when at rest).
  let display = -1;
  let beats = 0;
  let blink = 0;
  let look = 0;
  const rest = wings.map((w) => w.rotation.z);
  const restX = wings.map((w) => w.rotation.x);
  const RAISE = 0.8; // wings up
  const BEAT = 1.05; // each beat
  const FOLD = 1.3; // folding back
  const UP = 0.3; // how far the wings rise (rad)
  const headRest = headNode?.rotation.y ?? 0;
  const centre = toWorld(new Vector3(0, 2.2, 0));

  return {
    objects,
    glow: [
      ...pumpkins.glowLights(1.8, 0.2),
      { x: centre.x, z: centre.z, radius: 6, color: new Color(0.3, 0.7, 0.9), intensity: 0.35, flicker: 0 },
    ],
    sources: [{ position: toWorld(new Vector3(0, 2.5, 3)), color: new Color(0.45, 0.8, 1), intensity: 5, distance: 9 }],
    update(dt, time) {
      // Wings: + lowers both tips, - raises them; the twist turns the leading edge down.
      let lift = 0;
      let twist = 0;
      if (display >= 0) {
        display += dt;
        const t = display;
        const smooth = (u: number) => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u));
        if (t < RAISE) lift = -UP * smooth(t / RAISE);
        else if (t < RAISE + 2 * BEAT) {
          // Two slow beats, the second smaller: a quick, heavy downstroke and a slower recovery.
          const k = (t - RAISE) / BEAT;
          const n = Math.floor(k);
          const p = k - n;
          const depth = n === 0 ? 1 : 0.65;
          const down = p < 0.4 ? smooth(p / 0.4) : 1 - smooth((p - 0.4) / 0.6);
          lift = -UP + (UP + 0.1) * depth * down;
          twist = p < 0.4 ? 0.14 * Math.sin((Math.PI * p) / 0.4) * depth : -0.08 * Math.sin((Math.PI * (p - 0.4)) / 0.6) * depth;
          if (n + 1 > beats) {
            beats = n + 1;
            void ctx.audio.sfx('wing-beat', { at: pointOnGround(centre), volume: 0.8 * depth });
          }
        } else if (t < RAISE + 2 * BEAT + FOLD) {
          // Folding back, settling with a little overshoot.
          const u = (t - RAISE - 2 * BEAT) / FOLD;
          lift = -UP * (1 - smooth(u)) + 0.03 * Math.sin(Math.PI * smooth(u));
        } else display = -1;
      }
      wings.forEach((w, i) => {
        const side = i === 0 ? 1 : -1;
        w.rotation.z = (rest[i] ?? 0) + side * (Math.sin(time * 0.8) * 0.02 + lift);
        w.rotation.x = (restX[i] ?? 0) + twist;
      });
      // The body rises a touch with each downstroke.
      const beating = display >= RAISE && display < RAISE + 2 * BEAT;
      if (model) model.root.position.y = beating ? Math.max(0, lift + UP) * 0.12 : 0;
      if (blink > 0) {
        blink -= dt;
        if (head >= 0) pumpkins.setCarve(head, blink > 0 ? -1 : 100 + CARVE.owlEyes);
        if (eyes) eyes.emissiveIntensity = blink > 0 ? 0.15 : 2.5;
      }
      // When you tap it, the head swivels round to you, the way owls do, and back.
      look = Math.max(0, look - dt / 2.8);
      if (headNode) headNode.rotation.y = headRest + Math.sin(look * Math.PI) * 0.55;
      pumpkins.update(ctx.camera, dt);
    },
    pick(ray: Ray) {
      if (ray.distanceSqToPoint(pointOnGround(centre)) > 6) return null;
      return () => {
        blink = 0.25;
        look = 1;
        void ctx.audio.sfx('owl-hoot', { at: pointOnGround(centre), volume: 0.9 });
        // Its wings, once it's done the last display.
        if (display < 0) {
          display = 0;
          beats = 0;
        }
      };
    },
    dispose() {
      pumpkins.dispose();
    },
  };
}
