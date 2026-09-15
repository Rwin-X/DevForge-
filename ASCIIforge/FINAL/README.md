<div align="center">

```
   ▄████████    ▄████████  ▄████████  ▄█     ▄███████▄  
  ███    ███   ███    ███ ███    ███ ███    ███    ███  
  ███    ███   ███    █▀  ███    █▀  ███▌   ███    ███  
  ███    ███  ▄███▄▄▄     ███        ███▌   ███    ███  
▀███████████ ▀▀███▀▀▀     ███        ███▌ ▀█████████▀   
  ███    ███   ███    █▄  ███    █▄  ███    ███          
  ███    ███   ███    ███ ███    ███ ███    ███          
  ███    █▀    ██████████ ████████▀  █▀    ▄████▀        

               ::  F O R G E  ::
```

**A browser-based ASCII art generator — text, images, and a live webcam feed, forged into terminal-ready glyphs.**

[![Made with](https://img.shields.io/badge/made%20with-HTML%2FCSS%2FJS-4ee08a?style=flat-square&labelColor=0a0e0c)](.)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-4fd8e0?style=flat-square&labelColor=0a0e0c)](.)
[![License](https://img.shields.io/badge/license-MIT-d9a55a?style=flat-square&labelColor=0a0e0c)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-any%20modern%20browser-c3d9cd?style=flat-square&labelColor=0a0e0c)](.)

</div>

---

🖥️ ASCII::FORGE turns text, images, and your webcam into ASCII/block-character art, live, in a single HTML file — no build step, no server, no install. Open it and it runs. Pick a font, pick a color mode, watch it render in a phosphor-green terminal console, then export it as `.txt`, `.png`, `.gif`, or a self-contained colored terminal script.

Everything — ten bitmap fonts, fifteen color engines, a GIF encoder, and a software 3D renderer — lives in one `.html` file with no external requests and no dependencies.

## ✨ Features

- 🔤 **Four input modes** — `Text`, `Image`, `Webcam`, and `3D`, switchable from a single console without reloading the page
- 🎨 **Ten bitmap fonts** — `block`, `slim`, `blob`, `shadow`, `bubble`, `marquee`, `thin`, `pixel`, `banner`, `tiny`, plus a `mix` mode that randomizes per-glyph
- 🌈 **Fifteen color engines** — Phosphor, Cyan, Amber, Gradient, Rainbow, Matrix, Glitch, Mono, Ocean, Sunset, Toxic, Ember, and three real-time animated modes: Plasma, Pulse, and Wave
- 🖼️ **Image-to-ASCII conversion** — drop in any image and it's resampled to a grid of characters weighted by luminance
- 📷 **Live webcam ASCII feed** — captures from `getUserMedia` and re-renders every frame as ASCII in real time
- 🧊 **Software 3D text renderer** — extrudes ASCII characters into a spinning, tiltable 3D word rendered entirely on `<canvas>`, no WebGL
- 🎞️ **Built-in GIF encoder** — exports the entrance animation (or a full 360° spin for 3D mode) as a looping `.gif`, encoded client-side
- 📤 **Four export formats** — plain `.txt`, rendered `.png`, animated `.gif`, and a standalone Python/Bash script that reprints the exact same colored art in a terminal via 24-bit ANSI escapes
- 🕹️ **Session history & randomizer** — the last eight renders are kept in-memory for one-click recall, plus a "surprise me" button that rolls a random font/color/glow combo
- 🌫️ **Terminal-styled interface** — scanlines, vignette, flicker, and a live ember-particle background, all rendered without any image assets

## Screenshots

*(add screenshots or a `.gif` export here once you've generated one — the app itself can produce these via the "Download .gif" button)*

## Requirements

- Any modern desktop browser with `<canvas>` support (Chrome, Firefox, Edge, Safari)
- No build tools, package manager, or internet connection required to run it
- Webcam mode additionally requires:
  - A webcam
  - The page to be served over `https://` or `localhost` (browsers block `getUserMedia` on plain `http://`)

## Installation

There is nothing to install. ASCII::FORGE is a single self-contained HTML file.

### Quick start

```bash
git clone https://github.com/black8arch/ascii-forge.git
cd ascii-forge
xdg-open ascii-forge.html   # Linux
# open ascii-forge.html     # macOS
# start ascii-forge.html    # Windows
```

### Webcam mode over a local server (optional)

Some browsers still restrict camera access on a `file://` page. If Webcam mode doesn't prompt for permission, serve the file locally instead:

```bash
python3 -m http.server 8000
# then open http://localhost:8000/ascii-forge.html
```

## Usage

| Action | How |
|---|---|
| Switch input mode | Click `Text`, `Image`, `Webcam`, or `3D` in the tab bar |
| Change font | Select a typeface from the font dropdown (Text mode) |
| Change color engine | Click a color chip — animated modes (Plasma, Pulse, Wave) render live |
| Adjust glow / depth / tilt | Drag the relevant slider in the console |
| Randomize the look | Click the dice / random button |
| Recall a past render | Click any entry in the history strip |
| Copy art as plain text | `Copy` button |
| Export as text file | `Download .txt` |
| Export as image | `Download .png` |
| Export as looping animation | `Download .gif` |
| Export as a runnable terminal script | `Copy code` / `Download script` (colored via ANSI 24-bit escapes) |

## Project structure

```
ascii-forge/
├── ascii-forge.html   # entire application: markup, styles, and logic
│                       #   - font bank (10 bitmap typefaces)
│                       #   - color engine (15 modes, 3 animated via requestAnimationFrame)
│                       #   - image/webcam-to-ASCII sampling
│                       #   - software 3D extrusion + rotation renderer (canvas 2D, no WebGL)
│                       #   - client-side GIF encoder
│                       #   - ANSI terminal script generator (Python/Bash export)
├── LICENSE
└── README.md
```

Everything is intentionally kept in one file: there is no build pipeline, no bundler, and no external script tags. Cloning the repo and opening the file is the entire setup process.

## License

MIT — see [LICENSE](LICENSE).
