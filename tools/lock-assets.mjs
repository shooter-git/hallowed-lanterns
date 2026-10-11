// Lists every file in public/ that isn't in assets.lock.json yet as our own work ("own"):
// everything in this creation is modelled or synthesised by its own tools (tools/blender,
// tools/audio). Run after rendering new models or sounds: node tools/lock-assets.mjs [projectDir]
import { readdir, readFile, writeFile } from 'node:fs/promises';
import { join, relative } from 'node:path';

const root = process.argv[2] ?? process.cwd();
const lockPath = join(root, 'assets.lock.json');
const EXT = new Set(['glb', 'gltf', 'png', 'jpg', 'jpeg', 'webp', 'ktx2', 'mp3', 'ogg', 'opus', 'wav', 'm4a', 'woff', 'woff2', 'ttf', 'otf', 'hdr', 'exr']);

async function walk(dir) {
  const out = [];
  for (const e of await readdir(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) out.push(...(await walk(p)));
    else out.push(p);
  }
  return out;
}

const lock = JSON.parse(await readFile(lockPath, 'utf8'));
const listed = new Set(lock.assets.map((a) => a.path));
let added = 0;
for (const file of await walk(join(root, 'public'))) {
  const path = relative(root, file).split('\\').join('/');
  if (!EXT.has(path.split('.').pop().toLowerCase()) || listed.has(path)) continue;
  const source = path.startsWith('public/audio/')
    ? 'Synthesised with tools/audio (Hallowed Lanterns)'
    : path.startsWith('public/models/')
      ? 'Modelled procedurally with tools/blender (Hallowed Lanterns)'
      : 'Made for Hallowed Lanterns';
  lock.assets.push({ path, license: 'own', source });
  added++;
}
lock.assets.sort((a, b) => a.path.localeCompare(b.path));
await writeFile(lockPath, `${JSON.stringify(lock, null, 2)}\n`);
console.log(`${added} added, ${lock.assets.length} listed`);
