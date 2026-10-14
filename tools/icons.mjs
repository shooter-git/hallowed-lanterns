// The app's icons are the night's first sight: the Arbor of Faces at sunset, its lanterns lit,
// looking down the lane, as the engine draws it.
//
//   node tools/icons.mjs [projectDir]
//     Crops and grades tools/icons/arbor-at-sunset.png into public/icons/: the home-screen icons
//     (iPhone, Android, Android's maskable), the ones for installing on a computer, and the
//     favicon. Needs ImageMagick (`convert`).
//
//   node tools/icons.mjs --capture [projectDir]
//     Draws that frame again first, from the dev server (`pnpm dev`, on http://localhost:5199 by
//     default, or HL_URL), with the lanterns woken. Needs Playwright (its path in PLAYWRIGHT if
//     it isn't installed here). Without a graphics card it draws in software, which takes a few
//     minutes, and at the mid tier: the high one comes out black.
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const args = process.argv.slice(2);
const capture = args.includes('--capture');
const root = resolve(args.find((a) => !a.startsWith('--')) ?? process.cwd());
const frame = join(root, 'tools/icons/arbor-at-sunset.png');
const out = join(root, 'public/icons');
mkdirSync(out, { recursive: true });

if (capture) {
  const where = process.env.PLAYWRIGHT ?? 'playwright';
  const { chromium } = await import(where.startsWith('/') ? pathToFileURL(where).href : where);
  const browser = await chromium.launch({
    args: ['--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--ignore-gpu-blocklist'],
  });
  const page = await browser.newPage({ viewport: { width: 800, height: 800 } });
  // At the mouth of the lane, on its middle line, looking down it.
  await page.goto(`${process.env.HL_URL ?? 'http://localhost:5199'}/?tier=mid&chapter=0&at=24`);
  await page.waitForFunction(() => window.hl?.chapter, null, { timeout: 300_000 });
  await page.waitForTimeout(20_000);
  await page.evaluate(() => {
    const hl = window.hl;
    // Full resolution however slowly it draws, and twenty seconds on: the wave has woken them all.
    hl.stage.resolution.scale = 1;
    hl.stage.resolution.frame = () => false;
    window.dispatchEvent(new Event('resize'));
    for (let i = 0; i < 80; i++) hl.chapter.update(0.25);
  });
  await page.addStyleTag({ content: '.hl-ui, [class^="ats-"], [class*=" ats-"] { display: none !important; }' });
  await page.waitForTimeout(30_000);
  mkdirSync(join(root, 'tools/icons'), { recursive: true });
  await page.screenshot({ path: frame, timeout: 1_500_000 });
  await browser.close();
  console.log(`frame drawn to ${frame}`);
}

const magick = (...a) => execFileSync('convert', a.flat(Infinity));

/**
 * The frame cropped to a square around the end of the lane (`share` of the frame's width), a
 * little warmer, with the edges softly darkened to draw the eye down the lane.
 */
function square(size, share) {
  const crop = Math.round(800 * share);
  const at = Math.round((800 - crop) / 2);
  return [
    frame,
    ['-crop', `${crop}x${crop}+${at}+${at}`, '+repage', '-filter', 'Lanczos', '-resize', `${size}x${size}`],
    ['-modulate', '100,108,100'],
    ['(', '-size', `${size}x${size}`, 'radial-gradient:white-#9a8f99', ')', '-compose', 'multiply', '-composite'],
  ];
}

/** Rounded corners (a radius of 22.5%) with clear corners, for icons shown as they are. */
const rounded = (size) => [
  ['(', '-size', `${size}x${size}`, 'xc:none', '-fill', 'white'],
  ['-draw', `roundrectangle 0,0,${size - 1},${size - 1},${size * 0.225},${size * 0.225}`, ')'],
  ['-compose', 'DstIn', '-composite'],
];

const write = (name) => ['-strip', join(out, name)];

// Shown as they are (installing on a computer, the browser's own lists): rounded.
for (const size of [192, 512]) magick(square(size, 0.875), rounded(size), write(`icon-${size}.png`));
// Shaped by the device: the iPhone rounds the corners itself, and Android cuts its mask from the
// middle 80%, where the lane and its lanterns are.
magick(square(180, 0.875), write('apple-touch-icon.png'));
magick(square(512, 0.875), write('icon-maskable-512.png'));
// The favicon is closer in, so the lit lanterns still read at 32 px.
magick(square(32, 0.66), rounded(32), write('favicon-32.png'));
console.log(`icons written to ${out}`);
