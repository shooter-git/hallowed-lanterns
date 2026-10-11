import type { Portal } from '@allthespaces/portal';
import { createStage, type Stage } from '@allthespaces/portal/three';
import { Color, NoToneMapping, Raycaster, Vector2, Vector3 } from 'three';
import { CHAPTERS } from '../chapters/index.ts';
import type { Chapter, ChapterContext, SurfaceKind, Tier } from '../chapters/types.ts';
import { AudioDirector } from './audio.ts';
import { buildCarvingAtlas } from './carvings.ts';
import { Ember } from './ember.ts';
import { GlowField } from './glowfield.ts';
import { LightPool } from './lights.ts';
import { People } from './people.ts';
import { Post } from './post.ts';
import { Walker } from './rig.ts';
import { shared } from './shared.ts';
import { Sky } from './sky.ts';
import { setCurrentTerrain } from './terrain.ts';
import { bakeSurface, DRY_GRASS, GRAVEL, LAWN, LEAF_LITTER, SNOW, type SurfaceMaps } from './texgen.ts';
import { UI } from './ui.ts';

type Progress = {
  /** Furthest chapter reached (index). */
  reached: number;
};

/**
 * Runs the night: the renderer and its finishing, the walk, the Ember, sound, the chapters in
 * order and the fog-soft transitions between them.
 */
export class Engine {
  private stage!: Stage;
  private ctx!: ChapterContext;
  private chapter: Chapter | null = null;
  private index = 0;
  private next: Promise<Chapter> | null = null;
  private transition: { t: number; phase: 'out' | 'in'; target: number } | null = null;
  private time = 0;
  private begun = false;
  private progress: Progress = { reached: 0 };
  private readonly raycaster = new Raycaster();
  private readonly surfaces = new Map<SurfaceKind, SurfaceMaps>();
  private moved = false;
  private people!: People;

  constructor(private readonly portal: Portal) {}

  async boot() {
    const portal = this.portal;
    const forced = import.meta.env.DEV ? new URLSearchParams(location.search).get('tier') : null;
    portal.progress(0.05, 'Gathering pumpkins');
    this.stage = createStage(portal, { fov: 62, shadows: false, antialias: false });
    const { renderer, camera } = this.stage;
    // Drawn without a graphics card (a software renderer): use the lightest settings so the
    // page keeps answering.
    let tier = (forced ?? portal.tier) as Tier;
    const gl = renderer.getContext();
    const info = gl.getExtension('WEBGL_debug_renderer_info');
    const name = String(info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
    if (!forced && /swiftshader|llvmpipe|software|basic render/i.test(name)) tier = 'low';
    renderer.toneMapping = NoToneMapping;
    renderer.setClearColor(0x000000, 1);
    camera.near = 0.05;
    camera.far = 700;
    camera.updateProjectionMatrix();

    const post = new Post(renderer, { samples: tier === 'low' ? 0 : 4, levels: tier === 'low' ? 5 : 6 });
    const glow = new GlowField(tier === 'low' ? 256 : 512);
    const lights = new LightPool(tier === 'low' ? 2 : tier === 'mid' ? 4 : 6);
    const sky = new Sky();
    const ember = new Ember();
    const ui = new UI(portal.viewport.touch);
    const walker = new Walker(portal, camera, renderer.domElement);
    const audio = new AudioDirector(portal);
    portal.input.define({ move: 'stick' });

    portal.progress(0.15, 'Carving faces');
    const atlas = buildCarvingAtlas();
    await audio.load();
    try {
      const saved = await portal.save.personal.get<Progress>('progress');
      if (saved) this.progress = saved;
    } catch {
      // Nothing saved yet.
    }

    this.ctx = {
      portal,
      renderer,
      camera,
      tier,
      atlas,
      glow,
      lights,
      audio,
      ember,
      walker,
      post,
      sky,
      ui,
      surface: (kind) => {
        let s = this.surfaces.get(kind);
        if (!s) {
          const glsl = { gravel: GRAVEL, dryGrass: DRY_GRASS, lawn: LAWN, leaves: LEAF_LITTER, snow: SNOW }[kind];
          s = bakeSurface(renderer, glsl, tier === 'low' ? 512 : 1024);
          this.surfaces.set(kind, s);
        }
        return s;
      },
      reducedMotion: portal.reducedMotion,
      restart: () => this.goTo(0),
    };

    this.people = new People(
      portal,
      (i) => CHAPTERS[i]?.name ?? 'the next part of the night',
      (text) => ui.say(text, 4),
    );

    portal.progress(0.35, 'Lighting candles');
    this.chapter = await this.build(0);
    // Set the scene (light, sky, fog) now, so the title sits over the real place.
    this.enter(this.chapter, true);
    portal.progress(0.75, 'Rolling in the fog');
    await renderer.compileAsync(this.chapter.scene, camera);

    // Input: taps touch things; E / Enter / gamepad A touch what's in the middle of the view.
    walker.onTap = (x, y) => this.tap(x, y);
    walker.onHover = (x, y) => {
      const action = this.pickAt(x, y);
      renderer.domElement.style.cursor = action ? 'pointer' : '';
    };
    addEventListener('keydown', (e) => {
      if (!this.begun || e.repeat) return;
      if (e.code === 'KeyE' || e.code === 'Enter' || e.code === 'Space') {
        if ((e.target as HTMLElement)?.closest?.('button')) return;
        this.tap(innerWidth / 2, innerHeight / 2);
      }
    });
    walker.onStep = () => {
      if (!this.chapter) return;
      void audio.sfx(this.chapter.steps, { volume: 0.3, rate: 0.93 + Math.random() * 0.14, send: 'sfx' });
    };
    ui.walkButton.addEventListener('click', () => {
      walker.auto = !walker.auto;
      ui.setWalking(walker.auto);
      void audio.sfx('ui-tap', { send: 'ui', volume: 0.5 });
    });
    portal.onExit(() => {
      void portal.save.personal.set('progress', this.progress).catch(() => undefined);
    });

    let padA = false;
    this.stage.loop((dt) => {
      const pads = portal.input.gamepads();
      const a = pads.some((p) => (p.buttons[0] ?? 0) > 0.5);
      if (a && !padA && this.begun) this.tap(innerWidth / 2, innerHeight / 2);
      padA = a;
      this.frame(dt);
    });
    portal.progress(1, 'Ready');
    portal.ready();

    // While developing: ?at=<metres> starts straight away at that point of the first chapter,
    // ?chapter=<n> at another chapter, and window.hl gives scripts the engine.
    if (import.meta.env.DEV) {
      const q = new URLSearchParams(location.search);
      (window as unknown as { hl: unknown }).hl = this;
      if (q.has('at') || q.has('chapter')) {
        const n = Number(q.get('chapter') ?? 0);
        if (n > 0) {
          this.chapter.dispose();
          this.chapter = await this.build(n);
          this.index = n;
          this.enter(this.chapter, true);
        }
        this.begin();
        const at = Number(q.get('at') ?? 0);
        if (at > 0) walker.setPath(this.chapter.path, at);
        return;
      }
    }

    await ui.showTitle(() => {
      // Inside the tap itself, so every browser lets the sound start.
      void portal.audio.context.resume();
    });
    this.begin();
  }

  private begin() {
    const { ui, audio, walker, portal } = this.ctx;
    audio.start();
    this.begun = true;
    void audio.setScene(this.chapter?.music ?? null, this.chapter?.ambience ?? null, 3);
    ui.showControls();
    const info = CHAPTERS[this.index];
    if (info) setTimeout(() => ui.chapterCard(info.numeral, info.name, info.subtitle), 600);
    setTimeout(
      () =>
        ui.showHint(
          portal.viewport.touch
            ? 'Drag to look around · walk with the stick · tap the lanterns'
            : 'W A S D to walk · drag to look · click the lanterns',
          10,
        ),
      5200,
    );
    this.refreshMenu();
    walker.auto = false;
  }

  private async build(index: number): Promise<Chapter> {
    const info = CHAPTERS[index];
    if (!info) throw new Error(`No chapter ${index}`);
    const mod = await info.load();
    return mod.build(this.ctx);
  }

  /** Puts the shared things (sky, Ember, lights) into a chapter's scene and starts there. */
  private enter(chapter: Chapter, run: boolean) {
    const { sky, ember, lights, walker, audio } = this.ctx;
    setCurrentTerrain(chapter.terrain ?? null);
    if (chapter.terrain) {
      shared.uTerrain.value = chapter.terrain.texture;
      shared.uTerrainBounds.value.copy(chapter.terrain.bounds);
    } else {
      shared.uTerrainBounds.value.set(-1e5, -1e5, 2e5, 2e5);
    }
    audio.setUnderwater(0);
    chapter.scene.add(sky.mesh, ember.group, ember.trail);
    lights.attach(chapter.scene);
    this.people?.enter(chapter.scene, this.index);
    walker.setPath(chapter.path, 0);
    if (chapter.startYaw !== undefined) walker.yaw = chapter.startYaw;
    walker.autoTarget = null;
    if (run) chapter.enter();
  }

  private pickAt(x: number, y: number) {
    if (!this.chapter || !this.begun || this.transition) return null;
    const ndc = new Vector2((x / innerWidth) * 2 - 1, -(y / innerHeight) * 2 + 1);
    this.raycaster.setFromCamera(ndc, this.stage.camera);
    return this.chapter.pick(this.raycaster.ray);
  }

  private tap(x: number, y: number) {
    const action = this.pickAt(x, y);
    action?.();
  }

  private refreshMenu() {
    this.ctx.ui.setChapters(
      CHAPTERS.map((c, i) => ({
        numeral: c.numeral,
        name: c.name,
        reached: i <= this.progress.reached,
        go: () => this.goTo(i),
      })),
    );
  }

  private goTo(index: number) {
    if (this.transition || index === this.index) return;
    this.next = this.build(index);
    this.transition = { t: 0, phase: 'out', target: index };
    void this.ctx.audio.sfx('fog-swirl', { volume: 0.7 });
  }

  private frame(dt: number) {
    const { renderer, camera } = this.stage;
    const { walker, ember, glow, lights, sky, audio, post, ui } = this.ctx;
    this.time += dt;
    shared.uHlTime.value = this.time;

    if (this.begun) {
      walker.update(dt);
      if (!this.moved && walker.pace > 0.3) {
        this.moved = true;
        setTimeout(() => ui.hideHint(), 2500);
      }
      ui.setWalking(walker.auto);
    } else {
      // Before the walk: stand at the entrance, breathing.
      walker.update(0);
    }
    this.chapter?.update(dt, this.time);

    // Chapter's end: fade into the fog, swap, fade back.
    if (this.chapter && !this.transition && this.begun && this.chapter.finished() && this.index < CHAPTERS.length - 1) {
      this.goTo(this.index + 1);
    }
    if (this.transition) this.stepTransition(dt);

    if (this.begun) glow.moving.push(...this.people.update(dt, walker.position));
    const forward = new Vector3(0, 0, -1).applyQuaternion(camera.quaternion);
    ember.update(dt, renderer.domElement.height / (2 * Math.tan((camera.fov * Math.PI) / 360)), camera.position);
    lights.update(dt, camera.position, forward);
    glow.render(renderer);
    sky.update(camera.position);
    audio.update(camera);
    if (this.chapter) post.render(this.chapter.scene, camera, this.time);
  }

  private stepTransition(dt: number) {
    const tr = this.transition as NonNullable<typeof this.transition>;
    const { post, audio, ui } = this.ctx;
    const OUT = 2.6;
    const IN = 3.2;
    tr.t += dt;
    if (tr.phase === 'out') {
      const k = Math.min(1, tr.t / OUT);
      post.fade = k * k * (3 - 2 * k);
      post.fadeColor.copy(shared.uFogColor.value).multiplyScalar(1.6).add(new Color(0.02, 0.015, 0.02));
      if (k >= 1 && this.next) {
        const next = this.next;
        this.next = null;
        void next.then(async (chapter) => {
          const old = this.chapter;
          this.chapter = chapter;
          this.index = tr.target;
          this.enter(chapter, true);
          await this.stage.renderer.compileAsync(chapter.scene, this.stage.camera);
          old?.dispose();
          tr.phase = 'in';
          tr.t = 0;
          void audio.setScene(chapter.music, chapter.ambience, 5);
          const info = CHAPTERS[this.index];
          if (info) ui.chapterCard(info.numeral, info.name, info.subtitle);
          if (this.index > this.progress.reached) {
            this.progress.reached = this.index;
            void this.portal.save.personal.set('progress', this.progress).catch(() => undefined);
          }
          this.refreshMenu();
        });
      }
    } else {
      const k = Math.min(1, tr.t / IN);
      post.fade = 1 - k * k * (3 - 2 * k);
      if (k >= 1) {
        post.fade = 0;
        this.transition = null;
      }
    }
  }
}
