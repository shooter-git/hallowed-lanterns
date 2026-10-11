# tools/audio — the Hallowed Lanterns sound renderer

Everything in `public/audio/` is **synthesised from scratch** by this folder:
no samples, soundfonts or recordings. It is our own work (`"license": "own"`
in `assets.lock.json`). Python + numpy/scipy, with a few sample-by-sample
kernels compiled by numba; ffmpeg (libmp3lame) encodes and measures.

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

A music loop takes 2–5 minutes on 8 cores (choirs and string sections are the
slow part), an ambience under a minute, all the sfx about two minutes. Peak
memory is around 1–1.5 GB per process.

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

Every chapter weaves the motif in, on its own instrument and in its own key
(the chimes `sfx/ember-chime-<chapter>` use the same key as that chapter's
music, so the Ember always sounds in tune with what is playing):

| chapter  | music          | key                | the motif on…            | motif notes        |
|----------|----------------|--------------------|--------------------------|--------------------|
| arbor    | Sundown        | D major, 6/8       | music box                | D B A F# A         |
| grove    | Blue Hour      | B minor → D        | celesta                  | D B A F# A         |
| garden   | Lantern Song   | G major pentatonic | zither (and flute)       | G E D B D          |
| pasture  | Gentle Giants  | D, open fifths     | horn & cello             | D B A F# A         |
| hollow   | Sugar Rush     | D major            | glockenspiel, pumpkins   | D B A F# A         |
| snow     | First Snow     | A major, 3/4       | celesta, sleigh bells    | A F# E C# E        |
| deep     | Where the Lanterns Swim | F# minor / A | whale-song choir     | F# D C# A C# (minor) |
| marigold | Remember Me    | G major            | nylon guitar             | G E D B D          |
| finale   | Hallowed Lanterns | D → E major     | everyone, in turn        | all of the above   |
| picture show | The Picture Show | F major, 3/4 waltz | upright piano, celesta | F D C A C          |

## Files

```
render.py            command line (targets = pieces/<kind>/<name>.py)
requirements.txt
hlaudio/             the library
  core.py            sample rate, note names, envelopes, noise, Track (circular stereo buffer)
  score.py           notes, a tiny text notation, chords, voice-leading, tempo clocks (rubato)
  arrange.py         arranging helpers (pads by rank, comping, dynamics shapes, augmentation)
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
pieces/music/        arbor grove garden pasture hollow snow deep marigold   (loops)
                     picture_show (the shadow-puppet waltz, loop)
                     finale ember_born keeper_rises                           (one-shots)
pieces/ambience/     arbor grove garden pasture hollow snow deep marigold projector
pieces/sfx/          footsteps ember_chimes lanterns creatures sparkles extras
```

Each piece script documents its form at the top (bars, sections, who plays).

## Conventions

* **Loops** are rendered *circularly*: every note, reverb tail, chorus and
  wobble that runs past the end wraps back to the start (period-N circular
  convolution, periodic LFOs, warmed-up filters), so the audio is the steady
  state of the piece playing forever. Files are `loopSeconds + tailSeconds`
  long and the tail is literally the first `tailSeconds` again (seam
  correlation = 1.000000, printed on every render). Music: 120 s + 4 s.
  Ambience: 60 s + 3 s.
* **Mastering**: music −16 LUFS integrated (First Snow −17, it is meant to be
  hushed), ambience −20 LUFS, true peak ≤ −2 dBTP before encoding; every MP3
  is decoded and measured with `ffmpeg -af ebur128=peak=true` and nudged until
  it lands within ±0.35 LU and ≤ −1.6 dBTP.
* **SFX** are true-peak normalised by role: chimes, knocks and bells −3 dBTP;
  softer things (snowflakes, bubbles, squeaks, swings, butterflies) −4…−5;
  footsteps −6 (they repeat constantly); `ui-tap` −9. Mono unless the brief
  said stereo (ember chimes, sprinkle-burst, butterflies, wish-hang, fog-swirl).
* MP3: music 128 kbps CBR, ambience and sfx 96 kbps CBR, 44.1 kHz, no ID3 tag
  (the LAME/Xing header stays, so decoders trim the encoder delay).
* `sfx/water-lap.mp3` is rendered circularly and is exactly 4.0 s, so it can
  be looped directly (`AudioBufferSourceNode.loop`); the PCM is seamless, the
  MP3 frame boundary leaves at most a tiny step around −40 dBFS.
* Size: everything in `public/audio/` is about 28.5 MB (budget 30 MB). Music
  loops are 120 s and ambiences 60 s (the minimum of the brief) to stay small.
* Nothing is synthesised above ~9.5 kHz and instruments roll off from 6 kHz:
  the soundtrack should feel warm, never glassy.

## Adding or changing a piece

Write notes with `seq("D5:1 | B5:2 A5:1 F#5:1 A5:2", start)` (durations in the
piece's beat unit), chords with `prog("G:3 D/F#:3")`, accompaniment with
`pad`, `arpeggio`, `bass_line`, `comp`; convert with a `Clock`; render each
part with an instrument into a `Mix` track; send to reverbs; call
`finish_loop` (circular) or `finish_oneshot`. Stem loudness is printed while
rendering (`stem … LUFS`) to help balance.
