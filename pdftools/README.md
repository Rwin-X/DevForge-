# NIMBUS

A self-contained, single-file PDF reader built for distraction-free reading. No install, no build step, no backend — open the HTML file in a browser and drop in a PDF.

Two theme variants are included:

| File | Theme |
|---|---|
| `PDFReader.html` | Dark, phosphor-terminal aesthetic |
| `PDFReader_White.html` | Light, paper-white aesthetic |

Both ship with the same feature set and the same soft-light reading modes.

## Features

- **Open a PDF** by clicking `OPEN` or dragging a file onto the window
- **Continuous scroll** through pages, or jump directly via the page number field
- **Page thumbnails** in a collapsible side panel for quick navigation
- **Zoom in / out** and a **fit-width** toggle
- **In-document search** with match highlighting and next/previous navigation (`Ctrl+F`)
- **Selectable, copyable text** — a real text layer sits on top of every rendered page
- **Fullscreen mode**
- **Keyboard shortcuts**:
  - `Ctrl+O` — open file
  - `Ctrl+F` — search
  - `←` / `→` or `Page Up` / `Page Down` — previous / next page
  - `+` / `-` — zoom in / out
  - `Esc` — close search

### Soft-light reading modes

Two independent toggles, combinable:

- **WARM** — lays a soft amber/sepia wash over the page, similar to warm paper tone, without changing the surrounding app chrome
- **DIM** — reduces the brightness of the rendered page itself, for low-light reading

## Tech stack

- Plain HTML, CSS, and JavaScript — no framework, no build step
- [PDF.js](https://mozilla.github.io/pdf.js/) (Mozilla), loaded from a CDN, for PDF parsing, canvas rendering, and text-layer extraction

## Usage

1. Download either `PDFReader.html` or `PDFReader_White.html`
2. Open it in any modern browser (Chrome, Firefox, Edge, Safari)
3. Drag a PDF onto the window, or click `OPEN` / `SELECT FILE` to browse

An internet connection is required on first load, since PDF.js is fetched from a CDN rather than bundled into the file.

## Notes

- All rendering happens client-side; PDFs are never uploaded anywhere
- Designed as a single portable file — safe to rename, move, or share as-is
- Part of the [`devforge`](https://github.com/black8arch/devforge) collection of tools by [black8arch](https://github.com/black8arch)

## License

MIT
