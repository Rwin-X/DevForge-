# Changelog

## 2.0.0

### Added
- **Categories** — organize entries into categories (General, Work, Banking, etc.) with a filter bar in the sidebar.
- **Tags** — attach free-form tags to any entry; searchable alongside name/username/URL.
- **Password strength meter** — live entropy-based strength feedback while typing a password, both when creating an entry and when setting a master password.
- **Security Check dashboard** — a summary view that flags weak passwords and passwords reused across multiple entries, with one click to jump to the affected entry.
- **Password history** — changing an entry's password keeps the previous value (last 5 shown), so you can see what it used to be.
- **Change master password** — re-encrypts the entire vault under a new master password, with a fresh random salt.
- **Auto-lock** — the vault automatically re-locks after 5 minutes of inactivity (configurable in `passvault/__main__.py`).
- **Encrypted export/import (`.pvexport`)** — export your vault protected by a password of your choice, portable and independent of your main master password.
- **Plaintext export/import (JSON/CSV)** — for migrating to another tool, gated behind an explicit warning dialog.
- **Atomic writes** — vault saves now write to a temp file and swap it in, so a crash mid-save can't corrupt your vault.
- Unit test suite (`tests/`) covering crypto, storage, password utilities, and the entry model.

### Changed
- **Project restructured** from a single script into a proper package (`passvault/`) with separated concerns: `crypto.py`, `storage.py`, `models.py`, `password_utils.py`, `theme.py`, and a `ui/` subpackage for screens and widgets.
- Entry point is now `python -m passvault` or `python run.py` instead of a single `passvault.py`.

## 1.0.0

- Initial release: single-file Tkinter password manager with PBKDF2 + Fernet encryption, add/edit/delete entries, password generator, show/hide, copy-to-clipboard, and search.
