import type { Portal } from '@allthespaces/portal';
import type { PerspectiveCamera, Ray, Scene, Texture, WebGLRenderer } from 'three';
import type { AudioDirector } from '../engine/audio.ts';
import type { Ember } from '../engine/ember.ts';
import type { GlowField } from '../engine/glowfield.ts';
import type { LightPool } from '../engine/lights.ts';
import type { Post } from '../engine/post.ts';
import type { Path, Walker } from '../engine/rig.ts';
import type { Sky } from '../engine/sky.ts';
import type { SurfaceMaps } from '../engine/texgen.ts';
import type { Terrain } from '../engine/terrain.ts';
import type { UI } from '../engine/ui.ts';

export type Tier = 'low' | 'mid' | 'high';
export type SurfaceKind = 'gravel' | 'dryGrass' | 'lawn' | 'leaves' | 'snow';

/** What a chapter can use from the engine. */
export interface ChapterContext {
  portal: Portal;
  renderer: WebGLRenderer;
  camera: PerspectiveCamera;
  tier: Tier;
  atlas: Texture;
  glow: GlowField;
  lights: LightPool;
  audio: AudioDirector;
  ember: Ember;
  walker: Walker;
  post: Post;
  sky: Sky;
  ui: UI;
  /** Baked ground textures (made once, shared between chapters). */
  surface(kind: SurfaceKind): SurfaceMaps;
  reducedMotion: boolean;
  /** Back to the beginning of the night. */
  restart: () => void;
}

/** What happens when someone taps something. */
export type TapAction = () => void;

export interface Chapter {
  readonly scene: Scene;
  readonly path: Path;
  /** Which way you face when you arrive (radians); along the path if left out. */
  readonly startYaw?: number;
  /** The lie of the land (gentle rises and dips); flat if left out. */
  readonly terrain?: Terrain;
  /** Music and ambience keys in the audio manifest. */
  readonly music: string;
  readonly ambience: string;
  /** Footstep sounds (sfx key). */
  readonly steps: string;
  /** Called when you arrive (the picture is still faded; it clears over the next seconds). */
  enter(): void;
  update(dt: number, time: number): void;
  /** What tapping along this ray would do, if anything. */
  pick(ray: Ray): TapAction | null;
  /** True once the chapter is over and the next can begin. */
  finished(): boolean;
  dispose(): void;
}

export interface ChapterInfo {
  id: string;
  numeral: string;
  name: string;
  subtitle: string;
  /** The key its music is in: the passage into the chapter is played in it (sfx passage-<key>). */
  key: 'd' | 'b' | 'g' | 'a' | 'fs';
  load: () => Promise<{ build: (ctx: ChapterContext) => Promise<Chapter> }>;
}
