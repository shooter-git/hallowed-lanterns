import { SLIDER_DEFAULT } from './audio.ts';

/** The settings' two sound levels, 0-100 (SLIDER_DEFAULT is the mix as made). */
export type SoundSettings = {
  music: number;
  sounds: number;
};

type ChapterEntry = { numeral: string; name: string; reached: boolean; go: () => void };

/**
 * Everything drawn over the world: the title, chapter cards, story lines, hints and the two
 * controls (walk with me, chapters). The app's own menu button lives in the top-left corner,
 * so nothing goes there. The chapters menu also holds the settings (the sound levels).
 */
const TITLE_HEADING = `
        <p class="hl-kicker">One October night at the pumpkin patch</p>
        <h1>Hallowed Lanterns</h1>`;

export class UI {
  readonly root = document.createElement('div');
  private readonly title = document.createElement('div');
  private readonly card = document.createElement('div');
  private readonly line = document.createElement('p');
  private readonly hint = document.createElement('p');
  private readonly controls = document.createElement('div');
  readonly walkButton = document.createElement('button');
  private readonly offers = new Set<HTMLButtonElement>();
  private waiting: { text: string; seconds: number } | null = null;
  readonly menuButton = document.createElement('button');
  private idleWatched = false;
  private readonly menu = document.createElement('div');
  private chapters: ChapterEntry[] = [];
  private sound: SoundSettings = { music: SLIDER_DEFAULT, sounds: SLIDER_DEFAULT };
  private soundChanged: ((v: SoundSettings, done: boolean) => void) | null = null;
  private settingsOpen = false;
  private lineTimer = 0;
  private cardTimer = 0;
  private hintTimer = 0;

  constructor(touch: boolean) {
    this.root.className = 'hl-ui';
    this.title.className = 'hl-title';
    this.card.className = 'hl-card';
    this.line.className = 'hl-line';
    this.hint.className = 'hl-hint';
    this.controls.className = 'hl-controls';
    this.menu.className = 'hl-menu';
    this.menu.hidden = true;

    this.walkButton.type = 'button';
    this.walkButton.className = 'hl-button';
    this.walkButton.setAttribute('aria-pressed', 'false');
    // The label shortens to "Walk" on narrow phones, beside the joystick; its name doesn't.
    this.walkButton.setAttribute('aria-label', 'Walk with me');
    this.walkButton.innerHTML = `<span class="hl-ico" aria-hidden="true">${FOOTSTEPS}</span><span>Walk<span class="hl-walk-more"> with me</span></span>`;
    this.menuButton.type = 'button';
    this.menuButton.className = 'hl-button hl-round';
    this.menuButton.setAttribute('aria-label', 'Chapters');
    this.menuButton.innerHTML = `<span class="hl-ico" aria-hidden="true">${LANTERN}</span>`;
    this.menuButton.addEventListener('click', () => this.toggleMenu());
    this.controls.append(this.walkButton);
    this.controls.hidden = true;
    this.menuButton.hidden = true;

    this.root.append(this.title, this.card, this.line, this.hint, this.controls, this.menuButton, this.menu);
    document.body.append(this.root);
    this.root.dataset.touch = touch ? '1' : '0';

    // From the very first moment: the title on a solid night, while everything loads behind it.
    // Nothing is seen of the world until it has drawn itself a few times (showTitle lifts it).
    this.title.innerHTML = `
      <div class="hl-title-inner">${TITLE_HEADING}
        <p class="hl-loading">Lighting the lanterns…</p>
      </div>`;
    this.title.classList.add('hl-show', 'hl-cover');
  }

  /** Lifts the title away at once (when a developer starts partway in). */
  dropTitle() {
    this.title.remove();
  }

  /**
   * The opening title. If sound can't start yet (most phones need a tap first), it asks for one:
   * that tap calls `onSound` (inside the tap, so the browser lets sound start) and the title theme
   * plays while you look. Then a tap anywhere calls `onBegin` and resolves.
   */
  showTitle(options: { soundReady: boolean; onSound: () => void; onBegin: () => void }): Promise<void> {
    const heading = TITLE_HEADING;
    const ready = () => {
      this.title.innerHTML = `
      <div class="hl-title-inner">${heading}
        <button type="button" class="hl-begin">Begin the walk</button>
        <p class="hl-small">Best with headphones</p>
      </div>`;
    };
    // The night behind the title fades in under it.
    this.title.classList.add('hl-show');
    this.title.classList.remove('hl-cover');
    return new Promise((resolve) => {
      let stage: 'listen' | 'begin' = options.soundReady ? 'begin' : 'listen';
      let since = performance.now();
      if (stage === 'begin') {
        options.onSound();
        ready();
      } else {
        this.title.innerHTML = `
      <div class="hl-title-inner">${heading}
        <button type="button" class="hl-begin hl-listen">Tap to hear the night</button>
        <p class="hl-small">Sound on, best with headphones</p>
      </div>`;
      }
      // A tap anywhere on the title does it (the buttons are there to be found by keyboard too).
      const tap = () => {
        if (performance.now() - since < 450) return;
        if (stage === 'listen') {
          options.onSound();
          stage = 'begin';
          since = performance.now();
          ready();
          (this.title.querySelector('.hl-begin') as HTMLButtonElement | null)?.focus();
          return;
        }
        stage = 'begin';
        this.title.removeEventListener('click', tap);
        options.onBegin();
        this.title.classList.remove('hl-show');
        this.title.classList.add('hl-gone');
        setTimeout(() => this.title.remove(), 1600);
        const waiting = this.waiting;
        this.waiting = null;
        if (waiting) setTimeout(() => this.say(waiting.text, waiting.seconds), 2600);
        resolve();
      };
      since -= 450;
      this.title.addEventListener('click', tap);
    });
  }

  showControls() {
    this.controls.hidden = false;
    this.menuButton.hidden = false;
    if (this.root.dataset.touch === '1') this.fadeWhenIdle();
  }

  /**
   * On touch screens the joystick and the walk button fade almost away after a few seconds with
   * no finger on the screen (html.hl-idle), and come straight back at a touch. A finger resting on
   * the joystick counts as a touch.
   */
  private fadeWhenIdle() {
    if (this.idleWatched) return;
    this.idleWatched = true;
    const html = document.documentElement;
    const down = new Set<number>();
    let timer = 0;
    const rest = () => {
      clearTimeout(timer);
      timer = window.setTimeout(() => down.size === 0 && html.classList.add('hl-idle'), IDLE_MS);
    };
    addEventListener('pointerdown', (e) => {
      down.add(e.pointerId);
      html.classList.remove('hl-idle');
      rest();
    }, true);
    const up = (e: PointerEvent) => {
      down.delete(e.pointerId);
      rest();
    };
    addEventListener('pointerup', up, true);
    addEventListener('pointercancel', up, true);
    rest();
  }

  /** "I · The Arbor of Faces", fading in and out. */
  chapterCard(numeral: string, name: string, subtitle: string) {
    this.card.innerHTML = `<p class="hl-numeral">${numeral}</p><h2>${name}</h2><p class="hl-sub">${subtitle}</p>`;
    this.card.classList.remove('hl-show');
    void this.card.offsetWidth;
    this.card.classList.add('hl-show');
    clearTimeout(this.cardTimer);
    this.cardTimer = window.setTimeout(() => this.card.classList.remove('hl-show'), 5200);
  }

  /** A short line of story, for a few seconds. */
  say(text: string, seconds = 5) {
    // Nothing is said over the title: the latest line waits until the walk begins.
    if (this.title.classList.contains('hl-show')) {
      this.waiting = { text, seconds };
      return;
    }
    this.line.textContent = text;
    this.line.classList.add('hl-show');
    clearTimeout(this.lineTimer);
    this.lineTimer = window.setTimeout(() => this.line.classList.remove('hl-show'), seconds * 1000);
  }

  /** How to move, until they've moved. */
  showHint(text: string, seconds = 9) {
    this.hint.textContent = text;
    this.hint.classList.add('hl-show');
    clearTimeout(this.hintTimer);
    this.hintTimer = window.setTimeout(() => this.hideHint(), seconds * 1000);
  }

  hideHint() {
    this.hint.classList.remove('hl-show');
  }

  setWalking(on: boolean) {
    this.walkButton.setAttribute('aria-pressed', on ? 'true' : 'false');
    this.walkButton.classList.toggle('hl-on', on);
  }

  /** The chapters you can return to. */
  setChapters(list: ChapterEntry[]) {
    this.chapters = list;
    this.renderMenu();
  }

  /** The sound levels shown in the settings; `onChange` hears every move (`done` when a slider is let go). */
  setSound(values: SoundSettings, onChange: (v: SoundSettings, done: boolean) => void) {
    this.sound = { ...values };
    this.soundChanged = onChange;
    this.renderMenu();
  }

  private renderMenu() {
    this.menu.innerHTML = '';
    const h = document.createElement('p');
    h.className = 'hl-menu-title';
    h.textContent = 'Chapters';
    this.menu.append(h);
    for (const c of this.chapters) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'hl-menu-item';
      b.disabled = !c.reached;
      b.innerHTML = `<span class="hl-menu-num">${c.numeral}</span><span>${c.reached ? c.name : 'Not yet found'}</span>`;
      b.addEventListener('click', () => {
        this.toggleMenu(false);
        c.go();
      });
      this.menu.append(b);
    }
    this.menu.append(this.settings());
  }

  /** The settings: a row that opens two sliders (the music; the sounds of the world) and a reset. */
  private settings(): HTMLElement {
    const wrap = document.createElement('div');
    wrap.className = 'hl-settings-wrap';
    const open = document.createElement('button');
    open.type = 'button';
    open.className = 'hl-menu-item hl-menu-settings';
    open.setAttribute('aria-expanded', this.settingsOpen ? 'true' : 'false');
    open.setAttribute('aria-controls', 'hl-settings');
    open.innerHTML = `<span class="hl-menu-num" aria-hidden="true">${SLIDERS}</span><span>Settings</span>`;
    const panel = document.createElement('div');
    panel.className = 'hl-settings';
    panel.id = 'hl-settings';
    panel.hidden = !this.settingsOpen;
    panel.innerHTML = `
      <p class="hl-settings-title">Sound</p>
      <div class="hl-slider">
        <label for="hl-vol-music">Music</label>
        <output for="hl-vol-music"></output>
        <input id="hl-vol-music" class="hl-range" type="range" min="0" max="100" step="1" data-k="music">
      </div>
      <div class="hl-slider">
        <label for="hl-vol-sounds">Sound effects</label>
        <output for="hl-vol-sounds"></output>
        <input id="hl-vol-sounds" class="hl-range" type="range" min="0" max="100" step="1" data-k="sounds"
          aria-describedby="hl-vol-sounds-note">
        <small id="hl-vol-sounds-note">Wind, footsteps, creatures and chimes</small>
      </div>
      <button type="button" class="hl-button hl-quiet hl-reset">Back to default</button>`;
    const inputs = [...panel.querySelectorAll<HTMLInputElement>('.hl-range')];
    const show = () => {
      for (const r of inputs) {
        const v = this.sound[r.dataset.k as keyof SoundSettings];
        r.value = String(v);
        r.style.setProperty('--fill', `${v}%`);
        r.setAttribute('aria-valuetext', `${v} percent`);
        (r.parentElement?.querySelector('output') as HTMLOutputElement).textContent = String(v);
      }
    };
    show();
    for (const r of inputs) {
      const k = r.dataset.k as keyof SoundSettings;
      r.addEventListener('input', () => {
        this.sound[k] = Number(r.value);
        show();
        this.soundChanged?.({ ...this.sound }, false);
      });
      r.addEventListener('change', () => this.soundChanged?.({ ...this.sound }, true));
    }
    (panel.querySelector('.hl-reset') as HTMLButtonElement).addEventListener('click', () => {
      this.sound = { music: SLIDER_DEFAULT, sounds: SLIDER_DEFAULT };
      show();
      this.soundChanged?.({ ...this.sound }, true);
    });
    open.addEventListener('click', () => {
      this.settingsOpen = !this.settingsOpen;
      panel.hidden = !this.settingsOpen;
      open.setAttribute('aria-expanded', this.settingsOpen ? 'true' : 'false');
      if (this.settingsOpen) panel.scrollIntoView({ block: 'nearest' });
    });
    wrap.append(open, panel);
    return wrap;
  }

  /**
   * Asks for a wish: a few words and a leaf colour. Resolves with them, or null if they'd rather
   * not. Nothing leaves the creation except into the group's own saves.
   */
  askWish(): Promise<{ text: string; color: 'coral' | 'teal' } | null> {
    return new Promise((resolve) => {
      const panel = document.createElement('div');
      panel.className = 'hl-dialog';
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-label', 'Hang a wish on the tree');
      panel.innerHTML = `
        <p class="hl-dialog-title">Hang a wish on the tree</p>
        <textarea maxlength="80" rows="2" placeholder="A few words — for someone, or for something"></textarea>
        <div class="hl-dialog-row" role="radiogroup" aria-label="Leaf colour">
          <button type="button" class="hl-chip hl-coral" role="radio" aria-checked="true" data-c="coral">Coral leaf</button>
          <button type="button" class="hl-chip hl-teal" role="radio" aria-checked="false" data-c="teal">Teal leaf</button>
        </div>
        <div class="hl-dialog-row">
          <button type="button" class="hl-button hl-quiet" data-a="cancel">Not now</button>
          <button type="button" class="hl-button hl-go" data-a="hang">Hang it</button>
        </div>`;
      let color: 'coral' | 'teal' = 'coral';
      const text = panel.querySelector('textarea') as HTMLTextAreaElement;
      panel.querySelectorAll<HTMLButtonElement>('.hl-chip').forEach((b) =>
        b.addEventListener('click', () => {
          color = b.dataset.c as 'coral' | 'teal';
          panel.querySelectorAll('.hl-chip').forEach((o) => o.setAttribute('aria-checked', o === b ? 'true' : 'false'));
        }),
      );
      const done = (v: { text: string; color: 'coral' | 'teal' } | null) => {
        panel.remove();
        resolve(v);
      };
      (panel.querySelector('[data-a="cancel"]') as HTMLButtonElement).addEventListener('click', () => done(null));
      (panel.querySelector('[data-a="hang"]') as HTMLButtonElement).addEventListener('click', () => {
        const t = text.value.replace(/\s+/g, ' ').trim();
        done({ text: t || '✶', color });
      });
      this.root.append(panel);
      setTimeout(() => text.focus(), 50);
    });
  }

  /** A wish someone hung, shown for a few seconds. */
  showWish(text: string, by: string) {
    this.say(by ? `“${text}” — ${by}` : `“${text}”`, 6);
  }

  /** A soft call to action floating low in the frame (e.g. "Hang a wish"). Returns a remover. */
  offer(label: string, onClick: () => void): () => void {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'hl-button hl-offer';
    b.textContent = label;
    b.addEventListener('click', onClick);
    this.root.append(b);
    this.offers.add(b);
    return () => {
      b.remove();
      this.offers.delete(b);
    };
  }

  /** Takes down every offer (a chapter's offers end with it). */
  clearOffers() {
    for (const b of this.offers) b.remove();
    this.offers.clear();
  }

  /** The end of the night. */
  ending(onAgain: () => void) {
    const card = document.createElement('div');
    card.className = 'hl-title hl-show hl-ending';
    card.innerHTML = `
      <div class="hl-title-inner">
        <p class="hl-kicker">and every light found its way home</p>
        <h1>Hallowed Lanterns</h1>
        <p class="hl-small">Thank you for walking with us tonight.</p>
        <div class="hl-dialog-row" style="justify-content:center;margin-top:1.4em">
          <button type="button" class="hl-button hl-quiet" data-a="stay">Stay a while</button>
          <button type="button" class="hl-begin" data-a="again">Walk again</button>
        </div>
      </div>`;
    (card.querySelector('[data-a="stay"]') as HTMLButtonElement).addEventListener('click', () => card.remove());
    (card.querySelector('[data-a="again"]') as HTMLButtonElement).addEventListener('click', () => {
      card.remove();
      onAgain();
    });
    this.root.append(card);
  }

  toggleMenu(show = this.menu.hidden) {
    this.menu.hidden = !show;
    document.documentElement.classList.toggle('hl-menu-open', !this.menu.hidden);
    this.menuButton.setAttribute('aria-expanded', show ? 'true' : 'false');
  }
}

/** How long the joystick and the walk button stay clear after the last touch. */
const IDLE_MS = 4000;

const FOOTSTEPS = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><ellipse cx="8" cy="7" rx="2.6" ry="4"/><ellipse cx="8.2" cy="14.6" rx="1.9" ry="1.6"/><ellipse cx="16" cy="11" rx="2.6" ry="4"/><ellipse cx="16.2" cy="18.6" rx="1.9" ry="1.6"/></svg>`;
const SLIDERS = `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/></svg>`;
const LANTERN = `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M12 2.5v2"/><path d="M9 4.5h6"/><ellipse cx="12" cy="12" rx="6.5" ry="6.8"/><path d="M12 5.4c-2.2 2-2.2 11.2 0 13.2M12 5.4c2.2 2 2.2 11.2 0 13.2"/><path d="M12 18.8v2.7"/></svg>`;
