# tools/audio — the Hallowed Lanterns sound renderer

Everything in `public/audio/` is made by this folder (our own work:
`"license": "own"` in `assets.lock.json`), except the footsteps. The **music**
and the instrument-like sound effects (xylophone notes, the big guitar's
strings, the Ember's chimes, snowflakes, sprinkle-burst, wish-hang) are
composed here and played by real orchestral samples from **VSCO 2 Community
Edition** (see *Samples* below); everything else (ambiences, creatures, magic)
is synthesised from scratch. Python + numpy/scipy, with a few sample-by-sample
kernels compiled by numba; ffmpeg (libmp3lame) encodes and measures.

**Footsteps** (`pieces/sfx/footsteps.py`) are cut from real studio foley by
Joseph Sardin at [BigSoundBank](https://bigsoundbank.com), released under CC0:
gravel, dry leaves, grass, snow, and wet mud for the sea floor. The piece fetches
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
  "/Strings/Solo Contrabass/SusNV/" "/Strings/Solo Contrabass/Spic/" "/Strings/Solo Violin/Arco Vib/" \
  "/Strings/Harp/" "/Brass/F Horn/" "/Brass/Tenor Trombone/" "/Brass/Tuba/" "/Keys/Organ/" "/Keys/Upright Nr1/" \
  "/Percussion/Timpani*" "/Percussion/BDrumNewhit*" "/Percussion/Glock*" "/Percussion/Marimba*" \
  "/Percussion/Sleighbells*" "/Percussion/Triangle3*" "/Percussion/BellTree*" \
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
* **arranged to the library's strengths**: long lyrical lines go to the solo
  violin, the woodwinds, horns, piano and organ; the string sections play
  pizzicato (with a little room so it blooms, round-robins and varied
  velocities), spiccato and short swells, and any long section sustain is
  soft, low and deep in the hall under the organ or the glass;
* light processing: a gentle transient softener (the bow's attack is what
  makes them real), some air left on top. Then every instrument goes through its own
tone chain (`orch.TONE`: a transient softener, warm low mids, the 2–6 kHz
presence tamed, the top rolled off; the piano is made "felt", the glockenspiel
soft) and is seated at a depth in a generated concert hall (`orch.SEAT`:
further = less and darker dry signal, more hall), the organ in a cathedral.

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
guitar's six open strings `guitar-1..6` are **D3 A3 D4 F#4 A4 B4**, so the motif
is strings **3 6 5 4 5** (`motif.guitarNotes`, `motif.guitar = [2, 5, 4, 3, 4]`).

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
| title    | Hallowed Lanterns | D (Lydian colours), 4/4 3+3+2 | felt-piano cycle, the theme emerging as its top voice; solo violin + clarinet canon; pizzicato pedal; glass pulse, swell | — |
| arbor    | Sundown        | D, 4/4                            | piano figure phasing against the bar; clarinet/bassoon/flute/solo-violin canon of the augmented cell; pizzicato bass and canon; organ pedal; horns | felt piano + glass halo, D |
| grove    | Blue Hour      | B aeolian, 7/8 (2+2+3)            | glass arpeggio + mirror; pizzicato pedal; clarinet cell; stretto (solo violin, flute, bassoon); spiccato ticking | three variations: harp, high harp, felt piano + bell tree; D B A F# A |
| garden   | Lantern Song   | G mixolydian, 4/4 3+3+2           | harp additive process; organ cycling; woodwind hocket; fugue on winds, horn and solo violin; pizzicato harmony; pedal augmentation | harp + glass halo, G E D B D |
| pasture  | Gentle Giants  | D mixolydian, 4/4                 | brass canon/stretto; dotted spiccato ostinato; solo violin + clarinet inversion; one braam on G | felt piano + harp, D |
| hollow   | Sugar Rush     | D lydian, 4/4 (3+3+2)             | marimba cycling; pizzicato hocket of the diminished cell; woodwind additive; relative-minor lift | marimba + glass halo, D |
| snow     | First Snow     | A lydian, 4/4                     | harp quarters against glass dotted quarters (3:4); clarinet + solo violin canon; flute inversion; pizzicato drops | harp + soft glock, A |
| deep     | Where the Lanterns Swim | F# dorian / A lydian, 4/4 | five-note synth arp phasing through a tidal filter; mirror glass; whale glass; horn + solo violin canon | harp under water + glass, A F# E C# E |
| marigold | Remember Me    | G with borrowed C minor, 4/4      | upright-piano cycle (Cmaj7→Cm6 inside the figure); cell in RH, clarinet canon, flute counterline; pizzicato | big guitar, G |
| finale   | Hallowed Lanterns | D, 4/4 (one-shot)              | the title grown: theme emerging, three-voice canon, Zimmer build, a prepared A-pedal lift, coda | — |
| picture show | The Picture Show | F, 3/4 waltz (on purpose)   | upright piano, solo violin over pizzicato, clarinet, flute | — |

Harmonic colour comes from voicing, pedal points and modal mixture inside
the key; no piece jumps to a remote key.

Ember-born and keeper-rises are short stingers (D major; F# dorian → A).

## Files

```
render.py            command line (targets = pieces/<kind>/<name>.py)
requirements.txt
hlaudio/             the library
  core.py            sample rate, note names, envelopes, noise, Track (circular stereo buffer)
  score.py           notes, a tiny text notation, chords, voice-leading, tempo clocks (rubato)
  arrange.py         arranging helpers (pads by rank, comping, dynamics shapes, augmentation)
  sampler.py         the VSCO 2 CE sampler (catalogue, tuning, layers, loops, legato, divisi)
  orch.py            the orchestra on a stage: seats (pan/width/depth), per-instrument tone
                     chains, hall sends, stem loudness/D-R/brightness report, tape, air
  process.py         compositional processes: modes, the motif as a cell (P/I/R/RI, fragments),
                     additive and cycling figures, canon, hocket, ticking, fitting to harmony
  electro.py         the only synthesised music layers: glass tones, filtered arps, pads,
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
pieces/music/        title arbor grove garden pasture hollow snow deep marigold   (loops)
                     picture_show (the shadow-puppet waltz, loop)
                     finale ember_born keeper_rises                           (one-shots)
pieces/ambience/     arbor grove garden pasture hollow snow deep marigold projector
pieces/sfx/          footsteps ember_chimes lanterns creatures sparkles extras well_and_flytrap
```

Each piece script documents its form at the top (bars, sections, who plays).

## Conventions

* **Loops** are rendered *circularly*: every note, reverb tail, chorus and
  wobble that runs past the end wraps back to the start (period-N circular
  convolution, periodic LFOs, warmed-up filters), so the audio is the steady
  state of the piece playing forever. Files are `loopSeconds + tailSeconds`
  long and the tail is literally the first `tailSeconds` again (seam
  correlation = 1.000000, printed on every render). Music: whole bars of
  about 133–136 s + 4 s (the title 72 s + 4 s, picture show 120 s + 4 s);
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
  footsteps −6 (they repeat constantly); `ui-tap` −9. Mono unless the brief
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
