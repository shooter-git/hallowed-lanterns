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
];
