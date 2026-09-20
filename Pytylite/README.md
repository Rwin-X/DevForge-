<h1 align="center">PyLite</h1>

<p align="center">
  A minimal, fast Python editor for Linux with a built-in runner.<br>
  Think IDLE, but with a modern dark UI and VS Code–style syntax colours.
</p>

<p align="center">
  <img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white">
  <img alt="PyQt6" src="https://img.shields.io/badge/GUI-PyQt6-41CD52">
  <img alt="Platform: Linux" src="https://img.shields.io/badge/platform-Linux-lightgrey">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue">
</p>



## Why PyLite?

IDLE is always there but looks dated. VS Code and PyCharm are powerful but heavy
when all you want is to write a script and run it. PyLite sits in between: it
starts instantly, has no project model, no plugins and no configuration files —
just an editor, a Python-only highlighter and a terminal panel.

## Features

- **VS Code Dark+ style highlighting**, Python only — keywords, control flow,
  strings (incl. `f`/`r`/`b` prefixes and multi-line docstrings), comments,
  numbers, decorators, classes, function definitions and calls, `self`/`cls`.
- **Built-in terminal panel** — press `F5` to run the current file. Output and
  errors stream live (stderr in red), `input()` works through a stdin line, and
  you can stop the process at any time.
- **Smart editing** — auto-indent (including after `:` and open brackets),
  auto-closing brackets and quotes, smart backspace, block indent/dedent,
  comment toggling.
- **Tabs**, drag-and-drop file opening, unsaved-changes protection.
- **Line numbers, current-line highlight, zoom** (`Ctrl` + mouse wheel).
- **Choose your interpreter** — use system Python, a virtualenv or Conda.
- **Small codebase** — about 1,200 lines of readable Python, one dependency.

## Installation

### Requirements

- Linux (X11 or Wayland)
- Python 3.9 or newer
- PyQt6 ≥ 6.4 (installed automatically)

Then start it with:

```bash
pylite                 # empty editor
pylite script.py       # open one or more files
python3 -m pylite      # equivalent, without installing the entry point
```

### Run from source without installing

```bash
pip install -r requirements.txt
python3 -m pylite
```

### Optional: add it to your application menu

```bash
install -Dm644 packaging/pylite.desktop ~/.local/share/applications/pylite.desktop
install -Dm644 pylite/assets/pylite.svg ~/.local/share/icons/hicolor/scalable/apps/pylite.svg
```

### Troubleshooting

If Qt fails with *"Could not load the Qt platform plugin "xcb""*, install the
missing system library. On Debian/Ubuntu:

```bash
sudo apt install libxcb-cursor0
```

On some Wayland setups you may also need `qt6-wayland`.

## Keyboard shortcuts

| Action | Shortcut |
| --- | --- |
| New / Open / Save / Save As | `Ctrl+N` / `Ctrl+O` / `Ctrl+S` / `Ctrl+Shift+S` |
| Close tab / Quit | `Ctrl+W` / `Ctrl+Q` |
| **Run file** | `F5` (or `Ctrl+R`) |
| **Stop process** | `Shift+F5` |
| Toggle terminal panel | `Ctrl+J` (or ``Ctrl+` ``) |
| Toggle comment | `Ctrl+/` |
| Indent / Dedent selection | `Tab` / `Shift+Tab` (or `Ctrl+]` / `Ctrl+[`) |
| Undo / Redo | `Ctrl+Z` / `Ctrl+Shift+Z` |
| Zoom in / out / reset | `Ctrl+=` / `Ctrl+-` / `Ctrl+0` (or `Ctrl` + wheel) |
| Send EOF to the running program | `Ctrl+D` (in the terminal input line) |

## How running works

When you press `F5`, PyLite saves the file (asking for a name if it is new) and
starts `python3 -u <file>` as a child process with the file's folder as the
working directory. Output is shown in the terminal panel; anything you type in
the input line is sent to the program's stdin.

The interpreter defaults to `python3` from your `PATH`. To use a virtualenv or a
different Python, choose **Run → Select Interpreter…** and pick its executable,
for example `~/.venvs/myproject/bin/python`. The choice is remembered.

## Project layout

```
pylite/
├── pylite/
│   ├── app.py          # main window, tabs, menus, file handling, entry point
│   ├── editor.py       # code editor widget (line numbers, smart editing)
│   ├── highlighter.py  # Python syntax highlighter
│   ├── terminal.py     # run panel (QProcess, live output, stdin)
│   ├── theme.py        # colours, fonts and the Qt stylesheet
│   └── assets/         # application icon
├── packaging/          # .desktop entry
├── docs/               # screenshot
└── pyproject.toml
```

To restyle the app, edit the palette at the top of `pylite/theme.py`.

## Limitations

- The run panel is a pipe, not a real pseudo-terminal. `input()`, `print()` and
  tracebacks work as expected, but full-screen programs (`curses`, `vim`) and
  ANSI colours do not; escape sequences are stripped from the output.
- Stopping a script sends `SIGTERM` to the script's process; subprocesses that
  the script itself started are not killed.
- No code completion, linting, debugger or search-and-replace yet. PyLite is
  intentionally small.

## Contributing

Issues and pull requests are welcome. Please keep changes small and in the
spirit of the project: fast startup, few dependencies, readable code.

## License

Released under the [MIT License](LICENSE).
