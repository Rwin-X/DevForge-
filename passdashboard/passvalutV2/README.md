# 🔐 PassVault

A minimal, local-first password manager with a clean dark UI and real encryption — no cloud, no accounts, no telemetry. Your data never leaves your machine.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
![Tests](https://img.shields.io/badge/tests-36%20passing-brightgreen.svg)

---

## Overview

PassVault is a desktop application for storing passwords, usernames, URLs, categories, tags, and notes. Everything is encrypted with a key derived from your own master password — nothing is ever stored in plain text, and there is no way for anyone (including you, if you forget your password) to bypass that.

Built with Python's standard `tkinter` for the UI, so there's nothing heavy to install beyond one library.

## Features

- 🔒 **Real encryption at rest** — AES-based encryption (Fernet) with a key derived via PBKDF2-HMAC-SHA256 (390,000 iterations)
- 🎨 **Minimal, dark UI** — clean two-pane layout, no clutter
- 🗂 **Categories & tags** — organize entries (Work, Banking, Personal…) and filter or search by tag
- 📊 **Password strength meter** — live entropy-based feedback as you type, on both entries and your master password
- 🛡 **Security Check dashboard** — flags weak and reused passwords across your whole vault, one click to fix
- 🕓 **Password history** — see an entry's previous passwords after you change one
- 🔑 **Password generator** — secure random password generation with adjustable character sets
- 🔁 **Change master password** — re-encrypts your entire vault under a new password + fresh salt
- ⏱ **Auto-lock** — vault re-locks itself after 5 minutes of inactivity
- 📤 **Encrypted export/import** (`.pvexport`) — portable backups protected by a password of your choice
- 📄 **Plaintext export/import** (JSON/CSV) — for migrating to another tool, gated behind an explicit warning
- 👁 **Reveal / hide & one-click copy** — passwords stay masked until you choose to view or copy them
- 💻 **100% offline** — no network calls, no accounts, no sync
- 🧪 **Tested** — unit tests cover encryption, storage, and password logic

## Screenshots

*(Add screenshots here — e.g. `screenshots/login.png`, `screenshots/vault.png`, `screenshots/security-check.png`)*

## Installation

### Requirements

- Python 3.8 or later
- `tkinter` (included with most Python installations — see note below for Linux)
- [`cryptography`](https://pypi.org/project/cryptography/)

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/passvault.git
cd passvault

# Install dependencies
pip install -r requirements.txt

# Run it
python run.py
# or equivalently:
python -m passvault
```

> **Linux users:** if you get a `ModuleNotFoundError: No module named 'tkinter'`, install it via your package manager, e.g.:
> ```bash
> sudo apt install python3-tk      # Debian/Ubuntu
> sudo dnf install python3-tkinter # Fedora
> sudo pacman -S tk                # Arch
> ```

## Usage

1. **First run** — create a master password. Choose something strong; this is the only key to your vault. The strength meter will guide you.
2. **Unlock** — on future runs, enter your master password to decrypt and open the vault.
3. **Add an entry** — click **+ New Entry**, fill in name, category, tags, username, password (or generate one with ⟳), URL, and notes.
4. **Organize** — use the category chips at the top of the list to filter, or search by name/username/URL/tag.
5. **Check your security** — open the **⋮ Menu → Security Check** to see weak or reused passwords at a glance.
6. **Back up** — use **⋮ Menu → Export…** for an encrypted `.pvexport` backup, or plaintext JSON/CSV if migrating elsewhere.
7. **Rotate your master password** — **⋮ Menu → Change Master Password…** whenever you want.

The vault also **auto-locks after 5 minutes of inactivity** — you'll need to re-enter your master password to keep working.

## How it works

```
Master Password + Random Salt
        │
        ▼
  PBKDF2-HMAC-SHA256
  (390,000 iterations)
        │
        ▼
   Encryption Key
        │
        ▼
  Fernet (AES-128-CBC + HMAC)
        │
        ▼
   vault.dat (encrypted)
```

- **`vault.salt`** — a randomly generated salt (not secret, but required alongside your password to derive the correct key)
- **`vault.dat`** — your encrypted vault; unreadable without the correct master password
- Your master password is **never written to disk** in any form
- Vault writes are **atomic** (write-to-temp-then-replace), so an interrupted save can't corrupt your data

## ⚠️ Important: no recovery

There is intentionally **no password reset or recovery mechanism**. If you forget your master password, your vault **cannot** be decrypted by anyone — that's the whole point of real encryption. Back up your master password somewhere safe (e.g. a physical safe or another password manager).

## Backing up your vault

Your vault is two files, created next to where you run the app:

```
vault.dat    # encrypted entries
vault.salt   # salt used for key derivation
```

Back up both together — losing `vault.salt` makes `vault.dat` undecipherable even with the correct master password. For a more portable backup, use **Export → Encrypted (.pvexport)**, which bundles its own salt into a single file protected by a password you choose.

## Project structure

```
passvault/
├── passvault/
│   ├── __init__.py
│   ├── __main__.py              # App shell, entry point, auto-lock
│   ├── crypto.py                 # Key derivation, encrypt/decrypt
│   ├── storage.py                # Vault load/save, export/import
│   ├── models.py                 # Entry data model, categories, tags
│   ├── password_utils.py         # Generator, strength scoring, reuse detection
│   ├── theme.py                  # Color palette / styling constants
│   └── ui/
│       ├── __init__.py
│       ├── widgets.py             # Reusable widgets (scroll frame, strength bar, tag chip)
│       ├── login_screen.py        # Master password entry / vault creation
│       ├── entry_dialog.py        # Add/edit entry dialog
│       ├── vault_screen.py        # Main list + detail view
│       ├── change_master_dialog.py
│       ├── export_import_dialog.py
│       └── security_dashboard.py  # Weak/reused password report
├── tests/
│   ├── test_crypto.py
│   ├── test_storage.py
│   ├── test_password_utils.py
│   └── test_models.py
├── run.py                        # Convenience launcher
├── requirements.txt
├── pytest.ini
├── CHANGELOG.md
└── README.md
```

## Running tests

```bash
pip install pytest
pytest
```

36 tests cover key derivation, encrypt/decrypt round-trips, wrong-password handling, vault save/load, atomic writes, encrypted and plaintext export/import, password generation, strength scoring, weak/reused password detection, and the entry model (including password history).

## Security notes

- Encryption: **Fernet** (AES-128 in CBC mode with PKCS7 padding, authenticated via HMAC-SHA256) from the [`cryptography`](https://cryptography.io/) library
- Key derivation: **PBKDF2-HMAC-SHA256**, 390,000 iterations, 16-byte random salt per vault
- Password strength scoring is a local heuristic (entropy estimate + common-pattern penalties) — it never calls any external service
- No network access, no analytics, no external calls of any kind
- This is a personal-use tool, not an audited enterprise product — review the source before trusting it with sensitive data

## Contributing

Issues and pull requests are welcome. Please keep the philosophy in mind: minimal, offline, no unnecessary dependencies, and every new module should come with tests.

## License

MIT — do whatever you'd like with this, no warranty provided.
