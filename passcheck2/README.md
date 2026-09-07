# passcheck

A minimal desktop tool that scores password strength in real time as
you type, with a plain-language explanation of what makes the
password weak and how to improve it.

## Features

- Live strength meter updated on every keystroke, no submit button
- Entropy-based scoring with penalties for common passwords, keyboard
  sequences, and repeated characters
- Rough crack-time estimate based on an offline GPU-cracking baseline
- Concrete, per-password issues and suggestions, not a generic tip list
- Show/hide toggle for the password field

## Requirements

- Python 3.10 or newer
- PyQt6 (installed automatically by `install.sh`)

## Installation

### Quick install

```bash
./install.sh
```

### Manual install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run from source

```bash
python -m passcheck.main
```

## Usage

Type a password into the field. The meter, strength label, issues, and
suggestions update immediately. Use "Show" to reveal the typed
characters if you need to verify what was entered.

Nothing typed into this tool is stored, logged, or sent anywhere —
scoring happens entirely in memory on your own machine.

## Project structure

```
passcheck/
├── main.py                    # entry point
├── core/
│   └── strength.py             # scoring engine — no PyQt imports, unit-testable headlessly
└── ui/
    ├── main_window.py           # frameless main window, wires input to the meter
    ├── style.py                 # QSS stylesheet and palette constants
    └── widgets/
        ├── title_bar.py          # custom drag-to-move title bar
        ├── window_controls.py    # procedurally drawn minimize/maximize/close glyphs
        └── strength_meter.py     # procedurally drawn segmented strength bar
tests/
└── test_strength.py            # unit tests for the scoring engine
```

## Why this design

Scoring runs directly on the main thread rather than a worker thread:
`score_password()` is a pure computation with no I/O, completing in
well under a millisecond, so moving it to a background thread would
add complexity without a real responsiveness benefit.

## License

MIT
