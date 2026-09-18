# Vedit — a modal text editor with a modern, themeable UI

A vim-style modal editor built with PyQt6: real Normal / Insert / Visual /
Visual-Line / Replace modes and vim's core motions and operators, wrapped
in a modern UI with tabs, a file tree, syntax highlighting, and five
built-in color themes. Cross-platform — runs the same on Linux, Windows,
and macOS.

## Features

- **Real modal editing** — Normal, Insert, Visual, Visual Line, and
  Replace modes, not just a few keyboard shortcuts bolted onto a normal
  text box
- **Motions** — `h j k l`, `w b e`, `0 ^ $`, `gg G`, with numeric counts
  (`3j`, `5dd`, …)
- **Operators** — `d c y` combined with motions and text ranges
  (`dw`, `cw`, `dd`, `yy`, `dG`, …), plus the classic `cw` vim quirk
  (stops at the word, doesn't eat trailing whitespace)
- **Visual mode** — character-wise and line-wise selection, with
  delete/yank/change/case-toggle applied to the selection
- **Undo/redo**, `x X D C p P ~ J R`, and more
- **Five built-in themes** — Obsidian (dark, default), Paper Light,
  Nord Deep, Amber Terminal, Midnight Violet — switchable live from the
  Theme menu or `:theme <name>`
- **Syntax highlighting** via Pygments — works for any language Pygments
  recognizes, colored per the active theme
- **Tabs** — multiple open buffers, closable and reorderable
- **File tree sidebar** — browse and open files by double-click
- **Command line** (`:`) — `:w`, `:q`, `:wq`, `:q!`, `:x`, `:qa`, `:wqa`,
  `:e <file>`, `:tabnew`, `:bn` / `:bp`, `:theme <name>`, `:%s/pat/rep/g`,
  and `:<N>` to jump to a line
- **Search** — `/` forward, `?` backward
- **Status bar** — current mode (color-coded), filename, active theme,
  cursor position, line count

## Requirements

- Python 3.10+
- PyQt6, Pygments, chardet

## Setup

```bash
pip install PyQt6 Pygments chardet --break-system-packages
# or, inside a virtualenv:
python3 -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate
pip install PyQt6 Pygments chardet
```

## Run

```bash
python3 vedit.py
python3 vedit.py somefile.py            # open a file directly
python3 vedit.py file1.py file2.py      # open several, each in its own tab
```

On Windows, this works the same way from PowerShell or Command Prompt
(`python vedit.py`), and the file tree, tabs, and theme menu all behave
identically. `Consolas` is used automatically as the editor font if
`JetBrains Mono` isn't installed.

## Keybindings

### Modes
| Key | Action |
|---|---|
| `i` / `a` | Insert before / after cursor |
| `I` / `A` | Insert at start / end of line |
| `o` / `O` | Open new line below / above, enter Insert |
| `Esc` | Back to Normal mode |
| `v` | Visual (character-wise) |
| `V` | Visual Line |
| `R` | Replace mode (overtype) |

### Motions
| Key | Action |
|---|---|
| `h j k l` | Left / down / up / right |
| `w` / `b` / `e` | Word forward / backward / word-end |
| `0` / `^` / `$` | Start of line / first non-blank / end of line |
| `gg` / `G` | Top / bottom of file |
| `3j`, `5w`, … | Any motion with a numeric count prefix |

### Editing
| Key | Action |
|---|---|
| `x` / `X` | Delete char forward / backward |
| `dd` / `yy` / `cc` | Delete / yank / change whole line(s) |
| `dw` / `yw` / `cw` | Operator + motion (word, or any motion) |
| `D` / `C` | Delete / change to end of line |
| `p` / `P` | Paste after / before cursor or line |
| `u` / `Ctrl+R` | Undo / redo |
| `~` | Toggle case under cursor |
| `J` | Join line below into current line |

### Visual mode
| Key | Action |
|---|---|
| `d` / `x` | Delete selection |
| `y` | Yank selection |
| `c` | Change selection |
| `u` / `U` | Lowercase / uppercase selection |
| `:` | Open command line pre-filled with `'<,'>` (range) |

### Command line
| Command | Action |
|---|---|
| `:w [file]` | Write (save), optionally to a new path |
| `:w!` | Force write |
| `:q` / `:q!` | Quit tab / force quit, discarding changes |
| `:wq` / `:x` | Write then quit |
| `:qa` / `:wqa` | Quit all tabs / write and quit all |
| `:e <file>` | Open a file in a new tab |
| `:tabnew [file]` | New empty tab, or open a file in one |
| `:bn` / `:bp` | Next / previous tab |
| `:theme <name>` | Switch color theme |
| `:%s/pat/rep/g` | Substitute across the whole buffer |
| `:'<,'>s/pat/rep/` | Substitute across a Visual-mode selection |
| `:<N>` | Jump to line N |

Full keybinding list is also available in-app under **Help → Keybindings**.

## Project structure

```
vedit.py          Main window: tabs, sidebar, status bar, command line, file I/O
modal_editor.py    The modal editing engine (all vim-like logic lives here)
theme.py           Theme definitions (palette + QSS) and the QSS builder
syntax.py          Pygments-based syntax highlighter, theme-aware
commands.py        Ex-command parsing (:w, :q, :%s/../.., etc.)
```

## Notes on scope

This implements the vim motions and operators people reach for
day-to-day — it's a practical subset, not a complete reimplementation of
vim's editing model. Things intentionally left out: registers beyond a
single clipboard slot, macros, marks, jumps, folds, and multi-file
buffers list (`:ls`). These would be natural next additions if you want
to extend it.


created by Rwin-X
