import {
  AdditiveBlending,
  Color,
  CylinderGeometry,
  ExtrudeGeometry,
  Group,
  Mesh,
  MeshStandardMaterial,
  type Object3D,
  type Ray,
  ShaderMaterial,
  Shape,
  Vector3,
} from 'three';
import type { ChapterContext } from '../chapters/types.ts';
import { CARVE } from '../engine/carvings.ts';
import type { GlowLight } from '../engine/glowfield.ts';
import { loadModel } from '../engine/models.ts';
import { PumpkinField, type PumpkinSpec } from '../engine/pumpkins.ts';
import { hallow, shared, VERTEX_TERRAIN } from '../engine/shared.ts';
import { pointOnGround } from '../engine/terrain.ts';
import type { SetPiece } from './types.ts';

/**
 * The giant guitar by the ofrenda: a guitar-shaped board covered in leaves and carved pumpkins
 * (roses and sugar skulls glowing red), a rim of little pumpkins with pink and purple lights, and
 * six tall neon-green strings rising into the green fog. Tap a string to play it — and the
 * Ember's song can be played on them.
 */
export async function guitar(ctx: ChapterContext, at: Vector3, yaw: number): Promise<SetPiece & { onSong: (() => void) | null }> {
  const objects: Object3D[] = [];
  const toWorld = (v: Vector3) => v.clone().applyAxisAngle(new Vector3(0, 1, 0), yaw).add(at);
  const group = new Group();
  group.position.copy(at);
  group.rotation.y = yaw;
  objects.push(group);

  const model = await loadModel('pumpkin-guitar', { glowReceive: 1 });
  const bodySpots: Vector3[] = [];
  const rimSpots: Vector3[] = [];
  /** Pumpkin diameters from the model (each spot's scale), by spot. */
  const bodySize: number[] = [];
  const rimSize: number[] = [];
  const strings: { bottom: Vector3; bend?: Vector3; top: Vector3 }[] = [];
  if (model) {
    group.add(model.root);
    group.updateMatrixWorld(true);
    model.node('pumpkin_spots')?.traverse((o) => {
      if (!o.name.startsWith('spot_')) return;
      // spot_00..15 are the big pumpkins on the body, the rest the little ones round the rim.
      const p = o.getWorldPosition(new Vector3());
      const big = Number(o.name.slice(5)) < 16;
      (big ? bodySpots : rimSpots).push(p);
      (big ? bodySize : rimSize).push(o.scale.x);
    });
    for (let k = 0; k < 6; k++) {
      const b = model.node(`string_bottom_${k}`);
      const t = model.node(`string_top_${k}`);
      // Where the string leaves the straight neck and fans out to its peg.
      const bend = model.node(`string_bend_${k}`)?.getWorldPosition(new Vector3());
      if (b && t) strings.push({ bottom: b.getWorldPosition(new Vector3()), bend, top: t.getWorldPosition(new Vector3()) });
    }
  }
  if (!bodySpots.length) {
    // A stand-in board: two rounded bouts and a waist, 3 m tall.
    const s = new Shape();
    s.absellipse(0, 0.95, 1.25, 0.95, 0, Math.PI * 2, false, 0);
    const upper = new Shape();
    upper.absellipse(0, 2.3, 0.95, 0.75, 0, Math.PI * 2, false, 0);
    const mat = hallow(new MeshStandardMaterial({ color: 0x1c2a14, roughness: 0.95 }), { key: 'guitar-board', glow: 1.2 });
    for (const sh of [s, upper]) {
      const m = new Mesh(new ExtrudeGeometry(sh, { depth: 0.18, bevelEnabled: false, curveSegments: 32 }), mat);
      m.position.z = -0.2;
      group.add(m);
    }
    for (let k = 0; k < 14; k++) bodySpots.push(toWorld(new Vector3(-0.8 + (k % 4) * 0.55 + (Math.floor(k / 4) % 2) * 0.25, 0.5 + Math.floor(k / 4) * 0.55, 0.1)));
    for (let k = 0; k < 40; k++) {
      const a = (k / 40) * Math.PI * 2;
      const upperBout = Math.sin(a) > 0.35;
      rimSpots.push(toWorld(upperBout ? new Vector3(Math.cos(a) * 1.0, 2.3 + Math.sin(a) * 0.8, 0.05) : new Vector3(Math.cos(a) * 1.3, 0.95 + Math.sin(a) * 1.0, 0.05)));
    }
  }
  if (!strings.length) for (let k = 0; k < 6; k++) strings.push({ bottom: toWorld(new Vector3(-0.25 + k * 0.1, 1.0, 0.15)), top: toWorld(new Vector3(-0.25 + k * 0.1 + (k < 3 ? -0.15 : 0.15), 6.3, 0.15)) });

  // Pumpkins: big carved ones on the body (roses, sugar skulls) glowing red; little ones round the rim
  // carved with dots of light in pink and purple.
  const specs: PumpkinSpec[] = [];
  const radii = (d: number | undefined, fallback: Vector3) => (d ? new Vector3(d / 2, d * 0.55, d * 0.45) : fallback);
  bodySpots.forEach((p, i) => specs.push({ position: p, size: radii(bodySize[i], new Vector3(0.24, 0.3, 0.2)), yaw, carve: i % 2 ? CARVE.rose : CARVE.sugarSkull, skin: new Color(0.55, 0.22, 0.05), glow: new Color(1, 0.12, 0.08).multiplyScalar(3.5), phase: i * 0.31 }));
  rimSpots.forEach((p, i) => specs.push({ position: p, size: radii(rimSize[i], new Vector3(0.12, 0.11, 0.12)), yaw, carve: CARVE.stars[i % CARVE.stars.length] as number, skin: new Color(0.6, 0.25, 0.06), glow: (i % 2 ? new Color(1, 0.15, 0.7) : new Color(0.6, 0.2, 1)).multiplyScalar(4), phase: i * 0.13 }));
  const pumpkins = new PumpkinField(specs, ctx.atlas, { detail: [28, 12], simple: [14, 7] });
  objects.push(pumpkins.group);

  // Six neon strings. Each its own little shader so it can shimmer and vibrate when played.
  const amps = strings.map(() => ({ value: 0 }));
  const segments = strings.flatMap((s, i) => (s.bend ? [{ from: s.bottom, to: s.bend, i }, { from: s.bend, to: s.top, i }] : [{ from: s.bottom, to: s.top, i }]));
  segments.forEach(({ from, to, i }) => {
    const len = from.distanceTo(to);
    const geo = new CylinderGeometry(0.025, 0.025, len, 6, 24, true);
    geo.translate(0, len / 2, 0);
    const mat = new ShaderMaterial({
      uniforms: { uAmp: amps[i] as { value: number }, uTime: { value: 0 }, uTerrain: shared.uTerrain, uTerrainBounds: shared.uTerrainBounds },
      vertexShader: /* glsl */ `
        uniform float uAmp;
        uniform float uTime;
        varying float vT;
        ${VERTEX_TERRAIN}
        void main() {
          vT = position.y;
          vec3 p = position;
          float along = clamp(p.y / ${len.toFixed(3)}, 0.0, 1.0);
          p.x += sin(along * 3.14159) * sin(uTime * 90.0) * uAmp * 0.08;
          vec4 w = modelMatrix * vec4(p, 1.0);
          w.y += hlTerrain(w.xz);
          gl_Position = projectionMatrix * viewMatrix * w;
        }`,
      fragmentShader: /* glsl */ `
        uniform float uAmp;
        varying float vT;
        void main() { gl_FragColor = vec4(vec3(0.25, 1.0, 0.35) * (7.0 + uAmp * 10.0), 1.0); }`,
      blending: AdditiveBlending,
      transparent: true,
      depthWrite: false,
    });
    const mesh = new Mesh(geo, mat);
    mesh.position.copy(from);
    mesh.quaternion.setFromUnitVectors(new Vector3(0, 1, 0), to.clone().sub(from).normalize());
    mesh.frustumCulled = false;
    mesh.userData.mat = mat;
    objects.push(mesh);
  });

  const centre = toWorld(new Vector3(0, 0, 0.5));
  const glow: GlowLight[] = [
    ...pumpkins.glowLights(1.5, 0.14),
    { x: centre.x, z: centre.z, radius: 7, color: new Color(0.25, 1, 0.35), intensity: 0.5, flicker: 0 },
  ];
  const played: number[] = [];
  // Strings, low to high: G D G B D E (the Marigold's G). The Ember's song (G E D B D) is strings 2 5 4 3 4.
  const song = [2, 5, 4, 3, 4];
  let time = 0;
  const piece = {
    objects,
    onSong: null as (() => void) | null,
    glow,
    sources: [
      { position: toWorld(new Vector3(0, 3, 1.5)), color: new Color(0.3, 1, 0.4), intensity: 6, distance: 10 },
      { position: toWorld(new Vector3(0, 1.2, 1)), color: new Color(1, 0.2, 0.4), intensity: 4, distance: 6 },
    ],
    update(dt: number) {
      time += dt;
      for (const o of objects) {
        const m = o.userData.mat as ShaderMaterial | undefined;
        if (m) m.uniforms.uTime!.value = time;
      }
      for (const a of amps) a.value = Math.max(0, a.value - dt * 0.7);
      pumpkins.update(ctx.camera, dt);
    },
    pick(ray: Ray) {
      let best = -1;
      let bestD = 0.12;
      strings.forEach((s, i) => {
        // Distance from the ray to the string's lower half (within reach).
        const end = s.bend ?? s.top;
        for (let t = 0.05; t < (s.bend ? 0.96 : 0.5); t += 0.05) {
          const p = pointOnGround(s.bottom.clone().lerp(end, t));
          const d = ray.distanceSqToPoint(p);
          if (d < bestD) {
            bestD = d;
            best = i;
          }
        }
      });
      if (best < 0) return null;
      return () => {
        (amps[best] as { value: number }).value = 1;
        void ctx.audio.sfxIndex('guitar', best, { at: pointOnGround(centre.clone().setY(1.5)), volume: 0.6 });
        played.push(best);
        if (played.length > 5) played.shift();
        if (played.length === 5 && played.every((n, k) => n === song[k])) {
          played.length = 0;
          for (const a of amps) a.value = 1.5;
          piece.onSong?.();
        }
      };
    },
    dispose() {
      pumpkins.dispose();
    },
  };
  return piece;
}
