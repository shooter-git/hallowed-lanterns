import type { Portal } from '@allthespaces/portal';
import {
  AdditiveBlending,
  CanvasTexture,
  Color,
  Group,
  Mesh,
  MeshBasicMaterial,
  type Scene,
  SphereGeometry,
  Sprite,
  SpriteMaterial,
  SRGBColorSpace,
  Vector3,
} from 'three';
import type { GlowLight } from './glowfield.ts';
import { heightAt } from './terrain.ts';

type Pose = { c: number; x: number; z: number };

interface Other {
  id: string;
  name: string;
  color: Color;
  chapter: number;
  target: Vector3;
  at: Vector3;
  seen: number;
  group: Group;
  glow: GlowLight;
}

function label(name: string, color: Color): Sprite {
  const c = document.createElement('canvas');
  c.width = 256;
  c.height = 64;
  const g = c.getContext('2d') as CanvasRenderingContext2D;
  g.font = 'italic 30px "Iowan Old Style", Palatino, Georgia, serif';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.shadowColor = `#${color.getHexString()}`;
  g.shadowBlur = 12;
  g.fillStyle = '#fbf3e6';
  g.fillText(name.slice(0, 18), 128, 32);
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  const s = new Sprite(new SpriteMaterial({ map: t, transparent: true, depthWrite: false }));
  s.scale.set(0.9, 0.225, 1);
  s.position.y = 0.42;
  return s;
}

/**
 * The people walking the night with you: each a small lantern-light in their own colour (like
 * the glow bracelets in the photos), with their name, walking where they are. Positions travel
 * about ten times a second and are smoothed. People in other chapters aren't drawn; when someone
 * moves on, you're told where they've gone.
 */
export class People {
  private readonly others = new Map<string, Other>();
  private sendClock = 0;
  private scene: Scene | null = null;
  private chapter = 0;

  constructor(
    private readonly portal: Portal,
    private readonly chapterName: (i: number) => string,
    private readonly say: (text: string) => void,
  ) {
    portal.session.on<Pose>('pose', (p, from) => this.receive(from, p));
    portal.session.onPlayers((players) => {
      const here = new Set(players.map((p) => p.id));
      for (const [id, o] of this.others) {
        if (!here.has(id)) {
          o.group.removeFromParent();
          this.others.delete(id);
        }
      }
    });
  }

  /** The chapter (and its scene) you're in now. */
  enter(scene: Scene, chapter: number) {
    this.scene = scene;
    this.chapter = chapter;
    for (const o of this.others.values()) {
      if (o.chapter === chapter) scene.add(o.group);
      else o.group.removeFromParent();
    }
  }

  private receive(from: string, p: Pose) {
    if (from === this.portal.me.id) return;
    let o = this.others.get(from);
    if (!o) {
      const person = this.portal.session.players.find((x) => x.id === from);
      const color = new Color(person?.color ?? '#ffb060');
      const group = new Group();
      const core = new Mesh(new SphereGeometry(0.07, 12, 8), new MeshBasicMaterial({ color: color.clone().multiplyScalar(5) }));
      const halo = new Sprite(new SpriteMaterial({ color: color.clone().multiplyScalar(1.4), blending: AdditiveBlending, depthWrite: false, transparent: true, opacity: 0.55 }));
      halo.scale.set(0.6, 0.6, 1);
      group.add(core, halo, label(person?.name ?? 'Someone', color));
      o = {
        id: from,
        name: person?.name ?? 'Someone',
        color,
        chapter: p.c,
        target: new Vector3(p.x, 0, p.z),
        at: new Vector3(p.x, 0, p.z),
        seen: 0,
        group,
        glow: { x: p.x, z: p.z, radius: 2.4, color, intensity: 0.5, flicker: 0 },
      };
      this.others.set(from, o);
      if (this.scene && p.c === this.chapter) this.scene.add(group);
    }
    if (p.c !== o.chapter) {
      if (p.c > o.chapter && o.chapter === this.chapter) this.say(`${o.name} has gone on to ${this.chapterName(p.c)}.`);
      o.chapter = p.c;
      if (p.c === this.chapter) {
        this.scene?.add(o.group);
        o.at.set(p.x, 0, p.z);
        this.say(`${o.name} is here with you.`);
      } else o.group.removeFromParent();
    }
    o.target.set(p.x, 0, p.z);
    o.seen = 0;
  }

  /** Sends where you are; smooths everyone else. Returns the glow lights of those nearby. */
  update(dt: number, me: Vector3): GlowLight[] {
    this.sendClock += dt;
    if (this.sendClock > 0.1 && this.portal.session.players.length > 1) {
      this.sendClock = 0;
      this.portal.session.send('pose', { c: this.chapter, x: Math.round(me.x * 100) / 100, z: Math.round(me.z * 100) / 100 });
    }
    const lights: GlowLight[] = [];
    for (const o of this.others.values()) {
      o.seen += dt;
      if (o.chapter !== this.chapter) continue;
      o.at.lerp(o.target, 1 - Math.exp(-dt * 8));
      const bob = Math.sin(performance.now() / 300 + o.id.length) * 0.03;
      o.group.position.set(o.at.x, heightAt(o.at.x, o.at.z) + 1.25 + bob, o.at.z);
      o.glow.x = o.at.x;
      o.glow.z = o.at.z;
      lights.push(o.glow);
    }
    return lights;
  }
}
