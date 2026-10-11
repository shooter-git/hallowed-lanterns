import {
  AdditiveBlending,
  Box3,
  BufferAttribute,
  BufferGeometry,
  Color,
  DoubleSide,
  ExtrudeGeometry,
  Float32BufferAttribute,
  HemisphereLight,
  InstancedBufferAttribute,
  InstancedBufferGeometry,
  Mesh,
  MeshBasicMaterial as MeshBasicGlow,
  type MeshStandardMaterial,
  type Object3D,
  PlaneGeometry,
  type Ray,
  Scene,
  ShaderMaterial,
  Shape,
  Vector2,
  Vector3,
} from 'three';
import { CARVE } from '../engine/carvings.ts';
import type { GlowLight } from '../engine/glowfield.ts';
import { type Bounds, ground, GroundMask } from '../engine/ground.ts';
import type { LightSource } from '../engine/lights.ts';
import { loadModel } from '../engine/models.ts';
import { defaultGrade, type Grade, lerpGrade } from '../engine/post.ts';
import { PumpkinField, type PumpkinSpec } from '../engine/pumpkins.ts';
import { Path } from '../engine/rig.ts';
import { aroundPath, onGround, pointOnGround, Terrain } from '../engine/terrain.ts';
import { hallow, SHADER_PARS, shared, VERTEX_TERRAIN } from '../engine/shared.ts';
import { lerpSky, skyState, treeLine } from '../engine/sky.ts';
import { woodland } from '../engine/canopy.ts';
import { forest, lineThePath } from '../engine/trees.ts';
import { Drift } from '../engine/weather.ts';
import type { Chapter, ChapterContext, TapAction } from './types.ts';

/**
 * VII. The Deep — the snow has become bubbles and blue light pours in: you walk the sea floor
 * under pumpkin jellyfish trailing glowing ribbons, past glowing coral and pufferfish, over beds of
 * blue lights. At the end the Keeper of the Deep rises from waves of light: a giant octopus with a
 * pumpkin for a head and ember-orange eyes. Wave to it, and it waves back.
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

const KEEPER = new Vector3(0, 0, -60);

/** Ribbons of light along both sides of the path: beds of tiny blue LEDs, twinkling. */
function ledBeds(path: Path, inner: number, outer: number): Mesh {
  const pos: number[] = [];
  const idx: number[] = [];
  const t = new Vector2();
  const p = new Vector2();
  for (const side of [-1, 1]) {
    const base = pos.length / 3;
    let n = 0;
    for (let s = 0; s <= path.length; s += 0.5) {
      path.at(s, p, t);
      const nx = -t.y * side;
      const nz = t.x * side;
      const wobble = Math.sin(s * 0.45 + side) * 0.5;
      pos.push(p.x + nx * inner, 0.012, p.y + nz * inner, p.x + nx * (outer + wobble), 0.012, p.y + nz * (outer + wobble));
      n++;
    }
    for (let i = 0; i < n - 1; i++) {
      const a = base + i * 2;
      idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  const mat = new ShaderMaterial({
    uniforms: { ...shared },
    vertexShader: /* glsl */ `
      varying vec3 vHlWorld;
      ${VERTEX_TERRAIN}
      void main() { vHlWorld = (modelMatrix * vec4(position, 1.0)).xyz; vHlWorld.y += hlTerrain(vHlWorld.xz); gl_Position = projectionMatrix * viewMatrix * vec4(vHlWorld, 1.0); }`,
    fragmentShader: /* glsl */ `
      ${SHADER_PARS}
      varying vec3 vHlWorld;
      void main() {
        vec2 g = vHlWorld.xz / 0.11;
        vec2 cell = floor(g);
        vec2 o = hlHash22(cell) * 0.6 + 0.2;
        float d = length(fract(g) - o);
        float on = step(0.35, hlHash12(cell + 3.1));
        float tw = 0.6 + 0.4 * sin(uHlTime * (1.0 + hlHash12(cell) * 3.0) + hlHash12(cell + 9.0) * 40.0);
        float led = smoothstep(0.14, 0.0, d) * on * tw;
        vec3 col = vec3(0.12, 0.28, 1.0) * led * 9.0;
        col = hlApplyFog(col, vHlWorld);
        gl_FragColor = vec4(col, 1.0);
      }`,
    blending: AdditiveBlending,
    transparent: true,
    depthWrite: false,
  });
  const mesh = new Mesh(g, mat);
  mesh.renderOrder = 2;
  return mesh;
}

/** Light rippling over the sea floor, as through moving water. */
function caustics(bounds: Bounds): Mesh {
  const [minX, minZ, sx, sz] = bounds;
  const geo = new PlaneGeometry(sx, sz, Math.ceil(sx / 1.5), Math.ceil(sz / 1.5));
  geo.rotateX(-Math.PI / 2);
  geo.translate(minX + sx / 2, 0.02, minZ + sz / 2);
  const mat = new ShaderMaterial({
    uniforms: { ...shared },
    vertexShader: /* glsl */ `
      varying vec3 vHlWorld;
      ${VERTEX_TERRAIN}
      void main() { vHlWorld = (modelMatrix * vec4(position, 1.0)).xyz; vHlWorld.y += hlTerrain(vHlWorld.xz); gl_Position = projectionMatrix * viewMatrix * vec4(vHlWorld, 1.0); }`,
    fragmentShader: /* glsl */ `
      ${SHADER_PARS}
      varying vec3 vHlWorld;
      float cell(vec2 p) {
        vec2 n = floor(p); vec2 f = fract(p); float d = 8.0;
        for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
          vec2 g = vec2(float(i), float(j));
          vec2 o = 0.5 + 0.45 * sin(uHlTime * 0.7 + 6.2831 * hlHash22(n + g));
          d = min(d, length(g + o - f));
        }
        return d;
      }
      void main() {
        vec2 p = vHlWorld.xz * 0.9;
        float c = pow(cell(p), 2.5) + pow(cell(p * 1.7 + 3.0), 2.5) * 0.6;
        float k = smoothstep(0.25, 0.85, c);
        float fade = exp(-distance(vHlWorld, cameraPosition) * 0.07);
        vec3 col = vec3(0.25, 0.55, 1.0) * k * 0.35 * fade;
        gl_FragColor = vec4(col, 1.0);
      }`,
    blending: AdditiveBlending,
    transparent: true,
    depthWrite: false,
  });
  const m = new Mesh(geo, mat);
  m.renderOrder = 3;
  return m;
}

/** Jellyfish ribbons: long pale streamers hanging from each bell, swaying in the current. */
function streamers(anchors: { p: Vector3; len: number; phase: number }[]): Mesh<InstancedBufferGeometry, ShaderMaterial> {
  const plane = new PlaneGeometry(0.1, 1, 1, 14);
  plane.translate(0, -0.5, 0);
  const geo = new InstancedBufferGeometry();
  geo.index = plane.index;
  geo.setAttribute('position', plane.getAttribute('position'));
  geo.setAttribute('uv', plane.getAttribute('uv'));
  const at = new Float32Array(anchors.length * 4);
  const ph = new Float32Array(anchors.length);
  anchors.forEach((a, i) => {
    at.set([a.p.x, a.p.y, a.p.z, a.len], i * 4);
    ph[i] = a.phase;
  });
  geo.setAttribute('aAt', new InstancedBufferAttribute(at, 4));
  geo.setAttribute('aPhase', new InstancedBufferAttribute(ph, 1));
  geo.instanceCount = anchors.length;
  return new Mesh(
    geo,
    new ShaderMaterial({
      uniforms: { ...shared },
      vertexShader: /* glsl */ `
        attribute vec4 aAt;
        attribute float aPhase;
        uniform float uHlTime;
        varying float vT;
        varying vec3 vHlWorld;
        ${VERTEX_TERRAIN}
        void main() {
          float t = -position.y;           // 0 at the bell, 1 at the tip
          vT = t;
          float wave = sin(uHlTime * 1.4 - t * 6.0 + aPhase * 6.28) * 0.12 * t;
          float wave2 = cos(uHlTime * 0.9 - t * 4.0 + aPhase * 3.0) * 0.1 * t;
          vec3 w = aAt.xyz + vec3(wave + cos(aPhase * 6.28) * 0.08, -t * aAt.w + hlTerrain(aAt.xz), wave2 + sin(aPhase * 6.28) * 0.08);
          // Face the camera around the vertical axis.
          vec3 toCam = normalize(vec3(cameraPosition.x - w.x, 0.0, cameraPosition.z - w.z));
          vec3 side = vec3(toCam.z, 0.0, -toCam.x);
          w += side * position.x * (1.0 - t * 0.5);
          // Curl like ribbon.
          w += side * sin(t * 9.0 + aPhase * 10.0) * 0.03;
          vHlWorld = w;
          gl_Position = projectionMatrix * viewMatrix * vec4(w, 1.0);
        }`,
      fragmentShader: /* glsl */ `
        ${SHADER_PARS}
        varying float vT;
        varying vec3 vHlWorld;
        void main() {
          vec3 col = mix(vec3(1.0, 0.7, 0.5), vec3(0.7, 0.75, 1.0), vT) * (2.4 - 1.6 * vT);
          col = hlApplyFog(col, vHlWorld);
          gl_FragColor = vec4(col * 0.9, 1.0);
        }`,
      transparent: true,
      depthWrite: false,
      blending: AdditiveBlending,
      side: DoubleSide,
    }),
  );
}

/** A flat painted coral cut-out board, branching, in a neon colour. */
function coral(height: number, color: Color, seed: number): Mesh {
  const rnd = rng(seed);
  const s = new Shape();
  // Built as a thick branching outline: trunk then forks, each a rounded finger.
  const fingers: { x: number; h: number; w: number; lean: number }[] = [];
  const n = 3 + Math.floor(rnd() * 3);
  for (let i = 0; i < n; i++) fingers.push({ x: (i / (n - 1) - 0.5) * height * 0.7, h: height * (0.55 + rnd() * 0.45), w: height * 0.07, lean: (rnd() - 0.5) * 0.3 });
  s.moveTo(-height * 0.08, 0);
  for (const f of fingers) {
    const tx = f.x + f.lean * f.h;
    s.lineTo(f.x * 0.25 - f.w, height * 0.25);
    s.quadraticCurveTo(f.x - f.w, f.h * 0.6, tx - f.w, f.h - f.w);
    s.quadraticCurveTo(tx, f.h + f.w * 0.8, tx + f.w, f.h - f.w);
    s.quadraticCurveTo(f.x + f.w, f.h * 0.6, f.x * 0.25 + f.w, height * 0.28);
  }
  s.lineTo(height * 0.08, 0);
  s.lineTo(-height * 0.08, 0);
  const geo = new ExtrudeGeometry(s, { depth: 0.04, bevelEnabled: false, curveSegments: 6 });
  return new Mesh(geo, hallow(new MeshBasicGlow({ color }), { key: 'coral' }));
}

export async function build(ctx: ChapterContext): Promise<Chapter> {
  const { tier } = ctx;
  const rnd = rng(77);
  const scene = new Scene();
  const bounds: Bounds = [-40, -85, 80, 100];

  const path = new Path(
    [
      [0, 8],
      [0, -6],
      [2.5, -18],
      [-1.5, -31],
      [1, -42],
      [0, -49],
    ],
    3.4,
  );
  const terrain = new Terrain(bounds, aroundPath(path, { profile: (s) => -0.055 * Math.min(s, 44) + 0.18 * Math.sin(s / 6), bank: 0.05, rough: 0.5, seed: 7 }));

  const mask = new GroundMask(bounds, 4);
  mask.stroke(path.points.filter((_, i) => i % 4 === 0).map((p) => [p.x, p.y]), 3.6, 'r', 0.95);
  mask.blob(KEEPER.x, KEEPER.z + 6, 9, 'r', 0.9);
  mask.soften(3);
  const floor = ground({ mask, a: ctx.surface('gravel'), aScale: 1.4, b: ctx.surface('leaves'), bScale: 2.2, tone: 0.9 });
  scene.add(floor);
  scene.add(ledBeds(path, 1.75, 3.8));
  scene.add(caustics(bounds));

  // Dark trees (seaweed-dark against the blue), hung with jellyfish.
  const treeAt = lineThePath(path.points, 5, { spacing: 4.5, depth: 2, seed: 31 });
  const woods = forest(
    [
      { species: 'tall', at: treeAt.filter((_, i) => i % 2 === 0) },
      { species: 'young', at: treeAt.filter((_, i) => i % 2 === 1) },
    ],
    { leafTint: new Color(0.25, 0.32, 0.5), bark: new Color(0.03, 0.04, 0.07) },
  );
  scene.add(woods.group);
  const canopy = woodland(path, {
    canopy: [6.2, 10], reach: 10, skyGap: 0.3, density: tier === 'low' ? 1.3 : 2.2, wallFrom: 4.2, wallTo: 13, wallHeight: 5, wallDensity: tier === 'low' ? 3 : 4,
    tint: new Color(0.22, 0.3, 0.55), seed: 51,
    clear: (x, z, y) => Math.hypot(x - KEEPER.x, z - KEEPER.z) < 9 && y < 8,
  });
  scene.add(canopy.mesh);
  scene.add(treeLine({ radius: 110, height: 16, color: new Color(0.004, 0.012, 0.04), under: new Color(0.01, 0.03, 0.12) }));

  // Jellyfish: glowing pumpkin bells with trailing ribbons.
  const specs: PumpkinSpec[] = [];
  const ribbons: { p: Vector3; len: number; phase: number }[] = [];
  const jellies: number[] = [];
  const tmp = new Vector2();
  const tan = new Vector2();
  const count = tier === 'low' ? 70 : tier === 'mid' ? 150 : 200;
  for (let i = 0; i < count; i++) {
    const s = 2 + rnd() * (path.length - 4);
    path.at(s, tmp, tan);
    const off = (rnd() - 0.5) * 2 * (rnd() < 0.6 ? 3.5 : 8);
    const pos = new Vector3(tmp.x - tan.y * off, 2.6 + rnd() * 3.8, tmp.y + tan.x * off);
    const r = 0.16 + rnd() * 0.12;
    const purple = rnd() < 0.5;
    jellies.push(specs.length);
    specs.push({
      position: pos,
      size: new Vector3(r, r * 0.88, r),
      yaw: rnd() * 6,
      carve: -3,
      skin: purple ? new Color(0.35, 0.12, 0.55) : new Color(0.9, 0.42, 0.08),
      glow: new Color(1, 0.5, 0.15).multiplyScalar(2.6),
      phase: rnd(),
      hang: 9 - pos.y,
    });
    const len = 1.1 + rnd() * 1.6;
    for (let k = 0; k < (tier === 'low' ? 4 : 7); k++) {
      const a = (k / 8) * Math.PI * 2;
      ribbons.push({ p: pos.clone().add(new Vector3(Math.cos(a) * r * 0.7, -r * 0.45, Math.sin(a) * r * 0.7)), len: len * (0.6 + rnd() * 0.5), phase: rnd() });
    }
  }
  // Pufferfish (lime, spotted) peering from the branches.
  const puffers: number[] = [];
  for (let i = 0; i < (tier === 'low' ? 14 : 36); i++) {
    const s = 3 + rnd() * (path.length - 6);
    path.at(s, tmp, tan);
    const off = (rnd() < 0.5 ? -1 : 1) * (2.6 + rnd() * 2.5);
    puffers.push(specs.length);
    specs.push({
      position: new Vector3(tmp.x - tan.y * off, 1.8 + rnd() * 2.2, tmp.y + tan.x * off),
      size: new Vector3(0.24, 0.22, 0.24),
      yaw: Math.atan2(tmp.x - (tmp.x - tan.y * off), tmp.y - (tmp.y + tan.x * off)),
      carve: 100 + (CARVE.stars[1] as number),
      skin: new Color(0.35, 0.85, 0.15),
      glow: new Color(0.05, 0.2, 0.05),
      phase: rnd(),
      hang: 2,
    });
  }
  // Modelled pufferfish replace the painted-pumpkin stand-ins when we have them.
  const pufferModel = await loadModel('pufferfish', { glowReceive: 0.6 });
  const pufferObjects: Object3D[] = [];
  if (pufferModel) {
    for (const i of puffers) {
      const s = specs[i] as PumpkinSpec;
      const o = pufferModel.root.clone(true);
      o.position.copy(s.position);
      o.rotation.y = s.yaw;
      o.scale.setScalar(0.9 + Math.random() * 0.5);
      o.userData.base = o.scale.x;
      scene.add(o);
      pufferObjects.push(o);
      s.size.set(0.001, 0.001, 0.001);
    }
    for (const m of pufferModel.glows.values()) m.emissiveIntensity = 1.6;
  }
  const pumpkins = new PumpkinField(specs, ctx.atlas, { detail: [28, 12], simple: [14, 7] });
  scene.add(pumpkins.group);
  const ribbonMesh = streamers(ribbons);
  scene.add(ribbonMesh);

  // Coral boards along the beds.
  const coralColors = [new Color(1, 0.45, 0.1), new Color(1, 0.25, 0.55), new Color(0.75, 1, 0.2), new Color(1, 0.8, 0.2)];
  const corals: Mesh[] = [];
  const coralModels = (await Promise.all(['coral-1', 'coral-2', 'coral-3'].map((n) => loadModel(n, { glowReceive: 0.5 })))).filter(Boolean);
  for (let i = 0; i < (tier === 'low' ? 34 : 80); i++) {
    const s = rnd() * path.length;
    path.at(s, tmp, tan);
    const off = (rnd() < 0.5 ? -1 : 1) * (2.2 + rnd() * 1.6);
    const cm = coralModels[i % Math.max(1, coralModels.length)];
    if (cm && rnd() < 0.6) {
      const o = cm.root.clone(true);
      o.position.set(tmp.x - tan.y * off, 0, tmp.y + tan.x * off);
      o.rotation.y = Math.atan2(-tan.y * -off, tan.x * -off) + (rnd() - 0.5) * 0.8;
      o.scale.setScalar(1.0 + rnd() * 1.2);
      scene.add(o);
      continue;
    }
    const c = coral(1.0 + rnd() * 1.1, (coralColors[i % coralColors.length] as Color).clone().multiplyScalar(1.6), i + 3);
    c.position.set(tmp.x - tan.y * off, 0, tmp.y + tan.x * off);
    c.rotation.y = Math.atan2(-tan.y * -off, tan.x * -off) + (rnd() - 0.5) * 0.8;
    scene.add(c);
    corals.push(c);
  }

  // Giant neon clam shells in the beds, as in the photo.
  for (let k = 0; k < 3; k++) {
    const sh = new Shape();
    const R = 1.0 + k * 0.15;
    sh.moveTo(-R, 0);
    for (let a = 0; a <= 12; a++) {
      const t = Math.PI - (a / 12) * Math.PI;
      const rr = R * (0.92 + 0.08 * Math.cos(a * Math.PI));
      sh.lineTo(Math.cos(t) * rr, Math.sin(t) * rr * 1.1);
    }
    sh.lineTo(R, 0);
    const geo = new ExtrudeGeometry(sh, { depth: 0.08, bevelEnabled: true, bevelSize: 0.03, bevelThickness: 0.03, curveSegments: 4 });
    const clam = new Mesh(geo, hallow(new MeshBasicGlow({ color: new Color(1, 0.3, 0.6).multiplyScalar(1.4) }), { key: 'clam' }));
    const s0 = path.length * (0.3 + k * 0.25);
    path.at(s0, tmp, tan);
    const side = k % 2 ? 1 : -1;
    clam.position.set(tmp.x - tan.y * 3.4 * side, 0, tmp.y + tan.x * 3.4 * side);
    clam.rotation.y = Math.atan2(-tan.y * -side, tan.x * -side) + 0.4 * side;
    clam.rotation.x = -0.25;
    scene.add(clam);
    corals.push(clam);
  }

  // The Keeper of the Deep.
  const keeper = await loadModel('octopus', { glowReceive: 0.3 });
  let keeperRoot: Object3D | null = null;
  const tentacles: { node: Object3D; mat: MeshStandardMaterial; wave: { value: number } }[] = [];
  let eyes: Object3D[] = [];
  let keeperBox = new Box3();
  if (keeper) {
    keeperRoot = keeper.root;
    const box = new Box3().setFromObject(keeperRoot);
    const h = box.max.y - box.min.y;
    if (Math.abs(h - 6.5) / 6.5 > 0.1) keeperRoot.scale.multiplyScalar(6.5 / h);
    keeperRoot.position.copy(KEEPER);
    scene.add(keeperRoot);
    for (const m of keeper.glows.values()) m.emissiveIntensity = m.name === 'glow_eyes' ? 6 : 1.4;
    eyes = ['eye_L', 'eye_R'].map((n) => keeper.node(n)).filter(Boolean) as Object3D[];
    keeperRoot.traverse((o) => {
      const mesh = o as Mesh;
      if (!mesh.isMesh || !o.name.startsWith('tentacle')) return;
      const mat = (mesh.material as MeshStandardMaterial).clone();
      const wave = { value: 0 };
      const phase = Number(o.name.split('_')[1] ?? 0) * 0.8;
      hallow(mat, {
        key: `tentacle${phase}`,
        glow: 0.3,
        uniforms: { uWave: wave, uPhase: { value: phase } },
        vertexPars: 'uniform float uWave;\nuniform float uPhase;',
        vertex: [
          [
            '#include <begin_vertex>',
            /* glsl */ `#include <begin_vertex>
            {
              // Bend along the tentacle (uv1.x: 0 at the root, 1 at the tip): a slow sway,
              // and a big wave when it waves at you.
              float a = uv1.x;
              float sway = sin(uHlTime * 0.7 + uPhase + a * 2.5) * 0.25 + uWave * sin(uHlTime * 5.0 + a * 3.0) * 0.9;
              transformed.x += sway * a * a;
              transformed.z += cos(uHlTime * 0.5 + uPhase * 1.3 + a * 2.0) * 0.15 * a * a;
              transformed.y += uWave * a * a * 0.6;
            }`,
          ],
        ],
      });
      mat.defines = { ...(mat.defines ?? {}), USE_UV1: '' };
      mesh.material = mat;
      tentacles.push({ node: o, mat, wave });
    });
    keeperBox = new Box3().setFromObject(keeperRoot);
    keeperRoot.position.y = -7;
  }

  // Waves of light: translucent blue sheets of fabric strung with tiny lights around the Keeper.
  const sheetMat = new ShaderMaterial({
    uniforms: { ...shared, uBright: { value: 0.3 } },
    vertexShader: /* glsl */ `
      uniform float uHlTime;
      varying vec2 vUv;
      varying vec3 vHlWorld;
      ${VERTEX_TERRAIN}
      void main() {
        vUv = uv;
        vec3 p = position;
        p.z += sin(p.x * 1.3 + uHlTime * 0.8) * 0.35 + sin(p.y * 2.0 + uHlTime * 0.6) * 0.15;
        vHlWorld = (modelMatrix * vec4(p, 1.0)).xyz;
        vHlWorld.y += hlTerrain(vHlWorld.xz);
        gl_Position = projectionMatrix * viewMatrix * vec4(vHlWorld, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      ${SHADER_PARS}
      uniform float uBright;
      varying vec2 vUv;
      varying vec3 vHlWorld;
      void main() {
        float folds = 0.55 + 0.45 * sin(vUv.x * 40.0 + sin(vUv.y * 6.0) * 2.0);
        vec3 col = vec3(0.12, 0.3, 1.0) * folds * 0.35 * uBright;
        vec2 g = vUv * vec2(60.0, 18.0);
        vec2 cell = floor(g);
        float led = smoothstep(0.18, 0.0, length(fract(g) - 0.5 - (hlHash22(cell) - 0.5) * 0.5)) * step(0.55, hlHash12(cell));
        float tw = 0.5 + 0.5 * sin(uHlTime * 2.0 + hlHash12(cell + 2.0) * 30.0);
        col += vec3(0.4, 0.65, 1.0) * led * tw * 4.0 * uBright;
        float edge = smoothstep(0.0, 0.15, vUv.y) * smoothstep(1.0, 0.7, vUv.y);
        gl_FragColor = vec4(col * edge, 1.0);
      }`,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
    side: DoubleSide,
  });
  const sheets: Mesh[] = [];
  for (let i = 0; i < 6; i++) {
    const geo = new PlaneGeometry(7, 2.6, 30, 8);
    // Curl each into a wave crest.
    const pos = geo.getAttribute('position') as BufferAttribute;
    for (let k = 0; k < pos.count; k++) {
      const x = pos.getX(k);
      const y = pos.getY(k) + 1.3;
      pos.setXYZ(k, x, y, Math.pow(y / 2.6, 2) * 1.4);
    }
    geo.computeVertexNormals();
    const sheet = new Mesh(geo, sheetMat);
    const a = -1.2 + i * 0.48;
    sheet.position.set(KEEPER.x + Math.sin(a) * 5, 0, KEEPER.z + Math.cos(a) * 4.2 + 1);
    sheet.rotation.y = a + Math.PI;
    sheet.renderOrder = 6;
    scene.add(sheet);
    sheets.push(sheet);
  }

  const bubbles = new Drift({ count: tier === 'low' ? 900 : 2200, box: 18, size: 0.07, color: new Color(0.5, 0.7, 1), style: 'bubble', opacity: 0.8 });
  bubbles.velocity.set(0.05, 0.55, 0);
  scene.add(bubbles.points);

  const glowLights: GlowLight[] = [...pumpkins.glowLights(2.2, tier === 'low' ? 0.08 : 0.05)];
  for (let s = 0; s <= path.length; s += 1.2) {
    path.at(s, tmp, tan);
    for (const side of [-1, 1]) glowLights.push({ x: tmp.x - tan.y * 2.7 * side, z: tmp.y + tan.x * 2.7 * side, radius: 2.2, color: new Color(0.15, 0.3, 1), intensity: 0.22, flicker: 0 });
  }
  for (const c of corals) glowLights.push({ x: c.position.x, z: c.position.z, radius: 1.2, color: (c.material as MeshBasicGlow).color, intensity: 0.08, flicker: 0 });
  glowLights.push({ x: KEEPER.x, z: KEEPER.z + 2, radius: 9, color: new Color(0.35, 0.2, 1), intensity: 0.5, flicker: 0 });
  const sources: LightSource[] = [
    { position: KEEPER.clone().add(new Vector3(0, 1, 4)), color: new Color(0.45, 0.3, 1), intensity: 10, distance: 16 },
    ...specs.filter((_, i) => jellies.includes(i)).slice(0, 60).map((s) => ({ position: s.position, color: new Color(1, 0.5, 0.2), intensity: 0.7, distance: 4 })),
  ];
  scene.add(new HemisphereLight(0x1c3cff, 0x02040c, 0.35));

  const sea = skyState({ zenith: new Color(0.0, 0.01, 0.05), horizon: new Color(0.0, 0.04, 0.14), stars: 0 });
  const grade: Grade = { ...defaultGrade(), exposure: 1.15, bloom: 0.13, saturation: 1.25, power: 1.05, tint: new Color(0.85, 0.95, 1.15), lift: new Color(0.0, 0.006, 0.03) };

  let time = 0;
  let risen = 0;
  let rising = false;
  let waving = 0;
  let hinted = 0;
  let wavedBack = false;
  const puffed = new Map<number, number>();

  const chapter: Chapter = {
    scene,
    path,
    terrain,
    music: 'deep',
    ambience: 'deep',
    steps: 'step-sand',

    enter() {
      ctx.glow.setBounds(...bounds);
      ctx.glow.setLights(glowLights);
      ctx.glow.wave = 1e9;
      ctx.lights.sources = sources;
      lerpSky(ctx.sky.state, sea, sea, 0);
      lerpGrade(ctx.post.grade, grade, grade, 0);
      shared.uFogColor.value.set(0.004, 0.03, 0.11);
      shared.uFogDensity.value = 0.05;
      shared.uFogHeight.value = 30;
      shared.uFogGlow.value = 0.6;
      ctx.audio.setUnderwater(1);
      ctx.ember.presence = 1;
      ctx.ember.place(new Vector3(0, 1.8, 5));
      ctx.audio.preload('marigold', ['bubble', 'puffer-puff', 'octopus-wave', 'step-sand']);
      setTimeout(() => ctx.ui.say('Everything sounds far away down here.', 5), 4000);
    },

    update(dt) {
      time += dt;
      const w = ctx.walker;
      const e = ctx.ember;
      const scale = ctx.renderer.domElement.height / (2 * Math.tan((ctx.camera.fov * Math.PI) / 360));
      bubbles.update(dt, scale);
      // Jellies pulse, brighter when you pass beneath.
      for (const i of jellies) {
        const s = specs[i] as PumpkinSpec;
        const pulse = Math.sin(time * 1.6 + (s.phase ?? 0) * 6.28);
        pumpkins.pose(i, 1, Math.sin(time * 0.5 + (s.phase ?? 0) * 6) * 0.15, 1 + pulse * 0.08);
        const d = Math.hypot(s.position.x - w.position.x, s.position.z - w.position.z);
        pumpkins.setLevel(i, 1 + Math.max(0, 1 - d / 3) * 1.2);
      }
      for (const [i, t] of puffed) {
        const k = t + dt;
        const big = k < 0.25 ? k / 0.25 : Math.max(0, 1 - (k - 1.5) / 0.6);
        const fish = pufferObjects[puffers.indexOf(i)];
        if (fish) fish.scale.setScalar((fish.userData.base as number) * (1 + big * 0.55));
        else pumpkins.pose(i, 1 + big * 0.45);
        if (k > 2.2) {
          puffed.delete(i);
          if (!fish) pumpkins.pose(i, 1);
        } else puffed.set(i, k);
      }
      // The Keeper rises as you come near.
      if (keeperRoot) {
        const d = Math.hypot(w.position.x - KEEPER.x, w.position.z - KEEPER.z);
        if (!rising && d < 22) {
          rising = true;
          void ctx.audio.cue('keeper-rises', 1);
          ctx.ui.say('Something enormous is rising…', 5);
        }
        if (rising) risen = Math.min(1, risen + dt / 7);
        const k = risen * risen * (3 - 2 * risen);
        keeperRoot.position.y = -7 * (1 - k) + Math.sin(time * 0.6) * 0.08 * k;
        sheetMat.uniforms.uBright!.value = 0.3 + 0.9 * k;
        // Its eyes follow you.
        for (const eye of eyes) {
          const local = eye.parent ? eye.parent.worldToLocal(ctx.camera.position.clone()) : ctx.camera.position.clone();
          const dir = local.sub(eye.position).normalize();
          eye.rotation.y += (Math.atan2(dir.x, dir.z) * 0.5 - eye.rotation.y) * (1 - Math.exp(-dt * 2));
          eye.rotation.x += (-Math.asin(Math.max(-1, Math.min(1, dir.y))) * 0.4 - eye.rotation.x) * (1 - Math.exp(-dt * 2));
        }
        waving = Math.max(0, waving - dt / 3);
        const wv = Math.sin(Math.min(1, waving) * Math.PI);
        tentacles.forEach((t, i) => (t.wave.value = i === 2 ? wv : wv * 0.15));
        if (k > 0.9 && !hinted && d < 14) {
          hinted = time;
          ctx.ui.say('Wave to it.', 4);
        }
        // If you don't, it waves first.
        if (hinted && !wavedBack && time - hinted > 10) wave('It waves at you.');
      }
      // The Ember swims ahead, then hovers by the Keeper.
      path.at(Math.min(path.length, w.s + 4), tmp);
      if (risen > 0.6) e.target.copy(KEEPER).add(new Vector3(1.8, 4.2, 2));
      else e.target.set(tmp.x, 2 + Math.sin(time * 0.9) * 0.3, tmp.y);
      ctx.glow.moving.length = 0;
      ctx.glow.moving.push(e.glow);
      pumpkins.update(ctx.camera, dt);
    },

    pick(ray: Ray): TapAction | null {
      if (keeperRoot && risen > 0.5 && ray.intersectsBox(onGround(keeperBox.clone().translate(new Vector3(0, keeperRoot.position.y, 0)))))
        return () => wave('It waves back.');
      for (let k = 0; k < pufferObjects.length; k++) {
        const fish = pufferObjects[k] as Object3D;
        if (ray.distanceSqToPoint(pointOnGround(fish.position)) < 0.18) {
          const i = puffers[k] as number;
          return () => {
            puffed.set(i, 0);
            void ctx.audio.sfx('puffer-puff', { at: pointOnGround(fish.position), volume: 0.8 });
          };
        }
      }
      const i = pumpkins.pick(ray, 18);
      if (i >= 0 && puffers.includes(i))
        return () => {
          puffed.set(i, 0);
          void ctx.audio.sfx('puffer-puff', { at: (specs[i] as PumpkinSpec).position, volume: 0.8 });
        };
      if (i >= 0)
        return () => {
          pumpkins.flare(i);
          void ctx.audio.sfx('bubble', { at: (specs[i] as PumpkinSpec).position, volume: 0.7 });
        };
      return null;
    },

    finished() {
      return wavedBack && risen >= 1 && ctx.walker.s > path.length - 1.2 && waving <= 0;
    },

    dispose() {
      terrain.dispose();
      ctx.audio.setUnderwater(0);
      pumpkins.dispose();
      woods.dispose();
      canopy.dispose();
      bubbles.dispose();
      floor.geometry.dispose();
      ribbonMesh.geometry.dispose();
      for (const c of corals) c.geometry.dispose();
    },
  };
  if (import.meta.env.DEV) (window as unknown as { deep: unknown }).deep = { rise: () => (risen = 1, rising = true) };

  function wave(line: string) {
    wavedBack = true;
    waving = 1.4;
    void ctx.audio.sfx('octopus-wave', { at: KEEPER.clone().add(new Vector3(0, 3, 0)), volume: 1 });
    ctx.ui.say(line, 4);
  }

  return chapter;
}
