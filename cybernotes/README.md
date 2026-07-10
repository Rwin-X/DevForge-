# CyberNotes

not minimal ((will be deleted))

Fast, minimal, IDLE-style desktop notes editor for security certification study
(Network+ / Security+ / CEH / OSCP). Part of the `devforge` toolkit.

## Why

You don't need a database or a web app to take study notes. You need a text
box that opens instantly and files you can `grep`, `diff`, and commit to git.
That's what this is — zero dependencies, stdlib-only, single file.

## Requirements

- Python 3.9+
- `tkinter` (ships with the standard python.org installers on Windows/macOS)

**Linux only:** `tkinter` is often *not* bundled with system Python and needs
a separate package:

```bash
# Debian / Ubuntu
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

If you run `python3 cybernotes.py` and get `ModuleNotFoundError: No module
named 'tkinter'`, this is why — install the package above and it'll work.

## Run

```bash
python3 cybernotes.py
```

On first launch it creates a `notes/` folder next to the script with five
subfolders: `General`, `Network+`, `Security+`, `CEH`, `OSCP`.

## Usage

| Action | How |
|---|---|
| New note | `+ NEW` button or `Ctrl+N` — creates it in the currently-selected track |
| Save | `Ctrl+S` |
| Open a note | Click it in the left panel |
| Rename | Select a note, click `RENAME` |
| Delete | Select a note, click `DELETE` (asks for confirmation) |

Notes are plain `.md` files under `notes/<Track>/<name>.md`. Nothing else
touches that folder — open it in any editor, `grep -r` across it, or `git
init` it directly.

```
notes/
├── General/
├── Network+/
├── Security+/
├── CEH/
└── OSCP/
    └── buffer-overflow-notes.md
```

## Design notes

- Single file, stdlib only (`tkinter`, `pathlib`) — no `pip install` needed.
- Unsaved changes prompt before switching notes or closing the window.
- No search, no tags, no syntax highlighting by design — this is meant to
  stay an editor, not grow into an IDE. If you want grep-based search across
  notes later, the plain-`.md` structure supports that without any app
  changes (`grep -rn "keyword" notes/`).

## Testing

`test_app.py` is a headless functional test that instantiates the real
`CyberNotes` app under Xvfb and drives its actual widgets (not a
reimplementation) through create/edit/save/rename/delete. Run it with:

```bash
xvfb-run -a python3 test_app.py
```
