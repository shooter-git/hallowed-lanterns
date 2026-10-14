// Hallowed Lanterns offline, opened on its own (GitHub Pages). tools/pwa.mjs writes this into the
// published build as sw.js and fills in BUILD; All the Spaces builds without it and never sees it.
//
// - The shell (the page, every script and stylesheet, the icons) is cached when this version
//   installs, so the whole night's code is there offline from the first visit.
// - Sounds and models are cached as each chapter first loads them, then served from the cache.
//   Each carries the revision it was cached at, so one that changes in a later version is fetched
//   again and the rest stay put.
// - A new version waits until the old one isn't open anywhere, then takes over on the next launch:
//   a night half-walked never has its files swapped underneath it.
const BUILD = /* BUILD */ null;
const SHELL = `hl-shell-${BUILD.version}`;
const FILES = 'hl-files';
const REV = 'x-hl-revision';

const at = (path) => new URL(path, self.registration.scope).href;
const shell = new Set(BUILD.shell.map(at));
const files = new Map(Object.entries(BUILD.files).map(([path, rev]) => [at(path), rev]));

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(SHELL)
      .then((cache) => cache.addAll([...shell].map((url) => new Request(url, { cache: 'reload' })))),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      for (const name of await caches.keys())
        if (name.startsWith('hl-shell-') && name !== SHELL) await caches.delete(name);
      // Let go of the sounds and models this version no longer has, or has changed.
      const cache = await caches.open(FILES);
      for (const request of await cache.keys()) {
        const cached = await cache.match(request);
        if (files.get(request.url) !== cached?.headers.get(REV)) await cache.delete(request);
      }
      // The first visit's page starts caching as it plays, without waiting for a reload.
      await self.clients.claim();
    })(),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  url.search = '';
  url.hash = '';
  // Any page in scope (`?chapter=3` too) is the one page.
  if (request.mode === 'navigate') return event.respondWith(fromShell(at('./'), request));
  if (shell.has(url.href)) return event.respondWith(fromShell(url.href, request));
  const rev = files.get(url.href);
  if (rev) event.respondWith(fromFiles(event, url.href, rev));
});

async function fromShell(url, request) {
  return (await caches.match(url, { cacheName: SHELL })) ?? fetch(request);
}

async function fromFiles(event, url, rev) {
  const cache = await caches.open(FILES);
  const cached = await cache.match(url);
  if (cached && cached.headers.get(REV) === rev) return cached;
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) return response;
  const body = await response.blob();
  const headers = new Headers(response.headers);
  headers.set(REV, rev);
  headers.delete('content-encoding');
  headers.delete('content-length');
  const init = { status: response.status, statusText: response.statusText, headers };
  // Out of room: it still plays, from the network.
  event.waitUntil(cache.put(url, new Response(body, init)).catch(() => {}));
  return new Response(body, init);
}
