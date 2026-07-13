# secNT

> A minimal encrypted notepad. What you type never touches disk in plaintext.

secNT is a zero-friction, always-encrypted notepad. There's no "Save" button, no plaintext file sitting on your drive, and no manual encrypt/decrypt step to forget. You open it, you type, and every change is transparently encrypted with **AES-256-GCM** and written to disk — automatically, on a short debounce timer.

```
┌─────────────────────────────────────┐
│  File                                │
├─────────────────────────────────────┤
│                                       │
│  your notes, plaintext on screen     │
│  AES-256-GCM ciphertext on disk      │
│                                       │
├─────────────────────────────────────┤
│  Saved (encrypted)                   │
└─────────────────────────────────────┘
```

## Why

Most "secure notes" tools ask you to lock/unlock a vault, click save, or trust a cloud backend. secNT does none of that:

- **No plaintext at rest.** `notes.txt` on disk is always a base64-encoded AES-256-GCM blob — even mid-sentence.
- **No manual save.** A debounced autosave (500ms after you stop typing) handles persistence for you.
- **No external dependencies beyond the essentials.** Just `PyQt6` for the UI and `cryptography` for AEAD encryption.
- **No accounts, no network, no telemetry.** Everything lives next to the script.

## How it works

| File | Purpose |
|---|---|
| `secNT.py` | The app itself |
| `secNT.key` | Your AES-256 key, base64-encoded, generated once on first run |
| `notes.txt` | Your notes — always encrypted, never plaintext |

On launch, secNT reads `secNT.key` (generating one if it's your first run), decrypts `notes.txt` in memory, and shows you the plaintext in the editor. From then on, every keystroke resets a save timer; when you pause typing, the current buffer is re-encrypted with a fresh nonce and written back to `notes.txt`.

### Crypto details

- **Cipher:** AES-256-GCM (authenticated encryption — tampering or corruption is detected, not silently accepted)
- **Key:** 256-bit, generated via `AESGCM.generate_key()`, stored base64-encoded in `secNT.key`
- **Nonce:** 12 random bytes (`os.urandom(12)`) generated fresh on every save, prepended to the ciphertext
- **Storage format:** `base64(nonce || ciphertext)` written directly to `notes.txt`

## Requirements

```bash
pip install PyQt6 cryptography
```

## Usage

```bash
python secNT.py
```

That's it. Start typing. Your key is shown once on first run (with a "Copy Key" button) — save it somewhere safe. You can view it again anytime from **File → Show Encryption Key**.

## ⚠️ Important notes

- **Losing `secNT.key` means losing your notes.** There is no recovery mechanism, no password reset, no backdoor — that's the point.
- **`secNT.key` and `notes.txt` should never be committed to version control.** Add them to `.gitignore` if you fork this into your own project.
- This is a personal-use tool for local, at-rest note encryption — it does not protect against a compromised machine, a keylogger, or someone with access while the app is open and decrypted on screen.

## Roadmap ideas

- [ ] Passphrase-derived key (Argon2id) instead of a raw key file, for an extra factor beyond "possession of `secNT.key`"
- [ ] Multiple note files / tabs
- [ ] Auto-lock after inactivity (re-prompt for key / passphrase)
- [ ] Optional key file location override via CLI flag

---

Part of the [devforge](#) toolkit.
