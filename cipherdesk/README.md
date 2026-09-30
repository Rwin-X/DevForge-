# Cipherdesk

A desktop cipher workbench: classical and modern encryption, cryptanalysis, and a
session vault, in a native PyQt6 app. The desktop counterpart to the Cipherdesk
web version — same 30+ algorithms, same cross-compatible AES output, native
window.

## Features

- **31 algorithms** across four groups: classical substitution/transposition
  (Caesar, Vigenère, Beaufort, Autokey, Playfair, Polybius, Rail Fence,
  Columnar Transposition, Affine, Atbash, ROT13/47, Baconian, Morse, XOR),
  encodings (Base64/32/URL-safe, Hex, Binary, Percent), modern symmetric
  ciphers (AES in CBC/ECB/CTR/CFB/OFB, 3DES, DES, RC4), asymmetric (RSA with
  hybrid file encryption), and one-way hashes/HMACs (MD5, SHA family,
  RIPEMD-160, SHA-3).
- **Binary file encryption** — drag or browse any file; binary files are
  detected automatically and encrypted byte-for-byte, not as text. Large
  files (>2 MB) run on a background thread so the UI never freezes.
- **Cryptanalysis** — letter frequency vs. English, index of coincidence,
  a brute-force Caesar solver, and Kasiski examination for guessing a
  Vigenère key length.
- **Pipeline** — chain multiple algorithms in sequence.
- **Vault** — save conversions locally (JSON in your config directory),
  restore or delete them later.
- **Cross-compatible with the web version** — AES/DES/3DES/RC4 ciphertext
  uses the same OpenSSL-style salted key derivation as CryptoJS, so text
  or files encrypted in one version decrypt cleanly in the other.

## Architecture

```
cipherdesk/
├── main.py                  # entry point
├── core/                    # pure Python, zero PyQt imports
│   ├── models.py            # dataclasses: CipherSpec, VaultEntry, ...
│   ├── ciphers.py           # every algorithm's implementation + registry
│   ├── analysis.py          # frequency analysis, IC, Caesar solver, Kasiski
│   └── vault.py             # JSON persistence for saved conversions
├── ui/
│   ├── style.py              # QSS stylesheet + palette constants
│   ├── main_window.py        # frameless window, tab wiring
│   ├── workers.py            # QThread workers (RSA keygen, large-file crypto)
│   └── widgets/
│       ├── title_bar.py       # custom frameless chrome
│       ├── algorithm_picker.py
│       ├── key_panel.py
│       ├── pipeline_panel.py
│       ├── convert_tab.py
│       ├── analyze_tab.py
│       └── vault_tab.py
└── tests/                    # core/ logic tests, no Qt dependency
```

`core/` never imports PyQt and is fully covered by `tests/` — every
algorithm's encrypt/decrypt round-trips, plus known test vectors (MD5,
HMAC-SHA256), cross-compatibility, and binary file handling at multiple
byte lengths including AES block-size edge cases.

## Install

```bash
./install.sh
./run.sh
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

## Run the tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## License

MIT — see [LICENSE](LICENSE).
