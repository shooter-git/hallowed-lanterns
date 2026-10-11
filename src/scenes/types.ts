import type { Object3D, Ray } from 'three';
import type { TapAction } from '../chapters/types.ts';
import type { GlowLight } from '../engine/glowfield.ts';
import type { LightSource } from '../engine/lights.ts';

/** A set piece placed inside a chapter (the owl, the web, the wreck…). */
export interface SetPiece {
  objects: Object3D[];
  glow: GlowLight[];
  sources: LightSource[];
  update(dt: number, time: number): void;
  pick(ray: Ray): TapAction | null;
  dispose(): void;
}
