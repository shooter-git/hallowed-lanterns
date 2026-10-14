# tools/audio — the Hallowed Lanterns sound renderer

Everything in `public/audio/` is made by this folder (our own work:
`"license": "own"` in `assets.lock.json`), except the footsteps. The **music**
and the instrument-like sound effects (xylophone notes, the big guitar's
strings, the Ember's chimes, snowflakes, sprinkle-burst, wish-hang) are
composed here and played by real orchestral samples from **VSCO 2 Community
Edition**, with a few instruments from the **Versilian Community Sample
Library** and October Snow's double bass from Karoryfer's **Meatbass** (see
*Samples* below); everything else (ambiences, creatures, magic)
is synthesised from scratch, and so are the Deep's analog synths. Python + numpy/scipy, with a few sample-by-sample
kernels compiled by numba; ffmpeg (libmp3lame) encodes and measures.

**Wind** in the outdoor ambiences is recorded too (`hlaudio/recordings.py`,
`wind()`): stretches of Joseph Sardin's CC0 field recordings, "Wind in shrub"
(the leafy chapters, each from a different stretch), "Wind in Tall Grass" (the
Pasture) and his foley "Wind" (the Snow, the Grove's fog), cross-faded round so
they loop without a seam, with twig-snap clicks taken down, and set to the same
loudness the synthesised wind had. ("Wind in the Trees" was fetched too, but has
birdsong in it, so it isn't used.) The **passage between chapters**
(`pieces/sfx/passage.py`) is played by the orchestra with a rush of that wind.

**Footsteps** (`pieces/sfx/footsteps.py`) are cut from real studio foley by
Joseph Sardin at [BigSoundBank](https://bigsoundbank.com), released under CC0:
fine gravel, dry leaves, grass, snow, and wet mud for the sea floor. The piece fetches
the originals into `.cache/recorded/` (git ignores them), splits them into single
steps, keeps the cleanest, and records each one in `assets.lock.json` as
`CC0-1.0` with its source.

## Samples: VSCO 2 Community Edition

The orchestra is **VSCO 2 CE** by Versilian Studios (Sam Gossner and
contributors; the pipe organ by Simon Dalzell), released under **CC0 1.0**
(public domain): <https://github.com/sgossner/VSCO-2-CE>. No credit is
required, but it is given here and in `assets.lock.json` ("using VSCO 2
Community Edition orchestral samples (CC0, Versilian Studios)").

The samples are not in this repository. They are fetched as a sparse git
checkout into `tools/audio/.cache/vsco/` (git-ignored, about 2.3 GB) with only
the folders we use:

```sh
git clone --filter=blob:none --no-checkout https://github.com/sgossner/VSCO-2-CE.git tools/audio/.cache/vsco
cd tools/audio/.cache/vsco
git sparse-checkout set --no-cone /LICENSE /README.md /Readme.txt \
  "/Strings/Violin Section/susVib/" "/Strings/Violin Section/Spic/" "/Strings/Violin Section/Pizz/" \
  "/Strings/Violin Section/Trem/" "/Strings/Viola Section/susvib/" "/Strings/Viola Section/spic/" \
  "/Strings/Viola Section/pizz/" "/Strings/Viola Section/trem/" "/Strings/Cello Section/susvib/" \
  "/Strings/Cello Section/spic/" "/Strings/Cello Section/pizzT/" "/Strings/Cello Section/trem/" \
  "/Strings/Solo Contrabass/SusNV/" "/Strings/Solo Contrabass/Spic/" "/Strings/Solo Contrabass/Pizz/" \
  "/Strings/Solo Violin/Arco Vib/" \
  "/Strings/Harp/" "/Brass/F Horn/" "/Brass/Tenor Trombone/" "/Brass/Tuba/" "/Keys/Organ/" "/Keys/Upright Nr1/" \
  "/Percussion/Timpani*" "/Percussion/BDrumNewhit*" "/Percussion/Glock*" "/Percussion/Marimba*" \
  "/Percussion/Sleighbells*" "/Percussion/Triangle3*" "/Percussion/BellTree*" "/Percussion/Conga-*" \
  "/Percussion/Tumba-*" "/Percussion/Tamb1-*" "/Percussion/Claves*" "/Percussion/Snare2-*" "/Percussion/susCymb1-*" \
  "/Woodwinds/Flute/stac/" "/Woodwinds/Flute/susNV/" "/Woodwinds/Flute/susvib/" "/Woodwinds/Clarinet/stac/" \
  "/Woodwinds/Clarinet/susLong/" "/Woodwinds/Oboe/Stacc/" "/Woodwinds/Oboe/Vib/" "/Woodwinds/Bassoon/stac/" \
  "/Woodwinds/Bassoon/sus/"
git checkout master
```

On first use `hlaudio/sampler.py` measures every sample (start, attack, loop
points, glitches, true tuning by YIN, layer loudness) and caches that in
`.cache/vsco-catalog.json`. Notes are played from the nearest sample (so a
shift of at most about 1.5–2 semitones inside the sampled range) with
band-limited (windowed-sinc) resampling, legato crossfades with a short
slide and release tails. What keeps the strings from sounding synthetic:

* **one recorded velocity layer per note** (chosen by the note's dynamic);
  swells are a smooth volume (expression) curve, never a cross-fade between
  two layers, which combs into a phasey pad;
* **no detuned or time-shifted copies** of a sample (that is a chorus, the
  classic synth-string sound): `double=` in old scores is ignored;
* **re-bowing instead of looping**: a bowed or blown note longer than about
  5.5–7 s (`sampler.REBOW`) is split into overlapping notes, each with its
  own natural attack; loops are only a last resort;
* **arranged to the library's strengths**: long lyrical lines go to the
  oboe (every line the solo violin used to carry: near, little hall, note by
  note, a touch of presence; `hlaudio/lead.py`), the other woodwinds, horns,
  piano and organ; the string sections play pizzicato (with a little room so
  it blooms, round-robins and varied velocities) and spiccato, and every
  bowed sustain, swell, bass line or tremolo is only a quiet bed far back in
  the hall (depth 0.95, no slides), where its legato can't be heard;
* light processing: a gentle transient softener (the bow's attack is what
  makes them real), some air left on top. Then every instrument goes through its own
tone chain (`orch.TONE`: a transient softener, warm low mids, the 2–6 kHz
presence tamed, the top rolled off; the piano is made "felt", the glockenspiel
soft) and is seated at a depth in a generated concert hall (`orch.SEAT`:
further = less and darker dry signal, more hall), the organ in a cathedral.

## Samples: VCSL (the Versilian Community Sample Library)

A few colours come from **VCSL** by Versilian Studios (Sam Gossner and
contributors), also **CC0 1.0** (public domain):
<https://github.com/sgossner/VCSL>. Credit, as for VSCO: "using the
Versilian Community Sample Library (CC0, Versilian Studios)". Sparse-checked
out into `tools/audio/.cache/vcsl/` (git-ignored, about 300 MB):

```sh
git clone --filter=blob:none --no-checkout https://github.com/sgossner/VCSL.git tools/audio/.cache/vcsl
cd tools/audio/.cache/vcsl
git sparse-checkout set --no-cone "/LICENSE*" "/README*" "/Chordophones/Zithers/Dan Tranh/" \
  "/Idiophones/Struck Idiophones/Gong 1/" "/Idiophones/Struck Idiophones/Gong 2/" \
  "/Idiophones/Struck Idiophones/Finger Cymbals/" "/Idiophones/Struck Idiophones/Woodblock/" \
  "/Aerophones/Edge-blown Aerophones/Ocarina, Typical/" "/Idiophones/Struck Idiophones/Shaker, Small/" \
  "/Membranophones/Struck Membranophones/Bongos/" "/Idiophones/Struck Idiophones/Hi-Hat Cymbal/" \
  "/Membranophones/Struck Membranophones/Snare Drum, Modern 2/" "/Idiophones/Struck Idiophones/Vibraphone/"
git checkout master
```

| instrument (`sampler.INSTRUMENTS`) | VCSL folder | used in |
|---|---|---|
| `zither`, `zither_trem`, `zither_gliss_up`, `zither_gliss_down` | Dan Tranh: Normal (mf/f/ff), Tremolo, Gliss (Up/Dwn Med mf) | the Lantern Garden (played as a guzheng) |
| `ocarina` (`ocarina_vib`) | Ocarina, Typical: Sustains/Sus (SusVib) | the Garden (as a xun), the Marigold Garden (a clay flute) |
| `gong` | Gong 1 (p, mf, f, fff) | the Garden (two strokes); the Marigold's far bell and the gong under its peak |
| `finger_cymbal` | Finger Cymbals | the Garden (phrase starts); October Snow (glints, and the snowflakes) |
| `woodblock` | Woodblock (`wood_click_*`: pp, mp, f, ff) | the Garden (the temple block); October Snow (the snowman's steps) |
| `shaker_down`, `shaker_up` | Shaker, Small | the Marigold (its few phased hats) |
| `vibes`, `vibes_bowed` | Vibraphone: Soft Mallets, Bowed (named an octave low) | the Arbor (the Ember's motif; its birth and chime) |
| `bongo_hi`, `bongo_hi_muted`, `bongo_lo`, `hihat`, `hihat_open`, `hihat_pedal`, `drum_snare`, `drum_xstick`, `drum_roll` | Bongos; Hi-Hat Cymbal; Snare Drum, Modern 2 | available, not played by any piece now |

VCSL is catalogued separately (`.cache/vcsl-catalog.json`), so adding a VCSL
instrument never re-measures VSCO. Its names follow other conventions, and
some pitches are measured rather than read:

* the dan tranh and the ocarina name their notes an octave low (B1 is B2);
* the dan tranh's strings are B C# D# F# G# (B pentatonic) from B2 to B5, so
  any G-pentatonic note is at most a semitone from a string, and the
  glissandi, played a major third down, sweep exactly G A B D E;
* a hard pluck starts sharp, so the zither's tuning is read 0.6–1.6 s after
  the pluck (its C# strings sit 37–42 cents sharp and are corrected; plucks
  land within ±6 cents);
* the gong (fundamental ~143.5 Hz, played as D3), the finger cymbal (~3.1 kHz,
  G7) and the woodblock (~1.37 kHz, played at E6) are pitched by their
  strongest partial;
* plucked and struck notes can carry a pitch curve, `x["bend"]` (time,
  semitone breakpoints) and `x["vib"]` (a pressed vibrato): the guzheng's
  slides, presses and left-hand vibrato (`hlaudio/festival.py`).

The zither's own vibrato samples are not used (their vibrato rises ~30 cents
above the note); the vibrato is drawn on the plain plucks instead.

## Samples: Meatbass (the jazz double bass)

October Snow's double bass is **Meatbass** by Karoryfer Samples, **CC0 1.0**:
a 1958 Otto Rubner double bass played and sampled by Drogomir Smolken
(<https://github.com/sfzinstruments/karoryfer.meatbass>). Its plucks are
sampled every minor third (C, E-flat, G-flat, A; `c1`, `eb1`, `gb1`, `a1`, ...,
named by sounding pitch) at four dynamics with four round robins, and ring for
seconds, as a bass on a concert stage does. Cloned into
`tools/audio/.cache/meatbass/` (git-ignored, about 530 MB with its history):

```sh
git clone --depth 1 https://github.com/sfzinstruments/karoryfer.meatbass.git tools/audio/.cache/meatbass
```

It is the sampler's instrument `upright` (catalogue `.cache/meatbass-catalog.json`;
only `Samples/pizz/` is used). The Snow plays it low, around the open A string
(up an octave the strings are short and the notes die at once): the softer
plucks, which ring longest, the first milliseconds of each pluck left out (the
side of the finger, not the orchestra's snap), and a gentle compressor
(`effects.compress`) for the even sustain of a bass through its amp.

## Samples: FreePats (the Spanish classical guitar)

No piece plays it now (the Marigold Garden did, before its present score); it
stays available as the sampler's `nylon`. It is the **Spanish classical guitar** of the
[FreePats project](https://freepats.zenvoid.org/Guitar/acoustic-guitar.html)
(version 2019-06-18), **CC0 1.0**: one dynamic layer, every semitone from G1
to C6, named by sounding pitch. Fetched and converted to WAV into
`tools/audio/.cache/freepats/` (git-ignored, about 13 MB):

```sh
mkdir -p tools/audio/.cache/freepats/Guitar/SpanishClassicalGuitar && cd tools/audio/.cache
curl -LO "https://freepats.zenvoid.org/Guitar/SpanishClassicalGuitar/SpanishClassicalGuitar-SFZ+FLAC-20190618.7z"
7z x SpanishClassicalGuitar-SFZ+FLAC-20190618.7z
for f in SpanishClassicalGuitar-SFZ+FLAC-20190618/samples/*.flac; do
  ffmpeg -v error -i "$f" -c:a pcm_s16le "freepats/Guitar/SpanishClassicalGuitar/$(basename "$f" .flac).wav"
done
```

It is the sampler's instrument `nylon` (catalogue `.cache/freepats-catalog.json`).
The recordings sit 5–16 cents sharp and are corrected note by note; above B4
they ring for barely a second, so the guitar keeps to the altar's broken
chords (its lowest notes, C and B, are played an octave up, as a guitar
would). It has one dynamic layer, so a repeated note is never the same pluck
twice: `x["nb"]` plays it from the neighbouring note's recording (shifted to
pitch), `x["skip"]` starts the pluck a few milliseconds in and `x["detune"]`
moves it a few cents.

## Rendering

```sh
python3 -m venv tools/audio/.venv                     # once
tools/audio/.venv/bin/pip install -r tools/audio/requirements.txt

python3 tools/audio/render.py --list                  # every target
python3 tools/audio/render.py arbor                   # music + ambience "arbor"
python3 tools/audio/render.py music:finale sfx:footsteps
python3 tools/audio/render.py music                   # every music piece
python3 tools/audio/render.py --all -j 3              # everything, 3 at a time
```

`render.py` re-runs itself inside `tools/audio/.venv` when needed. Each
target writes its MP3 into `public/audio/`, updates `public/audio/manifest.json`
and, at the end of the run, adds any new files to the `assets` array of
`assets.lock.json` (merging with what others wrote; `--no-lock` skips that).
Renders are deterministic (every random choice is seeded by name).

A music loop takes 3–5 minutes on 8 cores (the sampler and the halls are the
slow part), an ambience under a minute, all the sfx a few minutes. Peak
memory is around 1.5–2 GB per process; run at most two renders at a time.

QA by-products go to `tools/audio/.cache/` (git-ignored): `wav/` (the exact
audio that was encoded) and `qa/` (a spectrogram + level picture per piece).

## The motif

The Ember's chime and the seed of every piece, in **D major**:

```
6/8:   D5 (eighth pickup) | B5 (quarter)  A5 (eighth)  F#5 (eighth)  A5 (quarter, held)
       1                  | 6             5            3             5
       "ti | TAA ti ti TAA"   intervals from the first note: 0, +9, +7, +4, +7
```

A rising major sixth (the flame leaps out of its lantern), a sigh down a step,
a dip to the third and a lift back to the fifth: it ends open, like "this way!".
All five notes are in D major pentatonic, so it is playable on the eight letter
pumpkins `xylo-1..8` = **D5 E5 F#5 A5 B5 D6 E6 F#6**: pumpkins **1 5 4 3 4**
(0-based `[0, 4, 3, 2, 3]`, also in `manifest.json` → `motif.xylo`). The big
guitar's six open strings `guitar-1..6` are tuned to the Marigold's G, **G3 D4 G4 B4
D5 E5**, so the motif, a fourth up (G E D B D, as the Marigold's chime sings it), is
strings **3 6 5 4 5** (`motif.guitarNotes`, `motif.guitar = [2, 5, 4, 3, 4]`).

The full theme (`hlaudio/theme.py`) grows from it: A states the motif, answers
it with the same shape a step lower, restates it and climbs to the high D; B
goes to B minor and a borrowed G minor chord, rising in motif-shaped steps.

Every chapter weaves the motif in as a *cell*, the way Philip Glass, Hans
Zimmer and Cliff Martinez treat a motif: fragmented, inverted, augmented in a
bass or organ pedal, diminished, displaced against the bar, in canon and
stretto, emerging from a cycling texture rather than sung as a tune
(`hlaudio/process.py`). The chimes `sfx/ember-chime-<chapter>` play it on
that chapter's instrument in the same key as its music, so the Ember always
sounds in tune with what is playing:

| piece    | title          | key / mode, meter                 | built from…                                         | chime on…          |
|----------|----------------|-----------------------------------|-----------------------------------------------------|--------------------|
| title    | Hallowed Lanterns | D (Lydian colours), 4/4 3+3+2 | felt-piano cycle, the theme emerging as its top voice; oboe + clarinet canon; cello pizzicato pedal, then a stand-up bass (12) and, at the swell's height, a short groove (16–19: the bass's syncopated pickups, tumba and conga); glass pulse, swell | — |
| arbor    | Sundown        | B minor, 12/8 at 60 (160 s)        | a felt piano's triplets (the left hand holding the bass, the sustain pedal down, the upper keys voiced down so nothing leaps out), beginning soft and far and growing steadily, turning in place, climbing from bar 16; the harmony B minor, G, E minor, F# minor (no cadence home); the Ember's motif (D, B A F# A) on a vibraphone (VCSL, soft mallets), a beat a note, the bowed vibraphone and glass holding its long notes; the bowed vibraphone sings it a bar a note over a dark analog bass held and decaying a chord at a time; the swell with long sub booms, timpani and cymbal crescendos, climbing again (a timpani roll, the greatest boom) to its peak at bar 29; the piano alone over a last held B, tapering away to the level it began at | vibraphone, the song's motif, B minor |
| grove    | Blue Hour      | B aeolian, 7/8 (2+2+3)            | glass arpeggio + mirror; pizzicato pedal; clarinet cell; stretto (solo violin, flute, bassoon); spiccato ticking | three variations: harp, high harp, felt piano + bell tree; D B A F# A |
| garden   | Lantern Song   | G major pentatonic, 4/4 3+3+2     | a lantern festival: the zither (dan tranh as a guzheng) sings the cell with sweeps, slides and pressed vibrato over a low harp additive process and the organ's cycling; ocarina (as a xun) augmentation; fugue (winds, zither, ocarina, horn, oboe), temple block, finger cymbals; drums and gong at the top; zither tremolo canon over the pedal augmentation | harp + glass halo, G E D B D |
| pasture  | Gentle Giants  | D mixolydian, 4/4                 | brass canon/stretto; dotted spiccato ostinato; oboe + clarinet inversion; one braam on G; the giants' gait (drums, bars 20–31) | felt piano + harp, D |
| hollow   | Sugar Rush     | D lydian, 4/4 (3+3+2)             | marimba cycling; pizzicato hocket of the diminished cell; woodwind additive; relative-minor lift | marimba + glass halo, D |
| snow     | First Snow     | A lydian, 4/4 3+3+2 (160 s)       | it begins to snow: glass colours over a far organ A (its wind is the chapter's ambience); a music box (glockenspiel, felt piano an octave below) turning one figure (E A C# D#) that never changes; a jazz double bass (Meatbass), low and ringing, two long notes a bar; the theme as the top voice of piano chords; the winter's percussion as an orchestra plays it (sleigh bells far left, triangle and finger-cymbal glints, the snowman's woodblock steps with his pizzicato-and-clarinet bounce, a stop and a clink, a warm B-over-A on the horns); the rise (tremolo strings, organ, horns, a soft concert bass drum, timpani, a cymbal swell); the flakes rise (a bell tree, reversed piano and glockenspiel, a harp sweep, a glass line climbing octave over octave); the hush again | harp + soft glock, A |
| deep     | Where the Lanterns Swim | F# dorian / A lydian, 4/4 | a 1980s analog-synth colour (`analog.py`): the five-note arp phasing through a resonant ladder filter on the tide; a sixteenth bass pulse; a sixteenth sequencer walking the cell; pad swells in the light; mirror glass; whale glass; horn + oboe canon; drums in the light (22–38) | harp under water + glass, A F# E C# E |
| marigold | Remember Me    | E minor, 4/4 at 72 (186.7 s)     | the stillness of Cliff Martinez, the build of Hans Zimmer, the turning piano and quiet beat of Ólafur Arnalds (their ways, none of their tunes): a glass world over the organ's E, colours drifting one note at a time; a felt piano turns one figure (B E F# G) while the bass slides beneath it; a beat born from real brush taps, a tuned sub kick, a warm analog bass only under the accents, booms (a sub diving onto the bass note, a timpani for its pop, a suspended cymbal's crescendo before, the gong under the greatest), a few phased shaker hats; the build (horns sing the cell, strings walk forward); the peak in C; the dark on B; the release; the afterglow lifting into G (the figure a third higher, the Ember chiming its own song, high strings), its last glass colour the intro's first. Every voice has a near and a far seat (`place()`) | big guitar, G |
| finale   | Hallowed Lanterns | D, 4/4 (one-shot)              | the title grown: theme emerging, three-voice canon, Zimmer build with drums (24–37), a prepared A-pedal lift, coda | — |
| picture show | The Picture Show | F, 3/4 waltz (on purpose)   | upright piano, solo violin over pizzicato, clarinet, flute | — |

Harmonic colour comes from voicing, pedal points and modal mixture inside
the key; no piece jumps to a remote key.

**Beats** belong to the swells, and only to them: the Garden's top (bars
28–40, a Chinese drum's weight under the gong), the Pasture's build (20–31,
the giants' gait), the Deep's turn into the light (22–38), First Snow's one
swell (24–33, soft), the finale's build and statement (24–37), and, barely,
an electronic heartbeat under the height of the Marigold Garden's swell
(34–39). `hlaudio/beats.py` writes them as a
groove whose hits each have a weight and a gate on the swell: low timpani
following the bass and the concert bass drum, in the piece's 3+3+2, the
downbeats first, then the syncopations, then ghost notes and pickups as the
swell grows, dropping out in reverse - never a drum loop, never a pop kick.
Everywhere else there is none.

Ember-born is a short stinger (D major). (The Keeper of the Deep rises to a sound, not a
stinger: `pieces/sfx/keeper.py`.)

## Files

```
render.py            command line (targets = pieces/<kind>/<name>.py)
requirements.txt
hlaudio/             the library
  core.py            sample rate, note names, envelopes, noise, Track (circular stereo buffer)
  score.py           notes, a tiny text notation, chords, voice-leading, tempo clocks (rubato)
  arrange.py         arranging helpers (pads by rank, comping, dynamics shapes, augmentation)
  sampler.py         the VSCO 2 CE + VCSL + FreePats sampler (catalogues, tuning, layers, loops, legato,
                     re-bowing, pitch curves for bends and vibrato)
  festival.py        the Garden's festival instruments on the stage (seats, tone chains) and the
                     guzheng's idioms: slide_in, vibrato, press, glissandi landing on the beat
  beats.py           grooves born and gone with a swell (weights and gates), drum pitches that
                     follow the bass
  analog.py          vintage analog voices for the Deep: polyBLEP saws/pulses, drifting
                     oscillators, a 4-pole ladder filter with per-note envelopes, saturation;
                     bass, sequencer, swell and arp patches
  lead.py            where the lines sit: the oboe lead near and present, the bowed-string bed
                     far back in the hall (depth, sends, tone)
  orch.py            the orchestra on a stage: seats (pan/width/depth), per-instrument tone
                     chains, hall sends, stem loudness/D-R/brightness report, tape, air
  process.py         compositional processes: modes, the motif as a cell (P/I/R/RI, fragments),
                     additive and cycling figures, canon, hocket, ticking, fitting to harmony
  electro.py         synthesised music layers: glass tones, filtered arps, pads,
                     sub pulse, braam half, gliding glass line
  sfxkit.py          sampled instrument sfx (close, ~15% of the music's reverb)
  theme.py           THE MOTIF and the full theme (melody + harmony), manifest entry
  nb.py              numba kernels: Karplus-Strong string, time-varying SVF, combs, dynamics
  lines.py           continuous "line" synthesis (glides, delayed vibrato, swells) + wavetable osc
  mallets.py         modal synthesis: music box, celesta, glockenspiel, bells, sleigh bells,
                     wind chimes, finger cymbal, pumpkin xylophone, upright piano
  plucked.py         extended Karplus-Strong: harp, guzheng (bends, vibrato), nylon guitar,
                     the big magical guitar, pizzicato
  bowed.py           string sections and solo cello (detuned players, bow noise, body IRs)
  body.py            modal body impulse responses (violin, viola, cello, bass, guitar, harp, zither)
  wind.py            bamboo flute (chiff, pitched breath) and soft horn section
  voice.py           formant choir (ooh/aah), glass pad, whale calls, drones
  perc.py            frame drum / taiko heartbeat, shaker, wooden knock
  nature.py          crickets, birds, distant murmur, wind in leaves, reeds, fog, creaks,
                     snow hush, underwater bed, bubbles, owls
  effects.py         biquad EQ, generated convolution reverbs (room, forest, field, hall,
                     cathedral, underwater, plate, sky), shimmer, chorus, wow/flutter,
                     saturation, echo
  master.py          BS.1770 loudness, true peak, glue compressor, true-peak limiter,
                     MP3 encode + ffmpeg ebur128 verification
  piece.py           Mix (dry bus + reverb sends), finish_loop / finish_oneshot / finish_sfx,
                     manifest writing
  qa.py              stats (LUFS, peaks, DC, HF share), spectrogram pictures, pitch check
  recordings.py      CC0 recordings (BigSoundBank): fetch once, de-click, seamless loops,
                     recorded wind for the ambiences, assets.lock.json entries
pieces/music/        title arbor grove garden pasture hollow snow deep marigold   (loops)
                     picture_show (the shadow-puppet film's cue, loop)
                     finale ember_born                                        (one-shots)
pieces/ambience/     arbor grove garden pasture hollow snow deep marigold projector
pieces/sfx/          footsteps ember_chimes lanterns creatures sparkles extras well_and_flytrap passage
                     keeper wings
```

Each piece script documents its form at the top (bars, sections, who plays).

## Conventions

* **Loops** are rendered *circularly*: every note, reverb tail, chorus and
  wobble that runs past the end wraps back to the start (period-N circular
  convolution, periodic LFOs, warmed-up filters), so the audio is the steady
  state of the piece playing forever. Files are `loopSeconds + tailSeconds`
  long and the tail is literally the first `tailSeconds` again (seam
  correlation = 1.000000, printed on every render). Music: whole bars of
  about 133–136 s + 4 s (the title 72 s + 4 s, picture show 120 s + 4 s,
  the Marigold Garden 186.7 s + 4 s, so its swell has room to build);
  `loopSeconds` is written to 6 decimals. Ambience: 60 s + 3 s.
* **Mastering**: music −16 LUFS integrated (First Snow −17, it is meant to be
  hushed), ambience −20 LUFS, true peak ≤ −2 dBTP before encoding; every MP3
  is decoded and measured with `ffmpeg -af ebur128=peak=true` and nudged until
  it lands within ±0.35 LU and ≤ −1.6 dBTP.
* The Ember's chimes are soft plucked or struck real samples (harp, felt
  piano, marimba, a little glockenspiel or bell tree, a faint glass halo),
  never anything reedy; the grove has three variations
  (`ember-chime-grove`, `-2`, `-3`, one manifest group) because it is heard
  several times in a row. `qa.reed_check` is a listen-proxy for reedy,
  square-ish tone (odd against even harmonics in 1–4 kHz).
* **SFX** are true-peak normalised by role: chimes, knocks and bells −3 dBTP;
  softer things (snowflakes, bubbles, squeaks, swings, butterflies) −4…−5;
  footsteps −6 (they repeat constantly); `ui-tap` −12 (a soft wooden tick). Mono unless the brief
  said stereo (ember chimes, sprinkle-burst, butterflies, wish-hang, fog-swirl).
* MP3: music 192 kbps CBR (128 kbps smears dense strings into a phasey
  shimmer), ambience and sfx 96 kbps CBR, 44.1 kHz, no ID3 tag (the
  LAME/Xing header stays, so decoders trim the encoder delay).
* `sfx/water-lap.mp3` is rendered circularly and is exactly 4.0 s, so it can
  be looped directly (`AudioBufferSourceNode.loop`); the PCM is seamless, the
  MP3 frame boundary leaves at most a tiny step around −40 dBFS.
* Size: everything in `public/audio/` stays under about 45 MB.
* Nothing is synthesised above ~9.5 kHz and instruments roll off from 6 kHz:
  the soundtrack should feel warm, never glassy.

## Adding or changing a piece

Write the harmony with `prog("Dmaj9:8 G6add9/D:8")` and the lines as
processes (`process.cell`, `realize`, `cycling`, `additive`, `ticking`,
`canon`, `fit`) or plain `seq("D5:1 | B5:2 A5:1", start)`; convert with a
`Clock`; play each part on a `Stage` (`st.play("violas", notes, "violas",
dyn=curve, shape=..., double=1)`), add electronic layers with `electro`;
`st.render(...)`; call `finish_loop` (circular) or `finish_oneshot`. Each
stem's loudness, depth, direct-to-reverb ratio and top-end excess (no third-
octave band above 4 kHz louder than the one an octave below) is printed while
rendering to help balance.
