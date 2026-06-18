[README.md](https://github.com/user-attachments/files/29107823/README.md)
# VaultNotes

A minimal, keyboard-first Markdown note-taking application built with Python and PySide6.

Inspired by Obsidian and VS Code — no Electron, no web tech. Pure Qt.

---

## Features

- **Markdown editor** with live syntax highlighting (headings, bold, italic, code, tags, links)
- **Live preview / split view** with rendered HTML
- **Folder tree** with right-click context menus
- **Tag system** — auto-extracted `#tags` from note content
- **Full-text search** with title/content/tag scoring
- **Auto-save** every 30 seconds + manual Ctrl+S
- **Line numbers** in editor
- **Smart list continuation** on Enter
- **Dark theme** — deep blue/white accent palette

---

## Setup

```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python main.py
```

**Requirements:** Python 3.11+, PySide6 6.6+

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New note |
| `Ctrl+S` | Save current note |
| `Ctrl+K` | Focus search |
| `Ctrl+W` | Close current tab |
| `Ctrl+Tab` | Next tab |
| `Ctrl+Shift+E` | Toggle sidebar |
| `Escape` | Clear search |

---

## Data Storage

Notes are stored as plain `.md` files in:

```
~/.vaultnotes/vault/
```

Metadata (timestamps) is stored alongside in:

```
~/.vaultnotes/.meta/
```

You can back up, sync (via Syncthing, Dropbox, etc.), or version-control the vault directory directly.

---

## Project Structure

```
vaultnotes/
├── main.py              # Entry point
├── requirements.txt
├── README.md
└── vaultnotes/
    ├── __init__.py
    ├── app.py           # Main window
    ├── editor.py        # Markdown editor + syntax highlighter
    ├── preview.py       # HTML preview renderer
    ├── sidebar.py       # File tree, search, tag browser
    ├── storage.py       # Filesystem note management
    └── theme.py         # Colors + Qt stylesheet
```
