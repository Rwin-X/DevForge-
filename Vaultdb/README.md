# VaultDB

A minimal, dark, fully graphical tool for creating and managing a personal database — with optional password encryption. Built with **PyQt6**.

No SQL and no command line knowledge needed. Notes, files and small data items live in a single portable file that can be locked with a password. Every screen explains itself in plain language, so non-technical users can use it without instructions.

```
┌────────────┬─────────────────────────────────────────────┐
│ VAULTDB    │  Notes                                      │
│ notes.vdb  │  Write anything you want to keep.           │
│            │                                             │
│ Overview   │  ┌─────────────┐  TITLE                     │
│ Notes    ◀ │  │ Search…     │  ┌───────────────────────┐ │
│ Files      │  │─────────────│  │ Wi-Fi passwords       │ │
│ Data       │  │ Wi-Fi pass… │  └───────────────────────┘ │
│ Security   │  │ Ideas       │  YOUR NOTE                 │
│            │  └─────────────┘  ┌───────────────────────┐ │
│ New        │  [ + New note ]   │ …                     │ │
│ Open…      │                   └───────────────────────┘ │
└────────────┴─────────────────────────────────────────────┘
```

> Replace the block above with a real screenshot: `docs/screenshot.png`.

## Features

| Section       | What it does                                                                   |
|---------------|--------------------------------------------------------------------------------|
| **Overview**  | Counts, stored size, file location, protection status                          |
| **Notes**     | Titled notes with tags, search, created / last-changed timestamps              |
| **Files**     | Drag & drop or browse to add any file; save copies back out; multi-select      |
| **Data**      | Name → value pairs (e.g. *Email → me@example.com*), one-click **Copy value**   |
| **Security**  | Set / change / remove password, auto-lock, readable JSON export & import       |

**Security features**

- **Auto-lock** after 1 / 5 / 15 / 60 minutes of real inactivity (keyboard, mouse, scroll). On lock the database is saved, wiped from memory, every screen is cleared, and any open dialog is dismissed. Default: 5 minutes.
- **Clipboard guard**: a copied value is removed from the clipboard after 30 seconds, or immediately on lock — but only if the clipboard still holds that value.
- **Automatic backup**: every save keeps the previous good version as `<name>.bak`.
- **Crash-safe saves**: written to a temp file, flushed to disk (`fsync`), then atomically renamed.
- **Legacy upgrade**: databases from earlier versions open normally and are upgraded to the current format on first save.

**Beginner-friendly by design:** every field has a plain-language label and example placeholder, empty screens say what to do next, destructive actions ask for confirmation, and a first-run welcome screen explains the three steps.

Also: autosave after every change, keyboard shortcuts (`Ctrl+N`, `Ctrl+O`, `Ctrl+S`), and plain SQLite compatibility for unencrypted databases.

## Install

Requires **Python 3.11+** (uses `sqlite3.Connection.serialize/deserialize`).

```bash
git clone https://github.com/<your-user>/vaultdb.git
cd vaultdb
pip install -r requirements.txt
python vaultdb.py
```

On Linux you may also need Qt's system libraries, e.g. `sudo apt install libxcb-cursor0`.

## Usage

1. **New** — choose a file location; optionally set a password immediately.
2. **Open** — encrypted `.vdb` files prompt for the password; plain SQLite files open directly.
3. Use the **Text**, **Files** and **Key / Value** tabs to add data. Every change is written to disk immediately.
4. Use **Security** to encrypt an existing plain database, rotate the password, or remove encryption.

| Shortcut   | Action         |
|------------|----------------|
| `Ctrl + N` | New database   |
| `Ctrl + O` | Open database  |
| `Ctrl + S` | Save           |

## Security model

| Property           | Implementation                                                              |
|--------------------|-----------------------------------------------------------------------------|
| Cipher             | **AES-256-GCM** (authenticated encryption)                                  |
| Key derivation     | **scrypt**, N=2¹⁷, r=8, p=1 (~128 MiB memory, ~0.3 s) — memory-hard, so GPU/ASIC guessing is expensive |
| Salt               | 16 random bytes, regenerated on every password change                       |
| Nonce              | 12 random bytes, **regenerated on every save** (never reused with a key)    |
| Header integrity   | The header (magic, KDF parameters, salt) is bound to the ciphertext as AEAD associated data; changing any byte fails authentication |
| Hostile files      | Absurd KDF parameters are rejected *before* any key derivation (prevents memory-exhaustion attacks) |
| Plaintext handling | The decrypted database exists **only in memory** while open                 |
| Disk writes        | Temp file → `fsync` → atomic rename; previous version kept as `.bak`        |

### Container format (v2)

```
offset  size  field
0       6     magic  "VDB2\x00\x02"
6       1     scrypt log2(N)
7       1     scrypt r
8       1     scrypt p
9       16    salt
25      12    nonce
37      n     AES-256-GCM ciphertext + 16-byte tag   (AAD = bytes 0..24)
```

Databases created by earlier versions (v1: PBKDF2-HMAC-SHA256 + Fernet) can still be opened and are upgraded to v2 automatically.

### Limitations — read before trusting it

- **No password recovery.** A lost password means lost data by design.
- **Whole-file encryption.** Every save re-encrypts the entire database (the derived key is cached, so saves do not re-run scrypt, but the full file is still rewritten). Fine for notes and modest files; not intended for multi-GB stores.
- **Memory-resident.** The full database is loaded into RAM while open.
- **Not hardened against a compromised machine.** Keyloggers, memory dumps and malware on the host are out of scope. Python cannot reliably wipe secrets from memory, so auto-lock removes the database from the app, but copies may linger in process memory until it is reused or the app exits.
- **JSON exports are not encrypted.** They exist for readable backups and migration; the app warns before writing one. Store them carefully or delete them.
- **The `.bak` file is as sensitive as the database.** It is encrypted the same way, but it is a second copy — delete it when you delete the database.
- **Auto-lock is bypassed by an unencrypted database** (there is nothing to lock).
- **Not independently audited.** It composes standard primitives from the `cryptography` library, but the composition itself has not been reviewed by a third party.
- Use a long passphrase. A memory-hard KDF slows guessing but cannot save a weak password. The strength bar in the password dialog is a rough hint based on length and variety, not a guarantee.

## Project structure

```
vaultdb/
├── vaultdb.py        # PyQt6 GUI (presentation only)
├── core.py           # storage + encryption layer (no GUI imports)
├── tests/
│   └── test_core.py  # headless tests for crypto and CRUD
├── requirements.txt
├── LICENSE
└── README.md
```

The GUI never touches SQLite or cryptography directly; everything goes through `core.Vault`, so the storage layer can be reused from scripts or tests. The GUI itself has no automated tests yet.

### Data model

The *Data* tab is stored in `kv_entries`.

```sql
text_entries(id, title, body, tags, created, modified)
file_entries(id, name, mime, size, data BLOB, tags, created)
kv_entries(id, key UNIQUE, value, created, modified)
```

## Tests

```bash
python tests/test_core.py
```

18 headless checks: no plaintext on disk; wrong / missing password; binary round-trip; fresh nonce per save; tampering detected in the KDF parameters, salt, nonce, ciphertext and tag; hostile KDF parameters and truncated files refused; `.bak` behaviour; re-keying; removing encryption; literal search for `%` and `_`; JSON export → import round-trip with atomic rollback on a corrupt file; **opening a genuine v1 file and upgrading it**; plain SQLite; default header parameters.

The GUI has no automated tests. Its auto-lock and clipboard logic was checked with a simulated clock, but the Qt windows themselves have only been reviewed statically.

## Build a standalone executable

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name VaultDB vaultdb.py
```

## Roadmap

- [ ] Streaming / chunked encryption for large databases
- [ ] Argon2id as an alternative KDF
- [ ] Optional key file as a second factor
- [ ] Attachment preview (images, text)
- [ ] GUI test suite (pytest-qt)
- [x] Auto-lock, clipboard guard, automatic backups
- [x] scrypt + AES-256-GCM, JSON export / import

## License

MIT — see [LICENSE](LICENSE).
