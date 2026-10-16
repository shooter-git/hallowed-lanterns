import type { Portal } from '@allthespaces/portal';
import { createStage, type Stage } from '@allthespaces/portal/three';
import { Color, NoToneMapping, type PerspectiveCamera, Raycaster, Vector2, Vector3 } from 'three';
import { CHAPTERS } from '../chapters/index.ts';
import type { Chapter, ChapterContext, SurfaceKind, Tier } from '../chapters/types.ts';
import { AudioDirector, SOUND_DEFAULTS, sliderGain } from './audio.ts';
import { buildCarvingAtlas } from './carvings.ts';
import { Ember } from './ember.ts';
import { Glimmers } from './glimmers.ts';
import { GlowField } from './glowfield.ts';
import { LightPool } from './lights.ts';
import { People } from './people.ts';
import { Post } from './post.ts';
import { Walker } from './rig.ts';
import { shared } from './shared.ts';
import { Sky } from './sky.ts';
import { setCurrentTerrain } from './terrain.ts';
import { bakeSurface, DRY_GRASS, GRAVEL, LAWN, LEAF_LITTER, SNOW, type SurfaceMaps } from './texgen.ts';
import { type SoundSettings, UI } from './ui.ts';

type Progress = {
  /** Furthest chapter reached (index). */
  reached: number;
};

/**
 * Runs the night: the renderer and its finishing, the walk, the Ember, sound, the chapters in
 * order and the fog-soft transitions between them.
 */
/** The passage into a chapter: in its key, and into the last one, the farewell. */
/** Seconds from a passage's start to its downbeat, where the next chapter (and its music) begins. */
const PASSAGE_DOWNBEAT = 2.6;

function passageFor(index: number) {
  return index === CHAPTERS.length - 1 ? 'passage-final' : `passage-${CHAPTERS[index]?.key ?? 'd'}`;
}

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
  private readonly sunPoint = new Vector3();
  private readonly white = new Color(1, 1, 1);
  private readonly surfaces = new Map<SurfaceKind, SurfaceMaps>();
  private moved = false;
  private people!: People;
  /** The current chapter's glimmers (made as it's entered, let go when the next one is). */
  private glimmers: Glimmers | null = null;

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

    const post = new Post(renderer, { samples: tier === 'low' ? 0 : 4, levels: tier === 'low' ? 5 : 6, sharpen: tier === 'high' ? 0.5 : 0, shafts: tier !== 'low' });
    const glow = new GlowField(tier === 'low' ? 256 : 512);
    const lights = new LightPool(tier === 'low' ? 2 : tier === 'mid' ? 4 : 6);
    const sky = new Sky();
    sky.tier = tier;
    const ember = new Ember();
    const ui = new UI(portal.viewport.touch);
    const walker = new Walker(portal, camera, renderer.domElement);
    const audio = new AudioDirector(portal);
    portal.input.define({ move: 'stick' });
    // No joystick over the title: it appears when the walk begins.
    if (portal.viewport.touch) portal.input.showTouchControls(false);

    portal.progress(0.15, 'Carving faces');
    ui.loading(0.15);
    const atlas = buildCarvingAtlas();
    await audio.load();
    try {
      const saved = await portal.save.personal.get<Progress>('progress');
      if (saved) this.progress = saved;
    } catch {
      // Nothing saved yet.
    }
    // The listener's sound levels (the chapters menu's settings), kept with their progress.
    let sound: SoundSettings = { ...SOUND_DEFAULTS };
    try {
      const saved = await portal.save.personal.get<SoundSettings>('sound');
      if (saved && Number.isFinite(saved.music) && Number.isFinite(saved.sounds)) sound = saved;
    } catch {
      // Nothing saved yet: where the sliders start.
    }
    const applySound = (v: SoundSettings) => {
      audio.setLevel('music', sliderGain(v.music));
      audio.setLevel('sounds', sliderGain(v.sounds));
    };
    applySound(sound);
    ui.setSound(sound, (v, done) => {
      applySound(v);
      if (done) void portal.save.personal.set('sound', v).catch(() => undefined);
    });

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
    ui.loading(0.35);
    this.chapter = await this.build(0);
    // Set the scene (light, sky, fog) now, so the title sits over the real place.
    this.enter(this.chapter, true);
    if (this.chapter.titleView) {
      const view = this.chapter.titleView;
      // Half the width of the view, as an angle.
      const half = Math.atan(Math.tan((camera.fov * Math.PI) / 360) * camera.aspect);
      walker.yaw = view.leftOf === undefined ? view.yaw : Math.min(view.yaw, view.leftOf - half - 0.03);
      walker.pitch = view.pitch;
    }
    portal.progress(0.75, 'Rolling in the fog');
    ui.loading(0.75);
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
        if ((e.target as HTMLElement)?.closest?.('button, input')) return;
        this.tap(innerWidth / 2, innerHeight / 2);
      }
    });
    // Footsteps: left, right, left… each a touch to its side, and never quite the same.
    let foot = 1;
    walker.onStep = () => {
      if (!this.chapter) return;
      foot = -foot;
      void audio.sfx(this.chapter.steps, { volume: 0.24, rate: 0.96 + Math.random() * 0.08, pan: foot * 0.14, send: 'sfx' });
    };
    ui.walkButton.addEventListener('click', () => {
      walker.auto = !walker.auto;
      ui.setWalking(walker.auto);
      // A soft tick to start walking, a touch lower to stop.
      void audio.sfx('ui-tap', { send: 'ui', volume: 0.4, rate: walker.auto ? 1 : 0.9 });
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
    ui.loading(1);
    portal.ready();
    // Let the world draw itself a few times behind the title's cover (shaders compiled, the
    // evening's light settled) before it's seen: no flashes while it wakes.
    for (let i = 0; i < 4; i++) await new Promise((r) => requestAnimationFrame(r));
    await new Promise((r) => setTimeout(r, 250));

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
        ui.dropTitle();
        this.begin();
        const at = Number(q.get('at') ?? 0);
        if (at > 0) walker.setPath(this.chapter.path, at);
        return;
      }
    }

    // The title theme plays over the title: straight away if sound may already play, otherwise
    // from the first tap (made inside the tap itself, so every browser lets it start).
    await ui.showTitle({
      soundReady: portal.audio.context.state === 'running',
      onSound: () => {
        void portal.audio.context.resume();
        this.ctx.audio.start();
        void this.ctx.audio.setScene('title', null, 1.5);
        // the passage that carries the title into the walk, ready before "Begin" is tapped
        this.ctx.audio.preload('', [passageFor(this.index)]);
      },
      onBegin: () => void portal.audio.context.resume(),
    });
    this.begin();
  }

  private begin() {
    const { ui, audio, walker, portal } = this.ctx;
    if (portal.viewport.touch) portal.input.showTouchControls(true);
    audio.start();
    this.begun = true;
    // From the title theme into the walk the way every chapter is entered: the passage into the first chapter
    // swells over the title (which steps back under it) and resolves into the chapter's key, and the chapter's
    // music begins on that downbeat; the night's sounds come in at once.
    const music = this.chapter?.music ?? null;
    const ambience = this.chapter?.ambience ?? null;
    if (audio.currentMusic === 'title' && music) {
      void audio.setScene('title', ambience, 3);
      audio.musicLevel(0.35, 2.4);
      void audio
        .sfx(passageFor(this.index), { volume: 0.7, send: 'music' })
        .then(() => setTimeout(() => void audio.setScene(music, ambience, 2.5), PASSAGE_DOWNBEAT * 1000));
    } else {
      void audio.setScene(music, ambience, 3);
    }
    ui.showControls();
    // From the view behind the title round to where the walk begins (at once, for reduced motion).
    if (this.chapter?.titleView) walker.glideTo(this.chapter.startYaw ?? walker.yaw, 0.04, this.ctx.reducedMotion ? 0.01 : 4.5);
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
    this.glimmers?.dispose();
    this.glimmers = null;
    if (chapter.glimmers) {
      const g = chapter.glimmers;
      this.glimmers = new Glimmers(this.ctx.tier === 'low' ? { ...g, count: Math.ceil(g.count / 2) } : g);
      chapter.scene.add(this.glimmers.points);
    }
    lights.attach(chapter.scene);
    this.people?.enter(chapter.scene, this.index);
    walker.seated = false;
    walker.setPath(chapter.path, 0);
    if (chapter.startYaw !== undefined) walker.yaw = chapter.startYaw;
    walker.autoTarget = null;
    // The passage on to the next chapter, ready before it's needed (it lands on a beat).
    if (CHAPTERS[this.index + 1]) audio.preload('', [passageFor(this.index + 1)]);
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
    // Whatever the chapter you're leaving was offering goes with it.
    this.ctx.ui.clearOffers();
    // The passage: a bar that swells to the moment the next chapter appears, in its key (into the
    // last chapter, a farewell of its own). It's music, so it plays with the music, clear of the
    // Deep's underwater muffling. The music you're leaving steps back to let it through.
    const info = CHAPTERS[index];
    if (info) void this.ctx.audio.sfx(passageFor(index), { volume: 0.7, send: 'music' });
    this.ctx.audio.musicLevel(0.35, 2.4);
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
    const pixelScale = renderer.domElement.height / (2 * Math.tan((camera.fov * Math.PI) / 360));
    ember.update(dt, pixelScale, camera.position);
    this.glimmers?.update(pixelScale);
    lights.update(dt, camera.position, forward);
    glow.render(renderer);
    sky.update(camera.position);
    this.aimShafts(camera, forward);
    audio.update(camera);
    if (this.chapter) post.render(this.chapter.scene, camera, this.time);
  }

  /** Where the low sun is on the screen, and how strongly its shafts show (none once it's set). */
  private aimShafts(camera: PerspectiveCamera, forward: Vector3) {
    const { sky, post } = this.ctx;
    const s = sky.state;
    const facing = forward.dot(s.sunDir);
    camera.updateMatrixWorld();
    const p = this.sunPoint.copy(s.sunDir).multiplyScalar(100).add(camera.position).project(camera);
    post.sun.screen.set(p.x * 0.5 + 0.5, p.y * 0.5 + 0.5);
    // Fades as the sun leaves the view (it can be a little way off the edge and still shine in).
    const off = Math.max(Math.abs(p.x), Math.abs(p.y));
    const inView = facing > 0 ? 1 - Math.min(1, Math.max(0, (off - 1.1) / 0.8)) : 0;
    const up = Math.min(1, Math.max(0, s.sunDir.y * 12 + 1));
    post.sun.strength = Math.min(1, s.sunGlow) * inView * up * Math.min(1, facing * 3) * 0.6;
    // Half-way to white: the sky the shafts gather is already the sun's colour.
    post.sun.color.copy(s.sunColor).lerp(this.white, 0.5);
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
          ui.clearOffers();
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
