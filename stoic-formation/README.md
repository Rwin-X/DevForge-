# Stoic Formation

A single-file, zero-dependency visualization that renders Stoic quotes as text in motion: words appear scattered across the screen, drift like suspended particles, then converge — one at a time — into their place in the sentence.

No frameworks. No build step. No bundler. Open the HTML file and it runs.

---

## What it does

On load (and on every subsequent trigger):

1. A quote is fetched live from a public Stoic-quotes API — not a hardcoded list.
2. Each word of the quote is placed at a random position on screen and enters a slow, cloud-like drift (position + slight rotation, looping).
3. After a short interval, words leave the drift one by one, in reading order, and glide to their correct position in the sentence — fading in as they settle, with no overshoot or bounce.
4. Once the full sentence has assembled, the author's name fades in beneath it.
5. The whole cycle — scatter to settled sentence — resolves in roughly 6–7 seconds.

A new quote uses a randomly selected layout (see below), so consecutive runs don't look identical.

---

## Features

- **Live data, not a static pool.** Quotes are fetched at runtime from [`stoic-quotes.com`](https://stoic-quotes.com) (Marcus Aurelius, Seneca, Epictetus). A small local fallback set is used only if the network request fails (offline, CORS, or API downtime) — the fallback is a safety net, not the primary source.
- **Three randomized layouts**, chosen per run:
  - `centered` — single centered line, classic quote-card composition
  - `left` — left-aligned block, larger type, manifesto/poster feel
  - `stacked` — centered block that wraps across multiple lines for longer quotes
- **Subtle background grid.** A faint 48px grid plus corner tick labels give the piece a quiet, instrumented feel without competing with the text. Toggleable.
- **Fullscreen mode** for display on a second monitor, projector, or as ambient screen art.
- **Keyboard-driven** — no mouse required once running.
- **Minimal, monochrome aesthetic** — off-white (`#f7f5f0`) background, near-black (`#111111`) ink, no color, no chrome.

---

## Controls

| Key | Action |
|---|---|
| `Space` or `R` | Fetch and animate the next quote |
| `F` | Toggle fullscreen |
| `G` | Toggle background grid |
| `H` or `?` | Toggle the shortcuts panel |

The **Again** button (top of screen) and the **?** button (bottom-right) provide the same actions with a pointer, for environments without a keyboard.

---

## Running it

This is a static HTML file — open it directly:

```bash
open stoic-formation.html        # macOS
xdg-open stoic-formation.html    # Linux
```

**Note on the live fetch:** some browsers restrict `fetch()` requests made from a page loaded via `file://`. If quotes aren't loading, serve the file over local HTTP instead:

```bash
python3 -m http.server 8000
# then open http://localhost:8000/stoic-formation.html
```

Under `http://`, the live API call works normally.

---

## Architecture

Everything lives in one file:

- **CSS** handles all motion primitives — the drift loop is a CSS `@keyframes` animation; the convergence-to-sentence motion is a per-word CSS `transition` on `transform`/`opacity`/`filter`, driven from JS.
- **JS** is responsible for: fetching the quote, laying out invisible "slot" elements to compute each word's final `(x, y)`, spawning the floating word elements, and staggering the settle sequence so words land one at a time rather than all at once.
- No canvas, no SVG, no animation library. Just DOM elements and native browser easing.

Timing is parameterized near the top of the `run()` function (`floatDuration`, `travelTime`, `pauseBetween`) if you want to slow down, speed up, or restyle the sequence.

---

## Customization

- **Swap the quote source** — replace the `fetchQuote()` implementation to point at any API returning `{ text, author }`, or point it at a local JSON file for fully offline use.
- **Add a layout** — add a new `.layout-*` rule under `#sentence-line` in the CSS and register its class name in the `LAYOUTS` array in JS.
- **Change the palette** — everything routes through two CSS custom properties, `--bg` and `--ink`, in `:root`.

---

Quotes served by [stoic-quotes.com](https://stoic-quotes.com), a free public API of Stoic quotations (Marcus Aurelius, Seneca, Epictetus).

## License

MIT — do whate
