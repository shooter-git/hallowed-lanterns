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

export interface Manifest {
  motif?: { key: string; notes: string[]; rhythm?: string };
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
  private music: Loop | null = null;
  private ambience: Loop | null = null;
  private musicKey = '';
  private ambienceKey = '';
  private readonly sends = new Map<'music' | 'ambience' | 'sfx' | 'ui', AudioNode>();
  private active = 0;
  private started = false;

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

  /** Builds the routing; call after the first tap. */
  start() {
    if (this.started) return;
    this.started = true;
    const ctx = this.ctx;
    // Music, ambience and effects each go through an underwater filter, then into their groups.
    for (const name of ['music', 'ambience', 'sfx'] as const) {
      const g = ctx.createGain();
      const f = ctx.createBiquadFilter();
      f.type = 'lowpass';
      f.frequency.value = 20000;
      g.connect(f).connect(this.portal.audio.bus(name as BusName));
      this.sends.set(name, g);
      this.filters.push(f);
    }
    this.sends.set('ui', this.portal.audio.bus('ui'));
  }

  private readonly filters: BiquadFilterNode[] = [];

  /** 0 = in air, 1 = deep underwater (muffled, far away). */
  setUnderwater(amount: number) {
    const f = 20000 * (1 - amount) + 520 * amount;
    const now = this.started ? this.ctx.currentTime : 0;
    for (const filt of this.filters) filt.frequency.setTargetAtTime(f, now, 0.4);
  }

  private file(path: string): Promise<AudioBuffer | null> {
    let p = this.buffers.get(path);
    if (!p) {
      p = (async () => {
        try {
          const res = await fetch(new URL(path, base));
          if (!res.ok) return null;
          return await this.ctx.decodeAudioData(await res.arrayBuffer());
        } catch {
          return null;
        }
      })();
      this.buffers.set(path, p);
    }
    return p;
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

  /** Crossfades to a chapter's music and ambience. */
  async setScene(musicKey: string | null, ambienceKey: string | null, fade = 4) {
    if (!this.started || !this.manifest) return;
    if ((musicKey ?? '') !== this.musicKey) {
      this.musicKey = musicKey ?? '';
      this.music?.stop(fade);
      this.music = null;
      const info = musicKey ? this.manifest.music[musicKey] : undefined;
      if (info) {
        const buf = await this.file(info.file);
        if (buf && this.musicKey === musicKey)
          this.music = new Loop(this.ctx, buf, info.loopSeconds ?? buf.duration, info.tailSeconds ?? 0, this.sends.get('music') as AudioNode, 1, fade);
      }
    }
    if ((ambienceKey ?? '') !== this.ambienceKey) {
      this.ambienceKey = ambienceKey ?? '';
      this.ambience?.stop(fade);
      this.ambience = null;
      const info = ambienceKey ? this.manifest.ambience[ambienceKey] : undefined;
      if (info) {
        const buf = await this.file(info.file);
        if (buf && this.ambienceKey === ambienceKey)
          this.ambience = new Loop(this.ctx, buf, info.loopSeconds ?? buf.duration, info.tailSeconds ?? 0, this.sends.get('ambience') as AudioNode, 1, fade);
      }
    }
  }

  /** Music volume (e.g. lower while sitting and listening to the crickets). */
  musicLevel(level: number, seconds = 2) {
    if (!this.music) return;
    this.music.out.gain.setTargetAtTime(level, this.ctx.currentTime, seconds / 3);
  }

  /** Plays a one-shot music cue (a stinger, the finale) over the current music. */
  async cue(key: string, volume = 1) {
    if (!this.started || !this.manifest) return;
    const info = this.manifest.music[key];
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
    options: { volume?: number; rate?: number; at?: Vector3; spread?: number; send?: 'sfx' | 'ui' } = {},
  ) {
    if (!this.started) return;
    const list = this.manifest?.sfx[key];
    if (!list?.length) return;
    if (this.active >= this.maxVoices - (this.music?.voices ?? 0) - (this.ambience?.voices ?? 0)) return;
    const path = list[Math.floor(Math.random() * list.length)] as string;
    const buf = await this.file(path);
    if (!buf) return;
    this.playBuffer(buf, options);
  }

  /** Plays one of a list's variations by index (e.g. the xylophone's notes). */
  async sfxIndex(key: string, index: number, options: { volume?: number; at?: Vector3 } = {}) {
    if (!this.started) return;
    const path = this.manifest?.sfx[key]?.[index];
    if (!path) return;
    const buf = await this.file(path);
    if (buf) this.playBuffer(buf, options);
  }

  private playBuffer(
    buf: AudioBuffer,
    options: { volume?: number; rate?: number; at?: Vector3; send?: 'sfx' | 'ui' | 'music' },
  ) {
    const ctx = this.ctx;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.playbackRate.value = options.rate ?? 1;
    const g = ctx.createGain();
    g.gain.value = options.volume ?? 1;
    let node: AudioNode = src.connect(g);
    if (options.at) {
      const p = ctx.createPanner();
      p.panningModel = 'HRTF';
      p.distanceModel = 'inverse';
      p.refDistance = 1.5;
      p.rolloffFactor = 1.1;
      p.maxDistance = 60;
      setPannerPosition(p, options.at);
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
