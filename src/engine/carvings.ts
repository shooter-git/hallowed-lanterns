import { CanvasTexture, LinearMipmapLinearFilter, LinearFilter, NoColorSpace } from 'three';

/**
 * Every carving design, drawn once at load time into one atlas (no image files to download):
 * 8 × 8 cells. Red is the cut itself, green a narrow blur of it (the cut wall), blue a wide blur
 * (candle light glowing through the thin skin around the cuts).
 */
export const CELLS = 8;
const CELL = 256;

/** Which atlas cells hold which kind of design. */
export const CARVE = {
  faces: [] as number[],
  happy: [] as number[],
  candles: [] as number[],
  stars: [] as number[],
  creatures: [] as number[],
  heartSkull: -1,
  /** Painted letters: m, s (the candy pumpkins). */
  letters: [] as number[],
  /** Rows of feather scallops (the owl's body). */
  feathers: -1,
  /** A carved rose, and a sugar skull with flowers (the guitar). */
  rose: -1,
  sugarSkull: -1,
  /** Two huge round owl eyes, painted. */
  owlEyes: -1,
};

type Ctx = CanvasRenderingContext2D;
type Draw = (c: Ctx, rnd: () => number) => void;

function rng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// --- shapes, in a 0–1 cell (y down, the top of the pumpkin at the top) ---

function poly(c: Ctx, pts: [number, number][]) {
  c.beginPath();
  pts.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y)));
  c.closePath();
  c.fill();
}

function triEye(c: Ctx, x: number, y: number, s: number, tilt: number, flip: boolean) {
  const t = flip ? -tilt : tilt;
  poly(c, [
    [x - s, y + s * 0.65 + t * s],
    [x + s, y + s * 0.65 - t * s],
    [x + (flip ? -0.15 : 0.15) * s, y - s * 0.75],
  ]);
}

function roundEye(c: Ctx, x: number, y: number, s: number, pupil: boolean) {
  c.beginPath();
  c.ellipse(x, y, s * 0.8, s, 0, 0, Math.PI * 2);
  c.fill();
  if (pupil) {
    c.save();
    c.fillStyle = '#000';
    c.strokeStyle = '#000';
    c.beginPath();
    c.arc(x + s * 0.2, y + s * 0.2, s * 0.32, 0, Math.PI * 2);
    c.fill();
    c.restore();
  }
}

function crescentEye(c: Ctx, x: number, y: number, s: number, up: boolean) {
  c.beginPath();
  c.ellipse(x, y, s * 1.1, s * 0.7, 0, up ? Math.PI : 0, up ? Math.PI * 2 : Math.PI);
  c.ellipse(x, y + (up ? 0.25 : -0.25) * s, s * 0.8, s * 0.35, 0, up ? Math.PI * 2 : Math.PI, up ? Math.PI : 0, true);
  c.closePath();
  c.fill();
}

function angryEye(c: Ctx, x: number, y: number, s: number, flip: boolean) {
  const f = flip ? -1 : 1;
  poly(c, [
    [x - s * f, y - s * 0.5],
    [x + s * f, y + s * 0.05],
    [x + s * 0.7 * f, y + s * 0.7],
    [x - s * 0.8 * f, y + s * 0.55],
  ]);
}

function heart(c: Ctx, x: number, y: number, s: number) {
  c.beginPath();
  c.moveTo(x, y + s * 0.85);
  c.bezierCurveTo(x - s * 1.4, y - s * 0.1, x - s * 0.7, y - s * 1.1, x, y - s * 0.35);
  c.bezierCurveTo(x + s * 0.7, y - s * 1.1, x + s * 1.4, y - s * 0.1, x, y + s * 0.85);
  c.fill();
}

function star(c: Ctx, x: number, y: number, r: number, rot: number, points = 5) {
  const pts: [number, number][] = [];
  for (let i = 0; i < points * 2; i++) {
    const a = rot + (i * Math.PI) / points - Math.PI / 2;
    const rr = i % 2 ? r * 0.45 : r;
    pts.push([x + Math.cos(a) * rr, y + Math.sin(a) * rr]);
  }
  poly(c, pts);
}

function triNose(c: Ctx, x: number, y: number, s: number) {
  poly(c, [
    [x - s * 0.6, y + s * 0.5],
    [x + s * 0.6, y + s * 0.5],
    [x, y - s * 0.55],
  ]);
}

/** A grin: an arc band with square teeth knocked out of it. */
function grin(c: Ctx, y: number, w: number, h: number, curve: number, teeth: number, rnd: () => number) {
  const x0 = 0.5 - w / 2;
  const top = (t: number) => y - curve * Math.sin(Math.PI * t) * 0.6 + (t - 0.5) ** 2 * curve * 0.3;
  const bot = (t: number) => y + h - curve * Math.sin(Math.PI * t) * 0.05 + h * Math.sin(Math.PI * t) * 0.9;
  c.beginPath();
  for (let i = 0; i <= 24; i++) {
    const t = i / 24;
    const px = x0 + w * t;
    i ? c.lineTo(px, top(t)) : c.moveTo(px, top(t));
  }
  for (let i = 24; i >= 0; i--) {
    const t = i / 24;
    c.lineTo(x0 + w * t, bot(t));
  }
  c.closePath();
  c.fill();
  if (!teeth) return;
  c.save();
  c.fillStyle = '#000';
  c.strokeStyle = '#000';
  for (let i = 0; i < teeth; i++) {
    const t = (i + 0.5 + (rnd() - 0.5) * 0.3) / teeth;
    const px = x0 + w * t;
    const tw = (w / teeth) * 0.38;
    const fromTop = i % 2 === 0;
    const ty = fromTop ? top(t) - 0.02 : bot(t) - h * 0.55;
    c.fillRect(px - tw / 2, ty, tw, h * 0.55 + 0.02);
  }
  c.restore();
}

function zigzag(c: Ctx, y: number, w: number, h: number, n: number) {
  const x0 = 0.5 - w / 2;
  c.beginPath();
  c.moveTo(x0, y);
  for (let i = 0; i <= n; i++) {
    const px = x0 + (w * i) / n;
    c.lineTo(px, y + (i % 2 ? h * 0.55 : 0) - Math.sin((Math.PI * i) / n) * h * 0.25);
  }
  for (let i = n; i >= 0; i--) {
    const px = x0 + (w * i) / n;
    c.lineTo(px, y + h + (i % 2 ? 0 : h * 0.45) - Math.sin((Math.PI * i) / n) * h * 0.15);
  }
  c.closePath();
  c.fill();
}

function oMouth(c: Ctx, y: number, s: number) {
  c.beginPath();
  c.ellipse(0.5, y, s * 0.7, s, 0, 0, Math.PI * 2);
  c.fill();
}

function fangs(c: Ctx, y: number, w: number) {
  const x0 = 0.5 - w / 2;
  c.beginPath();
  c.moveTo(x0, y);
  c.quadraticCurveTo(0.5, y + 0.16, x0 + w, y);
  c.lineTo(x0 + w * 0.75, y + 0.035);
  c.lineTo(x0 + w * 0.7, y + 0.11);
  c.lineTo(x0 + w * 0.64, y + 0.06);
  c.lineTo(x0 + w * 0.36, y + 0.06);
  c.lineTo(x0 + w * 0.3, y + 0.11);
  c.lineTo(x0 + w * 0.25, y + 0.035);
  c.closePath();
  c.fill();
}

function candle(c: Ctx, x: number, base: number, w: number, h: number, rnd: () => number) {
  const top = base - h;
  c.beginPath();
  c.moveTo(x - w / 2, base);
  c.lineTo(x - w / 2, top + 0.02);
  // Wax drips down the front.
  const drips = 2 + Math.floor(rnd() * 2);
  for (let i = 0; i <= drips * 2; i++) {
    const t = i / (drips * 2);
    const px = x - w / 2 + w * t;
    const dy = i % 2 ? 0.03 + rnd() * 0.05 : 0;
    c.lineTo(px, top + dy);
  }
  c.lineTo(x + w / 2, base);
  c.closePath();
  c.fill();
  // The flame: a teardrop above a gap (the wick stays uncut).
  const fh = w * (1.3 + rnd() * 0.4);
  const fy = top - 0.03;
  c.beginPath();
  c.moveTo(x, fy - fh);
  c.bezierCurveTo(x + w * 0.45, fy - fh * 0.45, x + w * 0.35, fy, x, fy);
  c.bezierCurveTo(x - w * 0.35, fy, x - w * 0.45, fy - fh * 0.45, x, fy - fh);
  c.fill();
}

function crescentMoon(c: Ctx, x: number, y: number, r: number) {
  c.beginPath();
  c.arc(x, y, r, 0, Math.PI * 2);
  c.fill();
  c.save();
  c.fillStyle = '#000';
  c.strokeStyle = '#000';
  c.beginPath();
  c.arc(x + r * 0.45, y - r * 0.2, r * 0.85, 0, Math.PI * 2);
  c.fill();
  c.restore();
}

function bat(c: Ctx, x: number, y: number, s: number) {
  c.beginPath();
  c.moveTo(x, y - s * 0.15);
  c.quadraticCurveTo(x - s * 0.4, y - s * 0.55, x - s, y - s * 0.3);
  c.quadraticCurveTo(x - s * 0.8, y, x - s * 0.95, y + s * 0.2);
  c.quadraticCurveTo(x - s * 0.7, y + s * 0.05, x - s * 0.55, y + s * 0.25);
  c.quadraticCurveTo(x - s * 0.35, y + s * 0.1, x - s * 0.2, y + s * 0.3);
  c.lineTo(x, y + s * 0.15);
  c.lineTo(x + s * 0.2, y + s * 0.3);
  c.quadraticCurveTo(x + s * 0.35, y + s * 0.1, x + s * 0.55, y + s * 0.25);
  c.quadraticCurveTo(x + s * 0.7, y + s * 0.05, x + s * 0.95, y + s * 0.2);
  c.quadraticCurveTo(x + s * 0.8, y, x + s, y - s * 0.3);
  c.quadraticCurveTo(x + s * 0.4, y - s * 0.55, x, y - s * 0.15);
  c.fill();
  // Ears.
  poly(c, [
    [x - s * 0.12, y - s * 0.1],
    [x - s * 0.1, y - s * 0.35],
    [x - s * 0.02, y - s * 0.15],
  ]);
  poly(c, [
    [x + s * 0.12, y - s * 0.1],
    [x + s * 0.1, y - s * 0.35],
    [x + s * 0.02, y - s * 0.15],
  ]);
}

function owl(c: Ctx, x: number, y: number, s: number) {
  // Body
  c.beginPath();
  c.ellipse(x, y + s * 0.15, s * 0.55, s * 0.75, 0, 0, Math.PI * 2);
  c.fill();
  // Ear tufts
  poly(c, [
    [x - s * 0.5, y - s * 0.35],
    [x - s * 0.45, y - s * 0.8],
    [x - s * 0.15, y - s * 0.45],
  ]);
  poly(c, [
    [x + s * 0.5, y - s * 0.35],
    [x + s * 0.45, y - s * 0.8],
    [x + s * 0.15, y - s * 0.45],
  ]);
  c.save();
  c.fillStyle = '#000';
  c.strokeStyle = '#000';
  // Eyes and beak left uncut, belly feathers as small chevrons.
  for (const dx of [-0.22, 0.22]) {
    c.beginPath();
    c.arc(x + dx * s, y - s * 0.1, s * 0.17, 0, Math.PI * 2);
    c.fill();
  }
  poly(c, [
    [x - s * 0.07, y + s * 0.05],
    [x + s * 0.07, y + s * 0.05],
    [x, y + s * 0.2],
  ]);
  c.lineWidth = s * 0.06;
  for (let r = 0; r < 3; r++) {
    for (let i = -1; i <= 1; i++) {
      const cx = x + i * s * 0.2 + (r % 2) * s * 0.1;
      const cy = y + s * (0.42 + r * 0.16);
      c.beginPath();
      c.moveTo(cx - s * 0.07, cy - s * 0.04);
      c.lineTo(cx, cy + s * 0.03);
      c.lineTo(cx + s * 0.07, cy - s * 0.04);
      c.stroke();
    }
  }
  c.restore();
  c.beginPath();
  c.arc(x - 0.22 * s + s * 0.03, y - s * 0.1, s * 0.07, 0, Math.PI * 2);
  c.arc(x + 0.22 * s + s * 0.03, y - s * 0.1, s * 0.07, 0, Math.PI * 2);
  c.fill();
}

function ghost(c: Ctx, x: number, y: number, s: number) {
  c.beginPath();
  c.moveTo(x - s * 0.5, y + s * 0.7);
  c.lineTo(x - s * 0.5, y - s * 0.1);
  c.arc(x, y - s * 0.1, s * 0.5, Math.PI, 0);
  c.lineTo(x + s * 0.5, y + s * 0.7);
  for (let i = 0; i < 4; i++) {
    const x1 = x + s * 0.5 - (i + 0.5) * (s / 4);
    c.quadraticCurveTo(x1, y + s * (i % 2 ? 0.85 : 0.5), x1 - s / 8, y + s * 0.7);
  }
  c.closePath();
  c.fill();
  c.save();
  c.fillStyle = '#000';
  c.strokeStyle = '#000';
  c.beginPath();
  c.ellipse(x - s * 0.18, y - s * 0.12, s * 0.08, s * 0.13, 0, 0, Math.PI * 2);
  c.ellipse(x + s * 0.18, y - s * 0.12, s * 0.08, s * 0.13, 0, 0, Math.PI * 2);
  c.fill();
  c.beginPath();
  c.ellipse(x, y + s * 0.18, s * 0.1, s * 0.14, 0, 0, Math.PI * 2);
  c.fill();
  c.restore();
}

function cat(c: Ctx, x: number, y: number, s: number) {
  c.beginPath();
  // Arched-back cat, sitting.
  c.moveTo(x - s * 0.55, y + s * 0.6);
  c.quadraticCurveTo(x - s * 0.7, y - s * 0.1, x - s * 0.25, y - s * 0.25);
  c.lineTo(x - s * 0.3, y - s * 0.55);
  c.lineTo(x - s * 0.1, y - s * 0.35);
  c.lineTo(x + s * 0.1, y - s * 0.35);
  c.lineTo(x + s * 0.3, y - s * 0.55);
  c.lineTo(x + s * 0.25, y - s * 0.2);
  c.quadraticCurveTo(x + s * 0.55, y + s * 0.1, x + s * 0.45, y + s * 0.6);
  c.closePath();
  c.fill();
  // Tail curling up.
  c.lineWidth = s * 0.1;
  c.strokeStyle = '#fff';
  c.beginPath();
  c.moveTo(x + s * 0.4, y + s * 0.55);
  c.quadraticCurveTo(x + s * 0.85, y + s * 0.5, x + s * 0.75, y + s * 0.05);
  c.stroke();
  c.save();
  c.fillStyle = '#000';
  c.strokeStyle = '#000';
  for (const dx of [-0.13, 0.13]) {
    c.beginPath();
    c.ellipse(x + dx * s, y - s * 0.12, s * 0.06, s * 0.035, dx > 0 ? -0.3 : 0.3, 0, Math.PI * 2);
    c.fill();
  }
  c.restore();
}

function skull(c: Ctx, rnd: () => number) {
  void rnd;
  c.beginPath();
  c.ellipse(0.5, 0.42, 0.3, 0.27, 0, 0, Math.PI * 2);
  c.fill();
  c.fillRect(0.34, 0.5, 0.32, 0.2);
  c.save();
  c.fillStyle = '#000';
  c.strokeStyle = '#000';
  heart(c, 0.38, 0.42, 0.075);
  heart(c, 0.62, 0.42, 0.075);
  triNose(c, 0.5, 0.545, 0.05);
  for (let i = 0; i < 5; i++) c.fillRect(0.375 + i * 0.058, 0.62, 0.012, 0.09);
  c.restore();
}

// --- whole designs ---

function face(kind: number): Draw {
  return (c, rnd) => {
    const ey = 0.38 + rnd() * 0.05;
    const ex = 0.17 + rnd() * 0.05;
    const es = 0.075 + rnd() * 0.035;
    const eyes = kind % 6;
    const mouths = Math.floor(kind / 6) % 6;
    const tilt = rnd() * 0.5;
    if (eyes === 0) {
      triEye(c, 0.5 - ex, ey, es, tilt, false);
      triEye(c, 0.5 + ex, ey, es, tilt, true);
    } else if (eyes === 1) {
      roundEye(c, 0.5 - ex, ey, es * 0.9, rnd() > 0.5);
      roundEye(c, 0.5 + ex, ey, es * 0.9, rnd() > 0.5);
    } else if (eyes === 2) {
      crescentEye(c, 0.5 - ex, ey, es, true);
      crescentEye(c, 0.5 + ex, ey, es, true);
    } else if (eyes === 3) {
      angryEye(c, 0.5 - ex, ey, es, false);
      angryEye(c, 0.5 + ex, ey, es, true);
    } else if (eyes === 4) {
      // One big, one small — a wink or a squint.
      triEye(c, 0.5 - ex, ey, es * 1.2, 0, false);
      c.fillRect(0.5 + ex - es, ey - 0.01, es * 2, 0.03);
    } else {
      star(c, 0.5 - ex, ey, es * 1.1, rnd(), 5);
      star(c, 0.5 + ex, ey, es * 1.1, rnd(), 5);
    }
    if (rnd() > 0.35) triNose(c, 0.5, 0.52, 0.04 + rnd() * 0.02);
    const my = 0.6 + rnd() * 0.04;
    if (mouths === 0) grin(c, my, 0.48, 0.09, 0.05, 3 + Math.floor(rnd() * 3), rnd);
    else if (mouths === 1) zigzag(c, my, 0.46, 0.08, 6 + Math.floor(rnd() * 4));
    else if (mouths === 2) oMouth(c, my + 0.05, 0.07);
    else if (mouths === 3) fangs(c, my, 0.42);
    else if (mouths === 4) grin(c, my, 0.36, 0.06, 0.07, 0, rnd);
    else grin(c, my - 0.02, 0.52, 0.12, 0.09, 2, rnd);
  };
}

/** Big friendly smiles: what a lantern switches to when you tap it. */
function happy(kind: number): Draw {
  return (c, rnd) => {
    crescentEye(c, 0.33, 0.4, 0.085, true);
    crescentEye(c, 0.67, 0.4, 0.085, true);
    if (kind === 1) {
      heart(c, 0.5, 0.52, 0.035);
    }
    grin(c, 0.58, 0.54, 0.14, 0.1, kind === 2 ? 0 : 2, rnd);
  };
}

function candles(n: number): Draw {
  return (c, rnd) => {
    const base = 0.86;
    const xs = n === 1 ? [0.5] : n === 2 ? [0.4, 0.62] : [0.3, 0.5, 0.7];
    xs.forEach((x, i) => {
      const h = 0.25 + rnd() * 0.25 + (i === 1 ? 0.08 : 0);
      candle(c, x + (rnd() - 0.5) * 0.04, base - rnd() * 0.06, 0.1 + rnd() * 0.04, h, rnd);
    });
  };
}

function stars(kind: number): Draw {
  return (c, rnd) => {
    if (kind % 2 === 0) crescentMoon(c, 0.35 + rnd() * 0.1, 0.35, 0.12);
    const count = 4 + Math.floor(rnd() * 5);
    for (let i = 0; i < count; i++) {
      star(c, 0.18 + rnd() * 0.64, 0.18 + rnd() * 0.64, 0.035 + rnd() * 0.05, rnd() * 3);
    }
  };
}

const creatures: Draw[] = [
  (c) => bat(c, 0.5, 0.48, 0.32),
  (c) => owl(c, 0.5, 0.45, 0.3),
  (c) => ghost(c, 0.5, 0.42, 0.42),
  (c) => cat(c, 0.48, 0.48, 0.38),
  (c, rnd) => {
    bat(c, 0.35, 0.35, 0.18);
    bat(c, 0.65, 0.55, 0.15);
    star(c, 0.7, 0.28, 0.05, rnd());
  },
  (c) => {
    // A spider on its thread, and a web corner.
    c.lineWidth = 0.018;
    c.strokeStyle = '#fff';
    c.beginPath();
    c.moveTo(0.5, 0.12);
    c.lineTo(0.5, 0.46);
    c.stroke();
    c.beginPath();
    c.ellipse(0.5, 0.56, 0.09, 0.11, 0, 0, Math.PI * 2);
    c.fill();
    c.beginPath();
    c.arc(0.5, 0.45, 0.055, 0, Math.PI * 2);
    c.fill();
    c.lineWidth = 0.02;
    for (const s of [-1, 1]) {
      for (let i = 0; i < 4; i++) {
        c.beginPath();
        c.moveTo(0.5 + s * 0.06, 0.5 + i * 0.035);
        c.quadraticCurveTo(0.5 + s * 0.2, 0.42 + i * 0.07, 0.5 + s * (0.24 + i * 0.01), 0.55 + i * 0.07);
        c.stroke();
      }
    }
  },
];

/** Draws the atlas. Takes ~50 ms. */
export function buildCarvingAtlas(): CanvasTexture {
  const size = CELL * CELLS;
  const sharp = document.createElement('canvas');
  sharp.width = sharp.height = size;
  const c = sharp.getContext('2d') as Ctx;
  c.fillStyle = '#000';
  c.fillRect(0, 0, size, size);
  c.fillStyle = '#fff';
  c.strokeStyle = '#fff';
  c.lineJoin = 'round';
  c.lineCap = 'round';

  const designs: { draw: Draw; list: number[] | string }[] = [];
  for (let i = 0; i < 26; i++) designs.push({ draw: face(i + Math.floor(i / 6)), list: CARVE.faces });
  for (let i = 0; i < 3; i++) designs.push({ draw: happy(i), list: CARVE.happy });
  for (let i = 0; i < 12; i++) designs.push({ draw: candles(1 + (i % 3)), list: CARVE.candles });
  for (let i = 0; i < 8; i++) designs.push({ draw: stars(i), list: CARVE.stars });
  for (let i = 0; i < creatures.length; i++)
    designs.push({ draw: creatures[i] as Draw, list: CARVE.creatures });
  designs.push({ draw: skull, list: 'skull' });
  for (const ch of ['m', 's']) {
    designs.push({
      draw: (c) => {
        c.save();
        // Text at real pixel size (tiny fonts under a big scale don't render everywhere).
        c.scale(1 / CELL, 1 / CELL);
        c.font = 'bold 170px "Arial Rounded MT Bold", "Nunito", "Helvetica Neue", Arial, sans-serif';
        c.textAlign = 'center';
        c.textBaseline = 'middle';
        c.fillText(ch, CELL / 2, CELL * 0.47);
        c.restore();
      },
      list: CARVE.letters,
    });
  }

  const special: Record<string, Draw> = {
    feathers: (c) => {
      c.lineWidth = 0.045;
      c.strokeStyle = '#fff';
      for (let r = 0; r < 4; r++) {
        for (let k = 0; k < 3; k++) {
          const x = 0.22 + k * 0.28 + (r % 2) * 0.14 - 0.07;
          const y = 0.22 + r * 0.19;
          c.beginPath();
          c.arc(x, y, 0.1, 0.15 * Math.PI, 0.85 * Math.PI);
          c.stroke();
        }
      }
    },
    rose: (c) => {
      c.lineWidth = 0.035;
      c.strokeStyle = '#fff';
      for (let k = 0; k < 4; k++) {
        c.beginPath();
        c.arc(0.5, 0.42, 0.05 + k * 0.05, Math.PI * (0.1 + k * 0.4), Math.PI * (1.3 + k * 0.4));
        c.stroke();
      }
      c.beginPath();
      c.moveTo(0.5, 0.62);
      c.quadraticCurveTo(0.46, 0.75, 0.5, 0.88);
      c.stroke();
      for (const s2 of [-1, 1]) {
        c.beginPath();
        c.ellipse(0.5 + s2 * 0.1, 0.74, 0.08, 0.035, s2 * 0.5, 0, Math.PI * 2);
        c.fill();
      }
    },
    sugarSkull: (c, rnd) => {
      skull(c, rnd);
      c.save();
      c.fillStyle = '#fff';
      for (const [x, y] of [
        [0.3, 0.22],
        [0.5, 0.17],
        [0.7, 0.22],
      ] as [number, number][]) {
        for (let k = 0; k < 6; k++) {
          const a = (k * Math.PI) / 3;
          c.beginPath();
          c.ellipse(x + Math.cos(a) * 0.035, y + Math.sin(a) * 0.035, 0.03, 0.018, a, 0, Math.PI * 2);
          c.fill();
        }
      }
      c.restore();
    },
    owlEyes: (c) => {
      for (const x of [0.31, 0.69]) {
        c.beginPath();
        c.arc(x, 0.44, 0.19, 0, Math.PI * 2);
        c.fill();
      }
    },
  };
  for (const [name, draw] of Object.entries(special)) designs.push({ draw, list: name as 'skull' });

  designs.forEach((d, i) => {
    const cx = i % CELLS;
    const cy = Math.floor(i / CELLS);
    c.save();
    c.translate(cx * CELL, cy * CELL);
    c.scale(CELL, CELL);
    c.beginPath();
    c.rect(0, 0, 1, 1);
    c.clip();
    d.draw(c, rng(i * 7919 + 13));
    c.restore();
    if (typeof d.list === 'string') {
      if (d.list === 'skull') CARVE.heartSkull = i;
      else (CARVE as unknown as Record<string, number>)[d.list] = i;
    } else d.list.push(i);
  });

  // Blurs by shrinking and growing the picture (works everywhere, unlike canvas filters).
  const blur = (factor: number, passes: number) => {
    const small = document.createElement('canvas');
    small.width = small.height = size / factor;
    const sc = small.getContext('2d') as Ctx;
    const out = document.createElement('canvas');
    out.width = out.height = size;
    const oc = out.getContext('2d') as Ctx;
    oc.drawImage(sharp, 0, 0);
    for (let p = 0; p < passes; p++) {
      sc.imageSmoothingQuality = 'high';
      sc.clearRect(0, 0, small.width, small.height);
      sc.drawImage(out, 0, 0, small.width, small.height);
      oc.imageSmoothingQuality = 'high';
      oc.clearRect(0, 0, size, size);
      oc.drawImage(small, 0, 0, size, size);
    }
    return oc.getImageData(0, 0, size, size).data;
  };
  const narrow = blur(4, 2);
  const wide = blur(16, 2);
  const img = c.getImageData(0, 0, size, size);
  const px = img.data;
  for (let i = 0; i < px.length; i += 4) {
    px[i + 1] = narrow[i] as number;
    px[i + 2] = wide[i] as number;
    px[i + 3] = 255;
  }
  c.putImageData(img, 0, 0);

  const tex = new CanvasTexture(sharp);
  tex.colorSpace = NoColorSpace;
  tex.minFilter = LinearMipmapLinearFilter;
  tex.magFilter = LinearFilter;
  tex.anisotropy = 4;
  tex.generateMipmaps = true;
  return tex;
}
