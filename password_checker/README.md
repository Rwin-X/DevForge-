[README (1).md](https://github.com/user-attachments/files/29394680/README.1.md)
<div align="center">

```
██████╗  █████╗ ███████╗███████╗██╗    ██╗ ██████╗ ██████╗ ██████╗ 
██╔══██╗██╔══██╗██╔════╝██╔════╝██║    ██║██╔═══██╗██╔══██╗██╔══██╗
██████╔╝███████║███████╗███████╗██║ █╗ ██║██║   ██║██████╔╝██║  ██║
██╔═══╝ ██╔══██║╚════██║╚════██║██║███╗██║██║   ██║██╔══██╗██║  ██║
██║     ██║  ██║███████║███████║╚███╔███╔╝╚██████╔╝██║  ██║██████╔╝
╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝ ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═════╝ 
```

### Password Strength Checker

*A minimal, dark-themed desktop GUI for real-time password analysis*

---

![Python](https://img.shields.io/badge/Python-3.10%2B-0066CC?style=flat-square&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-6.x-0088EE?style=flat-square&logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-00C2FF?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-00E5B0?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-0077FF?style=flat-square)

</div>

---

## Overview

**PassWord** is a lightweight desktop application that analyzes the strength of any password in real time. Built with PyQt6 and custom-painted widgets, it gives you entropy metrics, crack-time estimates, character composition analysis, and a built-in secure password generator — all in a clean, dark blue UI with smooth animations.

No internet connection required. Nothing is logged or transmitted.

---

## Features

```
┌─────────────────────────────────────────────────┐
│                                                 │
│   ◉  Real-time strength analysis               │
│   📊  Shannon entropy calculation (bits)        │
│   ⏱  Crack-time estimation (GPU offline)       │
│   🔵  Animated 5-segment strength bar          │
│   💊  Character type pill badges               │
│   ✅  Live requirements checklist              │
│   ⚡  Secure password generator (16 chars)     │
│   📋  One-click copy to clipboard              │
│   👁  Toggle password visibility               │
│   ⚠  Common password detection (30+ entries)  │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Strength Levels

| Score | Label | Color |
|:-----:|-------|-------|
| 1 | Very Weak | 🔴 `#FF3A3A` |
| 2 | Weak | 🟠 `#FF8C00` |
| 3 | Fair | 🔵 `#1A7FFF` |
| 4 | Strong | 🩵 `#00C2FF` |
| 5 | Very Strong | 🟢 `#00E5B0` |

### Entropy Reference

| Bits | Assessment |
|------|-----------|
| < 25 | Critically weak |
| 25 – 40 | Weak |
| 40 – 60 | Moderate |
| 60 – 80 | Strong |
| 80 + | Very strong |

> Crack-time is calculated assuming a GPU offline attack at **10 billion guesses per second** — the realistic worst-case scenario for a leaked hash.

---

## Installation

**Requirements:** Python 3.10 or higher

```bash
# 1. Clone the repository
git clone https://github.com/Rwin-X/DevForge-.git
cd password-checker

# 2. Install the only dependency
pip install PyQt6

# 3. Run
python password_checker.py
```

No virtual environment needed for a single-file project, though one is always good practice:

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux / macOS
pip install PyQt6
python password_checker.py
```

---

## How It Works

### Entropy Calculation

Entropy is computed using Shannon's formula based on the character set used:

```
charset_size = 26 (lower) + 26 (upper) + 10 (digits) + 32 (symbols)
entropy = len(password) × log₂(charset_size)
```

A password only using lowercase letters has a charset of 26.
One using all four types has a charset of 94.

### Scoring Logic

A password receives 1 point for each satisfied condition:

```python
✔  Length ≥ 8 characters       → +1
✔  Length ≥ 12 characters      → +1
✔  Mixed case (a–z + A–Z)      → +1
✔  Contains a digit (0–9)      → +1
✔  Contains a symbol (!@#…)    → +1
```

Common passwords (e.g. `password`, `123456`, `iloveyou`) are hard-flagged as **⚠ Common Password** regardless of score.

### Password Generator

The generator produces a random 16-character password from the full charset (`a–z A–Z 0–9 !@#$%^&*`) and validates that it achieves a score of 5 before returning it. Passwords that don't meet the bar are silently discarded and regenerated.

---

## Project Structure

```
password-checker/
│
├── password_checker.py    # single-file application
└── README.md
```

### Key Classes

| Class | Role |
|-------|------|
| `SegmentBar` | Custom-painted animated 5-segment strength indicator |
| `StrengthBar` | Gradient fill bar (alternate renderer) |
| `PillBadge` | Character-type indicator badge with active/inactive states |
| `CheckRow` | Live requirement checklist row |
| `PasswordChecker` | Main window — layout, logic, and event handling |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| GUI Framework | PyQt6 |
| Custom Rendering | `QPainter`, `QPainterPath`, `QLinearGradient` |
| Animation | `QPropertyAnimation` + `QEasingCurve.OutCubic` |
| Clipboard | `QGuiApplication.clipboard()` |

---

## Security Notes

- All analysis runs **locally** — no data is sent anywhere
- The crack-time model assumes **bcrypt/SHA-256 GPU cracking at 10B/s** (worst case for offline attacks)
- Common password list covers the 30 most breached passwords per HIBP data
- The generator uses Python's `random.choices()` — sufficient for UI purposes; for cryptographic key generation, use `secrets` instead

---

## Contributing

Pull requests are welcome. For major changes, open an issue first.

```bash
git checkout -b feature/your-feature
git commit -m "feat: add your feature"
git push origin feature/your-feature
```

---

## License

MIT — do whatever you want with it.

---

<div align="center">

built by [@Rwin-X](https://github.com/Rwin-X) &nbsp;·&nbsp; Python + PyQt6 &nbsp;·&nbsp; 2025

</div>
