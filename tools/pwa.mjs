// The app's own files, in `pnpm build` only, the build published on its own to GitHub Pages: sw.js
// (tools/pwa-sw.js, filled in), and the manifest and its icons from pwa/ (served by `pnpm dev`
// too). All the Spaces builds creations with its own settings and ignores vite.config.ts, so its
// build has none of them: no service worker (a sealed frame couldn't run one), and no manifest,
// which its checks refuse to serve (and which its frame couldn't use anyway).
import { createHash } from 'node:crypto';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';

const hash = (data) => createHash('sha256').update(data).digest('hex').slice(0, 16);

function* walk(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) yield* walk(p);
    else yield p;
  }
}

/** Every file in `dir` as [its path inside it, with forward slashes, the file]. */
const files = (dir) => [...walk(dir)].map((file) => [relative(dir, file).split(sep).join('/'), file]);

const TYPES = { webmanifest: 'application/manifest+json', png: 'image/png' };

/** @returns {import('vite').Plugin[]} */
export function pwa() {
  let publicDir = '';
  let appDir = '';
  return [
    {
      name: 'hallowed-lanterns:app-files-in-dev',
      apply: 'serve',
      configResolved(config) {
        appDir = join(config.root, 'pwa');
      },
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          const path = decodeURIComponent((req.url ?? '').split('?')[0]).replace(/^\/+/, '');
          const file = join(appDir, path);
          if (!path || path.includes('..') || !existsSync(file)) return next();
          res.setHeader('Content-Type', TYPES[path.split('.').pop()] ?? 'application/octet-stream');
          res.end(readFileSync(file));
        });
      },
    },
    {
      name: 'hallowed-lanterns:service-worker',
      apply: 'build',
      enforce: 'post',
      configResolved(config) {
        publicDir = config.publicDir;
        appDir = join(config.root, 'pwa');
      },
      generateBundle(_, bundle) {
        // The shell: the page and everything the build made (scripts, styles), cached on install.
        // Their names carry a hash, so a new version is a new set of names.
        const shell = ['./'];
        const contents = [];
        for (const name of Object.keys(bundle))
          if (name !== 'index.html' && !name.endsWith('.map')) shell.push(name);
        contents.push(String(bundle['index.html']?.source ?? ''));
        // The manifest and its icons join the build here (they aren't in public/), and the shell.
        for (const [path, file] of files(appDir)) {
          const data = readFileSync(file);
          this.emitFile({ type: 'asset', fileName: path, source: data });
          shell.push(path);
          contents.push(hash(data));
        }
        // public/ ships as it is. Its icons (the favicon, the iPhone's) join the shell; sounds and
        // models are cached as they're first played, each by the revision of its contents.
        const cached = {};
        for (const [path, file] of files(publicDir)) {
          const data = readFileSync(file);
          if (path.startsWith('icons/')) {
            shell.push(path);
            contents.push(hash(data));
          } else cached[path] = hash(data);
        }
        shell.sort();
        const version = hash(JSON.stringify([shell, contents, cached]));
        const template = readFileSync(new URL('./pwa-sw.js', import.meta.url), 'utf8');
        this.emitFile({
          type: 'asset',
          fileName: 'sw.js',
          source: template.replace('/* BUILD */ null', JSON.stringify({ version, shell, files: cached })),
        });
      },
    },
  ];
}
