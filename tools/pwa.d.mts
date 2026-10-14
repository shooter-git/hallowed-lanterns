import type { Plugin } from 'vite';

/** Writes the service worker into the build published on its own (see pwa.mjs). */
export function pwa(): Plugin;
