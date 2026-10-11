import { gltfLoader } from '@allthespaces/portal/three';
import { Box3, type Group, InstancedMesh, type Material, Matrix4, type Mesh, MeshStandardMaterial, type Object3D, Vector3 } from 'three';
import { hallow } from './shared.ts';

const base = new URL('./models/', document.baseURI);
const cache = new Map<string, Promise<Group | null>>();

export interface LoadedModel {
  root: Group;
  /** Materials whose names start with `glow_`: drive their brightness with `emissiveIntensity`. */
  glows: Map<string, MeshStandardMaterial>;
  /** Named nodes (for animating parts: `head`, `arm_R`, `tentacle_3`…). */
  node: (name: string) => Object3D | undefined;
}

/**
 * Loads one of the Blender models from `public/models/`, makes its materials part of the world
 * (glow field and fog), and returns a fresh copy each time. Resolves to null if the model isn't
 * there (yet), so a chapter can stand in something simpler.
 */
export async function loadModel(name: string, options: { glowReceive?: number } = {}): Promise<LoadedModel | null> {
  let p = cache.get(name);
  if (!p) {
    p = (async () => {
      try {
        const gltf = await gltfLoader().loadAsync(new URL(`${name}.glb`, base).href);
        return gltf.scene;
      } catch {
        return null;
      }
    })();
    cache.set(name, p);
  }
  const source = await p;
  if (!source) return null;
  const root = source.clone(true);
  const glows = new Map<string, MeshStandardMaterial>();
  const patched = new Map<Material, Material>();
  root.traverse((o) => {
    const mesh = o as Mesh;
    if (!mesh.isMesh) return;
    const swap = (mat: Material): Material => {
      const done = patched.get(mat);
      if (done) return done;
      let out = mat;
      if ((mat as MeshStandardMaterial).isMeshStandardMaterial) {
        const m = (mat as MeshStandardMaterial).clone();
        const glow = m.name.startsWith('glow_');
        hallow(m, { key: `model:${glow ? 'glow' : 'lit'}`, glow: options.glowReceive ?? 1 });
        if (glow) glows.set(m.name, m);
        out = m;
      }
      patched.set(mat, out);
      return out;
    };
    mesh.material = Array.isArray(mesh.material) ? mesh.material.map(swap) : swap(mesh.material);
  });
  return { root, glows, node: (n) => root.getObjectByName(n) };
}

/**
 * Repeats a model at many places for a few draw calls: one instanced mesh per part of the model.
 * `placements` are world matrices for the model's root.
 */
export function instanceModel(model: LoadedModel, placements: Matrix4[], options: { skip?: string; only?: string } = {}): Group {
  const out = model.root.clone(false) as Group;
  out.clear();
  out.position.set(0, 0, 0);
  out.rotation.set(0, 0, 0);
  out.scale.set(1, 1, 1);
  model.root.updateMatrixWorld(true);
  const rootInverse = model.root.matrixWorld.clone().invert();
  const under = (o: Object3D, name: string) => {
    for (let p: Object3D | null = o; p; p = p.parent) if (p.name === name) return true;
    return false;
  };
  model.root.traverse((o) => {
    const mesh = o as Mesh;
    if (!mesh.isMesh || !mesh.visible) return;
    if (options.skip && under(o, options.skip)) return;
    if (options.only && !under(o, options.only)) return;
    const local = rootInverse.clone().multiply(mesh.matrixWorld);
    const inst = new InstancedMesh(mesh.geometry, mesh.material, placements.length);
    placements.forEach((p, i) => inst.setMatrixAt(i, p.clone().multiply(local)));
    inst.computeBoundingSphere();
    out.add(inst);
  });
  return out;
}

/** The model's size (m) as loaded. */
export function modelSize(model: LoadedModel): Vector3 {
  return new Box3().setFromObject(model.root).getSize(new Vector3());
}

/**
 * Lets a model's long parts (tentacles) sway and curl: each mesh whose name starts with `prefix`
 * gets a vertex bend driven by its `along` UV (0 at the root, 1 at the tip). Returns a handle per
 * part: set `wave` (0–1) to make it curl and wave.
 */
export function bendable(model: LoadedModel, prefix: string, options: { sway?: number; key?: string } = {}) {
  const parts: { node: Object3D; wave: { value: number } }[] = [];
  model.root.traverse((o) => {
    const mesh = o as Mesh;
    if (!mesh.isMesh) return;
    // '*' means every part that has a bend map; otherwise parts named with the prefix.
    if (prefix === '*' ? !mesh.geometry.getAttribute('uv1') : !o.name.startsWith(prefix)) return;
    const mat = (mesh.material as MeshStandardMaterial).clone();
    const wave = { value: 0 };
    const phase = parts.length * 0.8 + 0.3;
    hallow(mat, {
      key: `${options.key ?? prefix}${parts.length}`,
      glow: 0.3,
      uniforms: { uWave: wave, uPhase: { value: phase }, uSway: { value: options.sway ?? 0.25 } },
      vertexPars: 'uniform float uWave;\nuniform float uPhase;\nuniform float uSway;',
      vertex: [
        [
          '#include <begin_vertex>',
          /* glsl */ `#include <begin_vertex>
          {
            float a = uv1.x;
            float sway = sin(uHlTime * 0.7 + uPhase + a * 2.5) * uSway + uWave * sin(uHlTime * 5.0 + a * 3.0) * 0.9;
            transformed.x += sway * a * a;
            transformed.z += cos(uHlTime * 0.5 + uPhase * 1.3 + a * 2.0) * uSway * 0.6 * a * a;
            transformed.y += uWave * a * a * 0.6;
          }`,
        ],
      ],
    });
    mat.defines = { ...(mat.defines ?? {}), USE_UV1: '' };
    mesh.material = mat;
    parts.push({ node: o, wave });
  });
  return parts;
}
