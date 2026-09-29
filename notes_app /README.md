# NoteFlow

A fast, minimalist, local-first note-taking app for developers. Single-file PyQt6 application with a dark, VS Code-inspired interface.

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

## Features

- **Local-first storage** — notes are saved as plain `.md` files on disk, with metadata (titles, timestamps, pins, favorites) tracked in a single JSON file. No accounts, no sync, no cloud.
- **Autosave** — changes are written to disk automatically ~800ms after you stop typing, with a subtle save indicator in the toolbar.
- **Instant search** — filter notes by title or content as you type.
- **Pin & favorite** — keep important notes pinned to the top of the list or mark them as favorites.
- **Code-friendly editor** — monospace font (JetBrains Mono / Cascadia Code / Fira Code, with fallbacks), toggleable line numbers, toggleable word wrap, and 4-space tab insertion.
- **Focus mode** — hide the sidebar, menu bar, and toolbar to write distraction-free.
- **Live stats** — word, line, and character counts in the status bar.
- **Markdown export** — export any note to a `.md` file via the context menu.
- **Keyboard-driven** — full set of shortcuts for creating, saving, searching, and navigating notes.
- **Dark theme** — a crisp, near-black VS Code-flavored palette throughout.

## Screenshots

*Add a screenshot or GIF of the app here.*

## Installation

Requires Python 3.9+.

```bash
pip install PyQt6
```

## Usage

```bash
python notes_app.py
```

Notes are stored at `~/.noteflow/notes/`, with metadata in `~/.noteflow/meta.json`.

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New note |
| `Ctrl+S` | Force save |
| `Ctrl+F` | Focus search box |
| `Ctrl+W` | Close current note |
| `Ctrl+\` | Toggle sidebar |
| `Esc` | Exit focus mode / clear search / focus editor |

## Project Structure

NoteFlow is intentionally a single Python file (`notes_app.py`), organized into clear sections:

- **`NoteStore`** — handles all persistence (JSON metadata + plain-text note files)
- **`CodeEditor`** — the text editor widget, with line numbers and word wrap
- **`Sidebar`** — note list, search, and context menu (rename, pin, favorite, export, delete)
- **`EditorPanel`** — the right-hand editing pane, autosave, and live stats
- **`MainWindow`** — top-level window wiring, menus, and keyboard shortcuts

## Roadmap Ideas

- Tagging and tag-based filtering
- Markdown preview pane
- Multiple note folders/notebooks
- Syntax highlighting for embedded code blocks

## License

MIT — feel free to use, modify, and distribute.
