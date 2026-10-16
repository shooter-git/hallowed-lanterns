import {
  BoxGeometry,
  CanvasTexture,
  Color,
  DoubleSide,
  Group,
  InstancedMesh,
  Matrix4,
  Mesh,
  MeshStandardMaterial,
  PlaneGeometry,
  Quaternion,
  RepeatWrapping,
  SRGBColorSpace,
  Vector3,
} from 'three';
import type { GlowLight } from '../engine/glowfield.ts';
import { stringLights } from '../engine/lanterns.ts';
import type { LightSource } from '../engine/lights.ts';
import { PumpkinField, type PumpkinSpec } from '../engine/pumpkins.ts';
import { hallow } from '../engine/shared.ts';
import type { ChapterContext } from './types.ts';

/**
 * The way in: a great wall of stacked hay bales with the night's name in big black letters,
 * heirloom pumpkins — orange, white, dusty pink — piled on bales at its foot, and a rope of purple
 * and orange lights strung on white stakes in front. Where the walk begins, at sunset.
 */

let hayTex: CanvasTexture | null = null;
function hayTexture(): CanvasTexture {
  if (hayTex) return hayTex;
  const w = 256;
  const h = 128;
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const g = c.getContext('2d') as CanvasRenderingContext2D;
  g.fillStyle = '#8a6a3a';
  g.fillRect(0, 0, w, h);
  // Straw: thousands of short strokes in golds and browns, mostly lying along the bale.
  for (let i = 0; i < 2600; i++) {
    const x = Math.random() * w;
    const y = Math.random() * h;
    const len = 6 + Math.random() * 18;
    const a = (Math.random() - 0.5) * 0.9;
    const tone = Math.random();
    g.strokeStyle = `rgba(${Math.round(150 + tone * 90)},${Math.round(110 + tone * 70)},${Math.round(50 + tone * 40)},${0.5 + Math.random() * 0.5})`;
    g.lineWidth = 0.6 + Math.random() * 1.2;
    g.beginPath();
    g.moveTo(x, y);
    g.lineTo(x + Math.cos(a) * len, y + Math.sin(a) * len);
    g.stroke();
  }
  // Twine bands and a darker seam where bales meet.
  g.fillStyle = 'rgba(40,28,14,0.5)';
  g.fillRect(0, 0, w, 3);
  g.fillRect(0, 0, 3, h);
  g.fillStyle = 'rgba(30,20,10,0.35)';
  g.fillRect(w * 0.3, 0, 2, h);
  g.fillRect(w * 0.7, 0, 2, h);
  hayTex = new CanvasTexture(c);
  hayTex.colorSpace = SRGBColorSpace;
  hayTex.wrapS = hayTex.wrapT = RepeatWrapping;
  return hayTex;
}

function lettersTexture(lines: string[]): CanvasTexture {
  const c = document.createElement('canvas');
  c.width = 2048;
  c.height = 1024;
  const g = c.getContext('2d') as CanvasRenderingContext2D;
  g.fillStyle = '#0c0b0b';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  const size = 400;
  g.font = `bold ${size}px "Rockwell", "Roboto Slab", "Courier New", Georgia, serif`;
  lines.forEach((line, i) => {
    // Squeeze to fit the wall, letter by letter so the spacing stays even.
    const width = g.measureText(line).width;
    const scale = Math.min(1, 1960 / width);
    g.save();
    g.translate(1024, 260 + i * 480);
    g.scale(scale, 1);
    g.fillText(line, 0, 0);
    g.restore();
  });
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

export function buildEntrance(ctx: ChapterContext, at: Vector3, yaw: number, rnd: () => number) {
  const group = new Group();
  group.position.copy(at);
  group.rotation.y = yaw;

  // The wall: seven rows of bales, the top row a little ragged.
  const hay = hallow(new MeshStandardMaterial({ map: hayTexture(), roughness: 0.95, color: 0xe0c8a0 }), { key: 'hay', glow: 1.3 });
  const baleW = 1.15;
  const baleH = 0.6;
  const cols = 12;
  const rows = 7;
  const bales = new InstancedMesh(new BoxGeometry(baleW, baleH, 1.0), hay, cols * rows + 12);
  const m = new Matrix4();
  const q = new Quaternion();
  let n = 0;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (r === rows - 1 && rnd() < 0.25) continue;
      const x = (c - cols / 2 + 0.5) * baleW + (r % 2 ? baleW * 0.5 : 0) + (rnd() - 0.5) * 0.05;
      q.setFromAxisAngle(new Vector3(0, 1, 0), (rnd() - 0.5) * 0.05);
      m.compose(new Vector3(x, baleH / 2 + r * baleH, (rnd() - 0.5) * 0.06), q, new Vector3(1, 1 + (rnd() - 0.5) * 0.06, 1));
      bales.setMatrixAt(n++, m);
    }
  }
  // A low step of bales along the front, for the pumpkins.
  for (let c = 0; c < 12; c++) {
    m.compose(new Vector3((c - 5.5) * baleW, 0.3, 1.0), q.identity(), new Vector3(1, 1, 0.9));
    bales.setMatrixAt(n++, m);
  }
  bales.count = n;
  bales.computeBoundingSphere();
  group.add(bales);

  // The letters: black boards on the face of the wall (two layers, for a little depth).
  const letters = lettersTexture(['HALLOWED', 'LANTERNS']);
  for (const [z, shade] of [
    [0.52, 0x050505],
    [0.56, 0x161413],
  ] as [number, number][]) {
    const plane = new Mesh(
      new PlaneGeometry(cols * baleW * 0.95, rows * baleH * 0.95),
      hallow(new MeshStandardMaterial({ map: letters, color: shade, transparent: false, alphaTest: 0.5, roughness: 0.7, side: DoubleSide }), { key: 'letters', glow: 0.6 }),
    );
    plane.position.set(0, rows * baleH * 0.52, z);
    group.add(plane);
  }

  // Heirloom pumpkins on the step and on the ground: orange, white, dusty pink, a few big ones.
  const specs: PumpkinSpec[] = [];
  const skins = [new Color(0.75, 0.24, 0.03), new Color(0.82, 0.8, 0.7), new Color(0.8, 0.52, 0.45), new Color(0.7, 0.32, 0.06), new Color(0.6, 0.62, 0.45)];
  const world = (x: number, y: number, z: number) => new Vector3(x, y, z).applyAxisAngle(new Vector3(0, 1, 0), yaw).add(at);
  for (let i = 0; i < 46; i++) {
    const onStep = i < 26;
    const big = rnd() < 0.15;
    const r = big ? 0.32 + rnd() * 0.08 : 0.1 + rnd() * 0.12;
    const x = (rnd() - 0.5) * cols * baleW * 0.95;
    const y = onStep ? 0.6 + r * 0.7 : r * 0.7;
    const z = onStep ? 1.0 + (rnd() - 0.5) * 0.6 : 1.7 + rnd() * 1.2;
    specs.push({
      position: world(x, y, z),
      size: new Vector3(r, r * (0.7 + rnd() * 0.25), r),
      yaw: rnd() * 6.28,
      carve: -1,
      skin: (skins[Math.floor(rnd() * skins.length)] as Color).clone(),
      glow: new Color(0, 0, 0),
    });
  }
  const pumpkins = new PumpkinField(specs, ctx.atlas, { detail: [32, 14], simple: [14, 7] });

  // A rope of purple and orange lights on white stakes in front.
  const stakeMat = hallow(new MeshStandardMaterial({ color: 0xe8e4dc, roughness: 0.6 }), { key: 'stake-white', glow: 1 });
  const stakes = new InstancedMesh(new BoxGeometry(0.05, 1.0, 0.05), stakeMat, 6);
  const runs: { from: Vector3; to: Vector3; sag: number }[] = [];
  const stakeAt: Vector3[] = [];
  for (let k = 0; k < 6; k++) {
    const p = world((k - 2.5) * 2.6, 0, 3.4 + Math.sin(k) * 0.3);
    stakeAt.push(p);
    stakes.setMatrixAt(k, new Matrix4().makeTranslation(p.x, 0.5, p.z));
  }
  stakes.computeBoundingSphere();
  for (let k = 0; k < 5; k++) runs.push({ from: (stakeAt[k] as Vector3).clone().setY(0.95), to: (stakeAt[k + 1] as Vector3).clone().setY(0.95), sag: 0.45 });
  // Along the ground in front of the bales too.
  runs.push({ from: world(-7, 0.08, 1.6), to: world(7, 0.08, 1.6), sag: 0 });
  const purple = stringLights(runs, { spacing: 0.32, color: new Color(0.6, 0.15, 1), brightness: 12, size: 0.025, glowEvery: 2, glowRadius: 0.9, glowIntensity: 0.25 });
  const orange = stringLights(
    runs.map((r) => ({ from: r.from.clone().add(new Vector3(0.12, 0, 0.05)), to: r.to.clone().add(new Vector3(0.12, 0, 0.05)), sag: r.sag })),
    { spacing: 0.64, color: new Color(1, 0.4, 0.05), brightness: 12, size: 0.025, glowEvery: 2, glowRadius: 0.9, glowIntensity: 0.25 },
  );

  // Warm orange floodlights at the foot of the wall.
  const glow: GlowLight[] = [...purple.lights, ...orange.lights];
  for (let k = 0; k < 5; k++) {
    const p = world((k - 2) * 2.8, 0, 1.8);
    glow.push({ x: p.x, z: p.z, y: 0.3, radius: 3.4, color: new Color(1, 0.42, 0.12), intensity: 0.45, flicker: 0 });
  }
  const sources: LightSource[] = [
    { position: world(-3, 1.0, 3), color: new Color(1, 0.45, 0.15), intensity: 6, distance: 10 },
    { position: world(3, 1.0, 3), color: new Color(1, 0.45, 0.15), intensity: 6, distance: 10 },
  ];

  return {
    group,
    world: [pumpkins.group, stakes, purple.mesh, orange.mesh],
    pumpkins,
    glow,
    sources,
    dispose() {
      pumpkins.dispose();
      bales.geometry.dispose();
      stakes.geometry.dispose();
      purple.mesh.geometry.dispose();
      orange.mesh.geometry.dispose();
      letters.dispose();
    },
  };
}
