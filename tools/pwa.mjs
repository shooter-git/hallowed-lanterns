// Writes sw.js (tools/pwa-sw.js, filled in) into `pnpm build`, the build published on its own to
// GitHub Pages. All the Spaces builds creations with its own settings and ignores vite.config.ts,
// so its build never has a service worker (a sealed frame couldn't run one anyway).
import { createHash } from 'node:crypto';
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';

const hash = (data) => createHash('sha256').update(data).digest('hex').slice(0, 16);

function* walk(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) yield* walk(p);
    else yield p;
  }
}

/** @returns {import('vite').Plugin} */
export function pwa() {
  let publicDir = '';
  return {
    name: 'hallowed-lanterns:service-worker',
    apply: 'build',
    enforce: 'post',
    configResolved(config) {
      publicDir = config.publicDir;
    },
    generateBundle(_, bundle) {
      // The shell: the page and everything the build made (scripts, styles), cached on install.
      // Their names carry a hash, so a new version is a new set of names.
      const shell = ['./'];
      const contents = [];
      for (const name of Object.keys(bundle))
        if (name !== 'index.html' && !name.endsWith('.map')) shell.push(name);
      contents.push(String(bundle['index.html']?.source ?? ''));
      // public/ ships as it is. The manifest and icons join the shell; sounds and models are
      // cached as they're first played, each by the revision of its contents.
      const files = {};
      for (const file of walk(publicDir)) {
        const path = relative(publicDir, file).split(sep).join('/');
        const data = readFileSync(file);
        if (path === 'manifest.webmanifest' || path.startsWith('icons/')) {
          shell.push(path);
          contents.push(hash(data));
        } else files[path] = hash(data);
      }
      shell.sort();
      const version = hash(JSON.stringify([shell, contents, files]));
      const template = readFileSync(new URL('./pwa-sw.js', import.meta.url), 'utf8');
      this.emitFile({
        type: 'asset',
        fileName: 'sw.js',
        source: template.replace('/* BUILD */ null', JSON.stringify({ version, shell, files })),
      });
    },
  };
}
