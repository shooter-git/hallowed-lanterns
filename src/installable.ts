/**
 * Hallowed Lanterns as an app of its own: opened straight from its address (GitHub Pages), it can
 * be added to a home screen, opens full screen with its own icon (filling the whole screen on an
 * iPhone too), and plays offline once the night has been walked. Inside All the Spaces it's a
 * sealed frame with an opaque origin, where the frame's policy would block the manifest (and fail
 * the checks) and service workers can't exist, so there it does nothing at all.
 */
export function makeInstallable() {
  if (window.top !== window || window.origin === 'null') return;
  fitHomeScreen();
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

/**
 * An iPhone home-screen bug: with the see-through status bar, the page is laid out as if the
 * screen were shorter by the status bar's height, which leaves an empty band at the bottom. When
 * that's happening, everything that sizes itself by the window (the SDK's canvas and camera, taps)
 * is told the screen's real height, and the CSS (html.hl-ios-app) stretches the layers to it.
 */
function fitHomeScreen() {
  if (!(navigator as Navigator & { standalone?: boolean }).standalone) return;
  const root = document.documentElement;
  const real = () => {
    const portrait = matchMedia('(orientation: portrait)').matches;
    const short = Math.min(screen.width, screen.height);
    const long = Math.max(screen.width, screen.height);
    const width = portrait ? short : long;
    const height = portrait ? long : short;
    const gap = height - root.clientHeight;
    // Only when it fills the screen's width and the band is a status bar's worth.
    return Math.abs(root.clientWidth - width) < 2 && gap > 0 && gap <= 70 ? height : 0;
  };
  Object.defineProperty(window, 'innerHeight', {
    configurable: true,
    get: () => real() || root.clientHeight,
  });
  const fit = () => {
    const height = real();
    root.classList.toggle('hl-ios-app', height > 0);
    root.style.setProperty('--hl-app-h', height ? `${height}px` : '100%');
  };
  fit();
  addEventListener('resize', fit);
  addEventListener('orientationchange', () => {
    setTimeout(fit, 60);
    setTimeout(fit, 400);
  });
}
