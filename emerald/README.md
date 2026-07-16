# Local AI Notes

A small, offline personal knowledge base. Notes are plain `.md` files in a
folder you choose. No accounts, no cloud sync, no telemetry, no plugins,
no payments — everything runs on your machine.

## What it does

- **3-panel UI**: note list · Markdown editor · graph view, dark/phosphor theme
- **Plain `.md` files** — your notes folder is the entire database. Open it
  in any other editor, back it up with any tool, no lock-in.
- **`[[Wiki Links]]`** between notes, with automatic backlinks
- **Graph view** — each note is a node, each wiki link is an edge.
  Scroll to zoom, click-drag empty space to pan, click a node to open it,
  search box highlights matching nodes.
- **Auto-save** — edits are written to disk ~400ms after you stop typing.
  No save button.
- **Local AI helper**, exactly 3 actions, all on-device, zero network calls:
  - **Summarize** — short extractive summary of the current note
  - **Suggest Tags** — keyword-based tag suggestions
  - **Related Notes** — other notes in your vault ranked by similarity

There is no model download and no API key — the "AI" here is plain text
analysis (word frequency, TF-IDF, Jaccard similarity) that runs instantly
and never leaves your computer.

## Setup

```bash
pip install -r requirements.txt --break-system-packages
```

(`markdown` is optional — the app falls back to a small built-in renderer
for the Preview tab if it isn't installed. `PyQt6` is required.)

## Run

```bash
cd app
python3 main.py
```

On first launch it asks you to choose (or create) a folder — that's your
notes vault. It remembers the folder for next time in a tiny local config
file (`app/.local_ai_notes_config.json`), which stores nothing but that
one path.

## Using it

- **New Note** — creates `Title.md` in your vault folder
- Type `[[Note Title]]` anywhere in the editor to link to another note.
  If it doesn't exist yet, the Preview tab shows it as a broken link you
  can click to create.
- The **Backlinks** panel under the editor lists every note that links to
  the one you're currently viewing.
- **Rename** updates the filename and rewrites `[[old name]]` references
  across your whole vault to point at the new name.
- The **Graph** panel rebuilds automatically whenever notes are added,
  edited, renamed, or deleted.

## File layout

```
app/
  main.py            entry point
  main_window.py      3-panel UI, autosave, wiring
  note_store.py        filesystem layer (read/write .md, wikilinks, backlinks)
  ai_helper.py          summarize / tags / related — all offline
  graph_widget.py        zoomable/pannable node graph
  markdown_render.py    Markdown + wikilink -> HTML for the Preview tab
```

Everything is plain, readable Python — no framework magic, no hidden
network calls, no background services.

+ created by RWIN-X
>
