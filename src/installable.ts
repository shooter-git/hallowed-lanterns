/**
 * Hallowed Lanterns as an app of its own: opened straight from its address (GitHub Pages), it can
 * be added to a home screen, opens full screen with its own icon, and plays offline once the night
 * has been walked. Inside All the Spaces it's a sealed frame with an opaque origin, where the
 * frame's policy would block the manifest (and fail the checks) and service workers can't exist,
 * so there it does nothing at all.
 */
export function makeInstallable() {
  if (window.top !== window || window.origin === 'null') return;
  const manifest = document.createElement('link');
  manifest.rel = 'manifest';
  manifest.href = './manifest.webmanifest';
  document.head.append(manifest);
  // The service worker is made by the published build only (tools/pwa.mjs), never by `pnpm dev`.
  if (!import.meta.env.PROD) return;
  try {
    navigator.serviceWorker?.register('./sw.js').catch(() => {});
  } catch {
    // Not allowed here (a private window, say): it still plays, just not offline.
  }
  // Once installed, ask the browser to keep the cached night rather than clear it to make room.
  if (matchMedia('(display-mode: standalone), (display-mode: fullscreen)').matches)
    navigator.storage?.persist?.().catch(() => {});
}
