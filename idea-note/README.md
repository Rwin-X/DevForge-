# Idea Book

A local-only, distraction-free idea vault. Write in **Markdown+**, link ideas
together with `[[wikilinks]]`, and see the whole vault as a constellation
graph. No cloud, no login, no telemetry — just a SQLite file on disk and
your own thinking.

Built in the same spirit as `devforge`: minimal, dark, instrument-grade UI,
zero unnecessary dependencies on the network.

---

## Run it

```bash
pip install -r requirements.txt
python main.py
```

Requires Python 3.10+. Data lives at `~/.ideabook/vault.db` — delete that
file to reset the vault, or copy it to back up / sync manually.

## Features

**Write** — a monospace, distraction-free editor. No toolbar clutter.

**Markdown+** — standard markdown, extended with:

| Syntax | Result |
|---|---|
| `[[Note Title]]` | Link to another idea (auto-creates it if it doesn't exist yet) |
| `[[Note Title\|label]]` | Link with custom display text |
| `#tag` | Inline tag chip, click to filter the sidebar |
| `> [!idea] Title` | Idea callout |
| `> [!note]` | Note callout |
| `> [!warn]` | Warning callout |
| `> [!todo]` | Todo callout |
| `- [ ]` / `- [x]` | Checkboxes |
| fenced code blocks | Syntax highlighted |

**Read** — rendered preview pane. Click any `[[link]]` to jump straight to
that idea; dangling links (to ideas that don't exist yet) render dimmed and
create the note on click.

**Graph** — every idea in the vault as a node, every `[[link]]` as an edge,
laid out by a live force-directed simulation. Node size reflects how many
connections an idea has. Drag nodes, scroll to zoom, double-click to open.

## Architecture

```
ideabook/
├── main.py                  entry point
├── core/
│   ├── store.py              SQLite persistence, link/tag indexing, graph queries
│   └── markdown_plus.py      Markdown+ parser/renderer
└── ui/
    ├── theme.py               palette + QSS stylesheet (single source of truth)
    ├── titlebar.py            frameless-window macOS-style traffic lights
    ├── graph_view.py          force-directed constellation widget (QPainter)
    └── main_window.py         sidebar, editor, preview, view switching, wiring
```

No web view, no Electron, no bundled browser — the preview pane is a native
`QTextBrowser` and the graph is hand-drawn with `QPainter`. This keeps
startup fast and the whole thing under ~15MB installed (PySide6 itself is
the only heavy dependency).

## Design notes

- Palette is a warm near-black (`#161616`) rather than pure black, with a
  single desaturated amber accent (`#C9995C`) used only for selection,
  links, and pinned items — everything else stays quiet.
- The editor uses a monospace face; the chrome around it uses the system
  UI font, so the writing surface reads as an instrument and the frame
  disappears.
- Titlebar is custom-drawn (frameless window + traffic-light dots) rather
  than relying on the OS default, for a consistent look across platforms.
- Autosave runs 600ms after you stop typing — no explicit save action,
  no "unsaved changes" anxiety.
