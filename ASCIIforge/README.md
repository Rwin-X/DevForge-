# ASCII::FORGE

A single-file, zero-dependency ASCII art generator. Type a word, pick a font and a color mode, get a glyph-matrix render you can copy or download.

Built entirely in HTML, CSS, and vanilla JavaScript — no build step, no CDN, no external libraries. Open the file in a browser and it works.

## Features

- **Six bitmap fonts** — `BLOCK` (solid classic), `SLIM` (box-drawing line art), `BLOB` (thick condensed), `SHADOW` (drop-shadow offset), `BUBBLE` (rounded outline), `MARQUEE` (tall seven-row display face)
- **Eight color modes** — Phosphor, Cyan, Amber, Mono, Matrix (row-based shade falloff), Gradient (phosphor-to-cyan lerp), Rainbow (hue sweep across columns), Glitch (corrupted-pixel flecks with a periodic clip-path animation)
- **Adjustable glow** — off / low / high, applied as layered `text-shadow` on rendered glyphs
- **Copy to clipboard** and **download as `.txt`**, both exporting plain text with no markup
- **Randomize** — rolls a random font, color mode, and glow level in one click
- **Self-contained font engine** — each font is a plain glyph map (`{ "A": ["row1","row2",...] }`); adding a new font means adding one object, no external font files or canvas rasterization involved
- Dark, minimal, terminal-styled interface: phosphor-green accent, scanline overlay, boot-line intro text, bracketed field labels

## Requirements

- Any modern browser (Chrome, Firefox, Safari, Edge). No build tools, no runtime, no internet connection needed after download.

## Installation

This is a single HTML file — there is nothing to build or install.

### Quick start


Alternatively, just download `ascii-forge.html` and double-click it.

## Usage

| Action | How |
|---|---|
| Render text | Type in the input field — renders live on every keystroke, or press Enter |
| Change font | Select from the font dropdown |
| Change color mode | Click one of the color chips |
| Adjust glow | Drag the glow slider (off / low / high) |
| Copy output | Click **Copy** — copies plain text, no color codes |
| Save output | Click **Download .txt** — saves as `<your-text>.txt` |
| Try a random look | Click **Randomize style** |

Input is capped at 24 characters and automatically uppercased, since the font glyph maps are keyed on uppercase letters, digits, and a small set of punctuation. Unmapped characters fall back to a blank cell rather than breaking the layout.

## Project structure

```
ascii-forge/
├── README.md
├── LICENSE
└── ascii-forge.html   # everything: markup, styles, font data, and render logic in one file
```

Inside `ascii-forge.html`, the `<script>` block is organized top to bottom as:

- **Font data** — one object per font (`FONTS.block`, `FONTS.slim`, etc.), each a `{ height, glyphs }` map
- **Render engine** — `getGlyph()` (glyph lookup with fallback) and `renderText()` (assembles a string into a multi-line glyph grid)
- **Color engine** — `colorForCell()` (per-cell color by mode), plus `hslToHex()` / `lerpColor()` helpers for the gradient and rainbow modes
- **DOM wiring** — populates the font dropdown and color chips from the data objects above, binds input/button events, and drives the `draw()` function that paints the output

### Why a hand-rolled bitmap font engine instead of a real font-rendering library

Every font is authored as literal glyph rows (monospace strings), not generated from a `.flf` FIGlet file or rasterized from a system font. This keeps the entire tool at one file with no fetch, no font-parsing code, and no async loading state — at the cost of a smaller, hand-curated character set (uppercase letters, digits, and common punctuation) instead of full Unicode coverage.

## License

MIT — see [LICENSE](LICENSE).

