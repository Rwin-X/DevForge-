# VaultKeep

A minimal, dark-themed, local-first password manager built with PyQt6.

## Run it

```bash
pip install -r requirements.txt
python main.py
```

First launch asks you to create a master password. Every launch after that
asks you to unlock with it. The vault database lives at
`~/.vaultkeep/vault.db`.

## Security design

| Layer | Choice | Why |
|---|---|---|
| Key derivation | Argon2id, 256 MiB memory, 4 iterations, 2 lanes | Memory-hard, current OWASP-recommended KDF; resists GPU/ASIC brute force far better than PBKDF2/bcrypt |
| Encryption | AES-256-GCM, fresh 96-bit nonce per field | Authenticated encryption — tampering is detected, not just hidden |
| Storage | SQLite, ciphertext + nonce only | A stolen `vault.db` file reveals nothing but opaque blobs and timestamps |
| Master password | Never stored in any form | A separate "verifier" blob (a known plaintext encrypted under the derived key) checks correctness without a crackable hash sitting on disk |
| Unlock check | Verifier decrypt, not a fast hash compare | No fast offline path exists to check password guesses without paying the full Argon2id cost each time |
| Session | Key held only in memory while unlocked | Locking the vault (manually or via auto-lock) drops the reference immediately |
| Clipboard | Auto-clears 20s after a copy | Reduces exposure if you forget to clear it yourself |
| Backups | Independently encrypted with their own password | An exported `.vkbak` file is safe even outside your machine |

Each entry field (title, username, password, url, notes, tags) is encrypted
**individually** — not the row as JSON — so nothing is ever decrypted that
you didn't ask to see.

## Features

- Master-password-protected vault with Argon2id + AES-256-GCM
- Add / edit / delete / search credentials (search across title, username, URL, tags)
- Password generator: random (configurable length, charset, ambiguous-char avoidance) or diceware-style passphrase
- Live strength meter (entropy-based) on every password field
- One-click copy for password and username, with clipboard auto-clear
- Password history per entry (previous versions kept, encrypted, on change)
- Change master password (re-encrypts the entire vault under the new key)
- Encrypted export/import for backups, protected by a separate backup password
- Auto-lock after configurable inactivity (1/5/15/30 min or never)
- Minimal dark UI in white/blue, no external icon or image assets

## Files

- `main.py` — GUI (PyQt6): setup/unlock screens, vault dashboard, entry editor, generator, settings
- `crypto_core.py` — Argon2id KDF + AES-256-GCM primitives
- `vault_db.py` — SQLite schema and encrypted CRUD
- `pwgen.py` — password/passphrase generation and strength estimation
- `theme.py` — the dark/blue/white stylesheet

## Notes

- There is no password recovery. If you lose the master password, the vault
  cannot be decrypted by anyone — that's the point.
- Argon2id is deliberately tuned to take ~1–2 seconds per unlock. That's a
  security feature (it's the cost an attacker pays per guess), not a bug.
