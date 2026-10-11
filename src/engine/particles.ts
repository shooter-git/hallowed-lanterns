import {
  BoxGeometry,
  type BufferGeometry,
  Color,
  DynamicDrawUsage,
  InstancedMesh,
  Matrix4,
  MeshBasicMaterial,
  Quaternion,
  Vector3,
} from 'three';
import { hallow } from './shared.ts';

interface Bit {
  p: Vector3;
  v: Vector3;
  spin: Vector3;
  rot: Quaternion;
  life: number;
  max: number;
}

/**
 * Bursts of small bright things (sprinkles, petals, glints): instanced, with gravity, drag and
 * spin. Colours glow a little, as everything does under the farm's blacklights.
 */
export class Burst {
  readonly mesh: InstancedMesh;
  private readonly bits: Bit[] = [];
  private next = 0;
  private readonly m = new Matrix4();
  private readonly hidden = new Matrix4().makeScale(0, 0, 0);

  constructor(
    capacity: number,
    options: { geometry?: BufferGeometry; gravity?: number; drag?: number; brightness?: number } = {},
  ) {
    const geo = options.geometry ?? new BoxGeometry(0.045, 0.012, 0.012);
    const mat = hallow(new MeshBasicMaterial({ color: 0xffffff }), { key: 'burst' });
    this.mesh = new InstancedMesh(geo, mat, capacity);
    this.mesh.instanceMatrix.setUsage(DynamicDrawUsage);
    this.mesh.frustumCulled = false;
    for (let i = 0; i < capacity; i++) {
      this.bits.push({ p: new Vector3(), v: new Vector3(), spin: new Vector3(), rot: new Quaternion(), life: 0, max: 1 });
      this.mesh.setMatrixAt(i, this.hidden);
      this.mesh.setColorAt(i, new Color(1, 1, 1));
    }
    this.gravity = options.gravity ?? 3.5;
    this.drag = options.drag ?? 0.9;
    this.brightness = options.brightness ?? 1.6;
  }

  gravity: number;
  drag: number;
  brightness: number;

  /** Throws `count` bits from `at`, upward and outward, in the given colours. */
  emit(at: Vector3, count: number, colors: Color[], speed = 4, life = 3) {
    for (let k = 0; k < count; k++) {
      const i = this.next;
      this.next = (this.next + 1) % this.bits.length;
      const b = this.bits[i] as Bit;
      b.p.copy(at).add(new Vector3((Math.random() - 0.5) * 0.4, (Math.random() - 0.5) * 0.2, (Math.random() - 0.5) * 0.4));
      const a = Math.random() * Math.PI * 2;
      const up = 0.6 + Math.random() * 0.8;
      b.v.set(Math.cos(a) * (1 - up * 0.5), up, Math.sin(a) * (1 - up * 0.5)).multiplyScalar(speed * (0.5 + Math.random() * 0.7));
      b.spin.set(Math.random() * 12 - 6, Math.random() * 12 - 6, Math.random() * 12 - 6);
      b.rot.setFromAxisAngle(new Vector3(Math.random(), Math.random(), Math.random()).normalize(), Math.random() * 6);
      b.max = life * (0.6 + Math.random() * 0.6);
      b.life = b.max;
      const c = (colors[Math.floor(Math.random() * colors.length)] as Color).clone().multiplyScalar(this.brightness);
      this.mesh.setColorAt(i, c);
    }
    if (this.mesh.instanceColor) this.mesh.instanceColor.needsUpdate = true;
  }

  update(dt: number, floor = 0) {
    const q = new Quaternion();
    const s = new Vector3();
    let any = false;
    this.bits.forEach((b, i) => {
      if (b.life <= 0) return;
      any = true;
      b.life -= dt;
      b.v.y -= this.gravity * dt;
      b.v.multiplyScalar(Math.exp(-this.drag * dt));
      b.p.addScaledVector(b.v, dt);
      if (b.p.y < floor + 0.01) {
        b.p.y = floor + 0.01;
        b.v.set(0, 0, 0);
        b.spin.multiplyScalar(0.8);
      }
      q.setFromAxisAngle(b.spin.clone().normalize(), b.spin.length() * dt);
      b.rot.multiply(q);
      const k = b.life <= 0 ? 0 : Math.min(1, b.life / 0.4);
      s.set(k, k, k);
      this.m.compose(b.p, b.rot, s);
      this.mesh.setMatrixAt(i, this.m);
    });
    if (any) this.mesh.instanceMatrix.needsUpdate = true;
  }

  dispose() {
    this.mesh.geometry.dispose();
    (this.mesh.material as MeshBasicMaterial).dispose();
  }
}

export const RAINBOW = [
  new Color(1, 0.15, 0.25),
  new Color(1, 0.55, 0.05),
  new Color(1, 0.9, 0.1),
  new Color(0.2, 0.9, 0.3),
  new Color(0.15, 0.55, 1),
  new Color(0.65, 0.25, 1),
  new Color(1, 0.4, 0.8),
];
