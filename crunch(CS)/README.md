# CRUNCHX

A GUI-based, Crunch-style wordlist generator for security testing labs
(CEH/Security+ practice, offline hash-cracking test vectors, etc.).

## Features

- **Pattern mode** — crunch-style placeholders:
  - `@` = lowercase `[a-z]`
  - `,` = uppercase `[A-Z]`
  - `%` = digit `[0-9]`
  - `^` = symbol `[!@#$%^&*()-_=+]`
  - any other character in the pattern is kept literal (e.g. `user@@%%` →
    `user` + 2 lowercase + 2 digits)
- **Range mode** — classic min/max length brute-force over a chosen
  character set (lowercase / uppercase / digits / symbols, any combination)
- **Live estimate** — combination count and on-disk file size are
  calculated *before* you commit to a run, so you don't accidentally start
  a multi-terabyte generation
- **Confirmation prompt** on very large outputs (>200M words)
- Streams output directly to disk line-by-line — never holds the full
  wordlist in memory, so even billions of combinations won't exhaust RAM
- Save location is fully configurable (output directory + filename)
- PyQt6 GUI, pure white "inverted hacker" theme — white background, black
  borders/text, sharp corners, monospace throughout

## Install

```bash
pip install PyQt6
```

## Run

```bash
python3 crunchx_gui.py
```

## Usage

### Pattern mode
1. Switch to the **PATTERN MODE** tab.
2. Type a pattern, e.g. `admin@@%%^` (→ `admin` + 2 lowercase + 2 digits +
   1 symbol).
3. Check the estimate banner for the resulting word count and file size.
4. Set output directory + filename, click **GENERATE WORDLIST**.

### Range mode
1. Switch to the **RANGE MODE** tab.
2. Set MIN/MAX length and tick the character sets to include.
3. Check the estimate banner — range mode grows extremely fast (e.g. full
   charset, length 1–6, is already ~700 billion words), so narrow the
   range for anything beyond quick lab tests.
4. Set output directory + filename, click **GENERATE WORDLIST**.

Either mode can be stopped mid-run with **STOP** — the file is flushed and
closed cleanly, so a partial wordlist is still usable.

## Files

- `generator_engine.py` — core generation logic (pattern parsing,
  charset/range brute-force, disk streaming, estimation math). No GUI
  dependency, importable standalone.
- `crunchx_gui.py` — PyQt6 window, wires the engine to the UI via a
  `QThread` worker.

## Notes on scope vs. real Crunch

Not implemented (possible extensions later):
- `-p` permutation mode (permute a fixed set of words instead of
  character-by-character generation)
- Duplicate-character constraints (`-d`)
- Start-at / resume-from mid-sequence
- Built-in charset files (crunch ships several predefined `.chr` sets)
