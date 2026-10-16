import {
  Color,
  HemisphereLight,
  InstancedMesh,
  Matrix4,
  MeshBasicMaterial,
  type Ray,
  Scene,
  SphereGeometry,
  Vector2,
  Vector3,
} from 'three';
import { CARVE } from '../engine/carvings.ts';
import { FogBank } from '../engine/fogbank.ts';
import type { GlowLight } from '../engine/glowfield.ts';
import { type Bounds, ground, GroundMask } from '../engine/ground.ts';
import type { LightSource } from '../engine/lights.ts';
import { defaultGrade, type Grade, lerpGrade } from '../engine/post.ts';
import { clearOf, PUMPKIN_ORANGE, PumpkinField, type PumpkinSpec } from '../engine/pumpkins.ts';
import { Path } from '../engine/rig.ts';
import { aroundPath, Terrain } from '../engine/terrain.ts';
import { hallow, shared } from '../engine/shared.ts';
import { lerpSky, skyState, treeLine } from '../engine/sky.ts';
import { woodland } from '../engine/canopy.ts';
import { forest, lineThePath } from '../engine/trees.ts';
import { well } from '../scenes/well.ts';
import type { Chapter, ChapterContext, TapAction } from './types.ts';

/**
 * II. The Candle Grove — blue hour. Carved pumpkins hang high in the trees (candles, stars, moons
 * and owls cut through their skins), and red-lit fog rolls along the path at your feet. The Ember
 * plays hide and seek: it hides inside a pumpkin three times, and you find it.
 */

function rng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export async function build(ctx: ChapterContext): Promise<Chapter> {
  const { tier } = ctx;
  const rnd = rng(1022);
  const scene = new Scene();
  const bounds: Bounds = [-40, -90, 80, 105];

  // The magical well, just off the path on the bend, where the grove's red fog comes from. The
  // woods open round it into a little clearing, with a gap in the canopy above.
  const WELL = new Vector3(-1.2, 0, -20.5);
  const path = new Path(
    [
      [0, 8],
      [0, -2],
      [2.5, -14],
      [1, -27],
      [-3.5, -39],
      [-2, -51],
      [2.5, -62],
      [2, -74],
    ],
    3.2,
  );
  const terrain = new Terrain(bounds, aroundPath(path, { profile: (s) => 0.9 * Math.sin(s / 13) + 0.45 * Math.sin(s / 6.2 + 1.2) - 0.012 * s, bank: 0.07, rough: 0.7, seed: 19 }));

  // Ground: a packed gravel-and-dirt path through leaf litter.
  const mask = new GroundMask(bounds, 4);
  const line: [number, number][] = path.points.filter((_, i) => i % 4 === 0).map((p) => [p.x, p.y]);
  mask.stroke(line, 3.6, 'r', 0.85);
  // Thick fog along the path, as in the video, with pools beside it.
  mask.stroke(line, 7, 'g', 0.95);
  for (let i = 0; i < 26; i++) {
    const p = path.at(rnd() * path.length);
    mask.blob(p.x + (rnd() - 0.5) * 12, p.y + (rnd() - 0.5) * 6, 2 + rnd() * 4, 'g', 0.6);
  }
  mask.soften(4);
  const floor = ground({
    mask,
    a: ctx.surface('gravel'),
    aScale: 1.6,
    b: ctx.surface('leaves'),
    bScale: 2.4,
    tone: 0.7,
  });
  scene.add(floor);

  // The woods.
  // Dense woods: trees right at the path's edge, bare trunks behind, a closed canopy overhead.
  const byWell = (t: { x: number; z: number }) => Math.hypot(t.x - WELL.x, t.z - WELL.z) > 4.6;
  const trees = lineThePath(path.points, 3.4, { spacing: tier === 'low' ? 4.5 : 3.4, depth: 1, seed: 7 }).filter(byWell);
  const back = lineThePath(path.points, 6.5, { spacing: tier === 'low' ? 5 : 3.6, depth: tier === 'low' ? 2 : 3, seed: 8 }).filter(byWell);
  const woods = forest(
    [
      { species: 'tall', at: trees.filter((_, i) => i % 2 === 0) },
      { species: 'young', at: trees.filter((_, i) => i % 2 === 1) },
      { species: 'pole', at: back },
    ],
    { leafTint: new Color(0.42, 0.5, 0.4) },
  );
  scene.add(woods.group);
  const canopy = woodland(path, { canopy: [5.5, 10], reach: 10, skyGap: 0.55, density: tier === 'low' ? 1.4 : 2.4, wallFrom: 3.4, wallTo: 13, wallHeight: 5, wallDensity: tier === 'low' ? 3 : 5, tint: new Color(0.42, 0.5, 0.42), seed: 11, clear: (x, z, y) => Math.hypot(x - WELL.x, z - WELL.z) < 4.4 && y < 8 });
  scene.add(canopy.mesh);
  scene.add(treeLine({ radius: 120, height: 18, color: new Color(0.006, 0.008, 0.02), under: new Color(0.04, 0.02, 0.02) }));

  // The lanterns: hanging high in the branches on long strings, thickest over the path.
  const specs: PumpkinSpec[] = [];
  const count = tier === 'low' ? 300 : tier === 'mid' ? 680 : 860;
  const pick = () => {
    const r = rnd();
    if (r < 0.62) return CARVE.candles[Math.floor(rnd() * CARVE.candles.length)] as number;
    if (r < 0.84) return CARVE.stars[Math.floor(rnd() * CARVE.stars.length)] as number;
    return CARVE.creatures[Math.floor(rnd() * CARVE.creatures.length)] as number;
  };
  const tmp = new Vector2();
  const tan = new Vector2();
  for (let i = 0; i < count; i++) {
    // Most over and beside the path, the rest deeper in the trees, at every height up to the canopy;
    // never into a lantern already hung there (a few tries, else one fewer).
    let s = 0;
    let x = 0;
    let y = 0;
    let z = 0;
    let w = 0;
    let h = 0;
    let room = false;
    for (let t = 0; t < 8 && !room; t++) {
      s = rnd() * path.length;
      path.at(s, tmp, tan);
      const off = (rnd() - 0.5) * 2 * (rnd() < 0.6 ? 3.6 : 9.5);
      x = tmp.x - tan.y * off;
      z = tmp.y + tan.x * off;
      y = 2.0 + rnd() * rnd() * 5.5 + Math.abs(off) * 0.08;
      w = 0.13 + rnd() * rnd() * 0.13;
      h = w * (1.05 + rnd() * 0.35);
      room = clearOf(specs, { position: new Vector3(x, y, z), size: new Vector3(w, h, w), hang: 1 }, 0.03);
    }
    if (!room) continue;
    // Face back down the path, toward the people coming along it.
    const from = path.at(Math.max(0, s - 7 - rnd() * 4));
    const yaw = Math.atan2(from.x - x, from.y - z) + (rnd() - 0.5) * 0.6;
    specs.push({
      position: new Vector3(x, y, z),
      size: new Vector3(w, h, w),
      yaw,
      tilt: (rnd() - 0.5) * 0.2,
      carve: pick(),
      skin: (PUMPKIN_ORANGE[Math.floor(rnd() * PUMPKIN_ORANGE.length)] as Color).clone(),
      glow: new Color(1, 0.62 + rnd() * 0.1, 0.2).multiplyScalar(3.4 + rnd() * 1.2),
      phase: rnd(),
      hang: 9 - y + rnd() * 2,
    });
  }
  const pumpkins = new PumpkinField(specs, ctx.atlas, { detail: tier === 'low' ? [22, 10] : [28, 12], simple: [12, 6], chunkSize: 8 });
  pumpkins.detailDistance = tier === 'low' ? 7 : 11;
  scene.add(pumpkins.group);

  // Red LED strings in the grass along both sides of the path: they light the fog from below.
  const red = new Color(1, 0.05, 0.03);
  const ledSpots: Vector3[] = [];
  for (let s = 0; s < path.length; s += 0.32) {
    path.at(s, tmp, tan);
    for (const side of [-1, 1]) {
      const d = 1.85 + Math.sin(s * 0.7 + side) * 0.15;
      ledSpots.push(new Vector3(tmp.x - tan.y * d * side, 0.04, tmp.y + tan.x * d * side));
    }
  }
  const ledMat = hallow(new MeshBasicMaterial({ color: red.clone().multiplyScalar(16) }), { key: 'led-red' });
  const leds = new InstancedMesh(new SphereGeometry(0.02, 5, 3), ledMat, ledSpots.length);
  const m = new Matrix4();
  ledSpots.forEach((p, i) => leds.setMatrixAt(i, m.makeTranslation(p.x, p.y, p.z)));
  leds.computeBoundingSphere();
  scene.add(leds);

  const glowLights: GlowLight[] = pumpkins.glowLights(3.4, tier === 'low' ? 0.09 : 0.055);
  // Every other pair (the spots alternate sides), so both strings light the fog.
  ledSpots.forEach((p, i) => {
    if (i % 4 < 2) glowLights.push({ x: p.x, z: p.z, y: p.y, radius: 1.3, color: red, intensity: 0.6, flicker: 0 });
  });

  const theWell = await well(ctx, WELL, Math.PI / 2);
  scene.add(...theWell.objects);
  glowLights.push(...theWell.glow);

  const fog = new FogBank({
    bounds: mask.bounds,
    mask: mask.texture(),
    slices: tier === 'low' ? 5 : 10,
    height: 1.1,
    tint: new Color(0.012, 0.016, 0.036),
    density: 0.24,
    glow: 0.6,
    wind: new Vector2(0.12, -0.2),
  });
  scene.add(fog.mesh);

  const hemi = new HemisphereLight(0x3b55a8, 0x0a0606, 0.2);
  scene.add(hemi);

  const blueHour = skyState({
    zenith: new Color(0.012, 0.03, 0.12),
    horizon: new Color(0.08, 0.13, 0.32),
    sunColor: new Color(0.35, 0.18, 0.2),
    sunDir: new Vector3(0.4, -0.1, -1).normalize(),
    sunGlow: 0.4,
    stars: 0.25,
    clouds: 0.35,
  });
  const lateBlue = skyState({
    zenith: new Color(0.006, 0.014, 0.06),
    horizon: new Color(0.035, 0.06, 0.16),
    sunGlow: 0.1,
    sunColor: new Color(0.3, 0.12, 0.15),
    sunDir: new Vector3(0.4, -0.2, -1).normalize(),
    stars: 0.6,
    clouds: 0.3,
  });
  // Deep blue shadows and rich candlelight: blacks kept down, contrast and colour up.
  const gradeA: Grade = {
    ...defaultGrade(),
    exposure: 1.08,
    bloom: 0.12,
    saturation: 1.38,
    power: 1.24,
    tint: new Color(0.97, 0.98, 1.06),
    lift: new Color(0.001, 0.002, 0.012),
  };
  const gradeB: Grade = { ...gradeA, exposure: 1.14, lift: new Color(0.001, 0.002, 0.01) };
  const fogA = new Color(0.026, 0.038, 0.09);
  const fogB = new Color(0.012, 0.018, 0.046);

  const sources: LightSource[] = specs.filter((_, i) => i % 2 === 0).map((s) => ({
    position: s.position.clone().add(new Vector3(0, -0.1, 0)),
    color: new Color(1, 0.56, 0.18),
    intensity: 0.6,
    distance: 4.5,
    phase: s.phase as number,
  }));
  sources.push(...theWell.sources);

  // --- Hide and seek. ---
  // Three hiding places: a pumpkin near the path at about a quarter, a half and three quarters.
  const hides: number[] = [];
  for (const frac of [0.27, 0.52, 0.77]) {
    const target = path.at(path.length * frac);
    let best = 0;
    let bestScore = 1e9;
    specs.forEach((s, i) => {
      const d = Math.hypot(s.position.x - target.x, s.position.z - target.y);
      const score = d + Math.abs(s.position.y - 3) * 0.8;
      if (score < bestScore && !hides.includes(i)) {
        bestScore = score;
        best = i;
      }
    });
    hides.push(best);
    const spec = specs[best] as PumpkinSpec;
    spec.position.y = Math.min(spec.position.y, 3.1);
  }
  let found = 0;
  let hiding = -1; // index into hides while the Ember is inside
  let hideClock = 0;
  let chimeClock = 0;
  let phase: 'lead' | 'flying' | 'hidden' | 'done' = 'lead';
  let time = 0;
  // The well: noticed as you come near, and when you toss a coin in, the Ember dives in after it
  // and comes back up on the fog.
  let wellNoticed = 0;
  let wellHinted = false;
  let coins = 0;
  let diving = 0;
  const DIVE = 3.4;
  theWell.hooks.onCoin = () => {
    coins++;
    ctx.ui.hideHint();
    if (phase === 'lead' || phase === 'done') diving = DIVE;
    if (coins === 1) setTimeout(() => ctx.ui.say('A long way down… and the well breathes out.', 5), 2600);
  };
  const lines = ['Where did it go?', 'There! And off again…', 'Found it again. One more time.', 'It wants to show you something.'];

  const chapter: Chapter = {
    scene,
    path,
    terrain,
    music: 'grove',
    ambience: 'grove',
    steps: 'step-gravel', // the same packed gravel path as the Arbor's (the leaves lie beside it)

    enter() {
      ctx.glow.setBounds(...bounds);
      ctx.glow.setLights(glowLights);
      ctx.glow.wave = 1e9;
      ctx.lights.sources = sources;
      shared.uFogDensity.value = 0.024;
      shared.uFogHeight.value = 6;
      shared.uFogGlow.value = 0.7;
      ctx.ember.presence = 1;
      ctx.ember.place(new Vector3(0, 1.7, 3));
      ctx.audio.preload('garden');
      phase = 'lead';
    },

    update(dt) {
      time += dt;
      const w = ctx.walker;
      const t = Math.min(1, w.s / path.length);
      lerpSky(ctx.sky.state, blueHour, lateBlue, t);
      lerpGrade(ctx.post.grade, gradeA, gradeB, t);
      shared.uFogColor.value.copy(fogA).lerp(fogB, t);
      ctx.sky.mesh.material.uniforms.uSunColor!.value = ctx.sky.state.sunColor;
      theWell.update(dt, time);

      const e = ctx.ember;
      const toWell = Math.hypot(WELL.x - w.position.x, WELL.z - w.position.z);
      if (!wellNoticed && toWell < 10 && phase !== 'flying') {
        wellNoticed = time;
        ctx.ui.say('An old stone well, breathing red fog.', 5);
      }
      if (wellNoticed && !wellHinted && !coins && time - wellNoticed > 4 && toWell < 5.5) {
        wellHinted = true;
        ctx.ui.showHint(ctx.portal.viewport.touch ? 'Tap the well to toss in a coin' : 'Click the well to toss in a coin', 8);
      }
      if (diving > 0) {
        // Down into the shaft after the coin, then up again on the fog as the well breathes out.
        diving = Math.max(0, diving - dt);
        const k = DIVE - diving;
        const m = theWell.mouth;
        e.target.set(m.x, m.y + (k < 0.6 ? 1.1 : k < 1.6 ? -0.6 : 2.3), m.z);
        e.presence = k > 0.9 && k < 1.7 ? Math.max(0.15, e.presence - dt * 2) : Math.min(1, e.presence + dt * 2);
      } else if (phase === 'lead') {
        // Floats ahead until you near the next hiding place, then dives into it.
        path.at(Math.min(path.length, w.s + 4), tmp);
        e.target.set(tmp.x, 1.7 + Math.sin(time) * 0.2, tmp.y);
        e.presence = Math.min(1, e.presence + dt);
        const next = hides[found];
        if (next !== undefined) {
          const sp = specs[next] as PumpkinSpec;
          if (Math.hypot(sp.position.x - w.position.x, sp.position.z - w.position.z) < 13) {
            phase = 'flying';
            hiding = next;
            e.agility = 2.6;
            void ctx.audio.sfx('ember-chime-grove', { at: e.position, volume: 0.6 });
          }
        } else if (found >= 3) {
          phase = 'done';
        }
      } else if (phase === 'flying') {
        const sp = specs[hiding] as PumpkinSpec;
        e.target.copy(sp.position);
        if (e.position.distanceTo(sp.position) < 0.35) {
          phase = 'hidden';
          hideClock = 0;
          chimeClock = 1.5;
          if (found === 0) ctx.ui.say(lines[0] as string, 5);
        }
      } else if (phase === 'hidden') {
        hideClock += dt;
        chimeClock += dt;
        e.presence = Math.max(0, e.presence - dt * 3);
        // Its pumpkin glows brighter and gently pulses.
        pumpkins.setLevel(hiding, 1.9 + Math.sin(time * 4) * 0.35);
        const sp = specs[hiding] as PumpkinSpec;
        if (chimeClock > 3.2) {
          chimeClock = 0;
          void ctx.audio.sfx('ember-chime-grove', { at: sp.position, volume: 0.45 });
        }
        // If you walk right past without finding it, it gets impatient and pops out.
        const passed = Math.hypot(sp.position.x - w.position.x, sp.position.z - w.position.z) < 2.6 && hideClock > 6;
        if (passed || hideClock > 40) reveal();
      } else if (phase === 'done') {
        path.at(Math.min(path.length, w.s + 4.5), tmp);
        e.target.set(tmp.x, 1.6 + Math.sin(time * 0.8) * 0.2, tmp.y);
        e.presence = Math.min(1, e.presence + dt);
      }

      ctx.glow.moving.length = 0;
      if (e.presence > 0.01) ctx.glow.moving.push(e.glow);
      fog.walkers[0]?.set(w.position.x, w.position.z);
      fog.update();
      pumpkins.update(ctx.camera, dt);
    },

    pick(ray: Ray): TapAction | null {
      const wellTap = theWell.pick(ray);
      if (wellTap) return wellTap;
      const i = pumpkins.pick(ray, 30);
      if (i < 0) return null;
      if (phase === 'hidden' && i === hiding) return () => reveal(true);
      return () => {
        pumpkins.flare(i);
        void ctx.audio.sfx('pumpkin-flare', { at: (specs[i] as PumpkinSpec).position, volume: 0.6 });
      };
    },

    finished() {
      return phase === 'done' && ctx.walker.s > path.length - 1.2;
    },

    dispose() {
      terrain.dispose();
      pumpkins.dispose();
      theWell.dispose();
      woods.dispose();
      canopy.dispose();
      fog.dispose();
      floor.geometry.dispose();
      leds.geometry.dispose();
      ledMat.dispose();
    },
  };

  function reveal(byYou = false) {
    const sp = specs[hiding] as PumpkinSpec;
    pumpkins.setLevel(hiding, 1);
    pumpkins.flare(hiding);
    ctx.ember.place(sp.position.clone().add(new Vector3(0, 0, 0.2)));
    ctx.ember.presence = 0.6;
    ctx.ember.excitement = 1;
    setTimeout(() => (ctx.ember.excitement = 0), 1500);
    void ctx.audio.sfx('ember-chime-grove', { at: sp.position, volume: 0.9 });
    if (byYou) void ctx.audio.sfx('pumpkin-flare', { at: sp.position, volume: 0.7 });
    found++;
    ctx.ui.say(lines[found] as string, 4.5);
    phase = 'lead';
    hiding = -1;
  }

  return chapter;
}
