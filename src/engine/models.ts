import { gltfLoader } from '@allthespaces/portal/three';
import { type Group, type Material, type Mesh, MeshStandardMaterial, type Object3D } from 'three';
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
