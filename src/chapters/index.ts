import type { ChapterInfo } from './types.ts';

/** The night, in order. Each chapter's code loads only when it's needed. */
export const CHAPTERS: ChapterInfo[] = [
  {
    id: 'arbor',
    numeral: 'I',
    name: 'The Arbor of Faces',
    subtitle: 'Sunset, and the lanterns are waking',
    key: 'b',
    load: () => import('./arbor.ts'),
  },
  {
    id: 'grove',
    numeral: 'II',
    name: 'The Candle Grove',
    subtitle: 'Blue hour, and something is hiding',
    key: 'b',
    load: () => import('./grove.ts'),
  },
  {
    id: 'garden',
    numeral: 'III',
    name: 'The Lantern Garden',
    subtitle: 'Nightfall, under a sky of lanterns',
    key: 'g',
    load: () => import('./garden.ts'),
  },
  {
    id: 'pasture',
    numeral: 'IV',
    name: 'The Pasture of Giants',
    subtitle: 'Deep night, and something enormous is breathing',
    key: 'd',
    load: () => import('./pasture.ts'),
  },
  {
    id: 'hollow',
    numeral: 'V',
    name: 'Sweet Hollow',
    subtitle: 'Where the candy grows',
    key: 'd',
    load: () => import('./hollow.ts'),
  },
  {
    id: 'snow',
    numeral: 'VI',
    name: 'October Snow',
    subtitle: 'Then, impossibly, it begins to snow',
    key: 'a',
    load: () => import('./snow.ts'),
  },
  {
    id: 'deep',
    numeral: 'VII',
    name: 'The Deep',
    subtitle: 'Where the lanterns swim',
    key: 'fs',
    load: () => import('./deep.ts'),
  },
  {
    id: 'marigold',
    numeral: 'VIII',
    name: 'The Marigold Garden',
    subtitle: 'Remember, and make a wish',
    key: 'g',
    load: () => import('./marigold.ts'),
  },
];
