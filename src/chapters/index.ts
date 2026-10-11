import type { ChapterInfo } from './types.ts';

/** The night, in order. Each chapter's code loads only when it's needed. */
export const CHAPTERS: ChapterInfo[] = [
  {
    id: 'arbor',
    numeral: 'I',
    name: 'The Arbor of Faces',
    subtitle: 'Sunset, and the lanterns are waking',
    load: () => import('./arbor.ts'),
  },
  {
    id: 'grove',
    numeral: 'II',
    name: 'The Candle Grove',
    subtitle: 'Blue hour, and something is hiding',
    load: () => import('./grove.ts'),
  },
  {
    id: 'garden',
    numeral: 'III',
    name: 'The Lantern Garden',
    subtitle: 'Nightfall, under a sky of lanterns',
    load: () => import('./garden.ts'),
  },
  {
    id: 'pasture',
    numeral: 'IV',
    name: 'The Pasture of Giants',
    subtitle: 'Deep night, and something enormous is breathing',
    load: () => import('./pasture.ts'),
  },
];
