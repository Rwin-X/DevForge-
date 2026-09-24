# TERMPAL

A persistent ASCII creature that lives in your terminal, for Linux and macOS.

TERMPAL runs as a full-screen `curses` interface. Feed it, play with it,
clean it, and let it rest. It ages through life stages, its mood reacts
to how well you look after it, and its state is saved to disk so it
keeps aging even while you are not looking - close the terminal and it
picks up exactly where you left it, hungrier or happier depending on
how long you were gone.

## Features

- **Persistent simulation** - hunger, energy, fun, hygiene, and health
  decay in real time based on elapsed wall-clock time, not just while
  the program is open. A creature left alone for a week comes back
  neglected, not frozen.
- **Life stages** - progresses from egg to hatchling to juvenile to
  adult to elder as real hours pass, each with its own ASCII sprite set.
- **Mood-driven ASCII art** - the creature's appearance changes with its
  current mood (thriving, content, bored, hungry, tired, unwell,
  critical), independent of its life stage.
- **Two mini-games** - a number-guessing game and a reflex catch game,
  both playable from inside the TUI, that restore fun and are tracked
  in the creature's lifetime stats.
- **Real consequences** - sustained starvation drains health over time
  and the creature can die of neglect; a tombstone sprite and death
  reason are shown, and a new creature can be started in its place.
- **Local, offline save file** - a single JSON file under
  `~/.local/share/termpal/`, no network access, no account.

## Requirements

- Linux or macOS (relies on the `curses` terminal library)
- Python 3.10 or newer
- No third-party runtime dependencies - `curses`, `json`, and
  `argparse` are all part of the Python standard library.

On most systems `curses` ships with Python already. If it is missing:

```bash
# Debian / Ubuntu
sudo apt install python3-dev

# Fedora
sudo dnf install python3

# Arch
sudo pacman -S python
```


## Usage

On first run, TERMPAL asks for a name before the full-screen interface
opens. After that, the same creature loads automatically every time.

| Action              | Key |
|----------------------|-----|
| Feed                 | `F` |
| Play                 | `P` |
| Clean                | `C` |
| Rest                 | `R` |
| Guessing mini-game    | `G` |
| Catch mini-game       | `M` |
| Release / start over  | `X` (asks for confirmation) |
| Quit                  | `Q` |

Command-line flags:

```bash
termpal              # launch the TUI (creates a creature on first run)
termpal --reset       # delete the current save and start fresh
termpal --save-path   # print the save file location and exit
termpal --version     # print the version and exit
```

## Project structure

```
termpal/
├── termpal/
│   ├── main.py              # CLI entry point: naming prompt, save load, curses handoff
│   ├── core/                 # pure logic, no curses imports - unit-testable headlessly
│   │   ├── creature.py       # stats, decay, mood, life stages, actions
│   │   ├── storage.py        # JSON save/load
│   │   ├── sprites.py        # ASCII art lookup by life stage and mood
│   │   └── games.py          # mini-game rules (guessing game, catch game)
│   └── ui/                    # curses presentation layer - imports core, never the reverse
│       ├── app.py             # main loop, input handling, screen layout
│       ├── theme.py           # color pair setup (phosphor green/cyan)
│       └── widgets.py         # reusable draw helpers (boxes, stat bars, centered text)
├── tests/                     # headless tests for the core/ layer
├── install.sh                 # one-command install
├── pyproject.toml
├── requirements.txt

```

The `core`/`ui` split keeps every simulation rule - decay rates, mood
thresholds, life-stage timing, mini-game logic - testable with plain
`pytest` and no terminal attached. `tests/` exercises `core/` directly;
none of it imports `curses`.

## License

MIT - see [LICENSE](LICENSE).
