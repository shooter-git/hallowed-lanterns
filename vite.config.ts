import { defineConfig } from 'vite';
import { pwa } from './tools/pwa.mjs';

// Creations are served from their own sealed address, so:
// - every path is relative (the creation doesn't know its address in advance),
// - no inline scripts (the frame's security policy forbids them).
// All the Spaces builds with its own settings and ignores this file, so `pwa()` (the service
// worker) is only in `pnpm build`: the app published on its own, to GitHub Pages.
export default defineConfig({
  base: './',
  plugins: [pwa()],
  build: {
    target: 'es2022',
    modulePreload: { polyfill: false },
    assetsInlineLimit: 0,
    // three.js alone is ~600 KB (≈150 KB compressed); the creation budget is far larger.
    chunkSizeWarningLimit: 1500,
  },
});
