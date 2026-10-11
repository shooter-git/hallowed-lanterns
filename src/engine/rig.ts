import type { Portal } from '@allthespaces/portal';
import { CatmullRomCurve3, Euler, type PerspectiveCamera, Vector2, Vector3 } from 'three';
import { heightAt } from './terrain.ts';

/**
 * A walkable path: a smooth centre line with a width. People walk freely, but stay within the
 * corridor (or the open area, where the width is large).
 */
export class Path {
  readonly points: Vector2[] = [];
  readonly tangents: Vector2[] = [];
  readonly cum: number[] = [];
  readonly widths: number[] = [];
  readonly length: number;
  readonly step = 0.25;

  constructor(
    control: [number, number][],
    width: number | ((s: number, total: number) => number),
  ) {
    const curve = new CatmullRomCurve3(
      control.map(([x, z]) => new Vector3(x, 0, z)),
      false,
      'centripetal',
    );
    const total = curve.getLength();
    const n = Math.max(2, Math.ceil(total / this.step));
    const p = new Vector3();
    const t = new Vector3();
    for (let i = 0; i <= n; i++) {
      const u = i / n;
      curve.getPointAt(u, p);
      curve.getTangentAt(u, t);
      this.points.push(new Vector2(p.x, p.z));
      this.tangents.push(new Vector2(t.x, t.z).normalize());
      this.cum.push(u * total);
      this.widths.push(typeof width === 'number' ? width : width(u * total, total));
    }
    this.length = total;
  }

  /** The point (and tangent) at distance `s` along the path. */
  at(s: number, out = new Vector2(), tangent?: Vector2): Vector2 {
    const f = Math.max(0, Math.min(this.points.length - 1.001, s / this.step));
    const i = Math.floor(f);
    const k = f - i;
    out.copy(this.points[i] as Vector2).lerp(this.points[i + 1] as Vector2, k);
    if (tangent) tangent.copy(this.tangents[i] as Vector2).lerp(this.tangents[i + 1] as Vector2, k).normalize();
    return out;
  }

  /** Nearest point on the path to `p`, searching near `hint` (an index) for speed. */
  nearest(p: Vector2, hint = -1): { index: number; s: number; lateral: number; width: number } {
    let best = 0;
    let bestD = Number.POSITIVE_INFINITY;
    const from = hint < 0 ? 0 : Math.max(0, hint - 60);
    const to = hint < 0 ? this.points.length : Math.min(this.points.length, hint + 60);
    for (let i = from; i < to; i++) {
      const d = (this.points[i] as Vector2).distanceToSquared(p);
      if (d < bestD) {
        bestD = d;
        best = i;
      }
    }
    const c = this.points[best] as Vector2;
    const t = this.tangents[best] as Vector2;
    const dx = p.x - c.x;
    const dz = p.y - c.y;
    const lateral = dx * -t.y + dz * t.x;
    const along = dx * t.x + dz * t.y;
    return {
      index: best,
      s: Math.max(0, Math.min(this.length, (this.cum[best] as number) + along)),
      lateral,
      width: this.widths[best] as number,
    };
  }
}

export interface Look {
  yaw: number;
  pitch: number;
}

/**
 * Walking at eye height along a path: the stick (W A S D, gamepad, touch joystick) to walk, drag
 * (or the arrow keys, or the right stick) to look, a tap to touch things. "Walk with me" walks for
 * you, at an easy pace, along the path (or toward whatever the chapter says to follow).
 */
export class Walker {
  readonly position = new Vector3();
  yaw = 0;
  pitch = 0;
  /** Distance along the path. */
  s = 0;
  /** Walks by itself. */
  auto = false;
  /** Somewhere the automatic walk should go instead of along the path (e.g. the Ember). */
  autoTarget: Vector3 | null = null;
  speed = 1.6;
  eyeHeight = 1.62;
  /** Sitting (lower eyes, no walking). */
  seated = false;
  /** Called on each footstep. */
  onStep: (() => void) | null = null;
  /** Called with screen coordinates on a tap or click that wasn't a drag. */
  onTap: ((x: number, y: number) => void) | null = null;
  /** Called with screen coordinates as the mouse moves (for hover). */
  onHover: ((x: number, y: number) => void) | null = null;
  /** Walking speed right now (m/s). */
  pace = 0;

  private path: Path | null = null;
  private index = -1;
  private lookVel = new Vector2();
  private lastLook = -10;
  private now = 0;
  private stride = 0;
  private bob = 0;
  private eye = 1.62;
  private readonly euler = new Euler(0, 0, 0, 'YXZ');
  private readonly keys = new Set<string>();
  private readonly abort = new AbortController();
  private readonly drags = new Map<number, { x: number; y: number; sx: number; sy: number; t: number; moved: boolean }>();

  constructor(
    private readonly portal: Portal,
    private readonly camera: PerspectiveCamera,
    canvas: HTMLElement,
  ) {
    const { signal } = this.abort;
    canvas.addEventListener(
      'pointerdown',
      (e) => {
        this.drags.set(e.pointerId, { x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, t: performance.now(), moved: false });
        canvas.setPointerCapture?.(e.pointerId);
      },
      { signal },
    );
    canvas.addEventListener(
      'pointermove',
      (e) => {
        const d = this.drags.get(e.pointerId);
        if (!d) {
          if (e.pointerType === 'mouse') this.onHover?.(e.clientX, e.clientY);
          return;
        }
        const dx = e.clientX - d.x;
        const dy = e.clientY - d.y;
        d.x = e.clientX;
        d.y = e.clientY;
        if (Math.hypot(e.clientX - d.sx, e.clientY - d.sy) > 8) d.moved = true;
        if (!d.moved) return;
        // Sensitivity scales with the field of view, so it feels the same in portrait.
        const k = (this.camera.fov / 60) * (e.pointerType === 'mouse' ? 0.0042 : 0.0055);
        this.turn(dx * k, dy * k);
      },
      { signal },
    );
    const end = (e: PointerEvent) => {
      const d = this.drags.get(e.pointerId);
      if (!d) return;
      this.drags.delete(e.pointerId);
      if (e.type === 'pointerup' && !d.moved && performance.now() - d.t < 450) this.onTap?.(e.clientX, e.clientY);
    };
    canvas.addEventListener('pointerup', end, { signal });
    canvas.addEventListener('pointercancel', end, { signal });
    addEventListener(
      'keydown',
      (e) => {
        if ((e.target as HTMLElement)?.closest?.('input, textarea')) return;
        if (e.code.startsWith('Arrow')) {
          this.keys.add(e.code);
          e.preventDefault();
        }
      },
      { signal },
    );
    addEventListener('keyup', (e) => this.keys.delete(e.code), { signal });
    addEventListener('blur', () => this.keys.clear(), { signal });
  }

  /** Puts you on a path, at distance `s`, facing along it. */
  setPath(path: Path, s = 0, lateral = 0) {
    this.path = path;
    const p = new Vector2();
    const t = new Vector2();
    path.at(s, p, t);
    this.position.set(p.x + -t.y * lateral, 0, p.y + t.x * lateral);
    this.position.y = heightAt(this.position.x, this.position.z);
    this.index = -1;
    this.s = s;
    this.yaw = Math.atan2(-t.x, -t.y);
    this.pitch = 0.04;
    this.lookVel.set(0, 0);
  }

  private turn(dx: number, dy: number) {
    this.lastLook = this.now;
    this.lookVel.x -= dx;
    this.lookVel.y -= dy;
  }

  /** Has the person looked around in the last `seconds`? */
  lookedRecently(seconds = 2) {
    return this.now - this.lastLook < seconds;
  }

  update(dt: number) {
    this.now += dt;
    const reduced = this.portal.reducedMotion;
    // Look: drag deltas applied with a little smoothing; arrows and the right stick turn steadily.
    let kx = (this.keys.has('ArrowRight') ? 1 : 0) - (this.keys.has('ArrowLeft') ? 1 : 0);
    let ky = (this.keys.has('ArrowDown') ? 1 : 0) - (this.keys.has('ArrowUp') ? 1 : 0);
    for (const pad of this.portal.input.gamepads()) {
      const ax = pad.axes[2] ?? 0;
      const ay = pad.axes[3] ?? 0;
      if (Math.hypot(ax, ay) > 0.15) {
        kx += ax;
        ky += ay;
      }
    }
    if (kx || ky) {
      this.lastLook = this.now;
      this.yaw -= kx * 1.6 * dt;
      this.pitch -= ky * 1.1 * dt;
    }
    const take = 1 - Math.exp(-dt * 30);
    this.yaw += this.lookVel.x * take;
    this.pitch += this.lookVel.y * take;
    this.lookVel.multiplyScalar(1 - take);
    this.pitch = Math.max(-1.25, Math.min(1.3, this.pitch));

    // Walk.
    const move = this.portal.input.stick('move');
    let mx = move.x;
    let my = move.y;
    const manual = Math.hypot(mx, my) > 0.05;
    if (manual) this.auto = false;
    if (this.seated) {
      mx = 0;
      my = 0;
    } else if (this.auto && this.path) {
      // Head for a point a little ahead (or the target), turning gently toward where we're going.
      const goal = new Vector2();
      if (this.autoTarget) goal.set(this.autoTarget.x, this.autoTarget.z);
      else this.path.at(this.s + 2.5, goal);
      const dx = goal.x - this.position.x;
      const dz = goal.y - this.position.z;
      const dist = Math.hypot(dx, dz);
      const want = Math.atan2(-dx, -dz);
      if (!this.lookedRecently(2.5)) {
        let d = want - this.yaw;
        d = Math.atan2(Math.sin(d), Math.cos(d));
        this.yaw += d * (1 - Math.exp(-dt * 1.4));
        this.pitch += (0.06 - this.pitch) * (1 - Math.exp(-dt * 1.0));
      }
      // Walk toward the goal, relative to where we're facing.
      const f = Math.min(1, dist / 1.2) * 0.7;
      const rel = want - this.yaw;
      mx = -Math.sin(rel) * f;
      my = Math.cos(rel) * f;
    }
    const sin = Math.sin(this.yaw);
    const cos = Math.cos(this.yaw);
    const v = this.speed * dt;
    const before = this.position.clone();
    this.position.x += (mx * cos - my * sin) * v;
    this.position.z += (-mx * sin - my * cos) * v;

    // Stay on the path.
    if (this.path) {
      const p2 = new Vector2(this.position.x, this.position.z);
      const n = this.path.nearest(p2, this.index);
      this.index = n.index;
      this.s = n.s;
      const half = n.width / 2;
      if (Math.abs(n.lateral) > half) {
        const t = this.path.tangents[n.index] as Vector2;
        const push = Math.abs(n.lateral) - half;
        const sign = Math.sign(n.lateral);
        this.position.x -= -t.y * push * sign;
        this.position.z -= t.x * push * sign;
      }
      // Don't walk off either end.
      const first = this.path.points[0] as Vector2;
      const last = this.path.points[this.path.points.length - 1] as Vector2;
      const t0 = this.path.tangents[0] as Vector2;
      const t1 = this.path.tangents[this.path.tangents.length - 1] as Vector2;
      const back = (this.position.x - first.x) * t0.x + (this.position.z - first.y) * t0.y;
      if (back < 0) {
        this.position.x -= t0.x * back;
        this.position.z -= t0.y * back;
      }
      const over = (this.position.x - last.x) * t1.x + (this.position.z - last.y) * t1.y;
      if (over > 0) {
        this.position.x -= t1.x * over;
        this.position.z -= t1.y * over;
      }
    }
    const moved = Math.hypot(this.position.x - before.x, this.position.z - before.z);
    this.pace = moved / Math.max(dt, 1e-4);

    // Footsteps and a gentle head bob.
    const strideLen = 0.72;
    this.stride += moved;
    if (this.stride > strideLen) {
      this.stride -= strideLen;
      this.onStep?.();
    }
    const walking = Math.min(1, this.pace / this.speed);
    this.bob += moved * (Math.PI / strideLen);
    const bobY = reduced ? 0 : Math.abs(Math.sin(this.bob)) * 0.028 * walking - 0.014 * walking;
    const sway = reduced ? 0 : Math.sin(this.bob * 0.5) * 0.004 * walking;
    const targetEye = this.seated ? 1.05 : this.eyeHeight;
    this.eye += (targetEye - this.eye) * (1 - Math.exp(-dt * 3));
    // Stand on the ground: up the rises and down the dips, smoothly.
    const ground = heightAt(this.position.x, this.position.z);
    this.position.y += (ground - this.position.y) * (dt > 0 ? 1 - Math.exp(-dt * 10) : 1);
    this.camera.position.set(this.position.x, this.position.y + this.eye + bobY, this.position.z);
    this.euler.set(this.pitch, this.yaw, sway);
    this.camera.quaternion.setFromEuler(this.euler);
  }

  dispose() {
    this.abort.abort();
  }
}
