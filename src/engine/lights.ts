import { type Color, PointLight, type Scene, type Vector3 } from 'three';

export interface LightSource {
  position: Vector3;
  color: Color;
  intensity: number;
  distance: number;
  /** Flicker phase, or undefined for a steady light. */
  phase?: number;
}

/**
 * A few real point lights that follow the brightest lanterns near you, so nearby surfaces get
 * proper highlights and shading while the glow field handles the hundreds further away. The number
 * of lights never changes (so shaders never recompile); unused ones just go dark.
 */
export class LightPool {
  readonly lights: PointLight[] = [];
  sources: LightSource[] = [];
  private time = 0;

  constructor(count: number) {
    for (let i = 0; i < count; i++) {
      const l = new PointLight(0xffffff, 0, 6, 1.8);
      this.lights.push(l);
    }
  }

  attach(scene: Scene) {
    for (const l of this.lights) scene.add(l);
  }

  update(dt: number, camera: Vector3, forward: Vector3) {
    this.time += dt;
    // Score by distance, preferring what's in front of us.
    const scored = this.sources
      .map((s) => {
        const dx = s.position.x - camera.x;
        const dy = s.position.y - camera.y;
        const dz = s.position.z - camera.z;
        const d = Math.hypot(dx, dy, dz);
        const ahead = (dx * forward.x + dy * forward.y + dz * forward.z) / Math.max(d, 0.001);
        return { s, score: d * (1.3 - 0.5 * ahead) / Math.max(0.2, s.intensity) };
      })
      .sort((a, b) => a.score - b.score);
    const ease = 1 - Math.exp(-dt * 6);
    this.lights.forEach((l, i) => {
      const pick = scored[i];
      if (!pick) {
        l.intensity *= 1 - ease;
        return;
      }
      const s = pick.s;
      if (l.position.distanceToSquared(s.position) > 0.01) {
        // Swapping to another lantern: dim, move, brighten (eased so it never pops).
        l.intensity *= 1 - Math.min(1, ease * 2);
        if (l.intensity < 0.05) {
          l.position.copy(s.position);
          l.color.copy(s.color);
          l.distance = s.distance;
        }
        return;
      }
      const fl =
        s.phase === undefined
          ? 1
          : 0.85 + 0.08 * Math.sin(this.time * 7.3 + s.phase * 6.28) + 0.05 * Math.sin(this.time * 13.1 + s.phase * 17);
      l.intensity += (s.intensity * fl - l.intensity) * ease;
    });
  }

  dispose() {
    for (const l of this.lights) {
      l.removeFromParent();
      l.dispose();
    }
  }
}
