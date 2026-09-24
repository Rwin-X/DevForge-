# ASCII::FORGE

A single-file, zero-dependency ASCII art generator. Type text, pick a font and a color mode, get a glyph-matrix render you can copy, download, animate, or drop straight into a terminal.

Built entirely in HTML, CSS, and vanilla JavaScript — no build step, no CDN, no external libraries. Open the file in a browser and it works.

## Features

**Input modes**
- **Text** — multi-line input, live render on every keystroke, ten bitmap fonts plus a `MIX` mode that assigns a different font to every character
- **Image** — drop or upload an image, converts to ASCII via a brightness ramp with adjustable output width, four ramp presets, and an invert toggle
- **Webcam** — live camera feed converted to ASCII in real time, mirrored for a natural selfie view, with its own width and ramp controls

**Ten bitmap fonts**
`BLOCK` (solid classic) · `SLIM` (box-drawing line art) · `BLOB` (thick condensed) · `SHADOW` (drop-shadow offset) · `BUBBLE` (rounded outline) · `MARQUEE` (tall seven-row display face) · `THIN` (hairline single-stroke) · `PIXEL` (retro 8-bit chunky) · `BANNER` (double-line box outline) · `TINY` (compact three-row) — plus `MIX`, which cycles a different font per character.

**Fifteen color modes**
Phosphor, Cyan, Amber, Mono, Matrix, Gradient, Rainbow, Glitch, Ocean, Sunset, Toxic, Ember, and three animated modes — Plasma, Pulse, Wave — that shift continuously via `requestAnimationFrame`.

**Exports**
- Copy to clipboard or download as `.txt` (plain text, no markup)
- Download as `.png` (canvas-rendered, colors baked in)
- Download as an animated `.gif` — replays the same staggered letter-entrance animation seen on screen, frame count and duration scaled to the text length, encoded by a hand-written GIF89a encoder (no library)
- **Terminal snippet export** — generates a standalone Python or Bash script that reprints the exact current render, colors included, using 24-bit ANSI escape codes (`\033[38;2;r;g;bm`). Copy it or download a ready-to-run `.py`/`.sh` file.

**Visual details**
- Adjustable glow (off / low / high) as layered `text-shadow`
- Staggered letter-entrance animation on deliberate renders (Render button, font change, mode switch, history recall) — suppressed during live typing and animated-color frames so it never spams
- A quiet particle field drifts behind the whole page; respects `prefers-reduced-motion`
- Session-local render history (last 8 text renders) you can click back into
- Randomize — rolls a random font, color mode, and glow level in one click
- Dark, minimal, terminal-styled interface: phosphor-green accent, scanline overlay, boot-line intro text, bracketed field labels

## Screenshots

*(add screenshots here once you've generated them)*

## Requirements

- Any modern browser (Chrome, Firefox, Safari, Edge). No build tools, no runtime, no internet connection needed after download.
- Webcam mode requires camera permission and a browser that supports `getUserMedia`.

## Installation

This is a single HTML file — there is nothing to build or install.

### Quick start

```bash
git clone https://github.com/black8arch/ascii-forge.git
cd ascii-forge
xdg-open ascii-forge.html   # Linux
# or: open ascii-forge.html       (macOS)
# or: start ascii-forge.html      (Windows)
```

Alternatively, just download `ascii-forge.html` and double-click it.

## Usage

| Action | How |
|---|---|
| Render text | Type in the text panel — renders live on every keystroke, or press **Ctrl/Cmd+Enter** for a full render with the entrance animation |
| Switch input mode | Click the **Text** / **Image** / **Webcam** tabs |
| Change font | Select from the font dropdown (includes `MIX`) |
| Change color mode | Click one of the color chips |
| Adjust glow | Drag the glow slider (off / low / high) |
| Convert an image | Switch to the **Image** tab, drop or click to upload, adjust output width and ramp |
| Go live on webcam | Switch to the **Webcam** tab, click **Start**, adjust width and ramp |
| Copy output | Click **Copy** — plain text, no color codes |
| Save as text | Click **Download .txt** |
| Save as image | Click **Download .png** |
| Save as animation | Click **Download .gif** — works with any font or color, any input mode |
| Get terminal code | Scroll to **[ terminal snippet ]**, pick Python or Bash, then **Copy code** or **Download script** |
| Try a random look | Click **Randomize style** |
| Revisit a past render | Click any entry in the **[ recent ]** history strip |

Text input is capped at 120 characters across multiple lines and automatically uppercased, since the font glyph maps are keyed on uppercase letters, digits, and a small set of punctuation. Unmapped characters fall back to a blank cell rather than breaking the layout.

## Project structure

```
ascii-forge/
├── README.md
├── LICENSE
└── ascii-forge.html   # everything: markup, styles, font data, and render logic in one file
```

Inside `ascii-forge.html`, the `<script>` block is organized top to bottom as:

- **Particle background** — a self-contained `initParticleField()` IIFE, independent of app state
- **Font data** — one object per font (`FONTS.block`, `FONTS.slim`, etc.), each a `{ height, glyphs }` map
- **Render engine** — `getGlyph()` (glyph lookup with fallback), `renderText()` / `renderTextMixed()` (assemble a string into a multi-line glyph grid, single-font or per-character mixed)
- **Color engine** — `colorForCell()` (per-cell color by mode, time-aware for the three animated modes), plus `hslToHex()` / `lerpColor()` helpers
- **GIF encoder** — `buildGifPalette()` / `encodeGif()`, a from-scratch GIF89a writer with no external dependency
- **DOM wiring** — mode-tab switching, image/webcam capture pipelines, the entrance-animation timing (`entranceProgressForColumn()`), terminal code generation (`buildPythonScript()` / `buildBashScript()`), history, and every button/control binding

### Why a hand-rolled bitmap font engine instead of a real font-rendering library

Every font is authored as literal glyph rows (monospace strings), not generated from a `.flf` FIGlet file or rasterized from a system font. This keeps the entire tool at one file with no fetch, no font-parsing code, and no async loading state — at the cost of a smaller, hand-curated character set (uppercase letters, digits, and common punctuation) instead of full Unicode coverage.

### Why a hand-rolled GIF encoder instead of a library

Same reasoning: pulling in `gif.js` or similar would mean a CDN dependency or a bundler, breaking the single-file, zero-dependency property. `encodeGif()` implements GIF89a from scratch — global color table, per-frame graphic control extensions for delay timing, a NETSCAPE2.0 looping extension, and a real LZW compressor (`lzwEncode()`, with dictionary growth and code-size expansion, not a pass-through) — enough to produce valid, properly compressed animated GIFs that decode correctly in standard viewers.


