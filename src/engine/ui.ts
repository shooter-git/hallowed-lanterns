/**
 * Everything drawn over the world: the title, chapter cards, story lines, hints and the two
 * controls (walk with me, chapters). The app's own menu button lives in the top-left corner,
 * so nothing goes there.
 */
export class UI {
  readonly root = document.createElement('div');
  private readonly title = document.createElement('div');
  private readonly card = document.createElement('div');
  private readonly line = document.createElement('p');
  private readonly hint = document.createElement('p');
  private readonly controls = document.createElement('div');
  readonly walkButton = document.createElement('button');
  readonly menuButton = document.createElement('button');
  private readonly menu = document.createElement('div');
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
    this.walkButton.innerHTML = `<span class="hl-ico" aria-hidden="true">${FOOTSTEPS}</span><span>Walk with me</span>`;
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
  }

  /** The opening title. Calls `onBegin` inside the tap itself, then resolves. */
  showTitle(onBegin: () => void): Promise<void> {
    this.title.innerHTML = `
      <div class="hl-title-inner">
        <p class="hl-kicker">One October night at the pumpkin patch</p>
        <h1>Hallowed Lanterns</h1>
        <button type="button" class="hl-begin">Begin the walk</button>
        <p class="hl-small">Best with headphones</p>
      </div>`;
    this.title.classList.add('hl-show');
    const button = this.title.querySelector('button') as HTMLButtonElement;
    return new Promise((resolve) => {
      const go = () => {
        onBegin();
        this.title.classList.remove('hl-show');
        this.title.classList.add('hl-gone');
        setTimeout(() => this.title.remove(), 1600);
        resolve();
      };
      button.addEventListener('click', go, { once: true });
    });
  }

  showControls() {
    this.controls.hidden = false;
    this.menuButton.hidden = false;
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
  setChapters(list: { numeral: string; name: string; reached: boolean; go: () => void }[]) {
    this.menu.innerHTML = '';
    const h = document.createElement('p');
    h.className = 'hl-menu-title';
    h.textContent = 'Chapters';
    this.menu.append(h);
    for (const c of list) {
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
    return () => b.remove();
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
    this.menuButton.setAttribute('aria-expanded', show ? 'true' : 'false');
  }
}

const FOOTSTEPS = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><ellipse cx="8" cy="7" rx="2.6" ry="4"/><ellipse cx="8.2" cy="14.6" rx="1.9" ry="1.6"/><ellipse cx="16" cy="11" rx="2.6" ry="4"/><ellipse cx="16.2" cy="18.6" rx="1.9" ry="1.6"/></svg>`;
const LANTERN = `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M12 2.5v2"/><path d="M9 4.5h6"/><ellipse cx="12" cy="12" rx="6.5" ry="6.8"/><path d="M12 5.4c-2.2 2-2.2 11.2 0 13.2M12 5.4c2.2 2 2.2 11.2 0 13.2"/><path d="M12 18.8v2.7"/></svg>`;
