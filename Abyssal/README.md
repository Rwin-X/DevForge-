# Abyssal

A single-file, zero-dependency ASCII sea generator. Four ways to read the water — stacked ridgelines, an overhead surface, a side-on swell, or open chop — all built from seeded value noise, none of it borrowed from a sample or an image.

Built entirely in HTML, CSS, and vanilla JavaScript — no build step, no CDN, no external libraries. Open the file in a browser and it works.

## Features

**Four readings**
- **Ridgeline** — stacked horizon traces, far to near. Each trace clears the band below its own crest before drawing, so nearer traces occlude the ones behind them instead of tangling with them — the effect that makes a stack of lines read as depth.
- **Surface** — an overhead height field mapped through a density ramp; two crossed noise fields give it swell and cross-chop at once.
- **Swell** — a single horizon in side elevation, filled beneath the line with a ramp that thins as it goes deeper.
- **Chop** — several small wave trains interfering at different headings, for an even, restless field with no dominant direction.

**Deterministic sea** — every trace comes from a seeded value-noise field (`hash1` → `noise1` → `fbm`), so a given seed always regenerates the same water. New seed and Randomise both log a fresh one; nothing here is `Math.random()` in the render path itself.

**Reading controls** — span (40–180 columns), trace count, line pitch, amplitude, swell period, turbulence (fbm octaves), and peak focus (how tightly crests gather toward the centre of the span, modelled as a gaussian envelope).

**Trace controls**
- Pen: `Slope` (picks `/`, `\`, or `_` from the local gradient, so the line reads as genuinely drawn), `Solid`, `Hash`, `Dot`
- Density ramp (used by Surface, Swell, and Chop): Classic (` .:-=+*#%@`), Blocks (` ░▒▓█`), Soft (` .·•●●`), Binary (` .01`)

**Chart controls**
- Palette: Bone, Fathom, Sodium, Tide — each a two-colour gradient keyed to depth, not a flat colour
- Stock: **Ink on dark** or **Ink on paper** — the paper mode swaps in darkened palette variants so the ink still reads against a light chart background, rather than just inverting colours
- Drift: continuous animation speed, running on `requestAnimationFrame`; Pause/Resume stops it in place. Respects `prefers-reduced-motion` on load.

**Exports** — Copy to clipboard, download as `.txt` (trailing blank columns trimmed per row), or download as `.png` (canvas-rendered at the current palette and stock). Filenames carry the mode and seed, e.g. `abyssal_ridge_20260915.png`.



## Requirements

Any modern browser (Chrome, Firefox, Safari, Edge). No build tools, no runtime, no internet connection needed after download.


Alternatively, just download `abyssal.html` and double-click it.

## Usage

| Action | How |
|---|---|
| Switch reading | Click **Ridgeline** / **Surface** / **Swell** / **Chop** |
| Reshape the sea | Adjust Span, Traces, Line pitch, Amplitude, Swell period, Turbulence, Peak focus |
| Change how it's drawn | Pick a Pen and a Density ramp |
| Change how it's printed | Pick a Palette and a Stock (Ink on dark / Ink on paper) |
| Animate | Drag Drift above 0; **Pause drift** / **Resume drift** to stop and start in place |
| Get a new sea at the same settings | **New seed** |
| Get a new sea *and* new settings | **Randomise** |
| Save it | **Copy**, **Save .txt**, or **Save .png** |

The sounding line under the chart (`trace` / `span` / `sea state` / `period` / `seed`) always reflects what's currently on screen — sea state is a Beaufort-style band derived from the amplitude and turbulence actually in use, not a fixed label.

## Project structure

```
abyssal/
├── README.md
├── LICENSE
└── abyssal.html   # everything: markup, styles, noise, and the four sea builders in one file
```

Inside `abyssal.html`, the `<script>` block runs top to bottom as:

- **Noise** — `hash1()` (seeded integer hash), `noise1()` (smoothstep value noise), `fbm()` (fractal sum of octaves) — the only source of randomness in the render path, all seeded
- **Pens & ramps** — `RAMPS` (character density gradients) and `PENS` (`slopeGlyph()` picks a line character from the local gradient; `solid`/`hash`/`dot` are constant)
- **Palettes** — `PALETTES` and `PAPER_PALETTES`, each a `t → hex` gradient function keyed to depth
- **Sea builders** — `buildRidge()`, `buildSurface()`, `buildSwell()`, `buildChop()`, each returning a `{ grid, depth, w, h }` the paint step can render without knowing which mode produced it
- **Paint** — `paint()` walks each row and emits colour runs (`<span>` per run of same-coloured characters, not per character), then `updateSounding()` refreshes the readout line
- **Export** — `plainText()` for Copy/.txt, and a canvas re-render in `pngBtn`'s handler for `.png`

### Why runs instead of per-character spans

A 180×60 sea is 10,800 cells. Painting one `<span>` per cell would mean that many DOM nodes on every animated frame. `paint()` instead merges consecutive same-coloured characters into a single run, which is normally a small fraction of that count — a flat-coloured Bone ridgeline can paint an entire row as one run.

### Why a hand-rolled noise function instead of a library

Same reasoning as the sibling projects in this set: pulling in a noise library would mean a CDN dependency or a bundler, breaking the single-file property. `fbm()` is a few lines on top of a seeded hash and is enough to drive all four readings.

## License

MIT
