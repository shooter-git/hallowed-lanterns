import {
  AdditiveBlending,
  BoxGeometry,
  Color,
  CylinderGeometry,
  DynamicDrawUsage,
  Group,
  InstancedBufferAttribute,
  InstancedMesh,
  Matrix4,
  Mesh,
  MeshStandardMaterial,
  type Object3D,
  PlaneGeometry,
  Quaternion,
  type Ray,
  ShaderMaterial,
  Vector3,
} from 'three';
import type { ChapterContext } from '../chapters/types.ts';
import type { GlowLight } from '../engine/glowfield.ts';
import { loadModel } from '../engine/models.ts';
import { hallow, SHADER_PARS, shared, VERTEX_TERRAIN } from '../engine/shared.ts';
import { heightAt, pointOnGround } from '../engine/terrain.ts';
import type { SetPiece } from './types.ts';

/**
 * The magical well: an old stone well under a little shingled roof, ivy up its posts, and red-lit
 * fog welling up out of it and rolling over the rim, as if the grove's fog came from here. Toss a
 * coin in (tap it): it rings off the stone, falls a long way, and the well breathes out a surge
 * of fog as the echo comes back up.
 */

const PUFFS = 28;

/** Soft, slowly turning billows of fog, lit red from below. */
function plumeMaterial(): ShaderMaterial {
  return new ShaderMaterial({
    uniforms: { ...shared },
    vertexShader: /* glsl */ `
      attribute vec4 aPuff; // age 0..1, opacity, spin, seed
      varying vec2 vUv;
      varying float vAge;
      varying float vAlpha;
      varying float vSeed;
      varying vec3 vHlWorld;
      ${VERTEX_TERRAIN}
      void main() {
        vUv = uv;
        vAge = aPuff.x;
        vAlpha = aPuff.y;
        vSeed = aPuff.w;
        // Billboards: face the camera, sized by the instance's scale.
        vec4 centre = modelMatrix * instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);
        centre.y += hlTerrain(centre.xz);
        float size = length(instanceMatrix[0].xyz);
        float c = cos(aPuff.z), s = sin(aPuff.z);
        vec2 corner = mat2(c, -s, s, c) * position.xy * size;
        vec4 view = viewMatrix * centre + vec4(corner, 0.0, 0.0);
        vHlWorld = centre.xyz;
        gl_Position = projectionMatrix * view;
      }`,
    fragmentShader: /* glsl */ `
      ${SHADER_PARS}
      varying vec2 vUv;
      varying float vAge;
      varying float vAlpha;
      varying float vSeed;
      varying vec3 vHlWorld;
      void main() {
        vec2 p = vUv - 0.5;
        float r = length(p) * 2.0;
        float billow = hlFbm(p * 3.0 + vec2(vSeed * 7.0, vSeed * 3.0 - uHlTime * 0.05));
        float a = smoothstep(1.0, 0.15, r + (billow - 0.5) * 0.55) * vAlpha;
        if (a < 0.004) discard;
        // Lit from the well: deep red low down and young, a dusky rose as it rises and thins.
        vec3 col = mix(vec3(1.0, 0.16, 0.12), vec3(0.75, 0.32, 0.42), smoothstep(0.1, 0.9, vAge));
        col *= 0.55 + 0.6 * billow;
        gl_FragColor = vec4(col * a * 0.42, a * 0.3);
      }`,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
  });
}

export async function well(ctx: ChapterContext, at: Vector3, yaw: number): Promise<SetPiece> {
  const objects: Object3D[] = [];
  const toWorld = (v: Vector3) => v.clone().applyAxisAngle(new Vector3(0, 1, 0), yaw).add(at);
  const group = new Group();
  group.position.copy(at);
  group.rotation.y = yaw;
  objects.push(group);

  const model = await loadModel('magic-well', { glowReceive: 0.8 });
  let mouth = toWorld(new Vector3(0, 0.55, 0));
  let crank: Object3D | undefined;
  let drum: Object3D | undefined;
  if (model) {
    group.add(model.root);
    group.updateMatrixWorld(true);
    for (const m of model.glows.values()) m.emissiveIntensity = 1.6;
    const fog = model.node('fog_source');
    if (fog) mouth = fog.getWorldPosition(new Vector3());
    crank = model.node('crank');
    drum = model.node('windlass');
  } else {
    // A stand-in: a ring of stone, two posts and a roof.
    const stone = hallow(new MeshStandardMaterial({ color: 0x3b3a36, roughness: 0.95 }), { key: 'well-stone', glow: 1.2 });
    const wood = hallow(new MeshStandardMaterial({ color: 0x2a1c12, roughness: 0.9 }), { key: 'well-wood' });
    const wall = new Mesh(new CylinderGeometry(0.62, 0.66, 0.85, 20, 1, true), stone);
    wall.position.y = 0.42;
    const rim = new Mesh(new CylinderGeometry(0.7, 0.7, 0.1, 20), stone);
    rim.position.y = 0.88;
    const inner = new Mesh(
      new CylinderGeometry(0.55, 0.55, 0.6, 20, 1, true),
      new MeshStandardMaterial({ color: 0x100000, emissive: 0xff2010, emissiveIntensity: 1.2, side: 2 }),
    );
    inner.position.y = 0.55;
    group.add(wall, rim, inner);
    for (const side of [-1, 1]) {
      const post = new Mesh(new BoxGeometry(0.12, 2.2, 0.12), wood);
      post.position.set(side * 0.72, 1.1, 0);
      group.add(post);
    }
    for (const side of [-1, 1]) {
      const roof = new Mesh(new BoxGeometry(1.8, 0.05, 0.8), wood);
      roof.position.set(0, 2.25, side * 0.3);
      roof.rotation.x = side * 0.55;
      group.add(roof);
    }
    group.updateMatrixWorld(true);
  }

  // The fog that wells up: puffs born in the shaft, rising, spreading and rolling out over the rim.
  const mat = plumeMaterial();
  const puffs = new InstancedMesh(new PlaneGeometry(1, 1), mat, PUFFS);
  const state = new Float32Array(PUFFS * 4);
  const attr = new InstancedBufferAttribute(state, 4);
  attr.setUsage(DynamicDrawUsage);
  puffs.geometry.setAttribute('aPuff', attr);
  puffs.frustumCulled = false;
  puffs.renderOrder = 6;
  objects.push(puffs);
  type Puff = { age: number; life: number; drift: Vector3; spin: number; size: number };
  const list: Puff[] = [];
  const born = (p: Puff, now = false) => {
    p.age = now ? 0 : Math.random();
    p.life = 5 + Math.random() * 4;
    p.drift = new Vector3((Math.random() - 0.5) * 0.32, 0.16 + Math.random() * 0.12, (Math.random() - 0.5) * 0.32);
    p.spin = Math.random() * 6.28;
    p.size = 0.7 + Math.random() * 0.5;
  };
  for (let i = 0; i < PUFFS; i++) {
    const p = { age: 0, life: 6, drift: new Vector3(), spin: 0, size: 1 };
    born(p);
    list.push(p);
  }
  const m4 = new Matrix4();
  const q = new Quaternion();
  const pos = new Vector3();
  const scale = new Vector3();
  const ground = heightAt(mouth.x, mouth.z);
  const base = mouth.clone().setY(mouth.y - ground); // puffs are lifted onto the terrain in the shader

  let surge = 0;
  let time = 0;
  const glow: GlowLight = { x: mouth.x, z: mouth.z, radius: 2.6, color: new Color(1, 0.12, 0.08), intensity: 0.3, flicker: 0.15 };
  const coinAt = model?.node('coin_drop')?.getWorldPosition(new Vector3()) ?? mouth.clone().setY(mouth.y + 0.5);

  return {
    objects,
    glow: [glow],
    sources: [
      { position: mouth.clone().setY(mouth.y + 0.4), color: new Color(1, 0.15, 0.1), intensity: 3, distance: 4, phase: 0.7 },
      { position: toWorld(new Vector3(0, 1.4, -1.6)), color: new Color(0.6, 0.2, 1), intensity: 2, distance: 4 },
    ],
    update(dt) {
      time += dt;
      surge = Math.max(0, surge - dt / 4);
      glow.intensity = 0.3 + surge * 0.6;
      // the windlass turns as the well breathes out (both about their axle, along x)
      if (crank) crank.rotation.x -= dt * surge * 6;
      if (drum) drum.rotation.x -= dt * surge * 6;
      for (let i = 0; i < PUFFS; i++) {
        const p = list[i] as Puff;
        p.age += (dt * (1 + surge * 1.5)) / p.life;
        if (p.age >= 1) born(p, true);
        const t = p.age;
        // Up out of the shaft, then out and over the rim as it loses its lift.
        pos.copy(base).addScaledVector(p.drift, t * p.life * (1 + surge));
        pos.x += Math.sin(time * 0.3 + i) * 0.15 * t;
        // it lifts a little out of the shaft, then spills over the rim and settles
        pos.y = base.y + Math.min(t * p.life * p.drift.y, 0.9) - t * t * 0.7;
        const s = p.size * (0.4 + t * 1.2) * (1 + surge * 0.6);
        scale.set(s, s, s);
        m4.compose(pos, q, scale);
        puffs.setMatrixAt(i, m4);
        state[i * 4] = t;
        state[i * 4 + 1] = Math.sin(Math.PI * Math.min(1, t * 1.4)) * (0.6 + surge * 0.5);
        state[i * 4 + 2] = p.spin + time * 0.1;
        state[i * 4 + 3] = (i * 0.618) % 1;
      }
      puffs.instanceMatrix.needsUpdate = true;
      attr.needsUpdate = true;
    },
    pick(ray: Ray) {
      if (ray.distanceSqToPoint(pointOnGround(mouth.clone().setY(mouth.y + 0.3))) > 1.4) return null;
      return () => {
        void ctx.audio.sfx('well-coin', { at: pointOnGround(coinAt), volume: 0.9 });
        // The fog breathes out as the echo comes back up.
        setTimeout(() => (surge = 1), 1300);
      };
    },
    dispose() {
      puffs.geometry.dispose();
      mat.dispose();
    },
  };
}
