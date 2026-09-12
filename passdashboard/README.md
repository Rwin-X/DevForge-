# 🔐 PassVault

A minimal, local-first password manager with a clean dark UI and real encryption — no cloud, no accounts, no telemetry. Your data never leaves your machine.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

---

## Overview

PassVault is a single-file desktop application for storing passwords, usernames, URLs, and notes. Everything is encrypted with a key derived from your own master password — nothing is ever stored in plain text, and there is no way for anyone (including you, if you forget your password) to bypass that.

Built with Python's standard `tkinter` for the UI, so there's nothing heavy to install beyond one library.

## Features

- 🔒 **Real encryption at rest** — AES-based encryption (Fernet) with a key derived via PBKDF2-HMAC-SHA256 (390,000 iterations)
- 🎨 **Minimal, dark UI** — clean two-pane layout, no clutter
- 🔑 **Password generator** — built-in secure random password generator
- 👁 **Reveal / hide** — passwords stay masked until you choose to view them
- 📋 **One-click copy** — copy any field without ever displaying it if you don't want to
- 🔍 **Instant search** — filter entries by name, username, or URL as you type
- 📝 **Free-form notes** — attach any extra context to an entry (recovery codes, security questions, etc.)
- 💻 **100% offline** — no network calls, no accounts, no sync. Your vault file stays on your disk.
- 📦 **Single file** — the entire app is one Python script

## Screenshots

*(Add screenshots here after your first run — e.g. `screenshots/login.png`, `screenshots/vault.png`)*

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

# Install the only dependency
pip install cryptography

# Run it
python passvault.py
```

> **Linux users:** if you get a `ModuleNotFoundError: No module named 'tkinter'`, install it via your package manager, e.g.:
> ```bash
> sudo apt install python3-tk      # Debian/Ubuntu
> sudo dnf install python3-tkinter # Fedora
> sudo pacman -S tk                # Arch
> ```

## Usage

1. **First run** — you'll be asked to create a master password. Choose something strong; this is the only key to your vault.
2. **Unlock** — on future runs, enter your master password to decrypt and open the vault.
3. **Add an entry** — click **+ New Entry** and fill in the name, username, password (or generate one with ⟳), URL, and any notes.
4. **View / copy** — click any entry to see its details. Use **Show** to reveal a password, or **Copy** to copy a field to your clipboard without revealing it.
5. **Edit / delete** — use the buttons in the entry detail view.

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

## ⚠️ Important: no recovery

There is intentionally **no password reset or recovery mechanism**. If you forget your master password, your vault **cannot** be decrypted by anyone — that's the whole point of real encryption. Back up your master password somewhere safe (e.g. a physical safe or another password manager).

## Backing up your vault

Your entire vault is just two files, created next to the script:

```
vault.dat    # encrypted entries
vault.salt   # salt used for key derivation
```

Back up both files together. Losing `vault.salt` makes `vault.dat` undecipherable even with the correct master password.

## Project structure

```
passvault/
├── passvault.py    # the entire application
├── vault.dat       # created on first run (encrypted, gitignored)
├── vault.salt      # created on first run (gitignored)
└── README.md
```

## Security notes

- Encryption: **Fernet** (AES-128 in CBC mode with PKCS7 padding, authenticated via HMAC-SHA256) from the [`cryptography`](https://cryptography.io/) library
- Key derivation: **PBKDF2-HMAC-SHA256**, 390,000 iterations, 16-byte random salt
- No network access, no analytics, no external calls of any kind
- This is a personal-use tool, not an audited enterprise product — review the source (it's one file) before trusting it with sensitive data

## Contributing

Issues and pull requests are welcome. Please keep the philosophy in mind: minimal, offline, single-file, no unnecessary dependencies.

## License

MIT — do whatever you'd like with this, no warranty provided.
