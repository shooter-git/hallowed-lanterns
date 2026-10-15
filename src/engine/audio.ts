import type { BusName, Portal } from '@allthespaces/portal';
import type { Camera, Vector3 } from 'three';
import { Vector3 as V3 } from 'three';

interface LoopInfo {
  file: string;
  title?: string;
  loopSeconds?: number;
  tailSeconds?: number;
  oneShot?: boolean;
  seconds?: number;
}

/**
 * The settings' sliders run 0-100. The mix as made sits at 80, so there is room to turn up as well as
 * down; the curve is squared, close to how loudness is heard (80 is 0 dB, 100 about +4 dB, 40 -12 dB).
 */
export const SLIDER_DEFAULT = 80;
export const sliderGain = (v: number) => (Math.max(0, Math.min(100, v)) / SLIDER_DEFAULT) ** 2;

export interface Manifest {
  motif?: { key: string; notes: string[]; rhythm?: string; xyloNotes?: string[]; xylo?: number[] };
  music: Record<string, LoopInfo>;
  ambience: Record<string, LoopInfo>;
  sfx: Record<string, string[]>;
}

const base = new URL('./audio/', document.baseURI);

/** One looping track that crossfades into itself, so the seam never clicks. */
class Loop {
  private nextStart = 0;
  private readonly passes: { src: AudioBufferSourceNode; gain: GainNode; end: number }[] = [];
  private stopped = false;
  readonly out: GainNode;

  constructor(
    private readonly ctx: AudioContext,
    private readonly buffer: AudioBuffer,
    private readonly loopSeconds: number,
    private readonly tail: number,
    destination: AudioNode,
    volume: number,
    fadeIn: number,
  ) {
    this.out = ctx.createGain();
    this.out.gain.value = 0;
    this.out.gain.setTargetAtTime(volume, ctx.currentTime, Math.max(0.01, fadeIn / 3));
    this.out.connect(destination);
    this.nextStart = ctx.currentTime + 0.05;
    this.schedule(true);
  }

  private schedule(first: boolean) {
    const ctx = this.ctx;
    const at = Math.max(this.nextStart, ctx.currentTime + 0.02);
    const src = ctx.createBufferSource();
    src.buffer = this.buffer;
    const gain = ctx.createGain();
    src.connect(gain).connect(this.out);
    const loop = Math.min(this.loopSeconds, this.buffer.duration - this.tail);
    if (first) gain.gain.setValueAtTime(1, at);
    else {
      gain.gain.setValueAtTime(0, at);
      gain.gain.linearRampToValueAtTime(1, at + this.tail);
    }
    gain.gain.setValueAtTime(1, at + loop);
    gain.gain.linearRampToValueAtTime(0, at + loop + this.tail);
    src.start(at);
    src.stop(at + loop + this.tail + 0.05);
    this.passes.push({ src, gain, end: at + loop + this.tail + 0.1 });
    this.nextStart = at + loop;
  }

  update() {
    if (this.stopped) return;
    const now = this.ctx.currentTime;
    if (now > this.nextStart - 1.5) this.schedule(false);
    while (this.passes.length && (this.passes[0] as { end: number }).end < now) this.passes.shift();
  }

  get voices() {
    return this.passes.length;
  }

  stop(fade: number) {
    this.stopped = true;
    const now = this.ctx.currentTime;
    this.out.gain.cancelScheduledValues(now);
    this.out.gain.setValueAtTime(this.out.gain.value, now);
    this.out.gain.linearRampToValueAtTime(0, now + fade);
    for (const p of this.passes) {
      try {
        p.src.stop(now + fade + 0.1);
      } catch {
        // Already stopped.
      }
    }
    setTimeout(() => this.out.disconnect(), (fade + 0.3) * 1000);
  }
}

/**
 * The soundtrack and the world's sounds. Music and ambience crossfade between chapters; effects
 * can sit at a place in the world (heard through headphones from where they are); everything runs
 * through the app's sound groups, via a filter that closes when we're underwater.
 */
export class AudioDirector {
  manifest: Manifest | null = null;
  /** Most sounds at once (the budget is 32 on mid-range devices; keep some room). */
  maxVoices = 26;
  private readonly buffers = new Map<string, Promise<AudioBuffer | null>>();
  /** The variation each sound last played, so the next one differs. */
  private readonly lastPick = new Map<string, number>();
  private music: Loop | null = null;
  private ambience: Loop | null = null;
  private musicKey = '';
  private ambienceKey = '';
  private readonly sends = new Map<'music' | 'ambience' | 'sfx' | 'ui', AudioNode>();
  private active = 0;
  private started = false;
  /** The listener's own levels (the settings): 1 is the mix as made. */
  private readonly levels = { music: 1, sounds: 1 };

  constructor(private readonly portal: Portal) {}

  get ctx(): AudioContext {
    return this.portal.audio.context;
  }

  async load() {
    try {
      const res = await fetch(new URL('manifest.json', base));
      if (res.ok) this.manifest = (await res.json()) as Manifest;
    } catch {
      this.manifest = null;
    }
  }

  private manifestLoad: Promise<Manifest | null> | null = null;
  private manifestTried = 0;

  /** The manifest, fetched again (at most every few seconds) if it couldn't be at first. */
  private ensureManifest(): Promise<Manifest | null> {
    if (this.manifest) return Promise.resolve(this.manifest);
    if (!this.manifestLoad && performance.now() - this.manifestTried > 5000) {
      this.manifestTried = performance.now();
      this.manifestLoad = this.load().then(() => {
        this.manifestLoad = null;
        return this.manifest;
      });
    }
    return this.manifestLoad ?? Promise.resolve(null);
  }

  /** Builds the routing; call after the first tap. */
  start() {
    if (this.started) return;
    this.started = true;
    const ctx = this.ctx;
    // Music, ambience and effects each go through an underwater filter, then into their groups.
    for (const name of ['music', 'ambience', 'sfx'] as const) {
      const g = ctx.createGain();
      g.gain.value = name === 'music' ? this.levels.music : this.levels.sounds;
      const f = ctx.createBiquadFilter();
      f.type = 'lowpass';
      f.frequency.value = 20000;
      g.connect(f).connect(this.portal.audio.bus(name as BusName));
      this.sends.set(name, g);
      this.filters.push(f);
    }
    this.sends.set('ui', this.portal.audio.bus('ui'));
    // The night's space: sounds placed in the world send some of themselves here, so they sit out
    // among the trees instead of in your ears. It returns into the effects group (and so is
    // muffled underwater too).
    const hall = ctx.createConvolver();
    hall.buffer = hallImpulse(ctx);
    const back = ctx.createGain();
    back.gain.value = 0.55;
    this.reverb = ctx.createGain();
    this.reverb.connect(hall).connect(back).connect(this.sends.get('sfx') as AudioNode);
    // A phone suspends a page's sound when it's locked, another app takes over or a call comes in, and
    // it stays silent until the page starts it again, which browsers allow only from a tap. So any tap,
    // click or key starts it again, and so does coming back to the page (where that's allowed).
    const wake = () => {
      if (ctx.state !== 'running') void ctx.resume().catch(() => undefined);
    };
    for (const type of ['pointerdown', 'touchend', 'click', 'keydown'])
      window.addEventListener(type, wake, { capture: true, passive: true });
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') wake();
    });
  }

  private reverb: GainNode | null = null;

  private readonly filters: BiquadFilterNode[] = [];

  /**
   * 0 = in air, 1 = deep underwater: the world's sounds go muffled and far away. The music is
   * left alone unless `music` (the Deep's own music is written for being underwater).
   */
  setUnderwater(amount: number, music = false) {
    const f = 20000 * (1 - amount) + 520 * amount;
    const now = this.started ? this.ctx.currentTime : 0;
    this.filters.forEach((filt, i) => {
      if (i === 0 && !music) filt.frequency.setTargetAtTime(20000, now, 0.4);
      else filt.frequency.setTargetAtTime(f, now, 0.4);
    });
  }

  /**
   * A recording, fetched and decoded once and kept. One that fails (the connection gone for a moment,
   * a server's hiccup) isn't kept: the next time it's wanted, it's fetched again.
   */
  private file(path: string): Promise<AudioBuffer | null> {
    let p = this.buffers.get(path);
    if (!p) {
      const load: Promise<AudioBuffer | null> = this.fetchBuffer(path).then((buf) => {
        if (!buf && this.buffers.get(path) === load) this.buffers.delete(path);
        return buf;
      });
      this.buffers.set(path, load);
      p = load;
    }
    return p;
  }

  private async fetchBuffer(path: string): Promise<AudioBuffer | null> {
    try {
      const res = await fetch(new URL(path, base));
      if (!res.ok) return null;
      return await this.ctx.decodeAudioData(await res.arrayBuffer());
    } catch {
      return null;
    }
  }

  /**
   * A chapter's music or night sounds, fetched again while it fails and is still wanted (after 2, 4 and
   * 8 seconds, then every 30): when the connection comes back, so does the sound.
   */
  private async whileWanted(path: string, wanted: () => boolean): Promise<AudioBuffer | null> {
    for (let wait = 2; ; wait = wait < 8 ? wait * 2 : 30) {
      const buf = await this.file(path);
      if (buf || !wanted()) return buf;
      await new Promise((r) => setTimeout(r, wait * 1000));
      if (!wanted()) return null;
    }
  }

  /** Starts fetching and decoding what a chapter needs. */
  preload(chapter: string, sfx: string[] = []) {
    const m = this.manifest;
    if (!m) return;
    const music = m.music[chapter];
    const amb = m.ambience[chapter];
    if (music) void this.file(music.file);
    if (amb) void this.file(amb.file);
    for (const key of sfx) for (const f of m.sfx[key] ?? []) void this.file(f);
  }

  /** The music playing now (its key in the manifest), or '' for none. */
  get currentMusic(): string {
    return this.musicKey;
  }

  /**
   * Crossfades to a chapter's music and ambience. Each comes in as soon as it's loaded, on its own; one
   * that fails to load is tried again for as long as it's still the one wanted.
   */
  async setScene(musicKey: string | null, ambienceKey: string | null, fade = 4) {
    if (!this.started) return;
    const m = this.manifest ?? (await this.ensureManifest());
    if (!m) return;
    const music = async () => {
      const key = musicKey ?? '';
      if (key === this.musicKey) return;
      this.musicKey = key;
      this.music?.stop(fade);
      this.music = null;
      const info = key ? m.music[key] : undefined;
      if (!info) return;
      const buf = await this.whileWanted(info.file, () => this.musicKey === key);
      if (buf && this.musicKey === key)
        this.music = new Loop(this.ctx, buf, info.loopSeconds ?? buf.duration, info.tailSeconds ?? 0, this.sends.get('music') as AudioNode, 1, fade);
    };
    const ambience = async () => {
      const key = ambienceKey ?? '';
      if (key === this.ambienceKey) return;
      this.ambienceKey = key;
      this.ambience?.stop(fade);
      this.ambience = null;
      const info = key ? m.ambience[key] : undefined;
      if (!info) return;
      const buf = await this.whileWanted(info.file, () => this.ambienceKey === key);
      if (buf && this.ambienceKey === key)
        this.ambience = new Loop(this.ctx, buf, info.loopSeconds ?? buf.duration, info.tailSeconds ?? 0, this.sends.get('ambience') as AudioNode, 1, fade);
    };
    await Promise.all([music(), ambience()]);
  }

  /**
   * The listener's level for the music, or for the sounds of the world (its ambience and every effect:
   * wind, footsteps, creatures, chimes), relative to the mix as made (1). The interface's taps stay as
   * they are.
   */
  setLevel(group: 'music' | 'sounds', gain: number) {
    this.levels[group] = Math.max(0, gain);
    if (!this.started) return;
    const now = this.ctx.currentTime;
    for (const name of group === 'music' ? (['music'] as const) : (['ambience', 'sfx'] as const))
      (this.sends.get(name) as GainNode).gain.setTargetAtTime(this.levels[group], now, 0.05);
  }

  /** Music volume (e.g. lower while sitting and listening to the crickets). */
  musicLevel(level: number, seconds = 2) {
    if (!this.music) return;
    this.music.out.gain.setTargetAtTime(level, this.ctx.currentTime, seconds / 3);
  }

  /** Plays a one-shot music cue (a stinger, the finale) over the current music. */
  async cue(key: string, volume = 1) {
    if (!this.started) return;
    const info = (this.manifest ?? (await this.ensureManifest()))?.music[key];
    if (!info) return;
    const buf = await this.file(info.file);
    if (!buf) return;
    this.playBuffer(buf, { volume, send: 'music' });
  }

  /**
   * Plays an effect (a random one of its variations). With `at`, it sits at that place in the
   * world and you hear it from there.
   */
  async sfx(
    key: string,
    options: { volume?: number; rate?: number; at?: Vector3; pan?: number; wet?: number; spread?: number; send?: 'sfx' | 'ui' | 'music' } = {},
  ) {
    if (!this.started) return;
    const list = (this.manifest ?? (await this.ensureManifest()))?.sfx[key];
    if (!list?.length) return;
    if (this.active >= this.maxVoices - (this.music?.voices ?? 0) - (this.ambience?.voices ?? 0)) return;
    // Never the same variation twice running (two identical footsteps give the game away).
    let pick = Math.floor(Math.random() * list.length);
    if (list.length > 1 && pick === this.lastPick.get(key)) pick = (pick + 1 + Math.floor(Math.random() * (list.length - 1))) % list.length;
    this.lastPick.set(key, pick);
    const path = list[pick] as string;
    const buf = await this.file(path);
    if (!buf) return;
    this.playBuffer(buf, options);
  }

  /** Plays one of a list's variations by index (e.g. the xylophone's notes). */
  async sfxIndex(key: string, index: number, options: { volume?: number; at?: Vector3; wet?: number } = {}) {
    if (!this.started) return;
    const path = (this.manifest ?? (await this.ensureManifest()))?.sfx[key]?.[index];
    if (!path) return;
    const buf = await this.file(path);
    if (buf) this.playBuffer(buf, options);
  }

  private playBuffer(
    buf: AudioBuffer,
    options: { volume?: number; rate?: number; at?: Vector3; pan?: number; wet?: number; send?: 'sfx' | 'ui' | 'music' },
  ) {
    const ctx = this.ctx;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.playbackRate.value = options.rate ?? 1;
    const g = ctx.createGain();
    g.gain.value = options.volume ?? 1;
    let node: AudioNode = src.connect(g);
    // Sounds out in the world take some of the night's space; footsteps and the interface don't.
    const wet = options.wet ?? (options.at && options.send !== 'ui' ? 0.32 : 0);
    if (wet > 0 && this.reverb) {
      const w = ctx.createGain();
      w.gain.value = wet;
      g.connect(w).connect(this.reverb);
    }
    if (options.at) {
      const p = ctx.createPanner();
      p.panningModel = 'HRTF';
      p.distanceModel = 'inverse';
      p.refDistance = 1.5;
      p.rolloffFactor = 1.1;
      p.maxDistance = 60;
      setPannerPosition(p, options.at);
      node = node.connect(p);
    } else if (options.pan) {
      const p = ctx.createStereoPanner();
      p.pan.value = options.pan;
      node = node.connect(p);
    }
    node.connect(this.sends.get(options.send ?? 'sfx') as AudioNode);
    this.active++;
    src.onended = () => {
      this.active--;
      src.disconnect();
    };
    src.start();
  }

  /** Keeps the listener at the camera, facing where it faces. Call once a frame. */
  update(camera: Camera) {
    if (!this.started) return;
    this.music?.update();
    this.ambience?.update();
    const l = this.ctx.listener;
    const p = camera.position;
    const f = new V3(0, 0, -1).applyQuaternion(camera.quaternion);
    const u = new V3(0, 1, 0).applyQuaternion(camera.quaternion);
    const t = this.ctx.currentTime;
    if (l.positionX) {
      l.positionX.setTargetAtTime(p.x, t, 0.02);
      l.positionY.setTargetAtTime(p.y, t, 0.02);
      l.positionZ.setTargetAtTime(p.z, t, 0.02);
      l.forwardX.setTargetAtTime(f.x, t, 0.02);
      l.forwardY.setTargetAtTime(f.y, t, 0.02);
      l.forwardZ.setTargetAtTime(f.z, t, 0.02);
      l.upX.setTargetAtTime(u.x, t, 0.02);
      l.upY.setTargetAtTime(u.y, t, 0.02);
      l.upZ.setTargetAtTime(u.z, t, 0.02);
    } else {
      (l as unknown as { setPosition: (x: number, y: number, z: number) => void }).setPosition(p.x, p.y, p.z);
      (l as unknown as { setOrientation: (...a: number[]) => void }).setOrientation(f.x, f.y, f.z, u.x, u.y, u.z);
    }
  }

  stopAll(fade = 1.5) {
    this.music?.stop(fade);
    this.ambience?.stop(fade);
    this.music = null;
    this.ambience = null;
    this.musicKey = '';
    this.ambienceKey = '';
  }
}

function setPannerPosition(p: PannerNode, at: Vector3) {
  if (p.positionX) {
    p.positionX.value = at.x;
    p.positionY.value = at.y;
    p.positionZ.value = at.z;
  } else {
    (p as unknown as { setPosition: (x: number, y: number, z: number) => void }).setPosition(at.x, at.y, at.z);
  }
}

/**
 * A room for the night, made rather than recorded: a short pre-delay, a few early reflections off
 * the trees, then a dense tail that dies away over about 2.4 s, darker as it goes (the air and
 * the leaves take the highs first).
 */
function hallImpulse(ctx: BaseAudioContext, seconds = 2.4, preDelay = 0.022): AudioBuffer {
  const rate = ctx.sampleRate;
  const n = Math.floor(rate * seconds);
  const ir = ctx.createBuffer(2, n, rate);
  for (let c = 0; c < 2; c++) {
    const d = ir.getChannelData(c);
    let lp = 0;
    for (let i = Math.floor(preDelay * rate); i < n; i++) {
      const t = i / rate - preDelay;
      const k = 0.35 + 0.55 * Math.min(1, t / seconds);
      lp = lp * k + (Math.random() * 2 - 1) * (1 - k);
      d[i] = lp * Math.exp((-6.9 * t) / seconds) * Math.min(1, t / 0.012);
    }
    for (const [ms, gain] of [[9, 0.5], [17, 0.36], [26, 0.3], [38, 0.22], [51, 0.16]] as const) {
      const i = Math.floor((preDelay + ms / 1000 + c * 0.0017) * rate);
      if (i < n) d[i] = (d[i] ?? 0) + gain * (Math.random() < 0.5 ? -1 : 1) * 0.1;
    }
  }
  return ir;
}
